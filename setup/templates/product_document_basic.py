'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Your_Script_Name.py
    Version:        1.0
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        EDIT: One line summary shown on the script button.
    Author:         EDIT: Your Name
    Date:           EDIT: DD.MM.YY
    Description:    EDIT: Full description of what the script does.
                    EDIT: Continuation lines must be indented.
    dependencies = [
                    "pycatia",
                    ]
    requirements:   Python >= 3.10
                    pycatia
                    Catia V5 running with an open product document.
    -----------------------------------------------------------------------------------------------------------------------

    Change:

    -----------------------------------------------------------------------------------------------------------------------
'''

#Imports
from pycatia import catia, CatWorkModeType
from pycatia.mec_mod_interfaces.part_document import PartDocument
from pycatia.product_structure_interfaces.product_document import ProductDocument
from pathlib import Path
import sys

if __name__ == "__main__":
    caa = catia()                                                                                               #Catia application instance
    active_doc = caa.active_document                                                                           #Current active document

    if type(active_doc) is not ProductDocument:                                                                #Check that a CATProduct is active
        print("A CATProduct document must be the active document.")
        sys.exit()

    product_document: ProductDocument = active_doc                                                             #Cast to ProductDocument
    product = product_document.product                                                                         #Root product

    product.activate_terminal_node(product.products)                                                          #Activate all terminal nodes
    product.apply_work_mode(CatWorkModeType.DESIGN_MODE)                                                      #Put product in design mode

    # Collect all open CATPart documents loaded as children of this product
    part_documents = [doc for doc in caa.documents if doc.name.endswith('.CATPart')]                          #Get all open CATPart documents

    print(f"\n Found {len(part_documents)} CATPart document(s)\n")

    for part_document in part_documents:                                                                       #Iterate over each part document
        part_name = part_document.name.rsplit('.', 1)[0]                                                       #Get part name without extension
        print(f"  Processing: {part_name}")

        # TODO: Add logic here for each part document
        # part_document.part     — access the Part object
        # part_document.path()   — full path of the CATPart file

    print("\n\n Completed\n\n")
