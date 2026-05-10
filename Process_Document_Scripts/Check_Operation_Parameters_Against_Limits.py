'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Check_Operation_Parameters_Against_Limits.py
    Version:        1.3
    Code:           Python3.10.4, Pycatia 0.9.5
    Release:        V5R32
    Purpose:        Check all operation parameters against configurable min and max limits and flag any violations.
    Author:         Kai-Uwe Rathjen
    Date:           06.05.26
    Description:    This script reads the same machining parameters as Export_Process_Table_Parameters.py but
                    instead of writing them to Excel it checks each value against configurable min and max limits.
                    A dialog box lets the user review and change the limits before each run. Settings are saved
                    between sessions. Any parameter outside its limit is flagged in a result dialog.
                    Useful as a quick sanity check before sign-off.

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
                    10.05.26 1.2: Limits are now configured via a dialog box with saved settings.
                    10.05.26 1.3: Settings path moved to %APPDATA%\pycatia_scripts\<script_name>.

    -----------------------------------------------------------------------------------------------------------------------
'''

#Imports
from pycatia import catia
from pycatia.dmaps_interfaces.process_document import ProcessDocument
from pycatia.ppr_interfaces.ppr_document import PPRDocument
import wx
import wx.lib.dialogs
import os
import json

PARAM_ORDER = [
    "Maximum distance",
    "Machining tolerance",
    "Maximum depth of cut",
    "Offset on part",
    "Offset on check",
    "Depth of cut by level for Multi-Pass",
]

class LimitsDialog(wx.Dialog):
    def __init__(self, parent, title, settings_file):
        self.settings_file = settings_file
        self.hardcoded_defaults = {
            "Maximum distance":                     {"min": "0.0",  "max": "5.0"},   #Stepover limit
            "Machining tolerance":                  {"min": "0.0",  "max": "0.1"},   #Tolerance limit
            "Maximum depth of cut":                 {"min": "0.0",  "max": "3.0"},   #Depth of cut limit
            "Offset on part":                       {"min": "-1.0", "max": "1.0"},   #Part offset limit
            "Offset on check":                      {"min": "-1.0", "max": "1.0"},   #Check offset limit
            "Depth of cut by level for Multi-Pass": {"min": "0.0",  "max": "3.0"},   #Depth by level limit
        }

        defaults = {k: v.copy() for k, v in self.hardcoded_defaults.items()}

        if os.path.exists(settings_file):
            try:
                with open(settings_file, 'r') as f:
                    saved = json.load(f)
                for param in defaults:
                    if param in saved:
                        defaults[param].update(saved[param])
            except:
                pass

        super().__init__(parent, title=title, size=(560, 370))

        vbox = wx.BoxSizer(wx.VERTICAL)

        #Header row
        header = wx.FlexGridSizer(1, 4, 5, 10)
        header.Add(wx.StaticText(self, label="Parameter"),         1, wx.EXPAND)
        header.Add(wx.StaticText(self, label="Min (mm)"),          0)
        header.Add(wx.StaticText(self, label="Max (mm)"),          0)
        header.Add(wx.StaticText(self, label="Unit"),              0)
        header.AddGrowableCol(0, 1)
        vbox.Add(header, 0, wx.LEFT | wx.RIGHT | wx.TOP | wx.EXPAND, 15)

        vbox.Add(wx.StaticLine(self), 0, wx.LEFT | wx.RIGHT | wx.EXPAND, 15)

        #Parameter rows
        self.param_controls = {}

        grid = wx.FlexGridSizer(len(PARAM_ORDER), 4, 8, 10)
        grid.AddGrowableCol(0, 1)

        for param in PARAM_ORDER:
            vals = defaults[param]
            min_ctrl = wx.TextCtrl(self, value=vals["min"], size=(80, -1))
            max_ctrl = wx.TextCtrl(self, value=vals["max"], size=(80, -1))
            min_ctrl.SetToolTip("Minimum allowed value. Leave blank to skip this check.")
            max_ctrl.SetToolTip("Maximum allowed value. Leave blank to skip this check.")
            self.param_controls[param] = {"min": min_ctrl, "max": max_ctrl}

            grid.Add(wx.StaticText(self, label=param + ":"), 1, wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)
            grid.Add(min_ctrl, 0)
            grid.Add(max_ctrl, 0)
            grid.Add(wx.StaticText(self, label="mm"),        0, wx.ALIGN_CENTER_VERTICAL)

        vbox.Add(grid, 1, wx.ALL | wx.EXPAND, 15)

        note = wx.StaticText(self, label="Leave a field blank to skip that check for the parameter.")
        note.SetForegroundColour(wx.Colour(100, 100, 100))
        vbox.Add(note, 0, wx.LEFT | wx.BOTTOM, 15)

        #Buttons
        std_btn_sizer = self.CreateButtonSizer(wx.OK | wx.CANCEL | wx.HELP)
        reset_btn = wx.Button(self, label="Reset Defaults")
        clear_btn = wx.Button(self, label="Clear Saved")

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        btn_row.Add(reset_btn,       0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        btn_row.Add(clear_btn,       0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        btn_row.Add(std_btn_sizer,   0, wx.ALL, 5)

        vbox.Add(btn_row, 0, wx.ALIGN_CENTER | wx.BOTTOM, 10)

        self.SetSizer(vbox)
        self.Center()

        self.Bind(wx.EVT_BUTTON, self.on_help,          id=wx.ID_HELP)
        reset_btn.Bind(wx.EVT_BUTTON, self.on_reset)
        clear_btn.Bind(wx.EVT_BUTTON, self.on_clear_settings)

    def on_reset(self, event):
        success_color = wx.Colour(200, 255, 200)
        default_color = wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW)
        all_ctrls = []

        for param, vals in self.hardcoded_defaults.items():
            ctrls = self.param_controls[param]
            ctrls["min"].SetValue(vals["min"])
            ctrls["max"].SetValue(vals["max"])
            for ctrl in (ctrls["min"], ctrls["max"]):
                ctrl.SetBackgroundColour(success_color)
                ctrl.Refresh()
                all_ctrls.append(ctrl)

        wx.CallLater(500, self._clear_feedback_colors, all_ctrls, default_color)

    def _clear_feedback_colors(self, controls, color):
        for ctrl in controls:
            ctrl.SetBackgroundColour(color)
            ctrl.Refresh()

    def on_clear_settings(self, event):
        if os.path.exists(self.settings_file):
            try:
                os.remove(self.settings_file)
                wx.MessageBox("Saved settings deleted.", "Settings Cleared", wx.OK | wx.ICON_INFORMATION)
                self.on_reset(None)
            except Exception as e:
                wx.MessageBox(f"Error deleting settings: {e}", "Error", wx.OK | wx.ICON_ERROR)
        else:
            wx.MessageBox("No saved settings file found.", "Information", wx.OK | wx.ICON_INFORMATION)

    def on_help(self, event):
        help_text = (
            "PARAMETER LIMIT CHECKER - HELP\n"
            "==========================================================================\n\n"
            "PURPOSE\n"
            "--------------------------------------------------------------------------\n"
            " Checks each machining operation in the active CATProcess document against\n"
            " the minimum and maximum limits you define here. Any parameter outside its\n"
            " limit is reported in a scrollable violations dialog at the end.\n\n"

            "PARAMETER FIELDS\n"
            "--------------------------------------------------------------------------\n"
            " • Min: The minimum allowed value (mm). Leave blank to skip this check.\n\n"
            " • Max: The maximum allowed value (mm). Leave blank to skip this check.\n\n"

            "PARAMETERS CHECKED\n"
            "--------------------------------------------------------------------------\n"
            " • Maximum distance         Stepover — max distance between passes.\n"
            " • Machining tolerance      Max allowable surface tolerance.\n"
            " • Maximum depth of cut     Maximum axial depth per pass.\n"
            " • Offset on part           Surface offset applied to the machined part.\n"
            " • Offset on check          Surface offset applied to check surfaces.\n"
            " • Depth of cut by level    Depth per level for multi-pass operations.\n\n"

            "BUTTONS\n"
            "--------------------------------------------------------------------------\n"
            " [OK]             Saves the current limits and runs the parameter check.\n"
            " [Cancel]         Exits without running the check.\n"
            " [Reset Defaults] Restores factory default values (fields flash green).\n"
            " [Clear Saved]    Deletes the saved JSON settings file and resets the UI.\n"
            " [Help]           Opens this window.\n\n"

            "SETTINGS PERSISTENCE\n"
            "--------------------------------------------------------------------------\n"
            " Limits are saved automatically to:\n"
            "   %%APPDATA%%\\pycatia_scripts\\Check_Operation_Parameters_Against_Limits\\user_settings.json\n\n"
            " The saved values are pre-filled each time the script is run.\n"
            " Use [Clear Saved] to return to factory defaults.\n\n"

            "NOTES\n"
            "--------------------------------------------------------------------------\n"
            " Only tested with Sweep, Pencil, and Contour Driven operations.\n"
            " See the Export Process Table Parameters script for adding new types."
        )
        dlg = wx.lib.dialogs.ScrolledMessageDialog(self, help_text, "Help")
        mono_font = wx.Font(10, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        dlg.text.SetFont(mono_font)
        dlg.SetSize((620, 560))
        dlg.CenterOnParent()
        dlg.ShowModal()
        dlg.Destroy()

    def get_limits(self):
        """Returns PARAMETER_LIMITS dict from dialog values. Empty fields become None."""
        limits = {}
        for param in PARAM_ORDER:
            ctrls = self.param_controls[param]
            min_str = ctrls["min"].GetValue().strip()
            max_str = ctrls["max"].GetValue().strip()
            try:
                min_val = float(min_str) if min_str else None
            except ValueError:
                min_val = None
            try:
                max_val = float(max_str) if max_str else None
            except ValueError:
                max_val = None
            limits[param] = {"min": min_val, "max": max_val, "unit": "mm"}
        return limits

    def get_settings_to_save(self):
        """Returns the raw string values for JSON serialization."""
        settings = {}
        for param in PARAM_ORDER:
            ctrls = self.param_controls[param]
            settings[param] = {
                "min": ctrls["min"].GetValue().strip(),
                "max": ctrls["max"].GetValue().strip(),
            }
        return settings

if __name__ == "__main__":
    SETTINGS_DIR  = os.path.join(os.environ['APPDATA'], 'pycatia_scripts', 'Check_Operation_Parameters_Against_Limits') #User settings directory
    SETTINGS_FILE = os.path.join(SETTINGS_DIR, 'user_settings.json')                                             #User settings file

    if not os.path.exists(SETTINGS_DIR):                                                                          #Create directory if it does not exist
        os.makedirs(SETTINGS_DIR)

    caa = catia()                                                                                                  #Catia application instance
    check_document = caa.active_document                                                                          #Current Active Document
    current_document = None

    app = wx.App(None)                                                                                            #Initilize wx application

    if type(check_document) is ProcessDocument:                                                                   #Active Document is ProcessDocument
        current_document: PPRDocument = check_document.ppr_document                                               #Get PPRDocument
    elif type(check_document) is PPRDocument:                                                                     #Active document is PPRDocument
        current_document: PPRDocument = caa.active_document
    else:
        wx.MessageDialog(None, "A CATProcess document must be the active document.", "Error",
                wx.OK | wx.ICON_ERROR | wx.STAY_ON_TOP).ShowModal()                                               #Show error dialog
        exit()

    dlg = LimitsDialog(None, "Parameter Limit Checker - Set Limits", SETTINGS_FILE)                               #Show limits dialog

    if dlg.ShowModal() != wx.ID_OK:                                                                               #User cancelled
        dlg.Destroy()
        exit()

    PARAMETER_LIMITS = dlg.get_limits()                                                                           #Get limits from dialog

    with open(SETTINGS_FILE, 'w') as f:                                                                           #Save settings to file
        json.dump(dlg.get_settings_to_save(), f, indent=4)

    dlg.Destroy()

    processes = current_document.processes                                                                         #Get process list

    violation_count = 0                                                                                           #Count total violations
    operation_count = 0                                                                                           #Count total operations checked
    report_lines = []                                                                                             #List to build report lines

    known_indices = [26,27,73,79,84,90,144,192,195,229,230,232,233,247,252]                                       #Known parameter indices across all tested operation types

    for process_index in range(processes.count):                                                                   #Cycle through all processes
        activity = processes.item(process_index + 1)                                                              #Get process

        part_operations = activity.children_activities                                                            #Get collection of Part operations for process

        for part_operation_index in range(part_operations.count):                                                  #Cycle through all operations
            part_op = part_operations.item(part_operation_index + 1)                                              #Get Operation

            if part_op.type == "ManufacturingSetup":                                                              #Check for Part operation
                manufacturing_programs = part_op.children_activities                                              #Get all activities for part operation

                for man_index in range(manufacturing_programs.count):                                              #Cycle through all activities
                    man_prog = manufacturing_programs.item(man_index + 1)                                         #Get an activity

                    if man_prog.type == "ManufacturingProgram":                                                    #Check if activity is program
                        tool_changes = man_prog.children_activities                                               #Get activities for program

                        for tool_change_index in range(tool_changes.count):                                       #Cycle through all activities of program

                            if tool_changes.item(tool_change_index + 1).type == "ToolChange":                     #Skip tool changes
                                continue
                            elif tool_changes.item(tool_change_index + 1).type == "Start":                        #Skip Start activity
                                continue
                            elif tool_changes.item(tool_change_index + 1).type == "Stop":                         #Skip Stop activity
                                continue
                            else:                                                                                  #All remaining activities are operations
                                operation = tool_changes.item(tool_change_index + 1)                              #Get operation
                                operation_count = operation_count + 1                                             #Increment operation count
                                tool_changes_parameters = operation.parameters                                    #Get collection of parameters

                                found_params = {}                                                                 #Dict to store found parameter values

                                for t_parmeter_index in known_indices:                                            #Cycle through known parameter indices
                                    for param_name in PARAMETER_LIMITS.keys():                                    #Check each target parameter
                                        if tool_changes_parameters.item(t_parmeter_index + 1).name.find(param_name) != -1: #If parameter found
                                            try:
                                                val_str = tool_changes_parameters.item(
                                                        t_parmeter_index + 1).value_as_string()                  #Get value string
                                                val = float(val_str.replace("mm", "").replace("deg", "").strip()) #Parse numeric value
                                                found_params[param_name] = val                                    #Store found value
                                            except:
                                                pass                                                              #Skip if value cannot be parsed

                                for param_name, value in found_params.items():                                    #Check each found parameter against limits
                                    limits = PARAMETER_LIMITS[param_name]                                         #Get limits for this parameter
                                    violated = False                                                               #Flag for violation

                                    if limits["min"] is not None and value < limits["min"]:                       #Check minimum limit
                                        violated = True
                                        direction = f"below minimum ({limits['min']}{limits['unit']})"
                                    elif limits["max"] is not None and value > limits["max"]:                     #Check maximum limit
                                        violated = True
                                        direction = f"above maximum ({limits['max']}{limits['unit']})"

                                    if violated:                                                                  #If limit violated
                                        violation_count = violation_count + 1                                     #Increment violation count
                                        report_lines.append(f"*** VIOLATION ***")
                                        report_lines.append(f"  Part Op:   {part_op.name}")
                                        report_lines.append(f"  Program:   {man_prog.name}")
                                        report_lines.append(f"  Operation: {operation.name}")
                                        report_lines.append(f"  Parameter: {param_name}")
                                        report_lines.append(f"  Value:     {value}{limits['unit']} - {direction}")
                                        report_lines.append("")                                                   #Blank line between violations

    summary = f"{operation_count} operation(s) checked, {violation_count} violation(s) found."                   #Build summary string

    if violation_count == 0:                                                                                      #If no violations
        wx.MessageDialog(None, f"No violations found.\n\n{summary}",
                "Parameter Check - All OK",
                wx.OK | wx.ICON_INFORMATION | wx.STAY_ON_TOP).ShowModal()                                         #Show clean result dialog
    else:                                                                                                         #If violations found
        report_lines.insert(0, summary + "\n" + "-" * 60 + "\n")                                                 #Insert summary at top of report
        report_text = "\n".join(report_lines)                                                                     #Join report lines into single string

        wx.lib.dialogs.ScrolledMessageDialog(None, report_text,
                "Parameter Check - Violations Found",
                size=(550, 450)).ShowModal()                                                                       #Show scrollable violations report dialog
