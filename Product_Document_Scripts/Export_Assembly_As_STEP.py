'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Export_Assembly_As_STEP.py
    Version:        1.0
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Export the active product assembly as a single STEP file.
    Author:         Kai-Uwe Rathjen
    Date:           16.05.26
    Description:    This script exports the entire active CATProduct as a single assembled STEP file,
                    preserving the full assembly structure. The STEP file is saved next to the CATProduct
                    file, or in Downloads if the product has not been saved. This differs from
                    Save_Child_Parts_To_STEP which exports each CATPart as an individual STEP file.
    dependencies = [
                    "pycatia",
                    ]
    requirements:   Python >= 3.10
                    pycatia
                    Catia V5 running with an open CATProduct document.
                    This script needs an open CATProduct document.
    -----------------------------------------------------------------------------------------------------------------------

    Change:

    -----------------------------------------------------------------------------------------------------------------------
'''

#Imports
from pycatia import catia
from pycatia.product_structure_interfaces.product_document import ProductDocument
from pathlib import Path

if __name__ == "__main__":
    caa = catia()                                                                                                  #Catia application instance
    active_doc = caa.active_document                                                                               #Current open document

    if type(active_doc) is not ProductDocument:                                                                   #Check if product document
        print("A CATProduct document must be the active document.")
        exit()

    product_document: ProductDocument = active_doc

    doc_name = product_document.name.removesuffix('.CATProduct')                                                  #Document name without extension
    doc_path_str = str(product_document.path())                                                                   #Full file path as string

    if doc_path_str == product_document.name:                                                                     #Unsaved product — use Downloads
        output_path = Path.home() / "Downloads" / (doc_name + ".stp")
    else:
        output_path = Path(doc_path_str).parent / (doc_name + ".stp")                                            #Next to the CATProduct file

    print(f"\n Exporting assembly '{doc_name}' as STEP...\n")

    try:
        product_document.export_data(str(output_path), "stp", overwrite=True)                                     #Export full assembly as STEP
        print(f"\n\n Completed - saved to: {output_path}\n\n")
    except Exception as e:
        print(f"Error: Export failed. {e}")
