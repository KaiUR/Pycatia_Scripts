'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Export_Process_Table_Parameters.py
    Version:        1.0
    Code:           Python3.10.4, Pycatia 0.9.5
    Release:        V5R32
    Purpose:        Exports parameters from process table to excel
    Author:         Kai-Uwe Rathjen
    Date:           08.03.26
    Description:    This script will export all of the parameters in the process table for all part operations
                    and insert them into excel.
                    
                    This script is to get all parameters for all manufacturing programs into one place so we can check our values to ensure
                    they are correct.
                    
                    *** Only tested with sweep, pencil and contour driven so far***
    dependencies = [
                    "pycatia",
                    "xlsxwriter",
                    ]
    requirements:   Python >= 9.10
                    pycatia >= 0.9.5 (There is a bug in privious vesrions, scritp will not work)
                    xlsxwriter
                    Catia V5 running wtih an open process containing a part operation with a program and operation.
                    This script needs an open part process document.
    -----------------------------------------------------------------------------------------------------------------------
    
    Change:
    
    -----------------------------------------------------------------------------------------------------------------------
'''

#Imports
from pycatia import catia
from pycatia.dmaps_interfaces.process_document import ProcessDocument
from pycatia.dmaps_interfaces.activities import Activities
from pycatia.dmaps_interfaces.activity import Activity
from pycatia.ppr_interfaces.ppr_document import PPRDocument
import xlsxwriter

'''
    | Due to the inherent design restrictions, PPRDocument and another interface ProcessDocument need to
    | be used with care, since the ActiveDocument could be either ProcessDocument or PPRDocument. With that
    | in mind, a good practice of writing more robust VB script is to first tell the real type of document
    | (interface).
    | E.g. The following sentence
    | Dim MyDoc As PPRDocument
    | Set MyDoc = DELMIA.ActiveDocument.PPRDocument
    | could be replaced by the following:
    | Dim MyDoc As PPRDocument
    | Set MyProcDoc = DELMIA.ActiveDocument
    | if (TypeName(MyProcDoc)="ProcessDocument")
    | then MyDoc = MyProcDoc.PPRDocument
    | else MyDoc = DELMIA.ActiveDocument
    | end if
'''
if __name__ == "__main__":
    caa = catia()                                                                                           #Catia application instance
    check_document = caa.active_document                                                                    #Current Active Document
    current_document = None
    if type(check_document) is ProcessDocument:                                                             #Active Document is ProcessDocument
        current_document: PPRDocument = check_document.ppr_document                                         #Get PPRDocument
    elif type(check_document) is PPRDocument:                                                               #Active document is PPRDocument
        current_document: PPRDocument = caa.active_document
    else:
        print("A CATProcess document must be the active document.")                                         #Print error message
        exit()

    processes = current_document.processes                                                                  #Get process list
    
    workbook = xlsxwriter.Workbook('Process_Table.xlsx')                                                    #Create new excel file
    
    heading_format = workbook.add_format()                                                                  #Create new format fo headings
    heading_format.set_font_name('Century')                                                                 #Set font for heading
    heading_format.set_bold()                                                                               #Set heading to bold
    heading_format.set_font_size(14)                                                                        #Set font size
    heading_format.set_center_across()                                                                      #Centre text
    
    line_format_1 = workbook.add_format()                                                                   #Create new format for text
    line_format_1.set_font_name('Century')                                                                  #Set font
    line_format_1.set_font_size(12)                                                                         #Set font size                                        

    for process_index in range(processes.count):                                                            #Cycle through all processes
        activity = processes.item(process_index + 1)                                                        #Get process
        
        part_operations = activity.children_activities                                                      #Get collection of Part operations for process
        
        for part_operation_index in  range(part_operations.count):                                          #Cycle through all operations
            part_op = part_operations.item(part_operation_index + 1)                                        #Get Operation
            
            if part_op.type == "ManufacturingSetup":                                                        #Check for Part operation
                worksheet = workbook.add_worksheet(part_op.name)                                            #Create new sheet in workbook
                worksheet.set_landscape()                                                                   #Set shet to landscape
                row = 0                                                                                     #Set row counter to 0
                
                #Add headings to sheet
                worksheet.write(0, 0, "Program Name", heading_format)
                worksheet.write(0, 1, "Description", heading_format)
                worksheet.write(0, 2, "Tool", heading_format)
                worksheet.write(0, 3, "Stepover", heading_format)
                worksheet.write(0, 4, "MC Tolerance", heading_format)
                worksheet.write(0, 5, "Depth of Cut",heading_format)
                worksheet.write(0, 6, "Offset on Part", heading_format)
                worksheet.write(0, 7, "Offset on Check", heading_format)
                worksheet.write(0, 8, "Depth of cut by level", heading_format)
                
                
                manufacturing_programs = part_op.children_activities                                        #Get all activities for part operation
                
                for man_index in range(manufacturing_programs.count):                                       #Cycle through all activities
                    man_prog = manufacturing_programs.item(man_index + 1)                                   #Get an activiy
                    
                    if man_prog.type == "ManufacturingProgram":                                             #Check if activity is program
                        row = row + 1                                                                       #Add a new row for program
                        worksheet.write(row, 0, man_prog.name, line_format_1)                               #Write program name to sheet
                        
                        man_prog_desc = man_prog.description                                                #Get decription for program
                        if man_prog_desc.find("No Description") != -1:                                      #If default descriptin
                            man_prog_desc = ""                                                              #Set to empty
                        
                        worksheet.write(row, 1, man_prog_desc, line_format_1)                               #Write description to sheet
                        
                        if man_prog.children_activities.count > 1:                                          #If the program has activities
                            tool_changes = man_prog.children_activities                                     #Get activites for program
                            
                            tool_change_counter = 0                                                         #Count how many tool changes
                            operation_counter = 0                                                           #Count how many perations
                            
                            for tool_change_index in range(tool_changes.count):                             #Cycle through all activities of program
                                
                                if tool_changes.item(tool_change_index + 1).type == "ToolChange":           #If activity is Tool Change
                                    
                                    worksheet.write(row + tool_change_counter, 2, tool_changes.item(
                                            tool_change_index + 1).resources.item(1).name.split("(")[0], 
                                            line_format_1)                                                  #Write tool name and number to sheet, stripping extra info
                                    tool_change_counter = tool_change_counter + 1                           #Increment tool change count
                                    
                                elif tool_changes.item(tool_change_index + 1).type == "Start":              #Skip Start activity
                                    continue
                                    
                                elif tool_changes.item(tool_change_index + 1).type == "Stop":               #Skip Stop activity
                                    continue
                                    
                                else:                                                                       #All remaining activiies are operations
                                    tool_changes_parameters = tool_changes.item(
                                            tool_change_index + 1).parameters                               #Get collection of parameters for current activity
                                    
                                    for t_parmeter_index in [26,27,73,79,84,90,144,192,195,229,230,233,247,252]:#Cycle through parameters, only for indexes that have data that we want
                                    
                                        if tool_changes_parameters.item(
                                                t_parmeter_index + 1 ).name.find("Maximum distance") != -1: #Look for Maximum distance parameter (Stepover distance)
                                            worksheet.write(row + operation_counter, 3, 
                                                    tool_changes_parameters.item(t_parmeter_index + 1 
                                                    ).value_as_string(), line_format_1)                     #Write value to sheet
                                        
                                        if tool_changes_parameters.item(
                                                t_parmeter_index + 1 ).name.find("Machining tolerance") != -1:  #Find tolerance parameter
                                            worksheet.write(row + operation_counter, 4, 
                                                    tool_changes_parameters.item(t_parmeter_index + 1 
                                                    ).value_as_string(), line_format_1)                     #Write value to sheet
                                            
                                        if tool_changes_parameters.item(
                                                t_parmeter_index + 1 ).name.find("Maximum depth of cut") != -1: #Find depth of cut
                                            worksheet.write(row + operation_counter, 5, 
                                                    tool_changes_parameters.item(t_parmeter_index + 1 
                                                    ).value_as_string(), line_format_1)                     #Write value to sheet
 
                                        if tool_changes_parameters.item(
                                                t_parmeter_index + 1 ).name.find("Offset on part") != -1:   #Find offset on part value
                                            worksheet.write(row + operation_counter, 6, 
                                                    tool_changes_parameters.item(t_parmeter_index + 1 
                                                    ).value_as_string(), line_format_1)                     #Write value to shet
 
                                        if tool_changes_parameters.item(
                                                t_parmeter_index + 1 ).name.find("Offset on check") != -1:  #Find Offset on check pararmeter
                                            worksheet.write(row + operation_counter, 7, 
                                                    tool_changes_parameters.item(t_parmeter_index + 1 
                                                    ).value_as_string(), line_format_1)                     #Write to sheet
                                            
                                        if tool_changes_parameters.item(
                                                t_parmeter_index + 1 
                                                ).name.find("Depth of cut by level for Multi-Pass") != -1:  #Look for depth of cut parameter
                                            worksheet.write(row + operation_counter, 8, 
                                                    tool_changes_parameters.item(t_parmeter_index + 1 
                                                    ).value_as_string(), line_format_1)                     #Write to sheet
 
                                    operation_counter = operation_counter + 1                               #Add row for next operation
                                    
                            row = row + tool_change_counter + operation_counter - 1                         #Update row counter for next manufacturing program
            
                worksheet.autofit()                                                                         #Autofit sheet
                worksheet.fit_to_pages(1, 0)                                                                #Set print width to one sheet, and hight to unlimited
                      
    workbook.close()                                                                                        #Save and close workbook