'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Rotate_Three_Points_Keep_Name.py
    Version:        1.0
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Rotates hybrid shapes using three points definition while keeping the names.
    Author:         Kai-Uwe Rathjen
    Date:           12.05.26
    Description:    This script will ask the user to select hybrid shapes, a center point, a start point
                    and an end point. Script will rotate shapes and then use the same name as source shape.
    dependencies = [
                    "pycatia",
                    ]
    requirements:   Python >= 3.10
                    pycatia
                    Catia V5 running with an open part containing hybridshapes and three points.
                    This script needs an open part document.
    -----------------------------------------------------------------------------------------------------------------------

    Change:

    -----------------------------------------------------------------------------------------------------------------------
'''

#Imports
from pycatia import catia
from pycatia.mec_mod_interfaces.part_document import PartDocument

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

    if geo_type == 1:                                                                                           #Point
        datum = hybrid_shape_factory.add_new_point_datum(hybrid_shape)
        if name: datum.name = name
        hybrid_body.append_hybrid_shape(datum)
    elif geo_type == 2:                                                                                         #Curve
        datum = hybrid_shape_factory.add_new_curve_datum(hybrid_shape)
        if name: datum.name = name
        hybrid_body.append_hybrid_shape(datum)
    elif geo_type == 3:                                                                                         #Line
        datum = hybrid_shape_factory.add_new_line_datum(hybrid_shape)
        if name: datum.name = name
        hybrid_body.append_hybrid_shape(datum)
    elif geo_type == 4:                                                                                         #Circle
        datum = hybrid_shape_factory.add_new_circle_datum(hybrid_shape)
        if name: datum.name = name
        hybrid_body.append_hybrid_shape(datum)
    elif geo_type == 5:                                                                                         #Surface
        datum = hybrid_shape_factory.add_new_surface_datum(hybrid_shape)
        if name: datum.name = name
        hybrid_body.append_hybrid_shape(datum)

    hybrid_shape_factory.delete_object_for_datum(hybrid_shape)

if __name__ == "__main__":
    caa = catia()                                                                                               #Catia application instance
    active_doc = caa.active_document                                                                            #Current Document

    object_filter = ("HybridShape",)                                                                           #Set user selection filter (HybridShape)
    selectionSet = caa.active_document.selection                                                               #Create container for selection
    status = selectionSet.select_element3(object_filter, "Select Hybridshapes to rotate", False, 2, False)    #Runs an interactive selection command, exhaustive version.
    if status != "Normal":                                                                                      #Check if selection was succesful
        print("You must select a hybridshape")
        exit()

    selected_item = selectionSet.item(1)

    if type(active_doc) is PartDocument:
        part = active_doc.part                                                                                  #If document is part document
        part_document : PartDocument = active_doc
    else:                                                                                                       #Else get part from product structure
        leaf_product = selected_item.com_object.LeafProduct
        part_document = PartDocument(leaf_product.ReferenceProduct.Parent)
        part = part_document.part                                                                               #Get new part object

    hybrid_bodies = part.hybrid_bodies                                                                         #Set off all top level geometric sets
    hybrid_shape_factory = part.hybrid_shape_factory                                                           #GSD workbench to create hybridshapes

    hybridshapes_selected = [None] * selectionSet.count                                                        #Create array to store hybridshapes
    hybridshapes_selected_name = [None] * selectionSet.count
    hybridshapes_selected_count = selectionSet.count                                                           #Store number of shapes
    for index in range(selectionSet.count):                                                                    #Loop through selection
        hybridshapes_selected[index] = selectionSet.item(index + 1).reference                                  #Store selected shapes as reference
        hybridshapes_selected_name[index] = selectionSet.item(index + 1).value.name                            #Store Names

    object_filter = ("AnyObject",)                                                                             #Set user selection filter (AnyObject)
    selectionSet.clear()
    status = selectionSet.select_element3(object_filter, "Select center point", False, 2, False)               #Runs an interactive selection command, exhaustive version.
    if status != "Normal":                                                                                      #Check if selection was succesful
        print("You must select a center point")
        exit()

    center_ref = part.create_reference_from_object(selectionSet.item(1).value)                                 #Create reference to center point

    object_filter = ("AnyObject",)                                                                             #Set user selection filter (AnyObject)
    selectionSet.clear()
    status = selectionSet.select_element3(object_filter, "Select start point", False, 2, False)                #Runs an interactive selection command, exhaustive version.
    if status != "Normal":                                                                                      #Check if selection was succesful
        print("You must select a start point")
        exit()

    start_ref = part.create_reference_from_object(selectionSet.item(1).value)                                  #Create reference to start point

    object_filter = ("AnyObject",)                                                                             #Set user selection filter (AnyObject)
    selectionSet.clear()
    status = selectionSet.select_element3(object_filter, "Select end point", False, 2, False)                  #Runs an interactive selection command, exhaustive version.
    if status != "Normal":                                                                                      #Check if selection was succesful
        print("You must select an end point")
        exit()

    end_ref = part.create_reference_from_object(selectionSet.item(1).value)                                    #Create reference to end point

    hb = searchHybridBody(part.in_work_object.name, hybrid_bodies)                                            #Look for the in work object geometric set
    if hb == None:                                                                                             #If not found
        hb = hybrid_bodies.add()                                                                               #Add new geometric set
        hb.name = "Rotate_Three_Points_Keep_Name"                                                              #Rename geometric set

    for index in range(hybridshapes_selected_count):                                                           #For each hybridshape
        rotate = hybrid_shape_factory.add_new_empty_rotate()                                                   #Create new rotate
        rotate.elem_to_rotate = hybridshapes_selected[index]                                                   #Add element to rotate
        rotate.vector_type = 1                                                                                 #Set to three points
        rotate.first_point = center_ref                                                                        #Add center point
        rotate.second_point = start_ref                                                                        #Add start point
        rotate.third_point = end_ref                                                                           #Add end point
        rotate.volume_result = False                                                                           #Disable volume result
        rotate.name = hybridshapes_selected_name[index]                                                        #Set name
        hb.append_hybrid_shape(rotate)                                                                         #Add result to geometric set

        part.update()

        create_datum(hybrid_shape_factory, rotate, hb, hybridshapes_selected_name[index])                      #Create datum

    part.update()
