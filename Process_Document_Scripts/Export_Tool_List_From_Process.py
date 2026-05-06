'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Export_Tool_List_From_Process.py
    Version:        1.0
    Code:           Python3.10.4, Pycatia 0.9.5
    Release:        V5R32
    Purpose:        Export all cutting tools from a process document to an Excel file.
    Author:         Kai-Uwe Rathjen
    Date:           06.05.26
    Description:    This script will export all cutting tools found in a CATProcess document to a formatted
                    Excel file. For each tool change in every program the script collects the tool name,
                    number, and description. Duplicate tools are listed only once. The output file is saved
                    in the current working directory.
    dependencies = [
                    "pycatia",
                    "xlsxwriter",
                    ]
    requirements:   Python >= 3.10
                    pycatia >= 0.9.5
                    xlsxwriter
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
import xlsxwriter
import os

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

    workbook = xlsxwriter.Workbook('Tool_List.xlsx')                                                            #Create new excel file
    worksheet = workbook.add_worksheet("Tool List")                                                             #Create single worksheet

    heading_format = workbook.add_format()                                                                      #Create new format for headings
    heading_format.set_font_name('Century')                                                                     #Set font for heading
    heading_format.set_bold()                                                                                   #Set heading to bold
    heading_format.set_font_size(14)                                                                            #Set font size
    heading_format.set_center_across()                                                                          #Centre text

    line_format_1 = workbook.add_format()                                                                       #Create new format for text
    line_format_1.set_font_name('Century')                                                                      #Set font
    line_format_1.set_font_size(12)                                                                             #Set font size

    #Add headings to sheet
    worksheet.write(0, 0, "Tool Number", heading_format)
    worksheet.write(0, 1, "Tool Name", heading_format)
    worksheet.write(0, 2, "Part Operation", heading_format)
    worksheet.write(0, 3, "Program Name", heading_format)

    row = 1                                                                                                     #Start at row 1 (after headings)
    seen_tools = set()                                                                                          #Track tools already written to avoid duplicates

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

                        for tool_change_index in range(tool_changes.count):                                     #Cycle through all activities of program
                            if tool_changes.item(tool_change_index + 1).type == "ToolChange":                   #If activity is Tool Change
                                try:
                                    tool = tool_changes.item(tool_change_index + 1).resources.item(1)           #Get tool resource
                                    tool_full_name = tool.name                                                  #Get full tool name
                                    tool_display = tool_full_name.split("(")[0].strip()                         #Strip extra info from name

                                    tool_key = tool_full_name                                                   #Use full name as unique key
                                    if tool_key not in seen_tools:                                              #If tool not already written
                                        seen_tools.add(tool_key)                                                #Mark as seen

                                        tool_number = ""                                                        #Default tool number to empty
                                        if "(" in tool_full_name and ")" in tool_full_name:                     #If tool number present in brackets
                                            tool_number = tool_full_name.split("(")[1].split(")")[0].strip()    #Extract tool number from brackets

                                        worksheet.write(row, 0, tool_number, line_format_1)                     #Write tool number
                                        worksheet.write(row, 1, tool_display, line_format_1)                    #Write tool name
                                        worksheet.write(row, 2, part_op.name, line_format_1)                    #Write part operation name
                                        worksheet.write(row, 3, man_prog.name, line_format_1)                   #Write program name
                                        row = row + 1                                                           #Increment row
                                except:
                                    pass                                                                        #Skip tool changes with no resource

    worksheet.autofit()                                                                                         #Autofit sheet
    worksheet.fit_to_pages(1, 0)                                                                                #Set print width to one sheet, height unlimited

    workbook.close()                                                                                            #Save and close workbook

    print(f"\n Completed - {row - 1} unique tool(s) exported to Tool_List.xlsx\n")
    os.startfile(os.path.abspath('Tool_List.xlsx'))                                                             #Open file
