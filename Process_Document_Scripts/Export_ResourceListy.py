'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Export_Process_Table_Parameters.py
    Version:        1.0
    Code:           Python3.10.4, Pycatia 0.9.5
    Release:        V5R32
    Purpose:        Exports names of resourses to csv file
    Author:         Kai-Uwe Rathjen
    Date:           26.03.26
    Description:    This script will export the names of all resources in a process document. Output file will be created in
                    same location as script
    dependencies = [
                    "pycatia",
                    ]
    requirements:   Python >= 3.10
                    pycatia >= 0.9.5
                    Process document open with resources.
    -----------------------------------------------------------------------------------------------------------------------
    
    Change:
    
    -----------------------------------------------------------------------------------------------------------------------
'''

#Imports
from pycatia import catia
from pycatia.dmaps_interfaces.process_document import ProcessDocument
from pycatia.ppr_interfaces.ppr_document import PPRDocument

if __name__ == "__main__":
    caa = catia()                                                                                           #Catia application instance
    check_document = caa.active_document                                                                    #Current Active Document
    current_document = None
    if type(check_document) is ProcessDocument:                                                             #Active Document is ProcessDocument
        current_document: PPRDocument = check_document.ppr_document                                         #Get PPRDocument
    elif type(check_document) is PPRDocument:                                                               #Active document is PPRDocument
        current_document: PPRDocument = caa.active_document
    else:
        print("A CATProcess document must be the active document.")                                         #Error message, No ppr document open
        exit()                                                                                              #Exit script

    file_name = "Resource_list.csv"                                                                         #Output file name
    try:
        with open(file_name, "w") as output_file:                                                           #Create file
            ppr_resources = current_document.resources                                                      #Collection of all resources, as products
            
            for index in range(ppr_resources.count):                                                        #Cycle through collection
                resource = ppr_resources.item(index + 1)                                                    #Each resource
                output_file.write(f"{resource.reference_product.name},\n")                                  #Write name to file, reference product contains actual resource name
        
        print(f"Successfully created {file_name}")                                                          #Sucess message

    except PermissionError:
        print(f"Error: Permission denied. Is '{file_name}' already open in another program?")
    except IOError as e:
        print(f"Error: Could not write to file. {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")