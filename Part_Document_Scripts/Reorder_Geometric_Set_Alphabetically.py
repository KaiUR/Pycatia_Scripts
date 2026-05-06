'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Reorder_Geometric_Set_Alphabetically.py
    Version:        1.2
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Sort all elements inside a selected geometric set alphabetically by name.
    Author:         Kai-Uwe Rathjen
    Date:           06.05.26
    Description:    This script will ask the user to select a geometric set. The script will then sort all
                    hybrid shapes inside the selected geometric set alphabetically by name. Each shape is
                    recreated as a datum in sorted order and the original is removed. Child geometric sets
                    are not reordered. Useful for tidying large geometric sets that have grown messy over time.
    dependencies = [
                    "pycatia",
                    ]
    requirements:   Python >= 3.10
                    pycatia
                    Catia V5 running wtih an open part document containing a geometric set.
                    This script needs an open part document.
    -----------------------------------------------------------------------------------------------------------------------

    Change:         06.05.26 1.1: Attempted cut/paste approach - unreliable through API.
                    06.05.26 1.2: Replaced with datum recreation approach - creates sorted datums
                                  then removes originals, consistent with other scripts in collection.

    -----------------------------------------------------------------------------------------------------------------------
'''

#Imports
from pycatia import catia
from pycatia.mec_mod_interfaces.part_document import PartDocument

'''
    This function searches for a hybrid body by name and return is.

    Inputs:
        searchName              The name of the geometric set that is being searched for.
        currentHybridBodies     The current collection of geometric sets

    output:
        The geometric set that is found, or None if not found
'''
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

'''
    This function creates a datum from a hybrid shape preserving its name, then removes the original.

    Inputs:
        hybrid_shape_factory    The hybrid shape factory for the part
        hybrid_shape            The hybrid shape to create a datum from
        hybrid_body             The geometric set to add the datum to
        name                    The name to give the new datum

    output:
        None
'''
def create_datum(hybrid_shape_factory, hybrid_shape, hybrid_body, name=None):
    geo_type = hybrid_shape_factory.get_geometrical_feature_type(hybrid_shape)                                  #Get geometry type

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
    else:                                                                                                       #Unknown type
        print(f"  Warning: unsupported geometry type ({geo_type}) for '{name}' - skipped")
        return

    hybrid_shape_factory.delete_object_for_datum(hybrid_shape)                                                  #Remove original shape

if __name__ == "__main__":
    #Anchoring relavent components
    caa = catia()                                                                                               #Catia application instance
    active_doc = caa.active_document                                                                            #Current Document

    object_filter = ("HybridBody",)                                                                             #Set user selection filter (Geometric Set)
    selectionSet = caa.active_document.selection                                                                #Create container for selection
    status = selectionSet.select_element3(object_filter, "Select geometric set to sort alphabetically", False, 2, False) #Runs an interactive selection command, exhaustive version.
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
    hybrid_shape_factory = part.hybrid_shape_factory                                                            #GSD workbench to create hybridshapes

    target_hb = searchHybridBody(geo_set_name, hybrid_bodies)                                                   #Find the selected geometric set
    if target_hb is None:                                                                                       #If not found
        print(f"Error: Could not find geometric set '{geo_set_name}'")
        exit()

    hybrid_shapes = target_hb.hybrid_shapes                                                                     #Get all hybrid shapes in set

    if hybrid_shapes.count == 0:                                                                                #If no shapes
        print(f"Geometric set '{geo_set_name}' contains no hybrid shapes to sort")
        exit()

    shape_count = hybrid_shapes.count                                                                           #Store count before modifying
    print(f"\n Sorting {shape_count} element(s) in '{geo_set_name}' alphabetically\n")

    shape_names = []                                                                                            #Store names before loop as collection changes during recreation
    shape_refs = []                                                                                             #Store shape references before loop
    for index in range(shape_count):                                                                            #Loop through all shapes
        shape_names.append(hybrid_shapes.item(index + 1).name)                                                  #Store name
        shape_refs.append(hybrid_shapes.item(index + 1))                                                        #Store shape reference

    sorted_pairs = sorted(zip(shape_names, shape_refs), key=lambda p: p[0].lower())                            #Sort (name, ref) pairs alphabetically by name, case-insensitive

    for name, shape in sorted_pairs:                                                                            #Loop through shapes in sorted order
        print(f"  {name}")
        create_datum(hybrid_shape_factory, shape, target_hb, name)                                              #Create datum at end of set and remove original

    part.update()                                                                                               #Update part
    print(f"\n\n Completed - '{geo_set_name}' sorted alphabetically\n\n")
