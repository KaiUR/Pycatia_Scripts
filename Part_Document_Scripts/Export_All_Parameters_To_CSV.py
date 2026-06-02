'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Export_All_Parameters_To_CSV.py
    Version:        1.0
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Export all parameters from the active part to a CSV file.
    Author:         Kai-Uwe Rathjen
    Date:           06.05.26
    Description:    This script will export all parameters from the active part document to a CSV file.
                    The output file contains the parameter name, type, value, and formula (if any) for each
                    parameter. The file is saved in the same folder as the part document. Useful for design
                    reviews and change tracking.
    dependencies = [
                    "pycatia",
                    ]
    requirements:   Python >= 3.10
                    pycatia
                    Catia V5 running with an open part document.
                    This script needs an open part document.
    -----------------------------------------------------------------------------------------------------------------------

    Change:

    -----------------------------------------------------------------------------------------------------------------------
'''

#Imports
from pycatia import catia
from pycatia.mec_mod_interfaces.part_document import PartDocument
from pathlib import Path

if __name__ == "__main__":
    #Anchoring relavent components
    caa = catia()                                                                                               #Catia application instance
    part_document: PartDocument = caa.active_document                                                          #Current open document

    if type(part_document) is not PartDocument:                                                                 #Check if part document
        print("A CATPart document must be the active document.")
        exit()

    part = part_document.part                                                                                   #Current part
    parameters = part.parameters                                                                                #Get all parameters from part

    doc_name     = part_document.name.removesuffix('.CATPart')                                                  #Get document name without extension
    doc_path_str = str(part_document.path())                                                                     #Full path string
    if doc_path_str == part_document.name:                                                                       #Unsaved document — path() returns just the filename
        output_path = Path.home() / "Downloads" / (doc_name + "_Parameters.csv")                                #Fall back to Downloads
    else:
        output_path = Path(doc_path_str).parent / (doc_name + "_Parameters.csv")                                #Save alongside document

    print(f"\n Exporting {parameters.count} parameters\n")

    try:
        with open(output_path, "w") as output_file:                                                             #Create output file
            output_file.write("Parameter Name,Type,Value,Formula\n")                                            #Write CSV header

            for index in range(parameters.count):                                                               #Loop through all parameters
                param = parameters.item(index + 1)                                                              #Get parameter

                param_name = param.name                                                                         #Get parameter name
                param_type = param.user_access_mode                                                             #Get parameter type
                
                try:
                    param_value = param.value_as_string()                                                       #Get value as string
                except:
                    param_value = ""                                                                            #If value cannot be read, leave blank

                try:
                    relations = part.relations                                                                   #Get all relations (formulas)
                    param_formula = ""                                                                           #Default to empty formula
                    for r_index in range(relations.count):                                                       #Loop through relations
                        relation = relations.item(r_index + 1)                                                   #Get relation
                        if relation.name.find(param_name) != -1:                                                 #If relation is for this parameter
                            param_formula = relation.value                                                       #Get formula value
                            break
                except:
                    param_formula = ""                                                                           #If formula cannot be read, leave blank

                output_file.write(f"\"{param_name}\",\"{param_type}\",\"{param_value}\",\"{param_formula}\"\n") #Write parameter to file
                print(f"  {param_name}: {param_value}")                                                         #Print to console

        print(f"\n\n Completed - saved to: {output_path}\n\n")

    except PermissionError:
        print("Error: Permission denied. Is the output file already open in another program?")
    except IOError as e:
        print(f"Error: Could not write to file. {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
