'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    BOM_Export_To_CSV.py
    Version:        1.1
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Export a bill of materials from the active product to a CSV file.
    Author:         Kai-Uwe Rathjen
    Date:           16.05.26
    Description:    This script will recurse through the active CATProduct document tree and export a
                    bill of materials to a CSV file. Each row represents one component instance in the
                    tree. Columns: Level, Part Number, Instance Name, Description, Nomenclature, File Name.
                    The CSV is saved next to the CATProduct file, or in Downloads if unsaved.
    dependencies = [
                    "pycatia",
                    ]
    requirements:   Python >= 3.10
                    pycatia
                    Catia V5 running with an open CATProduct document.
                    This script needs an open CATProduct document.
    -----------------------------------------------------------------------------------------------------------------------

    Change:         16.05.26 1.1: Fix product attribute access — use product.reference_product and pycatia properties.

    -----------------------------------------------------------------------------------------------------------------------
'''

#Imports
from pycatia import catia
from pycatia.product_structure_interfaces.product_document import ProductDocument
from pathlib import Path

def _ref_attr(child, attr):
    try:
        val = getattr(child.reference_product, attr)                                                              #Read from reference product (where PN/description live)
        return val if val else ""
    except Exception:
        try:
            return getattr(child, attr) or ""                                                                     #Fallback to instance level
        except Exception:
            return ""

def collect_bom(product, level, rows):
    children = product.products                                                                                    #Get child products collection
    for i in range(children.count):                                                                               #Loop through children
        child = children.item(i + 1)                                                                              #Get child product
        rows.append({                                                                                              #Append row
            'Level':         level,
            'Part Number':   _ref_attr(child, 'part_number'),
            'Instance Name': child.name,
            'Description':   _ref_attr(child, 'definition'),
            'Nomenclature':  _ref_attr(child, 'nomenclature'),
            'File Name':     child.file_name,
        })
        if child.products.count > 0:                                                                              #Recurse into sub-assemblies
            collect_bom(child, level + 1, rows)

if __name__ == "__main__":
    caa = catia()                                                                                                  #Catia application instance
    active_doc = caa.active_document                                                                               #Current open document

    if not type(active_doc) is ProductDocument:                                                                   #Check if product document
        print("A CATProduct document must be the active document.")
        exit()

    product_document: ProductDocument = active_doc
    product = product_document.product                                                                             #Get root product

    doc_name = product_document.name.removesuffix('.CATProduct')                                                  #Document name without extension
    doc_path_str = str(product_document.path())                                                                   #Full file path as string

    if doc_path_str == product_document.name:                                                                     #Unsaved product — use Downloads
        output_path = Path.home() / "Downloads" / (doc_name + "_BOM.csv")
    else:
        output_path = Path(doc_path_str).parent / (doc_name + "_BOM.csv")                                        #Next to the CATProduct file

    rows = []
    collect_bom(product, 1, rows)                                                                                  #Collect all BOM data

    print(f"\n Found {len(rows)} component instances\n")

    try:
        with open(output_path, "w", encoding="utf-8") as f:                                                       #Open output file
            f.write("Level,Part Number,Instance Name,Description,Nomenclature,File Name\n")                       #CSV header
            for row in rows:                                                                                       #Write each row
                indent = "  " * (row['Level'] - 1)
                f.write(
                    f"\"{row['Level']}\","
                    f"\"{row['Part Number']}\","
                    f"\"{row['Instance Name']}\","
                    f"\"{row['Description']}\","
                    f"\"{row['Nomenclature']}\","
                    f"\"{row['File Name']}\"\n"
                )
                print(f"  {indent}{row['Part Number']} — {row['Instance Name']}")                                  #Print progress

        print(f"\n\n Completed - saved to: {output_path}\n\n")

    except PermissionError:
        print("Error: Permission denied. Is the output file already open in another program?")
    except IOError as e:
        print(f"Error: Could not write to file. {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
