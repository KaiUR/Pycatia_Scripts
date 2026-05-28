'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Export_Process_Table_Parameters.py
    Version:        1.3
    Code:           Python3.10.4, Pycatia 0.9.5
    Release:        V5R32
    Purpose:        Exports parameters from process table to excel
    Author:         Kai-Uwe Rathjen
    Date:           29.04.26
    Description:    This script will export all of the parameters in the process table for all part operations
                    and insert them into excel.

                    This script is to get all parameters for all manufacturing programs into one place so we can check our values to ensure
                    they are correct.

                    *** Only tested with sweep, pencil and contour driven so far***
    dependencies = [
                    "pycatia",
                    "xlsxwriter",
                    ]
    requirements:   Python >= 3.9
                    pycatia >= 0.9.5 (There is a bug in privious vesrions, scritp will not work)
                    xlsxwriter
                    Catia V5 running wtih an open process containing a part operation with a program and operation.
                    This script needs an open part process document.
    -----------------------------------------------------------------------------------------------------------------------

    Change:         29.04.26 1.1: Fixed script not showing part offset value for sweeps.
                    11.05.26 1.2: Improved Excel formatting — navy header, alternating row bands, centred numeric columns, frozen header row, navy tab colour, explicit column widths.
                    28.05.26 1.3: Added Operation column (between Description and Tool) showing the activity type (Sweep, Pencil, Contour...).

    -----------------------------------------------------------------------------------------------------------------------
'''

#Imports
from pycatia import catia
from pycatia.dmaps_interfaces.process_document import ProcessDocument
from pycatia.dmaps_interfaces.activities import Activities
from pycatia.dmaps_interfaces.activity import Activity
from pycatia.ppr_interfaces.ppr_document import PPRDocument
import xlsxwriter
import os

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

    # --- Formats ---
    FONT        = 'Century'
    HDR_BG      = '#1F3864'   # Dark navy
    HDR_FG      = '#FFFFFF'
    PROG_BG     = '#D6E4F0'   # Soft blue for program rows
    ROW_BG_ODD  = '#FFFFFF'
    ROW_BG_EVEN = '#EEF2F7'   # Very light blue-grey for alternating rows
    BORDER_CLR  = '#B0BEC5'

    def _base(bg, bold=False, size=11, font=FONT, color='#000000', align='left', valign='vcenter'):
        fmt = workbook.add_format({
            'font_name':  font,
            'font_size':  size,
            'bold':       bold,
            'font_color': color,
            'bg_color':   bg,
            'align':      align,
            'valign':     valign,
            'border':     1,
            'border_color': BORDER_CLR,
        })
        return fmt

    heading_format  = _base(HDR_BG, bold=True, size=11, color=HDR_FG, align='center')   #Column heading
    prog_fmt        = _base(PROG_BG, bold=True, size=11)                                 #Program name row
    prog_desc_fmt   = _base(PROG_BG, bold=False, size=11)                               #Program description row
    line_format_1   = _base(ROW_BG_ODD,  size=11)                                       #Operation row (odd)
    line_format_2   = _base(ROW_BG_EVEN, size=11)                                       #Operation row (even)
    num_fmt_1       = _base(ROW_BG_ODD,  size=11, align='center')                       #Numeric cell (odd)
    num_fmt_2       = _base(ROW_BG_EVEN, size=11, align='center')                       #Numeric cell (even)
    line_format_1_bold = _base(ROW_BG_ODD,  bold=True, size=11)                        #Bold operation row (odd) — programme name cell
    line_format_2_bold = _base(ROW_BG_EVEN, bold=True, size=11)                        #Bold operation row (even) — programme name cell

    DEBUG_PARAMS = False                                                                                    #Set to True to print all parameter names and indices for each operation
                                                                                                            #Useful for discovering indices when adding support for new operation types
                                                                                                            #Set back to False for normal use

    used_sheet_names = set()                                                                                 #Track sheet names to avoid duplicates

    def unique_sheet_name(name):                                                                             #Return a unique sheet name <= 31 chars
        base = name[:31]
        if base not in used_sheet_names:
            used_sheet_names.add(base)
            return base
        counter = 2
        while True:
            suffix = f"_{counter}"
            candidate = name[:31 - len(suffix)] + suffix
            if candidate not in used_sheet_names:
                used_sheet_names.add(candidate)
                return candidate
            counter += 1

    for process_index in range(processes.count):                                                            #Cycle through all processes
        activity = processes.item(process_index + 1)                                                        #Get process
        
        part_operations = activity.children_activities                                                      #Get collection of Part operations for process
        
        for part_operation_index in  range(part_operations.count):                                          #Cycle through all operations
            part_op = part_operations.item(part_operation_index + 1)                                        #Get Operation
            
            if part_op.type == "ManufacturingSetup":                                                        #Check for Part operation
                sheet_name = unique_sheet_name(part_op.name)                                                 #Unique sheet name, max 31 chars
                worksheet = workbook.add_worksheet(sheet_name)                                              #Create new sheet in workbook
                worksheet.set_landscape()                                                                   #Set sheet to landscape
                worksheet.set_row(0, 22)                                                                    #Header row height
                worksheet.freeze_panes(1, 0)                                                                #Freeze header row
                worksheet.set_tab_color('#1F3864')                                                          #Navy tab colour

                #Set column widths
                worksheet.set_column(0, 0, 28)   # Program Name
                worksheet.set_column(1, 1, 32)   # Description
                worksheet.set_column(2, 2, 20)   # Operation
                worksheet.set_column(3, 3, 30)   # Tool
                worksheet.set_column(4, 4, 14)   # Stepover
                worksheet.set_column(5, 5, 16)   # MC Tolerance
                worksheet.set_column(6, 6, 16)   # Depth of Cut
                worksheet.set_column(7, 7, 16)   # Offset on Part
                worksheet.set_column(8, 8, 17)   # Offset on Check
                worksheet.set_column(9, 9, 22)   # Depth of cut by level

                row = 0                                                                                     #Set row counter to 0

                #Add headings to sheet
                worksheet.write(0, 0, "Program Name",          heading_format)
                worksheet.write(0, 1, "Description",           heading_format)
                worksheet.write(0, 2, "Operation",             heading_format)
                worksheet.write(0, 3, "Tool",                  heading_format)
                worksheet.write(0, 4, "Stepover",              heading_format)
                worksheet.write(0, 5, "MC Tolerance",          heading_format)
                worksheet.write(0, 6, "Depth of Cut",          heading_format)
                worksheet.write(0, 7, "Offset on Part",        heading_format)
                worksheet.write(0, 8, "Offset on Check",       heading_format)
                worksheet.write(0, 9, "Depth of Cut by Level", heading_format)
                
                
                manufacturing_programs = part_op.children_activities                                        #Get all activities for part operation
                global_op_index = 0                                                                        #Global counter for alternating row colours across all programs

                for man_index in range(manufacturing_programs.count):                                       #Cycle through all activities
                    man_prog = manufacturing_programs.item(man_index + 1)                                   #Get an activiy
                    
                    if man_prog.type == "ManufacturingProgram":                                             #Check if activity is program
                        row = row + 1                                                                       #Add a new row for program
                        worksheet.write(row, 0, man_prog.name, prog_fmt)                                    #Write program name to sheet

                        man_prog_desc = man_prog.description                                                #Get description for program
                        if man_prog_desc.find("No Description") != -1:                                      #If default description
                            man_prog_desc = ""                                                              #Set to empty

                        worksheet.write(row, 1, man_prog_desc, prog_desc_fmt)                               #Write description to sheet
                        for _col in range(2, 10):                                                           #Fill remaining columns with programme row background
                            worksheet.write_blank(row, _col, None, prog_fmt)
                        
                        if man_prog.children_activities.count > 1:                                          #If the program has activities
                            tool_changes = man_prog.children_activities                                     #Get activities for program

                            tool_change_counter = 0                                                         #Count how many tool changes
                            operation_counter = 0                                                           #Count how many operations

                            alt_fmt      = line_format_1      if global_op_index % 2 == 0 else line_format_2      #Alternating colour for this program's row
                            alt_fmt_bold = line_format_1_bold if global_op_index % 2 == 0 else line_format_2_bold #Bold variant for programme name cell
                            worksheet.write(row, 0, man_prog.name, alt_fmt_bold)                           #Overwrite name cell — bold, alternating colour
                            worksheet.write(row, 1, man_prog_desc, alt_fmt)                                #Overwrite description cell with alternating colour
                            for _col in range(2, 10):
                                worksheet.write_blank(row, _col, None, alt_fmt)                            #Overwrite remaining cells with alternating colour

                            for tool_change_index in range(tool_changes.count):                             #Cycle through all activities of program

                                if tool_changes.item(tool_change_index + 1).type == "ToolChange":           #If activity is Tool Change
                                    r_fmt = line_format_1 if global_op_index % 2 == 0 else line_format_2
                                    worksheet.write(row + tool_change_counter, 3, tool_changes.item(
                                            tool_change_index + 1).resources.item(1).name.split("(")[0],
                                            r_fmt)                                                          #Write tool name, stripping extra info
                                    tool_change_counter = tool_change_counter + 1                           #Increment tool change count

                                elif tool_changes.item(tool_change_index + 1).type == "Start":              #Skip Start activity
                                    continue

                                elif tool_changes.item(tool_change_index + 1).type == "Stop":               #Skip Stop activity
                                    continue

                                else:                                                                       #All remaining activities are operations
                                    tool_changes_parameters = tool_changes.item(
                                            tool_change_index + 1).parameters                               #Get collection of parameters for current activity

                                    r_fmt  = line_format_1 if global_op_index % 2 == 0 else line_format_2  #Alternating row colour
                                    n_fmt  = num_fmt_1     if global_op_index % 2 == 0 else num_fmt_2      #Alternating numeric cell colour

                                    op_type = tool_changes.item(tool_change_index + 1).type                #Operation type (e.g. "ManufacturingM3xSweep")
                                    op_label = op_type.replace("Manufacturing", "")                        #Strip "Manufacturing" prefix
                                    if op_label == "M3xBitangency":
                                        op_label = "PencilTrace"
                                    elif op_label.startswith("M3x"):
                                        op_label = op_label[3:]                                            #Strip "M3x" prefix
                                    worksheet.write(row + operation_counter, 2, op_label, r_fmt)           #Write operation type

                                    if DEBUG_PARAMS:                                                        #If debug mode is on, print all parameter names and indices
                                        print(f"--- Operation: {tool_changes.item(tool_change_index + 1).name} ---")
                                        for i in range(tool_changes_parameters.count):                     #Loop through all parameters
                                            print(f"  [{i}] {tool_changes_parameters.item(i + 1).name}")  #Print index and name

                                    for t_parmeter_index in [26,27,73,79,84,90,144,192,195,229,230,232,233,247,252]: #Cycle through relevant parameter indices

                                        if tool_changes_parameters.item(
                                                t_parmeter_index + 1).name.find("Maximum distance") != -1: #Stepover distance
                                            worksheet.write(row + operation_counter, 4,
                                                    tool_changes_parameters.item(t_parmeter_index + 1
                                                    ).value_as_string(), n_fmt)
                                        if tool_changes_parameters.item(
                                                t_parmeter_index + 1).name.find("Machining tolerance") != -1: #Machining tolerance
                                            worksheet.write(row + operation_counter, 5,
                                                    tool_changes_parameters.item(t_parmeter_index + 1
                                                    ).value_as_string(), n_fmt)
                                        if tool_changes_parameters.item(
                                                t_parmeter_index + 1).name.find("Maximum depth of cut") != -1 or tool_changes_parameters.item(
                                                t_parmeter_index + 1).name.find("Depth of cut by level for Multi-Pas") != -1: #Depth of cut
                                            worksheet.write(row + operation_counter, 6,
                                                    tool_changes_parameters.item(t_parmeter_index + 1
                                                    ).value_as_string(), n_fmt)
                                        if tool_changes_parameters.item(
                                                t_parmeter_index + 1).name.find("Offset on part") != -1:   #Offset on part
                                            worksheet.write(row + operation_counter, 7,
                                                    tool_changes_parameters.item(t_parmeter_index + 1
                                                    ).value_as_string(), n_fmt)
                                        if tool_changes_parameters.item(
                                                t_parmeter_index + 1).name.find("Offset on check") != -1:  #Offset on check
                                            worksheet.write(row + operation_counter, 8,
                                                    tool_changes_parameters.item(t_parmeter_index + 1
                                                    ).value_as_string(), n_fmt)
                                        if tool_changes_parameters.item(
                                                t_parmeter_index + 1
                                                ).name.find("Depth of cut by level for Multi-Pass") != -1: #Depth of cut by level
                                            worksheet.write(row + operation_counter, 9,
                                                    tool_changes_parameters.item(t_parmeter_index + 1
                                                    ).value_as_string(), n_fmt)
                                    operation_counter = operation_counter + 1                               #Add row for next operation
                                    global_op_index = global_op_index + 1                                  #Advance global colour index

                            row = row + max(tool_change_counter, operation_counter) - 1                  #Update row counter for next manufacturing program
            
                worksheet.fit_to_pages(1, 0)                                                                #Set print width to one sheet, height unlimited
                      
    workbook.close()                                                                                        #Save and close workbook
    
    os.startfile(os.path.abspath('Process_Table.xlsx'))