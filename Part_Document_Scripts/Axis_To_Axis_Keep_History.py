'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Axis_To_Axis_Keep_History.py
    Version:        1.0
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Moves hybrid shapes from axis to axis while keeping the names and parametric history.
    Author:         Kai-Uwe Rathjen
    Date:           16.05.26
    Description:    This script will ask the user to select hybrid shapes and a ref axis and a target axis. Script
                    will move shapes from axis to axis, use the same name as source shape, and leave the result
                    as a live parametric feature rather than converting it to a datum.
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
from pycatia.mec_mod_interfaces.hybrid_body import HybridBody
from pycatia.mec_mod_interfaces.part_document import PartDocument

if __name__ == "__main__":
    caa = catia()                                                                                               #Catia application instance
    active_doc = caa.active_document                                                                            #Current Document

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
        leaf_product = selected_item.com_object.LeafProduct
        part_document = PartDocument(leaf_product.ReferenceProduct.Parent)
        part = part_document.part                                                                               #Get new part object

    hybrid_bodies = part.hybrid_bodies                                                                          #Set off all top level geometric sets
    hybrid_shape_factory = part.hybrid_shape_factory                                                            #GSD workbentch to create hybridshapes

    hybridshapes_selected = [None] * selectionSet.count                                                         #Create array to store hybridshapes
    hybridshapes_selected_name = [None] * selectionSet.count
    hybridshapes_selected_count = selectionSet.count                                                            #Store number of shapes
    for index in range(selectionSet.count):                                                                     #Loop through selection
        hybridshapes_selected[index] = selectionSet.item(index + 1).reference                                   #Store selected shapes as reference
        hybridshapes_selected_name[index] = selectionSet.item(index + 1).value.name                             #Store Names

    object_filter = ("AxisSystem",)                                                                              #Set user selection filter (AnyObject)
    selectionSet.clear()
    status = selectionSet.select_element3(object_filter,"Select reference axis system" , False , 2 , False)     #Runs an interactive selection command, exhaustive version.
    if status != "Normal":                                                                                      #Check if selection was succesful
        print("You must select a reference axis system")
        exit()

    selected_axis_system_ref = selectionSet.item(1).value                                                       #Store selected axis system
    selected_axis_system_name_ref = selectionSet.item(1).name                                                   #Store selected axis system name

    object_filter = ("AxisSystem",)                                                                              #Set user selection filter (AnyObject)
    selectionSet.clear()
    status = selectionSet.select_element3(object_filter,"Select target axis system" , False , 2 , False)        #Runs an interactive selection command, exhaustive version.
    if status != "Normal":                                                                                      #Check if selection was succesful
        print("You must select a reference axis system")
        exit()

    selected_axis_system_tar = selectionSet.item(1).value                                                       #Store selected axis system
    selected_axis_system_name_tar = selectionSet.item(1).name                                                   #Store selected axis system name

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
        hb.name = "Axis_To_Axis_Keep_History"                                                                   #Rename geometric set

    for index in range(hybridshapes_selected_count):                                                            #For each curve
        axis_to_axis = hybrid_shape_factory.add_new_axis_to_axis(
                hybridshapes_selected[index],
                part.create_reference_from_object(selected_axis_system_ref),
                part.create_reference_from_object(selected_axis_system_tar))                                    #Preform an axis to axis transformation
        axis_to_axis.name = hybridshapes_selected_name[index]
        hb.append_hybrid_shape(axis_to_axis)                                                                    #Add axix to axis result to geometric set

        part.update()

    part.update()
