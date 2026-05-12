'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Your_Script_Name.py
    Version:        1.2
    Code:           Python3.10.4, Pycatia 0.8.3
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
                    pycatia
                    wxPython
                    Catia V5 running with an open part document.
    -----------------------------------------------------------------------------------------------------------------------

    Change:         12.05.26 1.1: Dialogs raised to foreground of CATIA window.
                    13.05.26 1.2: Fix searchHybridBody to use explicit name comparison.

    -----------------------------------------------------------------------------------------------------------------------
'''

#Imports
from pycatia import catia
from pycatia.mec_mod_interfaces.part_document import PartDocument
from pathlib import Path
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

'''
    This function searches for a hybrid body (geometric set) by name and returns it.
    Searches recursively through all nested geometric sets.

    Inputs:
        searchName              The name of the geometric set being searched for.
        currentHybridBodies     The current collection of hybrid bodies to search.

    output:
        The geometric set if found, or None if not found.
'''
def searchHybridBody(seachName, currentHybridBodies):
    for index in range(currentHybridBodies.count):                                                             #Search at current level by explicit name comparison
        hb = currentHybridBodies.item(index + 1)
        if hb.name == seachName:                                                                               #Found at this level
            return hb                                                                                          #Return found geometric set

    for index in range(currentHybridBodies.count):                                                             #Loop through geometric sets at this level
        if currentHybridBodies.item(index+1).hybrid_bodies.count > 0:
            found = searchHybridBody(seachName, currentHybridBodies.item(index+1).hybrid_bodies)               #Recursive call

            if found is not None:                                                                              #If found
                return found                                                                                   #Return found

    return None                                                                                                #Return not found


'''
    Replaces a hybrid shape with an isolated datum of the same type, preserving its name.
    Supports points (1), curves (2), lines (3), circles (4), and surfaces (5).

    Inputs:
        hybrid_shape_factory    The part's HybridShapeFactory (part.hybrid_shape_factory).
        hybrid_shape            The HybridShape to isolate.
        hybrid_body             The geometric set to append the new datum to.
        name                    Optional name for the datum.

    output:
        None — part.update() must be called after one or more create_datum calls.
'''
def create_datum(hybrid_shape_factory, hybrid_shape, hybrid_body, name=None):
    geo_type = hybrid_shape_factory.get_geometrical_feature_type(hybrid_shape)                                 #Get geometry type

    if geo_type == 1:                                                                                          #Point
        datum = hybrid_shape_factory.add_new_point_datum(hybrid_shape)
    elif geo_type == 2:                                                                                        #Curve
        datum = hybrid_shape_factory.add_new_curve_datum(hybrid_shape)
    elif geo_type == 3:                                                                                        #Line
        datum = hybrid_shape_factory.add_new_line_datum(hybrid_shape)
    elif geo_type == 4:                                                                                        #Circle
        datum = hybrid_shape_factory.add_new_circle_datum(hybrid_shape)
    elif geo_type == 5:                                                                                        #Surface
        datum = hybrid_shape_factory.add_new_surface_datum(hybrid_shape)
    else:
        print(f"  Warning: unsupported geometry type ({geo_type}) for '{name}' — skipped")
        return

    if name: datum.name = name                                                                                 #Apply name if given
    hybrid_body.append_hybrid_shape(datum)                                                                     #Add datum to geometric set
    hybrid_shape_factory.delete_object_for_datum(hybrid_shape)                                                 #Remove the original construction shape


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

        super().__init__(parent, title=title, size=(420, 260), style=wx.DEFAULT_DIALOG_STYLE | wx.STAY_ON_TOP) #EDIT: Adjust dialog size to fit your fields

        vbox = wx.BoxSizer(wx.VERTICAL)
        grid = wx.FlexGridSizer(2, 2, 10, 10)                                                                  #EDIT: First arg = number of parameter rows

        # EDIT: Add one StaticText + TextCtrl pair per parameter. Duplicate rows as needed.
        grid.Add(wx.StaticText(self, label="EDIT Parameter 1:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.param_1 = wx.TextCtrl(self, value=str(defaults["param_1"]))                                       #Pre-fill from saved settings
        self.param_1.SetToolTip("EDIT: Tooltip shown on hover.")                                               #EDIT: Set tooltip (optional, remove if not needed)
        grid.Add(self.param_1, 1, wx.EXPAND)

        grid.Add(wx.StaticText(self, label="EDIT Parameter 2:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.param_2 = wx.TextCtrl(self, value=str(defaults["param_2"]))                                       #Pre-fill from saved settings
        self.param_2.SetToolTip("EDIT: Tooltip shown on hover.")                                               #EDIT: Set tooltip (optional, remove if not needed)
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
        self.Center()

    def on_help(self, event):
        """Show inline help text in a scrollable dialog."""
        help_text = (
            "EDIT: Script Name\n"
            "==================================================\n\n"
            # EDIT: Fill in the help text for your script
            " PARAMETER 1\n"
            "   EDIT: Description of what Parameter 1 does and its valid range.\n\n"
            " PARAMETER 2\n"
            "   EDIT: Description of what Parameter 2 does and its valid range.\n\n"
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

if __name__ == "__main__":
    SETTINGS_DIR  = os.path.join(os.environ['APPDATA'], 'pycatia_scripts', 'Your_Script_Name')                 #EDIT: Match script filename without .py
    SETTINGS_FILE = os.path.join(SETTINGS_DIR, 'user_settings.json')                                          #User settings file

    if not os.path.exists(SETTINGS_DIR):                                                                       #Create settings directory if it does not exist
        os.makedirs(SETTINGS_DIR)

    caa = catia()                                                                                               #Catia application instance
    active_doc = caa.active_document                                                                           #Current active document
    app = wx.App(None)                                                                                         #Initialize wx application

    if type(active_doc) is not PartDocument:                                                                   #Check that a CATPart is active
        wx.MessageDialog(None, "A CATPart document must be the active document.", "Error",
                wx.OK | wx.ICON_ERROR | wx.STAY_ON_TOP).ShowModal()
        exit()

    part_document: PartDocument = active_doc                                                                   #Cast to PartDocument
    part = part_document.part                                                                                  #Current part
    hybrid_bodies = part.hybrid_bodies                                                                         #Top level geometric sets
    hybrid_shape_factory = part.hybrid_shape_factory                                                           #GSD workbench for creating hybrid shapes

    # NOTE: If your script selects geometry in CATIA, replace the check above with the
    # LeafProduct-aware pattern so the script also works on parts inside a product:
    #
    #   object_filter = ("HybridBody",)                                        # EDIT: filter type
    #   selectionSet = active_doc.selection
    #   status = selectionSet.select_element3(object_filter, "Select ...", False, 2, False)
    #   if status != "Normal":
    #       wx.MessageDialog(None, "Selection failed.", "Error",
    #               wx.OK | wx.ICON_ERROR | wx.STAY_ON_TOP).ShowModal()
    #       exit()
    #   selected_item = selectionSet.item(1)
    #
    #   if type(active_doc) is PartDocument:
    #       part_document: PartDocument = active_doc
    #       part = active_doc.part
    #   else:
    #       leaf_product = selected_item.com_object.LeafProduct
    #       part_document = PartDocument(leaf_product.ReferenceProduct.Parent)
    #       part = part_document.part

    dlg = ScriptDialog(None, "EDIT: Dialog Title")                                                             #EDIT: Set dialog title
    wx.CallAfter(_bring_to_front, dlg)
    if dlg.ShowModal() != wx.ID_OK:                                                                            #If user cancelled
        dlg.Destroy()
        exit()

    param_1 = dlg.param_1.GetValue().strip()                                                                   #EDIT: Get each field value
    param_2 = dlg.param_2.GetValue().strip()                                                                   #EDIT: Get each field value

    with open(SETTINGS_FILE, 'w') as f:                                                                        #Save settings for next run
        json.dump({                                                                                            #EDIT: Include every field
            "param_1": dlg.param_1.GetValue(),
            "param_2": dlg.param_2.GetValue(),
        }, f, indent=4)

    dlg.Destroy()                                                                                              #Destroy dialog

    # EDIT: Set maximum to the number of distinct progress steps in your script
    PROGRESS_STEPS = 5
    progress_dlg = wx.ProgressDialog(
        "EDIT: Operation Title",
        "Initializing...",
        maximum=PROGRESS_STEPS,
        parent=None,
        style=(wx.PD_APP_MODAL | wx.PD_AUTO_HIDE | wx.PD_SMOOTH |
               wx.PD_ELAPSED_TIME | wx.PD_REMAINING_TIME)
    )

    try:
        progress_dlg.Update(1, "EDIT: Step 1 message...")

        # TODO: Step 1 — first phase of work
        # part.update() here if geometry was created in this step

        progress_dlg.Update(2, "EDIT: Step 2 message...")

        # TODO: Step 2
        # part.update() here if geometry was created in this step

        progress_dlg.Update(3, "EDIT: Step 3 message...")

        # TODO: Step 3

        progress_dlg.Update(4, "EDIT: Step 4 message...")

        # TODO: Step 4

        part.update()                                                                                          #Final update after all operations

        progress_dlg.Update(PROGRESS_STEPS, "Done.")

    except Exception as e:
        # EDIT: If your script creates a body/geometric set that should be cleaned up on error,
        # delete it here before showing the error message.
        # Example: bodies.remove(new_body)
        progress_dlg.Destroy()
        wx.MessageDialog(None,
            f"An error occurred:\n\n{e}\n\n"
            "EDIT: Add any user-facing cleanup instructions here.",
            "Error", wx.OK | wx.ICON_ERROR | wx.STAY_ON_TOP
        ).ShowModal()
        exit()

    finally:
        progress_dlg.Destroy()                                                                                 #Always close progress dialog

    print("\n\n Completed\n\n")
