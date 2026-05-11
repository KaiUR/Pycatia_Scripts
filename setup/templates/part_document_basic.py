'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Your_Script_Name.py
    Version:        1.0
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        EDIT: One line summary shown on the script button.
    Author:         EDIT: Your Name
    Date:           EDIT: DD.MM.YY
    Description:    EDIT: Full description of what the script does.
                    EDIT: Continuation lines must be indented.
    dependencies = [
                    "pycatia",
                    ]
    requirements:   Python >= 3.10
                    pycatia
                    Catia V5 running with an open part document.
    -----------------------------------------------------------------------------------------------------------------------

    Change:

    -----------------------------------------------------------------------------------------------------------------------
'''

#Imports
from pycatia import catia
from pycatia.mec_mod_interfaces.part_document import PartDocument
from pathlib import Path

'''
    This function searches for a hybrid body (geometric set) by name and returns it.
    Searches recursively through all nested geometric sets.

    Inputs:
        searchName              The name of the geometric set being searched for.
        currentHybridBodies     The current collection of hybrid bodies to search.

    output:
        The geometric set if found, or None if not found.
'''
def searchHybridBody(seachName, currentHybridBodies):
    try:                                                                                                        #Try at current level
        currentSearch = currentHybridBodies.item(seachName)                                                    #Check if we can find it
        if currentSearch is not None:                                                                          #If found
            return currentSearch                                                                               #Return found geometric set
    except:
        pass                                                                                                   #Not found at this level — recurse

    for index in range(currentHybridBodies.count):                                                             #Loop through geometric sets at this level
        if currentHybridBodies.item(index+1).hybrid_bodies.count > 0:
            found = searchHybridBody(seachName, currentHybridBodies.item(index+1).hybrid_bodies)               #Recursive call

            if found is not None:                                                                              #If found
                return found                                                                                   #Return found

    return None                                                                                                #Return not found

if __name__ == "__main__":
    caa = catia()                                                                                               #Catia application instance
    active_doc = caa.active_document                                                                           #Current active document

    if type(active_doc) is not PartDocument:                                                                   #Check that a CATPart is active
        print("A CATPart document must be the active document.")
        exit()

    part_document: PartDocument = active_doc                                                                   #Cast to PartDocument
    part = part_document.part                                                                                  #Current part
    hybrid_bodies = part.hybrid_bodies                                                                         #Top level geometric sets
    hybrid_shape_factory = part.hybrid_shape_factory                                                           #GSD workbench for creating hybrid shapes
    selectionSet = active_doc.selection                                                                        #Create container for selection
    selectionSet.clear()                                                                                       #Clear any existing selection

    # TODO: Add script logic here.
    #
    # Common access patterns:
    #   searchHybridBody("Set Name", hybrid_bodies)    — find a geometric set by name
    #   hybrid_bodies.add()                            — add a new geometric set
    #   part.in_work_object = <hybrid_body>            — set the active geometric set
    #   hybrid_shape_factory.add_new_*()               — create hybrid shape features
    #   part.update()                                  — update after creating geometry
    #
    # For scripts that write files, build the output path alongside the document:
    #   doc_name = part_document.name.removesuffix('.CATPart')
    #   output_path = str(Path(str(part_document.path())).parent / (doc_name + "_output.csv"))
    #
    # File I/O error handling:
    #   try:
    #       with open(output_path, "w") as f:
    #           f.write(...)
    #   except PermissionError:
    #       print("Error: Permission denied. Is the file already open in another program?")
    #   except IOError as e:
    #       print(f"Error: Could not write to file. {e}")
    #   except Exception as e:
    #       print(f"An unexpected error occurred: {e}")

    print("\n\n Completed\n\n")
