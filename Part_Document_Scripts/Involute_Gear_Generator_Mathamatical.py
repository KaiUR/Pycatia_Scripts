'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Involute_Gear_Generator_Mathamatical.py
    Version:        1.0
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Create Involute Gear
    Author:         Kai-Uwe Rathjen
    Date:           24.03.26
    Description:    This script will ask the user for parameters to create spur gear profile. The script will create a gear,
                    shaft and key for the shaft. The settings will be stored for use the next time that the script is used.
                    I probably overdid it with this script.
    dependencies = [
                    "pycatia",
                    "wxPython",
                    ]
    requirements:   Python >= 3.10
                    pycatia
                    Catia V5 running with an open part.
                    This script needs an open part document.
                    Hybrid desgin should be disabled, the script will tempoary disable it if it is on.
    -----------------------------------------------------------------------------------------------------------------------
    
    Change:
    
    -----------------------------------------------------------------------------------------------------------------------
'''

#Imports
from pycatia import catia
from pycatia.mec_mod_interfaces.part_document import PartDocument
from pycatia.in_interfaces.setting_controllers import SettingControllers
from pycatia import CatConstraintType
from pycatia import CatConstraintMode
from pycatia import CatPrismOrientation
from pycatia import CatLimitMode
import math
import wx
import wx.lib.dialogs as dialogs
import wx.lib.agw.pyprogress as PP
import os
import json
import traceback

class DataInputDialog(wx.Dialog):
    def __init__(self, parent, title):
        self.hardcoded_defaults = {
            "module": "2.0", "teeth": "24", "pa": "20.0", "clearance": "0.25",
            "steps": "10", "thickness": "16.0", "fillet": "0.38", "shaft_r": "5.0",
            "key_w": "4.0", "key_d": "4.0", "key_mode": 0,
            "has_shaft": True, "has_key": True
        }
        defaults = self.hardcoded_defaults.copy()
        
        # Load from AppData if file exists
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r') as f:
                    defaults.update(json.load(f))
            except: pass # Fallback to hardcoded defaults on error

        super().__init__(parent, title=title, size=(450, 580))                                          #Set size of dialog
        
        vbox = wx.BoxSizer(wx.VERTICAL)                                                                 #Use the Dialog itself as the parent for the sizer
        
        grid = wx.FlexGridSizer(13, 3, 10, 10)                                                          #Set grid for fields
        
        self.module = wx.TextCtrl(self, value=str(defaults["module"]))                                  #Initilize field with default value
        self.number_of_teeth = wx.TextCtrl(self, value=str(defaults["teeth"]))                          #Initilize field with default value
        self.pressure_angle = wx.TextCtrl(self, value=str(defaults["pa"]))                              #Initilize field with default value
        self.clearance = wx.TextCtrl(self, value=str(defaults["clearance"]))                            #Initilize field with default value
        self.steps = wx.TextCtrl(self, value=str(defaults["steps"]))                                    #Initilize field with default value
        self.gear_thicness = wx.TextCtrl(self, value=str(defaults["thickness"]))                        #Initilize field with default value
        self.fillet_radius = wx.TextCtrl(self, value=str(defaults["fillet"]))                           #Initilize field with default value
        self.shaft_radius = wx.TextCtrl(self, value=str(defaults["shaft_r"]))                           #Initilize field with default value
        self.key_w = wx.TextCtrl(self, value=str(defaults["key_w"]))                                    #Initilize field with default value
        self.key_d = wx.TextCtrl(self, value=str(defaults["key_d"]))                                    #Initilize field with default value
        self.key_mode = wx.RadioBox(self, label="Key Measurement Mode", 
                            choices=['Ratio', 'Fixed (mm)'], 
                            majorDimension=1, style=wx.RA_SPECIFY_COLS)                                 #Selection for if slot is done by a ratio
        self.key_mode.SetSelection(defaults["key_mode"])                                                #Default to Ratio
        self.has_shaft = wx.CheckBox(self, label="Include Shaft Hole")                                  #Initilize field lable
        self.has_shaft.SetValue(defaults["has_shaft"])                                                  #Initilize field with default value
        self.has_keyway = wx.CheckBox(self, label="Include Keyway")                                     #Initilize field lable
        self.has_keyway.SetValue(defaults["has_key"])                                                   #Initilize field with default value

        self.has_shaft.Bind(wx.EVT_CHECKBOX, self.on_toggle_shaft)                                      #bind event function
        self.has_keyway.Bind(wx.EVT_CHECKBOX, self.on_toggle_keyway)                                    #bind event function
        
        self.unit_label_w = wx.StaticText(self, label="ratio")                                          #Define unit lable for shaft width, default ratio
        self.unit_label_d = wx.StaticText(self, label="ratio")                                          #Define unit lable for shaft width, default ratio
        
        self.key_mode.Bind(wx.EVT_RADIOBOX, self.on_unit_change)                                        #Bide method to change unit if mode changes
        
        self.module.SetToolTip("Gear Module: Defines the size of the teeth. (Standard is 2.0)")
        self.number_of_teeth.SetToolTip("Total number of teeth on the gear.")
        self.pressure_angle.SetToolTip("Angle of the tooth profile. Standard industrial gears use 20.0°.")
        self.clearance.SetToolTip("Gap between the tooth tip and the root of the mating gear.")
        self.steps.SetToolTip("Resolution of the involute curve. Higher values create smoother teeth.")
        self.gear_thicness.SetToolTip("The extrusion depth (Width) of the gear face in mm.")
        self.fillet_radius.SetToolTip("Radius for the base of the teeth to reduce stress concentration.")
        self.has_shaft.SetToolTip("Toggle to include a center hole for a mounting shaft.")
        self.shaft_radius.SetToolTip("Radius of the center hole in mm.")
        self.has_keyway.SetToolTip("Toggle to cut a rectangular key slot into the shaft hole.")
        self.key_mode.SetToolTip("Ratio: Size is (Shaft Diameter / Input).\nFixed: Size is exactly the input in mm.")
        self.key_w.SetToolTip("The horizontal width of the key slot.")
        self.key_d.SetToolTip("The vertical depth of the key slot.")
        
        grid.AddMany([
            (wx.StaticText(self, label="Module:")), (self.module, 1, wx.EXPAND), (wx.StaticText(self, label="mm")),
            (wx.StaticText(self, label="Number of Teeth:")), (self.number_of_teeth, 1, wx.EXPAND), (wx.StaticText(self, label="qty")),
            (wx.StaticText(self, label="Preasure Angle:")), (self.pressure_angle, 1, wx.EXPAND), (wx.StaticText(self, label="deg")),
            (wx.StaticText(self, label="Clearance:")), (self.clearance, 1, wx.EXPAND), (wx.StaticText(self, label="mm")),
            (wx.StaticText(self, label="Steps:")), (self.steps, 1, wx.EXPAND), (wx.StaticText(self, label="steps")),
            (wx.StaticText(self, label="Gear Thicness:")), (self.gear_thicness, 1, wx.EXPAND), (wx.StaticText(self, label="mm")),
            (wx.StaticText(self, label="Fillet Radius:")), (self.fillet_radius, 1, wx.EXPAND), (wx.StaticText(self, label="mm")),
            (wx.StaticText(self, label="Shaft Setting:")), (self.has_shaft, 0), (wx.StaticText(self, label="")),
            (wx.StaticText(self, label="Shaft Radius:")), (self.shaft_radius, 1, wx.EXPAND), (wx.StaticText(self, label="mm")),
            (wx.StaticText(self, label="Keyway Setting:")), (self.has_keyway, 0), (wx.StaticText(self, label="")),
            (wx.StaticText(self, label="Keyway Mode:")), (self.key_mode, 0), (wx.StaticText(self, label="")),
            (wx.StaticText(self, label="Key Width/Ratio:")), (self.key_w, 1, wx.EXPAND), self.unit_label_w,
            (wx.StaticText(self, label="Key Depth/Ratio:")), (self.key_d, 1, wx.EXPAND), self.unit_label_d
        ])                                                                                              #Create layout for dialog
        
        grid.AddGrowableCol(1, 1)                                                                       #Set cloum
        
        vbox.Add(grid, proportion=1, flag=wx.ALL|wx.EXPAND, border=15)                                  #Add grid border
        
        std_btn_sizer = self.CreateButtonSizer(wx.OK | wx.CANCEL | wx.HELP)

        reset_btn = wx.Button(self, label="Reset Defaults")
        clear_btn = wx.Button(self, label="Clear Saved")

        if std_btn_sizer:
            btn_row_sizer = wx.BoxSizer(wx.HORIZONTAL)
            btn_row_sizer.Add(reset_btn, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
            btn_row_sizer.Add(clear_btn, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
            btn_row_sizer.Add(std_btn_sizer, 0, wx.ALL, 5)

            vbox.Add(btn_row_sizer, flag=wx.ALIGN_CENTER | wx.BOTTOM, border=10)
        
        self.SetSizer(vbox)
        self.Center() 
        
        self.Bind(wx.EVT_BUTTON, self.on_help, id=wx.ID_HELP)                                           #Bind help button to help dialog
        reset_btn.Bind(wx.EVT_BUTTON, self.on_reset)
        clear_btn.Bind(wx.EVT_BUTTON, self.on_clear_settings)
        
        self.numeric_fields = [
            (self.module, float), 
            (self.number_of_teeth, int),
            (self.pressure_angle, float),
            (self.clearance, float),
            (self.gear_thicness, float)
        ]

        for ctrl, _ in self.numeric_fields:
            ctrl.Bind(wx.EVT_TEXT, self.on_validate_live)
            
    def on_clear_settings(self, event):
        """Deletes the saved JSON settings file and resets the current UI."""
        if os.path.exists(SETTINGS_FILE):
            try:
                os.remove(SETTINGS_FILE)
                wx.MessageBox("Saved presets have been deleted successfully.", 
                              "Settings Cleared", wx.OK | wx.ICON_INFORMATION)
                # Optional: Reset the UI immediately to show hardcoded defaults
                self.on_reset(None)
            except Exception as e:
                wx.MessageBox(f"Error deleting settings: {str(e)}", 
                              "Error", wx.OK | wx.ICON_ERROR)
        else:
            wx.MessageBox("No saved settings file found.", 
                          "Information", wx.OK | wx.ICON_INFORMATION)
            
    def on_reset(self, event):
        """Restores UI fields and provides a visual 'flash' feedback."""
        d = self.hardcoded_defaults
        success_color = wx.Colour(200, 255, 200) # Soft Green
        default_color = wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW)

        # List of all text controls to update
        controls = [
            self.module, self.number_of_teeth, self.pressure_angle, 
            self.clearance, self.steps, self.gear_thicness, 
            self.fillet_radius, self.shaft_radius, self.key_w, self.key_d
        ]

        # Apply values and set "Feedback" color
        self.module.SetValue(d["module"])
        self.number_of_teeth.SetValue(d["teeth"])
        self.pressure_angle.SetValue(d["pa"])
        self.clearance.SetValue(d["clearance"])
        self.steps.SetValue(d["steps"])
        self.gear_thicness.SetValue(d["thickness"])
        self.fillet_radius.SetValue(d["fillet"])
        self.shaft_radius.SetValue(d["shaft_r"])
        self.key_w.SetValue(d["key_w"])
        self.key_d.SetValue(d["key_d"])
        
        for ctrl in controls:
            ctrl.SetBackgroundColour(success_color)
            ctrl.Refresh()

        # Handle non-text controls
        self.key_mode.SetSelection(d["key_mode"])
        self.has_shaft.SetValue(d["has_shaft"])
        self.has_keyway.SetValue(d["has_key"])

        # Sync UI states
        self.on_toggle_shaft(None)
        self.on_toggle_keyway(None)
        self.on_unit_change(None)

        wx.CallLater(500, self._clear_feedback_colors, controls, default_color)                     #Use a timer to "flash" the color back to normal after 500ms

    def _clear_feedback_colors(self, controls, color):
        """Helper to revert colors after the feedback flash."""
        for ctrl in controls:
            ctrl.SetBackgroundColour(color)
            ctrl.Refresh()
            
    def on_validate_live(self, event):
        """Checks the value every time a key is pressed."""
        ctrl = event.GetEventObject()
        val_string = ctrl.GetValue().strip()
        
        target_type = next(t for c, t in self.numeric_fields if c == ctrl)                          #Find the expected type for this specific control

        if self.is_valid(val_string, target_type):
            ctrl.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW))
        else:
            ctrl.SetBackgroundColour(wx.Colour(255, 200, 200))                                      #Turn the background soft red if the input is invalid
        
        ctrl.Refresh()                                                                              #Force the UI to update the color

    def is_valid(self, value_str, target_type):
        """Helper to check if a string can be converted to the target type and is > 0."""
        try:
            val = target_type(value_str)
            return val > 0
        except ValueError:
            return False
        
    def on_help(self, event):                                                                           #Help Dialog
            
        help_text = (
            "INVOLUTE GEAR GENERATOR - COMPREHENSIVE USER MANUAL\n"
            "==========================================================================\n\n"
            "I. CORE GEAR GEOMETRY PARAMETERS\n"
            "--------------------------------------------------------------------------\n"
            " • Module:          The base unit of tooth size (Pitch Diameter / Teeth).\n"
            "                    Standard industrial gears typically use a Module of 2.0.\n\n"
            " • Number of Teeth: Defines the gear size and ratio. Fewer than 17 teeth\n"
            "                    may result in 'undercutting' (weakening of the root).\n\n"
            " • Pressure Angle:  Angle of force transmission between teeth. 20.0° is\n"
            "                    standard. 14.5° is quieter; higher angles are stronger.\n\n"
            " • Clearance:       The radial gap between the tooth tip and the mating root.\n"
            "                    The standard calculation is usually 0.25 × Module.\n\n"
            " • Steps:           Mathematical resolution of the involute curve. Higher\n"
            "                    values (10+) create smoother surfaces in CATIA.\n\n"
            " • Fillet Radius:   The curvature at the tooth root. Essential for reducing\n"
            "                    stress concentration and preventing tooth breakage.\n\n\n"

            "II. SHAFT AND KEYWAY GEOMETRY\n"
            "--------------------------------------------------------------------------\n"
            " • Shaft Radius:    The radius of the center bore hole (measured in mm).\n\n"
            " • Keyway Mode:     - Ratio: Sizes the keyway as a fraction of the shaft\n"
            "                      diameter (e.g., Width = Diameter / 4).\n"
            "                    - Fixed: Allows for exact millimeter input to match\n"
            "                      standard hardware or existing key-stock sizes.\n\n\n"

            "III. INTERFACE BUTTON FUNCTIONS\n"
            "--------------------------------------------------------------------------\n"
            " [OK]               Validates all inputs. If valid, triggers the automated\n"
            "                    3D geometry generation process within CATIA.\n\n"
            " [CANCEL]           Exits the script immediately without saving changes or\n"
            "                    generating any 3D geometry.\n\n"
            " [RESET DEFAULTS]   Restores all fields to the original factory settings.\n"
            "                    Fields will briefly flash green to confirm the reset.\n\n"
            " [CLEAR SAVED]      Deletes the locally stored 'user_presets.json' file.\n"
            "                    Ensures the script starts with factory defaults next time.\n\n"
            " [HELP]             Opens this detailed documentation window.\n\n\n"

            "IV. AUTOMATED DATA PERSISTENCE\n"
            "--------------------------------------------------------------------------\n"
            " This script includes an automated memory system. Whenever you click 'OK'\n"
            " and successfully generate a gear, your parameters are saved to a file in\n"
            " your Windows AppData folder.\n\n"
            " When the script is restarted, it automatically reloads your last used\n"
            " values, facilitating rapid iterative design. To wipe this memory and\n"
            " return to factory settings, use the 'Clear Saved' button."
        )                                                                                           #Help Text
        dlg = dialogs.ScrolledMessageDialog(self, help_text, "Help")                                    #Create scolling dialog
        mono_font = wx.Font(10, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)      #Define font
        dlg.text.SetFont(mono_font)                                                                     #Set font
        
        dlg.SetSize((700, 750)) 
        
        dlg.CenterOnParent()
        dlg.ShowModal()                                                                                 #Show dialog
        dlg.Destroy()                                                                                   #Close dialog
        
    def on_unit_change(self, event):                                                                    #Change unit if key mode changes
        unit = "mm" if self.key_mode.GetSelection() == 1 else "ratio"
        self.unit_label_w.SetLabel(unit)
        self.unit_label_d.SetLabel(unit)
        
    def on_toggle_shaft(self, event):
        """Enable/Disable shaft input based on checkbox."""
        state = self.has_shaft.IsChecked()
        self.shaft_radius.Enable(state)
        # If no shaft, there can't be a keyway
        self.has_keyway.Enable(state)
        if not state:
            self.has_keyway.SetValue(False)
            self.key_w.Enable(False)
            self.key_d.Enable(False)
        
    def on_toggle_keyway(self, event):
        """Enable/Disable keyway inputs based on checkbox."""
        state = self.has_keyway.IsChecked()
        self.key_w.Enable(state)
        self.key_d.Enable(state)
    
    def Validate(self):
        fields = [
            (self.module, "Module", float),
            (self.number_of_teeth, "Number of Teeth", int),
            (self.pressure_angle, "Pressure Angle", float),
            (self.clearance, "Clearance", float),
            (self.steps, "Steps", int),
            (self.gear_thicness, "Gear Thickness", float),
            (self.fillet_radius, "Fillet Radius", float),
            (self.shaft_radius, "Shaft Radius", float),
            (self.key_w, "Key Width Ratio", float),
            (self.key_d, "Key Depth Ratio", float)
        ]
        
        if self.has_shaft.IsChecked():
            fields.append((self.shaft_radius, "Shaft Radius", float))
        
        if self.has_keyway.IsChecked():
            fields.append((self.key_w, "Key Width Ratio", float))
            fields.append((self.key_d, "Key Depth Ratio", float))

        for ctrl, name, target_type in fields:
            val_string = ctrl.GetValue().strip()
            
            if not val_string:
                self.show_error(f"{name} cannot be empty.", ctrl)
                return False
            
            try:
                # Convert the value first
                val_numeric = target_type(val_string)
                
                # CHECK FOR ZERO OR NEGATIVE
                if val_numeric <= 0:
                    self.show_error(f"{name} must be greater than zero.", ctrl)
                    return False
                    
            except ValueError:
                self.show_error(f"{name} must be a valid {target_type.__name__}.", ctrl)
                return False
        
        pa = float(self.pressure_angle.GetValue())
        z = int(self.number_of_teeth.GetValue()) 

        z_min_calc = 2 / (math.sin(math.radians(pa))**2)
        
        #engineering check for low pa
        if pa < 14.5:
            msg = (f"Pressure angle ({pa}°) is below the standard industrial minimum (14.5°).\n"
                   "This will cause severe undercutting and weaken the teeth.\n\n"
                   "Proceed anyway?")
            if wx.MessageBox(msg, "Design Warning", wx.YES_NO | wx.ICON_WARNING) == wx.NO:
                self.pressure_angle.SetFocus()
                return False
        
        #engineering check for low teeth count
        if z < z_min_calc:
            msg = (
                f"Number of teeth ({z}) is below the theoretical limit of {int(z_min_calc)} "
                f"for a {pa}° pressure angle\n"
                "This may cause 'undercutting' at the tooth root.\n\n"
                "Proceed anyway?"
            )
            if wx.MessageBox(msg, "Design Warning", wx.YES_NO | wx.ICON_WARNING) == wx.NO:
                self.number_of_teeth.SetFocus()
                return False
        
        #Engineeering check for pa over 45
        if pa >= 45:
            self.show_error("Pressure angle must be less than 45 degrees to maintain gear geometry.", self.pressure_angle)
            return False
            
        #engineeing check for to deep key
        if self.has_shaft.IsChecked() and self.has_keyway.IsChecked():
            m = float(self.module.GetValue())
            r_shaft = float(self.shaft_radius.GetValue())
            
            # Calculate Dedendum (Root) Radius
            # r_p = m * z / 2; r_d = r_p - 1.25 * m (approx)
            r_dedendum = (m * z / 2) - (1.25 * m)
            
            # Keyway depth calculation (Simplified for validation)
            k_mode = self.key_mode.GetSelection()
            k_depth_input = float(self.key_d.GetValue())
            k_depth_mm = (r_shaft * 2 * (k_depth_input / 100)) if k_mode == 0 else k_depth_input
            
            if (r_shaft + k_depth_mm) >= r_dedendum:
                self.show_error("The Keyway depth is too deep and will cut into the gear teeth!", self.key_d)
                return False
                
        #engineering check for to shallow key
        if self.has_shaft.IsChecked() and self.has_keyway.IsChecked():
            k_mode = self.key_mode.GetSelection()
            k_width_input = float(self.key_w.GetValue())
            k_depth_input = float(self.key_d.GetValue())
            
            # If using Fixed mode (mm), we compare depth to width directly.
            # If using Ratio mode, depth is 'too shallow' if the ratio is too high.
            if k_mode == 1: # Fixed (mm)
                min_depth = k_width_input * 0.4 # Tolerance for slightly shallow keys
                if k_depth_input < min_depth:
                    msg = (f"Keyway depth ({k_depth_input}mm) is very shallow relative to the width ({k_width_input}mm).\n"
                           f"Standard depth is typically {k_width_input * 0.5:.2f}mm. Proceed?")
                    if wx.MessageBox(msg, "Design Warning", wx.YES_NO | wx.ICON_WARNING) == wx.NO:
                        self.key_d.SetFocus()
                        return False
            else: # Ratio Mode
                # In ratio mode, a higher input number means a smaller physical slot.
                # If standard is Shaft_Dia / 4
                if k_depth_input > 6.0: 
                    msg = (f"The Keyway depth ratio ({k_depth_input}) will result in a very shallow slot.\n"
                           "Standard ratio is usually around 4.0 or 6.0. Proceed anyway?")
                    if wx.MessageBox(msg, "Design Warning", wx.YES_NO | wx.ICON_WARNING) == wx.NO:
                        self.key_d.SetFocus()
                        return False
                
        max_fillet = 0.3 * float(self.module.GetValue())
        
        #engineering check for large fillet radius
        if float(self.fillet_radius.GetValue()) > max_fillet:
            msg = (f"Warning: Fillet radius ({float(self.fillet_radius.GetValue()):.2f}mm) exceeds standard max ({max_fillet:.2f}mm).\n"
                    "This may cause interference with mating teeth.\n\n"
                    "Do you want to procede anyway?")
            if wx.MessageBox(msg, "Design Warning", wx.YES_NO | wx.ICON_WARNING) == wx.NO:
                self.fillet_radius.SetFocus()
                return False
        
        #Engineering check for key width
        if self.has_keyway.IsChecked() and self.key_mode.GetSelection() == 1:
            d_shaft = float(self.shaft_radius.GetValue()) * 2
            suggested_w = d_shaft / 4
            if abs(float(self.key_w.GetValue()) - suggested_w) > (suggested_w * 0.5):
                msg = f"Key width seems unusual for a {d_shaft}mm shaft. (Standard is approx {suggested_w}mm). Proceed?"
                if wx.MessageBox(msg, "Design Warning", wx.YES_NO) == wx.NO:
                    return False
                    
        min_th = 8 * m
        max_th = 16 * m

        # Engineering check for Gear Thickness (Face Width)
        th = float(self.gear_thicness.GetValue())
        if th < min_th or th > max_th:
            msg = (f"Gear Thickness ({th}mm) is outside the standard engineering range "
                   f"({min_th}mm to {max_th}mm) for Module {m}.\n\n"
                   "Extremely thin gears may fail under load, while extremely thick "
                   "gears may cause shaft alignment issues.\n\n"
                   "Proceed anyway?")
            if wx.MessageBox(msg, "Design Warning", wx.YES_NO | wx.ICON_WARNING) == wx.NO:
                self.gear_thicness.SetFocus()
                return False
        
        #Engineering check for shaft size        
        if self.has_shaft.IsChecked():
            r_shaft = float(self.shaft_radius.GetValue())
            
            # Pitch Circle Diameter (D = m * z)
            d_pitch = m * z
            d_shaft = r_shaft * 2
            
            # Define limits (e.g., shaft should be 0.2 to 0.7 of Pitch Diameter)
            min_limit = d_pitch * 0.2
            max_limit = d_pitch * 0.7
            
            if d_shaft < min_limit:
                msg = (f"Shaft diameter ({d_shaft}mm) is below the recommended minimum "
                       f"({min_limit:.2f}mm) for this gear size.\n\n"
                       "The shaft may lack the required torque capacity. Proceed anyway?")
                if wx.MessageBox(msg, "Design Warning", wx.YES_NO | wx.ICON_WARNING) == wx.NO:
                    self.shaft_radius.SetFocus()
                    return False
                    
            if d_shaft > max_limit:
                msg = (f"Shaft diameter ({d_shaft}mm) exceeds the recommended maximum "
                       f"({max_limit:.2f}mm) for this gear size.\n\n"
                       "This leaves very little material between the shaft and the teeth. Proceed anyway?")
                if wx.MessageBox(msg, "Design Warning", wx.YES_NO | wx.ICON_WARNING) == wx.NO:
                    self.shaft_radius.SetFocus()
                    return False
        
        #Check for std module
        standard_modules = [
            0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 2.25, 2.5, 2.75, 3.0, 
            3.25, 3.5, 3.75, 4.0, 4.5, 5.0, 5.5, 6.0, 6.5, 7.0, 8.0, 9.0, 10.0
        ]

        m_input = float(self.module.GetValue())
        if m_input not in standard_modules:
            msg = (f"The entered Module ({m_input}) is not a common industrial standard.\n"
                   "Using non-standard modules may make it difficult or expensive "
                   "to source mating gears or cutting tools.\n\n"
                   "Proceed with this custom value?")
            if wx.MessageBox(msg, "Design Warning", wx.YES_NO | wx.ICON_WARNING) == wx.NO:
                self.module.SetFocus()
                return False
                
        #Check for pointed teeth
        pa_rad = math.radians(float(self.pressure_angle.GetValue()))

        # Calculate the pressure angle at the tip (alpha_a)
        # cos(alpha_a) = r_base / r_addendum
        r_p = (m * z) / 2
        r_b = r_p * math.cos(pa_rad)
        r_a = r_p + m

        # Ensure r_a > r_b to avoid math domain errors
        if r_a > r_b:
            alpha_a = math.acos(r_b / r_a)

            # Involute function: inv(x) = tan(x) - x
            inv_pa = math.tan(pa_rad) - pa_rad
            inv_alpha_a = math.tan(alpha_a) - alpha_a

            # Calculate Top Land Thickness (s_a)
            # s_a = s_p * (r_a / r_p) - 2 * r_a * (inv_alpha_a - inv_pa)
            # s_p (arc thickness at pitch circle) is typically (pi * m) / 2
            s_p = (math.pi * m) / 2
            s_a = r_a * (s_p / r_p - 2 * (inv_alpha_a - inv_pa))

            #Engineering Limit: Top land should be >= 0.3 * Module
            min_top_land = 0.3 * m
            if s_a < min_top_land:
                msg = (f"The resulting gear teeth will be dangerously thin or 'pointed' at the tip.\n"
                       f"Calculated Top Land: {s_a:.2f}mm (Recommended Minimum: {min_top_land:.2f}mm).\n\n"
                       "This can cause issues with heat treatment, durability, or manufacturing.\n"
                       "Decrease the Pressure Angle or increase the Number of Teeth to fix this.\n\n"
                       "Proceed anyway?")
                if wx.MessageBox(msg, "Design Warning: Pointed Teeth", wx.YES_NO | wx.ICON_WARNING) == wx.NO:
                    self.pressure_angle.SetFocus()
                    return False
 
        return True # All checks passed

    def show_error(self, message, ctrl):
        """Helper to show a message box and focus the problematic field."""
        wx.MessageBox(message, "Input Error", wx.OK | wx.ICON_ERROR)
        ctrl.SetFocus()
        ctrl.SelectAll()

if __name__ == "__main__":
    SETTINGS_DIR = os.path.join(os.environ['APPDATA'], 'InvoluteGearTool')                                      #User settings path
    SETTINGS_FILE = os.path.join(SETTINGS_DIR, 'user_presets.json')                                             #User settings file

    if not os.path.exists(SETTINGS_DIR):                                                                        #Check if directory does not exist
        os.makedirs(SETTINGS_DIR)                                                                               #Create directory
    
    caa = catia()                                                                                               #Catia application instance
    app = wx.App()
    if type(caa.active_document) is not PartDocument:                                                           #Check if part document
        msg = ("No active Part document found.\n\n"
           "Please open a CATPart before running this script.")
        wx.MessageBox(msg, "Active Document Error", wx.OK | wx.ICON_ERROR)
        exit()                                                                                                  #Exith script
    part_document: PartDocument = caa.active_document                                                           #Current open document
    part = part_document.part                                                                                   #Current part
    hybrid_bodies = part.hybrid_bodies                                                                          #Set off all top level geometric sets 
    bodies = part.bodies                                                                                        #Get collection of bodies
    hybrid_shape_factory = part.hybrid_shape_factory                                                            #GSD workbentch to create hybridshapes
    shape_factory = part.shape_factory                                                                          #Part Design workbench
    selectionSet = caa.active_document.selection                                                                #Create container for selection
    
    #Parameters
    pad_tol = 0.02                                                                                              #Tol added to ensure that the pads are all joined
    
    settings_controller = caa.application.setting_controllers()                                                 #Get catia settings
    part_infa = settings_controller.item("CATMmuPartInfrastructureSettingCtrl")                                 #Get part infastructure setting

    is_hybrid = part_infa.com_object.HybridDesignMode                                                           #Get hybrid design mode as boolean
    return_hybrid = False                                                                                       #Set return setting flag to false

    if is_hybrid:                                                                                               #If hybrid design is enabled
        part_infa.com_object.HybridDesignMode = False                                                           #Turn off hybrid design
        return_hybrid = True                                                                                    #Set flag to turn on hybrid design again at end of script
    
    dlg = DataInputDialog(None, "Involute Gear Parameters")                                                     #New dialog to get user parameters
    if dlg.ShowModal() == wx.ID_OK:                                                                             #If user input is valid and user pressed ok
        module = float(dlg.module.GetValue())                                                                   #Get value form dialog
        number_of_teeth = int(dlg.number_of_teeth.GetValue())                                                   #Get value form dialog
        pressure_angle = float(dlg.pressure_angle.GetValue())                                                   #Get value form dialog
        clearance = float(dlg.clearance.GetValue())                                                             #Get value form dialog
        steps = int(dlg.steps.GetValue())                                                                       #Get value form dialog
        gear_thicness = float(dlg.gear_thicness.GetValue())                                                     #Get value form dialog
        fillet_radius = float(dlg.fillet_radius.GetValue())                                                     #Get value form dialog
        shaft_radius = float(dlg.shaft_radius.GetValue())                                                       #Get value form dialog
        key_d = float(dlg.key_d.GetValue())                                                                     #Get value form dialog
        key_w = float(dlg.key_w.GetValue())                                                                     #Get value form dialog
        has_shaft = dlg.has_shaft.GetValue()                                                                    #Get value form dialog
        has_key = dlg.has_keyway.GetValue()                                                                     #Get value form dialog
        key_mode_index = dlg.key_mode.GetSelection()                                                            # 0 = Ratio, 1 = Fixed (mm)
        
        current_data = {
            "module": dlg.module.GetValue(),
            "teeth": dlg.number_of_teeth.GetValue(),
            "pa": dlg.pressure_angle.GetValue(),
            "clearance": dlg.clearance.GetValue(),
            "steps": dlg.steps.GetValue(),
            "thickness": dlg.gear_thicness.GetValue(),
            "fillet": dlg.fillet_radius.GetValue(),
            "shaft_r": dlg.shaft_radius.GetValue(),
            "key_w": dlg.key_w.GetValue(),
            "key_d": dlg.key_d.GetValue(),
            "key_mode": dlg.key_mode.GetSelection(),
            "has_shaft": dlg.has_shaft.GetValue(),
            "has_key": dlg.has_keyway.GetValue()
        }                                                                                                       #Update current data
    
        with open(SETTINGS_FILE, 'w') as f:                                                                     #Write settings data to jason
            json.dump(current_data, f, indent=4)
    else:                                                                                                       #User canceled or something whent wrong
        dlg.Destroy()                                                                                           #Close dialog
        exit()                                                                                                  #exit script
    dlg.Destroy()                                                                                               #Close dialog
    
    progress_dlg = wx.ProgressDialog(
        "Generating Gear", 
        "Initializing geometry...", 
        maximum=14, 
        parent=None, 
            style=(
                wx.PD_APP_MODAL | 
                wx.PD_AUTO_HIDE | 
                wx.PD_SMOOTH | 
                wx.PD_ELAPSED_TIME |
                wx.PD_REMAINING_TIME
            )
    )
    
    partbody = bodies.add()                                                                                     #Add new body
    sketches_part_body = partbody.sketches                                                                      #Get sketches in part body
    
    try:
        progress_dlg.Update(1, "Creating new Body ...")
        #formulas
        pitch_circle_radius = module * number_of_teeth                                                              #Pitch circle formula
        addendum_circle_radius = pitch_circle_radius + module                                                       #Addendum circle formula
        dedendum_circle_radius = pitch_circle_radius - ( (1 + clearance) * module )                                 #Dedendum circle formula
        base_circle_radius = pitch_circle_radius * math.cos(math.radians(pressure_angle))                           #base circle formula
        
        #Body and Sketch Con
        #partbody.name = "Involute Gear M:" + str(module) + " T:" + str(number_of_teeth)                             #Rename body simple
        shaft_str = f" | Shaft:{shaft_radius}mm" if has_shaft else ""
        if has_key:
            mode_text = "Ratio" if key_mode_index == 0 else "Fixed"
            key_str = f" | Key({mode_text}):{key_w}x{key_d}"
        else:
            key_str = ""
        partbody.name = (f"Involute Gear | M:{module} | T:{number_of_teeth} | PA:{pressure_angle}°"
                         f" | Th:{gear_thicness}mm | F:{fillet_radius}mm"
                         f"{shaft_str}{key_str}")                                                                   #Rename body with all user parameters
        
        part.in_work_object = partbody                                                                              #Make new body inwork object
        hb_sketches = partbody.sketches                                                                             #Get Collection of sketches
        plane_XY = part.origin_elements.plane_xy                                                                    #get reference to XY plane

        progress_dlg.Update(2, "Drawing pitch, addendum and dedendum circles ...")
        
        #create sketch for tooth on xy plane
        sketch_tooth_con = hb_sketches.add(plane_XY)                                                                #Add sketch                                    
        sketch_tooth_con.name = "sketch_tooth_con"                                                                  #Rename Sketch
        ske2D_tooth_con = sketch_tooth_con.open_edition()                                                           #Start Editing Sketch
        constraints = sketch_tooth_con.constraints                                                                  #Get collection of constraints for sketch
        geo_elements = sketch_tooth_con.geometric_elements                                                          #Get collection of geometric elements for sketch
        axis = geo_elements.item("AbsoluteAxis")                                                                    #Get Sketch Axis
        h_axis = axis.get_item("HDirection")                                                                        #Get H direction
        v_axis = axis.get_item("VDirection")                                                                        #Get V direction
        origin = sketch_tooth_con.absolute_axis.origin                                                              #Get origin
       
        center_point = ske2D_tooth_con.create_point(0, 0,)                                                          #Create Center Point
        center_point.name = "Center Point"                                                                          #Rename Center Point
        center_point_on = constraints.add_bi_elt_cst(CatConstraintType.catCstTypeOn, center_point, origin)          #Make coincident with origin
        center_point_on.name = "Center Point Coincident Origin"                                                     #Rename Constraint
       
        #create pitch circle
        pitch_circle = ske2D_tooth_con.create_closed_circle(0, 0, pitch_circle_radius)                              #Draw new circle
        pitch_circle.construction = True                                                                            #Make construction element
        pitch_circle.name = "Pitch Circle"                                                                          #Rename
        cnst_pitch_con = constraints.add_bi_elt_cst(CatConstraintType.catCstTypeConcentricity, pitch_circle, origin)#Make concentric to origin
        cnst_pitch_con.name = "Pitch Circle Concentric Origin"                                                      #Rename Constraint
        cnst_rad_pitch = constraints.add_mono_elt_cst(CatConstraintType.catCstTypeRadius, pitch_circle)             #Add radius constraint
        cnst_rad_pitch.mode = CatConstraintMode.catCstModeDrivingDimension                                          #Set to driving dimension
        cnst_rad_pitch.dimension.value = pitch_circle_radius                                                        #Set dimension
        cnst_rad_pitch.name = "Picth Circle Radius"                                                                 #Rename Constraint
        
        #create addendum circle
        addendum_circle = ske2D_tooth_con.create_closed_circle(0, 0, addendum_circle_radius)                        #Draw circle
        addendum_circle.construction = True                                                                         #Make construction element
        addendum_circle.name = "Addendum/Tip Circle"                                                                #Rename
        cnst_add_con = constraints.add_bi_elt_cst(CatConstraintType.catCstTypeConcentricity, 
                addendum_circle, origin)                                                                            #Make concentric to origin
        cnst_add_con.name = "Addendum Circle Concentric Origin"                                                     #Rename Constraint
        cnst_rad_addendum = constraints.add_mono_elt_cst(CatConstraintType.catCstTypeRadius, 
                addendum_circle)                                                                                    #Add radius constraint
        cnst_rad_addendum.mode = CatConstraintMode.catCstModeDrivingDimension                                       #Make driving dimension
        cnst_rad_addendum.dimension.value = addendum_circle_radius                                                  #Set dimension
        cnst_rad_addendum.name = "Addendum Circle Radius"                                                           #Rename Constraint
        
        #create dedendum circle
        dedendum_circle = ske2D_tooth_con.create_closed_circle(0, 0, dedendum_circle_radius)                        #Draw circle
        dedendum_circle.construction = True                                                                         #Set to construction element
        dedendum_circle.name = "Dedendum/Root Circle"                                                               #Rename
        cnst_de_con = constraints.add_bi_elt_cst(CatConstraintType.catCstTypeConcentricity, dedendum_circle, origin)#Make concentric to origin
        cnst_de_con.name = "Dedendum Circle Concentric Origin"                                                      #Rename Constraint
        cnst_rad_dedendum = constraints.add_mono_elt_cst(CatConstraintType.catCstTypeRadius, 
                dedendum_circle)                                                                                    #Add radius constraint
        cnst_rad_dedendum.mode = CatConstraintMode.catCstModeDrivingDimension                                       #Make driving dimension
        cnst_rad_dedendum.dimension.value = dedendum_circle_radius                                                  #Set radius
        cnst_rad_dedendum.name = "Dedendum Circle Radius"                                                           #Rename Constraint
        
        
        #Create centre line
        progress_dlg.Update(3, "Drawing preasure line and center line ...")
        center_line_origin = (0, 0)                                                                                 #Start point of line
        center_line_end_point = (0, addendum_circle_radius)                                                         #End point of line
        
        center_line = ske2D_tooth_con.create_line(*center_line_origin, *center_line_end_point)                      #Draw line
        center_line.construction = True                                                                             #Set to construction
        center_line.name = "Center_line"                                                                            #Rename
        
        center_line_start_point = ske2D_tooth_con.create_point(0, 0)                                                #Create point for start point of line
        center_line_start_point.name = "center line start point"                                                    #Rename
        center_line.start_point = center_line_start_point                                                           #Set as start point
        center_line_end_point = ske2D_tooth_con.create_point(0, addendum_circle_radius)                             #Create end point for line
        center_line_end_point.name = "center line end point"                                                        #Rename
        center_line.end_point = center_line_end_point                                                               #Set as endpoint
        
        center_line_par = constraints.add_bi_elt_cst(CatConstraintType.catCstTypeParallelism, 
                center_line, v_axis)                                                                                #Make line vertical
        center_line_par.name = "Center Line Parrallel V-Direction"                                                  #Rename Constraint
        center_line_on_1 = constraints.add_bi_elt_cst(CatConstraintType.catCstTypeOn, 
                center_line_start_point, origin)                                                                    #Make start point coincident to origin
        center_line_on_1.name = "Center Line Coincident Origin"                                                     #Rename Constraint
        center_line_on_2 = constraints.add_bi_elt_cst(CatConstraintType.catCstTypeOn, 
                center_line_end_point, addendum_circle)                                                             #Make end point coincident to addendum circle
        center_line_on_2.name = "Center Line Coicnident Addendum Circle"                                            #Rename Constraint
        
        #create preasure angle line
        pressure_line = ske2D_tooth_con.create_line(0, 0, 10, 10)                                                   #Draw line
        pressure_line.construction = True                                                                           #Make construction element
        pressure_line.name = "Pressure_Line"                                                                        #Rename
        
        pressure_line_start_point = ske2D_tooth_con.create_point(0, 0)                                              #Create start point for line
        pressure_line_start_point.name = "pressure line start point"                                                #Rename
        pressure_line.start_point = pressure_line_start_point                                                       #Set as start point of line
        
        pressure_line_end_point = ske2D_tooth_con.create_point(10, 10)                                              #Create end-point for line
        pressure_line_end_point.name = "pressure line end point"                                                    #Rename
        pressure_line.end_point = pressure_line_end_point                                                           #Set as endpoint of line
        
        pressure_line_on_1 = constraints.add_bi_elt_cst(CatConstraintType.catCstTypeOn, 
                pressure_line_start_point, origin)                                                                  #Make start point coincident to origin
        pressure_line_on_1.name = "Preasure Line Coicnident Origin"                                                 #Rename Constraint
        pressure_line_angle_cst = constraints.add_bi_elt_cst(CatConstraintType.catCstTypeAngle, 
                pressure_line, center_line)                                                                         #Add new angle constraint
        pressure_line_angle_cst.mode = CatConstraintMode.catCstModeDrivingDimension                                 #Make driving dimension
        pressure_line_angle_cst.dimension.value = pressure_angle                                                    #Set angle
        pressure_line_angle_cst.name = "Preasure Line Angle"                                                        #Rename Constraint
        
        pressure_line_on_2 = constraints.add_bi_elt_cst(CatConstraintType.catCstTypeOn, 
                pressure_line_end_point, addendum_circle)                                                           #Make endpoint coincident to addendum circle
        pressure_line_on_2.name = "Preasure Line Coincident Addendum Circle"                                        #Rename Constraint
        
        #Create Base circle
        progress_dlg.Update(4, "Drawing base circle ...")
        base_circle = ske2D_tooth_con.create_closed_circle(0, 0, base_circle_radius)                                #Draw circle
        base_circle.construction = True                                                                             #Make construction
        base_circle.name = "Base Circle"                                                                            #Rename
        cnst_base_con = constraints.add_bi_elt_cst(CatConstraintType.catCstTypeConcentricity, base_circle, origin)  #Make concentric to origin
        cnst_base_con.name = "Base Circle Concentric Origin"                                                        #Rename Constraint
        cnst_rad_base_circle = constraints.add_mono_elt_cst(CatConstraintType.catCstTypeRadius, 
                base_circle)                                                                                        #Add radius dimension
        cnst_rad_base_circle.mode = CatConstraintMode.catCstModeDrivingDimension                                    #Make driving dimension
        cnst_rad_base_circle.dimension.value = base_circle_radius                                                   #set radius
        cnst_rad_base_circle.name = "Base Circle Radius"                                                            #Rename Constraint
        
        #Calculate invalute flank
        progress_dlg.Update(5, "Calculating and drawing involute flanks ...")
        max_t = math.sqrt(((addendum_circle_radius) / base_circle_radius)**2 - 1)                                   #Calculate maximum parameter value in radians
      
        inv_alpha = math.tan(math.radians(pressure_angle)) - math.radians(pressure_angle)                           #Involute function involute(alpha)
        half_tooth_thickness_angle = (math.pi / (2 * number_of_teeth)) + inv_alpha                                  #Half tooth thinkness
        
        form_circle_radius = max(dedendum_circle_radius + (fillet_radius * module), base_circle_radius)
        sqrt_input = (form_circle_radius / base_circle_radius)**2 - 1
        min_t = math.sqrt(max(0, sqrt_input))
        
        points_list_left = []                                                                                       #Colection of left involute points
        points_list_right = []                                                                                      #Collection of right involute points

        for i in range(steps + 1):                                                                                  #Calculate involute point acording to number of steps
            t = min_t + ((max_t - min_t) / steps) * i 
        
            x_current = base_circle_radius * (math.sin(t) - t * math.cos(t))                                        #Caluclate raw x involute from base circle
            y_current = base_circle_radius * (math.cos(t) + t * math.sin(t))                                        #Calculate raw y involute from base circle
            
            angle = half_tooth_thickness_angle                                                                      #Set angle
            x_l = x_current * math.cos(angle) - y_current * math.sin(angle)                                         #Rotate x to account for tooth thikness
            y_l = x_current * math.sin(angle) + y_current * math.cos(angle)                                         #Rotate y to account for tooth thikness
            
            point_l = ske2D_tooth_con.create_point(x_l, y_l)                                                        #Create left flank involute point for this step
            point_l.name = f"Involute_Point__Left_{i}"                                                              #Rename point
            if i != 0:                                                                                              #Dont fix the point so we can add tangency
                cnst_1 = constraints.add_mono_elt_cst(CatConstraintType.catCstTypeReference, point_l)               #Add fixed constraint
                cnst_1.name = f"Fixed Involute_Point__Left_{i}"                                                     #Rename Constraint
            points_list_left.append(point_l)                                                                        #Add to list
            
            point_r = ske2D_tooth_con.create_point(-x_l, y_l)                                                       #Create right flank involute point for this step
            point_r.name = f"Involute_Point__Right_{i}"                                                             #Rename point
            if i != 0:                                                                                              #Dont fix the point so we can add tangency
                cnst_2 = constraints.add_mono_elt_cst(CatConstraintType.catCstTypeReference, point_r)               #Create fixed constraint
                cnst_2.name = f"Fixed Involute_Point__Right_{i}"                                                    #Rename Constraint
            points_list_right.append(point_r)                                                                       #Add to list

        involute_flank_left = ske2D_tooth_con.create_spline(points_list_left)                                       #Create left involute flank spline
        involute_flank_left.name = "Involute_Flank_Left"                                                            #Rename spline
        
        involute_flank_right = ske2D_tooth_con.create_spline(points_list_right)                                     #Create right involute flank spline
        involute_flank_right.name = "Involute_Flank_right"                                                          #Rename spline
        
        #Create top land
        p_top_left = points_list_left[-1]                                                                           #Get first point of list (Outermost involute point)
        p_top_right = points_list_right[-1]                                                                         #Get first point of list (Outermost involute point)
        
        p_top_left_coord = p_top_left.get_coordinates()                                                             #Get coordinates of point for top land boundary
        p_top_right_coord = p_top_right.get_coordinates()                                                           #Get coordinates of point for top land boundary

        angle_l = math.atan2(p_top_left_coord[1], p_top_left_coord[0])                                              #Calculate polar angle in radians for arc span start
        angle_r = math.atan2(p_top_right_coord[1], p_top_right_coord[0])                                            #Calculate polar angle in radians for arc span end

        top_land = ske2D_tooth_con.create_circle(0, 0, addendum_circle_radius, angle_r, angle_l)                    #Create top land arc on addendum circle
        top_land.name = "Top_Land"                                                                                  #Rename arc
        
        top_land_start_point = ske2D_tooth_con.create_point(p_top_right_coord[0], p_top_right_coord[1])             #Create start point for arc
        top_land_start_point.name = "top_land start point"                                                          #Rename
        top_land.start_point = top_land_start_point                                                                 #Set as start point
        
        top_land_end_point = ske2D_tooth_con.create_point(p_top_left_coord[0], p_top_left_coord[1])                 #Create end point for arc
        top_land_end_point.name = "top_land end point"                                                              #Rename
        top_land.end_point = top_land_end_point                                                                     #Set as endpoint

        top_land_on_1 = constraints.add_bi_elt_cst(CatConstraintType.catCstTypeOn, 
                top_land_start_point, p_top_right)                                                                  #Make coincedent to right involute spline
        top_land_on_1.name = "Top Land Coincendent Involute Right"                                                  #Rename Constraint
        top_land_on_2 = constraints.add_bi_elt_cst(CatConstraintType.catCstTypeOn, 
                top_land_end_point, p_top_left)                                                                     #Make coincedent to left involute spline
        top_land_on_2.name = "Top Land Coincendent Involute Left"                                                   #Rename Constraint
        
        cnst_rad_top_land = constraints.add_mono_elt_cst(CatConstraintType.catCstTypeRadius, top_land)              #Add radius constraint to arc
        cnst_rad_top_land.mode = CatConstraintMode.catCstModeDrivingDimension                                       #Make driving dimmension
        cnst_rad_top_land.dimension.value = addendum_circle_radius                                                  #Set radius
        cnst_rad_top_land.name = "Top Land Radius"                                                                  #Rename Constraint
        
        #Create root fillets 
        progress_dlg.Update(6, "Drawing fillets ...")
        if base_circle_radius > dedendum_circle_radius:                                                             #Only run if the base circle is larger than the dedendum (requires a transition curve)
            # Get the first point of the involute (where it touches the base circle)
            p_start_involute = points_list_left[0]
            x_s, y_s = p_start_involute.get_coordinates()
            
            # Calculate standard fillet radius based on gear module
            r_f = fillet_radius * module
            
            # Determine the start height of the fillet relative to the dedendum
            r_fillet_start = dedendum_circle_radius + r_f
            angle_s = math.atan2(y_s, x_s)
            
            # Calculate coordinates for where the radial line meets the fillet
            x_f_start = r_fillet_start * math.cos(angle_s)
            y_f_start = r_fillet_start * math.sin(angle_s)
            
            # ---left fillet and line---
            # Create a line connecting the involute start to the fillet start
            radial_line_left = ske2D_tooth_con.create_line(x_s, y_s, x_f_start, y_f_start)
            radial_line_left.name = "Radial_Line_Left"
            
            # Define endpoints for the left radial line
            radial_line_left_start_point = ske2D_tooth_con.create_point(x_s, y_s)
            radial_line_left_start_point.name = "radial_line_left start point"
            radial_line_left.start_point = radial_line_left_start_point
            rad_line_left_cnst_start = constraints.add_mono_elt_cst(CatConstraintType.catCstTypeReference, radial_line_left_start_point)
            rad_line_left_cnst_start.name = "Fixed Radial Line Start Point Left"
     
            radial_line_left_end_point = ske2D_tooth_con.create_point(x_f_start, y_f_start)
            radial_line_left_end_point.name = "radial_line_left end point"
            radial_line_left.end_point = radial_line_left_end_point  

            # Constrain the line to be coincident with the involute and tangent to the flank
            radial_line_on_1 = constraints.add_bi_elt_cst(CatConstraintType.catCstTypeOn, radial_line_left_start_point, points_list_left[0])
            radial_line_on_1.name = "Radial Line Left Coincendent Involute Spline"
            radial_line_tangnt = constraints.add_bi_elt_cst(CatConstraintType.catCstTypeTangency, radial_line_left, involute_flank_left )
            radial_line_tangnt.name = "Radial Line Left Tangent Involute Spline"
            rad_line_left_cnst_end = constraints.add_mono_elt_cst(CatConstraintType.catCstTypeReference, radial_line_left_end_point)
            rad_line_left_cnst_end.name = "Fixed Radial Line End Point Left"

            # Calculate the center point (cx, cy) of the left fillet arc
            angle_perp = angle_s + (math.pi / 2)
            cx = x_f_start + r_f * math.cos(angle_perp)
            cy = y_f_start + r_f * math.sin(angle_perp)
            
            # Determine start and end angles for the fillet arc
            a1 = math.atan2(y_f_start - cy, x_f_start - cx)
            a2 = math.atan2(-cy, -cx)
            
            # Create the left root fillet arc
            fillet_left = ske2D_tooth_con.create_circle(cx, cy, r_f, a2, a1)
            fillet_left.name = "Root_Fillet_Left"
     
            # Define endpoints for the left fillet arc
            fillet_left_end_point = ske2D_tooth_con.create_point(x_f_start, y_f_start)
            fillet_left_end_point.name = "fillet_left end point"
            fillet_left.end_point = fillet_left_end_point
        
            fillet_left_start_point = ske2D_tooth_con.create_point(r_f * math.cos(a2), r_f * math.sin(a2))
            fillet_left_start_point.name = "fillet_left start point"
            fillet_left.start_point = fillet_left_start_point

            # Constrain the fillet to the radial line and set its radius dimension
            fillet_left_on_1 = constraints.add_bi_elt_cst(CatConstraintType.catCstTypeOn, fillet_left_end_point, radial_line_left_end_point)
            fillet_left_on_1.name = "Fillet Left Coincident Radial Line Left"
            fillet_left_start_pt = constraints.add_mono_elt_cst(CatConstraintType.catCstTypeReference, fillet_left_start_point) 
            fillet_left_start_pt.name = "Fixed Fillet Left Start Point"
            cnst_rad_fillet_left = constraints.add_mono_elt_cst(CatConstraintType.catCstTypeRadius, fillet_left)
            cnst_rad_fillet_left.mode = CatConstraintMode.catCstModeDrivingDimension
            cnst_rad_fillet_left.dimension.value = r_f
            cnst_rad_fillet_left.name = "Fillet Left Radius"
            
            # ---Right fillet and line---
            # Create a mirrored radial line for the right side of the tooth      
            radial_line_right = ske2D_tooth_con.create_line(-x_s, y_s, -x_f_start, y_f_start)
            radial_line_right.name = "Radial_Line_Right"
            
            # Define endpoints for the right radial line
            radial_line_right_start_point = ske2D_tooth_con.create_point(-x_s, y_s)
            radial_line_right_start_point.name = "radial_line_right start point"
            radial_line_right.start_point = radial_line_right_start_point
            rad_line_right_cnst_start = constraints.add_mono_elt_cst(CatConstraintType.catCstTypeReference, radial_line_right_start_point)
            rad_line_right_cnst_start.name = "Fixed Radial Line Start Point Right"
        
            radial_line_right_end_point = ske2D_tooth_con.create_point(-x_f_start, y_f_start)
            radial_line_right_end_point.name = "radial_line_right end point"
            radial_line_right.end_point = radial_line_right_end_point  

            # Constrain the line to be coincident with the involute and tangent to the flank
            radial_line_on_1 = constraints.add_bi_elt_cst(CatConstraintType.catCstTypeOn, radial_line_right_start_point, points_list_right[0])
            radial_line_on_1.name = "Radial Line Right Coincendent Involute Spline"
            radial_line_tangnt = constraints.add_bi_elt_cst(CatConstraintType.catCstTypeTangency, radial_line_right, involute_flank_right )
            radial_line_tangnt.name = "Radial Line Right Tangent Involute Spline"
            rad_line_right_cnst_end = constraints.add_mono_elt_cst(CatConstraintType.catCstTypeReference, radial_line_right_end_point)
            rad_line_right_cnst_end.name = "Fixed Radial Line End Point Right"
            
            # Calculate the mirrored center point and angles for the right fillet
            cx_r, cy_r = -cx, cy
            a1_r = math.atan2(y_f_start - cy_r, -x_f_start - cx_r)
            a2_r = math.atan2(-cy_r, -cx_r)
            
            # Create the right root fillet arc
            fillet_right = ske2D_tooth_con.create_circle(cx_r, cy_r, r_f, a1_r, a2_r)
            fillet_right.name = "Root_Fillet_Right"
            
            # Define and constrain the right fillet endpoints
            fillet_right_start_point = ske2D_tooth_con.create_point(-x_f_start, y_f_start)
            fillet_right_start_point.name = "fillet_right start point"
            fillet_right.start_point = fillet_right_start_point
        
            fillet_right_end_point = ske2D_tooth_con.create_point(r_f * math.cos(a2_r), r_f * math.sin(a2_r))
            fillet_right_end_point.name = "fillet_right end point"
            fillet_right.end_point = fillet_right_end_point

            # Finalize constraints and radius for the right fillet
            fillet_right_on_1 = constraints.add_bi_elt_cst(CatConstraintType.catCstTypeOn, fillet_right_start_point, radial_line_right_end_point)
            fillet_right_on_1.name = "Fillet Right Coincident Radial Line Right"
            fillet_right_start_pt = constraints.add_mono_elt_cst(CatConstraintType.catCstTypeReference, fillet_right_end_point) 
            fillet_right_start_pt.name = "Fixed Fillet Right Start Point"
            cnst_rad_fillet_right = constraints.add_mono_elt_cst(CatConstraintType.catCstTypeRadius, fillet_right)
            cnst_rad_fillet_right.mode = CatConstraintMode.catCstModeDrivingDimension
            cnst_rad_fillet_right.dimension.value = r_f
            cnst_rad_fillet_right.name = "Fillet Right Radius"
            
        else:
            # Base circle is inside or on the dedendum circle
            # No radial line needed; fillet attaches directly to the start of the involute
            p_start_left = points_list_left[0]
            x_s, y_s = p_start_left.get_coordinates()
            
            r_f = fillet_radius * module
            angle_s = math.atan2(y_s, x_s)
            
            # Center of the left fillet
            # We place it so it's tangent to the start point and reaches the dedendum circle
            angle_perp = angle_s + (math.pi / 2)
            cx = x_s + r_f * math.cos(angle_perp)
            cy = y_s + r_f * math.sin(angle_perp)

            # Angles for the arc (from dedendum circle to involute start)
            a1 = math.atan2(y_s - cy, x_s - cx)
            a2 = math.atan2(-cy, -cx)
            
            # Create Left Fillet
            fillet_left = ske2D_tooth_con.create_circle(cx, cy, r_f, a2, a1)
            fillet_left.name = "Root_Fillet_Left"
            
            fillet_left_end_point = ske2D_tooth_con.create_point(x_s, y_s)
            fillet_left_end_point.name = "fillet_left_end_point"
            fillet_left.end_point = fillet_left_end_point
            #Put the point on the spline and make tangent
            fillet_l_on = constraints.add_bi_elt_cst(CatConstraintType.catCstTypeOn, fillet_left_end_point, p_start_left)
            fillet_l_on.name = "Fillet Left Coincident Involute Spline"
            fillet_l_t = constraints.add_bi_elt_cst(CatConstraintType.catCstTypeTangency, fillet_left, involute_flank_left)
            fillet_l_t.name = "Fillet Left Tangent Involute Spline"
            
            fillet_left_start_point = ske2D_tooth_con.create_point(dedendum_circle_radius * math.cos(a2), dedendum_circle_radius * math.sin(a2))
            fillet_left_start_point.name = "fillet_left_start_point"
            fillet_left.start_point = fillet_left_start_point
            
            # Add Radius Constraint
            cnst_rad_l = constraints.add_mono_elt_cst(CatConstraintType.catCstTypeRadius, fillet_left)
            cnst_rad_l.dimension.value = r_f
            cnst_rad_l.name = "Fillet Left Radius"

            # Create Right Fillet (Mirror of left)
            cx_r, cy_r = -cx, cy
            a1_r = math.atan2(y_s - cy_r, -x_s - cx_r)
            a2_r = math.atan2(-cy_r, -cx_r)
            
            fillet_right = ske2D_tooth_con.create_circle(cx_r, cy_r, r_f, a1_r, a2_r)
            fillet_right.name = "Root_Fillet_Right"
            
            fillet_right_start_point = ske2D_tooth_con.create_point(-x_s, y_s)
            fillet_right_start_point.name = "fillet_right_start_point"
            fillet_right.start_point = fillet_right_start_point
            #Put the point on the spline and make tangent
            fillet_r_on = constraints.add_bi_elt_cst(CatConstraintType.catCstTypeOn, fillet_right_start_point, points_list_right[0])
            fillet_r_on.name = "Fillet Right Coincident Involute Spline"
            fillet_r_t = constraints.add_bi_elt_cst(CatConstraintType.catCstTypeTangency, fillet_right, involute_flank_right)
            fillet_r_t.name = "Fillet Right Tangent Involute Spline"
            
            fillet_right_end_point = ske2D_tooth_con.create_point(dedendum_circle_radius * math.cos(a2_r), dedendum_circle_radius * math.sin(a2_r))
            fillet_right_end_point.name = "fillet_right_end_point"
            fillet_right.end_point = fillet_right_end_point
            
            cnst_rad_r = constraints.add_mono_elt_cst(CatConstraintType.catCstTypeRadius, fillet_right)
            cnst_rad_r.dimension.value = r_f
            cnst_rad_r.name = "Fillet Right Radius"
            
            #Add distance constraints to fully define sketch
            dist_cst_1 = constraints.add_bi_elt_cst(CatConstraintType.catCstTypeDistance, origin, fillet_left_end_point)
            dist_cst_1.mode = CatConstraintMode.catCstModeDrivingDimension
            dist_cst_1.name = "Fillet Left End Point Origin Distance"
            
            dist_cst_2 = constraints.add_bi_elt_cst(CatConstraintType.catCstTypeDistance, origin, fillet_right_start_point)
            dist_cst_2.mode = CatConstraintMode.catCstModeDrivingDimension
            dist_cst_2.name = "Fillet Right End Point Origin Distance"


        #Add the root of tooth
        progress_dlg.Update(7, "Drawing root ...")
        angle_root_l = (math.atan2(cy, -cx) + 2 * math.pi) % (2 * math.pi)                                  #Calculate the normalized angles (0 to 2π) for the left and root point
        angle_root_r = (math.atan2(cy_r, -cx_r) + 2 * math.pi) % (2 * math.pi)                              #Calculate the normalized angles (0 to 2π) for the right and root point
        
        root_arc = ske2D_tooth_con.create_circle(0, 0, dedendum_circle_radius, angle_root_l, angle_root_r)  #Create the arc representing the bottom of the tooth space on the dedendum circle
        root_arc.name = "Tooth_Root_Arc"                                                                    #Rename arc
     
        root_r_coords = fillet_right_end_point.get_coordinates()                                            #Get the junction coordinates from the end of the right fillet
     
        root_arc_start_point = ske2D_tooth_con.create_point(root_r_coords[0], root_r_coords[1])             #Starting point for the root arc (right side)     
        root_arc_start_point.name = "root_arc start point"                                                  #Rename point

        root_arc.start_point = root_arc_start_point                                                         #Set as start point of arc
        
        root_l_coords = fillet_left_start_point.get_coordinates()                                           #Get the junction coordinates from the start of the left fillet

        root_arc_end_point = ske2D_tooth_con.create_point(root_l_coords[0], root_l_coords[1])               #End point for the root arc (left side)
        root_arc_end_point.name = "root_arc end point"                                                      #Rename point

        root_arc.end_point = root_arc_end_point                                                             #Set as endpoint of arc

        root_arc_on_1 = constraints.add_bi_elt_cst(CatConstraintType.catCstTypeOn,
                root_arc_start_point, fillet_right_end_point)                                               #Make coincedent to root arc
        root_arc_on_1.name = "Root Arc Coincident Fillet Right"                                             #Rename Constraint
        root_arc_on_2 = constraints.add_bi_elt_cst(CatConstraintType.catCstTypeOn,
                root_arc_end_point, fillet_left_start_point)                                                #Make coincedent to root arc
        root_arc_on_2.name = "Root Arc Coincident Fillet Left"                                              #Rename Constraint
        root_arc_con = constraints.add_bi_elt_cst(CatConstraintType.catCstTypeConcentricity, root_arc, origin)#Make concentric to origin
        root_arc_con.name = "Root Arc Concentric Origin"                                                    #Rename Constraint

        if base_circle_radius <= dedendum_circle_radius:                                                    #Add different constartis when there is no extention
            tan_1 = constraints.add_bi_elt_cst(CatConstraintType.catCstTypeTangency, root_arc, fillet_left) #Tangency
            tan_1.name = "Root Arc Tangent Fillet Left"                                                     #Rename Constraint
            tan_2 = constraints.add_bi_elt_cst(CatConstraintType.catCstTypeTangency, root_arc, fillet_right)#Tangency
            tan_2.name = "Root Arc Tangent Fillet Right"                                                    #Rename Constraint
            con_1 = constraints.add_bi_elt_cst(CatConstraintType.catCstTypeOn, root_arc, dedendum_circle)   #Coincident
            con_1.name  = "Root Arc Coincident Dedendum Circle"                                             #Rename Constraint
        
        #Close edition
        sketch_tooth_con.close_edition()                                                                    #Stop editing sketch
        part.update()                                                                                       #Update part
        
        progress_dlg.Update(8, "Drawing gear body ...")
        
        #create sketch for gear body on xy plane
        sketch_body_con = hb_sketches.add(plane_XY)                                                         #Create sketch on xy plane
        sketch_body_con.name = "sketch_body_con"                                                            #Rename sketch
        ske2D_body_con = sketch_body_con.open_edition()                                                     #Start editing sketch
        constraints_body = sketch_body_con.constraints                                                      #Get sketch constraints
        geo_elements_bdy = sketch_body_con.geometric_elements                                               #Get sketch geometric elements
        axis = geo_elements_bdy.item("AbsoluteAxis")                                                        #Get sketch axis
        h_axis = axis.get_item("HDirection")                                                                #Get H direction
        v_axis = axis.get_item("VDirection")                                                                #Get V direction
        
        origin = sketch_body_con.absolute_axis.origin                                                       #Get origin
       
        #create Body circle
        gear_circle = ske2D_body_con.create_closed_circle(0, 0, base_circle_radius + pad_tol)               #Draw circle
        gear_circle.name = "Body Circle"                                                                    #Rename circle
        cnst_con_bdy = constraints_body.add_bi_elt_cst(CatConstraintType.catCstTypeConcentricity, 
                gear_circle, origin)                                                                        #Make concentric to origin
        cnst_con_bdy.name = "Body Circle Concentric Origin"                                                 #Rename Constraint
        cnst_gear = constraints_body.add_mono_elt_cst(CatConstraintType.catCstTypeRadius, 
                gear_circle)                                                                                #Add radius constraint
        cnst_gear.mode = CatConstraintMode.catCstModeDrivingDimension                                       #Make driving dimmension

        cnst_gear.dimension.value = dedendum_circle_radius + pad_tol                                        #Add radius (pad_tol is to make sure their are no gaps when creating the gear)
        cnst_gear.name = "Body Circle Radius"                                                               #Rename Constraint
        
        #Close edition
        sketch_body_con.close_edition()                                                                     #Stop editing the sketch
        part.update()                                                                                       #Update the part
        
        #Create pad for gear body
        progress_dlg.Update(9, "Extruding gear body...")
        pad_body = shape_factory.add_new_pad(sketch_body_con, gear_thicness)                                #Add new pad for gear body
        pad_body.direction_orientation = CatPrismOrientation.catRegularOrientation                          #Set direction
        pad_body.first_limit.limit_mode = CatLimitMode.catOffsetLimit                                       #Set limit mode to offset
        pad_body.first_limit.dimension.value = gear_thicness                                                #Set pad dimmension
        pad_body.name = "Gear Body"                                                                         #Rename pad
        pad_body.set_profile_element(part.create_reference_from_object(sketch_body_con))                    #Link sketch to pad
        
        part.update()                                                                                       #Update part
        
        #Create pad for geart tooth
        progress_dlg.Update(10, "Extruding gear tooth...")
        pad_tooth = shape_factory.add_new_pad(sketch_tooth_con, gear_thicness)                              #Add new pad for gear tooth
        pad_tooth.direction_orientation = CatPrismOrientation.catRegularOrientation                         #Set direction
        pad_tooth.first_limit.limit_mode = CatLimitMode.catOffsetLimit                                      #Set limit mode to offset
        pad_tooth.first_limit.dimension.value = gear_thicness                                               #Set pad dimmension
        pad_tooth.name = "Gear Tooth"                                                                       #Rename pad
        pad_tooth.set_profile_element(part.create_reference_from_object(sketch_tooth_con))                  #Link sketch to pad
        
        part.update()                                                                                       #Update part
        
        progress_dlg.Update(11, f"Patterning {number_of_teeth} teeth...")
        
        # Create Circular Pattern for remaining gear teeth
        ref_axis = part.create_reference_from_object(plane_XY)                                              #Rotation axis
        ref_origin = part.create_reference_from_object(origin)                                              #Origin point
        
        circ_pattern = shape_factory.add_new_circ_pattern(
            pad_tooth,                                                                                      # 1. Feature to copy
            1,                                                                                              # 2. Radial instances
            number_of_teeth,                                                                                # 3. Angular instances
            0.0,                                                                                            # 4. Radial step
            360.0/number_of_teeth,                                                                          # 5. Angular step
            1,                                                                                              # 6. Radial position
            1,                                                                                              # 7. Angular position
            ref_origin,                                                                                     # 8. Rotation center reference
            ref_axis,                                                                                       # 9. Rotation axis reference
            False,                                                                                          # 10. Is reversed?
            0.0,                                                                                            # 11. Rotation angle
            True                                                                                            # 12. Is radius aligned?
        )
        
        circ_pattern.name = "Teeth"                                                                         #Rename pattern
        
        part.update()                                                                                       #Update part
        
        if has_shaft:
            progress_dlg.Update(12, "Cutting shaft hole...")
            
            #Create shaft hole
            shaft_hole = shape_factory.add_new_hole_from_point(0, 0, 0, plane_XY, gear_thicness)                #Create a new Hole feature

            shaft_hole.diameter.value = shaft_radius * 2                                                        #Set the diameter of the hole
            shaft_hole.bottom_type = 1                                                                          #Set to through all (Up to last)
            shaft_hole.reverse()                                                                                #Reverse the direction 0,0,-1
            shaft_hole.name = "Shaft_Hole"                                                                      #Rename hole feature
            shaft_hole.sketch.name = "Shaft Hole Con"                                                           #Rename sketch made by hole feature
            sketch_hole = shaft_hole.sketch                                                                     #Get the sketch
            
            ske2D_hole_con = sketch_hole.open_edition()                                                         #Edit the sketch
            constraints_hole = sketch_hole.constraints                                                          #Get sketch constraints
            geo_elements_hole = sketch_hole.geometric_elements                                                  #Get the geometric elements
            point = geo_elements_hole.item("Point.1")                                                           #Get the point
            point.name = "Hole Center Point"                                                                    #Rename the point
            cnst_hole = constraints_hole.add_mono_elt_cst(CatConstraintType.catCstTypeReference, point)         #Fix the point
            cnst_hole.name = "Fixed Centre Point"                                                               #Rename Constraint
            
            sketch_hole.close_edition()                                                                         #Close the sketch
            
            selectionSet.clear()                                                                                #Clear selection
            selectionSet.add(shaft_hole.sketch)                                                                 #Add hole feature sketch to selection
            selectionSet.vis_properties.set_show(1)                                                             #Hide selecton
            selectionSet.clear()                                                                                #Clear selection

            part.update()                                                                                       #Update part
            
            if has_key:
                progress_dlg.Update(13, "Cutting key hole...")
                #create sketch for key way on xy plane
                sketch_key_con = hb_sketches.add(plane_XY)                                                          #Create sketch on xy plane
                sketch_key_con.name = "sketch_key_con"                                                              #Rename sketch
                ske2D_key_con = sketch_key_con.open_edition()                                                       #Start editing sketch
                constraints_key = sketch_key_con.constraints                                                        #Get sketch constraints
                geo_elements_ky = sketch_key_con.geometric_elements                                                 #Get sketch geometric elements
                axis_k = geo_elements_ky.item("AbsoluteAxis")                                                       #Get sketch axis
                h_axis = axis_k.get_item("HDirection")                                                              #Get H direction
                v_axis = axis_k.get_item("VDirection")                                                              #Get V direction
                
                origin_k = sketch_key_con.absolute_axis.origin                                                      #Get origin
                
                if key_mode_index == 0:
                    kw_width = (shaft_radius * 2) / key_w                                                           #Calculate key width, shaft diameter divided by ratio
                    kw_depth = (shaft_radius * 2) / key_d                                                           #Calculate key depth, shaft diameter divided by ratio
                else:
                    kw_width = key_w                                                                                # Use the measurement directly from the user input
                    kw_depth = key_d                                                                                # Use the measurement directly from the user input
                
                y_start_inside = 0                                                                                  #Start at origin
                y_end = shaft_radius + kw_depth                                                                     #Depth, key depth + shaft radius
                x_left = -(kw_width / 2)                                                                            #Left Start point
                x_right = kw_width / 2                                                                              #Right end point

                line1 = ske2D_key_con.create_line(x_left, y_start_inside, x_right, y_start_inside)                  # Bottom
                line2 = ske2D_key_con.create_line(x_right, y_start_inside, x_right, y_end)                          # Right
                line3 = ske2D_key_con.create_line(x_right, y_end, x_left, y_end)                                    # Top
                line4 = ske2D_key_con.create_line(x_left, y_end, x_left, y_start_inside)                            # Left
                
                line1.name = "Line_1"                                                                               #Rename line
                line2.name = "Line_2"                                                                               #Rename line
                line3.name = "Line_3"                                                                               #Rename line
                line4.name = "Line_4"                                                                               #Rename line
                
                line1_sp = ske2D_key_con.create_point(x_left, y_start_inside)                                       #Create start point for line
                line1_sp.name = "line1_sp"                                                                          #Rename point
                line1.start_point = line1_sp                                                                        #Set point to line
                l1_s = constraints_key.add_mono_elt_cst(CatConstraintType.catCstTypeReference, line1_sp)            #Add fixed constraint
                l1_s.name = "Fixed Line 1 Start"                                                                    #Rename Constraint
                
                line1_ep = ske2D_key_con.create_point(x_right, y_start_inside)                                      #Create end point for line
                line1_ep.name = "line1_ep"                                                                          #Rename point
                line1.end_point = line1_ep                                                                          #Set point to line
                l1_e = constraints_key.add_mono_elt_cst(CatConstraintType.catCstTypeReference, line1_ep)            #Add fixed constraint
                l1_e.name = "Fixed Line 1 End"                                                                      #Rename Constraint
                
                line2_sp = ske2D_key_con.create_point(x_right, y_start_inside)                                      #Create start point for line
                line2_sp.name = "line2_sp"                                                                          #Rename point
                line2.start_point = line2_sp                                                                        #Set point to line
                l2_s = constraints_key.add_mono_elt_cst(CatConstraintType.catCstTypeReference, line2_sp)            #Add fixed constraint
                l2_s.name = "Fixed Line 2 Start"                                                                    #Rename Constraint
                
                line2_ep = ske2D_key_con.create_point(x_right, y_end)                                               #Create end point for line
                line2_ep.name = "line2_ep"                                                                          #Rename point
                line2.end_point = line2_ep                                                                          #Set point to line
                l2_e = constraints_key.add_mono_elt_cst(CatConstraintType.catCstTypeReference, line2_ep)            #Add fixed constraint
                l2_e.name = "Fixed Line 2 End"                                                                      #Rename Constraint
                
                line3_sp = ske2D_key_con.create_point(x_right, y_end)                                               #Create start point for line
                line3_sp.name = "line3_sp"                                                                          #Rename point
                line3.start_point = line3_sp                                                                        #Set point to line
                l3_s = constraints_key.add_mono_elt_cst(CatConstraintType.catCstTypeReference, line3_sp)            #Add fixed constraint
                l3_s.name = "Fixed Line 3 Start"                                                                    #Rename Constraint
                
                line3_ep = ske2D_key_con.create_point(x_left, y_end)                                                #Create end point for line
                line3_ep.name = "line3_ep"                                                                          #Rename point
                line3.end_point = line3_ep                                                                          #Set point to line
                l3_e = constraints_key.add_mono_elt_cst(CatConstraintType.catCstTypeReference, line3_ep)            #Add fixed constraint
                l3_e.name = "Fixed Line 3 End"                                                                      #Rename Constraint
                
                line4_sp = ske2D_key_con.create_point(x_left, y_end)                                                #Create start point for line 
                line4_sp.name = "line4_sp"                                                                          #Rename point
                line4.start_point = line4_sp                                                                        #Set point to line
                l4_s = constraints_key.add_mono_elt_cst(CatConstraintType.catCstTypeReference, line4_sp)            #Add fixed constraint
                l4_s.name = "Fixed Line 4 Start"                                                                    #Rename Constraint
                
                line4_ep = ske2D_key_con.create_point(x_left, y_start_inside)                                       #Create end point for line
                line4_ep.name = "line4_ep"                                                                          #Rename point
                line4.end_point = line4_ep                                                                          #Set point to line
                l4_e = constraints_key.add_mono_elt_cst(CatConstraintType.catCstTypeReference, line4_ep)            #Add fixed constraint
                l4_e.name = "Fixed Line 4 End"                                                                      #Rename Constraint

                sketch_key_con.close_edition()                                                                      #Close sketch
                
                #Create key pocket
                keyway_pocket = shape_factory.add_new_pocket(sketch_key_con, gear_thicness)                         #Add new pocket feature

                keyway_pocket.first_limit.limit_mode = CatLimitMode.catOffsetLimit                                  #Set limit mode to offset
                keyway_pocket.direction_orientation = CatPrismOrientation.catRegularOrientation                     #Set orientation
                keyway_pocket.name = "Key Pocket"                                                                   #Rename pocket
                keyway_pocket.set_profile_element(part.create_reference_from_object(sketch_key_con))                #Add scketch to feature as reference
                
                part.update()                                                                                       #Update part

        progress_dlg.Update(14, "Finalizing part...")

        if return_hybrid:                                                                                           #If hybrid desgin was turned off
            part_infa.com_object.HybridDesignMode = True                                                            #Turn hybrid desgin back on
            
        progress_dlg.Destroy()
        
    except Exception as e:                                                                                          #If any excption occurs during geomtry creation
        selectionSet.clear()                                                                                        #Clear selection
        selectionSet.add(partbody)                                                                                  #Select body we created
        selectionSet.delete()                                                                                       #Delete selection
        selectionSet.clear()                                                                                        #Clear selection

        if return_hybrid:                                                                                           #If hybrid desgin was turned off
            part_infa.com_object.HybridDesignMode = True                                                            #Turn hybrid desgin back on
        
        full_traceback = traceback.format_exc()
        print(full_traceback) 
        
        #error_msg = f"An error occurred during gear generation:\n\n{str(e)}"                                        #Generate error text
        error_msg = (
            f"Error Summary: {str(e)}\n"
            f"------------------------------------------\n"
            f"Technical Debug Info:\n\n{full_traceback}"
        )
        
        #wx.MessageBox(error_msg, "Script Error", wx.OK | wx.ICON_ERROR)                                             #Display error message to user
        e_dlg = dialogs.ScrolledMessageDialog(None, error_msg, "Script Error")
        
        error_icon = wx.ArtProvider.GetBitmap(wx.ART_ERROR, wx.ART_MESSAGE_BOX)
        icon_bitmap = wx.StaticBitmap(e_dlg, wx.ID_ANY, error_icon)
        
        header_text = wx.StaticText(e_dlg, label="An error occurred during gear generation:")
        header_font = wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        header_text.SetFont(header_font)
        
        main_sizer = e_dlg.GetSizer()
        
        header_sizer = wx.BoxSizer(wx.HORIZONTAL)
        header_sizer.Add(icon_bitmap, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 15)
        header_sizer.Add(header_text, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        
        main_sizer.Prepend(header_sizer, 0, wx.EXPAND)
        
        mono_font = wx.Font(9, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        e_dlg.text.SetFont(mono_font)
        
        e_dlg.SetSize((600, 400)) 
        
        e_dlg.CenterOnParent()
        e_dlg.ShowModal()
        e_dlg.Destroy()
        
        if progress_dlg:
            progress_dlg.Destroy()
        
        part.update()                                                                                               #Update part
        
        exit()                                                                                                      #Exit Script