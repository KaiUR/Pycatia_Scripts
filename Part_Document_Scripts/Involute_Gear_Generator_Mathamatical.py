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
                    ]
    requirements:   Python >= 9.10
                    pycatia
                    Catia V5 running with an open part.
                    This script needs an open part document.
    -----------------------------------------------------------------------------------------------------------------------
    
    Change:
    
    -----------------------------------------------------------------------------------------------------------------------
'''

#Imports
from pycatia import catia
from pycatia.mec_mod_interfaces.part_document import PartDocument
from pycatia.enumeration.enumeration_types import cat_constraint_type
from pycatia.enumeration.enumeration_types import cat_constraint_mode
from pycatia.enumeration.enumeration_types import cat_prism_orientation
from pycatia.enumeration.enumeration_types import cat_limit_mode 
import math

if __name__ == "__main__":
    #Anchoring relavent components
    caa = catia()                                                                                               #Catia application instance
    part_document: PartDocument = caa.active_document                                                           #Current open document
    part = part_document.part                                                                                   #Current part
    hybrid_bodies = part.hybrid_bodies                                                                          #Set off all top level geometric sets 
    bodies = part.bodies                                                                                        #Get collection of bodies
    partbody = bodies.add()                                                                                     #Add new body
    sketches_part_body = partbody.sketches                                                                      #Get sketches in part body
    hybrid_shape_factory = part.hybrid_shape_factory                                                            #GSD workbentch to create hybridshapes
    shape_factory = part.shape_factory                                                                          #Part Design workbench
    selectionSet = caa.active_document.selection                                                                #Create container for selection
    
    #Parameters
    module = 2
    number_of_teeth = 10 
    clearance = 1.25
    pressure_angle = 25
    steps = 10
    gear_thicness = 5
    pad_tol = 0.02
    
    #formulas
    pitch_circle_radius = module * number_of_teeth
    addendum_circle_radius = pitch_circle_radius + module
    dedendum_circle_radius = pitch_circle_radius - ( clearance * module )
    base_circle_radius = pitch_circle_radius * math.cos(math.radians(pressure_angle))
    
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
    pitch_circle = ske2D_tooth_con.create_closed_circle(0, 0, pitch_circle_radius)
    pitch_circle.construction = True
    pitch_circle.name = "Pitch Circle"
    constraints.add_bi_elt_cst(cat_constraint_type.index("catCstTypeConcentricity"), pitch_circle, origin)
    cnst_rad_pitch = constraints.add_mono_elt_cst(cat_constraint_type.index("catCstTypeRadius"), pitch_circle)
    cnst_rad_pitch.mode = cat_constraint_mode.index("catCstModeDrivingDimension")
    cnst_rad_pitch.dimension.value = pitch_circle_radius
    
    #create addendum circle
    addendum_circle = ske2D_tooth_con.create_closed_circle(0, 0, addendum_circle_radius)
    addendum_circle.construction = True
    addendum_circle.name = "Addendum/Tip Circle"
    constraints.add_bi_elt_cst(cat_constraint_type.index("catCstTypeConcentricity"), addendum_circle, origin)
    cnst_rad_addendum = constraints.add_mono_elt_cst(cat_constraint_type.index("catCstTypeRadius"), addendum_circle)
    cnst_rad_addendum.mode = cat_constraint_mode.index("catCstModeDrivingDimension")
    cnst_rad_addendum.dimension.value = addendum_circle_radius
    
    #create dedendum circle
    dedendum_circle = ske2D_tooth_con.create_closed_circle(0, 0, dedendum_circle_radius)
    dedendum_circle.construction = True
    dedendum_circle.name = "Dedendum/Root Circle"
    constraints.add_bi_elt_cst(cat_constraint_type.index("catCstTypeConcentricity"), dedendum_circle, origin)
    cnst_rad_dedendum = constraints.add_mono_elt_cst(cat_constraint_type.index("catCstTypeRadius"), dedendum_circle)
    cnst_rad_dedendum.mode = cat_constraint_mode.index("catCstModeDrivingDimension")
    cnst_rad_dedendum.dimension.value = dedendum_circle_radius
    
    #Create centre line
    center_line_origin = (0, 0)
    center_line_end_point = (0, addendum_circle_radius)
    
    center_line = ske2D_tooth_con.create_line(*center_line_origin, *center_line_end_point)
    center_line.construction = True
    center_line.name = "Center_line"
    
    center_line_start_point = ske2D_tooth_con.create_point(0, 0)
    center_line_start_point.name = "center line start point"
    center_line.start_point = center_line_start_point
    center_line_end_point = ske2D_tooth_con.create_point(0, addendum_circle_radius)
    center_line_end_point.name = "center line end point"
    center_line.end_point = center_line_end_point
    
    center_line_par = constraints.add_bi_elt_cst(cat_constraint_type.index("catCstTypeParallelism"), center_line, v_axis)

    center_line_on_1 = constraints.add_bi_elt_cst(cat_constraint_type.index("catCstTypeOn"), center_line_start_point, origin)
    center_line_on_2 = constraints.add_bi_elt_cst(cat_constraint_type.index("catCstTypeOn"), center_line_end_point, addendum_circle)
    
    #create preasure angle line
    pressure_line = ske2D_tooth_con.create_line(0, 0, 10, 10)
    pressure_line.construction = True
    pressure_line.name = "Pressure_Line"
    
    pressure_line_start_point = ske2D_tooth_con.create_point(0, 0)
    pressure_line_start_point.name = "pressure line start point"
    pressure_line.start_point = pressure_line_start_point
    
    pressure_line_end_point = ske2D_tooth_con.create_point(10, 10)
    pressure_line_end_point.name = "pressure line end point"
    pressure_line.end_point = pressure_line_end_point
    
    pressure_line_on_1 = constraints.add_bi_elt_cst(cat_constraint_type.index("catCstTypeOn"), pressure_line_start_point, origin)
    
    pressure_line_angle_cst = constraints.add_bi_elt_cst(6, pressure_line, center_line)
    pressure_line_angle_cst.mode = cat_constraint_mode.index("catCstModeDrivingDimension")
    pressure_line_angle_cst.dimension.value = pressure_angle
    
    pressure_line_on_2 = constraints.add_bi_elt_cst(cat_constraint_type.index("catCstTypeOn"), pressure_line_end_point, addendum_circle)
    
    #Create Base circle
    base_circle = ske2D_tooth_con.create_closed_circle(0, 0, base_circle_radius)
    base_circle.construction = True
    base_circle.name = "Base Circle"
    constraints.add_bi_elt_cst(cat_constraint_type.index("catCstTypeConcentricity"), base_circle, origin)
    cnst_rad_base_circle = constraints.add_mono_elt_cst(cat_constraint_type.index("catCstTypeRadius"), base_circle)
    cnst_rad_base_circle.mode = cat_constraint_mode.index("catCstModeDrivingDimension")
    cnst_rad_base_circle.dimension.value = base_circle_radius
    
    
    #Calculate invalute flank
    max_t = math.sqrt(((addendum_circle_radius) / base_circle_radius)**2 - 1)
    
    inv_alpha = math.tan(math.radians(pressure_angle)) - math.radians(pressure_angle)
    half_tooth_thickness_angle = (math.pi / (2 * number_of_teeth)) + inv_alpha
    
    points_list_left = []
    points_list_right = []

    for i in range(steps + 1):
        t = (max_t / steps) * i
        x_current = base_circle_radius * (math.sin(t) - t * math.cos(t))
        y_current = base_circle_radius * (math.cos(t) + t * math.sin(t))
        
        angle = half_tooth_thickness_angle
        x_l = x_current * math.cos(angle) - y_current * math.sin(angle)
        y_l = x_current * math.sin(angle) + y_current * math.cos(angle)
        
        point_l = ske2D_tooth_con.create_point(x_l, y_l)
        point_l.name = f"Involute_Point__Left_{i}"
        constraints.add_mono_elt_cst(cat_constraint_type.index("catCstTypeReference"), point_l)
        points_list_left.append(point_l)
        
        point_r = ske2D_tooth_con.create_point(-x_l, y_l)
        point_r.name = f"Involute_Point__Right_{i}"
        constraints.add_mono_elt_cst(cat_constraint_type.index("catCstTypeReference"), point_r)
        points_list_right.append(point_r)

    involute_flank_left = ske2D_tooth_con.create_spline(points_list_left)
    involute_flank_left.name = "Involute_Flank_Left"
    
    involute_flank_right = ske2D_tooth_con.create_spline(points_list_right)
    involute_flank_right.name = "Involute_Flank_right"
    
    #Create top land
    p_top_left = points_list_left[-1]
    p_top_right = points_list_right[-1]
    
    p_top_left_coord = p_top_left.get_coordinates()
    p_top_right_coord = p_top_right.get_coordinates()

    angle_l = math.atan2(p_top_left_coord[1], p_top_left_coord[0])
    angle_r = math.atan2(p_top_right_coord[1], p_top_right_coord[0])

    top_land = ske2D_tooth_con.create_circle(0, 0, addendum_circle_radius, angle_r, angle_l)
    top_land.name = "Top_Land"
    
    top_land_start_point = ske2D_tooth_con.create_point(p_top_right_coord[0], p_top_right_coord[1])
    top_land_start_point.name = "top_land start point"
    top_land.start_point = top_land_start_point
    
    top_land_end_point = ske2D_tooth_con.create_point(p_top_left_coord[0], p_top_left_coord[1])
    top_land_end_point.name = "top_land end point"
    top_land.end_point = top_land_end_point    

    top_land_on_1 = constraints.add_bi_elt_cst(cat_constraint_type.index("catCstTypeOn"), top_land_start_point, p_top_right)
    top_land_on_2 = constraints.add_bi_elt_cst(cat_constraint_type.index("catCstTypeOn"), top_land_end_point, p_top_left)
    
    cnst_rad_top_land = constraints.add_mono_elt_cst(cat_constraint_type.index("catCstTypeRadius"), top_land)
    cnst_rad_top_land.mode = cat_constraint_mode.index("catCstModeDrivingDimension")
    cnst_rad_top_land.dimension.value = addendum_circle_radius
    
    #Create root fillets 
    if base_circle_radius > dedendum_circle_radius:
        p_start_involute = points_list_left[0]
        x_s, y_s = p_start_involute.get_coordinates()
        
        r_f = 0.38 * module
        
        r_fillet_start = dedendum_circle_radius + r_f
        angle_s = math.atan2(y_s, x_s)
        
        x_f_start = r_fillet_start * math.cos(angle_s)
        y_f_start = r_fillet_start * math.sin(angle_s)
        
        #left fillet and line
        radial_line_left = ske2D_tooth_con.create_line(x_s, y_s, x_f_start, y_f_start)
        radial_line_left.name = "Radial_Line_Left"
        
        radial_line_left_start_point = ske2D_tooth_con.create_point(x_s, y_s)
        radial_line_left_start_point.name = "radial_line_left start point"
        radial_line_left.start_point = radial_line_left_start_point
    
        radial_line_left_end_point = ske2D_tooth_con.create_point(x_f_start, y_f_start)
        radial_line_left_end_point.name = "radial_line_left end point"
        radial_line_left.end_point = radial_line_left_end_point  

        radial_line_on_1 = constraints.add_bi_elt_cst(cat_constraint_type.index("catCstTypeOn"), radial_line_left_start_point, points_list_left[0])
        radial_line_tangnt = constraints.add_bi_elt_cst(cat_constraint_type.index("catCstTypeTangency"), radial_line_left, involute_flank_left )
        constraints.add_mono_elt_cst(cat_constraint_type.index("catCstTypeReference"), radial_line_left_end_point)

        angle_perp = angle_s + (math.pi / 2)
        
        cx = x_f_start + r_f * math.cos(angle_perp)
        cy = y_f_start + r_f * math.sin(angle_perp)
        
        a1 = math.atan2(y_f_start - cy, x_f_start - cx)
        a2 = math.atan2(-cy, -cx)
        
        fillet_left = ske2D_tooth_con.create_circle(cx, cy, r_f, a2, a1)
        fillet_left.name = "Root_Fillet_Left"
 
        fillet_left_end_point = ske2D_tooth_con.create_point(x_f_start, y_f_start)
        fillet_left_end_point.name = "fillet_left end point"
        fillet_left.end_point = fillet_left_end_point
    
        fillet_left_start_point = ske2D_tooth_con.create_point(r_f * math.cos(a2), r_f * math.sin(a2))
        fillet_left_start_point.name = "fillet_left start point"
        fillet_left.start_point = fillet_left_start_point

        fillet_left_on_1 = constraints.add_bi_elt_cst(cat_constraint_type.index("catCstTypeOn"), fillet_left_end_point, radial_line_left_end_point)
        constraints.add_mono_elt_cst(cat_constraint_type.index("catCstTypeReference"), fillet_left_start_point) 
        cnst_rad_fillet_left = constraints.add_mono_elt_cst(cat_constraint_type.index("catCstTypeRadius"), fillet_left)
        cnst_rad_fillet_left.mode = cat_constraint_mode.index("catCstModeDrivingDimension")
        cnst_rad_fillet_left.dimension.value = r_f
        
        #Right fillet and line        
        radial_line_right = ske2D_tooth_con.create_line(-x_s, y_s, -x_f_start, y_f_start)
        radial_line_right.name = "Radial_Line_Right"
        
        radial_line_right_start_point = ske2D_tooth_con.create_point(-x_s, y_s)
        radial_line_right_start_point.name = "radial_line_right start point"
        radial_line_right.start_point = radial_line_right_start_point
    
        radial_line_right_end_point = ske2D_tooth_con.create_point(-x_f_start, y_f_start)
        radial_line_right_end_point.name = "radial_line_right end point"
        radial_line_right.end_point = radial_line_right_end_point  

        radial_line_on_1 = constraints.add_bi_elt_cst(cat_constraint_type.index("catCstTypeOn"), radial_line_right_start_point, points_list_right[0])
        radial_line_tangnt = constraints.add_bi_elt_cst(cat_constraint_type.index("catCstTypeTangency"), radial_line_right, involute_flank_right )
        constraints.add_mono_elt_cst(cat_constraint_type.index("catCstTypeReference"), radial_line_right_end_point)
        
        cx_r, cy_r = -cx, cy
        
        a1_r = math.atan2(y_f_start - cy_r, -x_f_start - cx_r)
        a2_r = math.atan2(-cy_r, -cx_r)
        
        fillet_right = ske2D_tooth_con.create_circle(cx_r, cy_r, r_f, a1_r, a2_r)
        fillet_right.name = "Root_Fillet_Right"
        
        fillet_right_start_point = ske2D_tooth_con.create_point(-x_f_start, y_f_start)
        fillet_right_start_point.name = "fillet_right start point"
        fillet_right.start_point = fillet_right_start_point
    
        fillet_right_end_point = ske2D_tooth_con.create_point(r_f * math.cos(a2_r), r_f * math.sin(a2_r))
        fillet_right_end_point.name = "fillet_right end point"
        fillet_right.end_point = fillet_right_end_point

        fillet_right_on_1 = constraints.add_bi_elt_cst(cat_constraint_type.index("catCstTypeOn"), fillet_right_start_point, radial_line_right_end_point)
        constraints.add_mono_elt_cst(cat_constraint_type.index("catCstTypeReference"), fillet_right_end_point) 
        cnst_rad_fillet_right = constraints.add_mono_elt_cst(cat_constraint_type.index("catCstTypeRadius"), fillet_right)
        cnst_rad_fillet_right.mode = cat_constraint_mode.index("catCstModeDrivingDimension")
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
        constraints.add_bi_elt_cst(cat_constraint_type.index("catCstTypeOn"), fillet_left_end_point, p_start_left)
        
        fillet_left_start_point = ske2D_tooth_con.create_point(r_f * math.cos(a2), r_f * math.sin(a2))
        fillet_left.start_point = fillet_left_start_point
        
        # Add Radius Constraint
        cnst_rad_l = constraints.add_mono_elt_cst(cat_constraint_type.index("catCstTypeRadius"), fillet_left)
        cnst_rad_l.dimension.value = r_f

        # Create Right Fillet (Mirror of left)
        cx_r, cy_r = -cx, cy
        a1_r = math.atan2(y_s - cy_r, -x_s - cx_r)
        a2_r = math.atan2(-cy_r, -cx_r)
        
        fillet_right = ske2D_tooth_con.create_circle(cx_r, cy_r, r_f, a1_r, a2_r)
        fillet_right.name = "Root_Fillet_Right"
        
        fillet_right_start_point = ske2D_tooth_con.create_point(-x_s, y_s)
        fillet_right.start_point = fillet_right_start_point
        constraints.add_bi_elt_cst(cat_constraint_type.index("catCstTypeOn"), fillet_right_start_point, points_list_right[0])
        
        fillet_right_end_point = ske2D_tooth_con.create_point(r_f * math.cos(a2_r), r_f * math.sin(a2_r))
        fillet_right.end_point = fillet_right_end_point
        
        cnst_rad_r = constraints.add_mono_elt_cst(cat_constraint_type.index("catCstTypeRadius"), fillet_right)
        cnst_rad_r.dimension.value = r_f

    #Add the root of tooth
    angle_root_l = (math.atan2(cy, -cx) + 2 * math.pi) % (2 * math.pi)
    angle_root_r = (math.atan2(cy_r, -cx_r) + 2 * math.pi) % (2 * math.pi)
    
    root_arc = ske2D_tooth_con.create_circle(0, 0, dedendum_circle_radius, angle_root_l, angle_root_r)
    root_arc.name = "Tooth_Root_Arc"
 
    root_r_coords = fillet_right_end_point.get_coordinates()
 
    root_arc_start_point = ske2D_tooth_con.create_point(root_r_coords[0], root_r_coords[1])
    root_arc_start_point.name = "root_arc start point"
    root_arc.start_point = root_arc_start_point 
    
    root_l_coords = fillet_left_start_point.get_coordinates()
    
    root_arc_end_point = ske2D_tooth_con.create_point(root_l_coords[0], root_l_coords[1])
    root_arc_end_point.name = "root_arc end point"
    root_arc.end_point = root_arc_end_point 

    root_arc_on_1 = constraints.add_bi_elt_cst(cat_constraint_type.index("catCstTypeOn"), root_arc_start_point, fillet_right_end_point)
    root_arc_on_2 = constraints.add_bi_elt_cst(cat_constraint_type.index("catCstTypeOn"), root_arc_end_point, fillet_left_start_point)
    constraints.add_bi_elt_cst(cat_constraint_type.index("catCstTypeConcentricity"), root_arc, origin)
    
    #Close edition
    sketch_tooth_con.close_edition()
    part.update()
    
    #create sketch for gear body on xy plane
    sketch_body_con = hb_sketches.add(plane_XY)
    sketch_body_con.name = "sketch_body_con"
    ske2D_body_con = sketch_body_con.open_edition()
    constraints_body = sketch_body_con.constraints
    geo_elements_bdy = sketch_body_con.geometric_elements
    axis = geo_elements_bdy.item("AbsoluteAxis")
    h_axis = axis.get_item("HDirection")
    v_axis = axis.get_item("VDirection") 
    
    origin = sketch_body_con.absolute_axis.origin
   
    #create pitch circle
    gear_circle = ske2D_body_con.create_closed_circle(0, 0, dedendum_circle_radius + pad_tol)
    gear_circle.name = "Pitch Circle"
    constraints_body.add_bi_elt_cst(cat_constraint_type.index("catCstTypeConcentricity"), gear_circle, origin)
    cnst_gear = constraints_body.add_mono_elt_cst(cat_constraint_type.index("catCstTypeRadius"), gear_circle)
    cnst_gear.mode = cat_constraint_mode.index("catCstModeDrivingDimension")
    cnst_gear.dimension.value = dedendum_circle_radius + pad_tol 
    
    #Close edition
    sketch_body_con.close_edition()
    part.update()
    
    #Create pad for gear body
    pad_body = shape_factory.add_new_pad(sketch_body_con, gear_thicness)
    pad_body.direction_orientation = cat_prism_orientation.index("catRegularOrientation")
    pad_body.first_limit.limit_mode = cat_limit_mode.index("catOffsetLimit")
    pad_body.first_limit.dimension.value = gear_thicness
    pad_body.name = "Gear Body"
    pad_body.set_profile_element(part.create_reference_from_object(sketch_body_con))
    
    part.update()
    
    #Create pad for geart tooth
    pad_tooth = shape_factory.add_new_pad(sketch_tooth_con, gear_thicness)
    pad_tooth.direction_orientation = cat_prism_orientation.index("catRegularOrientation")
    pad_tooth.first_limit.limit_mode = cat_limit_mode.index("catOffsetLimit")
    pad_tooth.first_limit.dimension.value = gear_thicness
    pad_tooth.name = "Gear Tooth"
    pad_tooth.set_profile_element(part.create_reference_from_object(sketch_tooth_con))
    
    part.update()
    
    # Create Circular Pattern for remaining gear teeth
    ref_axis = part.create_reference_from_object(plane_XY) 
    ref_origin = part.create_reference_from_object(origin)
    
    circ_pattern = shape_factory.add_new_circ_pattern(
        pad_tooth,               # 1. Feature to copy
        1,                       # 2. Radial instances
        number_of_teeth,         # 3. Angular instances
        0.0,                     # 4. Radial step
        360.0/number_of_teeth,   # 5. Angular step
        1,                       # 6. Radial position
        1,                       # 7. Angular position
        ref_origin,              # 8. Rotation center reference
        ref_axis,                # 9. Rotation axis reference
        False,                   # 10. Is reversed?
        0.0,                     # 11. Rotation angle
        True                     # 12. Is radius aligned?
    )
    
    circ_pattern.name = "Teeth"
    
    part.update()