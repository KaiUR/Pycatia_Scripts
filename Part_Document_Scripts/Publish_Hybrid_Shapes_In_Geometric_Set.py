'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Publish_Hybrid_Shapes_In_Geometric_Set.py
    Version:        1.1
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Publish all hybrid shapes in a selected geometric set.
    Author:         Kai-Uwe Rathjen
    Date:           06.05.26
    Description:    This script will ask the user to select a geometric set. The script will then publish
                    every hybrid shape inside the selected geometric set using the shape name as the
                    publication name. Shapes that are already published are skipped. Useful for exposing
                    geometry for use in product context or skeleton models.

                    The reference path is built as:
                    PartName/!GeoSet/ChildSet/.../ShapeName
                    as required by CreateReferenceFromName.
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
    This function searches for a hybrid body by name and returns it along with its full path
    from the root hybrid bodies collection.

    Inputs:
        searchName              The name of the geometric set being searched for.
        currentHybridBodies     The current collection of geometric sets.
        currentPath             The path built so far (used in recursion).

    output:
        Tuple of (HybridBody, path string) if found, or (None, None) if not found.
        Path is in the form "GeoSetName/ChildSetName" for nested sets.
'''
def searchHybridBodyWithPath(seachName, currentHybridBodies, currentPath=""):
    for index in range(currentHybridBodies.count):                                                              #Search at current level by explicit name comparison
        hb = currentHybridBodies.item(index + 1)                                                                #Get geometric set
        if hb.name == seachName:                                                                                #Found at this level
            path = (currentPath + "/" if currentPath else "") + seachName                                       #Build path
            return hb, path                                                                                     #Return found geometric set and path

    for index in range(currentHybridBodies.count):                                                              #Loop through geometric sets of this level
        hb = currentHybridBodies.item(index + 1)                                                                #Get geometric set
        if hb.hybrid_bodies.count > 0:                                                                          #If it has children
            child_path = (currentPath + "/" if currentPath else "") + hb.name                                   #Build path to this level
            found, found_path = searchHybridBodyWithPath(seachName, hb.hybrid_bodies, child_path)               #Recursive call
            if found is not None:                                                                               #If found
                return found, found_path                                                                        #Return found

    return None, None                                                                                           #Return not found

if __name__ == "__main__":
    #Anchoring relavent components
    caa = catia()                                                                                               #Catia application instance
    part_document: PartDocument = caa.active_document                                                          #Current open document

    if type(part_document) is not PartDocument:                                                                 #Check if part document
        print("A CATPart document must be the active document.")
        exit()

    part = part_document.part                                                                                   #Current part
    product = part_document.product                                                                             #Get product interface for publications
    hybrid_bodies = part.hybrid_bodies                                                                          #Set of all top level geometric sets
    publications = product.publications                                                                         #Get publications collection

    object_filter = ("HybridBody",)                                                                             #Set user selection filter (Geometric Set)
    selectionSet = caa.active_document.selection                                                                #Create container for selection
    status = selectionSet.select_element3(object_filter, "Select geometric set to publish", False, 2, False)    #Runs an interactive selection command, exhaustive version.
    if status != "Normal":                                                                                      #Check if selection was succesful
        print("You must select a geometric set")
        exit()

    selected_item = selectionSet.item(1)                                                                        #Get selected item
    geo_set_name = selected_item.value.name                                                                     #Get name of selected geometric set

    target_hb = HybridBody(selected_item.value.com_object)                                                      #Get selected geometric set directly from selection
    _, hb_path = searchHybridBodyWithPath(geo_set_name, hybrid_bodies)                                          #Build path for publication references
    if hb_path is None:                                                                                         #If path could not be built
        print(f"Error: Could not build path for geometric set '{geo_set_name}'")
        exit()

    hybrid_shapes = target_hb.hybrid_shapes                                                                     #Get all hybrid shapes in set

    if hybrid_shapes.count == 0:                                                                                #If no shapes
        print(f"Geometric set '{geo_set_name}' contains no hybrid shapes to publish")
        exit()

    print(f"\n Publishing {hybrid_shapes.count} shape(s) from '{geo_set_name}'\n")

    #Collect existing publication names to avoid duplicates
    existing_publications = []                                                                                  #List to store existing publication names
    for pub_index in range(publications.count):                                                                 #Loop through existing publications
        existing_publications.append(publications.item(pub_index + 1).name)                                     #Store publication name

    published_count = 0                                                                                         #Count of shapes published
    skipped_count = 0                                                                                           #Count of shapes skipped

    part_name = part.name                                                                                       #Get part name for reference path

    for index in range(hybrid_shapes.count):                                                                    #Loop through all shapes in set
        shape = hybrid_shapes.item(index + 1)                                                                   #Get shape
        shape_name = shape.name                                                                                  #Get shape name

        if shape_name in existing_publications:                                                                  #If already published
            print(f"  Skipped (already published): {shape_name}")
            skipped_count = skipped_count + 1                                                                   #Increment skipped count
            continue

        #Build reference path: PartName/!GeoSetPath/ShapeName
        ref_path = part_name + "/!" + hb_path + "/" + shape_name                                               #Full reference path as required by CreateReferenceFromName

        try:
            shape_ref = product.create_reference_from_name(ref_path)                                           #Create reference from path
            publications.add(shape_name)                                                                        #Add publication with shape name
            publications.set_direct(shape_name, shape_ref)                                                      #Set publication to reference
            print(f"  Published: {shape_name}")
            published_count = published_count + 1                                                               #Increment published count
        except Exception as e:
            print(f"  Error publishing '{shape_name}': {e}")

    part.update()                                                                                               #Update part

    print(f"\n\n Completed - {published_count} shape(s) published, {skipped_count} skipped\n\n")
