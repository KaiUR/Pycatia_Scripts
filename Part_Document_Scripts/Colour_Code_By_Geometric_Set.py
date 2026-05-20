'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Colour_Code_By_Geometric_Set.py
    Version:        1.0
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Assign a unique colour to each child geometric set inside a selected parent geometric set.
    Author:         Kai-Uwe Rathjen
    Date:           20.05.26
    Description:    This script asks the user to select a parent geometric set. Each direct child geometric set
                    is assigned a visually distinct colour from an HSV palette (evenly-spaced hues at 80%
                    saturation and 90% brightness). The colour is set directly on every hybrid shape inside
                    each child set (recursively including nested child sets). Shapes directly in the parent
                    set (not in a child) are left unchanged. Useful for visually debugging or auditing a
                    complex part tree.
    dependencies = [
                    "pycatia",
                    ]
    requirements:   Python >= 3.10
                    pycatia
                    Catia V5 running with an open part document containing nested geometric sets.
    -----------------------------------------------------------------------------------------------------------------------
'''

import colorsys
from pycatia import catia
from pycatia.mec_mod_interfaces.hybrid_body import HybridBody
from pycatia.mec_mod_interfaces.part_document import PartDocument

def make_palette(n):
    palette = []
    for i in range(n):
        h = i / n
        r, g, b = colorsys.hsv_to_rgb(h, 0.80, 0.90)
        palette.append((int(r * 255), int(g * 255), int(b * 255)))
    return palette

def collect_shapes(hb, result):
    shapes = hb.hybrid_shapes
    for i in range(shapes.count):
        result.append(shapes.item(i + 1))
    for i in range(hb.hybrid_bodies.count):                                                                      # Recurse into child sets
        collect_shapes(hb.hybrid_bodies.item(i + 1), result)

if __name__ == "__main__":
    caa = catia()
    active_doc   = caa.active_document
    selectionSet = caa.active_document.selection

    status = selectionSet.select_element3(("HybridBody",), "Select the parent geometric set to colour-code", False, 2, False)
    if status != "Normal":
        print("Selection cancelled.")
        exit()

    selected_item = selectionSet.item(1)

    if type(active_doc) is PartDocument:
        part = active_doc.part
    else:
        leaf_product = selected_item.com_object.LeafProduct
        part = PartDocument(leaf_product.ReferenceProduct.Parent).part

    parent_hb    = HybridBody(selected_item.value.com_object)
    child_bodies = parent_hb.hybrid_bodies
    n            = child_bodies.count

    if n == 0:
        print(f"'{parent_hb.name}' has no child geometric sets to colour-code.")
        exit()

    palette = make_palette(n)

    print(f"\n Colour-coding {n} geometric set(s) inside '{parent_hb.name}'\n")

    for i in range(n):
        child_hb = child_bodies.item(i + 1)
        r, g, b  = palette[i]

        shapes = []
        collect_shapes(child_hb, shapes)                                                                         # Gather all shapes recursively within this child set

        if shapes:
            selectionSet.clear()
            for shape in shapes:
                selectionSet.add(shape)
            selectionSet.vis_properties.set_real_color(r, g, b, 0)                                              # Set colour directly on each shape

        print(f"  '{child_hb.name}' -> RGB({r}, {g}, {b})  ({len(shapes)} shape(s))")

    part.update()
    print(f"\n\n Completed - {n} geometric set(s) colour-coded in '{parent_hb.name}'\n\n")
