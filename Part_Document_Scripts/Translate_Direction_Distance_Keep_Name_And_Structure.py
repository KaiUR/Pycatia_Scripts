'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Translate_Direction_Distance_Keep_Name_And_Structure.py
    Version:        1.0
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Translates all hybrid shapes in a geometric set while keeping names and structure.
    Author:         Kai-Uwe Rathjen
    Date:           06.05.26
    Description:    This script will ask the user to select a geometric set, a direction and a distance.
                    The script will recreate the full geometric set structure inside the current in-work object,
                    perform a translation on every hybrid shape recursively through all child sets, and preserve
                    the original names of all shapes and geometric sets.
    dependencies = [
                    "pycatia",
                    "wxPython",
                    ]
    requirements:   Python >= 3.10
                    pycatia
                    wxPython
                    Catia V5 running wtih an open part containing a geometric set and an axis system.
                    This script needs an open part document.
    -----------------------------------------------------------------------------------------------------------------------

    Change:

    -----------------------------------------------------------------------------------------------------------------------
'''

#Imports
from pycatia import catia
from pycatia.mec_mod_interfaces.part_document import PartDocument
from pycatia.mec_mod_interfaces.hybrid_body import HybridBody
import wx

'''
    This function searches for a hybrid body by name and returns it.

    Inputs:
        searchName              The name of the geometric set that is being searched for.
        currentHybridBodies     The current collection of geometric sets

    output:
        The geometric set that is found, or None if not found
'''
def searchHybridBody(seachName, currentHybridBodies):
    try:                                                                                                        #Try at current level
        currentSearch = currentHybridBodies.item(seachName)                                                     #Check if we can find it
        if currentSearch is not None:                                                                           #If we found it
            return currentSearch                                                                                #Return found Geometric set
    except:
        pass                                                                                                    #If no found move to recursion

    for index in range(currentHybridBodies.count):                                                              #Loop through geometric sets of this level
        if currentHybridBodies.item(index+1).hybrid_bodies.count > 0:
            found = searchHybridBody(seachName, currentHybridBodies.item(index+1).hybrid_bodies)                #recursive call

            if found is not None:                                                                               #If found
                return found                                                                                     #Return found

    return None                                                                                                 #Return not found

'''
    This function creates a datum from a hybrid shape preserving its name, then removes the original.

    Inputs:
        hybrid_shape_factory    The hybrid shape factory for the part
        hybrid_shape            The hybrid shape to create a datum from
        hybrid_body             The geometric set to add the datum to
        name                    The name to give the new datum

    output:
        None
'''
def create_datum(hybrid_shape_factory, hybrid_shape, hybrid_body, name=None):
    geo_type = hybrid_shape_factory.get_geometrical_feature_type(hybrid_shape)                                  #Get geometry type

    if geo_type == 1:                                                                                           #Point
        datum = hybrid_shape_factory.add_new_point_datum(hybrid_shape)
        if name: datum.name = name
        hybrid_body.append_hybrid_shape(datum)
    elif geo_type == 2:                                                                                         #Curve
        datum = hybrid_shape_factory.add_new_curve_datum(hybrid_shape)
        if name: datum.name = name
        hybrid_body.append_hybrid_shape(datum)
    elif geo_type == 3:                                                                                         #Line
        datum = hybrid_shape_factory.add_new_line_datum(hybrid_shape)
        if name: datum.name = name
        hybrid_body.append_hybrid_shape(datum)
    elif geo_type == 4:                                                                                         #Circle
        datum = hybrid_shape_factory.add_new_circle_datum(hybrid_shape)
        if name: datum.name = name
        hybrid_body.append_hybrid_shape(datum)
    elif geo_type == 5:                                                                                         #Surface
        datum = hybrid_shape_factory.add_new_surface_datum(hybrid_shape)
        if name: datum.name = name
        hybrid_body.append_hybrid_shape(datum)
    else:                                                                                                       #Unknown type
        print(f"  Warning: unsupported geometry type ({geo_type}) for '{name}' - skipped")
        return

    hybrid_shape_factory.delete_object_for_datum(hybrid_shape)                                                  #Remove original translate shape

'''
    This function recursively processes a source geometric set, recreating its structure in the target
    geometric set and performing a translation on every hybrid shape.

    Inputs:
        source_hb               The source geometric set to process
        target_hb               The target geometric set to recreate the structure in
        part                    The active part
        hybrid_shape_factory    The hybrid shape factory for the part
        direction_ref           The brep direction reference — recreated fresh for each shape
        distance                The distance to translate

    output:
        None
'''
def process_hybrid_body(source_hb, target_hb, part, hybrid_shape_factory, direction_ref, distance):
    hybrid_shapes = source_hb.hybrid_shapes                                                                     #Get all hybrid shapes in source set

    for index in range(hybrid_shapes.count):                                                                    #Loop through all shapes in source set
        shape = hybrid_shapes.item(index + 1)                                                                   #Get shape
        shape_name = shape.name                                                                                  #Store shape name
        shape_ref = part.create_reference_from_object(shape)                                                    #Create reference to shape

        fresh_direction = hybrid_shape_factory.add_new_direction(direction_ref)                                 #Recreate direction object fresh for each shape

        transform = hybrid_shape_factory.add_new_empty_translate()                                              #Create new translate
        transform.elem_to_translate = shape_ref                                                                 #Add element to translate
        transform.vector_type = 0                                                                               #Set to direction, distance
        transform.direction = fresh_direction                                                                   #Add fresh direction
        transform.distance_value = distance                                                                     #Add distance
        transform.volume_result = False                                                                         #Disable volume result
        transform.name = shape_name                                                                             #Set name to match source shape
        target_hb.append_hybrid_shape(transform)                                                                #Add to target geometric set
        part.update()                                                                                           #Update part

        create_datum(hybrid_shape_factory, transform, target_hb, shape_name)                                    #Convert to datum preserving name

    for child_index in range(source_hb.hybrid_bodies.count):                                                    #Loop through child geometric sets in source
        source_child_hb = HybridBody(source_hb.hybrid_bodies.item(child_index + 1).com_object)                 #Get and cast source child geometric set
        target_child_hb = HybridBody(target_hb.hybrid_bodies.add().com_object)                                 #Create and cast new child geometric set in target
        target_child_hb.name = source_child_hb.name                                                            #Name to match source child set

        process_hybrid_body(source_child_hb, target_child_hb, part,                                            #Recurse into child set
                hybrid_shape_factory, direction_ref, distance)

if __name__ == "__main__":
    #Anchoring relavent components
    caa = catia()                                                                                               #Catia application instance
    active_doc = caa.active_document                                                                            #Current Document

    object_filter = ("HybridBody",)                                                                             #Set user selection filter (Geometric Set)
    selectionSet = caa.active_document.selection                                                                #Create container for selection
    status = selectionSet.select_element3(object_filter, "Select geometric set to translate", False, 2, False)  #Runs an interactive selection command, exhaustive version.
    if status != "Normal":                                                                                      #Check if selection was succesful
        print("You must select a geometric set")
        exit()

    selected_item = selectionSet.item(1)                                                                        #Get selected item
    source_geo_set_name = selected_item.value.name                                                              #Store source geometric set name

    if type(active_doc) is PartDocument:                                                                        #If document is part document
        part = active_doc.part
        part_document: PartDocument = active_doc
    else:                                                                                                       #Else get part from product structure
        leaf_product = selected_item.com_object.LeafProduct                                                     #Get leaf product
        part_document = PartDocument(leaf_product.ReferenceProduct.Parent)                                      #Get part document
        part = part_document.part                                                                               #Get new part object

    hybrid_bodies = part.hybrid_bodies                                                                          #Set off all top level geometric sets
    hybrid_shape_factory = part.hybrid_shape_factory                                                            #GSD workbench to create hybridshapes

    source_hb = searchHybridBody(source_geo_set_name, hybrid_bodies)                                            #Find the selected source geometric set
    if source_hb is None:                                                                                       #If not found
        print(f"Error: Could not find geometric set '{source_geo_set_name}'")
        exit()

    object_filter = ("AnyObject",)                                                                              #Set user selection filter (AnyObject)
    selectionSet.clear()
    status = selectionSet.select_element3(object_filter, "Select a Direction", False, 2, False)                 #Runs an interactive selection command, exhaustive version.
    if status != "Normal":                                                                                      #Check if selection was succesful
        print("You must select a direction")
        exit()

    #Create new direction using brep
    ref_name = selectionSet.item(1).reference.name                                                              #Get Reference name

    try:
        brep_core = ref_name.replace("Selection_", "").split(");AxisSystem")[0]                                 #Remove selection_ from string
        brep_name = f"{brep_core});WithPermanentBody;WithoutBuildError;WithSelectingFeatureSupport;MFBRepVersion_CXR29)" #Build brep string to create reference
        direction_ref = part.create_reference_from_b_rep_name(brep_name, selectionSet.item(1).value)            #Create reference from selected direction, works with face or line of axis system
        selected_direction_ref = hybrid_shape_factory.add_new_direction(direction_ref)                          #Create new direction object
    except:
        print("You must select a face or line of an axis system as direction")
        exit()

    app = wx.App(None)                                                                                          #Initilize wx application
    distance = 0.0                                                                                              #Initilize distance to 0

    dlg = wx.TextEntryDialog(None, "Enter distance to translate:", "Enter Distance", "0.0",
            wx.OK | wx.CANCEL | wx.CENTRE | wx.STAY_ON_TOP)                                                     #Create text entry dialog

    if dlg.ShowModal() == wx.ID_OK:                                                                             #If user clicked OK
        try:
            distance = float(dlg.GetValue())                                                                    #Get distance as float
        except ValueError:
            print("You must enter a valid number")
            exit()
    else:
        dlg.Destroy()
        print("You must enter a distance")
        exit()

    dlg.Destroy()                                                                                               #Destroy dialog

    inwork_hb = searchHybridBody(part.in_work_object.name, hybrid_bodies)                                       #Look for the in work object geometric set
    if inwork_hb is None:                                                                                       #If not found
        inwork_hb = hybrid_bodies.add()                                                                         #Add new geometric set
        inwork_hb.name = "Translate_Keep_Name_And_Structure"                                                    #Rename geometric set

    output_hb = inwork_hb.hybrid_bodies.add()                                                                   #Create new child geometric set inside in-work object
    output_hb.name = source_geo_set_name                                                                        #Name to match source geometric set

    print(f"\n Processing geometric set '{source_geo_set_name}'\n")

    process_hybrid_body(source_hb, output_hb, part,                                                            #Recursively process source geometric set
            hybrid_shape_factory, direction_ref, distance)

    part.update()                                                                                               #Final update
    print(f"\n\n Completed\n\n")
