'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Batch_Instance_Name_Equal_Part_Number.py
    Version:        1.0
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Set every instance name in the active product tree to match its part number.
    Author:         Kai-Uwe Rathjen
    Date:           16.05.26
    Description:    This script will recurse through the active CATProduct document tree and set each
                    component's instance name (what appears in the spec tree) to match its part number.
                    Components with an empty part number are skipped and reported. The product is saved
                    after all renames are complete.
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

def set_instance_names(product, skipped):
    children = product.products                                                                                    #Get child products collection
    count = 0
    for i in range(children.count):                                                                               #Loop through children
        child = children.item(i + 1)                                                                              #Get child product
        pn = child.part_number.strip() if child.part_number else ""                                               #Get trimmed part number
        if pn:                                                                                                     #If part number is not empty
            old_name = child.name
            child.name = pn                                                                                        #Set instance name to part number
            print(f"  Renamed: '{old_name}' -> '{pn}'")
            count += 1
        else:                                                                                                      #No part number — skip
            skipped.append(child.name)
        count += set_instance_names(child, skipped)                                                               #Recurse into sub-assemblies
    return count

if __name__ == "__main__":
    caa = catia()                                                                                                  #Catia application instance
    active_doc = caa.active_document                                                                               #Current open document

    if type(active_doc) is not ProductDocument:                                                                   #Check if product document
        print("A CATProduct document must be the active document.")
        exit()

    product_document: ProductDocument = active_doc
    product = product_document.product                                                                             #Get root product

    print(f"\n Processing product: '{product.part_number}'\n")

    skipped = []
    renamed = set_instance_names(product, skipped)                                                                #Rename all instances

    if skipped:                                                                                                    #Report skipped items
        print(f"\n Skipped {len(skipped)} component(s) with no part number:")
        for name in skipped:
            print(f"  - {name}")

    print(f"\n\n Completed - renamed {renamed} instance(s)\n\n")
