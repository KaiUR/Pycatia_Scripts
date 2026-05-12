'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Axis_To_Axis_Keep_Name_And_Structure.py
    Version:        1.1
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Moves all hybrid shapes in a geometric set from axis to axis while keeping names and structure.
    Author:         Kai-Uwe Rathjen
    Date:           06.05.26
    Description:    This script will ask the user to select a geometric set, a reference axis and a target axis.
                    The script will recreate the full geometric set structure inside the current in-work object,
                    perform an axis-to-axis transformation on every hybrid shape recursively through all child
                    sets, and preserve the original names of all shapes and geometric sets.
    dependencies = [
                    "pycatia",
                    ]
    requirements:   Python >= 3.10
                    pycatia
                    Catia V5 running wtih an open part containing a geometric set and two axis systems.
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

    hybrid_shape_factory.delete_object_for_datum(hybrid_shape)                                                  #Remove original axis to axis shape

'''
    This function recursively processes a source geometric set, recreating its structure in the target
    geometric set and performing an axis-to-axis transformation on every hybrid shape.

    Inputs:
        source_hb               The source geometric set to process
        target_hb               The target geometric set to recreate the structure in
        part                    The active part
        hybrid_shape_factory    The hybrid shape factory for the part
        ref_axis_ref            Reference to the reference axis system
        tar_axis_ref            Reference to the target axis system

    output:
        None
'''
def process_hybrid_body(source_hb, target_hb, part, hybrid_shape_factory, ref_axis_ref, tar_axis_ref):
    hybrid_shapes = source_hb.hybrid_shapes                                                                     #Get all hybrid shapes in source set

    for index in range(hybrid_shapes.count):                                                                    #Loop through all shapes in source set
        shape = hybrid_shapes.item(index + 1)                                                                   #Get shape
        shape_name = shape.name                                                                                  #Store shape name
        shape_ref = part.create_reference_from_object(shape)                                                    #Create reference to shape

        axis_to_axis = hybrid_shape_factory.add_new_axis_to_axis(                                               #Perform axis to axis transformation
                shape_ref,
                ref_axis_ref,
                tar_axis_ref)
        axis_to_axis.name = shape_name                                                                          #Set name to match source shape
        target_hb.append_hybrid_shape(axis_to_axis)                                                             #Add to target geometric set
        part.update()                                                                                           #Update part

        create_datum(hybrid_shape_factory, axis_to_axis, target_hb, shape_name)                                 #Convert to datum preserving name

    for child_index in range(source_hb.hybrid_bodies.count):                                                    #Loop through child geometric sets in source
        source_child_hb = source_hb.hybrid_bodies.item(child_index + 1)                                        #Get source child geometric set

        target_child_hb = target_hb.hybrid_bodies.add()                                                        #Create new child geometric set in target
        target_child_hb.name = source_child_hb.name                                                            #Name to match source child set

        process_hybrid_body(source_child_hb, target_child_hb, part,                                            #Recurse into child set
                hybrid_shape_factory, ref_axis_ref, tar_axis_ref)

if __name__ == "__main__":
    #Anchoring relavent components
    caa = catia()                                                                                               #Catia application instance
    active_doc = caa.active_document                                                                            #Current Document

    object_filter = ("HybridBody",)                                                                             #Set user selection filter (Geometric Set)
    selectionSet = caa.active_document.selection                                                                #Create container for selection
    status = selectionSet.select_element3(object_filter, "Select geometric set to move axis to axis", False, 2, False) #Runs an interactive selection command, exhaustive version.
    if status != "Normal":                                                                                      #Check if selection was succesful
        print("You must select a geometric set")
        exit()

    selected_item = selectionSet.item(1)                                                                        #Get selected item
    source_geo_set_name = selected_item.value.name                                                              #Store source geometric set name

    if type(active_doc) is PartDocument:                                                                        #If document is part document
        part = active_doc.part
        part_document: PartDocument = active_doc
    else:                                                                                                       #Else get part from product structure
        leaf_product = selected_item.com_object.LeafProduct                                                     #Get leaf product
        part_document = PartDocument(leaf_product.ReferenceProduct.Parent)                                      #Get part document
        part = part_document.part                                                                               #Get new part object

    hybrid_bodies = part.hybrid_bodies                                                                          #Set off all top level geometric sets
    hybrid_shape_factory = part.hybrid_shape_factory                                                            #GSD workbench to create hybridshapes

    source_hb = HybridBody(selected_item.value.com_object)                                                      #Get source geometric set directly from selection

    object_filter = ("AxisSystem",)                                                                             #Set user selection filter (Axis System)
    selectionSet.clear()
    status = selectionSet.select_element3(object_filter, "Select reference axis system", False, 2, False)       #Runs an interactive selection command, exhaustive version.
    if status != "Normal":                                                                                      #Check if selection was succesful
        print("You must select a reference axis system")
        exit()

    ref_axis_value = selectionSet.item(1).value                                                                 #Store reference axis system
    ref_axis_ref = part.create_reference_from_object(ref_axis_value)                                            #Create reference to reference axis

    object_filter = ("AxisSystem",)                                                                             #Set user selection filter (Axis System)
    selectionSet.clear()
    status = selectionSet.select_element3(object_filter, "Select target axis system", False, 2, False)          #Runs an interactive selection command, exhaustive version.
    if status != "Normal":                                                                                      #Check if selection was succesful
        print("You must select a target axis system")
        exit()

    tar_axis_value = selectionSet.item(1).value                                                                 #Store target axis system
    tar_axis_ref = part.create_reference_from_object(tar_axis_value)                                            #Create reference to target axis

    in_work = part.in_work_object                                                                               #Get in work object
    inwork_hb = None
    try:
        inwork_hb = HybridBody(in_work.com_object)                                                             #Try to use in_work_object directly as a HybridBody
        inwork_hb.hybrid_shapes                                                                                 #Validate it is a HybridBody
    except Exception:
        inwork_hb = None
    if inwork_hb is None:                                                                                       #If in_work_object is not a HybridBody (e.g. a feature)
        try:
            inwork_hb = HybridBody(in_work.com_object.Parent)                                                  #Try parent (the containing GS)
            inwork_hb.hybrid_shapes                                                                             #Validate it is a HybridBody
        except Exception:
            inwork_hb = None
    if inwork_hb is None:                                                                                       #If still not found, create new GS
        inwork_hb = hybrid_bodies.add()                                                                         #Add new geometric set
        inwork_hb.name = "Axis_To_Axis_Keep_Name_And_Structure"                                                 #Rename geometric set

    output_hb = inwork_hb.hybrid_bodies.add()                                                                   #Create new child geometric set inside in-work object
    output_hb.name = source_geo_set_name                                                                        #Name to match source geometric set

    print(f"\n Processing geometric set '{source_geo_set_name}'\n")

    process_hybrid_body(source_hb, output_hb, part,                                                            #Recursively process source geometric set
            hybrid_shape_factory, ref_axis_ref, tar_axis_ref)

    part.update()                                                                                               #Final update
    print(f"\n\n Completed\n\n")
