'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Export_Component_Positions_To_CSV.py
    Version:        1.0
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Export the 3D position of every component instance in the assembly to a CSV.
    Author:         Kai-Uwe Rathjen
    Date:           21.05.26
    Description:    This script recurses through the active CATProduct and exports the position
                    matrix of every component instance. The position is the full 4x3 placement matrix
                    stored as: X/Y/Z-axis direction cosines (9 values) and the translation vector
                    (TX, TY, TZ). This fully describes the component's orientation and location in the
                    assembly coordinate system. The CSV is saved next to the CATProduct file.
    dependencies = [
                    "pycatia",
                    ]
    requirements:   Python >= 3.10
                    pycatia
                    Catia V5 running with an open CATProduct document.
    -----------------------------------------------------------------------------------------------------------------------

    Change:

    -----------------------------------------------------------------------------------------------------------------------
'''

#Imports
from pycatia import catia, CatWorkModeType
from pycatia.product_structure_interfaces.product_document import ProductDocument
from pathlib import Path

def _collect_positions(product, level, parent_path, rows):
    children = product.products
    for i in range(children.count):
        child       = children.item(i + 1)
        inst_name   = child.name
        part_number = ""
        try:
            part_number = child.reference_product.part_number
        except Exception:
            pass

        full_path = f"{parent_path}/{inst_name}" if parent_path else inst_name

        pos_data = [0.0] * 12
        try:
            pos_data = list(child.position.get_components())                                                       #12-element matrix: [Xx,Xy,Xz, Yx,Yy,Yz, Zx,Zy,Zz, TX,TY,TZ]
        except Exception:
            pass

        rows.append({
            "Level":        level,
            "Path":         full_path,
            "Instance":     inst_name,
            "Part Number":  part_number,
            "Xx": round(pos_data[0],  6), "Xy": round(pos_data[1],  6), "Xz": round(pos_data[2],  6),
            "Yx": round(pos_data[3],  6), "Yy": round(pos_data[4],  6), "Yz": round(pos_data[5],  6),
            "Zx": round(pos_data[6],  6), "Zy": round(pos_data[7],  6), "Zz": round(pos_data[8],  6),
            "TX": round(pos_data[9],  4), "TY": round(pos_data[10], 4), "TZ": round(pos_data[11], 4),
        })

        if child.products.count > 0:                                                                               #Recurse into sub-assemblies
            _collect_positions(child, level + 1, full_path, rows)


if __name__ == "__main__":
    caa = catia()                                                                                                   #Catia application instance
    active_doc = caa.active_document                                                                               #Current open document

    if type(active_doc) is not ProductDocument:
        print("A CATProduct document must be the active document.")
        exit()

    product_document: ProductDocument = active_doc
    product = product_document.product

    product.activate_terminal_node(product.products)                                                               #Activate all terminal nodes
    product.apply_work_mode(CatWorkModeType.DESIGN_MODE)                                                           #Put assembly in design mode

    doc_name     = product_document.name.removesuffix('.CATProduct')
    doc_path_str = str(product_document.path())

    if doc_path_str == product_document.name:
        output_path = Path.home() / "Downloads" / (doc_name + "_ComponentPositions.csv")
    else:
        output_path = Path(doc_path_str).parent / (doc_name + "_ComponentPositions.csv")

    rows = []
    _collect_positions(product, 1, "", rows)

    print(f"\n Found {len(rows)} component instance(s)\n")

    if not rows:
        print("No components found in this assembly.")
        exit()

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("Level,Path,Instance Name,Part Number,"
                    "Xx,Xy,Xz,Yx,Yy,Yz,Zx,Zy,Zz,TX_mm,TY_mm,TZ_mm\n")
            for row in rows:
                indent = "  " * (row['Level'] - 1)
                print(f"  {indent}{row['Instance']}  [{row['TX']}, {row['TY']}, {row['TZ']}]")
                f.write(
                    f"\"{row['Level']}\","
                    f"\"{row['Path']}\","
                    f"\"{row['Instance']}\","
                    f"\"{row['Part Number']}\","
                    f"\"{row['Xx']}\",\"{row['Xy']}\",\"{row['Xz']}\","
                    f"\"{row['Yx']}\",\"{row['Yy']}\",\"{row['Yz']}\","
                    f"\"{row['Zx']}\",\"{row['Zy']}\",\"{row['Zz']}\","
                    f"\"{row['TX']}\",\"{row['TY']}\",\"{row['TZ']}\"\n"
                )

        print(f"\n\n Completed - saved to: {output_path}\n\n")

    except PermissionError:
        print("Error: Permission denied. Is the output file already open in another program?")
    except IOError as e:
        print(f"Error: Could not write to file. {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
