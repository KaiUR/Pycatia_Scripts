'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Measure_Curve_With_3_PTS_AS_CIRCLE.py
    Version:        1.1
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Measures curves by adding three points and gives a diamiter.
    Author:         Kai-Uwe Rathjen
    Date:           09.03.26
    Description:    This script will ask the user to select a curve. The script will put three points on the curve and then place a 
                    circle. Then the script will measure this circle.
    dependencies = [
                    "pycatia",  
                    ]
    requirements:   Python >= 9.10
                    pycatia
                    Catia V5 running wtih an open part cantaining a curve to measure
                    This script needs an open part document.
    -----------------------------------------------------------------------------------------------------------------------
    
    Change:         19.03.26
                    Modified script to work when there is a process or procuct open containing a part.
    
    -----------------------------------------------------------------------------------------------------------------------
'''

#Imports
from pycatia import catia
from pycatia.hybrid_shape_interfaces.hybrid_shape_extract import HybridShapeExtract
from pycatia.hybrid_shape_interfaces.hybrid_shape_point_on_curve import HybridShapePointOnCurve
from pycatia.mec_mod_interfaces.part_document import PartDocument
from pycatia.mec_mod_interfaces.part import Part
import time
'''
    This function will return a points coordinates relative to an axis system.
    
    Inputs:
        axis_system         The axis sytem to measure relative to
        point               The point being measured
        precision=6         The precision for the calculation (Default = 6)
        
    output:
        The coordinates of the point relative to the axis system inputed as a vector
        
    Requirments:
        Two custom functions to calculate the dot product and a function to 
        normalize vectors.
'''
def coords_relative_to_axis(axis_system, point, precision=6):
    #Get axises
    a_origin = axis_system.get_origin()
    a_xaxis = axis_system.get_x_axis()
    a_yaxis = axis_system.get_y_axis()
    a_zaxis = axis_system.get_z_axis()

    #Normalize
    n_x = normalize_vector(a_xaxis)
    n_y = normalize_vector(a_yaxis)
    n_z = normalize_vector(a_zaxis)

    #Measure Point
    reference = part.create_reference_from_object(point)
    measurable = spa_workbench.get_measurable(reference)
    coordinates = measurable.get_point()

    #Get difference
    diff = [0] * 3
    diff[0] = coordinates[0] - a_origin[0]
    diff[1] = coordinates[1] - a_origin[1]
    diff[2] = coordinates[2] - a_origin[2]

    #Get dot product
    x = round(dot_product(diff, n_x), precision)
    y = round(dot_product(diff, n_y), precision)
    z = round(dot_product(diff, n_z), precision)

    return x, y, z

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
    This function searches for a hybrid body by name and return is.
    
    Inputs:
        searchName              The name of the geometric set that is being searched for.
        currentHybridBodies     The current collection of geometric sets
        
    output:
        The geometric set that is found, or None if not found
''' 

if __name__ == "__main__":
    caa = catia()                                                                                               #Catia 
    active_doc = caa.active_document                                                                            #Current Document
    selectionSet = active_doc.selection                                                                         #Secection

    object_filter = ("MonoDimInfinite",)                                                                        #Set user selection filter(Curves)                              
    selectionSet = caa.active_document.selection                                                                #Create container for selection
    status = selectionSet.select_element3(
            object_filter,"Select a curve to measure" , False , 2 , False)                                      #Runs an interactive selection command, exhaustive version. 
    if status != "Normal":                                                                                      #Check if selection was succesful
        print("You must select a curve")
        exit()

    selected_item = selectionSet.item(1)                                                                        #Selected element
   
    try:
        part = active_doc.part                                                                                  #If document is part document
    except AttributeError:                                                                                      #Else get part from product structure
        # We are in a Product or Process; find the Part via the selection
        # We use .com_object to access the LeafProduct property
        leaf_product = selected_item.com_object.LeafProduct
        part_document = PartDocument(leaf_product.ReferenceProduct.Parent)
        # Navigation: LeafProduct -> ReferenceProduct -> Parent (PartDocument) -> Part
        part = part_document.part                                                                               #Get new part object

    spa_workbench = active_doc.spa_workbench()
    
    # Save the reference before clearing selection
    extract_ref = selected_item.reference                                                                       #Save selection as reference
    selectionSet.clear()                                                                                        #Clear selection
    
    hybrid_bodies = part.hybrid_bodies                                                                          #Set off all top level geometric sets
    hybrid_shape_factory = part.hybrid_shape_factory                                                            #GSD workbentch to create hybridshapes
    
    #create extract from selection
    hb = hybrid_bodies.add()                                                                                    #Add new geometric set
    hb.name = "MEASURE CURVE AS CIRCLE"                                                                         #Set name for new geometric set
    part.in_work_object = hb                                                                                    #Make new geometric set inwork object

    curve_extract = hybrid_shape_factory.add_new_extract(extract_ref)                                           #Create new extract

    curve_extract.propagation_type = 1                                                                          #Set Propagation type
    curve_extract.complementary_extract = False                                                                 #Set Comp extract to false
    curve_extract.is_federated = False                                                                          #Set federated to false
    hb.append_hybrid_shape(curve_extract)                                                                       #Add ectract to geometric set

    hb.hybrid_shapes.item(1).name = "Curve_Extract"                                                             #Rename Extract

    part.update()                                                                                               #Update part document
    
    #create Datum from Curve
    curve_extract_explicit = hybrid_shape_factory.add_new_curve_datum(hb.hybrid_shapes.item(1))                 #Create datum
    hb.append_hybrid_shape(curve_extract_explicit)                                                              #Add to geometric set

    hb.hybrid_shapes.item(2).name = "Curve_Extract_Datum"                                                       #Rename datum

    hybrid_shape_factory.delete_object_for_datum(hb.hybrid_shapes.item(1))                                      #Remove construction

    part.update()                                                                                               #Update part document
    
    '''
    We are creating the points as extremums becuase if you try to create points on a closed curve
    the script will fail as the points on a closed curves are explicit, and can only be exposed using
    boundary references. However creating extremums will not work on curves with big radii, in this case 
    we will check for the failur of the extremum points( generally all three poinst are the same) and
    we will instead create the point as a percentage along the curve.
    '''
    dir_con_1 = hybrid_shape_factory.add_new_direction_by_coord(0, 0, 1)                                        #Create direction for extremum
    dir_con_2 = hybrid_shape_factory.add_new_direction_by_coord(0, 1, 0)                                        #Create direction for extremum
    dir_con_3 = hybrid_shape_factory.add_new_direction_by_coord(1, 0, 0)                                        #Create direction for extremum
    
    curve_ref = part.create_reference_from_object(hb.hybrid_shapes.item(1))                                     #Create a ref
    extremum_point_1 = hybrid_shape_factory.add_new_extremum(curve_ref, dir_con_1, 1)                           #Create first extremum point
    hb.append_hybrid_shape(extremum_point_1)                                                                    #Add point to set
    
    extremum_point_2 = hybrid_shape_factory.add_new_extremum(curve_ref, dir_con_2, 1)                           #Create first extremum point
    hb.append_hybrid_shape(extremum_point_2)                                                                    #Add point to set
    
    extremum_point_3 = hybrid_shape_factory.add_new_extremum(curve_ref, dir_con_3, 1)                           #Create first extremum point
    hb.append_hybrid_shape(extremum_point_3)                                                                    #Add point to set
    
    part.update()                                                                                               #Update part
    
    #Check points
    coords_1 = coords_relative_to_axis(part.axis_systems.item(1), extremum_point_1)                             #Get the point coordinates
    coords_2 = coords_relative_to_axis(part.axis_systems.item(1), extremum_point_1)                             #Get the point coordinates
    coords_3 = coords_relative_to_axis(part.axis_systems.item(1), extremum_point_1)                             #Get the point coordinates
    
    '''
    Here we replace points if the extremums didnt give a good result
    '''
    if len(set([coords_1, coords_2, coords_3])) == 1:                                                           #If points are equal
        hybrid_shape_factory.delete_object_for_datum(hb.hybrid_shapes.item(2))                                  #Remove point
        hybrid_shape_factory.delete_object_for_datum(hb.hybrid_shapes.item(2))                                  #Remove point
        hybrid_shape_factory.delete_object_for_datum(hb.hybrid_shapes.item(2))                                  #Remove point
        point_1 = hybrid_shape_factory.add_new_point_on_curve_from_percent(hb.hybrid_shapes.item(1), 0.2, 0)    #Create point on curve 20%
        hb.append_hybrid_shape(point_1)                                                                         #Add point to set
        point_2 = hybrid_shape_factory.add_new_point_on_curve_from_percent(hb.hybrid_shapes.item(1), 0.5, 0)    #Create point on curve 50%
        hb.append_hybrid_shape(point_2)                                                                         #Add point to set
        point_3 = hybrid_shape_factory.add_new_point_on_curve_from_percent(hb.hybrid_shapes.item(1), 0.8, 0)    #Create point on curve 80%
        hb.append_hybrid_shape(point_3)                                                                         #Add point to set
        part.update()                                                                                           #Part update
    
    #Create datum from points
    point_1_datum = hybrid_shape_factory.add_new_point_datum(hb.hybrid_shapes.item(2))                          #Create datum from point
    point_2_datum = hybrid_shape_factory.add_new_point_datum(hb.hybrid_shapes.item(3))                          #Create datum from point
    point_3_datum = hybrid_shape_factory.add_new_point_datum(hb.hybrid_shapes.item(4))                          #Create datum from point
    
    hb.append_hybrid_shape(point_1_datum)                                                                       #Add point to set
    hb.append_hybrid_shape(point_2_datum)                                                                       #Add point to set
    hb.append_hybrid_shape(point_3_datum)                                                                       #Add point to set
    
    hb.hybrid_shapes.item(5).name = "Point_Datum_1"                                                             #Rename point
    hb.hybrid_shapes.item(6).name = "Point_datum_2"                                                             #Rename point
    hb.hybrid_shapes.item(7).name = "Point_datum_3"                                                             #Rename point
    
    hybrid_shape_factory.delete_object_for_datum(hb.hybrid_shapes.item(2))                                      #Remove construction
    hybrid_shape_factory.delete_object_for_datum(hb.hybrid_shapes.item(2))                                      #Remove construction
    hybrid_shape_factory.delete_object_for_datum(hb.hybrid_shapes.item(2))                                      #Remove construction
    
    part.update()                                                                                               #Update part
    
    #Create 3 Point circle
    circle_to_measure = hybrid_shape_factory.add_new_circle3_points(
            hb.hybrid_shapes.item(2), hb.hybrid_shapes.item(3), hb.hybrid_shapes.item(4))                       #Create circle with 3 points
    
    circle_to_measure.set_limitation(1)                                                                         #Set limitation to 1, (Full circle)
    hb.append_hybrid_shape(circle_to_measure)                                                                   #Add circle to set
    
    part.update()                                                                                               #Update part
    
    circle_to_measure_datum = hybrid_shape_factory.add_new_circle_datum(hb.hybrid_shapes.item(5))               #Create datum from circle
    hb.append_hybrid_shape(circle_to_measure_datum)                                                             #Add datum to set
    hb.hybrid_shapes.item(6).name = "Circle_To_Measure_Datum"                                                   #Rename circle
    
    hybrid_shape_factory.delete_object_for_datum(hb.hybrid_shapes.item(5))                                      #Remove construction
    
    part.update()                                                                                               #Update part
    
    #Measure_Curve_With_3_PTS_AS_CIRCLE
    
    reference = part.create_reference_from_object(hb.hybrid_shapes.item(5))                                     #Create ref to measure
    measurable = spa_workbench.get_measurable(reference)                                                        #Create measureable object from spa workbench

    radius =  round(measurable.radius, 2)                                                                       #Get radius, rounded to 2 decimal places
    
    selectionSet.add(hb)                                                                                        #Select construction geometric set
    selectionSet.delete()                                                                                       #Delete construction
    
    time.sleep(1)                                                                                               #Wait a second for delete to finish before showing message_box
    
    result = catia().message_box(
            "Radius: " + str(radius) + "mm\nDiameter: " + str(radius * 2) + "mm", buttons=32, title="Result")   #Print result to message box.