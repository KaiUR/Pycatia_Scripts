'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Translate_Direction_Distance_Keep_Name.py
    Version:        1.1
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Moves hybrid shapes with translate while keeping the names.
    Author:         Kai-Uwe Rathjen
    Date:           23.04.26
    Description:    This script will ask the user to select hybrid shapes, a direction and a distance. Script
                    will translate shapes and then use the same name as source shape.
    dependencies = [
                    "pycatia",
                    "wxPython",
                    ]
    requirements:   Python >= 3.10
                    pycatia
                    Catia V5 running wtih an open part containing hybridshapes and two axis systems.
                    This script needs an open part document.
    -----------------------------------------------------------------------------------------------------------------------
    
    Change:         12.05.26 1.1: Dialog raised to foreground of CATIA window.

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

def create_datum(hybrid_shape_factory, hybrid_shape, hybrid_body, name=None):
    geo_type = hybrid_shape_factory.get_geometrical_feature_type(hybrid_shape)
    
    if geo_type == 1:
        datum_point = hybrid_shape_factory.add_new_point_datum(hybrid_shape)
        if name: datum_point.name = name
        hybrid_body.append_hybrid_shape(datum_point)
    elif geo_type == 2:
        datum_curve = hybrid_shape_factory.add_new_curve_datum(hybrid_shape)
        if name: datum_curve.name = name
        hybrid_body.append_hybrid_shape(datum_curve)
    elif geo_type == 3:
        datum_line = hybrid_shape_factory.add_new_line_datum(hybrid_shape)
        if name: datum_line.name = name
        hybrid_body.append_hybrid_shape(datum_line)
    elif geo_type == 4:
        datum_circle = hybrid_shape_factory.add_new_circle_datum(hybrid_shape)
        if name: datum_circle.name = name
        hybrid_body.append_hybrid_shape(datum_circle)
    elif geo_type == 5:
        datum_surface = hybrid_shape_factory.add_new_surface_datum(hybrid_shape)
        if name: datum_surface.name = name
        hybrid_body.append_hybrid_shape(datum_surface)
    
    hybrid_shape_factory.delete_object_for_datum(hybrid_shape)

if __name__ == "__main__":
    caa = catia()                                                                                               #Catia application instance
    active_doc = caa.active_document                                                                            #Current Document                                                                                #Collection of documents

    object_filter = ("HybridShape",)                                                                            #Set user selection filter (AnyObject)                             
    selectionSet = caa.active_document.selection                                                                #Create container for selection
    status = selectionSet.select_element3(object_filter,"Select Hybridshapes to move axis to axis" , False , 2 , False)          #Runs an interactive selection command, exhaustive version. 
    if status != "Normal":                                                                                      #Check if selection was succesful
        print("You must select a hybridshape")
        exit()
        
    selected_item = selectionSet.item(1) 

    if type(active_doc) is PartDocument:
        part = active_doc.part                                                                                  #If document is part document
        part_document : PartDocument = active_doc
    else:                                                                                                       #Else get part from product structure
        # We are in a Product or Process; find the Part via the selection
        # We use .com_object to access the LeafProduct property
        leaf_product = selected_item.com_object.LeafProduct
        part_document = PartDocument(leaf_product.ReferenceProduct.Parent)
        # Navigation: LeafProduct -> ReferenceProduct -> Parent (PartDocument) -> Part
        part = part_document.part                                                                               #Get new part object

    hybrid_bodies = part.hybrid_bodies                                                                          #Set off all top level geometric sets
    hybrid_shape_factory = part.hybrid_shape_factory                                                            #GSD workbentch to create hybridshapes
    
    hybridshapes_selected = [None] * selectionSet.count                                                         #Create array to store hybridshapes
    hybridshapes_selected_name = [None] * selectionSet.count 
    hybridshapes_selected_count = selectionSet.count                                                            #Store number of shapes
    for index in range(selectionSet.count):                                                                     #Loop through selection
        hybridshapes_selected[index] = selectionSet.item(index + 1).reference                                   #Store selected shapes as reference
        hybridshapes_selected_name[index] = selectionSet.item(index + 1).value.name                             #Store Names
        
    object_filter = ("AnyObject",)                                                                              #Set user selection filter (AnyObject)                             
    selectionSet.clear()
    status = selectionSet.select_element3(object_filter,"Select a Direction" , False , 2 , False)               #Runs an interactive selection command, exhaustive version. 
    if status != "Normal":                                                                                      #Check if selection was succesful
        print("You must select a direction")
        exit()

    #Create new direction using brep
    ref_name = selectionSet.item(1).reference.name                                                              #Get Reference name

    try:
        brep_core = ref_name.replace("Selection_", "").split(");AxisSystem")[0]                                     #Remove selection_ from string
        brep_name = f"{brep_core});WithPermanentBody;WithoutBuildError;WithSelectingFeatureSupport;MFBRepVersion_CXR29)"#Build bref string to create reference
        
        direction_ref = part.create_reference_from_b_rep_name(brep_name, selectionSet.item(1).value)                #Create reference from selected direction, works with face or line of axis system
        selected_direction_ref = hybrid_shape_factory.add_new_direction(direction_ref)                              #Create new direction object
    except:
        print("You must select a face or line of an axis system as direction")
        exit()       
    
    app = wx.App(None)
    distance = 0.0                                                                                              #Initilize distance to 0

    dlg = wx.TextEntryDialog(None, "Enter distance to translate:", "Enter Distance", "0.0", wx.OK | wx.CANCEL | wx.CENTRE | wx.STAY_ON_TOP)
    wx.CallAfter(_bring_to_front, dlg)
    if dlg.ShowModal() == wx.ID_OK:
        try:
            distance = float(dlg.GetValue())                                                                    #Get distance as float
        except ValueError:
            print("You must enter a valid number")
            exit()
    else:
        dlg.Destroy()
        print("You must enter a distance")
        exit()

    dlg.Destroy()
    
    in_work = part.in_work_object                                                                               #Get in work object
    hb = None
    try:
        hb = HybridBody(in_work.com_object)                                                                     #Try to use in_work_object directly as a HybridBody
        hb.hybrid_shapes                                                                                        #Validate it is a HybridBody
    except Exception:
        hb = None
    if hb is None:                                                                                              #If in_work_object is not a HybridBody (e.g. a feature)
        try:
            hb = HybridBody(in_work.com_object.Parent)                                                          #Try parent (the containing GS)
            hb.hybrid_shapes                                                                                    #Validate it is a HybridBody
        except Exception:
            hb = None
    if hb is None:                                                                                              #If still not found, create new GS
        hb = hybrid_bodies.add()                                                                                #Add new geometric set
        hb.name = "Translate_Keep_Name"                                                                         #Rename geometric set
    
    for index in range(hybridshapes_selected_count):                                                            #For each hybridshape
        transform = hybrid_shape_factory.add_new_empty_translate()                                              #Create new translate
        transform.elem_to_translate = hybridshapes_selected[index]                                              #Add element to translate
        transform.vector_type = 0                                                                               #Set to direction, distance
        transform.direction = selected_direction_ref                                                            #Add direction
        transform.distance_value = distance                                                                     #Add distance
        transform.volume_result = False                                                                         #Disable volume result
        transform.name = hybridshapes_selected_name[index]                                                      #Set name
        hb.append_hybrid_shape(transform)                                                                       #Add result to geometric set
        
        part.update()
        
        create_datum(hybrid_shape_factory, transform, hb, hybridshapes_selected_name[index])                    #Create datum
        
    part.update()