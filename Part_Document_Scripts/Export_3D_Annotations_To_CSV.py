'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Export_3D_Annotations_To_CSV.py
    Version:        1.0
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Export all 3D annotations (FTA) from the active part to a CSV file.
    Author:         Kai-Uwe Rathjen
    Date:           21.05.26
    Description:    This script accesses the Functional Tolerancing and Annotation (FTA) data
                    in the active CATPart. It iterates all Annotation Sets and their Annotations,
                    exporting each annotation's name, type, and text content to a CSV file.
                    The CSV is saved next to the CATPart. Requires the FTA/3D Tolerancing workbench
                    licence. If no annotation sets are present, the script exits cleanly.
    dependencies = [
                    "pycatia",
                    ]
    requirements:   Python >= 3.10
                    pycatia
                    Catia V5 running with an open part document.
                    CATIA FTA (3D Tolerancing & Annotation) workbench licence recommended.
    -----------------------------------------------------------------------------------------------------------------------

    Change:

    -----------------------------------------------------------------------------------------------------------------------
'''

#Imports
from pycatia import catia
from pycatia.mec_mod_interfaces.part_document import PartDocument
from pathlib import Path

if __name__ == "__main__":
    caa = catia()                                                                                                   #Catia application instance
    active_doc = caa.active_document                                                                               #Current open document

    if not type(active_doc) is PartDocument:
        print("A CATPart document must be the active document.")
        exit()

    part_document: PartDocument = active_doc
    part = part_document.part

    doc_name     = part_document.name.removesuffix('.CATPart')
    doc_path_str = str(part_document.path())

    if doc_path_str == part_document.name:
        output_path = Path.home() / "Downloads" / (doc_name + "_3DAnnotations.csv")
    else:
        output_path = Path(doc_path_str).parent / (doc_name + "_3DAnnotations.csv")

    part_com = part.com_object                                                                                     #Part COM object for FTA access

    rows = []

    try:
        annotation_sets = part_com.AnnotationSets                                                                  #FTA annotation sets collection
        set_count = annotation_sets.Count
        print(f"\n Found {set_count} annotation set(s)\n")

        for si in range(set_count):
            ann_set     = annotation_sets.Item(si + 1)
            set_name    = ""
            try:
                set_name = ann_set.Name
            except Exception:
                set_name = f"Set {si + 1}"

            print(f"  Processing set: {set_name}")

            try:
                annotations = ann_set.Annotations
                ann_count   = annotations.Count

                for ai in range(ann_count):
                    ann      = annotations.Item(ai + 1)
                    ann_name = ""
                    ann_type = ""
                    ann_text = ""

                    try:
                        ann_name = ann.Name
                    except Exception:
                        ann_name = f"Ann {ai + 1}"

                    try:
                        ann_type = str(type(ann).__name__)
                    except Exception:
                        pass

                    try:
                        ann_type = ann.com_object.GetType().Name
                    except Exception:
                        pass

                    for text_attr in ["Text", "TextString", "Value", "Content"]:                                   #Try common text attribute names
                        try:
                            val = getattr(ann.com_object, text_attr)
                            if val:
                                ann_text = str(val)
                                break
                        except Exception:
                            continue

                    rows.append({
                        "Set":  set_name,
                        "Name": ann_name,
                        "Type": ann_type,
                        "Text": ann_text,
                    })
                    print(f"    {ann_name} ({ann_type}): {ann_text[:60]}")

            except Exception as e:
                print(f"  Warning: Could not read annotations in set '{set_name}': {e}")

    except AttributeError:
        print("This part has no AnnotationSets. FTA data may not be present.")
        exit()
    except Exception as e:
        print(f"Error accessing FTA data: {e}")
        print("Ensure the FTA workbench is available and the part contains 3D annotations.")
        exit()

    if not rows:
        print("No annotations found to export.")
        exit()

    print(f"\n Exporting {len(rows)} annotation(s)\n")

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("Annotation Set,Name,Type,Text\n")
            for row in rows:
                text_escaped = row['Text'].replace('"', '""')
                f.write(
                    f"\"{row['Set']}\","
                    f"\"{row['Name']}\","
                    f"\"{row['Type']}\","
                    f"\"{text_escaped}\"\n"
                )

        print(f"\n\n Completed - saved to: {output_path}\n\n")

    except PermissionError:
        print("Error: Permission denied. Is the output file already open in another program?")
    except IOError as e:
        print(f"Error: Could not write to file. {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
