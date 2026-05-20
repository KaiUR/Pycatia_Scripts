'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Copy_Name_and_Colour.py
    Version:        1.0
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Copies the name, colour, line weight and line type from one element to a selection of elements.
    Author:         Kai-Uwe Rathjen
    Date:           20.05.26
    Description:    This script asks the user to select one or more target elements, then select a single source
                    element. The name, colour, line weight, line type and opacity of the source are applied to all
                    targets. Properties that do not apply to a given target (e.g. line weight on an unsupported
                    element type) are skipped silently.

                    Curves selected as targets and a surface as source (or vice versa): name and colour are always
                    copied; line weight/type are attempted and silently skipped if CATIA rejects them for the
                    element type.
    dependencies = [
                    "pycatia",
                    ]
    requirements:   Python >= 3.10
                    pycatia
                    Catia V5 running with an open part, product or process.
    -----------------------------------------------------------------------------------------------------------------------
'''

from pycatia import catia

CAT_VIS_PROPERTY_DEFINED = 0                                                                                     # catVisPropertyDefined: all elements share the same value

if __name__ == "__main__":
    caa = catia()                                                                                                 # Catia application instance

    object_filter = ("AnyObject",)                                                                               # Accept any element type
    selectionSet  = caa.active_document.selection                                                                 # Selection object

    # --- Step 1: multi-select target elements ---
    status = selectionSet.select_element3(object_filter, "Select elements to copy properties TO", False, 2, False)
    if status != "Normal":
        print("Selection cancelled.")
        exit()

    # Capture target object references before the selection is replaced
    targets = []
    for i in range(selectionSet.count):
        val = selectionSet.item(i + 1).value
        targets.append(val.parent if "Selection_" in val.name else val)      # Unwrap boundary refs to their parent feature

    # --- Step 2: single-select source element ---
    selectionSet.clear()
    status = selectionSet.select_element2(object_filter, "Select the SOURCE element to copy properties FROM", False)
    if status != "Normal":
        print("Source selection cancelled.")
        exit()

    source_val = selectionSet.item(1).value
    source_obj = source_val.parent if "Selection_" in source_val.name else source_val                            # Unwrap boundary ref if needed
    source_name = source_obj.name

    # Read visual properties with only the source in the selection
    selectionSet.clear()
    selectionSet.add(source_obj)
    vis_src = selectionSet.vis_properties

    colour    = vis_src.get_real_color()       # Returns (status, r, g, b)     – status 0 = Defined
    width     = vis_src.get_real_width()       # Returns (status, width_index)  – index range 1–63
    line_type = vis_src.get_real_line_type()   # Returns (status, line_type_index)
    opacity   = vis_src.get_real_opacity()     # Returns (status, opacity)      – 0 (transparent) to 255 (opaque)

    # --- Step 3: apply name and visual properties to each target ---
    for target_obj in targets:
        target_obj.name = source_name

        selectionSet.clear()
        selectionSet.add(target_obj)
        vis_tgt = selectionSet.vis_properties

        if colour[0] == CAT_VIS_PROPERTY_DEFINED:
            try:
                vis_tgt.set_real_color(colour[1], colour[2], colour[3], 0)
            except Exception:
                pass

        if width[0] == CAT_VIS_PROPERTY_DEFINED:
            try:
                vis_tgt.set_real_width(width[1], 0)
            except Exception:
                pass

        if line_type[0] == CAT_VIS_PROPERTY_DEFINED:
            try:
                vis_tgt.set_real_line_type(line_type[1], 0)
            except Exception:
                pass

        if opacity[0] == CAT_VIS_PROPERTY_DEFINED:
            try:
                vis_tgt.set_real_opacity(opacity[1], 0)
            except Exception:
                pass

    print(f"Copied properties from '{source_name}' to {len(targets)} element(s).")
