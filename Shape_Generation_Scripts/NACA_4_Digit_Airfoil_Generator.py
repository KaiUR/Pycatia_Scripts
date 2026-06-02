'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    NACA_4_Digit_Airfoil_Generator.py
    Version:        1.1
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Generate a NACA 4-digit airfoil profile as points and a closed spline.
    Author:         Kai-Uwe Rathjen
    Date:           22.05.26
    Description:    Generates a NACA 4-digit series airfoil (e.g. 0010, 2412) in the active CATPart.
                    The user specifies the NACA designation, chord length, point resolution, and output
                    plane. A geometric set is created containing a Points sub-set and a closed GSD
                    spline through all surface points. Cosine spacing is used for smooth LE/TE capture.
                    User parameters are persisted between runs.
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
import math
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


def naca4_points(m, p, t, n_pts):
    """Return (upper, lower) lists of (x, y) normalised to chord=1 using cosine spacing."""
    betas  = [math.pi * i / (n_pts - 1) for i in range(n_pts)]
    xs     = [(1 - math.cos(b)) / 2 for b in betas]           # cosine spacing, 0→1

    upper, lower = [], []
    for x in xs:
        # Thickness distribution (NACA standard, open trailing edge)
        y_t = (t / 0.2) * (
            0.2969 * math.sqrt(x)
            - 0.1260 * x
            - 0.3516 * x ** 2
            + 0.2843 * x ** 3
            - 0.1015 * x ** 4
        )
        # Mean camber line and gradient
        if m == 0.0 or p == 0.0:
            y_c, dyc_dx = 0.0, 0.0
        elif x < p:
            y_c     = (m / p ** 2) * (2 * p * x - x ** 2)
            dyc_dx  = (2 * m / p ** 2) * (p - x)
        else:
            y_c     = (m / (1 - p) ** 2) * ((1 - 2 * p) + 2 * p * x - x ** 2)
            dyc_dx  = (2 * m / (1 - p) ** 2) * (p - x)

        theta = math.atan(dyc_dx)
        upper.append((x - y_t * math.sin(theta),  y_c + y_t * math.cos(theta)))
        lower.append((x + y_t * math.sin(theta),  y_c - y_t * math.cos(theta)))

    return upper, lower


def to_3d(xu, yu, chord, plane_idx):
    """Scale and map normalised (xu, yu) to 3-D coordinates for the chosen plane."""
    x = xu * chord
    y = yu * chord
    if plane_idx == 0:   # XY
        return x, y, 0.0
    elif plane_idx == 1: # XZ
        return x, 0.0, y
    else:                # YZ
        return 0.0, x, y


class NacaDialog(wx.Dialog):
    HARDCODED_DEFAULTS = {
        "naca":  "0010",
        "chord": "1000.0",
        "n_pts": "50",
        "plane": 0,
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

        super().__init__(parent, title="NACA 4-Digit Airfoil Generator",
                         style=wx.DEFAULT_DIALOG_STYLE | wx.STAY_ON_TOP)

        vbox = wx.BoxSizer(wx.VERTICAL)
        grid = wx.FlexGridSizer(4, 3, 10, 10)
        grid.AddGrowableCol(1, 1)

        self.naca_ctrl  = wx.TextCtrl(self, value=str(defaults["naca"]))
        self.chord_ctrl = wx.TextCtrl(self, value=str(defaults["chord"]))
        self.npts_ctrl  = wx.TextCtrl(self, value=str(defaults["n_pts"]))
        self.plane_ctrl = wx.RadioBox(self, label="Output Plane",
                                      choices=self.PLANES,
                                      majorDimension=1, style=wx.RA_SPECIFY_COLS)
        self.plane_ctrl.SetSelection(int(defaults["plane"]))

        self.naca_ctrl.SetToolTip("4-digit NACA code, e.g. 0010 or 2412.")
        self.chord_ctrl.SetToolTip("Chord length in mm. The normalised profile is scaled to this length.")
        self.npts_ctrl.SetToolTip("Number of sample points per surface (upper and lower). Minimum 5.")

        grid.AddMany([
            (wx.StaticText(self, label="NACA code:")),    (self.naca_ctrl,  1, wx.EXPAND), (wx.StaticText(self, label="")),
            (wx.StaticText(self, label="Chord:")),         (self.chord_ctrl, 1, wx.EXPAND), (wx.StaticText(self, label="mm")),
            (wx.StaticText(self, label="Points / side:")), (self.npts_ctrl,  1, wx.EXPAND), (wx.StaticText(self, label="pts")),
            (wx.StaticText(self, label="Plane:")),         (self.plane_ctrl, 0),            (wx.StaticText(self, label="")),
        ])
        vbox.Add(grid, proportion=0, flag=wx.ALL | wx.EXPAND, border=15)

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

        reset_btn.Bind(wx.EVT_BUTTON, self.on_reset)
        clear_btn.Bind(wx.EVT_BUTTON, self.on_clear)
        self.Bind(wx.EVT_BUTTON, self.on_help, id=wx.ID_HELP)

    def on_reset(self, event):
        d = self.HARDCODED_DEFAULTS
        self.naca_ctrl.SetValue(d["naca"])
        self.chord_ctrl.SetValue(d["chord"])
        self.npts_ctrl.SetValue(d["n_pts"])
        self.plane_ctrl.SetSelection(int(d["plane"]))

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
            "NACA 4-DIGIT AIRFOIL GENERATOR — USER MANUAL\n"
            "==========================================================================\n\n"
            "NACA CODE\n"
            "----------\n"
            " The 4-digit NACA designation has the form MPXX where:\n"
            "   M  = Maximum camber as a percentage of chord (1st digit).\n"
            "        0 = symmetric profile.\n"
            "   P  = Chordwise position of max camber in tenths of chord (2nd digit).\n"
            "        0 = symmetric profile.\n"
            "   XX = Maximum thickness as a percentage of chord (last two digits).\n\n"
            " Examples:\n"
            "   0010 → Symmetric, 10% thick (classic NACA 0010)\n"
            "   2412 → 2% camber at 40% chord, 12% thick (NACA 2412)\n"
            "   4415 → 4% camber at 40% chord, 15% thick (NACA 4415)\n\n"
            "CHORD\n"
            "------\n"
            " The chord length in mm. The normalised profile (0–1) is scaled to this\n"
            " dimension. The leading edge is placed at the origin; the trailing edge\n"
            " lies at (chord, 0, 0) for XY and XZ planes.\n\n"
            "POINTS PER SIDE\n"
            "----------------\n"
            " Number of sample points on each surface (upper and lower).\n"
            " Cosine spacing clusters points near the leading and trailing edges\n"
            " where curvature is highest. 50 is a good default; use 20–30 for\n"
            " lightweight models and 100+ for high-fidelity analysis work.\n\n"
            "OUTPUT\n"
            "-------\n"
            " A geometric set is created named 'NACA_XXXX_Chord_YYYmm' containing:\n"
            "   • A 'Points' sub-set with all surface points (Upper_001..N, Lower_001..M).\n"
            "   • A closed GSD spline ('Airfoil_Spline') through all points.\n"
            "     The spline runs LE → TE along the upper surface, then TE → LE\n"
            "     along the lower surface, forming a single closed loop.\n"
        )
        dlg = dialogs.ScrolledMessageDialog(self, help_text, "Help")
        mono = wx.Font(10, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        dlg.text.SetFont(mono)
        dlg.SetSize((650, 560))
        dlg.CenterOnParent()
        dlg.ShowModal()
        dlg.Destroy()

    def Validate(self):
        code = self.naca_ctrl.GetValue().strip()
        if len(code) != 4 or not code.isdigit():
            wx.MessageBox("NACA code must be exactly 4 digits, e.g. 0010 or 2412.",
                          "Input Error", wx.OK | wx.ICON_ERROR)
            self.naca_ctrl.SetFocus()
            return False

        for ctrl, name, t, min_val in [
            (self.chord_ctrl, "Chord",          float, 0.0),
            (self.npts_ctrl,  "Points per side", int,   4),
        ]:
            try:
                val = t(ctrl.GetValue().strip())
                if val <= min_val:
                    wx.MessageBox(f"{name} must be greater than {min_val}.",
                                  "Input Error", wx.OK | wx.ICON_ERROR)
                    ctrl.SetFocus()
                    return False
            except ValueError:
                wx.MessageBox(f"{name} must be a valid number.",
                              "Input Error", wx.OK | wx.ICON_ERROR)
                ctrl.SetFocus()
                return False

        return True

    def get_values(self):
        return {
            "naca":  self.naca_ctrl.GetValue().strip(),
            "chord": float(self.chord_ctrl.GetValue()),
            "n_pts": int(self.npts_ctrl.GetValue()),
            "plane": self.plane_ctrl.GetSelection(),
        }


if __name__ == "__main__":
    SETTINGS_DIR  = os.path.join(os.environ['APPDATA'], 'pycatia_scripts', 'NACA_4_Digit_Airfoil_Generator')
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

    dlg = NacaDialog(None)
    wx.CallAfter(_bring_to_front, dlg)

    if dlg.ShowModal() != wx.ID_OK:
        dlg.Destroy()
        exit()

    params = dlg.get_values()
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(params, f, indent=4)
    except Exception:
        pass
    dlg.Destroy()

    naca_code = params["naca"]
    chord     = params["chord"]
    n_pts     = params["n_pts"]
    plane_idx = params["plane"]
    planes    = ["XY", "XZ", "YZ"]

    m = int(naca_code[0]) / 100.0           # max camber
    p = int(naca_code[1]) / 10.0            # camber position
    t = int(naca_code[2:]) / 100.0          # thickness

    upper_norm, lower_norm = naca4_points(m, p, t, n_pts)

    progress = wx.ProgressDialog(
        "Generating Airfoil", "Initialising...", maximum=5, parent=None,
        style=(wx.PD_APP_MODAL | wx.PD_AUTO_HIDE | wx.PD_SMOOTH |
               wx.PD_ELAPSED_TIME | wx.PD_REMAINING_TIME)
    )

    try:
        progress.Update(1, "Creating geometric sets...")

        geo_set = part.hybrid_bodies.add()
        geo_set.name = f"NACA_{naca_code}_Chord_{int(chord)}mm"

        pts_set = geo_set.hybrid_bodies.add()
        pts_set.name = "Points"

        progress.Update(2, "Creating upper surface points...")

        spline_refs = []

        part.in_work_object = pts_set
        for i, (xu, yu) in enumerate(upper_norm):
            x3, y3, z3 = to_3d(xu, yu, chord, plane_idx)
            pt = hsf.add_new_point_coord(x3, y3, z3)
            pt.name = f"Upper_{i + 1:03d}"
            pts_set.append_hybrid_shape(pt)
            part.update()
            spline_refs.append(part.create_reference_from_object(pt))

        progress.Update(3, "Creating lower surface points...")

        # Lower surface runs TE → LE; skip the shared TE (index -1) and LE (index 0)
        # so the closed spline does not duplicate those junction points.
        for i, (xl, yl) in enumerate(reversed(lower_norm[1:-1])):
            x3, y3, z3 = to_3d(xl, yl, chord, plane_idx)
            pt = hsf.add_new_point_coord(x3, y3, z3)
            pt.name = f"Lower_{i + 1:03d}"
            pts_set.append_hybrid_shape(pt)
            part.update()
            spline_refs.append(part.create_reference_from_object(pt))

        progress.Update(4, "Creating closed spline...")

        part.in_work_object = geo_set
        spline = hsf.add_new_spline()
        for ref in spline_refs:
            spline.add_point(ref)
        spline.set_closing(1)
        spline.name = "Airfoil_Spline"
        geo_set.append_hybrid_shape(spline)
        part.update()

        progress.Update(5, "Done.")

        print(f"\n NACA {naca_code} airfoil generated successfully.")
        print(f"   Chord:           {chord} mm")
        print(f"   Points per side: {n_pts}  ({2 * n_pts - 2} total spline points)")
        print(f"   Plane:           {planes[plane_idx]}")
        print("\n Completed\n\n")

    except Exception as e:
        full_traceback = traceback.format_exc()
        print(full_traceback)
        progress.Update(5, "Error.")
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
