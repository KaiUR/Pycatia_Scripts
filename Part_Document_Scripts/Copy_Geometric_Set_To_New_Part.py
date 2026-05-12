'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Copy_Geometric_Set_To_New_Part.py
    Version:        1.1
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Copy a selected geometric set and all its contents into a new blank CATPart.
    Author:         Kai-Uwe Rathjen
    Date:           06.05.26
    Description:    This script will ask the user to select a geometric set. The script will then copy all
                    hybrid shapes inside the selected geometric set into a new blank CATPart. The new part is
                    named after the selected geometric set. Useful for isolating geometry for delivery or
                    sharing a subset of a complex part.
    dependencies = [
                    "pycatia",
                    ]
    requirements:   Python >= 3.10
                    pycatia
                    Catia V5 running with an open part document containing a geometric set with hybrid shapes.
                    This script needs an open part document.
    -----------------------------------------------------------------------------------------------------------------------

    Change:         13.05.26 1.1: Replace name-based HybridBody lookup with direct COM reference.

    -----------------------------------------------------------------------------------------------------------------------
'''

#Imports
from pycatia import catia
from pycatia.mec_mod_interfaces.hybrid_body import HybridBody
from pycatia.mec_mod_interfaces.part_document import PartDocument

if __name__ == "__main__":
    #Anchoring relavent components
    caa = catia()                                                                                               #Catia application instance
    active_doc = caa.active_document                                                                            #Current Document

    object_filter = ("HybridBody",)                                                                             #Set user selection filter (Geometric Set)
    selectionSet = caa.active_document.selection                                                                #Create container for selection
    status = selectionSet.select_element3(object_filter, "Select geometric set to copy to new part", False, 2, False) #Runs an interactive selection command, exhaustive version.
    if status != "Normal":                                                                                      #Check if selection was succesful
        print("You must select a geometric set")
        exit()

    selected_item = selectionSet.item(1)                                                                        #Get selected item
    geo_set_name = selected_item.value.name                                                                     #Get name of selected geometric set

    if type(active_doc) is PartDocument:                                                                        #If document is part document
        part = active_doc.part
        part_document: PartDocument = active_doc
    else:                                                                                                       #Else get part from product structure
        leaf_product = selected_item.com_object.LeafProduct                                                     #Get leaf product
        part_document = PartDocument(leaf_product.ReferenceProduct.Parent)                                      #Get part document
        part = part_document.part                                                                               #Get new part object

    hybrid_bodies = part.hybrid_bodies                                                                          #Set off all top level geometric sets

    source_hb = HybridBody(selected_item.value.com_object)                                                      #Get selected geometric set directly from selection

    source_shapes = source_hb.hybrid_shapes                                                                     #Get all hybrid shapes in source set
    if source_shapes.count == 0:                                                                                #If no shapes
        print(f"Error: Geometric set '{geo_set_name}' contains no hybrid shapes")
        exit()

    print(f"\n Copying {source_shapes.count} shape(s) from '{geo_set_name}' to new part\n")

    source_selection = caa.active_document.selection                                                            #Get selection on source document
    source_selection.clear()                                                                                    #Clear selection

    for index in range(source_shapes.count):                                                                    #Loop through all shapes in source set
        source_selection.add(source_shapes.item(index + 1))                                                     #Add each shape to selection
        print(f"  Copying: {source_shapes.item(index + 1).name}")

    source_selection.copy()                                                                                     #Copy selection to clipboard

    new_part_document: PartDocument = caa.documents.add('Part')                                                 #Create new blank part document
    new_part_document.product.part_number = geo_set_name                                                        #Name the new part after the geometric set
    new_part = new_part_document.part                                                                           #Get new part

    new_hb = new_part.hybrid_bodies.add()                                                                       #Add a new geometric set to the new part
    new_hb.name = geo_set_name                                                                                  #Name the geometric set

    new_part.in_work_object = new_hb                                                                            #Set the new geometric set as in-work

    target_selection = new_part_document.selection                                                              #Get selection on new document
    target_selection.clear()                                                                                    #Clear selection
    target_selection.add(new_hb)                                                                                #Add new geometric set to selection
    target_selection.paste_special("CATPrtResultWithOutLink")                                                   #Paste as result without link (datum)

    new_part.update()                                                                                           #Update new part

    print(f"\n\n Completed - new part '{geo_set_name}' created\n\n")
