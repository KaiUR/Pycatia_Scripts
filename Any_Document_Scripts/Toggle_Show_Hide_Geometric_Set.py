'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Toggle_Show_Hide_Geometric_Set.py
    Version:        1.2
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Toggle the visibility of the contents and children of a selected geometric set.
    Author:         Kai-Uwe Rathjen
    Date:           06.05.26
    Description:    This script will ask the user to select a geometric set. The script will then toggle the visibility
                    of all contents and children inside the selected set. The selected set itself is not affected.
                    If an item is currently visible it will be hidden, if it is hidden it will be shown.
    dependencies = [
                    "pycatia",
                    ]
    requirements:   Python >= 3.10
                    pycatia
                    Catia V5 running with an open part, product, or process document containing a geometric set.
                    This script needs an open part document, product document or process document.
    -----------------------------------------------------------------------------------------------------------------------

    Change:         06.05.26 1.1: Fixed child visibility - now iterates hybrid_shapes collection directly
                                  instead of using invalid selection search query.
                    09.05.26 1.2: Selected set is no longer toggled — only its contents and children are affected.

    -----------------------------------------------------------------------------------------------------------------------
'''

#Imports
from pycatia import catia
from pycatia.mec_mod_interfaces.part_document import PartDocument
from pycatia.mec_mod_interfaces.hybrid_body import HybridBody

'''
    This function recursively sets the visibility of all hybrid shapes in a geometric set and its children.

    Inputs:
        hybrid_body     The geometric set to process
        selection       The active document selection object

    output:
        None
'''
def toggle_visibility_recursive(hybrid_body, selection):
    hybrid_shapes = hybrid_body.hybrid_shapes                                                                   #Get all hybrid shapes in this set
    for index in range(hybrid_shapes.count):                                                                    #Loop through all shapes
        selection.clear()                                                                                       #Clear selection
        selection.add(hybrid_shapes.item(index + 1))                                                            #Add shape to selection
        current = selection.vis_properties.get_show()                                                           #Get current visibility state of this shape
        selection.vis_properties.set_show(1 if current == 0 else 0)                                             #Toggle visibility of shape

    for child_index in range(hybrid_body.hybrid_bodies.count):                                                  #Loop through child geometric sets
        child_hb = HybridBody(hybrid_body.hybrid_bodies.item(child_index + 1).com_object)                       #Get and cast child geometric set
        selection.clear()                                                                                       #Clear selection
        selection.add(child_hb)                                                                                 #Add child set to selection
        current = selection.vis_properties.get_show()                                                           #Get current visibility state of this child set
        selection.vis_properties.set_show(1 if current == 0 else 0)                                             #Toggle visibility of child set
        toggle_visibility_recursive(child_hb, selection)                                                        #Recurse into child set

if __name__ == "__main__":
    #Anchoring relavent components
    caa = catia()                                                                                               #Catia application instance
    active_doc = caa.active_document                                                                            #Current Document

    object_filter = ("HybridBody",)                                                                             #Set user selection filter (Geometric Set)
    selectionSet = caa.active_document.selection                                                                #Create container for selection
    status = selectionSet.select_element3(object_filter, "Select geometric set to toggle visibility", False, 2, False) #Runs an interactive selection command, exhaustive version.
    if status != "Normal":                                                                                      #Check if selection was succesful
        print("You must select a geometric set")
        exit()

    selected_item = selectionSet.item(1)                                                                        #Get selected item
    selected_hb = HybridBody(selected_item.value.com_object)                                                    #Cast selected item to HybridBody

    if type(active_doc) is PartDocument:                                                                        #If document is part document
        part_document: PartDocument = active_doc
        part = active_doc.part
    else:                                                                                                       #Else get part from product structure
        leaf_product = selected_item.com_object.LeafProduct                                                     #Get leaf product
        part_document = PartDocument(leaf_product.ReferenceProduct.Parent)                                      #Get part document
        part = part_document.part                                                                               #Get new part object

    vis_properties = selectionSet.vis_properties                                                                #Get visible properties of selected item
    current_show = vis_properties.get_show()                                                                    #Get current visibility state (0 = shown, 1 = hidden)

    if current_show == 0:                                                                                       #If set is currently visible, its contents will be hidden
        print(f"Hiding contents of geometric set: {selected_hb.name}")
    else:                                                                                                       #If set is currently hidden, its contents will be shown
        print(f"Showing contents of geometric set: {selected_hb.name}")

    toggle_visibility_recursive(selected_hb, selectionSet)                                                     #Recursively toggle visibility of all contents and children

    selectionSet.clear()                                                                                        #Clear selection
    print("Completed")
