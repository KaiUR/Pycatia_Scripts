'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Join_Explicit_No_Connect_Curve.py
    Version:        1.0
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Joins curves even when they are not connex.
    Author:         Kai-Uwe Rathjen
    Date:           04.03.26
    Description:    This script will ask the user to select curves and join them without checking for connex.
    dependencies = [
                    "pycatia",
                    ]
    requirements:   Python >= 9.10
                    pycatia
                    Catia V5 running wtih an open part cantaining curves.
                    This script needs an open part document.
    -----------------------------------------------------------------------------------------------------------------------
    
    Change:
    
    -----------------------------------------------------------------------------------------------------------------------
'''

#Imports
from pycatia import catia
from pycatia.hybrid_shape_interfaces.hybrid_shape_assemble import HybridShapeAssemble
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
    currentSearch = currentHybridBodies.item(seachName)                                                     #Try to get the set we are looking for, will be none if not found.
    
    if currentSearch != None:                                                                               #If not none, i.e. Set was found
        return hybrid_bodies.item(seachName)                                                                #Return the set
    else:                                                                                                   #If not found
        if currentHybridBodies.count > 0:                                                                   #If the current set contains sets                                                 
            for index in range(hybrid_bodies.count):                                                        #Loop all sets in the current set
                return searchHybridBody(seachName, hybrid_bodies.item(index+1).hybrid_bodies)               #Recursive call of this function to search further down tree.
    
    return None 

if __name__ == "__main__":
    #Anchoring relavent components
    caa = catia()                                                                                               #Catia application instance
    part_document: PartDocument = caa.active_document                                                           #Current open document
    part = part_document.part                                                                                   #Current part
    hybrid_bodies = part.hybrid_bodies                                                                          #Set off all top level geometric sets
    hybrid_shape_factory = part.hybrid_shape_factory                                                            #GSD workbentch to create hybridshapes

    object_filter = ("MonoDimInfinite",)                                                                        #Set user selection filter (Curves)                             
    selectionSet = caa.active_document.selection                                                                #Create container for selection
    status = selectionSet.select_element3(object_filter,"Select curves to join" , False , 2 , False)            #Runs an interactive selection command, exhaustive version. 
    if status != "Normal":                                                                                      #Check if selection was succesful
        print("You must select curves")
        exit()

    if selectionSet.count < 2:                                                                                  #If nothing to join, exit
        print("You must select at least two curves")
        exit()
          
    #New join command
    join_hybrid_shapes = hybrid_shape_factory.add_new_join(
            selectionSet.item(1).reference, selectionSet.item(2).reference)                                     #Add first two elements to join command
    
    if selectionSet.count > 2:                                                                                  #If there are more than two elements
        index = 3
        while index <= selectionSet.count:                                                                      #Loop through remaining
            join_hybrid_shapes.add_element(selectionSet.item(index).reference)                                  #Add remaining to join
            index = index + 1
    
    #Set join paramaters
    join_hybrid_shapes.set_angular_tolerance(0.5)                                                               #Set angle tol
    join_hybrid_shapes.set_angular_tolerance_mode(False)                                                        #Turn off angle tol mode
    join_hybrid_shapes.set_connex(False)                                                                        #No check connex
    join_hybrid_shapes.set_deviation(0.02)                                                                      #Merge distance
    join_hybrid_shapes.set_federation_propagation(0)                                                            #no federate
    join_hybrid_shapes.set_healing_mode(False)                                                                  #No Healing
    join_hybrid_shapes.set_simplify(False)                                                                      #No simplify
    join_hybrid_shapes.set_suppress_mode(True)                                                                  #Must be true
    join_hybrid_shapes.set_tangency_continuity(False)                                                           #No tangent cont
    join_hybrid_shapes.set_manifold(True)                                                                       #Check manifold
    
    hb = searchHybridBody(part.in_work_object.name, hybrid_bodies)                                              #Find the in work object geometric set
    if hb == None:                                                                                              #If not found
        hb = hybrid_bodies.add()                                                                                #Add new gemetric set
        hb.name = "New Join Explicit"                                                                           #Rename Set
    
    hb.append_hybrid_shape(join_hybrid_shapes)                                                                  #Add join to geometric set
    part.update()                                                                                               #Update part
    
    join_datum_curve = hybrid_shape_factory.add_new_curve_datum(hb.hybrid_shapes.item(hb.hybrid_shapes.count))  #Create datum from join
    hb.append_hybrid_shape(join_datum_curve)                                                                    #Add datum to geometric set
    
    selectionSet.clear()                                                                                        #Clear selection
    selectionSet.search("Name=Join_Explicit_curve*,al")                                                         #look for all joins of this type
    new_number = selectionSet.count                                                                             #Count the result
    
    hb.hybrid_shapes.item(hb.hybrid_shapes.count).name = "Join_Explicit_curve." + str(new_number + 1)           #Name the join and add the number
    hybrid_shape_factory.delete_object_for_datum(hb.hybrid_shapes.item(hb.hybrid_shapes.count - 1))             #Remove construction
    part.update()                                                                                               #Update part