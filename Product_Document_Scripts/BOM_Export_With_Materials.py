'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    BOM_Export_With_Materials.py
    Version:        1.1
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Export a bill of materials with material information from the active product.
    Author:         Kai-Uwe Rathjen
    Date:           21.05.26
    Description:    This script recurses through the active CATProduct and exports a full bill of
                    materials enriched with material data. For each part in the assembly it reads the
                    applied material name and density via the Product Analyse interface. Columns:
                    Level, Part Number, Instance Name, Description, Nomenclature, Mass (kg),
                    Material Name, File Name. The CSV is saved next to the CATProduct.
                    Note: Mass and Material require a material to be applied to the CATPart body.
    dependencies = [
                    "pycatia",
                    ]
    requirements:   Python >= 3.10
                    pycatia
                    Catia V5 running with an open CATProduct document.
    -----------------------------------------------------------------------------------------------------------------------

    Change:         1.1 - Replaced non-existent analyze.material_name with MaterialManager
                          via part.get_item("CATMatManagerVBExt"). Checks part-level material
                          first then main body; labels result "(Part)" or "(Body)".

    -----------------------------------------------------------------------------------------------------------------------
'''

#Imports
from pycatia import catia, CatWorkModeType
from pycatia.product_structure_interfaces.product_document import ProductDocument
from pycatia.mec_mod_interfaces.part_document import PartDocument
from pycatia.cat_mat_interfaces.material_manager import MaterialManager
from pathlib import Path

def _ref_attr(child, attr):
    try:
        val = getattr(child.reference_product, attr)
        return val if val else ""
    except Exception:
        try:
            return getattr(child, attr) or ""
        except Exception:
            return ""


def _get_mass(child):
    try:
        return round(child.analyze.mass, 6)
    except Exception:
        return "N/A"


def _get_material_name(child):
    try:
        ref      = child.reference_product
        part_doc = PartDocument(ref.parent.com_object)                                                             #Parent of reference product is the PartDocument
        part     = part_doc.part
        mm       = MaterialManager(part.get_item("CATMatManagerVBExt").com_object)

        try:
            name = mm.get_material_on_part(part).name                                                             #Material applied at part level
            if name:
                return f"{name} (Part)"
        except Exception:
            pass

        try:
            name = mm.get_material_on_body(part.main_body).name                                                   #Material applied to PartBody
            if name:
                return f"{name} (Body)"
        except Exception:
            pass

    except Exception:
        pass
    return "N/A"


def collect_bom(product, level, rows):
    children = product.products
    for i in range(children.count):
        child = children.item(i + 1)

        rows.append({
            "Level":         level,
            "Part Number":   _ref_attr(child, 'part_number'),
            "Instance Name": child.name,
            "Description":   _ref_attr(child, 'definition'),
            "Nomenclature":  _ref_attr(child, 'nomenclature'),
            "Mass_kg":       _get_mass(child),
            "Material":      _get_material_name(child),
            "File Name":     child.file_name,
        })

        if child.products.count > 0:
            collect_bom(child, level + 1, rows)


if __name__ == "__main__":
    caa = catia()                                                                                                   #Catia application instance
    active_doc = caa.active_document                                                                               #Current open document

    if not type(active_doc) is ProductDocument:
        print("A CATProduct document must be the active document.")
        exit()

    product_document: ProductDocument = active_doc
    product = product_document.product

    product.activate_terminal_node(product.products)                                                               #Activate all terminal nodes
    product.apply_work_mode(CatWorkModeType.DESIGN_MODE)                                                           #Put product in design mode

    doc_name     = product_document.name.removesuffix('.CATProduct')
    doc_path_str = str(product_document.path())

    if doc_path_str == product_document.name:
        output_path = Path.home() / "Downloads" / (doc_name + "_BOM_Materials.csv")
    else:
        output_path = Path(doc_path_str).parent / (doc_name + "_BOM_Materials.csv")

    rows = []
    collect_bom(product, 1, rows)

    print(f"\n Found {len(rows)} component instance(s)\n")

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("Level,Part Number,Instance Name,Description,Nomenclature,Mass_kg,Material,File Name\n")
            for row in rows:
                indent = "  " * (row['Level'] - 1)
                print(f"  {indent}{row['Part Number']} — {row['Instance Name']}  [{row['Material']}  {row['Mass_kg']} kg]")
                f.write(
                    f"\"{row['Level']}\","
                    f"\"{row['Part Number']}\","
                    f"\"{row['Instance Name']}\","
                    f"\"{row['Description']}\","
                    f"\"{row['Nomenclature']}\","
                    f"\"{row['Mass_kg']}\","
                    f"\"{row['Material']}\","
                    f"\"{row['File Name']}\"\n"
                )

        print(f"\n\n Completed - saved to: {output_path}\n\n")

    except PermissionError:
        print("Error: Permission denied. Is the output file already open in another program?")
    except IOError as e:
        print(f"Error: Could not write to file. {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
