'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Export_Curve_Lengths_Surface_Areas_To_CSV.py
    Version:        1.0
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Export curve lengths and surface areas from a geometric set to a CSV file.
    Author:         Kai-Uwe Rathjen
    Date:           16.05.26
    Description:    This script will ask the user to select a geometric set. It will iterate through all
                    hybrid shapes (recursively through child sets) and use the CATIA SPA workbench to
                    measure each shape. Curves and lines report length (mm). Surfaces report area (mm2).
                    Points are listed with N/A. Results are exported to a CSV file next to the CATPart.
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
from pycatia.mec_mod_interfaces.hybrid_body import HybridBody
from pathlib import Path

GEO_TYPE_NAMES = {1: 'Point', 2: 'Curve', 3: 'Line', 4: 'Circle', 5: 'Surface'}

def measure_shapes(hb, part, hybrid_shape_factory, spa, rows, geo_set_path):
    shapes = hb.hybrid_shapes
    for i in range(shapes.count):
        shape = shapes.item(i + 1)
        shape_name = shape.name
        geo_type = hybrid_shape_factory.get_geometrical_feature_type(shape)
        geo_type_name = GEO_TYPE_NAMES.get(geo_type, f'Unknown({geo_type})')

        length = 'N/A'
        area   = 'N/A'

        try:
            shape_ref = part.create_reference_from_object(shape)
            meas = spa.GetMeasurable(shape_ref.com_object)

            if geo_type in (2, 3, 4):                                                                             #Curve, Line, Circle — measure length
                length = round(meas.Length, 6)
            elif geo_type == 5:                                                                                    #Surface — measure area (SPA returns m², convert to mm²)
                area = round(meas.Area * 1e6, 3)
        except Exception as e:
            print(f"  Warning: could not measure '{shape_name}': {e}")

        rows.append({
            'Geometric Set': geo_set_path,
            'Name':          shape_name,
            'Type':          geo_type_name,
            'Length_mm':     length,
            'Area_mm2':      area,
        })

    for i in range(hb.hybrid_bodies.count):                                                                       #Recurse into child sets
        child_hb = HybridBody(hb.hybrid_bodies.item(i + 1).com_object)
        child_path = f"{geo_set_path}/{child_hb.name}"
        measure_shapes(child_hb, part, hybrid_shape_factory, spa, rows, child_path)

if __name__ == "__main__":
    caa = catia()
    active_doc = caa.active_document

    object_filter = ("HybridBody",)
    selectionSet = caa.active_document.selection
    status = selectionSet.select_element3(object_filter, "Select geometric set to measure", False, 2, False)
    if status != "Normal":
        print("You must select a geometric set")
        exit()

    selected_item = selectionSet.item(1)

    if type(active_doc) is PartDocument:
        part = active_doc.part
        part_document: PartDocument = active_doc
    else:
        leaf_product = selected_item.com_object.LeafProduct
        part_document = PartDocument(leaf_product.ReferenceProduct.Parent)
        part = part_document.part

    hybrid_shape_factory = part.hybrid_shape_factory
    source_hb = HybridBody(selected_item.value.com_object)
    source_name = source_hb.name

    doc_path_str = str(part_document.path())
    doc_name = part_document.name.removesuffix('.CATPart')

    if doc_path_str == part_document.name:
        output_path = Path.home() / "Downloads" / (doc_name + f"_{source_name}_Measurements.csv")
    else:
        output_path = Path(doc_path_str).parent / (doc_name + f"_{source_name}_Measurements.csv")

    spa = active_doc.com_object.GetWorkbench("SPAWorkbench")                                                      #SPA workbench for measurement

    print(f"\n Measuring shapes in '{source_name}'...\n")

    rows = []
    measure_shapes(source_hb, part, hybrid_shape_factory, spa, rows, source_name)

    print(f"\n Found {len(rows)} shape(s)")

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("Geometric Set,Name,Type,Length_mm,Area_mm2\n")
            for row in rows:
                f.write(
                    f"\"{row['Geometric Set']}\","
                    f"\"{row['Name']}\","
                    f"\"{row['Type']}\","
                    f"\"{row['Length_mm']}\","
                    f"\"{row['Area_mm2']}\"\n"
                )

        print(f"\n\n Completed - saved to: {output_path}\n\n")

    except PermissionError:
        print("Error: Permission denied. Is the output file already open?")
    except IOError as e:
        print(f"Error: Could not write to file. {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
