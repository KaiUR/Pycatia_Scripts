'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Extract_Boundary_Curves.py
    Version:        1.0
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Extract all boundary edges of a selected surface as datum curves.
    Author:         Kai-Uwe Rathjen
    Date:           06.05.26
    Description:    This script will ask the user to select a surface and then an edge on that surface.
                    The script will then extract the boundary of the surface with tangent propagation as an
                    explicit datum curve and place it in the current in-work geometric set.
                    Each boundary curve is named Boundary_Extract.N where N is an incrementing number.
    dependencies = [
                    "pycatia",
                    ]
    requirements:   Python >= 3.10
                    pycatia
                    Catia V5 running with an open part document containing surfaces.
                    This script needs an open part document.
    -----------------------------------------------------------------------------------------------------------------------

    Change:

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

if __name__ == "__main__":
    #Anchoring relavent components
    caa = catia()                                                                                               #Catia application instance
    active_doc = caa.active_document                                                                            #Current Document

    object_filter = ("BiDimInfinite",)                                                                          #Set user selection filter (Surfaces only)
    selectionSet = caa.active_document.selection                                                                #Create container for selection
    status = selectionSet.select_element3(object_filter, "Select surface to extract boundaries from", False, 2, False) #Runs an interactive selection command, exhaustive version.
    if status != "Normal":                                                                                      #Check if selection was succesful
        print("You must select a surface")
        exit()

    selected_item = selectionSet.item(1)                                                                        #Get selected item

    if type(active_doc) is PartDocument:                                                                        #If document is part document
        part = active_doc.part
        part_document: PartDocument = active_doc
    else:                                                                                                       #Else get part from product structure
        leaf_product = selected_item.com_object.LeafProduct                                                     #Get leaf product
        part_document = PartDocument(leaf_product.ReferenceProduct.Parent)                                      #Get part document
        part = part_document.part                                                                               #Get new part object

    hybrid_bodies = part.hybrid_bodies                                                                          #Set off all top level geometric sets
    hybrid_shape_factory = part.hybrid_shape_factory                                                            #GSD workbench to create hybridshapes

    surface_reference = selected_item.reference                                                                  #Get reference to selected surface
    surface_value = selected_item.value                                                                         #Get surface value for use as support

    selectionSet.clear()                                                                                        #Clear selection
    object_filter2 = ("AnyObject",)                                                                             #Set user selection filter
    status2 = selectionSet.select_element3(object_filter2, "Select an edge on the surface", False, 2, False)    #Ask user to select an edge on the surface
    if status2 != "Normal":                                                                                     #Check if selection was succesful
        print("You must select an edge on the surface")
        exit()

    edge_reference = selectionSet.item(1).reference                                                             #Get reference to selected edge

    hb = searchHybridBody(part.in_work_object.name, hybrid_bodies)                                              #Look for the in work object geometric set
    if hb == None:                                                                                              #If not found
        hb = hybrid_bodies.add()                                                                                #Add new geometric set
        hb.name = "Boundary_Extract"                                                                            #Rename geometric set

    selectionSet.clear()                                                                                        #Clear selection
    selectionSet.search("Name=Boundary_Extract*,all")                                                           #Search for existing boundary extracts
    existing_count = selectionSet.count                                                                         #Count existing boundary extracts
    selectionSet.clear()                                                                                        #Clear selection

    boundary_count = 0                                                                                          #Count of boundaries created

    propagation_type = 2                                                                                        #Tangent propagation
    boundary = hybrid_shape_factory.add_new_boundary(edge_reference, surface_reference, propagation_type)       #Create boundary - requires edge, support surface and propagation type
    hb.append_hybrid_shape(boundary)                                                                            #Add boundary to geometric set
    part.update()                                                                                               #Update part

    boundary_datum = hybrid_shape_factory.add_new_curve_datum(                                                  #Create datum from boundary
            hb.hybrid_shapes.item(hb.hybrid_shapes.count))
    hb.append_hybrid_shape(boundary_datum)                                                                      #Add datum to geometric set
    hb.hybrid_shapes.item(hb.hybrid_shapes.count).name = "Boundary_Extract." + str(existing_count + 1)         #Name the boundary datum
    hybrid_shape_factory.delete_object_for_datum(hb.hybrid_shapes.item(hb.hybrid_shapes.count - 1))            #Remove construction boundary
    part.update()                                                                                               #Update part
    boundary_count = boundary_count + 1                                                                         #Increment count

    print(f"\n Completed - {boundary_count} boundary curve(s) created\n")
