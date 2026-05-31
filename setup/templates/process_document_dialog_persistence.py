'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Your_Script_Name.py
    Version:        1.2
    Code:           Python3.10.4, Pycatia 0.9.5
    Release:        V5R32
    Purpose:        EDIT: One line summary shown on the script button.
    Author:         EDIT: Your Name
    Date:           EDIT: DD.MM.YY
    Description:    EDIT: Full description of what the script does.
                    EDIT: Continuation lines must be indented.
                    Settings are saved between sessions.
    dependencies = [
                    "pycatia",
                    "wxPython",
                    ]
    requirements:   Python >= 3.10
                    pycatia >= 0.9.5
                    wxPython
                    Catia V5 / DELMIA running with an open CATProcess document.
    -----------------------------------------------------------------------------------------------------------------------

    Change:         12.05.26 1.1: Dialogs raised to foreground of CATIA window.
                    31.05.26 1.2: Use vbox.Fit(self) for dialog sizing.

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
import ctypes

def _bring_to_front(window):
    u32 = ctypes.windll.user32
    hwnd = window.GetHandle()
    fg_hwnd = u32.GetForegroundWindow()
    fg_tid = u32.GetWindowThreadProcessId(fg_hwnd, None)
    our_tid = ctypes.windll.kernel32.GetCurrentThreadId()
    if fg_tid != our_tid:
        u32.AttachThreadInput(fg_tid, our_tid, True)
    u32.SetWindowLongW(hwnd, -20, u32.GetWindowLongW(hwnd, -20) | 0x0008)
    u32.BringWindowToTop(hwnd)
    u32.SetForegroundWindow(hwnd)
    if fg_tid != our_tid:
        u32.AttachThreadInput(fg_tid, our_tid, False)

class ScriptDialog(wx.Dialog):
    def __init__(self, parent, title):
        self.hardcoded_defaults = {                                                                            #Factory defaults — these never change
            "param_1": "EDIT default",                                                                         #EDIT: Add your parameters and defaults
            "param_2": "EDIT default",                                                                         #EDIT: Add your parameters and defaults
        }
        defaults = self.hardcoded_defaults.copy()

        if os.path.exists(SETTINGS_FILE):                                                                      #Load saved settings if available
            try:
                with open(SETTINGS_FILE, 'r') as f:
                    defaults.update(json.load(f))
            except:
                pass                                                                                           #Fall back to hardcoded defaults on error

        super().__init__(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.STAY_ON_TOP)

        vbox = wx.BoxSizer(wx.VERTICAL)
        grid = wx.FlexGridSizer(2, 2, 10, 10)                                                                  #EDIT: First arg = number of parameter rows

        # EDIT: Add one StaticText + TextCtrl pair per parameter. Duplicate rows as needed.
        grid.Add(wx.StaticText(self, label="EDIT Parameter 1:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.param_1 = wx.TextCtrl(self, value=str(defaults["param_1"]))                                       #Pre-fill from saved settings
        grid.Add(self.param_1, 1, wx.EXPAND)

        grid.Add(wx.StaticText(self, label="EDIT Parameter 2:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.param_2 = wx.TextCtrl(self, value=str(defaults["param_2"]))                                       #Pre-fill from saved settings
        grid.Add(self.param_2, 1, wx.EXPAND)

        grid.AddGrowableCol(1, 1)
        vbox.Add(grid, 1, wx.ALL | wx.EXPAND, 15)

        #Buttons
        reset_btn = wx.Button(self, label="Reset Defaults")
        clear_btn = wx.Button(self, label="Clear Saved")
        std_btn_sizer = self.CreateButtonSizer(wx.OK | wx.CANCEL | wx.HELP)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        btn_row.Add(reset_btn,     0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        btn_row.Add(clear_btn,     0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        btn_row.Add(std_btn_sizer, 0, wx.ALL, 5)
        vbox.Add(btn_row, 0, wx.ALIGN_CENTER | wx.BOTTOM, 10)

        self.Bind(wx.EVT_BUTTON, self.on_help, id=wx.ID_HELP)
        reset_btn.Bind(wx.EVT_BUTTON, self.on_reset)
        clear_btn.Bind(wx.EVT_BUTTON, self.on_clear_settings)

        self.SetSizer(vbox)
        vbox.Fit(self)
        self.Center()

    def on_help(self, event):
        """Show inline help text."""
        help_text = (
            "EDIT: Script Name\n"
            "==================================================\n\n"
            # EDIT: Fill in the help text for your script
            " PARAMETER 1\n"
            "   EDIT: Description of what Parameter 1 does.\n\n"
            " PARAMETER 2\n"
            "   EDIT: Description of what Parameter 2 does.\n\n"
            " [Reset Defaults]   Restores factory default values (fields flash green).\n"
            " [Clear Saved]      Deletes the locally stored settings file.\n\n"
            " Settings are saved to:\n"
            "   %%APPDATA%%\\pycatia_scripts\\Your_Script_Name\\user_settings.json\n"  #EDIT: Match script name
            " The saved values are pre-filled each time the script is run.\n"
        )
        dlg = wx.lib.dialogs.ScrolledMessageDialog(self, help_text, "Help", size=(520, 400))
        dlg.ShowModal()
        dlg.Destroy()

    def on_reset(self, event):
        """Restore all fields to hardcoded factory defaults with a brief green flash."""
        d = self.hardcoded_defaults
        success_color = wx.Colour(200, 255, 200)
        default_color = wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW)

        # EDIT: Set each field to its hardcoded default
        self.param_1.SetValue(str(d["param_1"]))
        self.param_2.SetValue(str(d["param_2"]))

        controls = [self.param_1, self.param_2]                                                                #EDIT: List all text controls
        for ctrl in controls:
            ctrl.SetBackgroundColour(success_color)
            ctrl.Refresh()
        wx.CallLater(500, self._clear_feedback_colors, controls, default_color)

    def _clear_feedback_colors(self, controls, color):
        for ctrl in controls:
            ctrl.SetBackgroundColour(color)
            ctrl.Refresh()

    def on_clear_settings(self, event):
        """Delete the saved settings file and reset the UI to factory defaults."""
        if os.path.exists(SETTINGS_FILE):
            try:
                os.remove(SETTINGS_FILE)
                wx.MessageDialog(None, "Saved settings deleted.", "Settings Cleared",
                        wx.OK | wx.ICON_INFORMATION | wx.STAY_ON_TOP).ShowModal()
                self.on_reset(None)
            except Exception as e:
                wx.MessageDialog(None, f"Error deleting settings: {e}", "Error",
                        wx.OK | wx.ICON_ERROR | wx.STAY_ON_TOP).ShowModal()
        else:
            wx.MessageDialog(None, "No saved settings file found.", "Information",
                    wx.OK | wx.ICON_INFORMATION | wx.STAY_ON_TOP).ShowModal()

    def get_settings_to_save(self):
        """Return current field values for JSON serialization."""
        return {                                                                                                #EDIT: Include every field
            "param_1": self.param_1.GetValue(),
            "param_2": self.param_2.GetValue(),
        }

if __name__ == "__main__":
    SETTINGS_DIR  = os.path.join(os.environ['APPDATA'], 'pycatia_scripts', 'Your_Script_Name')                 #EDIT: Match script filename without .py
    SETTINGS_FILE = os.path.join(SETTINGS_DIR, 'user_settings.json')                                          #User settings file

    if not os.path.exists(SETTINGS_DIR):                                                                       #Create settings directory if it does not exist
        os.makedirs(SETTINGS_DIR)

    caa = catia()                                                                                               #Catia application instance
    check_document = caa.active_document                                                                       #Current active document
    current_document = None
    app = wx.App(None)                                                                                         #Initialize wx application

    if type(check_document) is ProcessDocument:                                                                #Active document is a ProcessDocument
        current_document: PPRDocument = check_document.ppr_document                                           #Get PPRDocument from ProcessDocument
    elif type(check_document) is PPRDocument:                                                                  #Active document is already a PPRDocument
        current_document: PPRDocument = caa.active_document
    else:
        wx.MessageDialog(None, "A CATProcess document must be the active document.", "Error",
                wx.OK | wx.ICON_ERROR | wx.STAY_ON_TOP).ShowModal()
        exit()

    dlg = ScriptDialog(None, "EDIT: Dialog Title")                                                             #EDIT: Set dialog title
    wx.CallAfter(_bring_to_front, dlg)
    if dlg.ShowModal() != wx.ID_OK:                                                                            #If user cancelled
        dlg.Destroy()
        exit()

    param_1 = dlg.param_1.GetValue().strip()                                                                   #EDIT: Get each field value
    param_2 = dlg.param_2.GetValue().strip()                                                                   #EDIT: Get each field value

    with open(SETTINGS_FILE, 'w') as f:                                                                        #Save settings for next run
        json.dump(dlg.get_settings_to_save(), f, indent=4)

    dlg.Destroy()                                                                                              #Destroy dialog

    processes = current_document.processes                                                                     #Get process list
    result_count = 0                                                                                           #Counter for reporting

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

                            # TODO: Add logic for each operation here using param_1, param_2
                            # operation.name                     — operation name
                            # operation.type                     — operation type string
                            # operation.parameters.item(n + 1)  — access operation parameters (1-indexed)
                            #   param.name                       — parameter name
                            #   param.value_as_string()          — parameter value as string
                            result_count += 1

    # To show large text results:
    #   wx.lib.dialogs.ScrolledMessageDialog(None, result_text, "Results", size=(500, 400)).ShowModal()

    print(f"\n\n Completed — {result_count} operation(s) processed\n\n")
