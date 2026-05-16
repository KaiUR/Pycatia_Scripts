'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Delete_Deactivated_Features.py
    Version:        1.0
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Delete all deactivated hybrid shapes inside a selected geometric set.
    Author:         Kai-Uwe Rathjen
    Date:           16.05.26
    Description:    This script will ask the user to select a geometric set. It will scan all hybrid
                    shapes (recursively through child sets) and collect every feature that has been
                    deactivated. The user is shown a count and prompted to confirm before deletion.
                    Useful for cleaning up parts before handoff or release.
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
import wx
import ctypes

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

def collect_deactivated(hb, deactivated):
    shapes = hb.hybrid_shapes
    for i in range(shapes.count):
        shape = shapes.item(i + 1)
        try:
            if not shape.com_object.Activity:                                                                     #Activity = False means deactivated
                deactivated.append(shape)
                print(f"  Found deactivated: {shape.name}")
        except Exception:
            pass                                                                                                   #Skip if Activity cannot be read
    for i in range(hb.hybrid_bodies.count):                                                                      #Recurse into child sets
        child_hb = HybridBody(hb.hybrid_bodies.item(i + 1).com_object)
        collect_deactivated(child_hb, deactivated)

if __name__ == "__main__":
    caa = catia()
    active_doc = caa.active_document

    object_filter = ("HybridBody",)
    selectionSet = caa.active_document.selection
    status = selectionSet.select_element3(object_filter, "Select geometric set to clean up", False, 2, False)
    if status != "Normal":
        print("You must select a geometric set")
        exit()

    selected_item = selectionSet.item(1)

    if type(active_doc) is PartDocument:
        part = active_doc.part
        part_document: PartDocument = active_doc
    else:
        leaf_product = selected_item.com_object.LeafProduct
        part_document = PartDocument(leaf_product.ReferenceProduct.Parent)
        part = part_document.part

    source_hb = HybridBody(selected_item.value.com_object)

    print(f"\n Scanning '{source_hb.name}' for deactivated features...\n")

    deactivated = []
    collect_deactivated(source_hb, deactivated)                                                                   #Collect all deactivated shapes

    if not deactivated:
        print("\n No deactivated features found.\n")
        exit()

    print(f"\n Found {len(deactivated)} deactivated feature(s)")

    app = wx.App(None)
    dlg = wx.MessageDialog(None,
            f"Found {len(deactivated)} deactivated feature(s).\n\nDelete all of them?",
            "Confirm Deletion",
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING | wx.STAY_ON_TOP)
    wx.CallAfter(_bring_to_front, dlg)

    if dlg.ShowModal() != wx.ID_YES:
        dlg.Destroy()
        print(" Cancelled — no features deleted.")
        exit()
    dlg.Destroy()

    sel = caa.active_document.selection                                                                           #Use selection to delete
    sel.clear()
    for shape in deactivated:
        sel.add(shape)
    sel.delete()

    part.update()
    print(f"\n\n Completed - deleted {len(deactivated)} deactivated feature(s)\n\n")
