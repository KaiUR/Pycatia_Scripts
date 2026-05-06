'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Export_NC_Program_Names_To_CSV.py
    Version:        1.0
    Code:           Python3.10.4, Pycatia 0.9.5
    Release:        V5R32
    Purpose:        Export all manufacturing program names and descriptions across all part operations to CSV.
    Author:         Kai-Uwe Rathjen
    Date:           06.05.26
    Description:    This script will cycle through all part operations in the active process document and
                    export the name and description of every manufacturing program to a CSV file. The output
                    is saved in the current working directory. Useful for generating a program list document
                    or cross-referencing programs with the machine controller.
    dependencies = [
                    "pycatia",
                    ]
    requirements:   Python >= 3.10
                    pycatia >= 0.9.5
                    Catia V5 / DELMIA running with an open CATProcess document containing a part operation
                    with manufacturing programs.
                    This script needs an open process document.
    -----------------------------------------------------------------------------------------------------------------------

    Change:

    -----------------------------------------------------------------------------------------------------------------------
'''

#Imports
from pycatia import catia
from pycatia.dmaps_interfaces.process_document import ProcessDocument
from pycatia.ppr_interfaces.ppr_document import PPRDocument

if __name__ == "__main__":
    caa = catia()                                                                                               #Catia application instance
    check_document = caa.active_document                                                                        #Current Active Document
    current_document = None
    if type(check_document) is ProcessDocument:                                                                 #Active Document is ProcessDocument
        current_document: PPRDocument = check_document.ppr_document                                             #Get PPRDocument
    elif type(check_document) is PPRDocument:                                                                   #Active document is PPRDocument
        current_document: PPRDocument = caa.active_document
    else:
        print("A CATProcess document must be the active document.")                                             #Print error message
        exit()

    processes = current_document.processes                                                                      #Get process list

    file_name = "NC_Program_List.csv"                                                                          #Output file name
    program_count = 0                                                                                           #Count total programs exported

    print("\n Exporting NC program names\n")

    try:
        with open(file_name, "w") as output_file:                                                               #Create output file
            output_file.write("Part Operation,Program Name,Description\n")                                      #Write CSV header

            for process_index in range(processes.count):                                                        #Cycle through all processes
                activity = processes.item(process_index + 1)                                                    #Get process

                part_operations = activity.children_activities                                                  #Get collection of Part operations for process

                for part_operation_index in range(part_operations.count):                                       #Cycle through all operations
                    part_op = part_operations.item(part_operation_index + 1)                                    #Get Operation

                    if part_op.type == "ManufacturingSetup":                                                    #Check for Part operation
                        manufacturing_programs = part_op.children_activities                                    #Get all activities for part operation

                        for man_index in range(manufacturing_programs.count):                                   #Cycle through all activities
                            man_prog = manufacturing_programs.item(man_index + 1)                               #Get an activity

                            if man_prog.type == "ManufacturingProgram":                                          #Check if activity is program
                                prog_name = man_prog.name                                                       #Get program name

                                prog_desc = man_prog.description                                                #Get program description
                                if prog_desc.find("No Description") != -1:                                      #If default description
                                    prog_desc = ""                                                              #Set to empty

                                output_file.write(f"\"{part_op.name}\",\"{prog_name}\",\"{prog_desc}\"\n")      #Write program to file
                                print(f"  {part_op.name} | {prog_name}")
                                program_count = program_count + 1                                               #Increment count

        print(f"\n\n Completed - {program_count} program(s) exported to {file_name}\n\n")

    except PermissionError:
        print(f"Error: Permission denied. Is '{file_name}' already open in another program?")
    except IOError as e:
        print(f"Error: Could not write to file. {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
