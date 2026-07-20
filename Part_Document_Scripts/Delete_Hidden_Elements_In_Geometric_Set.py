'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Delete_Hidden_Elements_In_Geometric_Set.py
    Version:        1.0
    Code:           Python3.10.4, Pycatia 0.10.0
    Release:        V5R32
    Purpose:        Delete all hidden elements inside a selected geometric set.
    Author:         Kai-Uwe Rathjen
    Date:           20.07.26
    Description:    This script will ask the user to select a geometric set. It will scan all hybrid shapes
                    and child geometric sets recursively and collect everything that is hidden. A hidden
                    child geometric set is deleted whole, including anything inside it, so its contents are
                    not scanned separately. The user is shown a count and prompted to confirm before
                    anything is deleted. Useful for cleaning up construction geometry before handoff.
    dependencies = [
                    "pycatia",
                    "wxPython",
                    ]
    requirements:   Python >= 3.10
                    pycatia
                    wxPython
                    Catia V5 running with an open part document.
                    This script needs an open part document.
    -----------------------------------------------------------------------------------------------------------------------

    Change:

    -----------------------------------------------------------------------------------------------------------------------
'''

#Imports
from pycatia import catia
from pycatia.mec_mod_interfaces.part_document import PartDocument
from pycatia.mec_mod_interfaces.hybrid_body import HybridBody
from pycatia.enumeration.enums import CatVisPropertyShow, CatVisPropertyStatus
import wx
import wx.lib.dialogs as dialogs
import ctypes
import traceback


def _bring_to_front(window):
    u32 = ctypes.windll.user32
    hwnd = window.GetHandle()
    fg_hwnd = u32.GetForegroundWindow()
    fg_tid = u32.GetWindowThreadProcessId(fg_hwnd, None)
    our_tid = ctypes.windll.kernel32.GetCurrentThreadId()
    if fg_tid != our_tid:
        u32.AttachThreadInput(fg_tid, our_tid, True)
    u32.SetWindowLongW(hwnd, -20, u32.GetWindowLongW(hwnd, -20) | 0x0008)
    u32.BringWindowToTop(hwnd)
    u32.SetForegroundWindow(hwnd)
    if fg_tid != our_tid:
        u32.AttachThreadInput(fg_tid, our_tid, False)

'''
    This function reports whether an element is hidden.

    Inputs:
        selection       The active document selection object
        item            The hybrid shape or geometric set to test

    output:
        True if the element is hidden, False if it is shown or its show state is undefined
'''
def is_hidden(selection, item):
    selection.clear()                                                                                            #Selection is the only way to read visibility
    selection.add(item)
    status, show = selection.vis_properties.get_show()                                                            #get_show() returns (status, show)
    if status != CatVisPropertyStatus.catVisPropertyDefined:
        return False                                                                                             #No defined state - leave it alone
    return show == CatVisPropertyShow.catVisPropertyNoShowAttr

'''
    This function recursively collects every hidden element in a geometric set and its children.
    A hidden child set is collected whole and not scanned further, because deleting it removes
    everything inside it anyway.

    Inputs:
        hybrid_body     The geometric set to scan
        selection       The active document selection object
        hidden_shapes   List that hidden hybrid shapes are appended to
        hidden_sets     List that hidden child geometric sets are appended to

    output:
        None
'''
def collect_hidden(hybrid_body, selection, hidden_shapes, hidden_sets):
    shapes = hybrid_body.hybrid_shapes
    for index in range(shapes.count):
        shape = shapes.item(index + 1)
        if is_hidden(selection, shape):
            hidden_shapes.append(shape)
            print(f"  Hidden shape: {shape.name}")

    for child_index in range(hybrid_body.hybrid_bodies.count):
        child_hb = HybridBody(hybrid_body.hybrid_bodies.item(child_index + 1).com_object)                         #Cast child to HybridBody
        if is_hidden(selection, child_hb):
            hidden_sets.append(child_hb)
            print(f"  Hidden geometric set: {child_hb.name}")
            continue                                                                                             #Deleted whole - do not scan inside
        collect_hidden(child_hb, selection, hidden_shapes, hidden_sets)                                           #Recurse into visible child sets


if __name__ == "__main__":
    app = wx.App(None)                                                                                           #Needed for the confirm and error dialogs

    try:
        #Anchoring relavent components
        caa = catia()                                                                                            #Catia application instance
        active_doc = caa.active_document                                                                         #Current document

        object_filter = ("HybridBody",)                                                                          #Set user selection filter (Geometric Set)
        selectionSet = caa.active_document.selection                                                             #Create container for selection
        status = selectionSet.select_element3(object_filter, "Select geometric set to clean up", False, 2, False) #Runs an interactive selection command, exhaustive version.
        if status != "Normal":                                                                                   #Check if selection was succesful
            print("You must select a geometric set")
            exit()

        selected_item = selectionSet.item(1)                                                                     #Get selected item

        if type(active_doc) is PartDocument:                                                                     #If document is part document
            part_document: PartDocument = active_doc
            part = active_doc.part
        else:                                                                                                    #Else get part from product structure
            leaf_product = selected_item.com_object.LeafProduct                                                  #Get leaf product
            part_document = PartDocument(leaf_product.ReferenceProduct.Parent)                                   #Get part document
            part = part_document.part                                                                            #Get new part object

        source_hb = HybridBody(selected_item.value.com_object)                                                   #Cast selected item to HybridBody

        print(f"\n Scanning '{source_hb.name}' for hidden elements...\n")

        hidden_shapes = []
        hidden_sets = []
        collect_hidden(source_hb, selectionSet, hidden_shapes, hidden_sets)                                       #Collect everything hidden
        selectionSet.clear()                                                                                     #Release the elements used for the visibility checks

        total = len(hidden_shapes) + len(hidden_sets)
        if not total:
            print("\n No hidden elements found.\n")
            exit()

        print(f"\n Found {len(hidden_shapes)} hidden shape(s) and {len(hidden_sets)} hidden geometric set(s)")

        message = (f"Found {len(hidden_shapes)} hidden shape(s) and "
                   f"{len(hidden_sets)} hidden geometric set(s).\n\n")
        if hidden_sets:
            message += ("A hidden geometric set is deleted whole, including any visible elements inside it.\n\n")
        message += "Delete all of them?"

        dlg = wx.MessageDialog(None, message, "Confirm Deletion",
                               wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING | wx.STAY_ON_TOP)
        wx.CallAfter(_bring_to_front, dlg)

        if dlg.ShowModal() != wx.ID_YES:
            dlg.Destroy()
            print(" Cancelled — nothing deleted.")
            exit()
        dlg.Destroy()

        selectionSet.clear()                                                                                     #Use selection to delete
        for shape in hidden_shapes:
            selectionSet.add(shape)
        for hybrid_body in hidden_sets:
            selectionSet.add(hybrid_body)
        selectionSet.delete()

        part.update()
        print(f"\n\n Completed - deleted {len(hidden_shapes)} shape(s) and {len(hidden_sets)} geometric set(s)\n\n")

    except Exception as e:
        full_traceback = traceback.format_exc()
        print(full_traceback)
        error_msg = (
            f"Error Summary: {str(e)}\n"
            f"------------------------------------------\n"
            f"Technical Debug Info:\n\n{full_traceback}"
        )
        e_dlg = dialogs.ScrolledMessageDialog(None, error_msg, "Script Error")
        error_icon = wx.ArtProvider.GetBitmap(wx.ART_ERROR, wx.ART_MESSAGE_BOX)
        icon_bitmap = wx.StaticBitmap(e_dlg, wx.ID_ANY, error_icon)
        header_text = wx.StaticText(e_dlg, label="An error occurred while deleting hidden elements:")
        header_font = wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        header_text.SetFont(header_font)
        main_sizer = e_dlg.GetSizer()
        header_sizer = wx.BoxSizer(wx.HORIZONTAL)
        header_sizer.Add(icon_bitmap, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 15)
        header_sizer.Add(header_text, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        main_sizer.Prepend(header_sizer, 0, wx.EXPAND)
        mono_font = wx.Font(9, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        e_dlg.text.SetFont(mono_font)
        e_dlg.SetSize((600, 400))
        e_dlg.CenterOnParent()
        wx.CallAfter(_bring_to_front, e_dlg)
        e_dlg.ShowModal()
        e_dlg.Destroy()
        exit()
