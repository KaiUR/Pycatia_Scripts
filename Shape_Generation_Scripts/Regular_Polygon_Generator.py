'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Regular_Polygon_Generator.py
    Version:        1.1
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Generate a regular polygon as vertices, edges, and a joined wire in GSD.
    Author:         Kai-Uwe Rathjen
    Date:           31.05.26
    Description:    Creates a regular N-sided polygon in the active CATPart. The user specifies the
                    number of sides, radius type (circumradius vertex-to-centre, or inradius
                    edge-midpoint-to-centre), radius value, and optional rotation offset.
                    Output plane can be XY, XZ, YZ, or Custom — when Custom is selected the script
                    prompts for a plane then a centre point from the CATIA model after OK.
                    N vertex points are placed in a Vertices sub-set, N straight edges connect them
                    (hidden after creation), and a Polygon_Join joins all edges into a single closed
                    wire. User parameters are persisted between runs.
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
from pycatia.enumeration.enums import CatVisPropertyShow
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


def polygon_vertices(n, r_circ, rotation_deg):
    """Return list of (u, v) vertex coordinates for a regular N-gon with circumradius r_circ."""
    rotation_rad = math.radians(rotation_deg)
    pts = []
    for i in range(n):
        angle = 2 * math.pi * i / n + rotation_rad
        pts.append((r_circ * math.cos(angle), r_circ * math.sin(angle)))
    return pts


def map_to_plane(u, v, plane_idx):
    """Map 2D (u, v) to 3D coordinates for an axis-aligned output plane."""
    if plane_idx == 0:
        return u, v, 0.0
    elif plane_idx == 1:
        return u, 0.0, v
    else:
        return 0.0, u, v


def map_to_custom_plane(u, v, origin, local_x, local_y, centre_u, centre_v):
    """Map 2D (u, v) to 3D on a custom plane, offset by the projected centre point."""
    u += centre_u
    v += centre_v
    x = origin[0] + u * local_x[0] + v * local_y[0]
    y = origin[1] + u * local_x[1] + v * local_y[1]
    z = origin[2] + u * local_x[2] + v * local_y[2]
    return x, y, z


class PolygonDialog(wx.Dialog):
    HARDCODED_DEFAULTS = {
        "n_sides":  "6",
        "radius":   "50.0",
        "r_type":   0,
        "rotation": "0.0",
        "plane":    0,
    }
    PLANES  = ["XY", "XZ", "YZ", "Custom (select)"]
    R_TYPES = ["Circumradius (vertex)", "Inradius (edge midpoint)", "Side length"]

    def __init__(self, parent):
        defaults = self.HARDCODED_DEFAULTS.copy()
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r') as f:
                    defaults.update(json.load(f))
            except Exception:
                pass

        super().__init__(parent, title="Regular Polygon Generator",
                         style=wx.DEFAULT_DIALOG_STYLE | wx.STAY_ON_TOP)

        vbox = wx.BoxSizer(wx.VERTICAL)
        grid = wx.FlexGridSizer(5, 3, 10, 10)
        grid.AddGrowableCol(1, 1)

        self.nsides_ctrl   = wx.TextCtrl(self, value=str(defaults["n_sides"]))
        self.radius_ctrl   = wx.TextCtrl(self, value=str(defaults["radius"]))
        self.rtype_ctrl    = wx.RadioBox(self, label="Radius Type", choices=self.R_TYPES,
                                         majorDimension=1, style=wx.RA_SPECIFY_COLS)
        self.rtype_ctrl.SetSelection(int(defaults["r_type"]))
        self.rotation_ctrl = wx.TextCtrl(self, value=str(defaults["rotation"]))
        self.plane_ctrl    = wx.RadioBox(self, label="Output Plane", choices=self.PLANES,
                                         majorDimension=1, style=wx.RA_SPECIFY_COLS)
        self.plane_ctrl.SetSelection(int(defaults["plane"]))

        self.nsides_ctrl.SetToolTip("Number of sides. Minimum 3 (triangle). E.g. 6 = hexagon.")
        self.radius_ctrl.SetToolTip("Radius value. Interpretation depends on Radius Type selection.")
        self.rotation_ctrl.SetToolTip("Rotation offset in degrees. 0° places the first vertex at the positive first-axis direction.")
        self.plane_ctrl.SetToolTip("XY/XZ/YZ: axis-aligned plane through origin.\nCustom: prompts for a plane then a centre point after OK.")

        self.radius_label = wx.StaticText(self, label="Radius:")
        self._update_radius_label()

        grid.AddMany([
            (wx.StaticText(self, label="Sides:")),       (self.nsides_ctrl,   1, wx.EXPAND), (wx.StaticText(self, label="")),
            (self.radius_label),                         (self.radius_ctrl,   1, wx.EXPAND), (wx.StaticText(self, label="mm")),
            (wx.StaticText(self, label="Radius type:")), (self.rtype_ctrl,    0),            (wx.StaticText(self, label="")),
            (wx.StaticText(self, label="Rotation:")),    (self.rotation_ctrl, 1, wx.EXPAND), (wx.StaticText(self, label="°")),
            (wx.StaticText(self, label="Plane:")),       (self.plane_ctrl,    0),            (wx.StaticText(self, label="")),
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

        self.rtype_ctrl.Bind(wx.EVT_RADIOBOX, self._on_rtype_change)
        reset_btn.Bind(wx.EVT_BUTTON, self.on_reset)
        clear_btn.Bind(wx.EVT_BUTTON, self.on_clear)
        self.Bind(wx.EVT_BUTTON, self.on_help, id=wx.ID_HELP)

    def _update_radius_label(self):
        labels = ["Radius:", "Radius:", "Side Length:"]
        self.radius_label.SetLabel(labels[self.rtype_ctrl.GetSelection()])

    def _on_rtype_change(self, event):
        self._update_radius_label()
        event.Skip()

    def on_reset(self, event):
        d = self.HARDCODED_DEFAULTS
        self.nsides_ctrl.SetValue(d["n_sides"])
        self.radius_ctrl.SetValue(d["radius"])
        self.rtype_ctrl.SetSelection(int(d["r_type"]))
        self.rotation_ctrl.SetValue(d["rotation"])
        self.plane_ctrl.SetSelection(int(d["plane"]))
        self._update_radius_label()

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
            "REGULAR POLYGON GENERATOR — USER MANUAL\n"
            "==========================================================================\n\n"
            "PARAMETERS\n"
            "----------\n"
            " Sides\n"
            "   Number of sides: 3 = triangle, 4 = square, 6 = hexagon, etc.\n\n"
            " Radius\n"
            "   The size of the polygon, interpreted according to Radius Type.\n\n"
            " Radius Type\n"
            "   Circumradius (vertex):      Distance from centre to a vertex.\n"
            "                               This is the radius of the circumscribed circle.\n"
            "   Inradius (edge midpoint):   Distance from centre to the midpoint of an edge.\n"
            "                               This is the radius of the inscribed circle.\n"
            "                               Inradius = Circumradius x cos(pi/N)\n"
            "   Side length:                Length of one edge.\n"
            "                               Side = 2 x Circumradius x sin(pi/N)\n\n"
            " Rotation\n"
            "   Rotates the whole polygon by this angle in degrees.\n"
            "   0 deg places the first vertex at the positive first-axis direction.\n\n"
            " Plane\n"
            "   XY / XZ / YZ: polygon is centred at the origin on the chosen axis plane.\n"
            "   Custom (select): after clicking OK you will be prompted to:\n"
            "     1. Select a plane (any GSD plane or planar face) in CATIA.\n"
            "     2. Select a centre point in CATIA.\n"
            "        The polygon is placed on the selected plane, centred at the\n"
            "        projection of the selected point onto that plane.\n\n"
            "OUTPUT\n"
            "------\n"
            " A geometric set 'Polygon_N{n}_R{r}mm' containing:\n"
            "   - A 'Vertices' sub-set with N vertex points.\n"
            "   - N edges (Edge_01 ... Edge_N), hidden after creation.\n"
            "   - A 'Polygon_Join' — single closed wire joining all edges.\n"
        )
        dlg = dialogs.ScrolledMessageDialog(self, help_text, "Help")
        mono = wx.Font(10, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        dlg.text.SetFont(mono)
        dlg.SetSize((600, 520))
        dlg.CenterOnParent()
        dlg.ShowModal()
        dlg.Destroy()

    def Validate(self):
        try:
            n = int(self.nsides_ctrl.GetValue().strip())
            if n < 3:
                wx.MessageBox("Number of sides must be at least 3.", "Input Error", wx.OK | wx.ICON_ERROR)
                self.nsides_ctrl.SetFocus()
                return False
        except ValueError:
            wx.MessageBox("Number of sides must be a whole number.", "Input Error", wx.OK | wx.ICON_ERROR)
            self.nsides_ctrl.SetFocus()
            return False

        try:
            r = float(self.radius_ctrl.GetValue().strip())
            if r <= 0.0:
                wx.MessageBox("Radius must be greater than zero.", "Input Error", wx.OK | wx.ICON_ERROR)
                self.radius_ctrl.SetFocus()
                return False
        except ValueError:
            wx.MessageBox("Radius must be a valid number.", "Input Error", wx.OK | wx.ICON_ERROR)
            self.radius_ctrl.SetFocus()
            return False

        try:
            float(self.rotation_ctrl.GetValue().strip())
        except ValueError:
            wx.MessageBox("Rotation must be a valid number.", "Input Error", wx.OK | wx.ICON_ERROR)
            self.rotation_ctrl.SetFocus()
            return False

        return True

    def get_values(self):
        return {
            "n_sides":  int(self.nsides_ctrl.GetValue()),
            "radius":   float(self.radius_ctrl.GetValue()),
            "r_type":   self.rtype_ctrl.GetSelection(),
            "rotation": float(self.rotation_ctrl.GetValue()),
            "plane":    self.plane_ctrl.GetSelection(),
        }


if __name__ == "__main__":
    SETTINGS_DIR  = os.path.join(os.environ['APPDATA'], 'pycatia_scripts', 'Regular_Polygon_Generator')
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

    dlg = PolygonDialog(None)
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

    n         = params["n_sides"]
    r_input   = params["radius"]
    r_type    = params["r_type"]
    rotation  = params["rotation"]
    plane_idx = params["plane"]

    if r_type == 1:
        r_circ = r_input / math.cos(math.pi / n)
    elif r_type == 2:
        r_circ = r_input / (2 * math.sin(math.pi / n))
    else:
        r_circ = r_input

    vertices = polygon_vertices(n, r_circ, rotation)

    # For custom plane: select plane then centre point before opening the progress dialog
    plane_origin = plane_local_x = plane_local_y = None
    centre_u = centre_v = 0.0
    plane_label = ["XY", "XZ", "YZ"][plane_idx] if plane_idx < 3 else "Custom"

    if plane_idx == 3:
        sel = caa.active_document.selection

        sel.clear()
        status = sel.select_element3(("Plane",), "Select plane for polygon", False, 2, False)
        if status != "Normal":
            print("\n Error: No plane selected. Script cancelled.\n")
            wx.MessageBox("No plane selected. Script cancelled.", "Cancelled", wx.OK | wx.ICON_INFORMATION)
            exit()
        plane_ref = part.create_reference_from_object(sel.item(1).value)
        sel.clear()

        spa = part_document.spa_workbench()
        pd  = spa.get_measurable(plane_ref).get_plane()
        plane_origin  = (pd[0], pd[1], pd[2])
        plane_local_x = (pd[3], pd[4], pd[5])
        plane_local_y = (pd[6], pd[7], pd[8])

        sel.clear()
        status = sel.select_element3(("AnyObject",), "Select centre point for polygon", False, 2, False)
        if status != "Normal":
            print("\n Error: No centre point selected. Script cancelled.\n")
            wx.MessageBox("No point selected. Script cancelled.", "Cancelled", wx.OK | wx.ICON_INFORMATION)
            exit()
        try:
            pt_meas = spa.get_measurable(sel.item(1).reference)
            coords  = pt_meas.get_point()
            diff    = [coords[i] - plane_origin[i] for i in range(3)]
            centre_u = sum(diff[i] * plane_local_x[i] for i in range(3))
            centre_v = sum(diff[i] * plane_local_y[i] for i in range(3))
        except Exception as e:
            print(f"\n Error: Could not read point coordinates: {e}\n")
            wx.MessageBox(f"Could not read point coordinates:\n{e}", "Error", wx.OK | wx.ICON_ERROR)
            exit()
        sel.clear()

    progress = wx.ProgressDialog(
        "Generating Polygon", "Initialising...", maximum=5, parent=None,
        style=(wx.PD_APP_MODAL | wx.PD_AUTO_HIDE | wx.PD_SMOOTH |
               wx.PD_ELAPSED_TIME | wx.PD_REMAINING_TIME)
    )

    try:
        progress.Update(1, "Creating geometric sets...")

        geo_set = part.hybrid_bodies.add()
        geo_set.name = f"Polygon_N{n}_R{int(r_input)}mm"

        vtx_set = geo_set.hybrid_bodies.add()
        vtx_set.name = "Vertices"

        progress.Update(2, "Creating vertex points...")

        pts = []
        part.in_work_object = vtx_set
        for i, (u, v) in enumerate(vertices):
            if plane_idx == 3:
                x, y, z = map_to_custom_plane(u, v, plane_origin, plane_local_x, plane_local_y, centre_u, centre_v)
            else:
                x, y, z = map_to_plane(u, v, plane_idx)
            pt = hsf.add_new_point_coord(x, y, z)
            pt.name = f"Vertex_{i + 1:02d}"
            vtx_set.append_hybrid_shape(pt)
            pts.append(pt)
        part.update()

        refs = [part.create_reference_from_object(pt) for pt in pts]

        progress.Update(3, "Creating edges...")

        lines = []
        part.in_work_object = geo_set
        for i in range(n):
            line = hsf.add_new_line_pt_pt(refs[i], refs[(i + 1) % n])
            line.name = f"Edge_{i + 1:02d}"
            geo_set.append_hybrid_shape(line)
            lines.append(line)
        part.update()

        progress.Update(4, "Creating join...")

        edge_refs = [part.create_reference_from_object(line) for line in lines]
        join = hsf.add_new_join(edge_refs[0], edge_refs[1])
        for ref in edge_refs[2:]:
            join.add_element(ref)
        join.name = "Polygon_Join"
        geo_set.append_hybrid_shape(join)
        part.update()

        selection = caa.active_document.selection
        selection.clear()
        for line in lines:
            selection.add(line)
        selection.vis_properties.set_show(CatVisPropertyShow.catVisPropertyNoShowAttr)
        selection.clear()

        progress.Update(5, "Done.")

        r_type_label = {0: "Circumradius", 1: "Inradius", 2: "Side length"}[r_type]
        print(f"\n Regular polygon generated successfully.")
        print(f"   Sides:        {n}")
        print(f"   {r_type_label}:  {r_input} mm")
        print(f"   Circumradius: {r_circ:.4f} mm")
        print(f"   Rotation:     {rotation} deg")
        print(f"   Plane:        {plane_label}")
        print(f"\n\n Completed\n\n")

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
        header_text = wx.StaticText(e_dlg, label="An error occurred during polygon generation:")
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
