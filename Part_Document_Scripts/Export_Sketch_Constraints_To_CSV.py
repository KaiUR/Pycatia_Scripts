'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Export_Sketch_Constraints_To_CSV.py
    Version:        1.1
    Code:           Python3.10.4, Pycatia 0.10.0
    Release:        V5R32
    Purpose:        Export all sketch constraints and dimensions from the active part to a CSV file.
    Author:         Kai-Uwe Rathjen
    Date:           28.05.26
    Description:    This script iterates all sketches in the active part document and exports every
                    constraint to a CSV file. Sketches are found in two locations: solid bodies
                    (body.sketches) and geometric sets (hybrid_body.hybrid_sketches), including
                    nested geometric sets. Each row contains the sketch name, constraint name,
                    constraint type, satisfaction status, and the dimensional value for Distance,
                    Length, Angle, Radius and similar dimensional constraint types. Non-dimensional
                    constraints (Tangency, Parallelism, etc.) are exported with an empty value
                    column. The output file is saved alongside the part document.
    dependencies = [
                    "pycatia",
                    ]
    requirements:   Python >= 3.10
                    pycatia
                    Catia V5 running with an open part document.
                    This script needs an open part document.
    -----------------------------------------------------------------------------------------------------------------------

    Change:         20.07.26 1.1: Import enums from pycatia.enumeration.enums for consistency.

    -----------------------------------------------------------------------------------------------------------------------
'''

#Imports
from pycatia import catia
from pycatia.enumeration.enums import CatConstraintType, CatConstraintStatus
from pycatia.mec_mod_interfaces.part_document import PartDocument
from pathlib import Path

DIMENSIONAL_TYPES = {                                                                                                #Constraint types that carry a meaningful dimension value
    CatConstraintType.catCstTypeDistance,
    CatConstraintType.catCstTypeLength,
    CatConstraintType.catCstTypeAngle,
    CatConstraintType.catCstTypePlanarAngle,
    CatConstraintType.catCstTypeRadius,
    CatConstraintType.catCstTypeMajorRadius,
    CatConstraintType.catCstTypeMinorRadius,
    CatConstraintType.catCstTypeCylinderRadius,
}


def collect_sketches(hybrid_body, sketch_list):
    '''Recursively collect all sketches from a hybrid body and its nested hybrid bodies.'''
    try:
        hb_sketches = hybrid_body.hybrid_sketches                                                                    #Sketches directly in this geometric set
        for i in range(hb_sketches.count):
            sketch_list.append(hb_sketches.item(i + 1))
    except Exception:
        pass

    try:
        sub_bodies = hybrid_body.hybrid_bodies                                                                       #Nested geometric sets
        for i in range(sub_bodies.count):
            collect_sketches(sub_bodies.item(i + 1), sketch_list)                                                    #Recurse into nested geometric set
    except Exception:
        pass


def process_sketch(sketch, rows):
    '''Extract all constraints from a single sketch and append them to rows.'''
    sketch_name = sketch.name

    try:
        constraints = sketch.constraints                                                                              #Constraints collection for this sketch
    except Exception:
        return

    for c_idx in range(constraints.count):
        try:
            constraint  = constraints.item(c_idx + 1)                                                               #Get constraint (1-based)
            cst_name    = constraint.name                                                                            #Constraint name
            cst_type    = CatConstraintType(constraint.type)                                                         #Type as enum
            cst_status  = CatConstraintStatus(constraint.status)                                                     #Status as enum
            type_str    = cst_type.name                                                                              #Enum name as string
            status_str  = cst_status.name                                                                            #Enum name as string

            value_str = ""                                                                                           #Default: no value
            if cst_type in DIMENSIONAL_TYPES:                                                                        #Only read value for dimensional types
                try:
                    value_str = str(round(constraint.dimension.value, 6))                                            #Dimensional value (document units)
                except Exception:
                    value_str = ""                                                                                   #Leave blank if value unreadable

            rows.append((sketch_name, cst_name, type_str, status_str, value_str))
            print(f"  {sketch_name}  {cst_name}  {type_str}  {value_str}")

        except Exception as e:
            print(f"  Warning: Could not read constraint {c_idx + 1} in '{sketch_name}': {e}")


if __name__ == "__main__":
    caa = catia()                                                                                                    #Catia application instance
    active_doc = caa.active_document                                                                                 #Current active document

    if type(active_doc) is not PartDocument:                                                                         #Check that a CATPart is active
        print("A CATPart document must be the active document.")
        exit()

    part_document: PartDocument = active_doc                                                                         #Cast to PartDocument
    part = part_document.part                                                                                        #Current part

    doc_name     = part_document.name.removesuffix('.CATPart')                                                       #Document name without extension
    doc_path_str = str(part_document.path())                                                                         #Full path string
    if doc_path_str == part_document.name:                                                                           #Unsaved document — path() returns just the filename
        output_path = Path.home() / "Downloads" / (doc_name + "_Sketch_Constraints.csv")                            #Fall back to Downloads
    else:
        output_path = Path(doc_path_str).parent / (doc_name + "_Sketch_Constraints.csv")                            #Save alongside document

    all_sketches = []                                                                                                #All sketches found across both locations

    for b_idx in range(part.bodies.count):                                                                           #Sketches inside solid bodies
        body = part.bodies.item(b_idx + 1)
        try:
            body_sketches = body.sketches
            for s_idx in range(body_sketches.count):
                all_sketches.append(body_sketches.item(s_idx + 1))
        except Exception:
            pass

    for hb_idx in range(part.hybrid_bodies.count):                                                                   #Sketches inside geometric sets (recurses nested sets)
        collect_sketches(part.hybrid_bodies.item(hb_idx + 1), all_sketches)

    print(f"\n Found {len(all_sketches)} sketch(es)\n")

    rows = []                                                                                                        #Collected CSV rows
    for sketch in all_sketches:
        process_sketch(sketch, rows)

    print(f"\n Exporting {len(rows)} constraints\n")

    try:
        with open(output_path, "w", encoding="utf-8") as f:                                                          #Write CSV file
            f.write("Sketch Name,Constraint Name,Type,Status,Value\n")                                               #CSV header
            for row in rows:
                f.write(",".join(f'"{col}"' for col in row) + "\n")                                                  #Quote all fields

        print(f"\n\n Completed - saved to: {output_path}\n\n")

    except PermissionError:
        print("Error: Permission denied. Is the output file already open in another program?")
    except IOError as e:
        print(f"Error: Could not write to file. {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
