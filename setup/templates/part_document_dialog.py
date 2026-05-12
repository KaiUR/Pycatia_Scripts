'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Your_Script_Name.py
    Version:        1.1
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        EDIT: One line summary shown on the script button.
    Author:         EDIT: Your Name
    Date:           EDIT: DD.MM.YY
    Description:    EDIT: Full description of what the script does.
                    EDIT: Continuation lines must be indented.
    dependencies = [
                    "pycatia",
                    "wxPython",
                    ]
    requirements:   Python >= 3.10
                    pycatia
                    wxPython
                    Catia V5 running with an open part document.
    -----------------------------------------------------------------------------------------------------------------------

    Change:         12.05.26 1.1: Dialogs raised to foreground of CATIA window.

    -----------------------------------------------------------------------------------------------------------------------
'''

#Imports
from pycatia import catia
from pycatia.mec_mod_interfaces.part_document import PartDocument
from pathlib import Path
import wx
import wx.lib.dialogs
import ctypes

def _bring_to_front(window):
    u32 = ctypes.windll.user32
    hwnd = window.GetHandle()
    fg_hwnd = u32.GetForegroundWindow()
    fg_tid = u32.GetWindowThreadProcessId(fg_hwnd, None)
    our_tid = ctypes.windll.kernel32.GetCurrentThreadId()
    if fg_tid != our_tid:
        u32.AttachThreadInput(fg_tid, our_tid, True)
    u32.BringWindowToTop(hwnd)
    u32.SetForegroundWindow(hwnd)
    if fg_tid != our_tid:
        u32.AttachThreadInput(fg_tid, our_tid, False)

'''
    This function opens a file open dialog and returns the selected file path, or None if cancelled.

    Inputs:
        wildcard    File type filter string, e.g. '*.txt;*.csv'

    output:
        The selected file path as a string, or None if cancelled.
'''
def get_path(wildcard):
    app = wx.App(None)                                                                                         #Bootstrap the wxPython system
    style = wx.FD_OPEN | wx.FD_FILE_MUST_EXIST                                                                 #Open dialog flags
    dialog = wx.FileDialog(None, 'Open', wildcard=wildcard, style=style)                                       #Create file dialog
    if dialog.ShowModal() == wx.ID_OK:                                                                         #Show dialog and wait for selection
        path = dialog.GetPath()                                                                                #Get selected path
    else:
        path = None                                                                                            #User cancelled
    dialog.Destroy()                                                                                           #Close dialog
    return path                                                                                                #Return path or None

'''
    This function searches for a hybrid body (geometric set) by name and returns it.
    Searches recursively through all nested geometric sets.

    Inputs:
        searchName              The name of the geometric set being searched for.
        currentHybridBodies     The current collection of hybrid bodies to search.

    output:
        The geometric set if found, or None if not found.
'''
def searchHybridBody(seachName, currentHybridBodies):
    try:                                                                                                        #Try at current level
        currentSearch = currentHybridBodies.item(seachName)                                                    #Check if we can find it
        if currentSearch is not None:                                                                          #If found
            return currentSearch                                                                               #Return found geometric set
    except:
        pass                                                                                                   #Not found at this level — recurse

    for index in range(currentHybridBodies.count):                                                             #Loop through geometric sets at this level
        if currentHybridBodies.item(index+1).hybrid_bodies.count > 0:
            found = searchHybridBody(seachName, currentHybridBodies.item(index+1).hybrid_bodies)               #Recursive call

            if found is not None:                                                                              #If found
                return found                                                                                   #Return found

    return None                                                                                                #Return not found


'''
    Replaces a hybrid shape with an isolated datum of the same type, preserving its name.
    Supports points (1), curves (2), lines (3), circles (4), and surfaces (5).

    Inputs:
        hybrid_shape_factory    The part's HybridShapeFactory (part.hybrid_shape_factory).
        hybrid_shape            The HybridShape to isolate.
        hybrid_body             The geometric set to append the new datum to.
        name                    Optional name for the datum.

    output:
        None — part.update() must be called after one or more create_datum calls.
'''
def create_datum(hybrid_shape_factory, hybrid_shape, hybrid_body, name=None):
    geo_type = hybrid_shape_factory.get_geometrical_feature_type(hybrid_shape)                                 #Get geometry type

    if geo_type == 1:                                                                                          #Point
        datum = hybrid_shape_factory.add_new_point_datum(hybrid_shape)
    elif geo_type == 2:                                                                                        #Curve
        datum = hybrid_shape_factory.add_new_curve_datum(hybrid_shape)
    elif geo_type == 3:                                                                                        #Line
        datum = hybrid_shape_factory.add_new_line_datum(hybrid_shape)
    elif geo_type == 4:                                                                                        #Circle
        datum = hybrid_shape_factory.add_new_circle_datum(hybrid_shape)
    elif geo_type == 5:                                                                                        #Surface
        datum = hybrid_shape_factory.add_new_surface_datum(hybrid_shape)
    else:
        print(f"  Warning: unsupported geometry type ({geo_type}) for '{name}' — skipped")
        return

    if name: datum.name = name                                                                                 #Apply name if given
    hybrid_body.append_hybrid_shape(datum)                                                                     #Add datum to geometric set
    hybrid_shape_factory.delete_object_for_datum(hybrid_shape)                                                 #Remove the original construction shape


class ScriptDialog(wx.Dialog):
    def __init__(self, parent, title):
        super().__init__(parent, title=title, size=(420, 200), style=wx.DEFAULT_DIALOG_STYLE | wx.STAY_ON_TOP)  #EDIT: Adjust dialog size to fit your fields

        vbox = wx.BoxSizer(wx.VERTICAL)
        grid = wx.FlexGridSizer(2, 2, 10, 10)                                                                  #EDIT: First arg = number of parameter rows

        # EDIT: Add one StaticText + TextCtrl pair per input. Duplicate rows as needed.
        grid.Add(wx.StaticText(self, label="EDIT Parameter 1:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.param_1 = wx.TextCtrl(self, value="EDIT default")                                                 #EDIT: Set field default value
        grid.Add(self.param_1, 1, wx.EXPAND)

        grid.Add(wx.StaticText(self, label="EDIT Parameter 2:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.param_2 = wx.TextCtrl(self, value="EDIT default")                                                 #EDIT: Set field default value
        grid.Add(self.param_2, 1, wx.EXPAND)

        grid.AddGrowableCol(1, 1)
        vbox.Add(grid, 1, wx.ALL | wx.EXPAND, 15)

        btn_sizer = wx.StdDialogButtonSizer()
        btn_ok     = wx.Button(self, wx.ID_OK,     label="OK")
        btn_cancel = wx.Button(self, wx.ID_CANCEL, label="Cancel")
        btn_ok.SetDefault()
        btn_sizer.AddButton(btn_ok)
        btn_sizer.AddButton(btn_cancel)
        btn_sizer.Realize()
        vbox.Add(btn_sizer, 0, wx.ALL | wx.EXPAND, 10)

        self.SetSizer(vbox)
        self.Center()

if __name__ == "__main__":
    caa = catia()                                                                                               #Catia application instance
    active_doc = caa.active_document                                                                           #Current active document
    app = wx.App(None)                                                                                         #Initialize wx application

    if type(active_doc) is not PartDocument:                                                                   #Check that a CATPart is active
        wx.MessageDialog(None, "A CATPart document must be the active document.", "Error",
                wx.OK | wx.ICON_ERROR | wx.STAY_ON_TOP).ShowModal()
        exit()

    part_document: PartDocument = active_doc                                                                   #Cast to PartDocument
    part = part_document.part                                                                                  #Current part
    hybrid_bodies = part.hybrid_bodies                                                                         #Top level geometric sets
    hybrid_shape_factory = part.hybrid_shape_factory                                                           #GSD workbench for creating hybrid shapes

    # NOTE: If your script selects geometry in CATIA before showing the dialog, replace the
    # document check above with the LeafProduct-aware pattern below. This allows the script to
    # work on parts opened inside a product structure as well as standalone CATParts.
    #
    #   object_filter = ("HybridBody",)                                        # EDIT: filter type
    #   selectionSet = active_doc.selection
    #   status = selectionSet.select_element3(object_filter, "Select ...", False, 2, False)
    #   if status != "Normal":
    #       wx.MessageDialog(None, "You must select a geometric set.", "Error",
    #               wx.OK | wx.ICON_ERROR | wx.STAY_ON_TOP).ShowModal()
    #       exit()
    #   selected_item = selectionSet.item(1)
    #
    #   if type(active_doc) is PartDocument:                                   # Standalone CATPart
    #       part_document: PartDocument = active_doc
    #       part = active_doc.part
    #   else:                                                                  # Part inside a product/process
    #       leaf_product = selected_item.com_object.LeafProduct
    #       part_document = PartDocument(leaf_product.ReferenceProduct.Parent)
    #       part = part_document.part
    #
    # Common select_element3 filter types:
    #   "AnyObject"      — anything
    #   "HybridBody"     — geometric sets
    #   "HybridShape"    — individual hybrid shapes
    #   "AxisSystem"     — axis systems
    #   "MonoDimInfinite" — curves
    #   "BiDimInfinite"  — surfaces
    #   "Face"           — faces

    dlg = ScriptDialog(None, "EDIT: Dialog Title")                                                             #EDIT: Set dialog title
    wx.CallAfter(_bring_to_front, dlg)
    if dlg.ShowModal() != wx.ID_OK:                                                                            #If user cancelled
        dlg.Destroy()
        exit()

    param_1 = dlg.param_1.GetValue().strip()                                                                   #EDIT: Get each field value
    param_2 = dlg.param_2.GetValue().strip()                                                                   #EDIT: Get each field value
    dlg.Destroy()                                                                                              #Destroy dialog

    # EDIT: Validate inputs
    if not param_1:
        wx.MessageDialog(None, "EDIT: Parameter 1 cannot be empty.", "Error",
                wx.OK | wx.ICON_ERROR | wx.STAY_ON_TOP).ShowModal()
        exit()

    selectionSet = active_doc.selection                                                                        #Create container for selection
    selectionSet.clear()                                                                                       #Clear any existing selection

    # TODO: Add script logic here using param_1, param_2, part, hybrid_bodies, hybrid_shape_factory
    #
    # To show large text results use ScrolledMessageDialog:
    #   wx.lib.dialogs.ScrolledMessageDialog(None, result_text, "Results", size=(500, 400)).ShowModal()
    #
    # File I/O alongside the document:
    #   doc_name = part_document.name.removesuffix('.CATPart')
    #   output_path = str(Path(str(part_document.path())).parent / (doc_name + "_output.csv"))
    #   try:
    #       with open(output_path, "w") as f:
    #           f.write(...)
    #   except PermissionError:
    #       wx.MessageDialog(None, "Permission denied. Is the file open in another program?", "Error",
    #               wx.OK | wx.ICON_ERROR | wx.STAY_ON_TOP).ShowModal()
    #   except Exception as e:
    #       wx.MessageDialog(None, f"Could not write file: {e}", "Error",
    #               wx.OK | wx.ICON_ERROR | wx.STAY_ON_TOP).ShowModal()

    part.update()                                                                                              #Update part after all operations

    print("\n\n Completed\n\n")
