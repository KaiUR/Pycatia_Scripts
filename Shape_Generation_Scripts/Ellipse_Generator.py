'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Ellipse_Generator.py
    Version:        1.1
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Generate an ellipse as a point set and closed GSD spline.
    Author:         Kai-Uwe Rathjen
    Date:           31.05.26
    Description:    Creates a parametric ellipse in the active CATPart from user-defined semi-major
                    axis (a) and semi-minor axis (b). Generates N evenly-spaced points on the ellipse
                    using the parametric form x=a·cos(t), y=b·sin(t), places them in a Points sub-set,
                    and builds a closed GSD spline through them. Output plane (XY, XZ, YZ) is selectable.
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


def ellipse_points(a, b, n_pts):
    """Return list of (u, v) coordinates for a full ellipse with n_pts evenly-spaced points."""
    pts = []
    for i in range(n_pts):
        t = 2 * math.pi * i / n_pts
        pts.append((a * math.cos(t), b * math.sin(t)))
    return pts


def map_to_plane(u, v, plane_idx):
    """Map 2D (u, v) to 3D coordinates for the chosen output plane."""
    if plane_idx == 0:
        return u, v, 0.0
    elif plane_idx == 1:
        return u, 0.0, v
    else:
        return 0.0, u, v


class EllipseDialog(wx.Dialog):
    HARDCODED_DEFAULTS = {
        "semi_a": "100.0",
        "semi_b": "50.0",
        "n_pts":  "72",
        "plane":  0,
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

        super().__init__(parent, title="Ellipse Generator",
                         style=wx.DEFAULT_DIALOG_STYLE | wx.STAY_ON_TOP)

        vbox = wx.BoxSizer(wx.VERTICAL)
        grid = wx.FlexGridSizer(4, 3, 10, 10)
        grid.AddGrowableCol(1, 1)

        self.semi_a_ctrl = wx.TextCtrl(self, value=str(defaults["semi_a"]))
        self.semi_b_ctrl = wx.TextCtrl(self, value=str(defaults["semi_b"]))
        self.npts_ctrl   = wx.TextCtrl(self, value=str(defaults["n_pts"]))
        self.plane_ctrl  = wx.RadioBox(self, label="Output Plane", choices=self.PLANES,
                                       majorDimension=1, style=wx.RA_SPECIFY_COLS)
        self.plane_ctrl.SetSelection(int(defaults["plane"]))

        self.semi_a_ctrl.SetToolTip("Semi-major axis length (a). Must be greater than zero.")
        self.semi_b_ctrl.SetToolTip("Semi-minor axis length (b). Must be greater than zero.")
        self.npts_ctrl.SetToolTip("Number of points on the ellipse. More points give a smoother spline. Minimum 4.")

        grid.AddMany([
            (wx.StaticText(self, label="Semi-major axis (a):")), (self.semi_a_ctrl, 1, wx.EXPAND), (wx.StaticText(self, label="mm")),
            (wx.StaticText(self, label="Semi-minor axis (b):")), (self.semi_b_ctrl, 1, wx.EXPAND), (wx.StaticText(self, label="mm")),
            (wx.StaticText(self, label="Number of points:")),    (self.npts_ctrl,   1, wx.EXPAND), (wx.StaticText(self, label="pts")),
            (wx.StaticText(self, label="Plane:")),               (self.plane_ctrl,  0),            (wx.StaticText(self, label="")),
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
        self.semi_a_ctrl.SetValue(d["semi_a"])
        self.semi_b_ctrl.SetValue(d["semi_b"])
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
            "ELLIPSE GENERATOR — USER MANUAL\n"
            "==========================================================================\n\n"
            "PARAMETERS\n"
            "----------\n"
            " Semi-major axis (a)\n"
            "   The longer half-axis of the ellipse in mm.\n"
            "   The ellipse extends from -a to +a along the first plane axis.\n\n"
            " Semi-minor axis (b)\n"
            "   The shorter half-axis of the ellipse in mm.\n"
            "   The ellipse extends from -b to +b along the second plane axis.\n"
            "   When a = b the result is a circle.\n\n"
            " Number of Points\n"
            "   Number of evenly-spaced sample points placed on the ellipse.\n"
            "   72 gives one point every 5°. Minimum is 4.\n\n"
            " Output Plane\n"
            "   XY: ellipse lies in the XY plane (a along X, b along Y).\n"
            "   XZ: ellipse lies in the XZ plane (a along X, b along Z).\n"
            "   YZ: ellipse lies in the YZ plane (a along Y, b along Z).\n\n"
            "OUTPUT\n"
            "------\n"
            " A geometric set named 'Ellipse_A{a}mm_B{b}mm' is created containing:\n"
            "   • A 'Points' sub-set with all N sample points.\n"
            "   • A closed GSD spline 'Ellipse_Spline' through all points.\n"
        )
        dlg = dialogs.ScrolledMessageDialog(self, help_text, "Help")
        mono = wx.Font(10, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        dlg.text.SetFont(mono)
        dlg.SetSize((580, 500))
        dlg.CenterOnParent()
        dlg.ShowModal()
        dlg.Destroy()

    def Validate(self):
        for ctrl, name, min_val in [
            (self.semi_a_ctrl, "Semi-major axis (a)", 0.0),
            (self.semi_b_ctrl, "Semi-minor axis (b)", 0.0),
        ]:
            try:
                val = float(ctrl.GetValue().strip())
                if val <= min_val:
                    wx.MessageBox(f"{name} must be greater than zero.", "Input Error", wx.OK | wx.ICON_ERROR)
                    ctrl.SetFocus()
                    return False
            except ValueError:
                wx.MessageBox(f"{name} must be a valid number.", "Input Error", wx.OK | wx.ICON_ERROR)
                ctrl.SetFocus()
                return False

        try:
            n = int(self.npts_ctrl.GetValue().strip())
            if n < 4:
                wx.MessageBox("Number of points must be at least 4.", "Input Error", wx.OK | wx.ICON_ERROR)
                self.npts_ctrl.SetFocus()
                return False
        except ValueError:
            wx.MessageBox("Number of points must be a whole number.", "Input Error", wx.OK | wx.ICON_ERROR)
            self.npts_ctrl.SetFocus()
            return False

        return True

    def get_values(self):
        return {
            "semi_a": float(self.semi_a_ctrl.GetValue()),
            "semi_b": float(self.semi_b_ctrl.GetValue()),
            "n_pts":  int(self.npts_ctrl.GetValue()),
            "plane":  self.plane_ctrl.GetSelection(),
        }


if __name__ == "__main__":
    SETTINGS_DIR  = os.path.join(os.environ['APPDATA'], 'pycatia_scripts', 'Ellipse_Generator')
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

    dlg = EllipseDialog(None)
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

    a         = params["semi_a"]
    b         = params["semi_b"]
    n_pts     = params["n_pts"]
    plane_idx = params["plane"]
    planes    = ["XY", "XZ", "YZ"]

    coords = ellipse_points(a, b, n_pts)

    progress = wx.ProgressDialog(
        "Generating Ellipse", "Initialising...", maximum=4, parent=None,
        style=(wx.PD_APP_MODAL | wx.PD_AUTO_HIDE | wx.PD_SMOOTH |
               wx.PD_ELAPSED_TIME | wx.PD_REMAINING_TIME)
    )

    try:
        progress.Update(1, "Creating geometric sets...")

        geo_set = part.hybrid_bodies.add()
        geo_set.name = f"Ellipse_A{int(a)}mm_B{int(b)}mm"

        pts_set = geo_set.hybrid_bodies.add()
        pts_set.name = "Points"

        progress.Update(2, "Creating points...")

        pts = []
        part.in_work_object = pts_set
        for i, (u, v) in enumerate(coords):
            x, y, z = map_to_plane(u, v, plane_idx)
            pt = hsf.add_new_point_coord(x, y, z)
            pt.name = f"Pt_{i + 1:03d}"
            pts_set.append_hybrid_shape(pt)
            pts.append(pt)
        part.update()

        spline_refs = [part.create_reference_from_object(pt) for pt in pts]

        progress.Update(3, "Creating closed spline...")

        part.in_work_object = geo_set
        spline = hsf.add_new_spline()
        for ref in spline_refs:
            spline.add_point(ref)
        spline.set_closing(1)
        spline.name = "Ellipse_Spline"
        geo_set.append_hybrid_shape(spline)
        part.update()

        progress.Update(4, "Done.")

        print("\n Ellipse generated successfully.")
        print(f"   Semi-major axis: {a} mm")
        print(f"   Semi-minor axis: {b} mm")
        print(f"   Points:          {n_pts}")
        print(f"   Plane:           {planes[plane_idx]}")
        print("\n\n Completed\n\n")

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
        header_text = wx.StaticText(e_dlg, label="An error occurred during ellipse generation:")
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
