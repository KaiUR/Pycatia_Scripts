'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Export_Points_Select_Geo_Set_To_CSV.py
    Version:        1.0
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Export points from any geometric set to an xyz file.
    Author:         Kai-Uwe Rathjen
    Date:           04.03.26
    Description:    This script will ask the user for for a geometric set containing points.
                    The script will measure the points relative to the absolute axis system and the create an
                    CSV file. The name of the points in the exported file are the same as in catia for each point. 
                    This scrip assumes that the points are explicit (Isolated)
    dependencies = [
                    "pycatia",
                    ]
    requirements:   Python >= 3.10
                    pycatia
                    Catia V5 running with an geometric set that contains points. The points should be datums(Isolated)
                    This script needs an open part document.
    -----------------------------------------------------------------------------------------------------------------------
    
    Change:
    
    -----------------------------------------------------------------------------------------------------------------------
'''

#Imports
from pycatia import catia
from pycatia.hybrid_shape_interfaces.hybrid_shape_point_coord import HybridShapePointCoord
from pycatia.mec_mod_interfaces.part_document import PartDocument
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

if __name__ == "__main__":
    #Anchoring relavent components
    caa = catia()                                                                                               #Catia application instance
    part_document: PartDocument = caa.active_document                                                           #Current open document
    part = part_document.part                                                                                   #Current part
    hybrid_bodies = part.hybrid_bodies                                                                          #Set off all top level geometric sets
    axis_systems = part.axis_systems                                                                            #Set of all axis systems
    spa_workbench = part_document.spa_workbench()                                                               #Initilize spa workbench (For measurments)
                     
    axis_id = 1                                                                                                 #ABS axix systme as default                                                                              #Set index
    axis_system = part.axis_systems.item(axis_id)                                                               #Set axis

    print("\n Select Geometric set containing points\n")
    #Get User to select a geometric set that contains the points
    object_filter = ("AnyObject",)                                                                              #Set user selection filter 
    selectionSet = caa.active_document.selection                                                                #Create container for selection
    status = selectionSet.select_element3(object_filter,"Select Set Containing Points" , False , 2 , False)     #Runs an interactive selection command, exhaustive version.

    if status != "Normal":                                                                                      #Check if selection was succesful
        print("Error selecting geometric set containing points.")
        exit(1);                                                                                                #Exit

    # Get points to measure
    hb = searchHybridBody(part_document.selection.item(1).value.name, hybrid_bodies)                            #Get selected geometric set
    if hb == None:                                                                                              #Could not get geometric set.
        print("Error: could not find geometric set.")
        exit(1);                                                                                                #Exit.

    hs = hb.hybrid_shapes                                                                                       #Get all hybrid shpaes in geometric set.

    print("\n Creating file\n\n")
    f = open(hb.name + ".xyz", "w")                                                                             #Create new file
    f.write("Point Name,X,Y,Z\n")                                                                              #csv file header

    #Walk through all points
    for i in range(len(hs)):                                                                              #Loop all hybrid shapes
        shape_index = i + 1                                                                                     #indexes start at one
        
        current_hs = hs.item(shape_index)                                                                       #Get current shape
        part_document.selection.clear()                                                                         # clear the selection on each loop.
        part_document.selection.add(current_hs)                                                                 # add the shape to the selection.
        selected_elem = part_document.selection.item(1)                                                         # create the selected element by getting the first item in the document selection.

        if selected_elem.type == "HybridShapePointExplicit":                                                    #Check that point is HybridShapePointExplicit
            point = HybridShapePointCoord(current_hs.com_object)                                                #Cast the point
            
            coords = coords_relative_to_axis(axis_system, point)                                                # Measure point to axis system and print
            print(current_hs.name, coords)                                                                      #Print Current point to console
            
            f.write(current_hs.name + "," + str(coords[0]) + "," + str(coords[1]) + "," + str(coords[2]) + "\n") #Write point to file

    f.close()                                                                                                   #Close file

    print("\n\n Completed\n\n")