'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Reset_Visual_Properties.py
    Version:        1.0
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Reset the visual properties of selected elements to CATIA defaults.
    Author:         Kai-Uwe Rathjen
    Date:           20.05.26
    Description:    This script asks the user to select one or more elements, then resets their colour, line
                    weight, line type and opacity to the CATIA wireframe defaults: white (255,255,255), weight
                    index 1, solid line type 1, and fully opaque (255). All selected elements are updated in
                    a single batch operation.
    dependencies = [
                    "pycatia",
                    ]
    requirements:   Python >= 3.10
                    pycatia
                    Catia V5 running with an open part, product or process.
    -----------------------------------------------------------------------------------------------------------------------
'''

from pycatia import catia

if __name__ == "__main__":
    caa = catia()                                                                                                 # Catia application instance

    object_filter = ("AnyObject",)                                                                               # Accept any element type
    selectionSet  = caa.active_document.selection                                                                 # Selection object

    status = selectionSet.select_element3(object_filter, "Select elements to reset visual properties", False, 2, False)
    if status != "Normal":
        print("Selection cancelled.")
        exit()

    # Unwrap boundary refs, collect real objects
    targets = []
    for i in range(selectionSet.count):
        val = selectionSet.item(i + 1).value
        targets.append(val.parent if "Selection_" in val.name else val)

    # Add all targets to selection at once and apply defaults in a single batch
    selectionSet.clear()
    for obj in targets:
        selectionSet.add(obj)

    vis = selectionSet.vis_properties
    vis.set_real_color(255, 255, 255, 0)                                                                         # White
    vis.set_real_width(1, 0)                                                                                     # Line weight index 1 (thinnest)
    vis.set_real_line_type(1, 0)                                                                                  # Line type 1 (solid)
    vis.set_real_opacity(255, 0)                                                                                  # Fully opaque

    print(f"Reset visual properties on {len(targets)} element(s).")
