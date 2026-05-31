'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Sine_Wave_Curve_Generator.py
    Version:        1.0
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Generate a sine wave curve as a point set and GSD spline.
    Author:         Kai-Uwe Rathjen
    Date:           31.05.26
    Description:    Creates a sine wave curve in the active CATPart from amplitude, period,
                    phase, x-range, and point count. The curve is defined as y = A·sin(2π/T · x + φ)
                    where A = amplitude, T = period (wavelength), φ = phase in degrees.
                    Points are placed in a Points sub-set and connected by an open GSD spline.
                    Output plane (XY, XZ, YZ) is selectable. User parameters are persisted.
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


def sine_wave_points(amp, period, phase_deg, x_start, x_end, n_pts):
    """Return list of (x, y) for y = A·sin(2π/T · x + φ)."""
    phase = math.radians(phase_deg)
    pts   = []
    for i in range(n_pts):
        x = x_start + (x_end - x_start) * i / (n_pts - 1)
        y = amp * math.sin(2 * math.pi / period * x + phase)
        pts.append((x, y))
    return pts


def map_to_plane(u, v, plane_idx):
    """Map 2D (u, v) to 3D coordinates for the chosen output plane."""
    if plane_idx == 0:
        return u, v, 0.0
    elif plane_idx == 1:
        return u, 0.0, v
    else:
        return 0.0, u, v


class SineWaveDialog(wx.Dialog):
    HARDCODED_DEFAULTS = {
        "amplitude": "10.0",
        "period":    "100.0",
        "phase":     "0.0",
        "x_start":   "0.0",
        "x_end":     "300.0",
        "n_pts":     "100",
        "plane":     0,
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

        super().__init__(parent, title="Sine Wave Curve Generator",
                         style=wx.DEFAULT_DIALOG_STYLE | wx.STAY_ON_TOP)

        vbox = wx.BoxSizer(wx.VERTICAL)
        grid = wx.FlexGridSizer(7, 3, 10, 10)
        grid.AddGrowableCol(1, 1)

        self.amp_ctrl    = wx.TextCtrl(self, value=str(defaults["amplitude"]))
        self.period_ctrl = wx.TextCtrl(self, value=str(defaults["period"]))
        self.phase_ctrl  = wx.TextCtrl(self, value=str(defaults["phase"]))
        self.xstart_ctrl = wx.TextCtrl(self, value=str(defaults["x_start"]))
        self.xend_ctrl   = wx.TextCtrl(self, value=str(defaults["x_end"]))
        self.npts_ctrl   = wx.TextCtrl(self, value=str(defaults["n_pts"]))
        self.plane_ctrl  = wx.RadioBox(self, label="Output Plane", choices=self.PLANES,
                                       majorDimension=1, style=wx.RA_SPECIFY_COLS)
        self.plane_ctrl.SetSelection(int(defaults["plane"]))

        self.amp_ctrl.SetToolTip("Peak amplitude — maximum deviation from zero (mm).")
        self.period_ctrl.SetToolTip("Wavelength / period — length of one complete cycle (mm).")
        self.phase_ctrl.SetToolTip("Phase offset in degrees. 0° starts at zero, 90° starts at peak.")
        self.xstart_ctrl.SetToolTip("Start of the X range (mm).")
        self.xend_ctrl.SetToolTip("End of the X range (mm). Must be greater than X start.")
        self.npts_ctrl.SetToolTip("Number of sample points. More points give a smoother spline. Minimum 2.")

        grid.AddMany([
            (wx.StaticText(self, label="Amplitude:")),  (self.amp_ctrl,    1, wx.EXPAND), (wx.StaticText(self, label="mm")),
            (wx.StaticText(self, label="Period:")),     (self.period_ctrl, 1, wx.EXPAND), (wx.StaticText(self, label="mm")),
            (wx.StaticText(self, label="Phase:")),      (self.phase_ctrl,  1, wx.EXPAND), (wx.StaticText(self, label="°")),
            (wx.StaticText(self, label="X start:")),    (self.xstart_ctrl, 1, wx.EXPAND), (wx.StaticText(self, label="mm")),
            (wx.StaticText(self, label="X end:")),      (self.xend_ctrl,   1, wx.EXPAND), (wx.StaticText(self, label="mm")),
            (wx.StaticText(self, label="Points:")),     (self.npts_ctrl,   1, wx.EXPAND), (wx.StaticText(self, label="pts")),
            (wx.StaticText(self, label="Plane:")),      (self.plane_ctrl,  0),            (wx.StaticText(self, label="")),
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
        self.amp_ctrl.SetValue(d["amplitude"])
        self.period_ctrl.SetValue(d["period"])
        self.phase_ctrl.SetValue(d["phase"])
        self.xstart_ctrl.SetValue(d["x_start"])
        self.xend_ctrl.SetValue(d["x_end"])
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
            "SINE WAVE CURVE GENERATOR — USER MANUAL\n"
            "==========================================================================\n\n"
            "FORMULA\n"
            "-------\n"
            "   y = Amplitude × sin( 2π / Period × x + Phase_radians )\n\n"
            "PARAMETERS\n"
            "----------\n"
            " Amplitude\n"
            "   Peak value (mm) — the wave oscillates between −Amplitude and +Amplitude.\n\n"
            " Period\n"
            "   Length of one complete cycle (mm), also called wavelength.\n"
            "   Must be greater than zero.\n\n"
            " Phase\n"
            "   Horizontal shift in degrees.\n"
            "     0°  → wave starts at zero, rising.\n"
            "     90° → wave starts at peak amplitude.\n"
            "    −90° → wave starts at −amplitude.\n\n"
            " X Start / X End\n"
            "   The X range over which the wave is sampled (mm).\n"
            "   X End must be greater than X Start.\n\n"
            " Points\n"
            "   Number of sample points. 100 is recommended for a smooth result.\n"
            "   Use more points for high-frequency waves or very long X ranges.\n\n"
            " Output Plane\n"
            "   XY: wave runs along X, oscillates in Y.\n"
            "   XZ: wave runs along X, oscillates in Z.\n"
            "   YZ: wave runs along Y, oscillates in Z.\n\n"
            "OUTPUT\n"
            "------\n"
            " A geometric set 'Sine_Wave_A{a}mm_T{t}mm' containing:\n"
            "   • A 'Points' sub-set with all sample points.\n"
            "   • An open GSD spline 'Sine_Wave_Spline'.\n"
        )
        dlg = dialogs.ScrolledMessageDialog(self, help_text, "Help")
        mono = wx.Font(10, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        dlg.text.SetFont(mono)
        dlg.SetSize((600, 540))
        dlg.CenterOnParent()
        dlg.ShowModal()
        dlg.Destroy()

    def Validate(self):
        for ctrl, name in [
            (self.amp_ctrl,    "Amplitude"),
            (self.period_ctrl, "Period"),
            (self.phase_ctrl,  "Phase"),
            (self.xstart_ctrl, "X start"),
            (self.xend_ctrl,   "X end"),
        ]:
            try:
                float(ctrl.GetValue().strip())
            except ValueError:
                wx.MessageBox(f"{name} must be a valid number.", "Input Error", wx.OK | wx.ICON_ERROR)
                ctrl.SetFocus()
                return False

        period = float(self.period_ctrl.GetValue())
        if period <= 0.0:
            wx.MessageBox("Period must be greater than zero.", "Input Error", wx.OK | wx.ICON_ERROR)
            self.period_ctrl.SetFocus()
            return False

        x_start = float(self.xstart_ctrl.GetValue())
        x_end   = float(self.xend_ctrl.GetValue())
        if x_end <= x_start:
            wx.MessageBox("X end must be greater than X start.", "Input Error", wx.OK | wx.ICON_ERROR)
            self.xend_ctrl.SetFocus()
            return False

        try:
            n = int(self.npts_ctrl.GetValue().strip())
            if n < 2:
                wx.MessageBox("Number of points must be at least 2.", "Input Error", wx.OK | wx.ICON_ERROR)
                self.npts_ctrl.SetFocus()
                return False
        except ValueError:
            wx.MessageBox("Number of points must be a whole number.", "Input Error", wx.OK | wx.ICON_ERROR)
            self.npts_ctrl.SetFocus()
            return False

        return True

    def get_values(self):
        return {
            "amplitude": float(self.amp_ctrl.GetValue()),
            "period":    float(self.period_ctrl.GetValue()),
            "phase":     float(self.phase_ctrl.GetValue()),
            "x_start":   float(self.xstart_ctrl.GetValue()),
            "x_end":     float(self.xend_ctrl.GetValue()),
            "n_pts":     int(self.npts_ctrl.GetValue()),
            "plane":     self.plane_ctrl.GetSelection(),
        }


if __name__ == "__main__":
    SETTINGS_DIR  = os.path.join(os.environ['APPDATA'], 'pycatia_scripts', 'Sine_Wave_Curve_Generator')
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

    dlg = SineWaveDialog(None)
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

    amp       = params["amplitude"]
    period    = params["period"]
    phase     = params["phase"]
    x_start   = params["x_start"]
    x_end     = params["x_end"]
    n_pts     = params["n_pts"]
    plane_idx = params["plane"]
    planes    = ["XY", "XZ", "YZ"]

    coords = sine_wave_points(amp, period, phase, x_start, x_end, n_pts)

    progress = wx.ProgressDialog(
        "Generating Sine Wave", "Initialising...", maximum=4, parent=None,
        style=(wx.PD_APP_MODAL | wx.PD_AUTO_HIDE | wx.PD_SMOOTH |
               wx.PD_ELAPSED_TIME | wx.PD_REMAINING_TIME)
    )

    try:
        progress.Update(1, "Creating geometric sets...")

        geo_set = part.hybrid_bodies.add()
        geo_set.name = f"Sine_Wave_A{int(amp)}mm_T{int(period)}mm"

        pts_set = geo_set.hybrid_bodies.add()
        pts_set.name = "Points"

        progress.Update(2, "Creating points...")

        pts = []
        part.in_work_object = pts_set
        for i, (u, v) in enumerate(coords):
            x, y, z = map_to_plane(u, v, plane_idx)
            pt = hsf.add_new_point_coord(x, y, z)
            pt.name = f"Pt_{i + 1:04d}"
            pts_set.append_hybrid_shape(pt)
            pts.append(pt)
        part.update()

        spline_refs = [part.create_reference_from_object(pt) for pt in pts]

        progress.Update(3, "Creating spline...")

        part.in_work_object = geo_set
        spline = hsf.add_new_spline()
        for ref in spline_refs:
            spline.add_point(ref)
        spline.name = "Sine_Wave_Spline"
        geo_set.append_hybrid_shape(spline)
        part.update()

        progress.Update(4, "Done.")

        waves = (x_end - x_start) / period
        print(f"\n Sine wave generated successfully.")
        print(f"   Amplitude: {amp} mm")
        print(f"   Period:    {period} mm")
        print(f"   Phase:     {phase}°")
        print(f"   X range:   {x_start} -> {x_end} mm  ({waves:.2f} cycles)")
        print(f"   Points:    {n_pts}")
        print(f"   Plane:     {planes[plane_idx]}")
        print(f"\n\n Completed\n\n")

    except Exception as e:
        import traceback
        print(f"\n Error: Sine wave generation failed: {e}")
        print(traceback.format_exc())
        progress.Update(4, "Error.")
        wx.MessageBox(
            f"Sine wave generation failed:\n\n{e}\n\n{traceback.format_exc()}",
            "Error", wx.OK | wx.ICON_ERROR
        )
    finally:
        progress.Destroy()
