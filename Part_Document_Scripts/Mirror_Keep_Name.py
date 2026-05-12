'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Mirror_Keep_Name.py
    Version:        1.1
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Mirrors hybrid shapes while keeping the names.
    Author:         Kai-Uwe Rathjen
    Date:           12.05.26
    Description:    This script will ask the user to select hybrid shapes and a mirror plane. Script
                    will mirror shapes and then use the same name as source shape.
    dependencies = [
                    "pycatia",
                    ]
    requirements:   Python >= 3.10
                    pycatia
                    Catia V5 running with an open part containing hybridshapes and a plane.
                    This script needs an open part document.
    -----------------------------------------------------------------------------------------------------------------------

    Change:         13.05.26 1.1: Replace name-based HybridBody lookup with direct COM reference.

    -----------------------------------------------------------------------------------------------------------------------
'''

#Imports
from pycatia import catia
from pycatia.mec_mod_interfaces.hybrid_body import HybridBody
from pycatia.mec_mod_interfaces.part_document import PartDocument

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
    status = selectionSet.select_element3(object_filter, "Select Hybridshapes to mirror", False, 2, False)    #Runs an interactive selection command, exhaustive version.
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
    status = selectionSet.select_element3(object_filter, "Select mirror plane", False, 2, False)               #Runs an interactive selection command, exhaustive version.
    if status != "Normal":                                                                                      #Check if selection was succesful
        print("You must select a mirror plane")
        exit()

    #Create mirror plane reference using brep
    ref_name = selectionSet.item(1).reference.name                                                             #Get Reference name

    try:
        brep_core = ref_name.replace("Selection_", "").split(");AxisSystem")[0]                                #Remove selection_ from string
        brep_name = f"{brep_core});WithPermanentBody;WithoutBuildError;WithSelectingFeatureSupport;MFBRepVersion_CXR29)" #Build brep string to create reference
        mirror_ref = part.create_reference_from_b_rep_name(brep_name, selectionSet.item(1).value)             #Create reference from selected plane, works with face of axis system
    except:
        print("You must select a face of an axis system as mirror plane")
        exit()

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
        hb.name = "Mirror_Keep_Name"                                                                            #Rename geometric set

    for index in range(hybridshapes_selected_count):                                                           #For each hybridshape
        symmetry = hybrid_shape_factory.add_new_symmetry(hybridshapes_selected[index], mirror_ref)            #Create mirror (symmetry)
        symmetry.name = hybridshapes_selected_name[index]                                                      #Set name
        hb.append_hybrid_shape(symmetry)                                                                       #Add result to geometric set

        part.update()

        create_datum(hybrid_shape_factory, symmetry, hb, hybridshapes_selected_name[index])                   #Create datum

    part.update()
