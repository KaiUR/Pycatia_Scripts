'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Export_Properties_To_CSV.py
    Version:        1.0
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Export document properties and user-defined properties to a CSV file.
    Author:         Kai-Uwe Rathjen
    Date:           21.05.26
    Description:    This script exports the standard file properties (Part Number, Revision, Definition,
                    Nomenclature, Description) and any user-defined custom properties from the active
                    document to a CSV file. Works with CATPart, CATProduct, and CATDrawing documents.
                    The CSV is saved next to the document, or in Downloads if unsaved.
    dependencies = [
                    "pycatia",
                    ]
    requirements:   Python >= 3.10
                    pycatia
                    Catia V5 running with an open document.
    -----------------------------------------------------------------------------------------------------------------------

    Change:

    -----------------------------------------------------------------------------------------------------------------------
'''

#Imports
from pycatia import catia
from pathlib import Path

def _safe_str(value):
    try:
        return str(value) if value else ""
    except Exception:
        return ""

if __name__ == "__main__":
    caa = catia()                                                                                                   #Catia application instance
    active_doc = caa.active_document                                                                               #Current open document

    doc_name_raw = active_doc.name
    doc_path_str = str(active_doc.path())

    if doc_path_str == doc_name_raw:                                                                               #Unsaved document — use Downloads
        output_path = Path.home() / "Downloads" / (doc_name_raw + "_Properties.csv")
    else:
        doc_stem = Path(doc_name_raw).stem
        output_path = Path(doc_path_str).parent / (doc_stem + "_Properties.csv")

    rows = []

    #Read standard product properties via COM
    try:
        prod_com = active_doc.com_object.Product                                                                   #Product COM object (works for Part and Product)

        standard_props = [
            ("Part Number",   "PartNumber"),
            ("Revision",      "Revision"),
            ("Definition",    "Definition"),
            ("Nomenclature",  "Nomenclature"),
            ("Description",   "DescriptionRef"),
        ]

        for label, attr in standard_props:
            try:
                rows.append({"Source": "Standard", "Name": label, "Value": _safe_str(getattr(prod_com, attr))})
            except Exception:
                rows.append({"Source": "Standard", "Name": label, "Value": ""})

    except Exception as e:
        print(f"  Note: Could not read standard product properties ({e})")

    #Read user-defined properties via COM
    try:
        user_props = active_doc.com_object.Product.UserRefProperties                                              #User-defined properties collection

        prop_count = user_props.Count
        print(f"\n Found {prop_count} user-defined property(ies)\n")

        for i in range(prop_count):
            try:
                prop = user_props.Item(i + 1)
                rows.append({
                    "Source": "User",
                    "Name":   _safe_str(prop.Name),
                    "Value":  _safe_str(prop.ValueAsString()),
                })
            except Exception as e:
                print(f"  Warning: Could not read user property {i+1}: {e}")

    except Exception as e:
        print(f"  Note: Could not read user-defined properties ({e})")

    if not rows:
        print("No properties found to export.")
        exit()

    print(f"\n Exporting {len(rows)} properties\n")

    try:
        with open(output_path, "w", encoding="utf-8") as f:                                                       #Open output file
            f.write("Source,Name,Value\n")                                                                        #CSV header
            for row in rows:
                f.write(f"\"{row['Source']}\",\"{row['Name']}\",\"{row['Value']}\"\n")
                print(f"  {row['Source']}: {row['Name']} = {row['Value']}")

        print(f"\n\n Completed - saved to: {output_path}\n\n")

    except PermissionError:
        print("Error: Permission denied. Is the output file already open in another program?")
    except IOError as e:
        print(f"Error: Could not write to file. {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
