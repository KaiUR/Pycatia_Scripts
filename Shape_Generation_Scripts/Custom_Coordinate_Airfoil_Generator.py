'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Custom_Coordinate_Airfoil_Generator.py
    Version:        1.1
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Generate a spline from user-supplied X Y coordinates in the active CATPart.
    Author:         Kai-Uwe Rathjen
    Date:           22.05.26
    Description:    Creates a GSD point set and closed spline from arbitrary X Y (or X Y Z)
                    coordinates supplied either by loading a .dat / .csv file or by pasting
                    values directly into the dialog text area. Supports Selig .dat format and
                    whitespace- or comma-separated CSV. An optional chord scale overrides the
                    raw coordinate range. The output plane (XY, XZ, YZ) is user-selectable.
                    A geometric set is created containing a Points sub-set and the spline.
                    Plane and scale settings are persisted between runs.
    dependencies = [
                    "pycatia",
                    "wxPython",
                    ]
    requirements:   Python >= 3.10
                    pycatia
                    wxPython
                    Catia V5 running with an open part document.
    -----------------------------------------------------------------------------------------------------------------------

    Change:         02.06.26 1.1: Error handler updated to use ScrolledMessageDialog pattern.

    -----------------------------------------------------------------------------------------------------------------------
'''

# Imports
from pycatia import catia
from pycatia.mec_mod_interfaces.part_document import PartDocument
import wx
import wx.lib.dialogs as dialogs
import os
import json
import traceback
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


def parse_coordinates(text):
    """
    Parse whitespace- or comma-separated coordinate lines.
    Returns a list of [x, y] or [x, y, z] float lists.
    Lines beginning with '#' and non-numeric header lines are silently skipped.
    """
    coords = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        parts = line.replace(',', ' ').split()
        if len(parts) < 2:
            continue
        try:
            row = [float(p) for p in parts[:3]]
            if len(row) >= 2:
                coords.append(row)
        except ValueError:
            continue   # skip non-numeric lines (e.g. Selig .dat airfoil name)
    return coords


def to_3d(coords_row, scale, plane_idx):
    """
    Map a parsed coordinate row to 3-D (x, y, z) applying optional chord scale.
    If the row has 3 values the plane selection is ignored and coords are used as-is.
    """
    if len(coords_row) >= 3:
        # Already 3-D — use directly, scale still applies
        sx = coords_row[0] * scale if scale > 0 else coords_row[0]
        sy = coords_row[1] * scale if scale > 0 else coords_row[1]
        sz = coords_row[2] * scale if scale > 0 else coords_row[2]
        return sx, sy, sz

    xu = coords_row[0]
    yu = coords_row[1]
    if scale > 0:
        xu *= scale
        yu *= scale

    if plane_idx == 0:   # XY
        return xu, yu, 0.0
    elif plane_idx == 1: # XZ
        return xu, 0.0, yu
    else:                # YZ
        return 0.0, xu, yu


class CoordDialog(wx.Dialog):
    HARDCODED_DEFAULTS = {
        "mode":       0,      # 0 = File, 1 = Text
        "scale":      "0.0",  # 0 = use raw coordinates
        "close":      True,
        "plane":      0,      # 0=XY, 1=XZ, 2=YZ
        "last_dir":   "",
    }
    PLANES = ["XY", "XZ", "YZ"]

    def __init__(self, parent):
        defaults = self.HARDCODED_DEFAULTS.copy()
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r') as f:
                    defaults.update(json.load(f))
            except Exception:
                pass

        super().__init__(parent, title="Custom Coordinate Airfoil Generator",
                         style=wx.DEFAULT_DIALOG_STYLE | wx.STAY_ON_TOP)

        vbox = wx.BoxSizer(wx.VERTICAL)

        # ── Input mode radio ──────────────────────────────────────────────────
        mode_box  = wx.StaticBox(self, label="Input Mode")
        mode_sizer = wx.StaticBoxSizer(mode_box, wx.HORIZONTAL)
        self.mode_file = wx.RadioButton(self, label="File (.dat / .csv)", style=wx.RB_GROUP)
        self.mode_text = wx.RadioButton(self, label="Paste text")
        self.mode_file.SetValue(int(defaults["mode"]) == 0)
        self.mode_text.SetValue(int(defaults["mode"]) == 1)
        mode_sizer.Add(self.mode_file, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        mode_sizer.Add(self.mode_text, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        vbox.Add(mode_sizer, 0, wx.ALL | wx.EXPAND, 8)

        # ── File picker ───────────────────────────────────────────────────────
        file_box   = wx.StaticBox(self, label="File")
        file_sizer = wx.StaticBoxSizer(file_box, wx.HORIZONTAL)
        self.file_ctrl   = wx.TextCtrl(self, value="")
        self.browse_btn  = wx.Button(self, label="Browse...")
        file_sizer.Add(self.file_ctrl,  1, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        file_sizer.Add(self.browse_btn, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        vbox.Add(file_sizer, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 8)

        # ── Text area ─────────────────────────────────────────────────────────
        text_box   = wx.StaticBox(self, label="Paste Coordinates  (X  Y  or  X  Y  Z  — one point per line)")
        text_sizer = wx.StaticBoxSizer(text_box, wx.VERTICAL)
        self.text_ctrl = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_DONTWRAP,
                                     size=(-1, 140))
        self.text_ctrl.SetFont(wx.Font(9, wx.FONTFAMILY_TELETYPE,
                                       wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        text_sizer.Add(self.text_ctrl, 1, wx.ALL | wx.EXPAND, 5)
        vbox.Add(text_sizer, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 8)

        # ── Options grid ──────────────────────────────────────────────────────
        opt_box    = wx.StaticBox(self, label="Options")
        opt_sizer  = wx.StaticBoxSizer(opt_box, wx.VERTICAL)
        opt_grid   = wx.FlexGridSizer(3, 3, 8, 10)
        opt_grid.AddGrowableCol(1, 1)

        self.scale_ctrl = wx.TextCtrl(self, value=str(defaults["scale"]))
        self.close_ctrl = wx.CheckBox(self, label="Close spline")
        self.close_ctrl.SetValue(bool(defaults["close"]))
        self.plane_ctrl = wx.RadioBox(self, label="Plane (2-D input only)",
                                      choices=self.PLANES,
                                      majorDimension=1, style=wx.RA_SPECIFY_COLS)
        self.plane_ctrl.SetSelection(int(defaults["plane"]))

        self.scale_ctrl.SetToolTip(
            "Chord scale in mm. The input coordinates are normalised to their X-range\n"
            "and scaled so the chord equals this value.\n"
            "Set to 0 to use the raw coordinate values without scaling."
        )
        self.close_ctrl.SetToolTip(
            "Connect the last point back to the first to form a closed spline.\n"
            "Enable for complete airfoil loops (Selig .dat format). Disable for\n"
            "open curves or when upper/lower surfaces are supplied separately."
        )
        self.plane_ctrl.SetToolTip("Plane used to place 2-D coordinates. Ignored when X Y Z input is provided.")

        opt_grid.AddMany([
            (wx.StaticText(self, label="Chord scale:")), (self.scale_ctrl, 1, wx.EXPAND), (wx.StaticText(self, label="mm  (0 = raw)")),
            (wx.StaticText(self, label="Spline:")),      (self.close_ctrl, 0),            (wx.StaticText(self, label="")),
            (wx.StaticText(self, label="Plane:")),       (self.plane_ctrl, 0),            (wx.StaticText(self, label="")),
        ])
        opt_sizer.Add(opt_grid, 0, wx.ALL | wx.EXPAND, 8)
        vbox.Add(opt_sizer, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 8)

        # ── Buttons ───────────────────────────────────────────────────────────
        btn_row   = wx.BoxSizer(wx.HORIZONTAL)
        reset_btn = wx.Button(self, label="Reset Defaults")
        clear_btn = wx.Button(self, label="Clear Saved")
        std_btns  = self.CreateButtonSizer(wx.OK | wx.CANCEL | wx.HELP)
        btn_row.Add(reset_btn, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        btn_row.Add(clear_btn, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        if std_btns:
            btn_row.Add(std_btns, 0, wx.ALL, 5)
        vbox.Add(btn_row, flag=wx.ALIGN_CENTER | wx.BOTTOM, border=10)

        self.SetSizer(vbox)
        vbox.Fit(self)
        self.Center()
        self._last_dir = str(defaults.get("last_dir", ""))
        self._update_mode()

        self.mode_file.Bind(wx.EVT_RADIOBUTTON, self.on_mode_change)
        self.mode_text.Bind(wx.EVT_RADIOBUTTON, self.on_mode_change)
        self.browse_btn.Bind(wx.EVT_BUTTON, self.on_browse)
        reset_btn.Bind(wx.EVT_BUTTON, self.on_reset)
        clear_btn.Bind(wx.EVT_BUTTON, self.on_clear)
        self.Bind(wx.EVT_BUTTON, self.on_help, id=wx.ID_HELP)

    def _update_mode(self):
        file_mode = self.mode_file.GetValue()
        self.file_ctrl.Enable(file_mode)
        self.browse_btn.Enable(file_mode)
        self.text_ctrl.Enable(not file_mode)

    def on_mode_change(self, event):
        self._update_mode()

    def on_browse(self, event):
        dlg = wx.FileDialog(
            self,
            message="Open coordinate file",
            defaultDir=self._last_dir or os.path.expanduser("~"),
            wildcard="Coordinate files (*.dat;*.csv;*.txt)|*.dat;*.csv;*.txt|All files (*.*)|*.*",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        )
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            self.file_ctrl.SetValue(path)
            self._last_dir = os.path.dirname(path)
        dlg.Destroy()

    def on_reset(self, event):
        d = self.HARDCODED_DEFAULTS
        self.mode_file.SetValue(int(d["mode"]) == 0)
        self.mode_text.SetValue(int(d["mode"]) == 1)
        self.scale_ctrl.SetValue(d["scale"])
        self.close_ctrl.SetValue(bool(d["close"]))
        self.plane_ctrl.SetSelection(int(d["plane"]))
        self._update_mode()

    def on_clear(self, event):
        if os.path.exists(SETTINGS_FILE):
            try:
                os.remove(SETTINGS_FILE)
                wx.MessageBox("Saved settings cleared.", "Done", wx.OK | wx.ICON_INFORMATION)
                self.on_reset(None)
            except Exception as e:
                wx.MessageBox(f"Could not delete settings: {e}", "Error", wx.OK | wx.ICON_ERROR)
        else:
            wx.MessageBox("No saved settings found.", "Information", wx.OK | wx.ICON_INFORMATION)

    def on_help(self, event):
        help_text = (
            "CUSTOM COORDINATE AIRFOIL GENERATOR — USER MANUAL\n"
            "==========================================================================\n\n"
            "INPUT MODE\n"
            "-----------\n"
            " File:  Browse to a .dat, .csv, or .txt file containing coordinates.\n"
            "        Selig .dat format is supported — the airfoil name line at the top\n"
            "        is automatically skipped as it cannot be parsed as numbers.\n"
            "        Lines beginning with '#' are treated as comments and skipped.\n\n"
            " Paste: Type or paste coordinate pairs directly into the text area.\n"
            "        Each line should contain one point: X Y  or  X Y Z.\n"
            "        Columns may be separated by spaces, tabs, or commas.\n\n"
            "CHORD SCALE\n"
            "------------\n"
            " When set to a positive value (mm), the script normalises the input\n"
            " coordinates to their X-range (max X − min X = 1) and then scales the\n"
            " result so the chord equals the specified length.\n"
            " Set to 0 to skip scaling and use the raw coordinate values.\n\n"
            "CLOSE SPLINE\n"
            "-------------\n"
            " Connects the last point back to the first point forming a closed loop.\n"
            " Enable for complete airfoil profiles (e.g. Selig .dat files that list\n"
            " coordinates around the full contour from TE → upper → LE → lower → TE).\n"
            " Disable for open curves or single-surface data.\n\n"
            "PLANE (2-D input only)\n"
            "-----------------------\n"
            " Determines which 3-D plane the 2-D (X Y) coordinates are placed on:\n"
            "   XY → points at (X, Y, 0)\n"
            "   XZ → points at (X, 0, Y)\n"
            "   YZ → points at (0, X, Y)\n"
            " If 3-column (X Y Z) input is supplied this setting is ignored.\n\n"
            "OUTPUT\n"
            "-------\n"
            " A geometric set is created named 'Custom_Airfoil' containing:\n"
            "   • A 'Points' sub-set with all input points (Point_001, Point_002 ...).\n"
            "   • A GSD spline ('Airfoil_Spline') through all points.\n"
        )
        dlg = dialogs.ScrolledMessageDialog(self, help_text, "Help")
        mono = wx.Font(10, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        dlg.text.SetFont(mono)
        dlg.SetSize((660, 580))
        dlg.CenterOnParent()
        dlg.ShowModal()
        dlg.Destroy()

    def Validate(self):
        # Validate scale
        try:
            scale = float(self.scale_ctrl.GetValue().strip())
            if scale < 0:
                wx.MessageBox("Chord scale must be 0 or a positive number.",
                              "Input Error", wx.OK | wx.ICON_ERROR)
                self.scale_ctrl.SetFocus()
                return False
        except ValueError:
            wx.MessageBox("Chord scale must be a valid number.",
                          "Input Error", wx.OK | wx.ICON_ERROR)
            self.scale_ctrl.SetFocus()
            return False

        # Validate and parse coordinates
        if self.mode_file.GetValue():
            path = self.file_ctrl.GetValue().strip()
            if not path:
                wx.MessageBox("Please select a coordinate file or switch to Paste Text mode.",
                              "Input Error", wx.OK | wx.ICON_ERROR)
                return False
            if not os.path.isfile(path):
                wx.MessageBox(f"File not found:\n{path}", "Input Error", wx.OK | wx.ICON_ERROR)
                return False
            try:
                with open(path, 'r') as fh:
                    text = fh.read()
            except Exception as e:
                wx.MessageBox(f"Could not read file:\n{e}", "Input Error", wx.OK | wx.ICON_ERROR)
                return False
        else:
            text = self.text_ctrl.GetValue()

        coords = parse_coordinates(text)
        if len(coords) < 3:
            wx.MessageBox(
                "At least 3 valid coordinate pairs are required to create a spline.\n\n"
                "Check that your data has one X Y point per line and that any header\n"
                "lines use non-numeric text (they will be skipped automatically).",
                "Input Error", wx.OK | wx.ICON_ERROR
            )
            return False

        self._parsed_coords = coords
        return True

    def get_values(self):
        return {
            "mode":   0 if self.mode_file.GetValue() else 1,
            "coords": self._parsed_coords,
            "scale":  float(self.scale_ctrl.GetValue()),
            "close":  self.close_ctrl.IsChecked(),
            "plane":  self.plane_ctrl.GetSelection(),
            "last_dir": self._last_dir,
        }


if __name__ == "__main__":
    SETTINGS_DIR  = os.path.join(os.environ['APPDATA'], 'pycatia_scripts', 'Custom_Coordinate_Airfoil_Generator')
    SETTINGS_FILE = os.path.join(SETTINGS_DIR, 'user_presets.json')
    if not os.path.exists(SETTINGS_DIR):
        os.makedirs(SETTINGS_DIR)

    caa = catia()
    app = wx.App()

    if type(caa.active_document) is not PartDocument:
        wx.MessageBox("No active Part document found.\nPlease open a CATPart before running this script.",
                      "Active Document Error", wx.OK | wx.ICON_ERROR)
        exit()

    part_document: PartDocument = caa.active_document
    part = part_document.part
    hsf  = part.hybrid_shape_factory

    dlg = CoordDialog(None)
    wx.CallAfter(_bring_to_front, dlg)

    if dlg.ShowModal() != wx.ID_OK:
        dlg.Destroy()
        exit()

    params = dlg.get_values()

    # Persist settings (not the raw coordinate data)
    try:
        save_data = {k: v for k, v in params.items() if k != "coords"}
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(save_data, f, indent=4)
    except Exception:
        pass
    dlg.Destroy()

    raw_coords = params["coords"]
    scale      = params["scale"]
    close      = params["close"]
    plane_idx  = params["plane"]
    planes     = ["XY", "XZ", "YZ"]
    is_3d      = any(len(c) >= 3 for c in raw_coords)

    # Normalise X range when scale > 0 and input is 2-D
    if scale > 0 and not is_3d:
        xs = [c[0] for c in raw_coords]
        x_min, x_range = min(xs), max(xs) - min(xs)
        if x_range > 0:
            raw_coords = [
                [(c[0] - x_min) / x_range, c[1] / x_range] for c in raw_coords
            ]

    progress = wx.ProgressDialog(
        "Generating Airfoil", "Initialising...", maximum=4, parent=None,
        style=(wx.PD_APP_MODAL | wx.PD_AUTO_HIDE | wx.PD_SMOOTH |
               wx.PD_ELAPSED_TIME | wx.PD_REMAINING_TIME)
    )

    try:
        progress.Update(1, "Creating geometric sets...")

        geo_set = part.hybrid_bodies.add()
        geo_set.name = "Custom_Airfoil"

        pts_set = geo_set.hybrid_bodies.add()
        pts_set.name = "Points"

        progress.Update(2, "Creating points...")

        spline_refs = []
        part.in_work_object = pts_set

        for i, row in enumerate(raw_coords):
            x3, y3, z3 = to_3d(row, scale if (scale > 0 and not is_3d) else 0, plane_idx)
            pt = hsf.add_new_point_coord(x3, y3, z3)
            pt.name = f"Point_{i + 1:03d}"
            pts_set.append_hybrid_shape(pt)
            part.update()
            spline_refs.append(part.create_reference_from_object(pt))

        progress.Update(3, "Creating spline...")

        part.in_work_object = geo_set
        spline = hsf.add_new_spline()
        for ref in spline_refs:
            spline.add_point(ref)
        spline.set_closing(1 if close else 0)
        spline.name = "Airfoil_Spline"
        geo_set.append_hybrid_shape(spline)
        part.update()

        progress.Update(4, "Done.")

        print(f"\n Custom airfoil generated successfully.")
        print(f"   Points:     {len(raw_coords)}")
        print(f"   Spline:     {'Closed' if close else 'Open'}")
        if scale > 0 and not is_3d:
            print(f"   Chord scale: {scale} mm")
        else:
            print(f"   Scale:      Raw coordinates (no scaling)")
        if not is_3d:
            print(f"   Plane:      {planes[plane_idx]}")
        else:
            print(f"   Input:      3-D coordinates (plane selection ignored)")
        print(f"\n Completed\n\n")

    except Exception as e:
        full_traceback = traceback.format_exc()
        print(full_traceback)
        progress.Update(4, "Error.")
        error_msg = (
            f"Error Summary: {str(e)}\n"
            f"------------------------------------------\n"
            f"Technical Debug Info:\n\n{full_traceback}"
        )
        e_dlg = dialogs.ScrolledMessageDialog(None, error_msg, "Script Error")
        error_icon  = wx.ArtProvider.GetBitmap(wx.ART_ERROR, wx.ART_MESSAGE_BOX)
        icon_bitmap = wx.StaticBitmap(e_dlg, wx.ID_ANY, error_icon)
        header_text = wx.StaticText(e_dlg, label="An error occurred during airfoil generation:")
        header_font = wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
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
    finally:
        progress.Destroy()
