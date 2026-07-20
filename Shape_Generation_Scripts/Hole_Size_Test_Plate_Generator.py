'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Hole_Size_Test_Plate_Generator.py
    Version:        1.4
    Code:           Python3.10.4, Pycatia 0.10.0
    Release:        V5R32
    Purpose:        Generate a rectangular test plate with a grid of incrementally sized through-holes.
    Author:         Kai-Uwe Rathjen
    Date:           02.06.26
    Description:    Creates a rectangular pad from user-defined width, length, and thickness, then fills it with a
                    grid of through-holes. The user specifies the number of holes, a starting diameter, and a step
                    value so that each hole increments in size. Holes are arranged left-to-right, top-to-bottom in
                    order of increasing diameter. The script uses CATIA Part Design Hole features (through-all).
                    Settings are saved to AppData for re-use on the next run.
    dependencies = [
                    "pycatia",
                    "wxPython",
                    ]
    requirements:   Python >= 3.10
                    pycatia
                    Catia V5 running with an open part.
                    This script needs an open part document.
                    Hybrid design should be disabled; the script will temporarily disable it if it is on.
    -----------------------------------------------------------------------------------------------------------------------

    Change:         03.06.26 1.1: Fix E741: rename l to length; fix E701: expand single-line if guard.
                    03.06.26 1.2: Fix F401: remove CatConstraintMode; fix F841: remove unused name variable; fix E701: expand bare except: pass.
                    03.06.26 1.3: Fix E722: replace bare except with except Exception.
                    20.07.26 1.4: Import enums from pycatia.enumeration.enums; use CatVisPropertyShow for set_show.

    -----------------------------------------------------------------------------------------------------------------------
'''

#Imports
import math
import os
import json
import ctypes
import traceback
import wx
import wx.lib.dialogs as dialogs
from pycatia import catia
from pycatia.mec_mod_interfaces.part_document import PartDocument
from pycatia.enumeration.enums import CatConstraintType, CatHoleType, CatLimitMode, CatPrismOrientation
from pycatia.enumeration.enums import CatVisPropertyShow


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


class DataInputDialog(wx.Dialog):
    def __init__(self, parent, title):
        self.hardcoded_defaults = {
            "width":     "300.0",
            "length":    "300.0",
            "thickness": "5.0",
            "n_holes":   "25",
            "start_dia": "2.0",
            "step":      "1.0",
        }
        defaults = self.hardcoded_defaults.copy()

        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r') as f:
                    defaults.update(json.load(f))
            except Exception:                                                                                            # Fallback to hardcoded defaults on error
                pass

        super().__init__(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.STAY_ON_TOP)

        vbox = wx.BoxSizer(wx.VERTICAL)

        grid = wx.FlexGridSizer(6, 3, 10, 10)                                                                           # 6 rows, 3 columns (label | field | unit)

        self.width     = wx.TextCtrl(self, value=str(defaults["width"]))                                                 # Initilize field with default value
        self.length    = wx.TextCtrl(self, value=str(defaults["length"]))                                                # Initilize field with default value
        self.thickness = wx.TextCtrl(self, value=str(defaults["thickness"]))                                             # Initilize field with default value
        self.n_holes   = wx.TextCtrl(self, value=str(defaults["n_holes"]))                                               # Initilize field with default value
        self.start_dia = wx.TextCtrl(self, value=str(defaults["start_dia"]))                                             # Initilize field with default value
        self.step      = wx.TextCtrl(self, value=str(defaults["step"]))                                                  # Initilize field with default value

        self.width.SetToolTip("Width of the test plate (X direction) in mm.")
        self.length.SetToolTip("Length of the test plate (Y direction) in mm.")
        self.thickness.SetToolTip("Thickness of the test plate (Z direction) in mm. All holes are through-all.")
        self.n_holes.SetToolTip("Total number of holes to create. Holes are arranged in a grid, filled left-to-right, top-to-bottom.")
        self.start_dia.SetToolTip("Diameter of the first (smallest) hole in mm.")
        self.step.SetToolTip("Amount to increment each subsequent hole diameter by, in mm. Use 0 for all holes to be the same size.")

        grid.AddMany([
            (wx.StaticText(self, label="Pad Width:"),        ), (self.width,     1, wx.EXPAND), (wx.StaticText(self, label="mm")),
            (wx.StaticText(self, label="Pad Length:"),       ), (self.length,    1, wx.EXPAND), (wx.StaticText(self, label="mm")),
            (wx.StaticText(self, label="Pad Thickness:"),    ), (self.thickness, 1, wx.EXPAND), (wx.StaticText(self, label="mm")),
            (wx.StaticText(self, label="Number of Holes:"),  ), (self.n_holes,   1, wx.EXPAND), (wx.StaticText(self, label="qty")),
            (wx.StaticText(self, label="Starting Diameter:"),), (self.start_dia, 1, wx.EXPAND), (wx.StaticText(self, label="mm")),
            (wx.StaticText(self, label="Diameter Step:"),    ), (self.step,      1, wx.EXPAND), (wx.StaticText(self, label="mm")),
        ])                                                                                                               # Create layout for dialog

        grid.AddGrowableCol(1, 1)                                                                                        # Make field column expand

        vbox.Add(grid, proportion=0, flag=wx.ALL | wx.EXPAND, border=15)

        # Info panel showing computed grid layout
        self.info_text = wx.StaticText(self, label="")                                                                  # Live grid info label
        info_font = wx.Font(9, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        self.info_text.SetFont(info_font)
        vbox.Add(self.info_text, flag=wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, border=15)

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
        vbox.Fit(self)
        self.Center()

        self.Bind(wx.EVT_BUTTON, self.on_help, id=wx.ID_HELP)
        reset_btn.Bind(wx.EVT_BUTTON, self.on_reset)
        clear_btn.Bind(wx.EVT_BUTTON, self.on_clear_settings)

        self.numeric_fields = [
            (self.width,     float),
            (self.length,    float),
            (self.thickness, float),
            (self.n_holes,   int),
            (self.start_dia, float),
            (self.step,      float),
        ]

        for ctrl, _ in self.numeric_fields:
            ctrl.Bind(wx.EVT_TEXT, self.on_validate_live)

        self._update_info()                                                                                              # Show initial grid info

    def _update_info(self):
        try:
            w    = float(self.width.GetValue())
            length = float(self.length.GetValue())
            n    = int(self.n_holes.GetValue())
            sd   = float(self.start_dia.GetValue())
            st   = float(self.step.GetValue())
            if w <= 0 or length <= 0 or n <= 0 or sd <= 0:
                raise ValueError
            cols = math.ceil(math.sqrt(n))
            rows = math.ceil(n / cols)
            cell_w = w / cols
            cell_h = length / rows
            max_d = sd + (n - 1) * st
            fit = min(cell_w, cell_h)
            fit_pct = (max_d / fit * 100) if fit > 0 else 0
            status = "OK" if max_d < fit * 0.85 else ("WARNING: tight fit" if max_d < fit else "ERROR: holes too large")
            info = (f"Grid:       {cols} × {rows}  ({cols * rows} cells, {n} holes)\n"
                    f"Cell size:  {cell_w:.1f} × {cell_h:.1f} mm\n"
                    f"Diameters:  {sd:.2f} mm → {max_d:.2f} mm\n"
                    f"Fit:        {fit_pct:.0f}% of cell  [{status}]")
            self.info_text.SetLabel(info)
        except Exception:
            self.info_text.SetLabel("(enter valid values to see grid preview)")
        self.Layout()
        self.Fit()

    def on_validate_live(self, event):
        ctrl = event.GetEventObject()
        val_string = ctrl.GetValue().strip()
        target_type = next(t for c, t in self.numeric_fields if c == ctrl)

        if self._is_valid(val_string, target_type, ctrl == self.step):                                                  # Step can be zero
            ctrl.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW))
        else:
            ctrl.SetBackgroundColour(wx.Colour(255, 200, 200))                                                          # Soft red for invalid input
        ctrl.Refresh()
        self._update_info()

    def _is_valid(self, value_str, target_type, allow_zero=False):
        try:
            val = target_type(value_str)
            return val >= 0 if allow_zero else val > 0
        except (ValueError, TypeError):
            return False

    def Validate(self):
        for ctrl, target_type in self.numeric_fields:
            allow_zero = (ctrl == self.step)
            val_string = ctrl.GetValue().strip()

            if not val_string:
                self.show_error("A required field is empty.", ctrl)
                return False

            try:
                val = target_type(val_string)
                if not (val >= 0 if allow_zero else val > 0):
                    self.show_error("All values must be greater than zero (Step may be zero).", ctrl)
                    return False
            except (ValueError, TypeError):
                self.show_error("Please enter a valid number.", ctrl)
                return False

        # Check n_holes >= 1
        try:
            n = int(self.n_holes.GetValue())
            if n < 1:
                self.show_error("Number of holes must be at least 1.", self.n_holes)
                return False
        except ValueError:
            return False

        # Check all hole diameters are positive when step is negative
        try:
            n    = int(self.n_holes.GetValue())
            sd   = float(self.start_dia.GetValue())
            st   = float(self.step.GetValue())
            min_d = sd + (n - 1) * st if st < 0 else sd                                                                 # Smallest diameter when step is negative
            if min_d <= 0:
                self.show_error(f"With the current step, some holes would have zero or negative diameter.\n"
                                f"The smallest hole would be {min_d:.3f} mm. Reduce the step or increase start diameter.",
                                self.start_dia)
                return False
        except ValueError:
            return False

        # Grid fit check
        try:
            w  = float(self.width.GetValue())
            length = float(self.length.GetValue())
            n  = int(self.n_holes.GetValue())
            sd = float(self.start_dia.GetValue())
            st = float(self.step.GetValue())

            cols   = math.ceil(math.sqrt(n))
            rows   = math.ceil(n / cols)
            cell_w = w / cols
            cell_h = length / rows
            max_d  = sd + (n - 1) * abs(st) if st >= 0 else sd                                                          # Largest diameter
            fit    = min(cell_w, cell_h)

            if max_d >= fit:
                self.show_error(f"The largest hole (D{max_d:.2f}mm) does not fit in a {cell_w:.1f} × {cell_h:.1f} mm cell.\n"
                                f"Reduce the number of holes, reduce the step, or increase the pad size.",
                                self.n_holes)
                return False

            if max_d > fit * 0.85:
                msg = (f"The largest hole (D{max_d:.2f}mm) uses {max_d / fit * 100:.0f}% of the cell width.\n"
                       f"The wall between adjacent holes may be very thin.\n\n"
                       f"Proceed anyway?")
                if wx.MessageBox(msg, "Design Warning", wx.YES_NO | wx.ICON_WARNING) == wx.NO:
                    return False

        except ValueError:
            return False

        return True

    def show_error(self, message, ctrl):
        wx.MessageBox(message, "Input Error", wx.OK | wx.ICON_ERROR)
        ctrl.SetFocus()
        ctrl.SelectAll()

    def on_clear_settings(self, event):
        if os.path.exists(SETTINGS_FILE):
            try:
                os.remove(SETTINGS_FILE)
                wx.MessageBox("Saved presets have been deleted successfully.", "Settings Cleared", wx.OK | wx.ICON_INFORMATION)
                self.on_reset(None)
            except Exception as e:
                wx.MessageBox(f"Error deleting settings: {str(e)}", "Error", wx.OK | wx.ICON_ERROR)
        else:
            wx.MessageBox("No saved settings file found.", "Information", wx.OK | wx.ICON_INFORMATION)

    def on_reset(self, event):
        d = self.hardcoded_defaults
        success_color = wx.Colour(200, 255, 200)
        default_color = wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW)
        controls = [self.width, self.length, self.thickness, self.n_holes, self.start_dia, self.step]

        self.width.SetValue(d["width"])
        self.length.SetValue(d["length"])
        self.thickness.SetValue(d["thickness"])
        self.n_holes.SetValue(d["n_holes"])
        self.start_dia.SetValue(d["start_dia"])
        self.step.SetValue(d["step"])

        for ctrl in controls:
            ctrl.SetBackgroundColour(success_color)
            ctrl.Refresh()

        wx.CallLater(500, self._clear_feedback_colors, controls, default_color)
        self._update_info()

    def _clear_feedback_colors(self, controls, color):
        for ctrl in controls:
            ctrl.SetBackgroundColour(color)
            ctrl.Refresh()

    def on_help(self, event):
        help_text = (
            "HOLE SIZE TEST PLATE GENERATOR - USER MANUAL\n"
            "==========================================================================\n\n"
            "I. PURPOSE\n"
            "--------------------------------------------------------------------------\n"
            " Creates a flat rectangular pad with a grid of through-holes of incrementally\n"
            " increasing diameter. Use this plate to test drill bit sizes, clearance fits,\n"
            " pin gauges, or any other hole-dependent process.\n\n\n"

            "II. PAD PARAMETERS\n"
            "--------------------------------------------------------------------------\n"
            " • Pad Width:      The X dimension of the plate in mm.  Default: 300 mm.\n\n"
            " • Pad Length:     The Y dimension of the plate in mm.  Default: 300 mm.\n\n"
            " • Pad Thickness:  The Z height of the plate in mm.  Default: 5 mm.\n"
            "                  All holes are through-all (full thickness).\n\n\n"

            "III. HOLE PARAMETERS\n"
            "--------------------------------------------------------------------------\n"
            " • Number of Holes:\n"
            "                  Total hole count. Holes fill a grid left-to-right, top-to-bottom\n"
            "                  in order of increasing diameter. The grid dimensions are\n"
            "                  calculated automatically (nearest square root layout).\n\n"
            " • Starting Diameter:\n"
            "                  Diameter of the first (top-left) hole in mm.\n\n"
            " • Diameter Step:\n"
            "                  Each subsequent hole is larger by this value in mm.\n"
            "                  Step = 0 creates a grid of identical holes.\n"
            "                  A negative step creates holes in decreasing order.\n\n\n"

            "IV. GRID LAYOUT\n"
            "--------------------------------------------------------------------------\n"
            " The number of columns is calculated as: cols = ceil(sqrt(n_holes))\n"
            " The number of rows is:                  rows = ceil(n_holes / cols)\n"
            " Holes are numbered 0, 1, 2 ... left-to-right, top-to-bottom.\n"
            " Hole 0 = starting diameter, each step increments by the step value.\n\n"
            " Example: 9 holes with start=2mm, step=1mm creates:\n"
            "   [D2]  [D3]  [D4]\n"
            "   [D5]  [D6]  [D7]\n"
            "   [D8]  [D9]  [D10]\n\n\n"

            "V. FIT WARNINGS\n"
            "--------------------------------------------------------------------------\n"
            " The grid preview shows whether the largest hole fits in its cell.\n"
            " A warning is shown if the largest hole exceeds 85% of the cell width.\n"
            " An error is shown if any hole diameter meets or exceeds the cell size.\n\n\n"

            "VI. INTERFACE BUTTONS\n"
            "--------------------------------------------------------------------------\n"
            " [OK]           Validates inputs and generates the 3D part in CATIA.\n"
            " [CANCEL]       Exits without making any changes.\n"
            " [RESET DEFAULTS] Restores all factory default values (flashes green).\n"
            " [CLEAR SAVED]  Deletes the saved presets file from AppData.\n"
            " [HELP]         Opens this window.\n\n\n"

            "VII. SETTINGS PERSISTENCE\n"
            "--------------------------------------------------------------------------\n"
            " On a successful run, your parameters are saved to AppData and reloaded\n"
            " automatically the next time the script is run."
        )
        dlg = dialogs.ScrolledMessageDialog(self, help_text, "Help")
        mono_font = wx.Font(10, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        dlg.text.SetFont(mono_font)
        dlg.SetSize((720, 650))
        dlg.CenterOnParent()
        dlg.ShowModal()
        dlg.Destroy()


if __name__ == "__main__":
    SETTINGS_DIR  = os.path.join(os.environ['APPDATA'], 'pycatia_scripts', 'Hole_Size_Test_Plate_Generator')            # User settings directory
    SETTINGS_FILE = os.path.join(SETTINGS_DIR, 'user_presets.json')                                                     # User settings file

    if not os.path.exists(SETTINGS_DIR):                                                                                 # Check if directory does not exist
        os.makedirs(SETTINGS_DIR)                                                                                        # Create directory

    caa = catia()                                                                                                        # Catia application instance
    app = wx.App()

    if type(caa.active_document) is not PartDocument:                                                                    # Check if part document
        msg = ("No active Part document found.\n\n"
               "Please open a CATPart before running this script.")
        wx.MessageBox(msg, "Active Document Error", wx.OK | wx.ICON_ERROR)
        exit()

    part_document: PartDocument = caa.active_document                                                                   # Current open document
    part          = part_document.part                                                                                   # Current part
    bodies        = part.bodies                                                                                          # Get collection of bodies
    shape_factory = part.shape_factory                                                                                   # Part Design workbench
    selectionSet  = caa.active_document.selection                                                                        # Create container for selection

    settings_controller = caa.application.setting_controllers()                                                         # Get catia settings
    part_infa = settings_controller.item("CATMmuPartInfrastructureSettingCtrl")                                         # Get part infrastructure setting

    is_hybrid    = part_infa.com_object.HybridDesignMode                                                                # Get hybrid design mode as boolean
    return_hybrid = False                                                                                                # Set return setting flag to false

    if is_hybrid:                                                                                                        # If hybrid design is enabled
        part_infa.com_object.HybridDesignMode = False                                                                   # Turn off hybrid design
        return_hybrid = True                                                                                             # Set flag to turn on hybrid design again at end

    dlg = DataInputDialog(None, "Hole Size Test Plate Parameters")                                                       # New dialog to get user parameters
    wx.CallAfter(_bring_to_front, dlg)
    if dlg.ShowModal() == wx.ID_OK:
        pad_width   = float(dlg.width.GetValue())                                                                        # Get value from dialog
        pad_length  = float(dlg.length.GetValue())                                                                       # Get value from dialog
        thickness   = float(dlg.thickness.GetValue())                                                                    # Get value from dialog
        n_holes     = int(dlg.n_holes.GetValue())                                                                        # Get value from dialog
        start_dia   = float(dlg.start_dia.GetValue())                                                                    # Get value from dialog
        step        = float(dlg.step.GetValue())                                                                         # Get value from dialog

        current_data = {
            "width":     dlg.width.GetValue(),
            "length":    dlg.length.GetValue(),
            "thickness": dlg.thickness.GetValue(),
            "n_holes":   dlg.n_holes.GetValue(),
            "start_dia": dlg.start_dia.GetValue(),
            "step":      dlg.step.GetValue(),
        }
        with open(SETTINGS_FILE, 'w') as f:                                                                             # Write settings data to json
            json.dump(current_data, f, indent=4)
    else:
        dlg.Destroy()                                                                                                    # Close dialog
        exit()                                                                                                           # Exit script
    dlg.Destroy()                                                                                                        # Close dialog

    # Grid layout calculations
    cols   = math.ceil(math.sqrt(n_holes))                                                                              # Number of columns (nearest square root)
    rows   = math.ceil(n_holes / cols)                                                                                   # Number of rows to accommodate all holes
    cell_w = pad_width  / cols                                                                                           # Width of each grid cell
    cell_h = pad_length / rows                                                                                           # Height of each grid cell

    max_dia  = start_dia + (n_holes - 1) * step                                                                         # Largest hole diameter

    total_steps  = n_holes + 5                                                                                           # Total progress steps

    progress_dlg = wx.ProgressDialog(
        "Generating Test Plate",
        "Initializing ...",
        maximum=total_steps,
        parent=None,
        style=(
            wx.PD_APP_MODAL    |
            wx.PD_AUTO_HIDE    |
            wx.PD_SMOOTH       |
            wx.PD_ELAPSED_TIME |
            wx.PD_REMAINING_TIME
        )
    )

    partbody            = bodies.add()                                                                                   # Add new body
    sketches_part_body  = partbody.sketches                                                                              # Get sketches in part body
    plane_XY            = part.origin_elements.plane_xy                                                                  # Reference to XY plane

    try:
        progress_dlg.Update(1, "Creating body ...")

        # Rename body with all user parameters
        partbody.name = (f"Test Plate | {pad_width}x{pad_length}x{thickness}mm | "
                         f"{n_holes} Holes | D{start_dia:.2f}-D{max_dia:.2f}mm | Step:{step:.2f}mm")
        part.in_work_object = partbody                                                                                   # Make new body the in-work object

        # ---- PAD SKETCH ----
        progress_dlg.Update(2, "Drawing pad profile ...")

        sketch_pad       = sketches_part_body.add(plane_XY)                                                             # Add sketch on XY plane
        sketch_pad.name  = "Pad Profile"                                                                                 # Rename sketch
        ske2D_pad        = sketch_pad.open_edition()                                                                     # Start editing sketch
        constraints_pad  = sketch_pad.constraints                                                                        # Get sketch constraints

        # Rectangle with bottom-left corner at origin
        #   p1 = bottom-left  (0,         0        )
        #   p2 = bottom-right (pad_width, 0        )
        #   p3 = top-right    (pad_width, pad_length)
        #   p4 = top-left     (0,         pad_length)

        line_b = ske2D_pad.create_line(0,         0,          pad_width, 0         )                                    # Bottom edge
        line_r = ske2D_pad.create_line(pad_width, 0,          pad_width, pad_length)                                    # Right edge
        line_t = ske2D_pad.create_line(pad_width, pad_length, 0,         pad_length)                                    # Top edge
        line_l = ske2D_pad.create_line(0,         pad_length, 0,         0         )                                    # Left edge

        line_b.name = "Bottom Edge"                                                                                      # Rename line
        line_r.name = "Right Edge"                                                                                       # Rename line
        line_t.name = "Top Edge"                                                                                         # Rename line
        line_l.name = "Left Edge"                                                                                        # Rename line

        # Create and fix all 8 line endpoints (fully constrains the rectangle)
        for line, pts, name in [
            (line_b, [(0,         0         ), (pad_width, 0         )], ["B_SP", "B_EP"]),
            (line_r, [(pad_width, 0         ), (pad_width, pad_length)], ["R_SP", "R_EP"]),
            (line_t, [(pad_width, pad_length), (0,         pad_length)], ["T_SP", "T_EP"]),
            (line_l, [(0,         pad_length), (0,         0         )], ["L_SP", "L_EP"]),
        ]:
            sp = ske2D_pad.create_point(pts[0][0], pts[0][1])                                                            # Create start point
            sp.name = name[0]                                                                                            # Rename point
            line.start_point = sp                                                                                        # Set as start point
            ep = ske2D_pad.create_point(pts[1][0], pts[1][1])                                                            # Create end point
            ep.name = name[1]                                                                                            # Rename point
            line.end_point = ep                                                                                          # Set as end point
            c_sp = constraints_pad.add_mono_elt_cst(CatConstraintType.catCstTypeReference, sp)                           # Fix start point
            c_sp.name = f"Fixed {name[0]}"                                                                               # Rename constraint
            c_ep = constraints_pad.add_mono_elt_cst(CatConstraintType.catCstTypeReference, ep)                           # Fix end point
            c_ep.name = f"Fixed {name[1]}"                                                                               # Rename constraint

        sketch_pad.close_edition()                                                                                       # Stop editing sketch
        part.update()                                                                                                    # Update part

        # ---- PAD EXTRUDE ----
        progress_dlg.Update(3, "Extruding pad ...")

        pad = shape_factory.add_new_pad(sketch_pad, thickness)                                                           # Create pad feature
        pad.direction_orientation    = CatPrismOrientation.catRegularOrientation                                         # Extrude in +Z direction
        pad.first_limit.limit_mode   = CatLimitMode.catOffsetLimit                                                       # Offset limit (fixed depth)
        pad.first_limit.dimension.value = thickness                                                                      # Set pad thickness
        pad.name = f"Pad {pad_width}x{pad_length}x{thickness}mm"                                                        # Rename pad
        pad.set_profile_element(part.create_reference_from_object(sketch_pad))                                           # Link sketch to pad feature

        part.update()                                                                                                    # Update part

        # ---- HOLES ----
        for i in range(n_holes):
            row     = i // cols                                                                                          # Current grid row (top = 0)
            col     = i % cols                                                                                           # Current grid column (left = 0)
            x_hole  = cell_w * (col + 0.5)                                                                              # Hole centre X (left-to-right from origin)
            y_hole  = pad_length - cell_h * (row + 0.5)                                                                 # Hole centre Y (top-to-bottom from top edge)
            diameter = start_dia + i * step                                                                              # Hole diameter for this index

            progress_dlg.Update(4 + i, f"Creating hole {i + 1}/{n_holes}  (D{diameter:.2f} mm) ...")

            hole = shape_factory.add_new_hole_from_point(                                                                # Create Hole feature from XY plane
                    x_hole, y_hole, 0,
                    plane_XY,
                    thickness)
            hole.type = CatHoleType.catSimpleHole                                                                        # Simple cylindrical hole
            hole.bottom_limit.limit_mode = CatLimitMode.catUpToLastLimit                                                 # Through all
            hole.diameter.value = diameter                                                                               # Set hole diameter
            hole.reverse()                                                                                               # Flip direction to go through the pad (+Z)
            hole.name = f"Hole_{i + 1:02d}_D{diameter:.2f}mm"                                                           # Rename hole feature
            hole.sketch.name = f"Hole_{i + 1:02d}_Sketch"                                                               # Rename the auto-generated sketch

            selectionSet.clear()                                                                                         # Clear selection
            selectionSet.add(hole.sketch)                                                                                # Add hole sketch to selection
            selectionSet.vis_properties.set_show(CatVisPropertyShow.catVisPropertyNoShowAttr)                            # Hide hole sketch to keep tree clean
            selectionSet.clear()                                                                                         # Clear selection

            part.update()                                                                                                # Update part after each hole

        progress_dlg.Update(total_steps - 1, "Finalizing part ...")

        if return_hybrid:                                                                                                 # If hybrid design was turned off
            part_infa.com_object.HybridDesignMode = True                                                                 # Turn hybrid design back on

        progress_dlg.Destroy()

    except Exception as e:                                                                                               # If any exception occurs during geometry creation
        try:
            selectionSet.clear()                                                                                         # Clear selection
            selectionSet.add(partbody)                                                                                   # Select body we created
            selectionSet.delete()                                                                                        # Delete selection
            selectionSet.clear()                                                                                         # Clear selection
        except Exception:
            pass                                                                                                         # If delete fails, continue with cleanup

        if return_hybrid:                                                                                                 # Restore hybrid design if needed
            try:
                part_infa.com_object.HybridDesignMode = True
            except Exception:
                pass

        full_traceback = traceback.format_exc()
        print(full_traceback)

        error_msg = (
            f"Error Summary: {str(e)}\n"
            f"------------------------------------------\n"
            f"Technical Debug Info:\n\n{full_traceback}"
        )

        e_dlg = dialogs.ScrolledMessageDialog(None, error_msg, "Script Error")

        error_icon   = wx.ArtProvider.GetBitmap(wx.ART_ERROR, wx.ART_MESSAGE_BOX)
        icon_bitmap  = wx.StaticBitmap(e_dlg, wx.ID_ANY, error_icon)
        header_text  = wx.StaticText(e_dlg, label="An error occurred during test plate generation:")
        header_font  = wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        header_text.SetFont(header_font)

        main_sizer   = e_dlg.GetSizer()
        header_sizer = wx.BoxSizer(wx.HORIZONTAL)
        header_sizer.Add(icon_bitmap, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 15)
        header_sizer.Add(header_text, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        main_sizer.Prepend(header_sizer, 0, wx.EXPAND)

        mono_font = wx.Font(9, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        e_dlg.text.SetFont(mono_font)
        e_dlg.SetSize((600, 400))
        e_dlg.CenterOnParent()
        wx.CallAfter(_bring_to_front, e_dlg)
        e_dlg.ShowModal()
        e_dlg.Destroy()

        if progress_dlg:
            progress_dlg.Destroy()

        try:
            part.update()                                                                                                # Attempt to clean up partial state
        except Exception:
            pass

        exit()                                                                                                           # Exit script
