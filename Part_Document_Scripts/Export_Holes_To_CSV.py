'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Export_Holes_To_CSV.py
    Version:        1.0
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Export all hole features from the active part to a CSV file.
    Author:         Kai-Uwe Rathjen
    Date:           21.05.26
    Description:    This script searches for all Hole features in the active CATPart using CATIA's
                    internal search. For each hole it exports: Name, Body, Type, Diameter (mm),
                    Depth (mm or Through), Thread Description, and approximate XYZ position (centre
                    of mass of the hole volume via SPA). The CSV is saved next to the CATPart.
                    Note: Position is the CoG of the hole cylindrical volume — for a blind hole this
                    is the midpoint along the depth, not the face entry point.
    dependencies = [
                    "pycatia",
                    ]
    requirements:   Python >= 3.10
                    pycatia
                    Catia V5 running with an open part document containing hole features.
    -----------------------------------------------------------------------------------------------------------------------

    Change:

    -----------------------------------------------------------------------------------------------------------------------
'''

#Imports
from pycatia import catia
from pycatia.mec_mod_interfaces.part_document import PartDocument
from pycatia.space_analyses_interfaces.spa_workbench import SPAWorkbench
from pathlib import Path

HOLE_TYPES = {                                                                                                     #CatHoleType enum to human-readable string
    0: "Simple",
    1: "Tapered",
    2: "Counterbored",
    3: "Countersunk",
    4: "Counterdrilled",
}

BOTTOM_TYPES = {                                                                                                   #CatHoleBottomType enum to human-readable string
    0: "FlatBottom",
    1: "VBottom",
    2: "ThruHole",
}

if __name__ == "__main__":
    caa = catia()                                                                                                   #Catia application instance
    active_doc = caa.active_document                                                                               #Current open document

    if not type(active_doc) is PartDocument:
        print("A CATPart document must be the active document.")
        exit()

    part_document: PartDocument = active_doc
    part = part_document.part

    doc_name    = part_document.name.removesuffix('.CATPart')
    doc_path_str = str(part_document.path())

    if doc_path_str == part_document.name:
        output_path = Path.home() / "Downloads" / (doc_name + "_Holes.csv")
    else:
        output_path = Path(doc_path_str).parent / (doc_name + "_Holes.csv")

    spa = SPAWorkbench(active_doc.com_object)                                                                      #SPA workbench for position measurement

    selection = active_doc.selection
    selection.clear()

    print("\n Searching for hole features...\n")

    try:
        selection.search("CATPrtSearch.Hole,sel")                                                                  #Find all holes in the part
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
        hole_com = sel_elem.value.com_object                                                                       #Hole COM object

        hole_name  = ""
        body_name  = ""
        hole_type  = ""
        diameter   = ""
        depth      = ""
        thread_desc = ""
        pos_x = pos_y = pos_z = ""

        try:
            hole_name = hole_com.Name
        except Exception:
            pass

        try:
            body_name = hole_com.Parent.Name
        except Exception:
            pass

        try:
            hole_type = HOLE_TYPES.get(hole_com.Type, f"Type {hole_com.Type}")
        except Exception:
            pass

        try:
            diameter = round(hole_com.Diameter.Value, 4)
        except Exception:
            pass

        try:
            bottom_type_val = hole_com.BottomType
            if BOTTOM_TYPES.get(bottom_type_val) == "ThruHole":
                depth = "Through"
            else:
                depth = round(hole_com.Depth.Value, 4)
        except Exception:
            pass

        try:
            thread_desc = hole_com.ThreadDescription
        except Exception:
            pass

        try:
            hole_ref = part.create_reference_from_object(sel_elem.value)
            meas     = spa.get_measurable(hole_ref)
            cog      = [0.0, 0.0, 0.0]
            meas.GetCOGPosition(cog)
            pos_x = round(cog[0], 4)
            pos_y = round(cog[1], 4)
            pos_z = round(cog[2], 4)
        except Exception:
            pass

        rows.append({
            "Name":    hole_name,
            "Body":    body_name,
            "Type":    hole_type,
            "Diameter_mm": diameter,
            "Depth_mm":    depth,
            "Thread":      thread_desc,
            "CoG_X_mm":    pos_x,
            "CoG_Y_mm":    pos_y,
            "CoG_Z_mm":    pos_z,
        })
        print(f"  {hole_name}  D={diameter}mm  Depth={depth}  [{pos_x}, {pos_y}, {pos_z}]")

    selection.clear()

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("Name,Body,Type,Diameter_mm,Depth_mm,Thread,CoG_X_mm,CoG_Y_mm,CoG_Z_mm\n")
            for row in rows:
                f.write(
                    f"\"{row['Name']}\","
                    f"\"{row['Body']}\","
                    f"\"{row['Type']}\","
                    f"\"{row['Diameter_mm']}\","
                    f"\"{row['Depth_mm']}\","
                    f"\"{row['Thread']}\","
                    f"\"{row['CoG_X_mm']}\","
                    f"\"{row['CoG_Y_mm']}\","
                    f"\"{row['CoG_Z_mm']}\"\n"
                )

        print(f"\n\n Completed - saved to: {output_path}\n\n")

    except PermissionError:
        print("Error: Permission denied. Is the output file already open in another program?")
    except IOError as e:
        print(f"Error: Could not write to file. {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
