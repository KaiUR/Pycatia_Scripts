'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Match_Properties_In_Geometric_Set.py
    Version:        1.0
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Apply the visual properties of a source element to all elements in a selected geometric set.
    Author:         Kai-Uwe Rathjen
    Date:           20.05.26
    Description:    This script asks the user to select a geometric set, then select a source element. The
                    colour, line weight, line type, opacity and point symbol of the source are applied to every
                    hybrid shape inside the geometric set (recursively including all child sets). Useful for
                    making all elements in a set visually consistent in one operation. Names are not changed.
    dependencies = [
                    "pycatia",
                    ]
    requirements:   Python >= 3.10
                    pycatia
                    Catia V5 running with an open part document containing a geometric set.
    -----------------------------------------------------------------------------------------------------------------------

    Change:

    -----------------------------------------------------------------------------------------------------------------------
'''

from pycatia import catia
from pycatia.mec_mod_interfaces.hybrid_body import HybridBody
from pycatia.mec_mod_interfaces.part_document import PartDocument

CAT_VIS_PROPERTY_DEFINED = 0                                                                                     # catVisPropertyDefined

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

    # --- Step 1: select target geometric set ---
    status = selectionSet.select_element3(("HybridBody",), "Select the geometric set to apply properties TO", False, 2, False)
    if status != "Normal":
        print("Selection cancelled.")
        exit()

    selected_item = selectionSet.item(1)

    if type(active_doc) is PartDocument:
        part = active_doc.part
    else:
        leaf_product = selected_item.com_object.LeafProduct
        part = PartDocument(leaf_product.ReferenceProduct.Parent).part

    target_hb = HybridBody(selected_item.value.com_object)

    # --- Step 2: single-select source element ---
    selectionSet.clear()
    status = selectionSet.select_element2(object_filter, "Select the SOURCE element to copy properties FROM", False)
    if status != "Normal":
        print("Selection cancelled.")
        exit()

    source_val = selectionSet.item(1).value
    source_obj = source_val.parent if "Selection_" in source_val.name else source_val

    # Read visual properties from source
    selectionSet.clear()
    selectionSet.add(source_obj)
    vis_src   = selectionSet.vis_properties
    colour    = vis_src.get_real_color()       # (status, r, g, b)
    width     = vis_src.get_real_width()       # (status, width_index)
    line_type = vis_src.get_real_line_type()   # (status, line_type_index)
    opacity   = vis_src.get_real_opacity()     # (status, opacity)
    symbol    = vis_src.get_symbol_type()      # (status, symbol_index)

    # Collect every shape in the set recursively
    all_shapes = []
    collect_shapes(target_hb, all_shapes)

    if not all_shapes:
        print(f"No shapes found in '{target_hb.name}'.")
        exit()

    # Add all shapes to the selection and apply properties in one batch
    selectionSet.clear()
    for shape in all_shapes:
        selectionSet.add(shape)

    vis_tgt = selectionSet.vis_properties

    if colour[0] == CAT_VIS_PROPERTY_DEFINED:
        vis_tgt.set_real_color(colour[1], colour[2], colour[3], 0)
    if width[0] == CAT_VIS_PROPERTY_DEFINED:
        vis_tgt.set_real_width(width[1], 0)
    if line_type[0] == CAT_VIS_PROPERTY_DEFINED:
        vis_tgt.set_real_line_type(line_type[1], 0)
    if opacity[0] == CAT_VIS_PROPERTY_DEFINED:
        vis_tgt.set_real_opacity(opacity[1], 0)
    if symbol[0] == CAT_VIS_PROPERTY_DEFINED:
        try:
            vis_tgt.set_symbol_type(symbol[1])
        except Exception:
            pass

    part.update()
    print(f"Applied properties from '{source_obj.name}' to {len(all_shapes)} element(s) in '{target_hb.name}'.")
