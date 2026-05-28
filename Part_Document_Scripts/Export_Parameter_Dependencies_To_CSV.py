'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Export_Parameter_Dependencies_To_CSV.py
    Version:        1.0
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Export all parameters with their formula dependencies to a CSV file.
    Author:         Kai-Uwe Rathjen
    Date:           28.05.26
    Description:    This script exports all user parameters from the active part document with two
                    dependency columns. The "Driven By" column shows the name of the formula or
                    relation that computes the parameter (if any). The "Used In" column lists every
                    relation that reads the parameter as an input, separated by semicolons. This
                    makes it easy to understand which parameters are free inputs and which are
                    driven or consumed by formulas. The output file is saved alongside the part.
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
    caa = catia()                                                                                                    #Catia application instance
    active_doc = caa.active_document                                                                                 #Current active document

    if type(active_doc) is not PartDocument:                                                                         #Check that a CATPart is active
        print("A CATPart document must be the active document.")
        exit()

    part_document: PartDocument = active_doc                                                                         #Cast to PartDocument
    part = part_document.part                                                                                        #Current part
    parameters = part.parameters                                                                                     #All parameters
    relations  = part.relations                                                                                       #All relations (formulas, rules, checks)

    doc_name     = part_document.name.removesuffix('.CATPart')                                                       #Document name without extension
    doc_path_str = str(part_document.path())                                                                         #Full path string
    if doc_path_str == part_document.name:                                                                           #Unsaved document — path() returns just the filename
        output_path = Path.home() / "Downloads" / (doc_name + "_Parameter_Dependencies.csv")                        #Fall back to Downloads
    else:
        output_path = Path(doc_path_str).parent / (doc_name + "_Parameter_Dependencies.csv")                        #Save alongside document

    #Build mapping: parameter name -> list of relation names that use it as input
    used_in_map = {}                                                                                                 #param_name -> [relation_names]
    for r_idx in range(relations.count):                                                                             #Iterate all relations
        try:
            relation = relations.item(r_idx + 1)                                                                     #Get relation (1-based)
            rel_name = relation.name                                                                                  #Relation name
            for p_idx in range(relation.nb_in_parameters):                                                           #Iterate input parameters of this relation
                try:
                    in_param = relation.get_in_parameter(p_idx + 1)                                                  #Get input param (may not be a Parameter object)
                    in_name  = in_param.name                                                                          #Get name via AnyObject
                    used_in_map.setdefault(in_name, []).append(rel_name)                                             #Record that this param feeds this relation
                except Exception:
                    pass                                                                                             #Skip if input is not a named object
        except Exception:
            pass                                                                                                     #Skip unreadable relations

    print(f"\n Found {parameters.count} parameters, {relations.count} relations\n")

    rows = []                                                                                                        #Collected CSV rows
    for p_idx in range(parameters.count):                                                                            #Iterate all parameters
        try:
            param      = parameters.item(p_idx + 1)                                                                  #Get parameter (1-based)
            param_name = param.name                                                                                   #Parameter name

            try:
                value_str = str(param.value)                                                                         #Parameter value
            except Exception:
                value_str = ""                                                                                       #Leave blank if value unreadable

            driven_by = ""                                                                                           #Name of relation driving this parameter
            try:
                opt_rel   = param.optional_relation                                                                   #Relation that drives this param (may throw if None)
                driven_by = opt_rel.name                                                                              #Formula/rule name
            except Exception:
                driven_by = ""                                                                                       #No driving relation

            used_in = "; ".join(used_in_map.get(param_name, []))                                                     #Relations that read this param as input

            rows.append((param_name, value_str, driven_by, used_in))
            print(f"  {param_name}  =  {value_str}  driven_by: {driven_by or '-'}  used_in: {used_in or '-'}")

        except Exception as e:
            print(f"  Warning: Could not read parameter {p_idx + 1}: {e}")

    print(f"\n Exporting {len(rows)} parameters\n")

    try:
        with open(output_path, "w", encoding="utf-8") as f:                                                          #Write CSV file
            f.write("Parameter Name,Value,Driven By,Used In\n")                                                      #CSV header
            for row in rows:
                f.write(",".join(f'"{col}"' for col in row) + "\n")                                                  #Quote all fields

        print(f"\n\n Completed - saved to: {output_path}\n\n")

    except PermissionError:
        print("Error: Permission denied. Is the output file already open in another program?")
    except IOError as e:
        print(f"Error: Could not write to file. {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
