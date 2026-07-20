'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Select_By_Colour.py
    Version:        1.1
    Code:           Python3.10.4, Pycatia 0.10.0
    Release:        V5R32
    Purpose:        Select all elements in a geometric set that share the same colour as a chosen source element.
    Author:         Kai-Uwe Rathjen
    Date:           20.05.26
    Description:    This script asks the user to select a geometric set to search within, then select a source
                    element whose colour to match. Every hybrid shape in the set (recursively including child
                    sets) whose real colour exactly matches the source element's real colour is added to the
                    CATIA selection. Elements with an undefined colour are skipped. Pairs naturally with
                    Copy_Name_and_Colour.py as a "find what I already coloured" tool.
    dependencies = [
                    "pycatia",
                    ]
    requirements:   Python >= 3.10
                    pycatia
                    Catia V5 running with an open part document containing a geometric set.
    -----------------------------------------------------------------------------------------------------------------------

    Change:         20.07.26 1.1: Use CatVisPropertyStatus enum instead of local CatVisPropertyStatus.catVisPropertyDefined constant.

    -----------------------------------------------------------------------------------------------------------------------
'''

from pycatia import catia
from pycatia.mec_mod_interfaces.hybrid_body import HybridBody
from pycatia.mec_mod_interfaces.part_document import PartDocument
from pycatia.enumeration.enums import CatVisPropertyStatus

def collect_shapes(hb, result):
    shapes = hb.hybrid_shapes
    for i in range(shapes.count):
        result.append(shapes.item(i + 1))
    for i in range(hb.hybrid_bodies.count):                                                                      # Recurse into child sets
        collect_shapes(hb.hybrid_bodies.item(i + 1), result)

if __name__ == "__main__":
    caa = catia()
    active_doc    = caa.active_document
    object_filter = ("AnyObject",)
    selectionSet  = caa.active_document.selection

    # --- Step 1: select geometric set to search ---
    status = selectionSet.select_element3(("HybridBody",), "Select geometric set to search for matching colour", False, 2, False)
    if status != "Normal":
        print("Selection cancelled.")
        exit()

    selected_item = selectionSet.item(1)

    if type(active_doc) is PartDocument:
        part = active_doc.part
    else:
        leaf_product = selected_item.com_object.LeafProduct
        part = PartDocument(leaf_product.ReferenceProduct.Parent).part

    search_hb = HybridBody(selected_item.value.com_object)

    # --- Step 2: select source element to read colour from ---
    selectionSet.clear()
    status = selectionSet.select_element2(object_filter, "Select an element whose colour to match", False)
    if status != "Normal":
        print("Selection cancelled.")
        exit()

    source_val = selectionSet.item(1).value
    source_obj = source_val.parent if "Selection_" in source_val.name else source_val

    selectionSet.clear()
    selectionSet.add(source_obj)
    colour_result = selectionSet.vis_properties.get_real_color()                                                  # (status, r, g, b)

    if colour_result[0] != CatVisPropertyStatus.catVisPropertyDefined:
        print("Could not read a defined colour from the selected element.")
        exit()

    src_r, src_g, src_b = colour_result[1], colour_result[2], colour_result[3]

    # Collect all shapes in the set recursively
    all_shapes = []
    collect_shapes(search_hb, all_shapes)

    # Compare each shape's colour against source
    matches = []
    for shape in all_shapes:
        selectionSet.clear()
        selectionSet.add(shape)
        shape_colour = selectionSet.vis_properties.get_real_color()                                               # (status, r, g, b)
        if shape_colour[0] == CatVisPropertyStatus.catVisPropertyDefined:
            if shape_colour[1] == src_r and shape_colour[2] == src_g and shape_colour[3] == src_b:
                matches.append(shape)

    if not matches:
        print(f"No elements with colour RGB({src_r}, {src_g}, {src_b}) found in '{search_hb.name}'.")
        selectionSet.clear()
        exit()

    # Leave matching elements selected in CATIA
    selectionSet.clear()
    for shape in matches:
        selectionSet.add(shape)

    print(f"Selected {len(matches)} element(s) with colour RGB({src_r}, {src_g}, {src_b}) in '{search_hb.name}'.")
