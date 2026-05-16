'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Spline_Through_Points_In_Geometric_Set.py
    Version:        1.0
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Create a spline through all points in a selected geometric set.
    Author:         Kai-Uwe Rathjen
    Date:           16.05.26
    Description:    This script will ask the user to select a geometric set containing points. It will
                    collect all point-type hybrid shapes from the set (in tree order) and create a single
                    spline passing through them. The spline is added to the current in-work object.
                    Non-point shapes in the set are ignored. Useful as the second step after importing
                    points via Insert_Points_Catia or Insert_Points_Catia_With_Names.
    dependencies = [
                    "pycatia",
                    ]
    requirements:   Python >= 3.10
                    pycatia
                    Catia V5 running with an open part containing a geometric set of points.
                    This script needs an open part document.
    -----------------------------------------------------------------------------------------------------------------------

    Change:

    -----------------------------------------------------------------------------------------------------------------------
'''

#Imports
from pycatia import catia
from pycatia.mec_mod_interfaces.part_document import PartDocument
from pycatia.mec_mod_interfaces.hybrid_body import HybridBody

if __name__ == "__main__":
    caa = catia()
    active_doc = caa.active_document

    object_filter = ("HybridBody",)
    selectionSet = caa.active_document.selection
    status = selectionSet.select_element3(object_filter, "Select geometric set containing points", False, 2, False)
    if status != "Normal":
        print("You must select a geometric set")
        exit()

    selected_item = selectionSet.item(1)

    if type(active_doc) is PartDocument:
        part = active_doc.part
        part_document: PartDocument = active_doc
    else:
        leaf_product = selected_item.com_object.LeafProduct
        part_document = PartDocument(leaf_product.ReferenceProduct.Parent)
        part = part_document.part

    hybrid_bodies = part.hybrid_bodies
    hybrid_shape_factory = part.hybrid_shape_factory

    source_hb = HybridBody(selected_item.value.com_object)

    shapes = source_hb.hybrid_shapes
    point_refs = []

    for i in range(shapes.count):                                                                                  #Collect point references in tree order
        shape = shapes.item(i + 1)
        geo_type = hybrid_shape_factory.get_geometrical_feature_type(shape)
        if geo_type == 1:                                                                                          #Points only
            ref = part.create_reference_from_object(shape)
            point_refs.append(ref)

    if len(point_refs) < 2:
        print(f"At least 2 points are required. Found {len(point_refs)} point(s) in the selected set.")
        exit()

    print(f"\n Found {len(point_refs)} point(s) — creating spline...\n")

    in_work = part.in_work_object
    hb = None
    try:
        hb = HybridBody(in_work.com_object)
        hb.hybrid_shapes
    except Exception:
        hb = None
    if hb is None:
        try:
            hb = HybridBody(in_work.com_object.Parent)
            hb.hybrid_shapes
        except Exception:
            hb = None
    if hb is None:
        hb = hybrid_bodies.add()
        hb.name = "Spline_Through_Points"

    spline_com = hybrid_shape_factory.com_object.AddNewSpline()                                                   #Create spline via COM
    for ref in point_refs:
        spline_com.AddPoint(ref.com_object)                                                                       #Add each point to spline

    spline_name = f"Spline_{source_hb.name}"
    spline_com.Name = spline_name
    hb.com_object.AppendHybridShape(spline_com)
    part.update()

    print(f"\n\n Completed - created '{spline_name}' through {len(point_refs)} point(s)\n\n")
