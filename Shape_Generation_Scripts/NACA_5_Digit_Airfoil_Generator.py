'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    NACA_5_Digit_Airfoil_Generator.py
    Version:        1.0
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Generate a NACA 5-digit airfoil profile as points and a closed spline.
    Author:         Kai-Uwe Rathjen
    Date:           31.05.26
    Description:    Generates a NACA 5-digit series airfoil (e.g. 23012, 23015) in the active
                    CATPart. The user specifies the NACA designation, chord length, point resolution,
                    and output plane. Supports the five standard non-reflexed (Q=0) camber line
                    configurations (P = 1–5). Cosine spacing is used for smooth LE/TE capture.
                    A geometric set is created containing a Points sub-set and a closed GSD spline.
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

    Change:

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
import ctypes

# Tabulated m and k1 values for NACA 5-digit standard non-reflexed (Q=0) camber line.
# Key = P digit (1–5). m = chordwise position of max camber; k1 = camber scaling factor at L=2.
_NACA5_TABLE = {
    1: (0.0580, 361.4),
    2: (0.1260,  51.64),
    3: (0.2025,  15.957),
    4: (0.2900,   6.643),
    5: (0.3910,   3.230),
}


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


def naca5_points(l_digit, p_digit, t_frac, n_pts):
    """
    Return (upper, lower) lists of (x, y) normalised to chord=1 using cosine spacing.
    l_digit: first NACA 5 digit (1–9), design CL = l_digit × 3/20
    p_digit: second NACA 5 digit (1–5), max camber position
    t_frac:  thickness fraction (e.g. 0.12 for 12%)
    n_pts:   number of sample points per surface
    """
    m, k1_at_l2 = _NACA5_TABLE[p_digit]
    k1 = k1_at_l2 * (l_digit / 2.0)           # Scale k1 proportionally for l_digit ≠ 2

    betas  = [math.pi * i / (n_pts - 1) for i in range(n_pts)]
    xs     = [(1 - math.cos(b)) / 2 for b in betas]

    upper, lower = [], []
    for x in xs:
        # Thickness distribution (same formula as NACA 4-digit)
        y_t = (t_frac / 0.2) * (
            0.2969 * math.sqrt(x)
            - 0.1260 * x
            - 0.3516 * x ** 2
            + 0.2843 * x ** 3
            - 0.1015 * x ** 4
        )
        # NACA 5-digit standard (Q=0) camber line
        if x <= m:
            y_c     = (k1 / 6.0) * (x ** 3 - 3 * m * x ** 2 + m ** 2 * (3 - m) * x)
            dyc_dx  = (k1 / 6.0) * (3 * x ** 2 - 6 * m * x + m ** 2 * (3 - m))
        else:
            y_c     = (k1 * m ** 3 / 6.0) * (1 - x)
            dyc_dx  = -(k1 * m ** 3 / 6.0)

        theta = math.atan(dyc_dx)
        upper.append((x - y_t * math.sin(theta),  y_c + y_t * math.cos(theta)))
        lower.append((x + y_t * math.sin(theta),  y_c - y_t * math.cos(theta)))

    return upper, lower


def to_3d(xu, yu, chord, plane_idx):
    """Scale and map normalised (xu, yu) to 3D coordinates for the chosen plane."""
    x = xu * chord
    y = yu * chord
    if plane_idx == 0:
        return x, y, 0.0
    elif plane_idx == 1:
        return x, 0.0, y
    else:
        return 0.0, x, y


class Naca5Dialog(wx.Dialog):
    HARDCODED_DEFAULTS = {
        "naca":  "23012",
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

        super().__init__(parent, title="NACA 5-Digit Airfoil Generator",
                         style=wx.DEFAULT_DIALOG_STYLE | wx.STAY_ON_TOP)

        vbox = wx.BoxSizer(wx.VERTICAL)
        grid = wx.FlexGridSizer(4, 3, 10, 10)
        grid.AddGrowableCol(1, 1)

        self.naca_ctrl  = wx.TextCtrl(self, value=str(defaults["naca"]))
        self.chord_ctrl = wx.TextCtrl(self, value=str(defaults["chord"]))
        self.npts_ctrl  = wx.TextCtrl(self, value=str(defaults["n_pts"]))
        self.plane_ctrl = wx.RadioBox(self, label="Output Plane", choices=self.PLANES,
                                      majorDimension=1, style=wx.RA_SPECIFY_COLS)
        self.plane_ctrl.SetSelection(int(defaults["plane"]))

        self.naca_ctrl.SetToolTip("5-digit NACA code, e.g. 23012. Third digit must be 0 (non-reflexed).")
        self.chord_ctrl.SetToolTip("Chord length in mm.")
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
            "NACA 5-DIGIT AIRFOIL GENERATOR — USER MANUAL\n"
            "==========================================================================\n\n"
            "NACA CODE FORMAT: L P Q T T\n"
            "-----------------------------------------\n"
            " L (1st digit): Design lift coefficient digit.\n"
            "                Design CL = L × 3/20.  Common value: 2 (CL = 0.3).\n\n"
            " P (2nd digit): Position of maximum camber.\n"
            "                Max camber at P/20 × chord.  Supported: 1–5.\n"
            "                P=3 → max camber at 15% chord (most common, 23xxx family).\n\n"
            " Q (3rd digit): Camber line type.  Must be 0 (standard non-reflexed).\n"
            "                Q=1 (reflexed) is not supported.\n\n"
            " TT (4+5th):    Thickness as a percentage of chord.\n"
            "                E.g. 12 = 12% thick.\n\n"
            "COMMON EXAMPLES\n"
            "---------------\n"
            "  23012  →  L=2, P=3 (15%), Q=0, 12% thick  (classic transport wing)\n"
            "  23015  →  L=2, P=3 (15%), Q=0, 15% thick\n"
            "  24012  →  L=2, P=4 (20%), Q=0, 12% thick\n\n"
            "CHORD\n"
            "------\n"
            " Chord length in mm. Leading edge at origin, trailing edge at (chord, 0, 0).\n\n"
            "OUTPUT\n"
            "-------\n"
            " A geometric set 'NACA_XXXXX_Chord_YYYmm' containing:\n"
            "   • A 'Points' sub-set (Upper_001..N, Lower_001..M).\n"
            "   • A closed spline 'Airfoil_Spline': LE→TE upper, TE→LE lower.\n"
        )
        dlg = dialogs.ScrolledMessageDialog(self, help_text, "Help")
        mono = wx.Font(10, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        dlg.text.SetFont(mono)
        dlg.SetSize((660, 560))
        dlg.CenterOnParent()
        dlg.ShowModal()
        dlg.Destroy()

    def Validate(self):
        code = self.naca_ctrl.GetValue().strip()
        if len(code) != 5 or not code.isdigit():
            wx.MessageBox("NACA code must be exactly 5 digits, e.g. 23012.",
                          "Input Error", wx.OK | wx.ICON_ERROR)
            self.naca_ctrl.SetFocus()
            return False

        p_digit = int(code[1])
        if p_digit not in _NACA5_TABLE:
            wx.MessageBox(f"Second digit (P) must be 1–5. Got '{code[1]}'.\n"
                          "Supported camber positions: P=1 (5%), P=2 (10%), P=3 (15%), P=4 (20%), P=5 (25%).",
                          "Input Error", wx.OK | wx.ICON_ERROR)
            self.naca_ctrl.SetFocus()
            return False

        if code[2] != '0':
            wx.MessageBox(f"Third digit (Q) must be 0 (standard non-reflexed). Got '{code[2]}'.\n"
                          "Reflexed camber lines (Q=1) are not supported by this script.",
                          "Input Error", wx.OK | wx.ICON_ERROR)
            self.naca_ctrl.SetFocus()
            return False

        if int(code[0]) == 0:
            wx.MessageBox("First digit (L) must be 1–9 (non-zero design lift coefficient).",
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
    SETTINGS_DIR  = os.path.join(os.environ['APPDATA'], 'pycatia_scripts', 'NACA_5_Digit_Airfoil_Generator')
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

    dlg = Naca5Dialog(None)
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

    l_digit = int(naca_code[0])
    p_digit = int(naca_code[1])
    t_frac  = int(naca_code[3:]) / 100.0

    upper_norm, lower_norm = naca5_points(l_digit, p_digit, t_frac, n_pts)

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

        pts        = []
        spline_pts = []

        part.in_work_object = pts_set
        for i, (xu, yu) in enumerate(upper_norm):
            x3, y3, z3 = to_3d(xu, yu, chord, plane_idx)
            pt = hsf.add_new_point_coord(x3, y3, z3)
            pt.name = f"Upper_{i + 1:03d}"
            pts_set.append_hybrid_shape(pt)
            pts.append(pt)
            spline_pts.append(pt)

        progress.Update(3, "Creating lower surface points...")

        for i, (xl, yl) in enumerate(reversed(lower_norm[1:-1])):
            x3, y3, z3 = to_3d(xl, yl, chord, plane_idx)
            pt = hsf.add_new_point_coord(x3, y3, z3)
            pt.name = f"Lower_{i + 1:03d}"
            pts_set.append_hybrid_shape(pt)
            pts.append(pt)
            spline_pts.append(pt)

        part.update()
        spline_refs = [part.create_reference_from_object(pt) for pt in spline_pts]

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

        design_cl = l_digit * 3 / 20
        camber_pct = _NACA5_TABLE[p_digit][0] * 100
        print(f"\n NACA {naca_code} airfoil generated successfully.")
        print(f"   Design CL:       {design_cl:.2f}  (L={l_digit})")
        print(f"   Max camber at:   {camber_pct:.1f}%  chord  (P={p_digit})")
        print(f"   Thickness:       {int(naca_code[3:])}%")
        print(f"   Chord:           {chord} mm")
        print(f"   Points per side: {n_pts}  ({2 * n_pts - 2} total spline points)")
        print(f"   Plane:           {planes[plane_idx]}")
        print(f"\n\n Completed\n\n")

    except Exception as e:
        import traceback
        print(f"\n Error: Airfoil generation failed: {e}")
        print(traceback.format_exc())
        progress.Update(5, "Error.")
        wx.MessageBox(
            f"Airfoil generation failed:\n\n{e}\n\n{traceback.format_exc()}",
            "Error", wx.OK | wx.ICON_ERROR
        )
    finally:
        progress.Destroy()
