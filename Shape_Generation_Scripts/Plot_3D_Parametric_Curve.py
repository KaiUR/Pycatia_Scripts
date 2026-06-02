'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Plot_3D_Parametric_Curve.py
    Version:        1.1
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Plot a 3D parametric curve (x(t), y(t), z(t)) as a GSD point set and spline.
    Author:         Kai-Uwe Rathjen
    Date:           31.05.26
    Description:    Evaluates three user-entered mathematical expressions x(t), y(t), z(t) over a
                    parameter range [t_start, t_end] and creates the resulting 3D curve in the active
                    CATPart as a GSD point set and spline. All functions from Python's math module are
                    available. If the first and last points coincide the spline is automatically closed.
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


def eval_expr(expr, t_val):
    """Evaluate a parametric component expression at parameter value t."""
    ns = _MATH_NS.copy()
    ns['t'] = t_val
    return float(eval(expr, {"__builtins__": {}}, ns))


def _sanitise_for_name(expr):
    """Return a shortened, filesystem-safe version of an expression for a geo set name."""
    safe = expr.replace(' ', '').replace('*', 'x').replace('/', '_').replace('+', 'p').replace('-', 'm')
    return safe[:20]


class ParametricDialog(wx.Dialog):
    HARDCODED_DEFAULTS = {
        "expr_x":  "cos(t) * 50",
        "expr_y":  "sin(t) * 50",
        "expr_z":  "t * 5",
        "t_start": "0.0",
        "t_end":   "2 * pi",
        "n_pts":   "100",
    }

    def __init__(self, parent):
        defaults = self.HARDCODED_DEFAULTS.copy()
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r') as f:
                    defaults.update(json.load(f))
            except Exception:
                pass

        super().__init__(parent, title="Plot 3D Parametric Curve",
                         style=wx.DEFAULT_DIALOG_STYLE | wx.STAY_ON_TOP)

        vbox = wx.BoxSizer(wx.VERTICAL)
        grid = wx.FlexGridSizer(6, 3, 10, 10)
        grid.AddGrowableCol(1, 1)

        self.expr_x_ctrl  = wx.TextCtrl(self, value=str(defaults["expr_x"]))
        self.expr_y_ctrl  = wx.TextCtrl(self, value=str(defaults["expr_y"]))
        self.expr_z_ctrl  = wx.TextCtrl(self, value=str(defaults["expr_z"]))
        self.tstart_ctrl  = wx.TextCtrl(self, value=str(defaults["t_start"]))
        self.tend_ctrl    = wx.TextCtrl(self, value=str(defaults["t_end"]))
        self.npts_ctrl    = wx.TextCtrl(self, value=str(defaults["n_pts"]))

        self.expr_x_ctrl.SetToolTip("X coordinate as a function of t.\nAll math module functions available: sin, cos, pi, etc.")
        self.expr_y_ctrl.SetToolTip("Y coordinate as a function of t.")
        self.expr_z_ctrl.SetToolTip("Z coordinate as a function of t.")
        self.tstart_ctrl.SetToolTip("Start value of the parameter t. Can use 'pi': e.g. -pi or 0.")
        self.tend_ctrl.SetToolTip("End value of the parameter t. Can use 'pi': e.g. 2*pi or 10.")
        self.npts_ctrl.SetToolTip("Number of sample points. Minimum 2.")

        grid.AddMany([
            (wx.StaticText(self, label="x(t) =")),     (self.expr_x_ctrl, 1, wx.EXPAND), (wx.StaticText(self, label="mm")),
            (wx.StaticText(self, label="y(t) =")),     (self.expr_y_ctrl, 1, wx.EXPAND), (wx.StaticText(self, label="mm")),
            (wx.StaticText(self, label="z(t) =")),     (self.expr_z_ctrl, 1, wx.EXPAND), (wx.StaticText(self, label="mm")),
            (wx.StaticText(self, label="t start:")),   (self.tstart_ctrl, 1, wx.EXPAND), (wx.StaticText(self, label="")),
            (wx.StaticText(self, label="t end:")),     (self.tend_ctrl,   1, wx.EXPAND), (wx.StaticText(self, label="")),
            (wx.StaticText(self, label="Points:")),    (self.npts_ctrl,   1, wx.EXPAND), (wx.StaticText(self, label="pts")),
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
        self.expr_x_ctrl.SetValue(d["expr_x"])
        self.expr_y_ctrl.SetValue(d["expr_y"])
        self.expr_z_ctrl.SetValue(d["expr_z"])
        self.tstart_ctrl.SetValue(d["t_start"])
        self.tend_ctrl.SetValue(d["t_end"])
        self.npts_ctrl.SetValue(d["n_pts"])

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
            "PLOT 3D PARAMETRIC CURVE — USER MANUAL\n"
            "==========================================================================\n\n"
            "EXPRESSIONS  x(t), y(t), z(t)\n"
            "------------------------------\n"
            " Each coordinate is a Python math expression using 't' as the parameter.\n"
            " All functions from Python's math module are available:\n"
            "   sin, cos, tan, asin, acos, atan, atan2(y,x)\n"
            "   sinh, cosh, tanh\n"
            "   sqrt, exp, log (natural), log2, log10\n"
            "   floor, ceil, fabs, factorial\n"
            "   pi  (3.14159…),  e  (2.71828…)\n\n"
            " EXAMPLES\n"
            "   Circle (XY, r=50):   x=cos(t)*50   y=sin(t)*50   z=0\n"
            "   Helix:               x=cos(t)*50   y=sin(t)*50   z=t*10\n"
            "   Lissajous:           x=sin(3*t)*50 y=sin(2*t)*50 z=0\n"
            "   Torus knot (3,2):    x=(3+cos(2*t))*cos(3*t)*20\n"
            "                        y=(3+cos(2*t))*sin(3*t)*20\n"
            "                        z=sin(2*t)*20\n"
            "   Viviani curve:       x=50*(1+cos(t))  y=50*sin(t)  z=100*sin(t/2)\n\n"
            "T RANGE\n"
            "--------\n"
            " t start and t end define the parameter range.\n"
            " You can use 'pi' in the expression: e.g. '2*pi' or '-pi'.\n"
            " The range is sampled at N equally-spaced values.\n\n"
            "CLOSED CURVES\n"
            "--------------\n"
            " If the first and last points are within 0.001 mm of each other, the\n"
            " spline is automatically closed (e.g. full circles, periodic curves).\n\n"
            "OUTPUT\n"
            "-------\n"
            " A geometric set 'Parametric_x(t)_<expr>' containing:\n"
            "   • A 'Points' sub-set with all sample points.\n"
            "   • A GSD spline 'Parametric_Spline' (open or closed).\n"
        )
        dlg = dialogs.ScrolledMessageDialog(self, help_text, "Help")
        mono = wx.Font(10, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        dlg.text.SetFont(mono)
        dlg.SetSize((660, 600))
        dlg.CenterOnParent()
        dlg.ShowModal()
        dlg.Destroy()

    def _parse_t(self, text):
        """Parse a t-range value that may contain 'pi'."""
        ns = {'pi': math.pi, 'e': math.e}
        return float(eval(text.strip(), {"__builtins__": {}}, ns))

    def Validate(self):
        for ctrl, name in [
            (self.expr_x_ctrl, "x(t)"),
            (self.expr_y_ctrl, "y(t)"),
            (self.expr_z_ctrl, "z(t)"),
        ]:
            expr = ctrl.GetValue().strip()
            if not expr:
                wx.MessageBox(f"Expression {name} cannot be empty.", "Input Error", wx.OK | wx.ICON_ERROR)
                ctrl.SetFocus()
                return False
            try:
                eval_expr(expr, 1.0)
            except Exception as e:
                wx.MessageBox(f"Expression {name} could not be evaluated at t=1:\n{e}",
                              "Expression Error", wx.OK | wx.ICON_ERROR)
                ctrl.SetFocus()
                return False

        for ctrl, name in [
            (self.tstart_ctrl, "t start"),
            (self.tend_ctrl,   "t end"),
        ]:
            try:
                self._parse_t(ctrl.GetValue())
            except Exception as e:
                wx.MessageBox(f"{name} could not be parsed:\n{e}\n\nYou may use 'pi', e.g. '2*pi'.",
                              "Input Error", wx.OK | wx.ICON_ERROR)
                ctrl.SetFocus()
                return False

        t_start = self._parse_t(self.tstart_ctrl.GetValue())
        t_end   = self._parse_t(self.tend_ctrl.GetValue())
        if t_end <= t_start:
            wx.MessageBox("t end must be greater than t start.", "Input Error", wx.OK | wx.ICON_ERROR)
            self.tend_ctrl.SetFocus()
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

    def _parse_t(self, text):
        ns = {'pi': math.pi, 'e': math.e}
        return float(eval(text.strip(), {"__builtins__": {}}, ns))

    def get_values(self):
        return {
            "expr_x":  self.expr_x_ctrl.GetValue().strip(),
            "expr_y":  self.expr_y_ctrl.GetValue().strip(),
            "expr_z":  self.expr_z_ctrl.GetValue().strip(),
            "t_start": self.tstart_ctrl.GetValue().strip(),
            "t_end":   self.tend_ctrl.GetValue().strip(),
            "n_pts":   int(self.npts_ctrl.GetValue()),
        }


if __name__ == "__main__":
    SETTINGS_DIR  = os.path.join(os.environ['APPDATA'], 'pycatia_scripts', 'Plot_3D_Parametric_Curve')
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

    dlg = ParametricDialog(None)
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

    expr_x  = params["expr_x"]
    expr_y  = params["expr_y"]
    expr_z  = params["expr_z"]
    n_pts   = params["n_pts"]

    _t_ns = {'pi': math.pi, 'e': math.e}
    t_start = float(eval(params["t_start"], {"__builtins__": {}}, _t_ns))
    t_end   = float(eval(params["t_end"],   {"__builtins__": {}}, _t_ns))

    ts = [t_start + (t_end - t_start) * i / (n_pts - 1) for i in range(n_pts)]

    # Pre-evaluate all points before touching CATIA
    coords = []
    for t_val in ts:
        try:
            x = eval_expr(expr_x, t_val)
            y = eval_expr(expr_y, t_val)
            z = eval_expr(expr_z, t_val)
        except Exception as e:
            wx.MessageBox(f"Expression evaluation failed at t = {t_val:.6f}:\n{e}",
                          "Evaluation Error", wx.OK | wx.ICON_ERROR)
            exit()
        coords.append((x, y, z))

    # Check whether start and end coincide (within 0.001 mm) for auto-close
    p0, p1 = coords[0], coords[-1]
    dist = math.sqrt((p1[0]-p0[0])**2 + (p1[1]-p0[1])**2 + (p1[2]-p0[2])**2)
    is_closed = dist < 0.001

    progress = wx.ProgressDialog(
        "Plotting Parametric Curve", "Initialising...", maximum=4, parent=None,
        style=(wx.PD_APP_MODAL | wx.PD_AUTO_HIDE | wx.PD_SMOOTH |
               wx.PD_ELAPSED_TIME | wx.PD_REMAINING_TIME)
    )

    try:
        progress.Update(1, "Creating geometric sets...")

        geo_set = part.hybrid_bodies.add()
        geo_set.name = f"Parametric_x(t)_{_sanitise_for_name(expr_x)}"

        pts_set = geo_set.hybrid_bodies.add()
        pts_set.name = "Points"

        progress.Update(2, "Creating points...")

        pts = []
        part.in_work_object = pts_set
        spline_coords = coords[:-1] if is_closed else coords
        for i, (x, y, z) in enumerate(spline_coords):
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
        if is_closed:
            spline.set_closing(1)
        spline.name = "Parametric_Spline"
        geo_set.append_hybrid_shape(spline)
        part.update()

        progress.Update(4, "Done.")

        closed_label = " (closed)" if is_closed else " (open)"
        print(f"\n Parametric curve generated successfully{closed_label}.")
        print(f"   x(t) = {expr_x}")
        print(f"   y(t) = {expr_y}")
        print(f"   z(t) = {expr_z}")
        print(f"   t range: {t_start:.6g} -> {t_end:.6g}")
        print(f"   Points:  {n_pts}")
        print(f"\n\n Completed\n\n")

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
        header_text = wx.StaticText(e_dlg, label="An error occurred during parametric curve generation:")
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
