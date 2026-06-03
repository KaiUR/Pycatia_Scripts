'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Batch_Isolate_Geometric_Set.py
    Version:        1.2
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Isolate (make datum) every element inside a selected geometric set in one operation.
    Author:         Kai-Uwe Rathjen
    Date:           06.05.26
    Description:    This script will ask the user to select a geometric set. The script will then isolate every
                    hybrid shape inside the selected geometric set, replacing each element with a datum of the
                    same type and preserving the original name. Supports points, curves, lines, circles and
                    surfaces. Useful for delivering geometry or breaking parametric links in bulk.
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

'''
    This function creates a datum from a hybrid shape preserving its name, then removes the original.

    Inputs:
        hybrid_shape_factory    The hybrid shape factory for the part
        hybrid_shape            The hybrid shape to isolate
        hybrid_body             The geometric set to add the datum to
        name                    The name to give the new datum

    output:
        None
'''
def create_datum(hybrid_shape_factory, hybrid_shape, hybrid_body, name=None):
    geo_type = hybrid_shape_factory.get_geometrical_feature_type(hybrid_shape)                                  #Get geometry type

    if geo_type == 1:                                                                                           #Point
        datum = hybrid_shape_factory.add_new_point_datum(hybrid_shape)
        if name:
            datum.name = name
        hybrid_body.append_hybrid_shape(datum)
    elif geo_type == 2:                                                                                         #Curve
        datum = hybrid_shape_factory.add_new_curve_datum(hybrid_shape)
        if name:
            datum.name = name
        hybrid_body.append_hybrid_shape(datum)
    elif geo_type == 3:                                                                                         #Line
        datum = hybrid_shape_factory.add_new_line_datum(hybrid_shape)
        if name:
            datum.name = name
        hybrid_body.append_hybrid_shape(datum)
    elif geo_type == 4:                                                                                         #Circle
        datum = hybrid_shape_factory.add_new_circle_datum(hybrid_shape)
        if name:
            datum.name = name
        hybrid_body.append_hybrid_shape(datum)
    elif geo_type == 5:                                                                                         #Surface
        datum = hybrid_shape_factory.add_new_surface_datum(hybrid_shape)
        if name:
            datum.name = name
        hybrid_body.append_hybrid_shape(datum)
    else:                                                                                                       #Unknown type
        print(f"  Warning: unsupported geometry type ({geo_type}) for '{name}' - skipped")
        return

    hybrid_shape_factory.delete_object_for_datum(hybrid_shape)                                                  #Remove original construction shape

if __name__ == "__main__":
    #Anchoring relavent components
    caa = catia()                                                                                               #Catia application instance
    active_doc = caa.active_document                                                                            #Current Document

    object_filter = ("HybridBody",)                                                                             #Set user selection filter (Geometric Set)
    selectionSet = caa.active_document.selection                                                                #Create container for selection
    status = selectionSet.select_element3(object_filter, "Select geometric set to isolate", False, 2, False)    #Runs an interactive selection command, exhaustive version.
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

    target_hb = HybridBody(selected_item.value.com_object)                                                      #Get selected geometric set directly from selection

    hybrid_shapes = target_hb.hybrid_shapes                                                                     #Get all hybrid shapes in set

    if hybrid_shapes.count == 0:                                                                                #If no shapes
        print(f"Geometric set '{geo_set_name}' contains no hybrid shapes to isolate")
        exit()

    shape_count = hybrid_shapes.count                                                                           #Store count before modifying
    print(f"\n Isolating {shape_count} element(s) in '{geo_set_name}'\n")

    shape_names = []                                                                                            #Store names before loop as count changes during isolation
    shape_refs = []                                                                                             #Store shapes before loop
    for index in range(shape_count):                                                                            #Loop through all shapes
        shape_names.append(hybrid_shapes.item(index + 1).name)                                                  #Store name
        shape_refs.append(hybrid_shapes.item(index + 1))                                                        #Store shape reference

    for index in range(shape_count):                                                                            #Loop through stored shapes
        shape = shape_refs[index]                                                                               #Get shape
        name = shape_names[index]                                                                               #Get name
        print(f"  Isolating: {name}")
        create_datum(hybrid_shape_factory, shape, target_hb, name)                                              #Create datum and remove original

    part.update()                                                                                               #Update part once after all isolations
    print(f"\n\n Completed - {shape_count} element(s) isolated\n\n")
