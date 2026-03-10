'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Save_Child_Parts_To_STEP.py
    Version:        1.0
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Save all child parts as step
    Author:         Kai-Uwe Rathjen
    Date:           10.03.26
    Description:    This script will save all CATParts in a file to STEP
    
                    Modified from Pycatia user scripts.
                    
                    Original:
                    https://github.com/evereux/pycatia/blob/master/user_scripts/save_child_parts_to_stp.py
                    
                    This script will work on unsaved products, in that case the export will be saved to downlaods folder.
    dependencies = [
                    "pycatia",
                    ]
    requirements:   Python >= 9.10
                    pycatia
                    Catia V5 running with an open product with part.
                    This script needs an open part document.
    -----------------------------------------------------------------------------------------------------------------------
    
    Change:
    
    -----------------------------------------------------------------------------------------------------------------------
'''

#Imports
from pycatia import catia, CatWorkModeType
from pycatia.mec_mod_interfaces.part_document import PartDocument
from pycatia.product_structure_interfaces.product_document import ProductDocument
from pathlib import Path

if __name__ == "__main__":
    caa = catia()                                                                                                       #Catia application instance
    product_document: ProductDocument = caa.active_document                                                             #Current open document
    
    product_document_name = product_document.name.removesuffix('.CATProduct')                                           #Get Name of product
    product_document_path = str(
            product_document.path()).removesuffix(product_document.name) + "\STEP_Export_" + product_document_name      #path of current product, as string with filename removed, destination foleder added
    
    if product_document_path == "\STEP_Export_" + product_document_name:                                                #If product has not been saved path will be empty
        product_document_path = str(Path.home() / "Downloads") + "\STEP_Export_" + product_document_name                #Export to users download folder
        
    Path(product_document_path).mkdir(parents=True, exist_ok=True)                                                      #Create Directory if doesnt exist

    if not type(product_document) == ProductDocument:                                                                   #Check if product
        print("A CATProduct document must be the active document.")
        sys.exit()

    product = product_document.product                                                                                  
    product.activate_terminal_node(product.products)
    
    product.apply_work_mode(CatWorkModeType.DESIGN_MODE)                                                                #put the product in design mode.
    
    part_documents = [catpart for catpart in caa.documents if catpart.name.endswith('.CATPart')]                        #get all the CATParts from the document collection object.

    for part_document in part_documents:                                                                                #for each part, export to step
        file_type = 'stp'
        stp_name = Path(product_document_path, part_document.name.rsplit('.', 1)[0] + f'.{file_type}')
        print('Saving STP to ' + str(stp_name))
        part_document.export_data(stp_name, file_type, overwrite=True)