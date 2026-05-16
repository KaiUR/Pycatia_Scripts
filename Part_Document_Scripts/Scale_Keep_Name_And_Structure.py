'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Scale_Keep_Name_And_Structure.py
    Version:        1.0
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Scales all hybrid shapes in a geometric set while keeping names and structure.
    Author:         Kai-Uwe Rathjen
    Date:           16.05.26
    Description:    This script will ask the user to select a geometric set, a center point, and a scale
                    ratio. The script will recreate the full geometric set structure inside the current
                    in-work object, perform a scale on every hybrid shape recursively through all child
                    sets, and preserve the original names of all shapes and geometric sets.
    dependencies = [
                    "pycatia",
                    "wxPython",
                    ]
    requirements:   Python >= 3.10
                    pycatia
                    wxPython
                    Catia V5 running with an open part containing a geometric set and a point.
                    This script needs an open part document.
    -----------------------------------------------------------------------------------------------------------------------

    Change:

    -----------------------------------------------------------------------------------------------------------------------
'''

#Imports
from pycatia import catia
from pycatia.mec_mod_interfaces.part_document import PartDocument
from pycatia.mec_mod_interfaces.hybrid_body import HybridBody
from pycatia.mec_mod_interfaces.hybrid_shape import HybridShape
import wx
import ctypes
import pythoncom

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

def create_datum(hybrid_shape_factory, hybrid_shape, hybrid_body, name=None):
    geo_type = hybrid_shape_factory.get_geometrical_feature_type(hybrid_shape)                                    #Get geometry type

    if geo_type == 1:                                                                                             #Point
        datum = hybrid_shape_factory.add_new_point_datum(hybrid_shape)
        if name: datum.name = name
        hybrid_body.append_hybrid_shape(datum)
    elif geo_type == 2:                                                                                           #Curve
        datum = hybrid_shape_factory.add_new_curve_datum(hybrid_shape)
        if name: datum.name = name
        hybrid_body.append_hybrid_shape(datum)
    elif geo_type == 3:                                                                                           #Line
        datum = hybrid_shape_factory.add_new_line_datum(hybrid_shape)
        if name: datum.name = name
        hybrid_body.append_hybrid_shape(datum)
    elif geo_type == 4:                                                                                           #Circle
        datum = hybrid_shape_factory.add_new_circle_datum(hybrid_shape)
        if name: datum.name = name
        hybrid_body.append_hybrid_shape(datum)
    elif geo_type == 5:                                                                                           #Surface
        datum = hybrid_shape_factory.add_new_surface_datum(hybrid_shape)
        if name: datum.name = name
        hybrid_body.append_hybrid_shape(datum)
    else:
        print(f"  Warning: unsupported geometry type ({geo_type}) for '{name}' - skipped")
        return

    hybrid_shape_factory.delete_object_for_datum(hybrid_shape)                                                    #Remove original scale shape

def process_hybrid_body(source_hb, target_hb, part, hybrid_shape_factory, center_ref, ratio):
    hybrid_shapes = source_hb.hybrid_shapes                                                                       #Get all hybrid shapes in source set

    for index in range(hybrid_shapes.count):                                                                      #Loop through shapes
        shape = hybrid_shapes.item(index + 1)
        shape_name = shape.name
        shape_ref = part.create_reference_from_object(shape)

        scale_com = hybrid_shape_factory.com_object.AddNewScaling(                                                #Create scale via COM
                shape_ref.com_object,
                center_ref.com_object)
        scale_com.Ratio.Value = ratio                                                                              #Set ratio
        scale_com.Name = shape_name
        target_hb.com_object.AppendHybridShape(scale_com)
        part.update()

        scale = HybridShape(scale_com)                                                                             #Wrap for datum creation
        create_datum(hybrid_shape_factory, scale, target_hb, shape_name)

    for child_index in range(source_hb.hybrid_bodies.count):                                                      #Loop through child sets
        source_child_hb = HybridBody(source_hb.hybrid_bodies.item(child_index + 1).com_object)
        target_child_hb = HybridBody(target_hb.hybrid_bodies.add().com_object)
        target_child_hb.name = source_child_hb.name

        process_hybrid_body(source_child_hb, target_child_hb, part,                                              #Recurse
                hybrid_shape_factory, center_ref, ratio)

if __name__ == "__main__":
    caa = catia()
    active_doc = caa.active_document

    object_filter = ("HybridBody",)
    selectionSet = caa.active_document.selection
    status = selectionSet.select_element3(object_filter, "Select geometric set to scale", False, 2, False)
    if status != "Normal":
        print("You must select a geometric set")
        exit()

    selected_item = selectionSet.item(1)
    source_geo_set_name = selected_item.value.name

    if type(active_doc) is PartDocument:
        part = active_doc.part
        part_document: PartDocument = active_doc
    else:
        leaf_product = selected_item.com_object.LeafProduct
        part_document = PartDocument(leaf_product.ReferenceProduct.Parent)
        part = part_document.part

    hybrid_bodies = part.hybrid_bodies
    hybrid_shape_factory = part.hybrid_shape_factory

    source_hb = HybridBody(selected_item.value.com_object)

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
            ratio = float(dlg.GetValue())
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
    inwork_hb = None
    try:
        inwork_hb = HybridBody(in_work.com_object)
        inwork_hb.hybrid_shapes
    except Exception:
        inwork_hb = None
    if inwork_hb is None:
        try:
            inwork_hb = HybridBody(in_work.com_object.Parent)
            inwork_hb.hybrid_shapes
        except Exception:
            inwork_hb = None
    if inwork_hb is None:
        inwork_hb = hybrid_bodies.add()
        inwork_hb.name = "Scale_Keep_Name_And_Structure"

    try:                                                                                                          #Guard: source must not be the in-work object
        src_unk = source_hb.com_object._oleobj_.QueryInterface(pythoncom.IID_IUnknown)
        inw_unk = inwork_hb.com_object._oleobj_.QueryInterface(pythoncom.IID_IUnknown)
        same_object = (src_unk == inw_unk)
    except Exception:
        same_object = (source_hb.name == inwork_hb.name)
    if same_object:
        print("Error: The selected geometric set is the current in-work object. Please select a different geometric set or change the in-work object.")
        exit()

    output_hb = inwork_hb.hybrid_bodies.add()
    output_hb.name = source_geo_set_name

    print(f"\n Processing geometric set '{source_geo_set_name}'\n")

    process_hybrid_body(source_hb, output_hb, part, hybrid_shape_factory, center_ref, ratio)

    part.update()
    print(f"\n\n Completed\n\n")
