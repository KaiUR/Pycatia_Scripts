'''
    -----------------------------------------------------------------------------------------------------------------------
    Common Functions — Pycatia Scripts
    -----------------------------------------------------------------------------------------------------------------------

    This file is a reference collection of helper functions that appear across multiple scripts
    in this repository. Copy the functions you need into your own script.

    Functions are organised by category:

        1. Geometric Set Navigation
               searchHybridBody          — find a geometric set by name (recursive)
               searchHybridBodyWithPath  — same, but also returns the "/path/to/set" string

        2. Geometry Operations
               create_datum              — isolate (make datum) a hybrid shape, preserving its name
               collect_all_names         — collect (name, parent_set) pairs from a set recursively

        3. Coordinate Maths  (requires spa_workbench from part_document.spa_workbench())
               normalize_vector          — normalise a 3D vector to unit length
               dot_product               — dot product of two 3D vectors
               cross_product             — cross product of two 3D vectors
               are_collinear             — check whether three 3D points are collinear
               coords_relative_to_axis   — measure a point's coordinates relative to an axis system

        4. File Input
               get_path                  — open a wx file-picker dialog and return the selected path

    -----------------------------------------------------------------------------------------------------------------------
'''



# ==============================================================================
# 1. GEOMETRIC SET NAVIGATION
# ==============================================================================

'''
    Searches for a hybrid body (geometric set) by name and returns it.
    Searches recursively through all nested geometric sets.

    Inputs:
        searchName              The name of the geometric set being searched for.
        currentHybridBodies     The hybrid bodies collection to search (e.g. part.hybrid_bodies).

    output:
        The HybridBody if found, or None if not found.

    Usage:
        hb = searchHybridBody("My_Set", part.hybrid_bodies)
        if hb is None:
            print("Not found")
'''
def searchHybridBody(seachName, currentHybridBodies):
    for index in range(currentHybridBodies.count):                                                             #Search at current level by explicit name comparison
        hb = currentHybridBodies.item(index + 1)
        if hb.name == seachName:                                                                               #Found at this level
            return hb                                                                                          #Return found geometric set

    for index in range(currentHybridBodies.count):                                                             #Loop through geometric sets at this level
        if currentHybridBodies.item(index+1).hybrid_bodies.count > 0:
            found = searchHybridBody(seachName, currentHybridBodies.item(index+1).hybrid_bodies)               #Recursive call
            if found is not None:                                                                              #If found
                return found                                                                                   #Return found

    return None                                                                                                #Return not found


'''
    Searches for a hybrid body by name and also returns the "/" separated path to it.

    Inputs:
        searchName              The name of the geometric set being searched for.
        currentHybridBodies     The hybrid bodies collection to search.
        currentPath             Accumulated path string (leave blank on first call).

    output:
        Tuple (HybridBody, path_string) if found, or (None, None) if not found.

    Usage:
        hb, path = searchHybridBodyWithPath("My_Set", part.hybrid_bodies)
        # path == "Parent_Set/Child_Set/My_Set"
'''
def searchHybridBodyWithPath(seachName, currentHybridBodies, currentPath=""):
    for index in range(currentHybridBodies.count):                                                             #Search at current level by explicit name comparison
        hb = currentHybridBodies.item(index + 1)
        if hb.name == seachName:                                                                               #Found at this level
            path = (currentPath + "/" if currentPath else "") + seachName                                      #Build path
            return hb, path                                                                                    #Return found geometric set and path

    for index in range(currentHybridBodies.count):                                                             #Loop through geometric sets at this level
        hb = currentHybridBodies.item(index + 1)
        if hb.hybrid_bodies.count > 0:
            child_path = (currentPath + "/" if currentPath else "") + hb.name                                  #Build path to this level
            found, found_path = searchHybridBodyWithPath(seachName, hb.hybrid_bodies, child_path)              #Recursive call
            if found is not None:                                                                              #If found
                return found, found_path                                                                       #Return found

    return None, None                                                                                          #Return not found


# ==============================================================================
# 2. GEOMETRY OPERATIONS
# ==============================================================================

'''
    Replaces a hybrid shape with an isolated datum of the same type, preserving its name.
    Supports points (1), curves (2), lines (3), circles (4), and surfaces (5).
    Unsupported types are skipped with a warning.

    Inputs:
        hybrid_shape_factory    The part's HybridShapeFactory (part.hybrid_shape_factory).
        hybrid_shape            The HybridShape to isolate.
        hybrid_body             The geometric set to append the new datum to.
        name                    Optional name for the datum. If None, name is not set.

    output:
        None — the original shape is replaced by the datum in hybrid_body.

    Requires:
        part.update() must be called after one or more create_datum calls.

    Usage:
        create_datum(hybrid_shape_factory, my_shape, target_set, name="My_Datum")
        part.update()
'''
def create_datum(hybrid_shape_factory, hybrid_shape, hybrid_body, name=None):
    geo_type = hybrid_shape_factory.get_geometrical_feature_type(hybrid_shape)                                 #Get geometry type

    if geo_type == 1:                                                                                          #Point
        datum = hybrid_shape_factory.add_new_point_datum(hybrid_shape)
    elif geo_type == 2:                                                                                        #Curve
        datum = hybrid_shape_factory.add_new_curve_datum(hybrid_shape)
    elif geo_type == 3:                                                                                        #Line
        datum = hybrid_shape_factory.add_new_line_datum(hybrid_shape)
    elif geo_type == 4:                                                                                        #Circle
        datum = hybrid_shape_factory.add_new_circle_datum(hybrid_shape)
    elif geo_type == 5:                                                                                        #Surface
        datum = hybrid_shape_factory.add_new_surface_datum(hybrid_shape)
    else:
        print(f"  Warning: unsupported geometry type ({geo_type}) for '{name}' — skipped")
        return

    if name:                                                                                                   #Apply name if given
        datum.name = name
    hybrid_body.append_hybrid_shape(datum)                                                                     #Add datum to geometric set
    hybrid_shape_factory.delete_object_for_datum(hybrid_shape)                                                 #Remove the original construction shape


'''
    Recursively collects all (shape_name, parent_set_name) tuples from a geometric set
    and all its nested children.

    Inputs:
        hybrid_body     The geometric set to scan.
        name_list       A list to append tuples to (pass an empty list on first call).

    output:
        None — appends (name, parent_set_name) tuples directly to name_list.

    Usage:
        all_names = []
        collect_all_names(target_set, all_names)
        # all_names == [("Shape1", "Set_A"), ("Shape2", "Set_B"), ...]
'''
def collect_all_names(hybrid_body, name_list):
    hybrid_shapes = hybrid_body.hybrid_shapes                                                                  #Get all hybrid shapes in this set
    for index in range(hybrid_shapes.count):                                                                   #Loop through shapes
        shape = hybrid_shapes.item(index + 1)                                                                  #Get shape (1-indexed)
        name_list.append((shape.name, hybrid_body.name))                                                       #Append (name, parent set name) tuple

    for child_index in range(hybrid_body.hybrid_bodies.count):                                                 #Loop through child geometric sets
        collect_all_names(hybrid_body.hybrid_bodies.item(child_index + 1), name_list)                          #Recurse into child sets


# ==============================================================================
# 3. COORDINATE MATHS
# ==============================================================================

'''
    Normalises a 3D vector to unit length.

    Inputs:
        vec     A 3-element list or tuple [x, y, z].

    output:
        Normalised vector as a tuple (x, y, z), or None if the vector has zero magnitude.
'''
def normalize_vector(vec):
    magnitude = (vec[0] ** 2 + vec[1] ** 2 + vec[2] ** 2) ** 0.5                                             #Get magnitude
    if magnitude != 0:
        return vec[0] / magnitude, vec[1] / magnitude, vec[2] / magnitude                                     #Return normalised vector


'''
    Returns the dot product of two 3D vectors.

    Inputs:
        vec1    First vector [x, y, z].
        vec2    Second vector [x, y, z].

    output:
        Scalar dot product.
'''
def dot_product(vec1, vec2):
    return vec1[0] * vec2[0] + vec1[1] * vec2[1] + vec1[2] * vec2[2]


'''
    Returns the cross product of two 3D vectors.

    Inputs:
        a   First vector [x, y, z].
        b   Second vector [x, y, z].

    output:
        Cross product as a list [x, y, z].
'''
def cross_product(a, b):
    return [
        a[1]*b[2] - a[2]*b[1],
        a[2]*b[0] - a[0]*b[2],
        a[0]*b[1] - a[1]*b[0]
    ]


'''
    Checks whether three 3D points are collinear (lie on the same line).
    Uses the normalised cross product magnitude so the test is scale-independent.
    Returns True if either input vector is zero length (degenerate case).

    Inputs:
        point_a, point_b, point_c   Each a list or tuple [x, y, z].

    output:
        True if the points are collinear (or degenerate), False otherwise.
'''
def are_collinear(point_a, point_b, point_c):
    vectorAB = point_b[0] - point_a[0], point_b[1] - point_a[1], point_b[2] - point_a[2]
    vectorAC = point_c[0] - point_a[0], point_c[1] - point_a[1], point_c[2] - point_a[2]

    cross_product_vectors = cross_product(vectorAB, vectorAC)

    cross_mag_sq = cross_product_vectors[0]**2 + cross_product_vectors[1]**2 + cross_product_vectors[2]**2
    ab_mag_sq    = vectorAB[0]**2 + vectorAB[1]**2 + vectorAB[2]**2
    ac_mag_sq    = vectorAC[0]**2 + vectorAC[1]**2 + vectorAC[2]**2

    if ab_mag_sq == 0 or ac_mag_sq == 0:                                                                       #Degenerate — treat as collinear
        return True

    return cross_mag_sq / (ab_mag_sq * ac_mag_sq) < 1e-6


'''
    Measures a point's coordinates relative to a given axis system.

    Inputs:
        part            The Part object (part_document.part).
        spa_workbench   The SPA workbench (part_document.spa_workbench()).
        axis_system     The axis system to measure relative to.
        point           The HybridShapePointCoord to measure.
        precision       Decimal places to round to (default 6).

    output:
        Tuple (x, y, z) in the axis system's local coordinate frame.

    Usage:
        spa_workbench = part_document.spa_workbench()
        coords = coords_relative_to_axis(part, spa_workbench, my_axis, my_point)
'''
def coords_relative_to_axis(part, spa_workbench, axis_system, point, precision=6):
    a_origin = axis_system.get_origin()                                                                        #Get axis origin
    n_x = normalize_vector(axis_system.get_x_axis())                                                           #Normalise X axis
    n_y = normalize_vector(axis_system.get_y_axis())                                                           #Normalise Y axis
    n_z = normalize_vector(axis_system.get_z_axis())                                                           #Normalise Z axis

    reference = part.create_reference_from_object(point)                                                       #Create reference from point
    measurable = spa_workbench.get_measurable(reference)                                                       #Get measurable
    coordinates = measurable.get_point()                                                                       #Get absolute coordinates

    diff = [coordinates[i] - a_origin[i] for i in range(3)]                                                   #Vector from axis origin to point

    x = round(dot_product(diff, n_x), precision)                                                               #Project onto X
    y = round(dot_product(diff, n_y), precision)                                                               #Project onto Y
    z = round(dot_product(diff, n_z), precision)                                                               #Project onto Z

    return x, y, z


# ==============================================================================
# 4. FILE INPUT
# ==============================================================================

'''
    Opens a wx file-open dialog and returns the selected file path, or None if cancelled.
    Requires wx.App(None) to already be initialised before calling.

    Inputs:
        wildcard    File type filter string, e.g. '*.txt;*.csv'

    output:
        The selected file path as a string, or None if cancelled.

    Usage:
        app = wx.App(None)
        path = get_path('*.txt;*.csv')
        if path is None:
            exit()
'''
def get_path(wildcard):
    import wx
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
    style = wx.FD_OPEN | wx.FD_FILE_MUST_EXIST                                                                 #Open dialog flags
    dialog = wx.FileDialog(None, 'Open', wildcard=wildcard, style=style)                                       #Create file dialog
    wx.CallAfter(_bring_to_front, dialog)
    if dialog.ShowModal() == wx.ID_OK:                                                                         #Show dialog and wait for selection
        path = dialog.GetPath()                                                                                #Get selected path
    else:
        path = None                                                                                            #User cancelled
    dialog.Destroy()                                                                                           #Close dialog
    return path                                                                                                #Return path or None
