'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Export_Geometric_Set_Structure_To_CSV.py
    Version:        1.0
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Export the full geometric set tree and its contents to a CSV file.
    Author:         Kai-Uwe Rathjen
    Date:           06.05.26
    Description:    This script will export the full structure of all geometric sets in the active part to a CSV file.
                    For each geometric set the script writes the set name, its depth in the tree, and the name and
                    type of every element inside it. The file is saved in the same folder as the part document.
                    Useful for auditing complex parts and tracking geometry changes.
    dependencies = [
                    "pycatia",
                    ]
    requirements:   Python >= 3.10
                    pycatia
                    Catia V5 running with an open part document.
                    This script needs an open part document.
    -----------------------------------------------------------------------------------------------------------------------

    Change:

    -----------------------------------------------------------------------------------------------------------------------
'''

#Imports
from pycatia import catia
from pycatia.mec_mod_interfaces.part_document import PartDocument
from pathlib import Path

'''
    This function recursively walks all geometric sets and writes their contents to the output file.

    Inputs:
        hybrid_bodies       The collection of geometric sets to walk
        output_file         The open file object to write to
        depth               The current depth in the tree (used for indentation prefix)

    output:
        None - writes directly to output_file
'''
def write_hybrid_body_tree(hybrid_bodies, output_file, depth=0):
    prefix = "  " * depth                                                                                       #Build indentation prefix for tree depth

    for index in range(hybrid_bodies.count):                                                                    #Loop through geometric sets at this level
        hb = hybrid_bodies.item(index + 1)                                                                      #Get geometric set

        output_file.write(f"\"{prefix}[GEO SET] {hb.name}\",\"{depth}\",\"\"\n")                               #Write geometric set name with depth

        hybrid_shapes = hb.hybrid_shapes                                                                        #Get all hybrid shapes in this set
        for hs_index in range(hybrid_shapes.count):                                                             #Loop through all hybrid shapes
            hs = hybrid_shapes.item(hs_index + 1)                                                               #Get hybrid shape
            output_file.write(f"\"{prefix}  {hs.name}\",\"{depth + 1}\",\"\"\n")                               #Write shape name

        if hb.hybrid_bodies.count > 0:                                                                          #If there are child geometric sets
            write_hybrid_body_tree(hb.hybrid_bodies, output_file, depth + 1)                                    #Recurse into child sets


if __name__ == "__main__":
    #Anchoring relavent components
    caa = catia()                                                                                               #Catia application instance
    part_document: PartDocument = caa.active_document                                                          #Current open document

    if not type(part_document) is PartDocument:                                                                 #Check if part document
        print("A CATPart document must be the active document.")
        exit()

    part = part_document.part                                                                                   #Current part
    hybrid_bodies = part.hybrid_bodies                                                                          #Get all top level geometric sets

    doc_path = str(part_document.path())                                                                        #Get document path
    doc_name = part_document.name.removesuffix('.CATPart')                                                      #Get document name without extension
    output_path = str(Path(doc_path).parent / (doc_name + "_Geometric_Set_Structure.csv"))                      #Build output file path

    print(f"\n Exporting geometric set structure\n")

    try:
        with open(output_path, "w") as output_file:                                                             #Create output file
            output_file.write("Name,Depth,Notes\n")                                                             #Write CSV header
            write_hybrid_body_tree(hybrid_bodies, output_file, 0)                                               #Walk and write entire tree

        print(f"\n\n Completed - saved to: {output_path}\n\n")

    except PermissionError:
        print(f"Error: Permission denied. Is the output file already open in another program?")
    except IOError as e:
        print(f"Error: Could not write to file. {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
