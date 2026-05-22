'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    List_Properties_To_CSV.py
    Version:        1.1
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Export name, type and visual properties of all elements in a geometric set to a CSV file.
    Author:         Kai-Uwe Rathjen
    Date:           20.05.26
    Description:    This script asks the user to select a geometric set. It iterates all hybrid shapes
                    recursively through all child sets and records the name, geometry type, geometric set path,
                    RGB colour, line weight index, line type index and opacity for each element. Results are
                    saved to a CSV file next to the CATPart (or in the Downloads folder if unsaved). Useful
                    for auditing visual styles, generating a style sheet, or comparing geometry properties
                    across parts.
    dependencies = [
                    "pycatia",
                    ]
    requirements:   Python >= 3.10
                    pycatia
                    Catia V5 running with an open part document containing a geometric set.
    -----------------------------------------------------------------------------------------------------------------------

    Change:         1.1 - Replaced hardcoded CAT_VIS_PROPERTY_DEFINED constant with
                          CatVisPropertyStatus.catVisPropertyDefined enum. Replaced
                          GEO_TYPE_NAMES dict with GeometricalFeatureType enum lookup
                          (adds Plane and Solid Volume coverage, unknown types handled).

    -----------------------------------------------------------------------------------------------------------------------
'''

from pathlib import Path
from pycatia import catia
from pycatia.mec_mod_interfaces.hybrid_body import HybridBody
from pycatia.mec_mod_interfaces.part_document import PartDocument
from pycatia.enumeration.enums import CatVisPropertyStatus, GeometricalFeatureType

LINE_WEIGHT_MAP = {1: '0.13mm', 2: '0.35mm', 3: '0.7mm', 4: '1.0mm',
                   5: '1.4mm',  6: '2.0mm',  7: '2.3mm', 8: '2.6mm'}                                           # Indices 9-55 are custom slots that default to 0.13mm

LINE_TYPE_MAP = {1: 'Solid', 2: 'Dashed', 3: 'Long Dash', 4: 'Dash-Dot',
                 5: 'Dash-Double Dot', 6: 'Dotted', 7: 'Long Dash-Dot'}                                         # Indices beyond 7 are custom line type slots

OPACITY_MAP = {255: '100%', 191: '75%', 127: '50%', 63: '25%', 0: '0%'}                                        # CATIA's five discrete transparency levels

def map_line_type(index):
    return LINE_TYPE_MAP.get(index, str(index))                                                                   # Fallback to raw integer for custom line type slots

def map_line_weight(index):
    if index in LINE_WEIGHT_MAP:
        return LINE_WEIGHT_MAP[index]
    if 9 <= index <= 55:
        return '0.13mm'
    return str(index)                                                                                             # Fallback for unexpected values

def map_opacity(value):
    return OPACITY_MAP.get(value, str(value))                                                                    # Fallback to raw integer if not a standard level

def collect_rows(hb, rows, sel, factory, geo_set_path):
    shapes = hb.hybrid_shapes
    for i in range(shapes.count):
        shape     = shapes.item(i + 1)
        geo_type  = factory.get_geometrical_feature_type(shape)
        try:
            type_name = GeometricalFeatureType(geo_type).name.replace('_', ' ')
        except ValueError:
            type_name = f'Unknown({geo_type})'

        sel.clear()
        sel.add(shape)
        vis = sel.vis_properties

        colour    = vis.get_real_color()       # (status, r, g, b)
        width     = vis.get_real_width()       # (status, width_index)
        line_type = vis.get_real_line_type()   # (status, line_type_index)
        opacity   = vis.get_real_opacity()     # (status, opacity)

        rows.append({
            'Geometric Set': geo_set_path,
            'Name':          shape.name,
            'Type':          type_name,
            'R':             colour[1]    if colour[0]    == CatVisPropertyStatus.catVisPropertyDefined else 'N/A',
            'G':             colour[2]    if colour[0]    == CatVisPropertyStatus.catVisPropertyDefined else 'N/A',
            'B':             colour[3]    if colour[0]    == CatVisPropertyStatus.catVisPropertyDefined else 'N/A',
            'Line Weight':   map_line_weight(width[1])   if width[0]     == CatVisPropertyStatus.catVisPropertyDefined else 'N/A',
            'Line Type':     map_line_type(line_type[1]) if line_type[0] == CatVisPropertyStatus.catVisPropertyDefined else 'N/A',
            'Opacity':       map_opacity(opacity[1])    if opacity[0]   == CatVisPropertyStatus.catVisPropertyDefined else 'N/A',
        })

    for i in range(hb.hybrid_bodies.count):                                                                      # Recurse into child sets
        child      = hb.hybrid_bodies.item(i + 1)
        child_path = f"{geo_set_path}/{child.name}"
        collect_rows(child, rows, sel, factory, child_path)

if __name__ == "__main__":
    caa = catia()
    active_doc   = caa.active_document
    selectionSet = caa.active_document.selection

    status = selectionSet.select_element3(("HybridBody",), "Select geometric set to list properties", False, 2, False)
    if status != "Normal":
        print("You must select a geometric set.")
        exit()

    selected_item = selectionSet.item(1)

    if type(active_doc) is PartDocument:
        part          = active_doc.part
        part_document = active_doc
    else:
        leaf_product  = selected_item.com_object.LeafProduct
        part_document = PartDocument(leaf_product.ReferenceProduct.Parent)
        part          = part_document.part

    factory   = part.hybrid_shape_factory
    source_hb = HybridBody(selected_item.value.com_object)
    set_name  = source_hb.name

    doc_path_str = str(part_document.path())
    doc_name     = part_document.name.removesuffix('.CATPart')

    if doc_path_str == part_document.name:                                                                       # Unsaved document — write to Downloads
        output_path = Path.home() / "Downloads" / f"{doc_name}_{set_name}_Properties.csv"
    else:
        output_path = Path(doc_path_str).parent / f"{doc_name}_{set_name}_Properties.csv"

    print(f"\n Reading properties from '{set_name}'...\n")

    rows = []
    collect_rows(source_hb, rows, selectionSet, factory, set_name)

    if not rows:
        print(f"No shapes found in '{set_name}'.")
        exit()

    print(f"\n Found {len(rows)} shape(s)")

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("Geometric Set,Name,Type,R,G,B,Line Weight,Line Type,Opacity\n")
            for row in rows:
                f.write(
                    f"\"{row['Geometric Set']}\","
                    f"\"{row['Name']}\","
                    f"\"{row['Type']}\","
                    f"\"{row['R']}\","
                    f"\"{row['G']}\","
                    f"\"{row['B']}\","
                    f"\"{row['Line Weight']}\","
                    f"\"{row['Line Type']}\","
                    f"\"{row['Opacity']}\"\n"
                )
        print(f"\n\n Completed - saved to: {output_path}\n\n")

    except PermissionError:
        print("Error: Permission denied. Is the output file already open?")
    except IOError as e:
        print(f"Error: Could not write to file. {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
