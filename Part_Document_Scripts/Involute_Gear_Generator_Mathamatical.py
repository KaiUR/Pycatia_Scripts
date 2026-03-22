'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Involute_Gear_Generator_Mathamatical.py
    Version:        1.0
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Create Involute Gear
    Author:         Kai-Uwe Rathjen
    Date:           03.03.26
    Description:    This script will ask the user for parameters to create spur gear profile
    dependencies = [
                    "pycatia",
                    "wxPython",
                    ]
    requirements:   Python >= 9.10
                    pycatia
                    Catia V5 running with an open part.
                    This script needs an open part document.
                    Hybrid desgin should be disabled.
    -----------------------------------------------------------------------------------------------------------------------
    
    Change:
    
    -----------------------------------------------------------------------------------------------------------------------
'''

#Imports
from pycatia import catia
from pycatia.mec_mod_interfaces.part_document import PartDocument
from pycatia import CatConstraintType
from pycatia import CatConstraintMode
from pycatia import CatPrismOrientation
from pycatia import CatLimitMode
import math
import wx
from pycatia.in_interfaces.setting_controllers import SettingControllers

class DataInputDialog(wx.Dialog):
    def __init__(self, parent, title):
        super().__init__(parent, title=title, size=(350, 500))                                          #Set size of dialog
        
        vbox = wx.BoxSizer(wx.VERTICAL)                                                                 #Use the Dialog itself as the parent for the sizer
        
        grid = wx.FlexGridSizer(12, 2, 10, 10)                                                          #Set grid for fields
        
        self.module = wx.TextCtrl(self, value="2.0")                                                    #Initilize field with default value
        self.number_of_teeth = wx.TextCtrl(self, value="20")                                            #Initilize field with default value
        self.pressure_angle = wx.TextCtrl(self, value="20.0")                                           #Initilize field with default value
        self.clearance = wx.TextCtrl(self, value="0.25")                                                #Initilize field with default value
        self.steps = wx.TextCtrl(self, value="10")                                                      #Initilize field with default value
        self.gear_thicness = wx.TextCtrl(self, value="5.0")                                             #Initilize field with default value
        self.fillet_radius = wx.TextCtrl(self, value="0.38")                                            #Initilize field with default value
        self.shaft_radius = wx.TextCtrl(self, value="5.0")                                              #Initilize field with default value
        self.key_w = wx.TextCtrl(self, value="4.0")                                                     #Initilize field with default value
        self.key_d = wx.TextCtrl(self, value="8.0")                                                     #Initilize field with default value
        self.has_shaft = wx.CheckBox(self, label="Include Shaft Hole")                                  #Initilize field lable
        self.has_shaft.SetValue(True)                                                                   #Initilize field with default value
        self.has_keyway = wx.CheckBox(self, label="Include Keyway")                                     #Initilize field lable
        self.has_keyway.SetValue(True)                                                                  #Initilize field with default value

        self.has_shaft.Bind(wx.EVT_CHECKBOX, self.on_toggle_shaft)                                      #bind event function
        self.has_keyway.Bind(wx.EVT_CHECKBOX, self.on_toggle_keyway)                                    #bind event function
        
        grid.AddMany([
            (wx.StaticText(self, label="Module:")), (self.module, 1, wx.EXPAND),
            (wx.StaticText(self, label="Number of Teeth:")), (self.number_of_teeth, 1, wx.EXPAND),
            (wx.StaticText(self, label="Preasure Angle:")), (self.pressure_angle, 1, wx.EXPAND),
            (wx.StaticText(self, label="Clearance:")), (self.clearance, 1, wx.EXPAND),
            (wx.StaticText(self, label="Steps:")), (self.steps, 1, wx.EXPAND),
            (wx.StaticText(self, label="Gear Thicness:")), (self.gear_thicness, 1, wx.EXPAND),
            (wx.StaticText(self, label="Fillet Radius:")), (self.fillet_radius, 1, wx.EXPAND),
            (wx.StaticText(self, label="Shaft Setting:")), (self.has_shaft, 0),
            (wx.StaticText(self, label="Shaft Radius:")), (self.shaft_radius, 1, wx.EXPAND),
            (wx.StaticText(self, label="Keyway Setting:")), (self.has_keyway, 0),
            (wx.StaticText(self, label="Key Width Ratio:")), (self.key_w, 1, wx.EXPAND),
            (wx.StaticText(self, label="Key Depth Ratio:")), (self.key_d, 1, wx.EXPAND)
        ])                                                                                              #Create layout for dialog
        
        grid.AddGrowableCol(1, 1)                                                                       #Set cloum
        
        vbox.Add(grid, proportion=1, flag=wx.ALL|wx.EXPAND, border=15)                                  #Add grid border
        
        btn_sizer = self.CreateButtonSizer(wx.OK | wx.CANCEL)                                           #Create ok and cancel button
        if btn_sizer:
            vbox.Add(btn_sizer, flag=wx.ALIGN_CENTER | wx.BOTTOM, border=10)
        
        self.SetSizer(vbox)
        
    def on_toggle_shaft(self, event):
        """Enable/Disable shaft input based on checkbox."""
        state = self.has_shaft.IsChecked()
        self.shaft_radius.Enable(state)
        # If no shaft, there can't be a keyway
        self.has_keyway.Enable(state)
        if not state:
            self.has_keyway.SetValue(False)
            self.key_w.Enable(False)
            self.key_d.Enable(False)
        
    def on_toggle_keyway(self, event):
        """Enable/Disable keyway inputs based on checkbox."""
        state = self.has_keyway.IsChecked()
        self.key_w.Enable(state)
        self.key_d.Enable(state)
    
    def Validate(self):
        fields = [
            (self.module, "Module", float),
            (self.number_of_teeth, "Number of Teeth", int),
            (self.pressure_angle, "Pressure Angle", float),
            (self.clearance, "Clearance", float),
            (self.steps, "Steps", int),
            (self.gear_thicness, "Gear Thickness", float),
            (self.fillet_radius, "Fillet Radius", float),
            (self.shaft_radius, "Shaft Radius", float),
            (self.key_w, "Key Width Ratio", float),
            (self.key_d, "Key Depth Ratio", float)
        ]
        
        if self.has_shaft.IsChecked():
            fields.append((self.shaft_radius, "Shaft Radius", float))
        
        if self.has_keyway.IsChecked():
            fields.append((self.key_w, "Key Width Ratio", float))
            fields.append((self.key_d, "Key Depth Ratio", float))

        for ctrl, name, target_type in fields:
            val_string = ctrl.GetValue().strip()
            
            try:
                # Convert the value first
                val_numeric = target_type(val_string)
                
                # CHECK FOR ZERO OR NEGATIVE
                if val_numeric <= 0:
                    self.show_error(f"{name} must be greater than zero.", ctrl)
                    return False
                    
            except ValueError:
                self.show_error(f"{name} must be a valid {target_type.__name__}.", ctrl)
                return False
        
        return True # Everything is positive and numeric

    def show_error(self, message, ctrl):
        """Helper to show a message box and focus the problematic field."""
        wx.MessageBox(message, "Input Error", wx.OK | wx.ICON_ERROR)
        ctrl.SetFocus()
        ctrl.SelectAll()

if __name__ == "__main__":
    #Anchoring relavent components
    caa = catia()                                                                                               #Catia application instance
    if type(caa.active_document) is not PartDocument:                                                           #Check if part document
        print("Script can only be use with Open PartDocument")                                                  #Print error message
        exit()                                                                                                  #Exith script
    part_document: PartDocument = caa.active_document                                                           #Current open document
    part = part_document.part                                                                                   #Current part
    hybrid_bodies = part.hybrid_bodies                                                                          #Set off all top level geometric sets 
    bodies = part.bodies                                                                                        #Get collection of bodies
    hybrid_shape_factory = part.hybrid_shape_factory                                                            #GSD workbentch to create hybridshapes
    shape_factory = part.shape_factory                                                                          #Part Design workbench
    selectionSet = caa.active_document.selection                                                                #Create container for selection
    
    #Parameters
    pad_tol = 0.02                                                                                              #Tol added to ensure that the pads are all joined
    
    settings_controller = caa.application.setting_controllers()                                                 #Get catia settings
    part_infa = settings_controller.item("CATMmuPartInfrastructureSettingCtrl")                                 #Get part infastructure setting

    is_hybrid = part_infa.com_object.HybridDesignMode                                                           #Get hybrid design mode as boolean
    return_hybrid = False                                                                                       #Set return setting flag to false

    if is_hybrid:                                                                                               #If hybrid design is enabled
        part_infa.com_object.HybridDesignMode = False                                                           #Turn off hybrid design
        return_hybrid = True                                                                                    #Set flag to turn on hybrid design again at end of script
    
    app = wx.App()
    dlg = DataInputDialog(None, "Involute Gear Parameters")                                                     #New dialog to get user parameters
    if dlg.ShowModal() == wx.ID_OK:                                                                             #If user input is valid and user pressed ok
        module = float(dlg.module.GetValue())                                                                   #Get value form dialog
        number_of_teeth = int(dlg.number_of_teeth.GetValue())                                                   #Get value form dialog
        pressure_angle = float(dlg.pressure_angle.GetValue())                                                   #Get value form dialog
        clearance = float(dlg.clearance.GetValue())                                                             #Get value form dialog
        clearance = clearance + 1                                                                               #+1 to make maths work later
        steps = int(dlg.steps.GetValue())                                                                       #Get value form dialog
        gear_thicness = float(dlg.gear_thicness.GetValue())                                                     #Get value form dialog
        fillet_radius = float(dlg.fillet_radius.GetValue())                                                     #Get value form dialog
        shaft_radius = float(dlg.shaft_radius.GetValue())                                                       #Get value form dialog
        key_d = float(dlg.key_d.GetValue())                                                                     #Get value form dialog
        key_w = float(dlg.key_w.GetValue())                                                                     #Get value form dialog
        has_shaft = dlg.has_shaft.GetValue()                                                                    #Get value form dialog
        has_key = dlg.has_keyway.GetValue()                                                                     #Get value form dialog
    else:                                                                                                       #User canceled or something whent wrong
        dlg.Destroy()                                                                                           #Close dialog
        exit()                                                                                                  #exit script
    dlg.Destroy()                                                                                               #Close dialog
    
    partbody = bodies.add()                                                                                     #Add new body
    sketches_part_body = partbody.sketches                                                                      #Get sketches in part body
    
    #formulas
    pitch_circle_radius = module * number_of_teeth                                                              #Pitch circle formula
    addendum_circle_radius = pitch_circle_radius + module                                                       #Addendum circle formula
    dedendum_circle_radius = pitch_circle_radius - ( clearance * module )                                       #Dedendum circle formula
    base_circle_radius = pitch_circle_radius * math.cos(math.radians(pressure_angle))                           #base circle formula
    
    #Body and Sketch Con
    partbody.name = "Involute Gear M:" + str(module) + " T:" + str(number_of_teeth)                             #Rename body
    part.in_work_object = partbody                                                                              #Make new body inwork object
    hb_sketches = partbody.sketches                                                                             #Get Collection of sketches
    plane_XY = part.origin_elements.plane_xy                                                                    #get reference to XY plane

    #create sketch for tooth on xy plane
    sketch_tooth_con = hb_sketches.add(plane_XY)                                                                #Add sketch                                    
    sketch_tooth_con.name = "sketch_tooth_con"                                                                  #Rename Sketch
    ske2D_tooth_con = sketch_tooth_con.open_edition()                                                           #Start Editing Sketch
    constraints = sketch_tooth_con.constraints                                                                  #Get collection of constraints for sketch
    geo_elements = sketch_tooth_con.geometric_elements                                                          #Get collection of geometric elements for sketch
    axis = geo_elements.item("AbsoluteAxis")                                                                    #Get Sketch Axis
    h_axis = axis.get_item("HDirection")                                                                        #Get H direction
    v_axis = axis.get_item("VDirection")                                                                        #Get V direction
    origin = sketch_tooth_con.absolute_axis.origin                                                              #Get origin
   
    #create pitch circle
    pitch_circle = ske2D_tooth_con.create_closed_circle(0, 0, pitch_circle_radius)                              #Draw new circle
    pitch_circle.construction = True                                                                            #Make construction element
    pitch_circle.name = "Pitch Circle"                                                                          #Rename
    constraints.add_bi_elt_cst(CatConstraintType.catCstTypeConcentricity, pitch_circle, origin)                 #Make concentric to origin
    cnst_rad_pitch = constraints.add_mono_elt_cst(CatConstraintType.catCstTypeRadius, pitch_circle)             #Add radius constraint
    cnst_rad_pitch.mode = CatConstraintMode.catCstModeDrivingDimension                                          #Set to driving dimension
    cnst_rad_pitch.dimension.value = pitch_circle_radius                                                        #Set dimension
    
    #create addendum circle
    addendum_circle = ske2D_tooth_con.create_closed_circle(0, 0, addendum_circle_radius)                        #Draw circle
    addendum_circle.construction = True                                                                         #Make construction element
    addendum_circle.name = "Addendum/Tip Circle"                                                                #Rename
    constraints.add_bi_elt_cst(CatConstraintType.catCstTypeConcentricity, 
            addendum_circle, origin)                                                                            #Make concentric to origin
    cnst_rad_addendum = constraints.add_mono_elt_cst(CatConstraintType.catCstTypeRadius, 
            addendum_circle)                                                                                    #Add radius constraint
    cnst_rad_addendum.mode = CatConstraintMode.catCstModeDrivingDimension                                       #Make driving dimension
    cnst_rad_addendum.dimension.value = addendum_circle_radius                                                  #Set dimension
    
    #create dedendum circle
    dedendum_circle = ske2D_tooth_con.create_closed_circle(0, 0, dedendum_circle_radius)                        #Draw circle
    dedendum_circle.construction = True                                                                         #Set to construction element
    dedendum_circle.name = "Dedendum/Root Circle"                                                               #Rename
    constraints.add_bi_elt_cst(CatConstraintType.catCstTypeConcentricity, dedendum_circle, origin)              #Make concentric to origin
    cnst_rad_dedendum = constraints.add_mono_elt_cst(CatConstraintType.catCstTypeRadius, 
            dedendum_circle)                                                                                    #Add radius constraint
    cnst_rad_dedendum.mode = CatConstraintMode.catCstModeDrivingDimension                                       #Make driving dimension
    cnst_rad_dedendum.dimension.value = dedendum_circle_radius                                                  #Set radius
    
    #Create centre line
    center_line_origin = (0, 0)                                                                                 #Start point of line
    center_line_end_point = (0, addendum_circle_radius)                                                         #End point of line
    
    center_line = ske2D_tooth_con.create_line(*center_line_origin, *center_line_end_point)                      #Draw line
    center_line.construction = True                                                                             #Set to construction
    center_line.name = "Center_line"                                                                            #Rename
    
    center_line_start_point = ske2D_tooth_con.create_point(0, 0)                                                #Create point for start point of line
    center_line_start_point.name = "center line start point"                                                    #Rename
    center_line.start_point = center_line_start_point                                                           #Set as start point
    center_line_end_point = ske2D_tooth_con.create_point(0, addendum_circle_radius)                             #Create end point for line
    center_line_end_point.name = "center line end point"                                                        #Rename
    center_line.end_point = center_line_end_point                                                               #Set as endpoint
    
    center_line_par = constraints.add_bi_elt_cst(CatConstraintType.catCstTypeParallelism, 
            center_line, v_axis)                                                                                #Make line vertical
    center_line_on_1 = constraints.add_bi_elt_cst(CatConstraintType.catCstTypeOn, 
            center_line_start_point, origin)                                                                    #Make start point coincident to origin
    center_line_on_2 = constraints.add_bi_elt_cst(CatConstraintType.catCstTypeOn, 
            center_line_end_point, addendum_circle)                                                             #Make end point coincident to addendum circle
    
    #create preasure angle line
    pressure_line = ske2D_tooth_con.create_line(0, 0, 10, 10)                                                   #Draw line
    pressure_line.construction = True                                                                           #Make construction element
    pressure_line.name = "Pressure_Line"                                                                        #Rename
    
    pressure_line_start_point = ske2D_tooth_con.create_point(0, 0)                                              #Create start point for line
    pressure_line_start_point.name = "pressure line start point"                                                #Rename
    pressure_line.start_point = pressure_line_start_point                                                       #Set as start point of line
    
    pressure_line_end_point = ske2D_tooth_con.create_point(10, 10)                                              #Create end-point for line
    pressure_line_end_point.name = "pressure line end point"                                                    #Rename
    pressure_line.end_point = pressure_line_end_point                                                           #Set as endpoint of line
    
    pressure_line_on_1 = constraints.add_bi_elt_cst(CatConstraintType.catCstTypeOn, 
            pressure_line_start_point, origin)                                                                  #Make start point coincident to origin
    
    pressure_line_angle_cst = constraints.add_bi_elt_cst(CatConstraintType.catCstTypeAngle, 
            pressure_line, center_line)                                                                         #Add new angle constraint
    pressure_line_angle_cst.mode = CatConstraintMode.catCstModeDrivingDimension                                 #Make driving dimension
    pressure_line_angle_cst.dimension.value = pressure_angle                                                    #Set angle
    
    pressure_line_on_2 = constraints.add_bi_elt_cst(CatConstraintType.catCstTypeOn, 
            pressure_line_end_point, addendum_circle)                                                           #Make endpoint coincident to addendum circle
    
    #Create Base circle
    base_circle = ske2D_tooth_con.create_closed_circle(0, 0, base_circle_radius)                                #Draw circle
    base_circle.construction = True                                                                             #Make construction
    base_circle.name = "Base Circle"                                                                            #Rename
    constraints.add_bi_elt_cst(CatConstraintType.catCstTypeConcentricity, base_circle, origin)                  #Make concentric to origin
    cnst_rad_base_circle = constraints.add_mono_elt_cst(CatConstraintType.catCstTypeRadius, 
            base_circle)                                                                                        #Add radius dimension
    cnst_rad_base_circle.mode = CatConstraintMode.catCstModeDrivingDimension                                    #Make driving dimension
    cnst_rad_base_circle.dimension.value = base_circle_radius                                                   #set radius
    
    
    #Calculate invalute flank
    max_t = math.sqrt(((addendum_circle_radius) / base_circle_radius)**2 - 1)                                   #Calculate maximum parameter value in radians
    
    inv_alpha = math.tan(math.radians(pressure_angle)) - math.radians(pressure_angle)                           #Involute function involute(alpha)
    half_tooth_thickness_angle = (math.pi / (2 * number_of_teeth)) + inv_alpha                                  #Half tooth thinkness
    
    points_list_left = []                                                                                       #Colection of left involute points
    points_list_right = []                                                                                      #Collection of right involute points

    for i in range(steps + 1):                                                                                  #Calculate involute point acording to number of steps
        t = (max_t / steps) * i                                                                                 #Calculate t parameter for this step
        x_current = base_circle_radius * (math.sin(t) - t * math.cos(t))                                        #Caluclate raw x involute from base circle
        y_current = base_circle_radius * (math.cos(t) + t * math.sin(t))                                        #Calculate raw y involute from base circle
        
        angle = half_tooth_thickness_angle                                                                      #Set angle
        x_l = x_current * math.cos(angle) - y_current * math.sin(angle)                                         #Rotate x to account for tooth thikness
        y_l = x_current * math.sin(angle) + y_current * math.cos(angle)                                         #Rotate y to account for tooth thikness
        
        point_l = ske2D_tooth_con.create_point(x_l, y_l)                                                        #Create left flank involute point for this step
        point_l.name = f"Involute_Point__Left_{i}"                                                              #Rename point
        constraints.add_mono_elt_cst(CatConstraintType.catCstTypeReference, point_l)                            #Add fixed constraint
        points_list_left.append(point_l)                                                                        #Add to list
        
        point_r = ske2D_tooth_con.create_point(-x_l, y_l)                                                       #Create right flank involute point for this step
        point_r.name = f"Involute_Point__Right_{i}"                                                             #Rename point
        constraints.add_mono_elt_cst(CatConstraintType.catCstTypeReference, point_r)                            #Create fixed constraint
        points_list_right.append(point_r)                                                                       #Add to list

    involute_flank_left = ske2D_tooth_con.create_spline(points_list_left)                                       #Create left involute flank spline
    involute_flank_left.name = "Involute_Flank_Left"                                                            #Rename spline
    
    involute_flank_right = ske2D_tooth_con.create_spline(points_list_right)                                     #Create right involute flank spline
    involute_flank_right.name = "Involute_Flank_right"                                                          #Rename spline
    
    #Create top land
    p_top_left = points_list_left[-1]                                                                           #Get first point of list (Outermost involute point)
    p_top_right = points_list_right[-1]                                                                         #Get first point of list (Outermost involute point)
    
    p_top_left_coord = p_top_left.get_coordinates()                                                             #Get coordinates of point for top land boundary
    p_top_right_coord = p_top_right.get_coordinates()                                                           #Get coordinates of point for top land boundary

    angle_l = math.atan2(p_top_left_coord[1], p_top_left_coord[0])                                              #Calculate polar angle in radians for arc span start
    angle_r = math.atan2(p_top_right_coord[1], p_top_right_coord[0])                                            #Calculate polar angle in radians for arc span end

    top_land = ske2D_tooth_con.create_circle(0, 0, addendum_circle_radius, angle_r, angle_l)                    #Create top land arc on addendum circle
    top_land.name = "Top_Land"                                                                                  #Rename arc
    
    top_land_start_point = ske2D_tooth_con.create_point(p_top_right_coord[0], p_top_right_coord[1])             #Create start point for arc
    top_land_start_point.name = "top_land start point"                                                          #Rename
    top_land.start_point = top_land_start_point                                                                 #Set as start point
    
    top_land_end_point = ske2D_tooth_con.create_point(p_top_left_coord[0], p_top_left_coord[1])                 #Create end point for arc
    top_land_end_point.name = "top_land end point"                                                              #Rename
    top_land.end_point = top_land_end_point                                                                     #Set as endpoint

    top_land_on_1 = constraints.add_bi_elt_cst(CatConstraintType.catCstTypeOn, 
            top_land_start_point, p_top_right)                                                                  #Make coincedent to right involute spline
    top_land_on_2 = constraints.add_bi_elt_cst(CatConstraintType.catCstTypeOn, 
            top_land_end_point, p_top_left)                                                                     #Make coincedent to left involute spline
    
    cnst_rad_top_land = constraints.add_mono_elt_cst(CatConstraintType.catCstTypeRadius, top_land)              #Add radius constraint to arc
    cnst_rad_top_land.mode = CatConstraintMode.catCstModeDrivingDimension                                       #Make driving dimmension
    cnst_rad_top_land.dimension.value = addendum_circle_radius                                                  #Set radius
    
    #Create root fillets 
    if base_circle_radius > dedendum_circle_radius:                                                             #Only run if the base circle is larger than the dedendum (requires a transition curve)
        # Get the first point of the involute (where it touches the base circle)
        p_start_involute = points_list_left[0]
        x_s, y_s = p_start_involute.get_coordinates()
        
        # Calculate standard fillet radius based on gear module
        r_f = fillet_radius * module
        
        # Determine the start height of the fillet relative to the dedendum
        r_fillet_start = dedendum_circle_radius + r_f
        angle_s = math.atan2(y_s, x_s)
        
        # Calculate coordinates for where the radial line meets the fillet
        x_f_start = r_fillet_start * math.cos(angle_s)
        y_f_start = r_fillet_start * math.sin(angle_s)
        
        # ---left fillet and line---
        # Create a line connecting the involute start to the fillet start
        radial_line_left = ske2D_tooth_con.create_line(x_s, y_s, x_f_start, y_f_start)
        radial_line_left.name = "Radial_Line_Left"
        
        # Define endpoints for the left radial line
        radial_line_left_start_point = ske2D_tooth_con.create_point(x_s, y_s)
        radial_line_left_start_point.name = "radial_line_left start point"
        radial_line_left.start_point = radial_line_left_start_point
 
        radial_line_left_end_point = ske2D_tooth_con.create_point(x_f_start, y_f_start)
        radial_line_left_end_point.name = "radial_line_left end point"
        radial_line_left.end_point = radial_line_left_end_point  

        # Constrain the line to be coincident with the involute and tangent to the flank
        radial_line_on_1 = constraints.add_bi_elt_cst(CatConstraintType.catCstTypeOn, radial_line_left_start_point, points_list_left[0])
        radial_line_tangnt = constraints.add_bi_elt_cst(CatConstraintType.catCstTypeTangency, radial_line_left, involute_flank_left )
        constraints.add_mono_elt_cst(CatConstraintType.catCstTypeReference, radial_line_left_end_point)

        # Calculate the center point (cx, cy) of the left fillet arc
        angle_perp = angle_s + (math.pi / 2)
        cx = x_f_start + r_f * math.cos(angle_perp)
        cy = y_f_start + r_f * math.sin(angle_perp)
        
        # Determine start and end angles for the fillet arc
        a1 = math.atan2(y_f_start - cy, x_f_start - cx)
        a2 = math.atan2(-cy, -cx)
        
        # Create the left root fillet arc
        fillet_left = ske2D_tooth_con.create_circle(cx, cy, r_f, a2, a1)
        fillet_left.name = "Root_Fillet_Left"
 
        # Define endpoints for the left fillet arc
        fillet_left_end_point = ske2D_tooth_con.create_point(x_f_start, y_f_start)
        fillet_left_end_point.name = "fillet_left end point"
        fillet_left.end_point = fillet_left_end_point
    
        fillet_left_start_point = ske2D_tooth_con.create_point(r_f * math.cos(a2), r_f * math.sin(a2))
        fillet_left_start_point.name = "fillet_left start point"
        fillet_left.start_point = fillet_left_start_point

        # Constrain the fillet to the radial line and set its radius dimension
        fillet_left_on_1 = constraints.add_bi_elt_cst(CatConstraintType.catCstTypeOn, fillet_left_end_point, radial_line_left_end_point)
        constraints.add_mono_elt_cst(CatConstraintType.catCstTypeReference, fillet_left_start_point) 
        cnst_rad_fillet_left = constraints.add_mono_elt_cst(CatConstraintType.catCstTypeRadius, fillet_left)
        cnst_rad_fillet_left.mode = CatConstraintMode.catCstModeDrivingDimension
        cnst_rad_fillet_left.dimension.value = r_f
        
        # ---Right fillet and line---
        # Create a mirrored radial line for the right side of the tooth      
        radial_line_right = ske2D_tooth_con.create_line(-x_s, y_s, -x_f_start, y_f_start)
        radial_line_right.name = "Radial_Line_Right"
        
        # Define endpoints for the right radial line
        radial_line_right_start_point = ske2D_tooth_con.create_point(-x_s, y_s)
        radial_line_right_start_point.name = "radial_line_right start point"
        radial_line_right.start_point = radial_line_right_start_point
    
        radial_line_right_end_point = ske2D_tooth_con.create_point(-x_f_start, y_f_start)
        radial_line_right_end_point.name = "radial_line_right end point"
        radial_line_right.end_point = radial_line_right_end_point  

        # Constrain the line to be coincident with the involute and tangent to the flank
        radial_line_on_1 = constraints.add_bi_elt_cst(CatConstraintType.catCstTypeOn, radial_line_right_start_point, points_list_right[0])
        radial_line_tangnt = constraints.add_bi_elt_cst(CatConstraintType.catCstTypeTangency, radial_line_right, involute_flank_right )
        constraints.add_mono_elt_cst(CatConstraintType.catCstTypeReference, radial_line_right_end_point)
        
        # Calculate the mirrored center point and angles for the right fillet
        cx_r, cy_r = -cx, cy
        a1_r = math.atan2(y_f_start - cy_r, -x_f_start - cx_r)
        a2_r = math.atan2(-cy_r, -cx_r)
        
        # Create the right root fillet arc
        fillet_right = ske2D_tooth_con.create_circle(cx_r, cy_r, r_f, a1_r, a2_r)
        fillet_right.name = "Root_Fillet_Right"
        
        # Define and constrain the right fillet endpoints
        fillet_right_start_point = ske2D_tooth_con.create_point(-x_f_start, y_f_start)
        fillet_right_start_point.name = "fillet_right start point"
        fillet_right.start_point = fillet_right_start_point
    
        fillet_right_end_point = ske2D_tooth_con.create_point(r_f * math.cos(a2_r), r_f * math.sin(a2_r))
        fillet_right_end_point.name = "fillet_right end point"
        fillet_right.end_point = fillet_right_end_point

        # Finalize constraints and radius for the right fillet
        fillet_right_on_1 = constraints.add_bi_elt_cst(CatConstraintType.catCstTypeOn, fillet_right_start_point, radial_line_right_end_point)
        constraints.add_mono_elt_cst(CatConstraintType.catCstTypeReference, fillet_right_end_point) 
        cnst_rad_fillet_right = constraints.add_mono_elt_cst(CatConstraintType.catCstTypeRadius, fillet_right)
        cnst_rad_fillet_right.mode = CatConstraintMode.catCstModeDrivingDimension
        cnst_rad_fillet_right.dimension.value = r_f
        
    else:
        # Base circle is inside or on the dedendum circle
        # No radial line needed; fillet attaches directly to the start of the involute
        p_start_left = points_list_left[0]
        x_s, y_s = p_start_left.get_coordinates()
        
        r_f = 0.38 * module
        angle_s = math.atan2(y_s, x_s)
        
        # Center of the left fillet
        # We place it so it's tangent to the start point and reaches the dedendum circle
        angle_perp = angle_s + (math.pi / 2)
        cx = x_s + r_f * math.cos(angle_perp)
        cy = y_s + r_f * math.sin(angle_perp)
        
        # Angles for the arc (from dedendum circle to involute start)
        a1 = math.atan2(y_s - cy, x_s - cx)
        a2 = math.atan2(-cy, -cx)
        
        # Create Left Fillet
        fillet_left = ske2D_tooth_con.create_circle(cx, cy, r_f, a2, a1)
        fillet_left.name = "Root_Fillet_Left"
        
        fillet_left_end_point = ske2D_tooth_con.create_point(x_s, y_s)
        fillet_left.end_point = fillet_left_end_point
        constraints.add_bi_elt_cst(CatConstraintType.catCstTypeOn, fillet_left_end_point, p_start_left)
        
        fillet_left_start_point = ske2D_tooth_con.create_point(r_f * math.cos(a2), r_f * math.sin(a2))
        fillet_left.start_point = fillet_left_start_point
        
        # Add Radius Constraint
        cnst_rad_l = constraints.add_mono_elt_cst(CatConstraintType.catCstTypeRadius, fillet_left)
        cnst_rad_l.dimension.value = r_f

        # Create Right Fillet (Mirror of left)
        cx_r, cy_r = -cx, cy
        a1_r = math.atan2(y_s - cy_r, -x_s - cx_r)
        a2_r = math.atan2(-cy_r, -cx_r)
        
        fillet_right = ske2D_tooth_con.create_circle(cx_r, cy_r, r_f, a1_r, a2_r)
        fillet_right.name = "Root_Fillet_Right"
        
        fillet_right_start_point = ske2D_tooth_con.create_point(-x_s, y_s)
        fillet_right.start_point = fillet_right_start_point
        constraints.add_bi_elt_cst(CatConstraintType.catCstTypeOn, fillet_right_start_point, points_list_right[0])
        
        fillet_right_end_point = ske2D_tooth_con.create_point(r_f * math.cos(a2_r), r_f * math.sin(a2_r))
        fillet_right.end_point = fillet_right_end_point
        
        cnst_rad_r = constraints.add_mono_elt_cst(CatConstraintType.catCstTypeRadius, fillet_right)
        cnst_rad_r.dimension.value = r_f

    #Add the root of tooth
    angle_root_l = (math.atan2(cy, -cx) + 2 * math.pi) % (2 * math.pi)                                  #Calculate the normalized angles (0 to 2π) for the left and root point
    angle_root_r = (math.atan2(cy_r, -cx_r) + 2 * math.pi) % (2 * math.pi)                              #Calculate the normalized angles (0 to 2π) for the right and root point
    
    root_arc = ske2D_tooth_con.create_circle(0, 0, dedendum_circle_radius, angle_root_l, angle_root_r)  #Create the arc representing the bottom of the tooth space on the dedendum circle
    root_arc.name = "Tooth_Root_Arc"                                                                    #Rename arc
 
    root_r_coords = fillet_right_end_point.get_coordinates()                                            #Get the junction coordinates from the end of the right fillet
 
    root_arc_start_point = ske2D_tooth_con.create_point(root_r_coords[0], root_r_coords[1])             #Starting point for the root arc (right side)     
    root_arc_start_point.name = "root_arc start point"                                                  #Rename point
    root_arc.start_point = root_arc_start_point                                                         #Set as start point of arc
    
    root_l_coords = fillet_left_start_point.get_coordinates()                                           #Get the junction coordinates from the start of the left fillet

    root_arc_end_point = ske2D_tooth_con.create_point(root_l_coords[0], root_l_coords[1])               #End point for the root arc (left side)
    root_arc_end_point.name = "root_arc end point"                                                      #Rename point
    root_arc.end_point = root_arc_end_point                                                             #Set as endpoint of arc

    root_arc_on_1 = constraints.add_bi_elt_cst(CatConstraintType.catCstTypeOn,
            root_arc_start_point, fillet_right_end_point)                                               #Make coincedent to root arc
    root_arc_on_2 = constraints.add_bi_elt_cst(CatConstraintType.catCstTypeOn,
            root_arc_end_point, fillet_left_start_point)                                                #Make coincedent to root arc
    constraints.add_bi_elt_cst(CatConstraintType.catCstTypeConcentricity, root_arc, origin)             #Make concentric to origin
    
    #Close edition
    sketch_tooth_con.close_edition()                                                                    #Stop editing sketch
    part.update()                                                                                       #Update part
    
    #create sketch for gear body on xy plane
    sketch_body_con = hb_sketches.add(plane_XY)                                                         #Create sketch on xy plane
    sketch_body_con.name = "sketch_body_con"                                                            #Rename sketch
    ske2D_body_con = sketch_body_con.open_edition()                                                     #Start editing sketch
    constraints_body = sketch_body_con.constraints                                                      #Get sketch constraints
    geo_elements_bdy = sketch_body_con.geometric_elements                                               #Get sketch geometric elements
    axis = geo_elements_bdy.item("AbsoluteAxis")                                                        #Get sketch axis
    h_axis = axis.get_item("HDirection")                                                                #Get H direction
    v_axis = axis.get_item("VDirection")                                                                #Get V direction
    
    origin = sketch_body_con.absolute_axis.origin                                                       #Get origin
   
    #create pitch circle
    gear_circle = ske2D_body_con.create_closed_circle(0, 0, dedendum_circle_radius + pad_tol)           #Draw circle
    gear_circle.name = "Pitch Circle"                                                                   #Rename circle
    constraints_body.add_bi_elt_cst(CatConstraintType.catCstTypeConcentricity, 
            gear_circle, origin)                                                                        #Make concentric to origin
    cnst_gear = constraints_body.add_mono_elt_cst(CatConstraintType.catCstTypeRadius, 
            gear_circle)                                                                                #Add radius constraint
    cnst_gear.mode = CatConstraintMode.catCstModeDrivingDimension                                       #Make driving dimmension
    cnst_gear.dimension.value = dedendum_circle_radius + pad_tol                                        #Add radius (pad_tol is to make sure their are no gaps when creating the gear)
    
    #Close edition
    sketch_body_con.close_edition()                                                                     #Stop editing the sketch
    part.update()                                                                                       #Update the part
    
    #Create pad for gear body
    pad_body = shape_factory.add_new_pad(sketch_body_con, gear_thicness)                                #Add new pad for gear body
    pad_body.direction_orientation = CatPrismOrientation.catRegularOrientation                          #Set direction
    pad_body.first_limit.limit_mode = CatLimitMode.catOffsetLimit                                       #Set limit mode to offset
    pad_body.first_limit.dimension.value = gear_thicness                                                #Set pad dimmension
    pad_body.name = "Gear Body"                                                                         #Rename pad
    pad_body.set_profile_element(part.create_reference_from_object(sketch_body_con))                    #Link sketch to pad
    
    part.update()                                                                                       #Update part
    
    #Create pad for geart tooth
    pad_tooth = shape_factory.add_new_pad(sketch_tooth_con, gear_thicness)                              #Add new pad for gear tooth
    pad_tooth.direction_orientation = CatPrismOrientation.catRegularOrientation                         #Set direction
    pad_tooth.first_limit.limit_mode = CatLimitMode.catOffsetLimit                                      #Set limit mode to offset
    pad_tooth.first_limit.dimension.value = gear_thicness                                               #Set pad dimmension
    pad_tooth.name = "Gear Tooth"                                                                       #Rename pad
    pad_tooth.set_profile_element(part.create_reference_from_object(sketch_tooth_con))                  #Link sketch to pad
    
    part.update()                                                                                       #Update part
    
    # Create Circular Pattern for remaining gear teeth
    ref_axis = part.create_reference_from_object(plane_XY)                                              #Rotation axis
    ref_origin = part.create_reference_from_object(origin)                                              #Origin point
    
    circ_pattern = shape_factory.add_new_circ_pattern(
        pad_tooth,                                                                                      # 1. Feature to copy
        1,                                                                                              # 2. Radial instances
        number_of_teeth,                                                                                # 3. Angular instances
        0.0,                                                                                            # 4. Radial step
        360.0/number_of_teeth,                                                                          # 5. Angular step
        1,                                                                                              # 6. Radial position
        1,                                                                                              # 7. Angular position
        ref_origin,                                                                                     # 8. Rotation center reference
        ref_axis,                                                                                       # 9. Rotation axis reference
        False,                                                                                          # 10. Is reversed?
        0.0,                                                                                            # 11. Rotation angle
        True                                                                                            # 12. Is radius aligned?
    )
    
    circ_pattern.name = "Teeth"                                                                         #Rename pattern
    
    part.update()                                                                                       #Update part
    
    if has_shaft:
        #Create shaft hole
        shaft_hole = shape_factory.add_new_hole_from_point(0, 0, 0, plane_XY, gear_thicness)                #Create a new Hole feature

        shaft_hole.diameter.value = shaft_radius * 2                                                        #Set the diameter of the hole
        shaft_hole.bottom_type = 1                                                                          #Set to through all (Up to last)
        shaft_hole.reverse()                                                                                #Reverse the direction 0,0,-1
        shaft_hole.name = "Shaft_Hole"                                                                      #Rename hole feature
        shaft_hole.sketch.name = "Shaft Hole Con"                                                           #Rename sketch made by hole feature
        
        selectionSet.clear()                                                                                #Clear selection
        selectionSet.add(shaft_hole.sketch)                                                                 #Add hole feature sketch to selection
        selectionSet.vis_properties.set_show(1)                                                             #Hide selecton
        selectionSet.clear()                                                                                #Clear selection

        part.update()                                                                                       #Update part
        
        if has_key:
            #create sketch for key way on xy plane
            sketch_key_con = hb_sketches.add(plane_XY)                                                          #Create sketch on xy plane
            sketch_key_con.name = "sketch_key_con"                                                              #Rename sketch
            ske2D_key_con = sketch_key_con.open_edition()                                                       #Start editing sketch
            constraints_key = sketch_key_con.constraints                                                        #Get sketch constraints
            geo_elements_ky = sketch_key_con.geometric_elements                                                 #Get sketch geometric elements
            axis_k = geo_elements_ky.item("AbsoluteAxis")                                                       #Get sketch axis
            h_axis = axis_k.get_item("HDirection")                                                              #Get H direction
            v_axis = axis_k.get_item("VDirection")                                                              #Get V direction
            
            origin_k = sketch_key_con.absolute_axis.origin                                                      #Get origin
            
            kw_width = (shaft_radius * 2) / key_w                                                               #Calculate key width, shaft diameter divided by ratio
            kw_depth = (shaft_radius * 2) / key_d                                                               #Calculate key depth, shaft diameter divided by ratio
            
            y_start_inside = 0                                                                                  #Start at origin
            y_end = shaft_radius + kw_depth                                                                     #Depth, key depth + shaft radius
            x_left = -(kw_width / 2)                                                                            #Left Start point
            x_right = kw_width / 2                                                                              #Right end point

            line1 = ske2D_key_con.create_line(x_left, y_start_inside, x_right, y_start_inside)                  # Bottom
            line2 = ske2D_key_con.create_line(x_right, y_start_inside, x_right, y_end)                          # Right
            line3 = ske2D_key_con.create_line(x_right, y_end, x_left, y_end)                                    # Top
            line4 = ske2D_key_con.create_line(x_left, y_end, x_left, y_start_inside)                            # Left
            
            line1.name = "Line_1"                                                                               #Rename line
            line2.name = "Line_2"                                                                               #Rename line
            line3.name = "Line_3"                                                                               #Rename line
            line4.name = "Line_4"                                                                               #Rename line
            
            line1_sp = ske2D_key_con.create_point(x_left, y_start_inside)                                       #Create start point for line
            line1_sp.name = "line1_sp"                                                                          #Rename point
            line1.start_point = line1_sp                                                                        #Set point to line
            constraints_key.add_mono_elt_cst(CatConstraintType.catCstTypeReference, line1_sp)                   #Add fixed constraint
            
            line1_ep = ske2D_key_con.create_point(x_right, y_start_inside)                                      #Create end point for line
            line1_ep.name = "line1_ep"                                                                          #Rename point
            line1.end_point = line1_ep                                                                          #Set point to line
            constraints_key.add_mono_elt_cst(CatConstraintType.catCstTypeReference, line1_ep)                   #Add fixed constraint
            
            line2_sp = ske2D_key_con.create_point(x_right, y_start_inside)                                      #Create start point for line
            line2_sp.name = "line2_sp"                                                                          #Rename point
            line2.start_point = line2_sp                                                                        #Set point to line
            constraints_key.add_mono_elt_cst(CatConstraintType.catCstTypeReference, line2_sp)                   #Add fixed constraint
            
            line2_ep = ske2D_key_con.create_point(x_right, y_end)                                               #Create end point for line
            line2_ep.name = "line2_ep"                                                                          #Rename point
            line2.end_point = line2_ep                                                                          #Set point to line
            constraints_key.add_mono_elt_cst(CatConstraintType.catCstTypeReference, line2_ep)                   #Add fixed constraint
            
            line3_sp = ske2D_key_con.create_point(x_right, y_end)                                               #Create start point for line
            line3_sp.name = "line3_sp"                                                                          #Rename point
            line3.start_point = line3_sp                                                                        #Set point to line
            constraints_key.add_mono_elt_cst(CatConstraintType.catCstTypeReference, line3_sp)                   #Add fixed constraint
            
            line3_ep = ske2D_key_con.create_point(x_left, y_end)                                                #Create end point for line
            line3_ep.name = "line3_ep"                                                                          #Rename point
            line3.end_point = line3_ep                                                                          #Set point to line
            constraints_key.add_mono_elt_cst(CatConstraintType.catCstTypeReference, line3_ep)                   #Add fixed constraint
            
            line4_sp = ske2D_key_con.create_point(x_left, y_end)                                                #Create start point for line 
            line4_sp.name = "line4_sp"                                                                          #Rename point
            line4.start_point = line4_sp                                                                        #Set point to line
            constraints_key.add_mono_elt_cst(CatConstraintType.catCstTypeReference, line4_sp)                   #Add fixed constraint
            
            line4_ep = ske2D_key_con.create_point(x_left, y_start_inside)                                       #Create end point for line
            line4_ep.name = "line4_ep"                                                                          #Rename point
            line4.end_point = line4_ep                                                                          #Set point to line
            constraints_key.add_mono_elt_cst(CatConstraintType.catCstTypeReference, line4_ep)                   #Add fixed constraint

            sketch_key_con.close_edition()                                                                      #Close sketch
            
            #Create key pocket
            keyway_pocket = shape_factory.add_new_pocket(sketch_key_con, gear_thicness)                         #Add new pocket feature

            keyway_pocket.first_limit.limit_mode = CatLimitMode.catOffsetLimit                                  #Set limit mode to offset
            keyway_pocket.direction_orientation = CatPrismOrientation.catRegularOrientation                     #Set orientation
            keyway_pocket.name = "Key Pocket"                                                                   #Rename pocket
            keyway_pocket.set_profile_element(part.create_reference_from_object(sketch_key_con))                #Add scketch to feature as reference

            part.update()                                                                                       #Update part
    
    if return_hybrid:                                                                                           #If hybrid desgin was turned off
        part_infa.com_object.HybridDesignMode = True                                                            #Turn hybrid desgin back on