'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Your_Script_Name.py
    Version:        1.0
    Code:           Python3.10.4, Pycatia 0.9.5
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
                    pycatia >= 0.9.5
                    Catia V5 / DELMIA running with an open CATProcess document.
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
    check_document = caa.active_document                                                                       #Current active document
    current_document = None

    if type(check_document) is ProcessDocument:                                                                #Active document is a ProcessDocument
        current_document: PPRDocument = check_document.ppr_document                                           #Get PPRDocument from ProcessDocument
    elif type(check_document) is PPRDocument:                                                                  #Active document is already a PPRDocument
        current_document: PPRDocument = caa.active_document
    else:
        print("A CATProcess document must be the active document.")
        exit()

    processes = current_document.processes                                                                     #Get process list

    print("\n Iterating processes\n")

    for process_index in range(processes.count):                                                               #Cycle through all processes
        activity = processes.item(process_index + 1)                                                          #Get process

        part_operations = activity.children_activities                                                        #Get all Part operations for this process

        for part_operation_index in range(part_operations.count):                                             #Cycle through Part operations
            part_op = part_operations.item(part_operation_index + 1)                                          #Get Part operation

            if part_op.type == "ManufacturingSetup":                                                          #Check for Part operation type
                programs = part_op.children_activities                                                        #Get manufacturing programs

                for program_index in range(programs.count):                                                   #Cycle through programs
                    program = programs.item(program_index + 1)                                                #Get program

                    if program.type == "ManufacturingProgram":                                                #Check for manufacturing program type
                        operations = program.children_activities                                              #Get operations for this program

                        for operation_index in range(operations.count):                                      #Cycle through operations
                            operation = operations.item(operation_index + 1)                                 #Get operation

                            # TODO: Add logic for each operation here
                            # operation.name     — operation name
                            # operation.type     — operation type string
                            print(f"  {part_op.name} | {program.name} | {operation.name}")

    print("\n\n Completed\n\n")
