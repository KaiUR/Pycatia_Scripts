'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Clash_Detection_Export.py
    Version:        1.0
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Run interference/clash detection on the active assembly and export results to CSV.
    Author:         Kai-Uwe Rathjen
    Date:           21.05.26
    Description:    This script accesses the DMU Space Analysis workbench via COM to create an
                    interference check between all components in the active CATProduct. After running
                    the analysis, it exports all detected clashes (type, status, component pair, and
                    interference volume) to a CSV file next to the CATProduct. Requires the DMU Space
                    Analysis or DMU Navigator module licence. If the workbench is unavailable, the
                    script will report the error and exit.
    dependencies = [
                    "pycatia",
                    ]
    requirements:   Python >= 3.10
                    pycatia
                    Catia V5 running with an open CATProduct document.
                    DMU Space Analysis or DMU Navigator licence required.
    -----------------------------------------------------------------------------------------------------------------------

    Change:

    -----------------------------------------------------------------------------------------------------------------------
'''

#Imports
from pycatia import catia, CatWorkModeType
from pycatia.product_structure_interfaces.product_document import ProductDocument
from pathlib import Path

CLASH_TYPES = {                                                                                                    #Interference type codes to human-readable labels
    0: "Clash",
    1: "Contact",
    2: "Clearance Violation",
}

if __name__ == "__main__":
    caa = catia()                                                                                                   #Catia application instance
    active_doc = caa.active_document                                                                               #Current open document

    if not type(active_doc) is ProductDocument:
        print("A CATProduct document must be the active document.")
        exit()

    product_document: ProductDocument = active_doc
    product = product_document.product

    product.activate_terminal_node(product.products)                                                               #Activate all terminal nodes
    product.apply_work_mode(CatWorkModeType.DESIGN_MODE)                                                           #Put assembly in design mode

    doc_name     = product_document.name.removesuffix('.CATProduct')
    doc_path_str = str(product_document.path())

    if doc_path_str == product_document.name:
        output_path = Path.home() / "Downloads" / (doc_name + "_ClashReport.csv")
    else:
        output_path = Path(doc_path_str).parent / (doc_name + "_ClashReport.csv")

    print("\n Accessing DMU Space Analysis workbench...\n")

    try:
        spa_wb = active_doc.com_object.GetWorkbench("DMUInterference")                                             #DMU Interference workbench via COM
    except Exception as e:
        print(f"Error: Could not access DMU Space Analysis workbench.")
        print(f"  Detail: {e}")
        print("\n  Ensure the DMU Space Analysis or DMU Navigator module is installed and licenced.")
        exit()

    rows = []

    try:
        interference_sets = spa_wb.InterferenceAnalysisSets                                                       #Collection of interference check sets

        check_set = None
        if interference_sets.Count == 0:                                                                           #Create a new check set if none exist
            check_set = interference_sets.Add()
        else:
            check_set = interference_sets.Item(1)                                                                  #Re-use the first existing set

        check_set.Name = "Python_Clash_Check"

        try:
            check_set.FirstGroup  = product                                                                        #Check all against all
            check_set.SecondGroup = product
        except Exception:
            pass

        print(" Running interference analysis...")
        check_set.Compute()                                                                                        #Run the analysis

        result_sets = check_set.InterferenceAnalysisResultSets
        print(f" Analysis complete — {result_sets.Count} result group(s) found\n")

        for ri in range(result_sets.Count):
            result_set = result_sets.Item(ri + 1)
            results    = result_set.InterferenceAnalysisResults

            for ci in range(results.Count):
                result = results.Item(ci + 1)

                clash_type   = ""
                component1   = ""
                component2   = ""
                volume       = ""
                status_str   = ""

                try:
                    clash_type = CLASH_TYPES.get(result.InterferenceType, f"Type {result.InterferenceType}")
                except Exception:
                    pass

                try:
                    component1 = result.Product1.Name
                except Exception:
                    pass

                try:
                    component2 = result.Product2.Name
                except Exception:
                    pass

                try:
                    volume = round(result.InterferenceVolume, 6)
                except Exception:
                    pass

                try:
                    status_str = str(result.InterferenceStatus)
                except Exception:
                    pass

                rows.append({
                    "Type":       clash_type,
                    "Component1": component1,
                    "Component2": component2,
                    "Volume_mm3": volume,
                    "Status":     status_str,
                })
                print(f"  {clash_type}: '{component1}' vs '{component2}'  Vol={volume} mm³")

    except Exception as e:
        print(f"Error during clash analysis: {e}")
        exit()

    if not rows:
        print("No clashes or interferences detected.")
        exit()

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("Type,Component1,Component2,Interference_Volume_mm3,Status\n")
            for row in rows:
                f.write(
                    f"\"{row['Type']}\","
                    f"\"{row['Component1']}\","
                    f"\"{row['Component2']}\","
                    f"\"{row['Volume_mm3']}\","
                    f"\"{row['Status']}\"\n"
                )

        print(f"\n\n Completed - {len(rows)} result(s) saved to: {output_path}\n\n")

    except PermissionError:
        print("Error: Permission denied. Is the output file already open in another program?")
    except IOError as e:
        print(f"Error: Could not write to file. {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
