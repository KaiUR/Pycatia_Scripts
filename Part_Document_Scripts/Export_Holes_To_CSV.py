'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Export_Holes_To_CSV.py
    Version:        1.1
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Export all hole features from the active part to a CSV file.
    Author:         Kai-Uwe Rathjen
    Date:           21.05.26
    Description:    This script searches for all Hole features in the active CATPart using CATIA's
                    internal search. For each hole it exports: Name, Body, Type, Diameter (mm),
                    Depth (mm or Through), Thread Description, and XYZ origin (hole anchor point
                    on the face). The CSV is saved next to the CATPart.
    dependencies = [
                    "pycatia",
                    ]
    requirements:   Python >= 3.10
                    pycatia
                    Catia V5 running with an open part document containing hole features.
    -----------------------------------------------------------------------------------------------------------------------

    Change:         22.05.26 1.1: Fixed search query sel → all; use pycatia Hole wrapper and CatHoleType/CatHoleBottomType enums; position from hole.get_origin().

    -----------------------------------------------------------------------------------------------------------------------
'''

#Imports
from pycatia import catia
from pycatia.mec_mod_interfaces.part_document import PartDocument
from pycatia.part_interfaces.hole import Hole
from pycatia.enumeration.enums import CatHoleType, CatHoleBottomType
from pathlib import Path

if __name__ == "__main__":
    caa = catia()                                                                                                   #Catia application instance
    active_doc = caa.active_document                                                                               #Current open document

    if type(active_doc) is not PartDocument:
        print("A CATPart document must be the active document.")
        exit()

    part_document: PartDocument = active_doc

    doc_name     = part_document.name.removesuffix('.CATPart')
    doc_path_str = str(part_document.path())

    if doc_path_str == part_document.name:
        output_path = Path.home() / "Downloads" / (doc_name + "_Holes.csv")
    else:
        output_path = Path(doc_path_str).parent / (doc_name + "_Holes.csv")

    selection = active_doc.selection
    selection.clear()

    print("\n Searching for hole features...\n")

    try:
        selection.search("CATPrtSearch.Hole,all")                                                                  #Search entire document for hole features
    except Exception as e:
        print(f"Error: Hole search failed. {e}")
        exit()

    hole_count = selection.count2
    print(f" Found {hole_count} hole(s)\n")

    if hole_count == 0:
        print("No hole features found in this part.")
        selection.clear()
        exit()

    rows = []

    for i in range(hole_count):
        sel_elem = selection.item2(i + 1)
        hole     = Hole(sel_elem.value.com_object)                                                                 #pycatia Hole wrapper

        hole_name   = ""
        body_name   = ""
        hole_type   = ""
        diameter    = ""
        depth       = ""
        thread_desc = ""
        pos_x = pos_y = pos_z = ""

        try:
            hole_name = hole.name
        except Exception:
            pass

        try:
            body_name = hole.parent.name
        except Exception:
            pass

        try:
            raw_type  = CatHoleType(hole.type).name                                                               #e.g. "catCounterboredHole"
            hole_type = raw_type[3:-4]                                                                             #strip "cat" prefix and "Hole" suffix → "Counterbored"
        except Exception:
            pass

        try:
            diameter = round(hole.diameter.value, 4)
        except Exception:
            pass

        try:
            if hole.bottom_type == CatHoleBottomType.catTrimmedHoleBottom:
                depth = "Through"
            else:
                depth = round(hole.bottom_limit.dimension.value, 4)
        except Exception:
            pass

        try:
            thread_desc = hole.hole_thread_description.value
        except Exception:
            pass

        try:
            origin = hole.get_origin()
            pos_x  = round(origin[0], 4)
            pos_y  = round(origin[1], 4)
            pos_z  = round(origin[2], 4)
        except Exception:
            pass

        rows.append({
            "Name":        hole_name,
            "Body":        body_name,
            "Type":        hole_type,
            "Diameter_mm": diameter,
            "Depth_mm":    depth,
            "Thread":      thread_desc,
            "Origin_X_mm": pos_x,
            "Origin_Y_mm": pos_y,
            "Origin_Z_mm": pos_z,
        })
        print(f"  {hole_name} ({hole_type})  D={diameter}mm  Depth={depth}  [{pos_x}, {pos_y}, {pos_z}]")

    selection.clear()

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("Name,Body,Type,Diameter_mm,Depth_mm,Thread,Origin_X_mm,Origin_Y_mm,Origin_Z_mm\n")
            for row in rows:
                f.write(
                    f"\"{row['Name']}\","
                    f"\"{row['Body']}\","
                    f"\"{row['Type']}\","
                    f"\"{row['Diameter_mm']}\","
                    f"\"{row['Depth_mm']}\","
                    f"\"{row['Thread']}\","
                    f"\"{row['Origin_X_mm']}\","
                    f"\"{row['Origin_Y_mm']}\","
                    f"\"{row['Origin_Z_mm']}\"\n"
                )

        print(f"\n\n Completed - saved to: {output_path}\n\n")

    except PermissionError:
        print("Error: Permission denied. Is the output file already open in another program?")
    except IOError as e:
        print(f"Error: Could not write to file. {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
