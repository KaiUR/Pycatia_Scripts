'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Swap_Names.py
    Version:        1.0
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Swap the names of two selected elements.
    Author:         Kai-Uwe Rathjen
    Date:           20.05.26
    Description:    This script asks the user to select two elements in sequence. The names of the two
                    elements are then swapped. Useful when rebuilding geometry in a different order or
                    correcting accidentally transposed names.
    dependencies = [
                    "pycatia",
                    ]
    requirements:   Python >= 3.10
                    pycatia
                    Catia V5 running with an open part, product or process.
    -----------------------------------------------------------------------------------------------------------------------

    Change:

    -----------------------------------------------------------------------------------------------------------------------
'''

from pycatia import catia

if __name__ == "__main__":
    caa = catia()                                                                                                 # Catia application instance

    object_filter = ("AnyObject",)                                                                               # Accept any element type
    selectionSet  = caa.active_document.selection                                                                 # Selection object

    # --- Step 1: select first element ---
    status = selectionSet.select_element2(object_filter, "Select the FIRST element to swap", False)
    if status != "Normal":
        print("Selection cancelled.")
        exit()

    val1  = selectionSet.item(1).value
    obj1  = val1.parent if "Selection_" in val1.name else val1
    name1 = obj1.name

    # --- Step 2: select second element ---
    selectionSet.clear()
    status = selectionSet.select_element2(object_filter, "Select the SECOND element to swap", False)
    if status != "Normal":
        print("Selection cancelled.")
        exit()

    val2  = selectionSet.item(1).value
    obj2  = val2.parent if "Selection_" in val2.name else val2
    name2 = obj2.name

    # --- Swap ---
    obj1.name = name2
    obj2.name = name1

    print(f"Swapped: '{name1}' <-> '{name2}'")
