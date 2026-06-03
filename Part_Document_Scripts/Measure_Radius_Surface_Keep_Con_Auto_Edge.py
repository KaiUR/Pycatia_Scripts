'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Measure_Radius_Surface_Keep_Con_Auto_Edge.py
    Version:        1.3
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Measures the radius of all border edges of a selected surface face.
    Author:         Kai-Uwe Rathjen
    Date:           18.05.26
    Description:    This script asks the user to select a surface face. It automatically loops over all
                    border edges, constructs a plane normal to each edge at its midpoint, intersects that
                    plane with the surface, places three points on the intersection curve, and fits a
                    3-point circle to measure the radius. Results for all edges are shown in one message
                    box. Curve construction geometry (CURVE CON sets) is deleted; measurement sets are
                    kept nested under one parent geometric set.
    dependencies = [
                    "pycatia",
                    ]
    requirements:   Python >= 3.10
                    pycatia
                    Catia V5 running with an open part containing a surface to measure.
                    This script needs an open part document.
    -----------------------------------------------------------------------------------------------------------------------

    Change:         18.05.26
                    Fix collinear check: normalise cross product by vector magnitudes so the test is scale-independent.

                    18.05.26
                    Replace extremum-anchor point placement with add_new_point_on_curve_from_percent — fixes points
                    collapsing to one location on edges where the extremum landed at the curve end.

                    31.05.26
                    Remove unused coords_relative_to_axis function.

    -----------------------------------------------------------------------------------------------------------------------
'''

#Imports
from pycatia import catia
from pycatia.hybrid_shape_interfaces.hybrid_shape_extract import HybridShapeExtract
from pycatia.hybrid_shape_interfaces.hybrid_shape_point_on_curve import HybridShapePointOnCurve
from pycatia.mec_mod_interfaces.part_document import PartDocument
from pycatia.mec_mod_interfaces.part import Part
import time
import re
'''
    This function will return a noralized vector

    Inputs:
        vec     The vector to normalize

    output:
        Normalized vector as vector
'''
def normalize_vector(vec):
    #Get magnitude
    magnitude = (vec[0] ** 2 + vec[1] ** 2 + vec[2] ** 2) ** 0.5

    #Normalize
    if magnitude != 0:
        x = vec[0] / magnitude
        y = vec[1] / magnitude
        z = vec[2] / magnitude

        return x, y, z

'''
    This function will return the dot product of two vectors

    Inputs:
        vec1    First vector
        vec2    Second vector

    output:
        Dot product of two vectors
'''
def dot_product(vec1, vec2):
    #return dot product
    return vec1[0] * vec2[0] + vec1[1] * vec2[1] + vec1[2] * vec2[2]

'''
    This function will return the cross product of two vectors

    Inputs:
        vec1    First vector
        vec2    Second vector

    output:
        Cross product of two vectors
'''
def cross_product(a, b):
    # a x b = [ay*bz - az*by, az*bx - ax*bz, ax*by - ay*bx]
    return [
        a[1]*b[2] - a[2]*b[1],
        a[2]*b[0] - a[0]*b[2],
        a[0]*b[1] - a[1]*b[0]
    ]

"""
    Check if three 2D points are collinear using the cross product ,ethod

    Args:
        p1, p2, p3: Tuples or lists representing the points, e.g., (x1, y1, z1).

    Returns:
        True if the points are collinear, False otherwise.
"""
def are_collinear(point_a, point_b, point_c):

    vectorAB = point_b[0] - point_a[0], point_b[1] - point_a[1], point_b[2] - point_a[2]
    vectorAC = point_c[0] - point_a[0], point_c[1] - point_a[1], point_c[2] - point_a[2]

    cross_poduct_vectors = cross_product(vectorAB, vectorAC)

    cross_mag_sq = cross_poduct_vectors[0]**2 + cross_poduct_vectors[1]**2 + cross_poduct_vectors[2]**2
    ab_mag_sq = vectorAB[0]**2 + vectorAB[1]**2 + vectorAB[2]**2
    ac_mag_sq = vectorAC[0]**2 + vectorAC[1]**2 + vectorAC[2]**2

    if ab_mag_sq == 0 or ac_mag_sq == 0:
        return True

    return cross_mag_sq / (ab_mag_sq * ac_mag_sq) < 1e-6

if __name__ == "__main__":
    #Anchoring relavent components
    caa = catia()                                                                                               #Catia
    active_doc = caa.active_document                                                                            #Current Document

    object_filter = ("Face",)                                                                                   #Set user selection filter(Curves)
    selectionSet = caa.active_document.selection                                                                #Create container for selection
    status = selectionSet.select_element3(
            object_filter,"Select a Surface to measure" , False , 2 , False)                                    #Runs an interactive selection command, exhaustive version.
    if status != "Normal":                                                                                      #Check if selection was succesful
        print("You must select a surface")
        exit()

    selected_item = selectionSet.item(1)                                                                        #Selected element

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

    spa_workbench = active_doc.spa_workbench()

    hybrid_bodies = part.hybrid_bodies                                                                          #Set off all top level geometric sets
    hybrid_shape_factory = part.hybrid_shape_factory                                                            #GSD workbentch to create hybridshapes

    surface_ref = selectionSet.item(1).reference
    surface_value = selectionSet.item(1).value
    surface_ref_name = selectionSet.item(1).reference.name

    pattern = r"Brp:\(GSMBiDim\.(\d+);(\d+)\)"
    match = re.search(pattern, surface_ref_name)
    gsm_id = match.group(1)
    total_edges = int(match.group(2))

    results = []

    hb_parent = hybrid_bodies.add()                                                                            #Parent geometric set for all edge results
    hb_parent.name = "MEASURE SURFACE CURVE AS CIRCLE"

    for edge_number in range(1, total_edges):

        edge_ref_b = None
        for orientation in ("+1", "-1"):
            brep_core = f"BorderREdge:(BEdge:(Brp:(GSMBiDim.{gsm_id};{edge_number});None:(Limits1:();Limits2:();{orientation});Cf14:());WithPermanentBody;WithoutBuildError;WithSelectingFeatureSupport;MFBRepVersion_CXR29)"
            try:
                edge_ref_b = part.create_reference_from_b_rep_name(brep_core, part.find_object_by_name(f"GSMBiDim.{gsm_id}"))
                break
            except:
                continue
        if edge_ref_b is None:
            continue                                                                                            #Skip indices that are not border edges

        #Create curve to measure
        hb_con = hybrid_bodies.add()
        hb_con.name = f"CURVE CON Edge {edge_number}"

        #Extract Edge
        edge_extract = hybrid_shape_factory.add_new_extract(edge_ref_b)                                       #Create new extract
        edge_extract.propagation_type = 2                                                                      #Set Propagation type - tangent continuity
        edge_extract.complementary_extract = False                                                             #Set Comp extract to false
        edge_extract.is_federated = False                                                                      #Set federated to false
        hb_con.append_hybrid_shape(edge_extract)                                                               #Add extract to geometric set
        edge_extract.name = "edge_extract"                                                                     #Rename Extract
        edge_ref = part.create_reference_from_object(edge_extract)
        part.update()

        direction_con_edge = hybrid_shape_factory.add_new_direction_by_coord(1.0, 2.0, 3.0)
        edge_extremum = hybrid_shape_factory.add_new_extremum(edge_ref, direction_con_edge, 1)
        hb_con.append_hybrid_shape(edge_extremum)
        part.update()

        edge_extremum_ref = part.create_reference_from_object(edge_extremum)
        edge_extremum_datum = hybrid_shape_factory.add_new_point_datum(edge_extremum_ref)
        hb_con.append_hybrid_shape(edge_extremum_datum)
        part.update()

        hybrid_shape_factory.delete_object_for_datum(edge_extremum_ref)
        part.in_work_object = edge_extremum_datum

        mid_point = hybrid_shape_factory.add_new_point_on_curve_from_percent(edge_ref, 0.5, False)
        mid_point.point = edge_extremum_datum
        hb_con.append_hybrid_shape(mid_point)
        part.update()

        plane_normal = hybrid_shape_factory.add_new_plane_normal(edge_ref, mid_point)
        hb_con.append_hybrid_shape(plane_normal)
        part.update()

        intersect_curve = hybrid_shape_factory.add_new_intersection(plane_normal, surface_ref)
        hb_con.append_hybrid_shape(intersect_curve)
        part.update()

        #Create extract from intersection
        hb = hb_parent.hybrid_bodies.add()                                                                     #Add sub geometric set inside parent
        hb.name = f"Edge {edge_number}"                                                                        #Set name for new geometric set
        part.in_work_object = hb                                                                               #Make new geometric set inwork object

        curve_extract = hybrid_shape_factory.add_new_extract(intersect_curve)                                 #Create new extract
        curve_extract.propagation_type = 2                                                                     #Set Propagation type - tangent continuity
        curve_extract.complementary_extract = False                                                            #Set Comp extract to false
        curve_extract.is_federated = False                                                                     #Set federated to false
        hb.append_hybrid_shape(curve_extract)                                                                  #Add extract to geometric set
        curve_extract.name = "Curve_Extract"                                                                   #Rename Extract
        part.update()

        #Create Datum from Curve
        curve_extract_explicit = hybrid_shape_factory.add_new_curve_datum(curve_extract)                      #Create datum
        hb.append_hybrid_shape(curve_extract_explicit)                                                         #Add to geometric set
        hb.hybrid_shapes.item(2).name = "Curve_Extract_Datum"                                                 #Rename datum
        hybrid_shape_factory.delete_object_for_datum(curve_extract)                                           #Remove construction

        selectionSet.clear()
        selectionSet.add(hb_con)
        selectionSet.delete()

        part.update()

        #Create points
        curve_extract_explicit_ref = part.create_reference_from_object(curve_extract_explicit)

        point_1 = hybrid_shape_factory.add_new_point_on_curve_from_percent(curve_extract_explicit_ref, 0.2, False)
        point_2 = hybrid_shape_factory.add_new_point_on_curve_from_percent(curve_extract_explicit_ref, 0.5, False)
        point_3 = hybrid_shape_factory.add_new_point_on_curve_from_percent(curve_extract_explicit_ref, 0.8, False)

        hb.append_hybrid_shape(point_1)
        hb.append_hybrid_shape(point_2)
        hb.append_hybrid_shape(point_3)
        part.update()

        point_1_ref = part.create_reference_from_object(point_1)
        point_2_ref = part.create_reference_from_object(point_2)
        point_3_ref = part.create_reference_from_object(point_3)

        #Create datum from points
        point_1_datum = hybrid_shape_factory.add_new_point_datum(point_1_ref)                                 #Create datum from point
        point_2_datum = hybrid_shape_factory.add_new_point_datum(point_2_ref)                                 #Create datum from point
        point_3_datum = hybrid_shape_factory.add_new_point_datum(point_3_ref)                                 #Create datum from point

        hb.append_hybrid_shape(point_1_datum)                                                                  #Add point to set
        hb.append_hybrid_shape(point_2_datum)                                                                  #Add point to set
        hb.append_hybrid_shape(point_3_datum)                                                                  #Add point to set

        point_1_datum.name = "Point_datum_1"                                                                   #Rename point
        point_2_datum.name = "Point_datum_2"                                                                   #Rename point
        point_3_datum.name = "Point_datum_3"                                                                   #Rename point

        hybrid_shape_factory.delete_object_for_datum(point_1_ref)                                             #Remove construction
        hybrid_shape_factory.delete_object_for_datum(point_2_ref)                                             #Remove construction
        hybrid_shape_factory.delete_object_for_datum(point_3_ref)                                             #Remove construction
        part.update()

        coords_1 = spa_workbench.get_measurable(part.create_reference_from_object(point_1_datum)).get_point()
        coords_2 = spa_workbench.get_measurable(part.create_reference_from_object(point_2_datum)).get_point()
        coords_3 = spa_workbench.get_measurable(part.create_reference_from_object(point_3_datum)).get_point()

        if are_collinear(coords_1, coords_2, coords_3):                                                        #Checks if points are colinear, 3point circle will fail in this case
            results.append(f"Edge {edge_number}: Planar (points are collinear)")
            continue

        point_1_datum_ref = part.create_reference_from_object(point_1_datum)
        point_2_datum_ref = part.create_reference_from_object(point_2_datum)
        point_3_datum_ref = part.create_reference_from_object(point_3_datum)

        #Create 3 Point circle
        circle_to_measure = hybrid_shape_factory.add_new_circle3_points(
                point_1_datum_ref, point_2_datum_ref, point_3_datum_ref)                                       #Create circle with 3 points
        circle_to_measure.set_limitation(1)                                                                    #Set limitation to 1, (Full circle)
        hb.append_hybrid_shape(circle_to_measure)                                                              #Add circle to set
        part.update()

        circle_to_measure_ref = part.create_reference_from_object(circle_to_measure)
        circle_to_measure_datum = hybrid_shape_factory.add_new_circle_datum(circle_to_measure_ref)            #Create datum from circle
        hb.append_hybrid_shape(circle_to_measure_datum)                                                        #Add datum to set
        circle_to_measure_datum.name = "Circle_To_Measure_Datum"                                              #Rename circle
        hybrid_shape_factory.delete_object_for_datum(circle_to_measure_ref)                                   #Remove construction
        part.update()

        reference = part.create_reference_from_object(circle_to_measure_datum)                                #Create ref to measure
        measurable = spa_workbench.get_measurable(reference)                                                   #Create measurable object from spa workbench
        radius = round(measurable.radius, 2)                                                                   #Get radius, rounded to 2 decimal places
        results.append(f"Edge {edge_number}: R={radius}mm  D={radius * 2}mm")

    catia().message_box("\n".join(results) if results else "No valid edges found", buttons=32, title="Result")  #Print result to message box.
