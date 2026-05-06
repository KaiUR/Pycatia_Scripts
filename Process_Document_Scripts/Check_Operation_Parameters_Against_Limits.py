'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Check_Operation_Parameters_Against_Limits.py
    Version:        1.1
    Code:           Python3.10.4, Pycatia 0.9.5
    Release:        V5R32
    Purpose:        Check all operation parameters against predefined min and max limits and flag any violations.
    Author:         Kai-Uwe Rathjen
    Date:           06.05.26
    Description:    This script reads the same machining parameters as Export_Process_Table_Parameters.py but
                    instead of writing them to Excel it checks each value against predefined min and max limits.
                    Any parameter outside its limit is flagged in a result dialog. A summary of violations is
                    shown at the end. Useful as a quick sanity check before sign-off.

                    Edit the PARAMETER_LIMITS dictionary below to set your own limits for each parameter.

                    *** Only tested with sweep, pencil and contour driven so far ***
    dependencies = [
                    "pycatia",
                    "wxPython",
                    ]
    requirements:   Python >= 3.10
                    pycatia >= 0.9.5
                    wxPython
                    Catia V5 / DELMIA running with an open CATProcess document containing a part operation
                    with a program and operations.
                    This script needs an open process document.
    -----------------------------------------------------------------------------------------------------------------------

    Change:         06.05.26 1.1: Results now shown in wx dialog instead of console.

    -----------------------------------------------------------------------------------------------------------------------
'''

#Imports
from pycatia import catia
from pycatia.dmaps_interfaces.process_document import ProcessDocument
from pycatia.ppr_interfaces.ppr_document import PPRDocument
import wx
import wx.lib.dialogs

#Edit these limits to match your process requirements. Set min or max to None to skip that check.
PARAMETER_LIMITS = {
    "Maximum distance":                     {"min": 0.0,    "max": 5.0,     "unit": "mm"},  #Stepover limit
    "Machining tolerance":                  {"min": 0.0,    "max": 0.1,     "unit": "mm"},  #Tolerance limit
    "Maximum depth of cut":                 {"min": 0.0,    "max": 3.0,     "unit": "mm"},  #Depth of cut limit
    "Offset on part":                       {"min": -1.0,   "max": 1.0,     "unit": "mm"},  #Part offset limit
    "Offset on check":                      {"min": -1.0,   "max": 1.0,     "unit": "mm"},  #Check offset limit
    "Depth of cut by level for Multi-Pass": {"min": 0.0,    "max": 3.0,     "unit": "mm"},  #Depth by level limit
}

if __name__ == "__main__":
    caa = catia()                                                                                               #Catia application instance
    check_document = caa.active_document                                                                        #Current Active Document
    current_document = None

    app = wx.App(None)                                                                                          #Initilize wx application

    if type(check_document) is ProcessDocument:                                                                 #Active Document is ProcessDocument
        current_document: PPRDocument = check_document.ppr_document                                             #Get PPRDocument
    elif type(check_document) is PPRDocument:                                                                   #Active document is PPRDocument
        current_document: PPRDocument = caa.active_document
    else:
        wx.MessageDialog(None, "A CATProcess document must be the active document.", "Error",
                wx.OK | wx.ICON_ERROR | wx.STAY_ON_TOP).ShowModal()                                             #Show error dialog
        exit()

    processes = current_document.processes                                                                      #Get process list

    violation_count = 0                                                                                         #Count total violations
    operation_count = 0                                                                                         #Count total operations checked
    report_lines = []                                                                                           #List to build report lines

    known_indices = [26,27,73,79,84,90,144,192,195,229,230,232,233,247,252]                                     #Known parameter indices across all tested operation types

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

                            if tool_changes.item(tool_change_index + 1).type == "ToolChange":                   #Skip tool changes
                                continue
                            elif tool_changes.item(tool_change_index + 1).type == "Start":                      #Skip Start activity
                                continue
                            elif tool_changes.item(tool_change_index + 1).type == "Stop":                       #Skip Stop activity
                                continue
                            else:                                                                               #All remaining activities are operations
                                operation = tool_changes.item(tool_change_index + 1)                            #Get operation
                                operation_count = operation_count + 1                                           #Increment operation count
                                tool_changes_parameters = operation.parameters                                  #Get collection of parameters

                                found_params = {}                                                               #Dict to store found parameter values

                                for t_parmeter_index in known_indices:                                          #Cycle through known parameter indices
                                    for param_name in PARAMETER_LIMITS.keys():                                  #Check each target parameter
                                        if tool_changes_parameters.item(t_parmeter_index + 1).name.find(param_name) != -1: #If parameter found
                                            try:
                                                val_str = tool_changes_parameters.item(
                                                        t_parmeter_index + 1).value_as_string()                #Get value string
                                                val = float(val_str.replace("mm", "").replace("deg", "").strip()) #Parse numeric value
                                                found_params[param_name] = val                                  #Store found value
                                            except:
                                                pass                                                            #Skip if value cannot be parsed

                                for param_name, value in found_params.items():                                  #Check each found parameter against limits
                                    limits = PARAMETER_LIMITS[param_name]                                       #Get limits for this parameter
                                    violated = False                                                             #Flag for violation

                                    if limits["min"] is not None and value < limits["min"]:                     #Check minimum limit
                                        violated = True
                                        direction = f"below minimum ({limits['min']}{limits['unit']})"
                                    elif limits["max"] is not None and value > limits["max"]:                   #Check maximum limit
                                        violated = True
                                        direction = f"above maximum ({limits['max']}{limits['unit']})"

                                    if violated:                                                                #If limit violated
                                        violation_count = violation_count + 1                                   #Increment violation count
                                        report_lines.append(f"*** VIOLATION ***")
                                        report_lines.append(f"  Part Op:   {part_op.name}")
                                        report_lines.append(f"  Program:   {man_prog.name}")
                                        report_lines.append(f"  Operation: {operation.name}")
                                        report_lines.append(f"  Parameter: {param_name}")
                                        report_lines.append(f"  Value:     {value}{limits['unit']} - {direction}")
                                        report_lines.append("")                                                 #Blank line between violations

    summary = f"{operation_count} operation(s) checked, {violation_count} violation(s) found."                 #Build summary string

    if violation_count == 0:                                                                                    #If no violations
        wx.MessageDialog(None, f"No violations found.\n\n{summary}",
                "Parameter Check - All OK",
                wx.OK | wx.ICON_INFORMATION | wx.STAY_ON_TOP).ShowModal()                                       #Show clean result dialog
    else:                                                                                                       #If violations found
        report_lines.insert(0, summary + "\n" + "-" * 60 + "\n")                                               #Insert summary at top of report
        report_text = "\n".join(report_lines)                                                                   #Join report lines into single string

        wx.lib.dialogs.ScrolledMessageDialog(None, report_text,
                "Parameter Check - Violations Found",
                size=(550, 450)).ShowModal()                                                                     #Show scrollable violations report dialog
