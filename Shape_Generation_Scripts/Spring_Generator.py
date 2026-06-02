'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Spring_Generator.py
    Version:        1.2
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Generate a parametric helical spring in the active CATPart.
    Author:         Kai-Uwe Rathjen
    Date:           21.05.26
    Description:    This script creates a parametric compression spring using CATIA GSD and Part Design.
                    A helix is created along the Z-axis with the specified pitch and height.
                    For open ends, a circular wire cross-section sketch is swept along the helix
                    using a Rib (Part Design).
                    For closed ends, three helices are joined (bottom dead coil, active body, top
                    dead coil) and the solid is built via GSD: the bottom cap circle is swept
                    explicitly along the joined spine (HybridShapeSweepExplicit), end caps are
                    filled (HybridShapeFill), the three surfaces are joined, then converted to a
                    solid (CloseSurface).
                    The resulting body is named with the key parameters. User parameters are
                    persisted between runs. The construction geometric set is placed inside the
                    spring body and hidden after generation.
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

    Change:         02.06.26 1.2: Error handler updated to use ScrolledMessageDialog pattern.
                    1.1 - Construction geo set now created inside the spring body (not at part level).
                          Construction geometry is hidden at the end of generation.
                          Added Closed ends option: three helices joined into a single spine;
                          solid built via GSD explicit sweep (HybridShapeSweepExplicit) + fill
                          caps (HybridShapeFill) + CloseSurface — avoids Rib failure on non-C1
                          joined spine.
                          Dialog widened to 520 px so all buttons are fully visible.

    -----------------------------------------------------------------------------------------------------------------------
'''

#Imports
from pycatia import catia
from pycatia import CatConstraintType, CatConstraintMode
from pycatia.mec_mod_interfaces.part_document import PartDocument
from pycatia.hybrid_shape_interfaces.hybrid_shape_factory import HybridShapeFactory
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


class SpringDialog(wx.Dialog):
    HARDCODED_DEFAULTS = {
        "wire_d":      "3.0",
        "coil_d":      "25.0",
        "free_length": "80.0",
        "num_coils":   "8.0",
        "clockwise":   True,
        "closed_ends": False,
    }

    def __init__(self, parent):
        defaults = self.HARDCODED_DEFAULTS.copy()
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r') as f:
                    defaults.update(json.load(f))
            except Exception:
                pass

        super().__init__(parent, title="Spring Generator", size=(520, 380),
                         style=wx.DEFAULT_DIALOG_STYLE | wx.STAY_ON_TOP)

        vbox = wx.BoxSizer(wx.VERTICAL)
        grid = wx.FlexGridSizer(7, 3, 10, 10)
        grid.AddGrowableCol(1, 1)

        self.wire_d_ctrl      = wx.TextCtrl(self, value=str(defaults["wire_d"]))
        self.coil_d_ctrl      = wx.TextCtrl(self, value=str(defaults["coil_d"]))
        self.free_len_ctrl    = wx.TextCtrl(self, value=str(defaults["free_length"]))
        self.num_coils_ctrl   = wx.TextCtrl(self, value=str(defaults["num_coils"]))
        self.clockwise_ctrl   = wx.CheckBox(self, label="Clockwise winding")
        self.clockwise_ctrl.SetValue(defaults["clockwise"])
        self.closed_ends_ctrl = wx.CheckBox(self, label="Closed (compressed) ends")
        self.closed_ends_ctrl.SetValue(defaults["closed_ends"])

        self.wire_d_ctrl.SetToolTip("Diameter of the wire (cross-section).")
        self.coil_d_ctrl.SetToolTip("Mean coil diameter (centre of wire to centre of wire across the coil).")
        self.free_len_ctrl.SetToolTip("Free (unloaded) length of the spring.")
        self.num_coils_ctrl.SetToolTip("Number of active coils. Does not include the dead end coils.")
        self.clockwise_ctrl.SetToolTip("If checked, the helix winds clockwise when viewed from above.")
        self.closed_ends_ctrl.SetToolTip(
            "Adds one dead coil (pitch = wire diameter, coils touching) at each end. "
            "Three helices are joined: bottom end coil, active body, top end coil. "
            "Free length includes both dead coils."
        )

        grid.AddMany([
            (wx.StaticText(self, label="Wire diameter:")),    (self.wire_d_ctrl,      1, wx.EXPAND), (wx.StaticText(self, label="mm")),
            (wx.StaticText(self, label="Mean coil diameter:")),(self.coil_d_ctrl,      1, wx.EXPAND), (wx.StaticText(self, label="mm")),
            (wx.StaticText(self, label="Free length:")),      (self.free_len_ctrl,    1, wx.EXPAND), (wx.StaticText(self, label="mm")),
            (wx.StaticText(self, label="Active coils:")),     (self.num_coils_ctrl,   1, wx.EXPAND), (wx.StaticText(self, label="")),
            (wx.StaticText(self, label="Winding:")),          (self.clockwise_ctrl,   0),            (wx.StaticText(self, label="")),
            (wx.StaticText(self, label="Ends:")),             (self.closed_ends_ctrl, 0),            (wx.StaticText(self, label="")),
            (wx.StaticText(self, label="")),                  (wx.StaticText(self, label="")),       (wx.StaticText(self, label="")),
        ])
        grid.AddGrowableRow(6, 1)
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
        self.closed_ends_ctrl.SetValue(d["closed_ends"])

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
            " • Free Length:       The unloaded height of the spring in mm.\n"
            "                       Includes dead end coils when Closed Ends is on.\n\n"
            " • Active Coils:      Number of load-bearing coils. Does not include the\n"
            "                       dead end coils added by the Closed Ends option.\n\n"
            " • Clockwise:         If checked, the helix winds clockwise when viewed\n"
            "                       from the positive Z direction.\n\n"
            " • Closed Ends:       Adds one dead coil at each end (pitch = wire diameter,\n"
            "                       coils touching) to model a closed compression spring.\n"
            "                       Three helices are joined: bottom dead coil, active body,\n"
            "                       top dead coil. Free length must be > 2 × wire diameter.\n\n"
            "DERIVED VALUES (calculated automatically)\n"
            "-----------------------------------------\n"
            "  Coil Radius     = Mean Coil Diameter / 2\n"
            "  Pitch (open)    = Free Length / Active Coils\n"
            "  Pitch (closed)  = (Free Length − 2 × Wire Diameter) / Active Coils\n"
            "  End coil pitch  = Wire Diameter (touching coils, closed ends only)\n\n"
            "OUTPUT\n"
            "------\n"
            " A new Part Body is created with the spring solid.\n"
            " The construction geometry (helix spine, profile plane) is stored in a\n"
            " geo set inside the body and hidden automatically after generation.\n"
        )
        dlg = dialogs.ScrolledMessageDialog(self, help_text, "Help")
        mono = wx.Font(10, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        dlg.text.SetFont(mono)
        dlg.SetSize((620, 540))
        dlg.CenterOnParent()
        dlg.ShowModal()
        dlg.Destroy()

    def Validate(self):
        fields = [
            (self.wire_d_ctrl,    "Wire Diameter",      float),
            (self.coil_d_ctrl,    "Mean Coil Diameter", float),
            (self.free_len_ctrl,  "Free Length",         float),
            (self.num_coils_ctrl, "Active Coils",        float),
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

        wire_d = float(self.wire_d_ctrl.GetValue())
        coil_d = float(self.coil_d_ctrl.GetValue())
        if wire_d >= coil_d / 2:
            wx.MessageBox("Wire diameter must be less than the coil radius (Mean Coil Diameter / 2).",
                          "Design Warning", wx.OK | wx.ICON_WARNING)
            return False

        free_len  = float(self.free_len_ctrl.GetValue())
        num_coils = float(self.num_coils_ctrl.GetValue())

        if self.closed_ends_ctrl.IsChecked():
            main_height = free_len - 2.0 * wire_d
            if main_height <= 0.0:
                wx.MessageBox(
                    f"With closed ends, main body height = Free length − 2 × Wire diameter = "
                    f"{main_height:.2f} mm.\nIncrease free length or reduce wire diameter.",
                    "Design Error", wx.OK | wx.ICON_ERROR)
                return False
            main_pitch = main_height / num_coils
            if main_pitch <= wire_d:
                if wx.MessageBox(
                        f"Main coil pitch ({main_pitch:.2f} mm) ≤ wire diameter ({wire_d} mm).\n"
                        "Active coils will overlap. Proceed anyway?",
                        "Design Warning", wx.YES_NO | wx.ICON_WARNING) == wx.NO:
                    return False
        else:
            pitch = free_len / num_coils
            if pitch <= wire_d:
                if wx.MessageBox(
                        f"Pitch ({pitch:.2f} mm) ≤ wire diameter ({wire_d} mm).\n"
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
            "closed_ends": self.closed_ends_ctrl.IsChecked(),
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

    wire_d      = params["wire_d"]
    coil_d      = params["coil_d"]
    free_length = params["free_length"]
    num_coils   = params["num_coils"]
    clockwise   = params["clockwise"]
    closed_ends = params["closed_ends"]

    coil_radius = coil_d / 2.0
    wire_radius = wire_d / 2.0

    max_steps = 12 if closed_ends else 7

    progress = wx.ProgressDialog(
        "Generating Spring", "Initialising...", maximum=max_steps, parent=None,
        style=(wx.PD_APP_MODAL | wx.PD_AUTO_HIDE | wx.PD_SMOOTH | wx.PD_ELAPSED_TIME | wx.PD_REMAINING_TIME)
    )

    hybrid_shape_factory = HybridShapeFactory(part.hybrid_shape_factory.com_object)                               #GSD workbench
    shape_factory        = part.shape_factory                                                                      #Part Design workbench
    bodies               = part.bodies

    try:
        step = 0

        step += 1
        progress.Update(step, "Creating spring body...")

        body = bodies.add()
        closed_label = " | Closed Ends" if closed_ends else ""
        body.name = (f"Spring | Wd:{wire_d}mm | Cd:{coil_d}mm | L:{free_length}mm"
                     f" | N:{num_coils} | {'CW' if clockwise else 'CCW'}{closed_label}")
        part.in_work_object = body

        geo_set = body.hybrid_bodies.add()                                                                         #Construction geo set inside the body
        geo_set.name = "Spring_Construction"
        part.in_work_object = geo_set

        step += 1
        progress.Update(step, "Creating construction geometry...")

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

        ref_z_axis = part.create_reference_from_object(z_axis_line)

        # ------------------------------------------------------------------ #
        #  Helix construction — branches on closed_ends                       #
        # ------------------------------------------------------------------ #

        if closed_ends:
            end_height  = wire_d                                                                                   #One dead coil per end, pitch = wire_d (coils touching)
            main_height = free_length - 2.0 * end_height
            main_pitch  = main_height / num_coils

            step += 1
            progress.Update(step, "Creating bottom end helix...")

            pt_start = hybrid_shape_factory.add_new_point_coord(coil_radius, 0.0, 0.0)
            pt_start.name = "Helix_Start"
            geo_set.append_hybrid_shape(pt_start)

            #After 1 full turn the start point is back at the same XY, up by end_height
            pt_main_start = hybrid_shape_factory.add_new_point_coord(coil_radius, 0.0, end_height)
            pt_main_start.name = "Main_Helix_Start"
            geo_set.append_hybrid_shape(pt_main_start)

            #After num_coils turns from pt_main_start, compute the XY landing position
            frac   = num_coils % 1.0
            y_sign = -1.0 if clockwise else 1.0
            x_top_start = coil_radius * math.cos(frac * 2.0 * math.pi)
            y_top_start = y_sign * coil_radius * math.sin(frac * 2.0 * math.pi)

            pt_top_start = hybrid_shape_factory.add_new_point_coord(x_top_start, y_top_start, end_height + main_height)
            pt_top_start.name = "Top_Helix_Start"
            geo_set.append_hybrid_shape(pt_top_start)
            part.update()

            ref_start      = part.create_reference_from_object(pt_start)
            ref_main_start = part.create_reference_from_object(pt_main_start)
            ref_top_start  = part.create_reference_from_object(pt_top_start)

            helix_bottom = hybrid_shape_factory.add_new_helix(
                ref_z_axis, False, ref_start, wire_d, end_height, clockwise, 0.0, 0.0, False)
            helix_bottom.name = "Helix_Bottom_End"
            geo_set.append_hybrid_shape(helix_bottom)

            step += 1
            progress.Update(step, "Creating main body helix...")

            helix_main = hybrid_shape_factory.add_new_helix(
                ref_z_axis, False, ref_main_start, main_pitch, main_height, clockwise, 0.0, 0.0, False)
            helix_main.name = "Helix_Main"
            geo_set.append_hybrid_shape(helix_main)

            step += 1
            progress.Update(step, "Creating top end helix...")

            helix_top = hybrid_shape_factory.add_new_helix(
                ref_z_axis, False, ref_top_start, wire_d, end_height, clockwise, 0.0, 0.0, False)
            helix_top.name = "Helix_Top_End"
            geo_set.append_hybrid_shape(helix_top)
            part.update()

            step += 1
            progress.Update(step, "Joining helices...")

            helix_join = hybrid_shape_factory.add_new_join(
                part.create_reference_from_object(helix_bottom),
                part.create_reference_from_object(helix_main),
            )
            helix_join.add_element(part.create_reference_from_object(helix_top))
            helix_join.name = "Helix_Join"
            geo_set.append_hybrid_shape(helix_join)
            part.update()

            ref_spine = part.create_reference_from_object(helix_join)

        else:
            pitch = free_length / num_coils

            step += 1
            progress.Update(step, "Creating helix...")

            pt_start = hybrid_shape_factory.add_new_point_coord(coil_radius, 0.0, 0.0)
            pt_start.name = "Helix_Start"
            geo_set.append_hybrid_shape(pt_start)
            part.update()

            ref_start = part.create_reference_from_object(pt_start)

            helix = hybrid_shape_factory.add_new_helix(
                ref_z_axis, False, ref_start, pitch, free_length, clockwise, 0.0, 0.0, False)
            helix.name = "Helix"
            geo_set.append_hybrid_shape(helix)
            part.update()

            ref_spine          = part.create_reference_from_object(helix)
            ref_profile_origin = part.create_reference_from_object(pt_start)

        # ------------------------------------------------------------------ #
        #  Solid geometry — branches on closed_ends                           #
        # ------------------------------------------------------------------ #

        if not closed_ends:
            step += 1
            progress.Update(step, "Creating profile plane...")

            profile_plane = hybrid_shape_factory.add_new_plane_normal(ref_spine, ref_profile_origin)
            profile_plane.name = "Profile_Plane"
            geo_set.append_hybrid_shape(profile_plane)
            part.update()

            step += 1
            progress.Update(step, "Creating wire cross-section sketch...")

            part.in_work_object = body

            profile_sketch = body.sketches.add(profile_plane)
            profile_sketch.name = "Wire_Profile"

            ske_2d      = profile_sketch.open_edition()
            origin_2d   = profile_sketch.absolute_axis.origin

            wire_circle = ske_2d.create_closed_circle(0.0, 0.0, wire_radius)
            wire_circle.name = "Wire_Cross_Section"

            constraints = profile_sketch.constraints
            cst_conc    = constraints.add_bi_elt_cst(CatConstraintType.catCstTypeConcentricity, wire_circle, origin_2d)
            cst_conc.name = "Wire_Concentric_Origin"
            cst_rad       = constraints.add_mono_elt_cst(CatConstraintType.catCstTypeRadius, wire_circle)
            cst_rad.mode  = CatConstraintMode.catCstModeDrivingDimension
            cst_rad.dimension.value = wire_radius
            cst_rad.name  = "Wire_Radius"

            profile_sketch.close_edition()
            part.update()

            step += 1
            progress.Update(step, "Creating rib (sweep) along helix...")

            part.in_work_object = body

            rib = shape_factory.add_new_rib_from_ref(
                part.create_reference_from_object(profile_sketch),
                ref_spine,
            )
            rib.name = "Spring_Rib"
            part.update()

        else:
            # ---- end cap planes + circles ---- #
            step += 1
            progress.Update(step, "Creating end cap geometry...")

            # End of top helix: same XY as top_start, Z = free_length (after 1 full revolution)
            pt_top_end = hybrid_shape_factory.add_new_point_coord(x_top_start, y_top_start, free_length)
            pt_top_end.name = "Top_Helix_End"
            geo_set.append_hybrid_shape(pt_top_end)
            ref_pt_top_end = part.create_reference_from_object(pt_top_end)

            plane_bot = hybrid_shape_factory.add_new_plane_normal(ref_spine, ref_start)
            plane_bot.name = "Plane_Bot_Cap"
            geo_set.append_hybrid_shape(plane_bot)

            plane_top = hybrid_shape_factory.add_new_plane_normal(ref_spine, ref_pt_top_end)
            plane_top.name = "Plane_Top_Cap"
            geo_set.append_hybrid_shape(plane_top)
            part.update()

            circle_bot = hybrid_shape_factory.add_new_circle_ctr_rad(
                ref_start,
                part.create_reference_from_object(plane_bot),
                False,
                wire_radius,
            )
            circle_bot.name = "Circle_Bot_Cap"
            geo_set.append_hybrid_shape(circle_bot)

            circle_top = hybrid_shape_factory.add_new_circle_ctr_rad(
                ref_pt_top_end,
                part.create_reference_from_object(plane_top),
                False,
                wire_radius,
            )
            circle_top.name = "Circle_Top_Cap"
            geo_set.append_hybrid_shape(circle_top)
            part.update()

            # ---- tubular sweep surface ---- #
            step += 1
            progress.Update(step, "Creating sweep surface...")

            sweep = hybrid_shape_factory.add_new_sweep_explicit(
                part.create_reference_from_object(circle_bot),
                ref_spine,
            )
            sweep.smooth_activity = False
            sweep.name = "Spring_Tube"
            geo_set.append_hybrid_shape(sweep)
            part.update()

            # ---- end cap fills ---- #
            step += 1
            progress.Update(step, "Creating end cap fills...")

            fill_bot = hybrid_shape_factory.add_new_fill()
            fill_bot.add_bound(part.create_reference_from_object(circle_bot))
            fill_bot.name = "Fill_Bot_Cap"
            geo_set.append_hybrid_shape(fill_bot)

            fill_top = hybrid_shape_factory.add_new_fill()
            fill_top.add_bound(part.create_reference_from_object(circle_top))
            fill_top.name = "Fill_Top_Cap"
            geo_set.append_hybrid_shape(fill_top)
            part.update()

            # ---- join tube + caps into closed surface ---- #
            step += 1
            progress.Update(step, "Joining surfaces...")

            surface_join = hybrid_shape_factory.add_new_join(
                part.create_reference_from_object(sweep),
                part.create_reference_from_object(fill_bot),
            )
            surface_join.add_element(part.create_reference_from_object(fill_top))
            surface_join.name = "Spring_Surface"
            geo_set.append_hybrid_shape(surface_join)
            part.update()

            # ---- close surface → solid ---- #
            step += 1
            progress.Update(step, "Closing surface to solid...")

            part.in_work_object = body
            close_solid = shape_factory.add_new_close_surface(
                part.create_reference_from_object(surface_join)
            )
            close_solid.name = "Spring_Solid"
            part.update()

        step += 1
        progress.Update(step, "Hiding construction geometry...")

        selection = caa.active_document.selection
        selection.clear()
        selection.add(geo_set)
        selection.vis_properties.set_show(CatVisPropertyShow.catVisPropertyNoShowAttr)
        selection.clear()

        if closed_ends:
            main_pitch_display = (free_length - 2.0 * wire_d) / num_coils
            print("\n\n Spring generated successfully (closed ends).")
            print(f"   Wire diameter:    {wire_d} mm")
            print(f"   Coil diameter:    {coil_d} mm  (mean)")
            print(f"   Free length:      {free_length} mm")
            print(f"   Active coils:     {num_coils}")
            print(f"   Main pitch:       {main_pitch_display:.4f} mm")
            print(f"   End coil pitch:   {wire_d} mm  (touching)")
            print(f"   Winding:          {'Clockwise' if clockwise else 'Counterclockwise'}")
        else:
            print("\n\n Spring generated successfully.")
            print(f"   Wire diameter:  {wire_d} mm")
            print(f"   Coil diameter:  {coil_d} mm  (mean)")
            print(f"   Free length:    {free_length} mm")
            print(f"   Active coils:   {num_coils}")
            print(f"   Pitch:          {free_length / num_coils:.4f} mm")
            print(f"   Winding:        {'Clockwise' if clockwise else 'Counterclockwise'}")

        print("\n\n Completed\n\n")

    except Exception as e:
        full_traceback = traceback.format_exc()
        print(full_traceback)
        progress.Update(max_steps, "Error.")
        error_msg = (
            f"Error Summary: {str(e)}\n"
            f"------------------------------------------\n"
            f"Technical Debug Info:\n\n{full_traceback}"
        )
        e_dlg = dialogs.ScrolledMessageDialog(None, error_msg, "Script Error")
        error_icon  = wx.ArtProvider.GetBitmap(wx.ART_ERROR, wx.ART_MESSAGE_BOX)
        icon_bitmap = wx.StaticBitmap(e_dlg, wx.ID_ANY, error_icon)
        header_text = wx.StaticText(e_dlg, label="An error occurred during spring generation:")
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
        if is_hybrid:
            part_infra.com_object.HybridDesignMode = True                                                          #Restore hybrid design mode
