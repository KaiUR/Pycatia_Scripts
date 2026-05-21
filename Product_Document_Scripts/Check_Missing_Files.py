'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Check_Missing_Files.py
    Version:        1.0
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Check all component file references in the assembly for missing or broken links.
    Author:         Kai-Uwe Rathjen
    Date:           21.05.26
    Description:    This script recurses through the active CATProduct and checks whether the file
                    referenced by each component instance actually exists on disk. Components whose
                    files cannot be found are listed with their assembly path and last known file
                    location. Results are printed to the console and optionally saved to a CSV file
                    next to the CATProduct. Useful for troubleshooting broken assembly references.
    dependencies = [
                    "pycatia",
                    ]
    requirements:   Python >= 3.10
                    pycatia
                    Catia V5 running with an open CATProduct document.
    -----------------------------------------------------------------------------------------------------------------------

    Change:

    -----------------------------------------------------------------------------------------------------------------------
'''

#Imports
from pycatia import catia
from pycatia.product_structure_interfaces.product_document import ProductDocument
from pathlib import Path

def _check_files(product, parent_path, rows):
    try:
        children = product.products
    except Exception:
        return

    for i in range(children.count):
        try:
            child     = children.item(i + 1)
            inst_name = child.name
        except Exception:
            continue

        full_path = f"{parent_path}/{inst_name}" if parent_path else inst_name

        file_name = ""
        file_exists = None

        try:
            file_name = child.full_name                                                                            #Full file path stored in the product link
            p = Path(file_name)
            file_exists = p.exists()
        except Exception:
            try:
                file_name   = child.file_name                                                                      #Fallback to file name only
                file_exists = None                                                                                  #Cannot check existence with name only
            except Exception:
                file_name   = "(unknown)"
                file_exists = None

        if file_exists is False:
            status = "MISSING"
        elif file_exists is None:
            status = "UNRESOLVED"
        else:
            status = "OK"

        rows.append({
            "Path":       full_path,
            "Instance":   inst_name,
            "File":       file_name,
            "Status":     status,
        })

        if child.products.count > 0:
            _check_files(child, full_path, rows)


if __name__ == "__main__":
    caa = catia()                                                                                                   #Catia application instance
    active_doc = caa.active_document                                                                               #Current open document

    if not type(active_doc) is ProductDocument:
        print("A CATProduct document must be the active document.")
        exit()

    product_document: ProductDocument = active_doc
    product = product_document.product

    doc_name     = product_document.name.removesuffix('.CATProduct')
    doc_path_str = str(product_document.path())

    if doc_path_str == product_document.name:
        output_path = Path.home() / "Downloads" / (doc_name + "_MissingFiles.csv")
    else:
        output_path = Path(doc_path_str).parent / (doc_name + "_MissingFiles.csv")

    rows = []
    _check_files(product, "", rows)

    total    = len(rows)
    ok_count = sum(1 for r in rows if r['Status'] == "OK")
    missing  = sum(1 for r in rows if r['Status'] == "MISSING")
    unres    = sum(1 for r in rows if r['Status'] == "UNRESOLVED")

    print(f"\n Checked {total} component reference(s)\n")
    print(f"  {'Instance':<35} {'Status':<12} File")
    print(f"  {'-'*35} {'-'*12} {'-'*50}")

    for row in rows:
        if row['Status'] != "OK":
            print(f"  {row['Instance']:<35} {row['Status']:<12} {row['File']}")

    if missing == 0 and unres == 0:
        print("  All references resolved — no missing files found.")

    print(f"\n Summary: {ok_count} OK  |  {missing} Missing  |  {unres} Unresolved")

    if missing > 0 or unres > 0:
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write("Assembly Path,Instance Name,File Reference,Status\n")
                for row in rows:
                    if row['Status'] != "OK":
                        f.write(
                            f"\"{row['Path']}\","
                            f"\"{row['Instance']}\","
                            f"\"{row['File']}\","
                            f"\"{row['Status']}\"\n"
                        )
            print(f"\n Missing files saved to: {output_path}")
        except Exception as e:
            print(f"\n Could not write CSV: {e}")

    print("\n\n Completed\n\n")
