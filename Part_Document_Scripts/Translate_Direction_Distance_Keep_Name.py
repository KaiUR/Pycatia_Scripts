'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Translate_Direction_Distance_Keep_Name.py
    Version:        1.0
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
    
    Change:         
    
    -----------------------------------------------------------------------------------------------------------------------
'''

#Imports
from pycatia import catia
from pycatia.mec_mod_interfaces.part_document import PartDocument
import wx

def searchHybridBody(seachName, currentHybridBodies):
    try:                                                                                                        #Try at current level
        currentSearch = currentHybridBodies.item(seachName)                                                     #Check if we can find it
        if currentSearch is not None:                                                                           #If we found it
            return currentSearch                                                                                #Return found Geometric set
    except:
        pass                                                                                                    #If no found move to recursion

    for index in range(currentHybridBodies.count):                                                              #Loop through geometric sets of this level
        if currentHybridBodies.item(index+1).hybrid_bodies.count > 0:
            found = searchHybridBody(seachName, currentHybridBodies.item(index+1).hybrid_bodies)                #recursive call
        
            if found is not None:                                                                               #If found
                return found                                                                                     #Return found

    return None                                                                                                 #Return not found
    
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
    active_doc = caa.active_document                                                                            #Current Document
    documents = caa.documents                                                                                   #Collection of documents

    object_filter = ("AnyObject",)                                                                              #Set user selection filter (AnyObject)                             
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

    brep_core = ref_name.replace("Selection_", "").split(");AxisSystem")[0]                                     #Remove selection_ from string
    brep_name = f"{brep_core});WithPermanentBody;WithoutBuildError;WithSelectingFeatureSupport;MFBRepVersion_CXR29)"#Build bref string to create reference
    
    direction_ref = part.create_reference_from_b_rep_name(brep_name, selectionSet.item(1).value)                #Create reference from selected direction, works with face or line of axis system
    selected_direction_ref = hybrid_shape_factory.add_new_direction(direction_ref)                              #Create new direction object
    
    app = wx.App(None)
    distance = 0.0                                                                                              #Initilize distance to 0

    dlg = wx.TextEntryDialog(None, "Enter distance to translate:", "Enter Distance", "0.0", wx.OK | wx.CANCEL | wx.CENTRE | wx.STAY_ON_TOP)

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
    
    hb = searchHybridBody(part.in_work_object.name, hybrid_bodies)                                              #Look for the in work object geometric set
    if hb == None:                                                                                              #If not found
        hb = hybrid_bodies.add()                                                                                #Add new geometric set
        hb.name = "Axis_To_Axis_Keep_Name"                                                                      #Rename geometric set
    
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