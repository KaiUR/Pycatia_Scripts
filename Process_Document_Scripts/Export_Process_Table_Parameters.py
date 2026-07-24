'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Export_Process_Table_Parameters.py
    Version:        1.6
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
                    03.06.26 1.4: Fix F401: remove unused Activities and Activity imports.
                    24.07.26 1.5: Contour driven stepover read from Step distance, the dialog value, found by
                                  scanning the parameter names. The Maximum distance the type also carries sits
                                  still whatever the dialog holds, so it is no longer written for contour driven.
                    24.07.26 1.6: Settings matched by parameter name instead of the fixed index list, the same
                                  way Manage_Program_Names_And_Comments reads them - where each setting sat is
                                  remembered per operation type and probed directly on the next operation of
                                  that type, each probed index checked by name before its value is trusted, and
                                  the full walk stops early once everything wanted has been found. Contour
                                  driven depth of cut now comes from Maximum depth of cut - the Multi-Pass
                                  depth stays set while Multi-Pass is off - and the CATIA Roughing operation's
                                  pass overlap is written as its stepover.

    -----------------------------------------------------------------------------------------------------------------------
'''

#Imports
from pycatia import catia
from pycatia.dmaps_interfaces.process_document import ProcessDocument
from pycatia.ppr_interfaces.ppr_document import PPRDocument
import xlsxwriter
import os

# The settings written to the sheet, matched on the parameter name the same way
# Manage_Program_Names_And_Comments does. The indices move between operation types, so every
# parameter is matched by name rather than read at a fixed index.
PARAMETER_COLUMNS = (
    ("Stepover", ("Maximum distance",)),
    ("MC Tolerance", ("Machining tolerance",)),
    ("Depth of Cut", ("Maximum depth of cut", "Depth of cut by level for Multi-Pas")),
    ("Offset on Part", ("Offset on part",)),
    ("Offset on Check", ("Offset on check",)),
    ("Depth of Cut by Level", ("Depth of cut by level for Multi-Pass",)),
)

PARAMETER_LABELS = tuple(label for label, _ in PARAMETER_COLUMNS)

# Operation types whose settings live under different parameter names. A contour driven
# operation's stepover is its Step distance - the dialog value, which a parameter dump shows
# moving between the semi-finish and finish operations while the Maximum distance the type
# also carries sits still - and its depth of cut is Maximum depth of cut, because the
# Multi-Pass depth stays set while Multi-Pass itself is off.
PARAMETER_OVERRIDES = {
    "M3xBetweenContour": {
        "Stepover": ("Step distance",),
        "Depth of Cut": ("Maximum depth of cut",),
    },
}

# The CATIA Roughing operation - M3xHardMaterial - states its stepover as a pass overlap: a mode
# and two values, of which the mode says which one is in force. A ratio is shown as a percentage
# of the tool diameter, a length as the distance it is.
ROUGHING_TYPE = "M3xHardMaterial"
OVERLAP_MODE = "Pass overlap mode"
OVERLAP_RATIO = "Pass overlap (diameter ratio)"
OVERLAP_LENGTH = "Pass overlap (length)"

# Where each setting sat, remembered per operation type and parameter count. Operations of one
# type lay their parameters out identically, so the first one read walks the whole list and the
# ones after it probe only the remembered indices - a handful of round trips to CATIA instead of
# hundreds. Every probed index is still checked by name before its value is trusted, which is
# what separates this from reading fixed indices; a name that no longer matches throws the entry
# away and the whole list is walked again.
PARAMETER_INDEX_CACHE = {}


'''
    This function reads the settings of one operation off remembered parameter indices.

    The indices were learned from a full walk of an earlier operation of the same type. Each one
    is checked by name before its value is taken, so a layout that differs from the remembered
    one is caught and handed back for a full walk rather than silently misread. Indices
    remembered as absent are skipped - the walk searched the whole list and found nothing.

    Inputs:
        parameters      The activity's parameters collection
        cached          The remembered entry - labels and overlap dicts of name to index
        columns         Tuple of (label, needles) in force for the activity's type
        values          Dict of label to value string, filled in place
        overlap         Dict of the Roughing operation's pass overlap pieces, filled in place

    output:
        True where every remembered index still matched its name, False where a full walk is needed
'''
def read_cached_parameters(parameters, cached, columns, values, overlap):
    needles_by_label = dict(columns)
    for label, index in cached["labels"].items():
        if index is None:
            continue                                                                                    #Absent on this operation type
        try:
            parameter = parameters.item(index + 1)
            name = parameter.name
        except Exception:
            return False
        if not any(needle in name for needle in needles_by_label.get(label, ())):
            return False                                                                                #The layout moved - the whole list must be walked
        try:
            values[label] = parameter.value_as_string()
        except Exception:
            pass
    for key, index in cached["overlap"].items():
        if index is None:
            continue
        try:
            parameter = parameters.item(index + 1)
            name = parameter.name
        except Exception:
            return False
        if key not in name:
            return False                                                                                #The layout moved - the whole list must be walked
        try:
            overlap[key] = parameter.value_as_string()
        except Exception:
            pass
    return True


'''
    This function reads the settings of one operation.

    Every parameter is walked once and matched on its name, so an operation type whose parameters
    sit at different indices still reports its settings. Types listed in PARAMETER_OVERRIDES have
    some settings read from other parameter names, and the Roughing operation's stepover is put
    together from its pass overlap mode and whichever of the two overlap values that mode is on.

    The walk stops as soon as everything wanted has a value, and where it sat is remembered in
    PARAMETER_INDEX_CACHE so the next operation of the same type probes those indices directly
    instead of walking hundreds of parameters - see the note on the cache for why that is safe.

    Inputs:
        activity        A manufacturing operation activity

    output:
        Tuple of (dict of label to value string, list of the labels that were not found)
'''
def read_operation_parameters(activity):
    values = {label: "" for label in PARAMETER_LABELS}

    try:
        activity_type = activity.type
    except Exception:
        activity_type = ""
    overrides = PARAMETER_OVERRIDES.get(activity_type, {})
    columns = tuple((label, overrides.get(label, needles)) for label, needles in PARAMETER_COLUMNS)
    overlap = {}                                                                                        #The Roughing operation's pass overlap pieces
    wanted_overlap = (OVERLAP_MODE, OVERLAP_RATIO, OVERLAP_LENGTH) if activity_type == ROUGHING_TYPE else ()

    try:
        parameters = activity.parameters
        count = parameters.count
    except Exception:
        return values, list(PARAMETER_LABELS)                                                           #No parameters at all - everything is missing

    cache_key = (activity_type, count)
    cached = PARAMETER_INDEX_CACHE.get(cache_key)
    if cached is not None and not read_cached_parameters(parameters, cached, columns, values, overlap):
        PARAMETER_INDEX_CACHE.pop(cache_key, None)                                                      #The layout moved - forget it and walk
        values = {label: "" for label in PARAMETER_LABELS}
        overlap = {}
        cached = None

    if cached is None:
        found = {"labels": {label: None for label in PARAMETER_LABELS},
                 "overlap": {key: None for key in wanted_overlap}}
        for index in range(count):
            try:
                parameter = parameters.item(index + 1)
                name = parameter.name
            except Exception:
                continue
            for key in wanted_overlap:
                if key in name and key not in overlap:
                    found["overlap"][key] = index
                    try:
                        overlap[key] = parameter.value_as_string()
                    except Exception:
                        pass
            for label, needles in columns:
                if values[label]:
                    continue                                                                            #First match wins
                if any(needle in name for needle in needles):
                    found["labels"][label] = index
                    try:
                        values[label] = parameter.value_as_string()
                    except Exception:
                        pass
            if all(values.values()) and len(overlap) == len(wanted_overlap):
                break                                                                                   #Everything wanted has a value - stop walking
        PARAMETER_INDEX_CACHE[cache_key] = found

    if activity_type == ROUGHING_TYPE and not values["Stepover"]:
        mode = overlap.get(OVERLAP_MODE, "")                                                            #M3xRatio, or one of the length modes
        if "Ratio" in mode and overlap.get(OVERLAP_RATIO):
            values["Stepover"] = overlap[OVERLAP_RATIO] + "%"                                           #A percentage of the tool diameter
        elif "Length" in mode and overlap.get(OVERLAP_LENGTH):
            values["Stepover"] = overlap[OVERLAP_LENGTH]

    missing = [label for label in PARAMETER_LABELS if not values[label]]
    return values, missing


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
                                                                                                            #Useful for discovering parameter names when adding support for new operation types
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
                                op_activity = tool_changes.item(tool_change_index + 1)                      #Get the activity once - every item call is a round trip to Catia

                                if op_activity.type == "ToolChange":                                        #If activity is Tool Change
                                    r_fmt = line_format_1 if global_op_index % 2 == 0 else line_format_2
                                    worksheet.write(row + tool_change_counter, 3,
                                            op_activity.resources.item(1).name.split("(")[0],
                                            r_fmt)                                                          #Write tool name, stripping extra info
                                    tool_change_counter = tool_change_counter + 1                           #Increment tool change count

                                elif op_activity.type == "Start":                                           #Skip Start activity
                                    continue

                                elif op_activity.type == "Stop":                                            #Skip Stop activity
                                    continue

                                else:                                                                       #All remaining activities are operations
                                    r_fmt  = line_format_1 if global_op_index % 2 == 0 else line_format_2  #Alternating row colour
                                    n_fmt  = num_fmt_1     if global_op_index % 2 == 0 else num_fmt_2      #Alternating numeric cell colour

                                    op_type = op_activity.type                                             #Operation type (e.g. "M3xSweeping")
                                    op_label = op_type.replace("Manufacturing", "")                        #Strip "Manufacturing" prefix
                                    if op_label == "M3xBitangency":
                                        op_label = "PencilTrace"
                                    elif op_label.startswith("M3x"):
                                        op_label = op_label[3:]                                            #Strip "M3x" prefix
                                    worksheet.write(row + operation_counter, 2, op_label, r_fmt)           #Write operation type

                                    if DEBUG_PARAMS:                                                        #If debug mode is on, print all parameter names and indices
                                        print(f"--- Operation: {op_activity.name} ---")
                                        debug_parameters = op_activity.parameters                          #Get collection of parameters for current activity
                                        for i in range(debug_parameters.count):                            #Loop through all parameters
                                            print(f"  [{i}] {debug_parameters.item(i + 1).name}")          #Print index and name

                                    values, _ = read_operation_parameters(op_activity)                     #Settings matched by name, remembered indices probed first
                                    for column, label in ((4, "Stepover"), (5, "MC Tolerance"),
                                                          (6, "Depth of Cut"), (7, "Offset on Part"),
                                                          (8, "Offset on Check"), (9, "Depth of Cut by Level")):
                                        if values[label]:
                                            worksheet.write(row + operation_counter, column,
                                                    values[label], n_fmt)                                  #Absent settings leave the cell blank, as before
                                    operation_counter = operation_counter + 1                               #Add row for next operation
                                    global_op_index = global_op_index + 1                                  #Advance global colour index

                            row = row + max(tool_change_counter, operation_counter) - 1                  #Update row counter for next manufacturing program
            
                worksheet.fit_to_pages(1, 0)                                                                #Set print width to one sheet, height unlimited
                      
    workbook.close()                                                                                        #Save and close workbook
    
    os.startfile(os.path.abspath('Process_Table.xlsx'))