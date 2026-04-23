'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Join_Explicit_No_Connect_Surface.py
    Version:        1.1
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Joins surfaces even when they are not connex.
    Author:         Kai-Uwe Rathjen
    Date:           04.03.26
    Description:    This script will ask the user to select surfaces and join them without checking for connex.
    dependencies = [
                    "pycatia",
                    ]
    requirements:   Python >= 9.10
                    pycatia
                    Catia V5 running wtih an open part cantaining surfaces.
                    This script needs an open part document.
    -----------------------------------------------------------------------------------------------------------------------
    
    Change:         19.03.26
                    Modified script to work when there is a process or procuct open containing a part.
    
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
    caa = catia()                                                                                               #Catia 
    active_doc = caa.active_document                                                                            #Current Document

    object_filter = ("BiDimInfinite",)                                                                          #Set user selection filter(Surfaces)                              
    selectionSet = caa.active_document.selection                                                                #Create container for selection
    status = selectionSet.select_element3(object_filter,"Select surfaces to join" , False , 2 , False)          #Runs an interactive selection command, exhaustive version. 
    if status != "Normal":                                                                                      #Check if selection was succesful
        print("You must select surfaces")
        exit()

    if selectionSet.count < 2:                                                                                  #If nothing to join, exit
        print("You must select at least two surface")
        exit()

    selected_item = selectionSet.item(1) 

    if type(active_doc) is PartDocument:
        part = active_doc.part                                                                                  #If document is part document
        part_document : PartDocument = active_doc
    else:                                                                                                       #Else get part from product structure
        # We are in a Product or Process; find the Part via the selection
        # We use .com_object to access the LeafProduct property
        leaf_product = selected_item.com_object.LeafProduct
        part_document = PartDocument(leaf_product.ReferenceProduct.Parent)
        # Navigation: LeafProduct -> ReferenceProduct -> Parent (PartDocument) -> Part
        part = part_document.part                                                                              #Get new part object

    hybrid_bodies = part.hybrid_bodies                                                                          #Set off all top level geometric sets
    hybrid_shape_factory = part.hybrid_shape_factory                                                            #GSD workbentch to create hybridshapes
         
    #New join command
    join_hybrid_shapes = hybrid_shape_factory.add_new_join(
        selectionSet.item(1).reference, selectionSet.item(2).reference)                                         #Add first two elements to join command
    
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
    
    hb = searchHybridBody(part.in_work_object.name, hybrid_bodies)                                              #Look for the in work object geometric set
    if hb == None:                                                                                              #If not found
        hb = hybrid_bodies.add()                                                                                #Add new geometric set
        hb.name = "New Join Explicit"                                                                           #Rename geometric set
        
    hb.append_hybrid_shape(join_hybrid_shapes)                                                                  #Add join to geometric set
    part.update()                                                                                               #Update part
    
    join_datum_surface = hybrid_shape_factory.add_new_surface_datum(
            hb.hybrid_shapes.item(hb.hybrid_shapes.count))                                                      #Create datum from join
    hb.append_hybrid_shape(join_datum_surface)                                                                  #Add datum to geometric set
    
    selectionSet.clear()                                                                                        #Clear selection
    selectionSet.search("Name=Join_Explicit_Surface*,al")                                                       #Look for all joins of this type
    new_number = selectionSet.count                                                                             #Count the result
    
    hb.hybrid_shapes.item(hb.hybrid_shapes.count).name = "Join_Explicit_Surface." + str(new_number + 1)         #Rename the join
    hybrid_shape_factory.delete_object_for_datum(hb.hybrid_shapes.item(hb.hybrid_shapes.count - 1))             #Remove the construction
    part.update()                                                                                               #Update part