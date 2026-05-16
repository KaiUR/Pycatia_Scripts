'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Scale_Keep_History.py
    Version:        1.0
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Scales hybrid shapes while keeping the names and parametric history.
    Author:         Kai-Uwe Rathjen
    Date:           16.05.26
    Description:    This script will ask the user to select hybrid shapes, a center point, and a scale
                    ratio. The script will scale each shape about the selected center point, use the same
                    name as the source shape, and leave the result as a live parametric feature rather
                    than converting it to a datum.
    dependencies = [
                    "pycatia",
                    "wxPython",
                    ]
    requirements:   Python >= 3.10
                    pycatia
                    wxPython
                    Catia V5 running with an open part containing hybrid shapes and a point.
                    This script needs an open part document.
    -----------------------------------------------------------------------------------------------------------------------

    Change:

    -----------------------------------------------------------------------------------------------------------------------
'''

#Imports
from pycatia import catia
from pycatia.mec_mod_interfaces.hybrid_body import HybridBody
from pycatia.mec_mod_interfaces.part_document import PartDocument
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

if __name__ == "__main__":
    caa = catia()                                                                                                  #Catia application instance
    active_doc = caa.active_document                                                                               #Current Document

    object_filter = ("HybridShape",)                                                                              #Set user selection filter
    selectionSet = caa.active_document.selection
    status = selectionSet.select_element3(object_filter, "Select hybrid shapes to scale", False, 2, False)        #Interactive selection
    if status != "Normal":
        print("You must select a hybrid shape")
        exit()

    selected_item = selectionSet.item(1)

    if type(active_doc) is PartDocument:
        part = active_doc.part
        part_document: PartDocument = active_doc
    else:
        leaf_product = selected_item.com_object.LeafProduct
        part_document = PartDocument(leaf_product.ReferenceProduct.Parent)
        part = part_document.part

    hybrid_bodies = part.hybrid_bodies
    hybrid_shape_factory = part.hybrid_shape_factory

    shapes_selected = [None] * selectionSet.count                                                                 #Store selected shape references
    shapes_selected_name = [None] * selectionSet.count
    shapes_count = selectionSet.count
    for index in range(selectionSet.count):
        shapes_selected[index] = selectionSet.item(index + 1).reference
        shapes_selected_name[index] = selectionSet.item(index + 1).value.name

    object_filter = ("AnyObject",)
    selectionSet.clear()
    status = selectionSet.select_element3(object_filter, "Select center point for scaling", False, 2, False)
    if status != "Normal":
        print("You must select a center point")
        exit()

    center_ref = selectionSet.item(1).reference                                                                   #Reference to center point

    app = wx.App(None)
    dlg = wx.TextEntryDialog(None, "Enter scale ratio (e.g. 2.0 = double, 0.5 = half):", "Enter Scale Ratio", "1.0",
            wx.OK | wx.CANCEL | wx.CENTRE | wx.STAY_ON_TOP)

    wx.CallAfter(_bring_to_front, dlg)
    if dlg.ShowModal() == wx.ID_OK:
        try:
            ratio = float(dlg.GetValue())                                                                         #Get ratio as float
            if ratio <= 0.0:
                print("Scale ratio must be greater than zero")
                exit()
        except ValueError:
            print("You must enter a valid number")
            exit()
    else:
        dlg.Destroy()
        print("You must enter a scale ratio")
        exit()

    dlg.Destroy()

    in_work = part.in_work_object
    hb = None
    try:
        hb = HybridBody(in_work.com_object)
        hb.hybrid_shapes
    except Exception:
        hb = None
    if hb is None:
        try:
            hb = HybridBody(in_work.com_object.Parent)
            hb.hybrid_shapes
        except Exception:
            hb = None
    if hb is None:
        hb = hybrid_bodies.add()
        hb.name = "Scale_Keep_History"

    for index in range(shapes_count):
        scale = hybrid_shape_factory.add_new_hybrid_scaling(
                shapes_selected[index],
                center_ref,
                ratio)
        scale.name = shapes_selected_name[index]
        hb.append_hybrid_shape(scale)
        part.update()

    part.update()
