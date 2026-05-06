'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Rename_Operations_From_Tool_Name.py
    Version:        1.0
    Code:           Python3.10.4, Pycatia 0.9.5
    Release:        V5R32
    Purpose:        Automatically rename each operation in a process program to match the assigned tool name.
    Author:         Kai-Uwe Rathjen
    Date:           06.05.26
    Description:    This script will cycle through all manufacturing programs in the active process document
                    and rename each operation to match the name of the tool assigned to it via the preceding
                    tool change. If an operation has no preceding tool change it is left unchanged. Duplicate
                    operation names within the same program are disambiguated by appending an incrementing
                    number. Keeps the process tree readable and consistent.
    dependencies = [
                    "pycatia",
                    ]
    requirements:   Python >= 3.10
                    pycatia >= 0.9.5
                    Catia V5 / DELMIA running with an open CATProcess document containing a part operation
                    with a program and tool changes.
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

    renamed_count = 0                                                                                           #Count total renames

    print("\n Renaming operations from tool names\n")

    for process_index in range(processes.count):                                                                #Cycle through all processes
        activity = processes.item(process_index + 1)                                                            #Get process

        part_operations = activity.children_activities                                                          #Get collection of Part operations for process

        for part_operation_index in range(part_operations.count):                                               #Cycle through all operations
            part_op = part_operations.item(part_operation_index + 1)                                            #Get Operation

            if part_op.type == "ManufacturingSetup":                                                            #Check for Part operation
                manufacturing_programs = part_op.children_activities                                            #Get all activities for part operation

                for man_index in range(manufacturing_programs.count):                                           #Cycle through all activities
                    man_prog = manufacturing_programs.item(man_index + 1)                                       #Get an activity

                    if man_prog.type == "ManufacturingProgram":                                                  #Check if activity is program
                        tool_changes = man_prog.children_activities                                             #Get activities for program

                        current_tool_name = None                                                                #Track the current active tool
                        name_usage_count = {}                                                                   #Track how many times each tool name has been used in this program

                        for tool_change_index in range(tool_changes.count):                                     #Cycle through all activities of program
                            activity_item = tool_changes.item(tool_change_index + 1)                            #Get activity

                            if activity_item.type == "ToolChange":                                              #If activity is Tool Change
                                try:
                                    tool = activity_item.resources.item(1)                                      #Get tool resource
                                    current_tool_name = tool.name.split("(")[0].strip()                         #Get tool name, strip extra info
                                except:
                                    current_tool_name = None                                                    #If no resource, clear tool name

                            elif activity_item.type in ("Start", "Stop"):                                       #Skip Start and Stop activities
                                continue

                            else:                                                                               #All remaining activities are operations
                                if current_tool_name is not None:                                               #If a tool is assigned
                                    if current_tool_name not in name_usage_count:                               #If first use of this tool name in program
                                        name_usage_count[current_tool_name] = 1                                 #Initialise counter
                                    else:                                                                       #If tool name already used
                                        name_usage_count[current_tool_name] += 1                                #Increment counter

                                    count = name_usage_count[current_tool_name]                                 #Get current count
                                    new_name = f"{current_tool_name}.{count}"                                   #Build new name with count suffix

                                    old_name = activity_item.name                                               #Store old name
                                    activity_item.name = new_name                                               #Rename operation
                                    renamed_count = renamed_count + 1                                           #Increment count
                                    print(f"  '{old_name}' -> '{new_name}'")

    print(f"\n\n Completed - {renamed_count} operation(s) renamed\n\n")
