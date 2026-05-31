'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Plot_2D_Function.py
    Version:        1.0
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Plot y = f(x) as a GSD point set and spline from a user-entered expression.
    Author:         Kai-Uwe Rathjen
    Date:           31.05.26
    Description:    Evaluates a user-entered mathematical expression f(x) over a specified X range
                    and creates the resulting curve in the active CATPart as a GSD point set and
                    open spline. All functions from Python's math module are available in the
                    expression (sin, cos, tan, sqrt, log, exp, pi, e, etc.).
                    Output plane (XY, XZ, YZ) selects which axes are used for X and Y.
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

# Safe evaluation namespace: all math module functions + abs, round.
_MATH_NS = {k: getattr(math, k) for k in dir(math) if not k.startswith('_')}
_MATH_NS['abs']   = abs
_MATH_NS['round'] = round


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


def eval_fx(expr, x_val):
    """Evaluate f(x) expression for a given x value. Raises on error."""
    ns = _MATH_NS.copy()
    ns['x'] = x_val
    return float(eval(expr, {"__builtins__": {}}, ns))


def map_to_plane(u, v, plane_idx):
    """Map 2D (u, v) to 3D coordinates for the chosen output plane."""
    if plane_idx == 0:
        return u, v, 0.0
    elif plane_idx == 1:
        return u, 0.0, v
    else:
        return 0.0, u, v


def _sanitise_for_name(expr):
    """Return a shortened, filesystem-safe version of an expression for use in a geo set name."""
    safe = expr.replace(' ', '').replace('*', 'x').replace('/', '_').replace('+', 'p').replace('-', 'm')
    return safe[:30]


class FunctionDialog(wx.Dialog):
    HARDCODED_DEFAULTS = {
        "expr":    "sin(x) * 10",
        "x_start": "0.0",
        "x_end":   "300.0",
        "n_pts":   "100",
        "plane":   0,
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

        super().__init__(parent, title="Plot 2D Function  y = f(x)",
                         style=wx.DEFAULT_DIALOG_STYLE | wx.STAY_ON_TOP)

        vbox = wx.BoxSizer(wx.VERTICAL)
        grid = wx.FlexGridSizer(5, 3, 10, 10)
        grid.AddGrowableCol(1, 1)

        self.expr_ctrl   = wx.TextCtrl(self, value=str(defaults["expr"]))
        self.xstart_ctrl = wx.TextCtrl(self, value=str(defaults["x_start"]))
        self.xend_ctrl   = wx.TextCtrl(self, value=str(defaults["x_end"]))
        self.npts_ctrl   = wx.TextCtrl(self, value=str(defaults["n_pts"]))
        self.plane_ctrl  = wx.RadioBox(self, label="Output Plane", choices=self.PLANES,
                                       majorDimension=1, style=wx.RA_SPECIFY_COLS)
        self.plane_ctrl.SetSelection(int(defaults["plane"]))

        self.expr_ctrl.SetToolTip(
            "Python math expression using x as the variable.\n"
            "Available: sin, cos, tan, sqrt, log, log10, exp, pi, e, abs, etc.\n"
            "Examples: sin(x)*10   x**2 / 100   log(x+1)*20"
        )
        self.xstart_ctrl.SetToolTip("Start of the X range (mm).")
        self.xend_ctrl.SetToolTip("End of the X range (mm). Must be greater than X start.")
        self.npts_ctrl.SetToolTip("Number of sample points. Minimum 2.")

        grid.AddMany([
            (wx.StaticText(self, label="f(x) =")),       (self.expr_ctrl,   1, wx.EXPAND), (wx.StaticText(self, label="")),
            (wx.StaticText(self, label="X start:")),     (self.xstart_ctrl, 1, wx.EXPAND), (wx.StaticText(self, label="mm")),
            (wx.StaticText(self, label="X end:")),       (self.xend_ctrl,   1, wx.EXPAND), (wx.StaticText(self, label="mm")),
            (wx.StaticText(self, label="Points:")),      (self.npts_ctrl,   1, wx.EXPAND), (wx.StaticText(self, label="pts")),
            (wx.StaticText(self, label="Plane:")),       (self.plane_ctrl,  0),            (wx.StaticText(self, label="")),
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
        self.expr_ctrl.SetValue(d["expr"])
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
            "PLOT 2D FUNCTION — USER MANUAL\n"
            "==========================================================================\n\n"
            "EXPRESSION  f(x)\n"
            "-----------------\n"
            " Enter a Python math expression where 'x' is the independent variable.\n"
            " The result is the Y coordinate at each X position.\n\n"
            " All functions from Python's math module are available:\n"
            "   sin, cos, tan, asin, acos, atan, atan2(y,x)\n"
            "   sinh, cosh, tanh\n"
            "   sqrt, exp, log (natural), log2, log10\n"
            "   floor, ceil, fabs, factorial\n"
            "   pi  (3.14159…),  e  (2.71828…)\n\n"
            " EXAMPLES\n"
            "   sin(x) * 10              → sine wave, amplitude 10 mm\n"
            "   x**2 / 100               → parabola\n"
            "   log(x + 1) * 20          → logarithm curve (x must stay > -1)\n"
            "   cos(x * pi / 180) * 50   → cosine where x is in degrees\n"
            "   sqrt(abs(x)) * 5         → square-root shape\n"
            "   (x/100)**3 * 100         → cubic\n\n"
            "X RANGE\n"
            "--------\n"
            " The X range is in mm. The Y coordinates produced by f(x) are also in mm.\n"
            " Make sure the expression is defined over the full X range (no division by\n"
            " zero, no log of negative numbers, etc.).\n\n"
            "OUTPUT PLANE\n"
            "-------------\n"
            " XY: curve runs along X, f(x) is plotted in Y.\n"
            " XZ: curve runs along X, f(x) is plotted in Z.\n"
            " YZ: curve runs along Y, f(x) is plotted in Z.\n\n"
            "OUTPUT\n"
            "-------\n"
            " A geometric set 'f(x)_<expr>' containing:\n"
            "   • A 'Points' sub-set with all sample points.\n"
            "   • An open GSD spline 'Function_Spline'.\n"
        )
        dlg = dialogs.ScrolledMessageDialog(self, help_text, "Help")
        mono = wx.Font(10, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        dlg.text.SetFont(mono)
        dlg.SetSize((640, 580))
        dlg.CenterOnParent()
        dlg.ShowModal()
        dlg.Destroy()

    def Validate(self):
        expr = self.expr_ctrl.GetValue().strip()
        if not expr:
            wx.MessageBox("Expression f(x) cannot be empty.", "Input Error", wx.OK | wx.ICON_ERROR)
            self.expr_ctrl.SetFocus()
            return False

        # Test evaluation at x=1
        try:
            eval_fx(expr, 1.0)
        except Exception as e:
            wx.MessageBox(f"Expression could not be evaluated at x=1:\n{e}\n\n"
                          "Check for syntax errors or unsupported functions.",
                          "Expression Error", wx.OK | wx.ICON_ERROR)
            self.expr_ctrl.SetFocus()
            return False

        for ctrl, name in [
            (self.xstart_ctrl, "X start"),
            (self.xend_ctrl,   "X end"),
        ]:
            try:
                float(ctrl.GetValue().strip())
            except ValueError:
                wx.MessageBox(f"{name} must be a valid number.", "Input Error", wx.OK | wx.ICON_ERROR)
                ctrl.SetFocus()
                return False

        if float(self.xend_ctrl.GetValue()) <= float(self.xstart_ctrl.GetValue()):
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
            "expr":    self.expr_ctrl.GetValue().strip(),
            "x_start": float(self.xstart_ctrl.GetValue()),
            "x_end":   float(self.xend_ctrl.GetValue()),
            "n_pts":   int(self.npts_ctrl.GetValue()),
            "plane":   self.plane_ctrl.GetSelection(),
        }


if __name__ == "__main__":
    SETTINGS_DIR  = os.path.join(os.environ['APPDATA'], 'pycatia_scripts', 'Plot_2D_Function')
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

    dlg = FunctionDialog(None)
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

    expr      = params["expr"]
    x_start   = params["x_start"]
    x_end     = params["x_end"]
    n_pts     = params["n_pts"]
    plane_idx = params["plane"]
    planes    = ["XY", "XZ", "YZ"]

    xs = [x_start + (x_end - x_start) * i / (n_pts - 1) for i in range(n_pts)]

    # Pre-evaluate all points — catch errors before touching CATIA
    coords = []
    for x_val in xs:
        try:
            y_val = eval_fx(expr, x_val)
        except Exception as e:
            wx.MessageBox(f"Expression evaluation failed at x = {x_val:.4f}:\n{e}",
                          "Evaluation Error", wx.OK | wx.ICON_ERROR)
            exit()
        coords.append((x_val, y_val))

    progress = wx.ProgressDialog(
        "Plotting Function", "Initialising...", maximum=4, parent=None,
        style=(wx.PD_APP_MODAL | wx.PD_AUTO_HIDE | wx.PD_SMOOTH |
               wx.PD_ELAPSED_TIME | wx.PD_REMAINING_TIME)
    )

    try:
        progress.Update(1, "Creating geometric sets...")

        geo_set = part.hybrid_bodies.add()
        geo_set.name = f"f(x)_{_sanitise_for_name(expr)}"

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
        spline.name = "Function_Spline"
        geo_set.append_hybrid_shape(spline)
        part.update()

        progress.Update(4, "Done.")

        y_vals = [c[1] for c in coords]
        print(f"\n Function curve generated successfully.")
        print(f"   f(x) = {expr}")
        print(f"   X range: {x_start} -> {x_end} mm")
        print(f"   Y range: {min(y_vals):.4f} -> {max(y_vals):.4f} mm")
        print(f"   Points:  {n_pts}")
        print(f"   Plane:   {planes[plane_idx]}")
        print(f"\n\n Completed\n\n")

    except Exception as e:
        import traceback
        print(f"\n Error: Function plot failed: {e}")
        print(traceback.format_exc())
        progress.Update(4, "Error.")
        wx.MessageBox(
            f"Function plot failed:\n\n{e}\n\n{traceback.format_exc()}",
            "Error", wx.OK | wx.ICON_ERROR
        )
    finally:
        progress.Destroy()
