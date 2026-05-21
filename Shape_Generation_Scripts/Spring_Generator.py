'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Spring_Generator.py
    Version:        1.0
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Generate a parametric helical spring in the active CATPart.
    Author:         Kai-Uwe Rathjen
    Date:           21.05.26
    Description:    This script creates a parametric compression spring using CATIA GSD and Part Design.
                    A helix is created along the Z-axis with the specified pitch and height. A circular
                    wire cross-section sketch is placed on a plane normal to the helix at its start
                    point, then swept along the helix using a Rib (Part Design). The resulting body is
                    named with the key parameters. User parameters are persisted between runs.
                    Note: Hybrid design mode is temporarily disabled if active.
    dependencies = [
                    "pycatia",
                    "wxPython",
                    ]
    requirements:   Python >= 3.10
                    pycatia
                    wxPython
                    Catia V5 running with an open part document.
                    Hybrid design mode should be disabled (the script handles this automatically).
    -----------------------------------------------------------------------------------------------------------------------

    Change:

    -----------------------------------------------------------------------------------------------------------------------
'''

#Imports
from pycatia import catia
from pycatia import CatConstraintType, CatConstraintMode
from pycatia.mec_mod_interfaces.part_document import PartDocument
from pycatia.hybrid_shape_interfaces.hybrid_shape_factory import HybridShapeFactory
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


class SpringDialog(wx.Dialog):
    HARDCODED_DEFAULTS = {
        "wire_d":       "3.0",
        "coil_d":       "25.0",
        "free_length":  "80.0",
        "num_coils":    "8.0",
        "clockwise":    True,
    }

    def __init__(self, parent):
        defaults = self.HARDCODED_DEFAULTS.copy()
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r') as f:
                    defaults.update(json.load(f))
            except Exception:
                pass

        super().__init__(parent, title="Spring Generator", size=(420, 340),
                         style=wx.DEFAULT_DIALOG_STYLE | wx.STAY_ON_TOP)

        vbox = wx.BoxSizer(wx.VERTICAL)
        grid = wx.FlexGridSizer(6, 3, 10, 10)
        grid.AddGrowableCol(1, 1)

        self.wire_d_ctrl      = wx.TextCtrl(self, value=str(defaults["wire_d"]))
        self.coil_d_ctrl      = wx.TextCtrl(self, value=str(defaults["coil_d"]))
        self.free_len_ctrl    = wx.TextCtrl(self, value=str(defaults["free_length"]))
        self.num_coils_ctrl   = wx.TextCtrl(self, value=str(defaults["num_coils"]))
        self.clockwise_ctrl   = wx.CheckBox(self, label="Clockwise winding")
        self.clockwise_ctrl.SetValue(defaults["clockwise"])

        self.wire_d_ctrl.SetToolTip("Diameter of the wire (cross-section).")
        self.coil_d_ctrl.SetToolTip("Mean coil diameter (centre of wire to centre of wire across the coil).")
        self.free_len_ctrl.SetToolTip("Free (unloaded) length of the spring.")
        self.num_coils_ctrl.SetToolTip("Number of active coils.")
        self.clockwise_ctrl.SetToolTip("If checked, the helix winds clockwise when viewed from above.")

        grid.AddMany([
            (wx.StaticText(self, label="Wire diameter:")),   (self.wire_d_ctrl,    1, wx.EXPAND), (wx.StaticText(self, label="mm")),
            (wx.StaticText(self, label="Mean coil diameter:")),(self.coil_d_ctrl,  1, wx.EXPAND), (wx.StaticText(self, label="mm")),
            (wx.StaticText(self, label="Free length:")),     (self.free_len_ctrl,  1, wx.EXPAND), (wx.StaticText(self, label="mm")),
            (wx.StaticText(self, label="Active coils:")),    (self.num_coils_ctrl, 1, wx.EXPAND), (wx.StaticText(self, label="")),
            (wx.StaticText(self, label="Winding:")),         (self.clockwise_ctrl, 0),            (wx.StaticText(self, label="")),
            (wx.StaticText(self, label="")),                 (wx.StaticText(self, label="")),     (wx.StaticText(self, label="")),
        ])
        grid.AddGrowableRow(5, 1)
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
        self.Center()

        reset_btn.Bind(wx.EVT_BUTTON, self.on_reset)
        clear_btn.Bind(wx.EVT_BUTTON, self.on_clear)
        self.Bind(wx.EVT_BUTTON, self.on_help, id=wx.ID_HELP)

    def on_reset(self, event):
        d = self.HARDCODED_DEFAULTS
        self.wire_d_ctrl.SetValue(d["wire_d"])
        self.coil_d_ctrl.SetValue(d["coil_d"])
        self.free_len_ctrl.SetValue(d["free_length"])
        self.num_coils_ctrl.SetValue(d["num_coils"])
        self.clockwise_ctrl.SetValue(d["clockwise"])

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
            "SPRING GENERATOR — USER MANUAL\n"
            "==========================================================================\n\n"
            "PARAMETERS\n"
            "----------\n"
            " • Wire Diameter:     Cross-section diameter of the wire in mm.\n\n"
            " • Mean Coil Diameter: Distance across the spring from wire centre to\n"
            "                       wire centre (NOT outer diameter). Standard formula:\n"
            "                       Mean = Outer Diameter − Wire Diameter.\n\n"
            " • Free Length:       The unloaded height of the spring in mm.\n\n"
            " • Active Coils:      Number of load-bearing coils. Does not include\n"
            "                       ground end coils if present.\n\n"
            " • Clockwise:         If checked, the helix winds clockwise when viewed\n"
            "                       from the positive Z direction.\n\n"
            "DERIVED VALUES (calculated automatically)\n"
            "-----------------------------------------\n"
            "  Coil Radius  = Mean Coil Diameter / 2\n"
            "  Pitch        = Free Length / Active Coils\n\n"
            "OUTPUT\n"
            "------\n"
            " A new Part Body is created with the helix, profile plane, and rib.\n"
            " The body is named with the key spring parameters.\n"
        )
        dlg = dialogs.ScrolledMessageDialog(self, help_text, "Help")
        mono = wx.Font(10, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        dlg.text.SetFont(mono)
        dlg.SetSize((600, 500))
        dlg.CenterOnParent()
        dlg.ShowModal()
        dlg.Destroy()

    def Validate(self):
        fields = [
            (self.wire_d_ctrl,    "Wire Diameter",     float),
            (self.coil_d_ctrl,    "Mean Coil Diameter", float),
            (self.free_len_ctrl,  "Free Length",        float),
            (self.num_coils_ctrl, "Active Coils",       float),
        ]
        for ctrl, name, t in fields:
            val_str = ctrl.GetValue().strip()
            try:
                val = t(val_str)
                if val <= 0:
                    wx.MessageBox(f"{name} must be greater than zero.", "Input Error", wx.OK | wx.ICON_ERROR)
                    ctrl.SetFocus()
                    return False
            except ValueError:
                wx.MessageBox(f"{name} must be a valid number.", "Input Error", wx.OK | wx.ICON_ERROR)
                ctrl.SetFocus()
                return False

        wire_d  = float(self.wire_d_ctrl.GetValue())
        coil_d  = float(self.coil_d_ctrl.GetValue())
        if wire_d >= coil_d / 2:
            wx.MessageBox("Wire diameter must be less than the coil radius (Mean Coil Diameter / 2).",
                          "Design Warning", wx.OK | wx.ICON_WARNING)
            return False

        free_len   = float(self.free_len_ctrl.GetValue())
        num_coils  = float(self.num_coils_ctrl.GetValue())
        pitch = free_len / num_coils
        if pitch <= wire_d:
            if wx.MessageBox(f"Pitch ({pitch:.2f}mm) is less than or equal to wire diameter ({wire_d}mm).\n"
                             "Coils will overlap. Proceed anyway?",
                             "Design Warning", wx.YES_NO | wx.ICON_WARNING) == wx.NO:
                return False

        return True

    def get_values(self):
        return {
            "wire_d":      float(self.wire_d_ctrl.GetValue()),
            "coil_d":      float(self.coil_d_ctrl.GetValue()),
            "free_length": float(self.free_len_ctrl.GetValue()),
            "num_coils":   float(self.num_coils_ctrl.GetValue()),
            "clockwise":   self.clockwise_ctrl.IsChecked(),
        }


if __name__ == "__main__":
    SETTINGS_DIR  = os.path.join(os.environ['APPDATA'], 'pycatia_scripts', 'Spring_Generator')
    SETTINGS_FILE = os.path.join(SETTINGS_DIR, 'user_presets.json')
    if not os.path.exists(SETTINGS_DIR):
        os.makedirs(SETTINGS_DIR)

    caa = catia()                                                                                                   #Catia application instance
    app = wx.App()

    if type(caa.active_document) is not PartDocument:
        wx.MessageBox("No active Part document found.\nPlease open a CATPart before running this script.",
                      "Active Document Error", wx.OK | wx.ICON_ERROR)
        exit()

    part_document: PartDocument = caa.active_document
    part = part_document.part

    settings_controller = caa.application.setting_controllers()
    part_infra          = settings_controller.item("CATMmuPartInfrastructureSettingCtrl")
    is_hybrid           = part_infra.com_object.HybridDesignMode
    if is_hybrid:                                                                                                   #Disable hybrid design mode if active
        part_infra.com_object.HybridDesignMode = False

    dlg = SpringDialog(None)
    wx.CallAfter(_bring_to_front, dlg)

    if dlg.ShowModal() != wx.ID_OK:
        dlg.Destroy()
        if is_hybrid:
            part_infra.com_object.HybridDesignMode = True
        exit()

    params = dlg.get_values()

    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump({k: str(v) if not isinstance(v, bool) else v for k, v in params.items()}, f, indent=4)
    except Exception:
        pass

    dlg.Destroy()

    wire_d       = params["wire_d"]
    coil_d       = params["coil_d"]
    free_length  = params["free_length"]
    num_coils    = params["num_coils"]
    clockwise    = params["clockwise"]

    coil_radius  = coil_d / 2.0
    pitch        = free_length / num_coils
    wire_radius  = wire_d / 2.0

    progress = wx.ProgressDialog(
        "Generating Spring", "Initialising...", maximum=7, parent=None,
        style=(wx.PD_APP_MODAL | wx.PD_AUTO_HIDE | wx.PD_SMOOTH | wx.PD_ELAPSED_TIME | wx.PD_REMAINING_TIME)
    )

    hybrid_shape_factory = HybridShapeFactory(part.hybrid_shape_factory.com_object)                               #GSD workbench
    shape_factory        = part.shape_factory                                                                      #Part Design workbench
    bodies               = part.bodies

    try:
        progress.Update(1, "Creating spring body...")

        body = bodies.add()
        body.name = (f"Spring | Wd:{wire_d}mm | Cd:{coil_d}mm | L:{free_length}mm"
                     f" | N:{num_coils} | {'CW' if clockwise else 'CCW'}")
        part.in_work_object = body

        progress.Update(2, "Creating construction geometry...")

        geo_set = part.hybrid_bodies.add()
        geo_set.name = "Spring_Construction"
        part.in_work_object = geo_set

        #Create Z-axis spine line (origin -> top of spring)
        pt_origin = hybrid_shape_factory.add_new_point_coord(0.0, 0.0, 0.0)
        pt_origin.name = "Origin"
        geo_set.append_hybrid_shape(pt_origin)

        pt_top = hybrid_shape_factory.add_new_point_coord(0.0, 0.0, free_length + wire_d)
        pt_top.name = "Z_Top"
        geo_set.append_hybrid_shape(pt_top)

        ref_origin = part.create_reference_from_object(pt_origin)
        ref_top    = part.create_reference_from_object(pt_top)

        z_axis_line = hybrid_shape_factory.add_new_line_pt_pt(ref_origin, ref_top)
        z_axis_line.name = "Z_Axis"
        geo_set.append_hybrid_shape(z_axis_line)
        part.update()

        #Create helix start point at (coil_radius, 0, 0)
        progress.Update(3, "Creating helix...")

        pt_start = hybrid_shape_factory.add_new_point_coord(coil_radius, 0.0, 0.0)
        pt_start.name = "Helix_Start"
        geo_set.append_hybrid_shape(pt_start)
        part.update()

        ref_z_axis = part.create_reference_from_object(z_axis_line)
        ref_start  = part.create_reference_from_object(pt_start)

        helix = hybrid_shape_factory.add_new_helix(
            ref_z_axis,                                                                                            #Axis
            False,                                                                                                 #Do not invert axis direction
            ref_start,                                                                                             #Starting point
            pitch,                                                                                                 #Pitch (mm)
            free_length,                                                                                           #Height (mm)
            clockwise,                                                                                             #Clockwise revolution
            0.0,                                                                                                   #Starting angle
            0.0,                                                                                                   #Taper angle (0 = cylindrical)
            False,                                                                                                 #Taper outward
        )
        helix.name = "Helix"
        geo_set.append_hybrid_shape(helix)
        part.update()

        progress.Update(4, "Creating profile plane...")

        ref_helix = part.create_reference_from_object(helix)
        ref_start2 = part.create_reference_from_object(pt_start)

        profile_plane = hybrid_shape_factory.add_new_plane_normal(ref_helix, ref_start2)                          #Plane normal to helix at start point
        profile_plane.name = "Profile_Plane"
        geo_set.append_hybrid_shape(profile_plane)
        part.update()

        progress.Update(5, "Creating wire cross-section sketch...")

        part.in_work_object = body                                                                                 #Switch back to body for sketch
        ref_plane     = part.create_reference_from_object(profile_plane)
        sketch_plane  = part.origin_elements.com_object                                                           #Needed to access the plane object for sketches

        profile_sketch = body.sketches.add(profile_plane)
        profile_sketch.name = "Wire_Profile"

        ske_2d = profile_sketch.open_edition()

        geo_elements = profile_sketch.geometric_elements
        axis_obj     = geo_elements.item("AbsoluteAxis")
        origin_2d    = profile_sketch.absolute_axis.origin

        wire_circle = ske_2d.create_closed_circle(0.0, 0.0, wire_radius)
        wire_circle.name = "Wire_Cross_Section"

        constraints = profile_sketch.constraints
        cst_conc    = constraints.add_bi_elt_cst(CatConstraintType.catCstTypeConcentricity, wire_circle, origin_2d)
        cst_conc.name = "Wire_Concentric_Origin"
        cst_rad     = constraints.add_mono_elt_cst(CatConstraintType.catCstTypeRadius, wire_circle)
        cst_rad.mode  = CatConstraintMode.catCstModeDrivingDimension
        cst_rad.dimension.value = wire_radius
        cst_rad.name = "Wire_Radius"

        profile_sketch.close_edition()
        part.update()

        progress.Update(6, "Creating rib (sweep) along helix...")

        part.in_work_object = body

        rib = shape_factory.add_new_rib_from_ref(
            part.create_reference_from_object(profile_sketch),
            ref_helix
        )
        rib.name = "Spring_Rib"

        part.update()

        progress.Update(7, "Done.")

        print(f"\n\n Spring generated successfully.")
        print(f"   Wire diameter:  {wire_d} mm")
        print(f"   Coil diameter:  {coil_d} mm  (mean)")
        print(f"   Free length:    {free_length} mm")
        print(f"   Active coils:   {num_coils}")
        print(f"   Pitch:          {pitch:.4f} mm")
        print(f"   Winding:        {'Clockwise' if clockwise else 'Counterclockwise'}")
        print(f"\n\n Completed\n\n")

    except Exception as e:
        progress.Update(7, "Error.")
        import traceback
        wx.MessageBox(
            f"Spring generation failed:\n\n{e}\n\n{traceback.format_exc()}",
            "Error", wx.OK | wx.ICON_ERROR
        )
        print(f"Error: {e}")

    finally:
        if is_hybrid:
            part_infra.com_object.HybridDesignMode = True                                                          #Restore hybrid design mode
