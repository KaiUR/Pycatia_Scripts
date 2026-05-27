'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Save_Child_Parts_To_STL.py
    Version:        1.0
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Save all child parts as STL
    Author:         Kai-Uwe Rathjen
    Date:           27.05.26
    Description:    This script will save all CATParts in a product to separate STL files.

                    Modified from Save_Child_Parts_To_STEP.py.

                    When a CATProduct is open, CATIA loads referenced parts into the Documents
                    collection in visualization mode — geometry is not fully loaded, so calling
                    export_data on them writes nothing. The fix is to collect the file paths first,
                    then open each part fresh as a standalone document, export it, and close it.

                    This script will work on unsaved products, in that case the export will be saved to the downloads folder.
    dependencies = [
                    "pycatia",
                    ]
    requirements:   Python >= 3.10
                    pycatia
                    Catia V5 running with an open product with parts.
                    This script needs an open product document.
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
    caa = catia()                                                                                                       #Catia application instance
    product_document: ProductDocument = caa.active_document                                                             #Current open document

    if not type(product_document) == ProductDocument:                                                                   #Check if product
        print("A CATProduct document must be the active document.")
        sys.exit()

    product_document_name = product_document.name.removesuffix('.CATProduct')                                           #Get name of product
    product_document_path = str(
            product_document.path()).removesuffix(product_document.name) + "\STL_Export_" + product_document_name      #Path of current product with destination folder appended

    if product_document_path == "\STL_Export_" + product_document_name:                                                #If product has not been saved, path will be empty
        product_document_path = str(Path.home() / "Downloads") + "\STL_Export_" + product_document_name                #Export to users download folder

    Path(product_document_path).mkdir(parents=True, exist_ok=True)                                                      #Create directory if it doesn't exist

    product = product_document.product
    product.activate_terminal_node(product.products)
    product.apply_work_mode(CatWorkModeType.DESIGN_MODE)                                                                #Put the product in design mode

    # Collect part paths now, before opening or closing anything, so the Documents collection stays stable during iteration
    catpart_paths = [doc.path() for doc in caa.documents if doc.name.endswith('.CATPart')]

    for catpart_path in catpart_paths:                                                                                  #For each part: open fresh, export, close
        part_document: PartDocument = caa.documents.open(catpart_path)                                                 #Open standalone — parts loaded via a product are in visualization mode and export nothing

        file_type = 'stl'
        stl_name = Path(product_document_path, catpart_path.stem + f'.{file_type}')
        print('Saving STL to ' + str(stl_name))
        part_document.export_data(stl_name, file_type, overwrite=True)

        part_document.close()                                                                                           #Close the standalone window — document was not modified so no save prompt

    product_document.activate()                                                                                         #Return focus to the product
