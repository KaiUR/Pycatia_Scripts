'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Check_Duplicate_Names_In_Geometric_Set.py
    Version:        1.2
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Scan a geometric set and report any elements that share a name.
    Author:         Kai-Uwe Rathjen
    Date:           06.05.26
    Description:    This script will ask the user to select a geometric set. The script will then scan all
                    hybrid shapes inside the selected geometric set and report any that share the same name.
                    Duplicate names are a common source of macro errors and can cause unexpected behaviour
                    when searching or referencing geometry by name. Results are shown in a dialog.
    dependencies = [
                    "pycatia",
                    "wxPython",
                    ]
    requirements:   Python >= 3.10
                    pycatia
                    wxPython
                    Catia V5 running with an open part document containing a geometric set.
                    This script needs an open part document.
    -----------------------------------------------------------------------------------------------------------------------

    Change:         06.05.26 1.1: Results now shown in wx dialog instead of console.
                    12.05.26 1.2: Dialogs raised to foreground of CATIA window.

    -----------------------------------------------------------------------------------------------------------------------
'''

#Imports
from pycatia import catia
from pycatia.mec_mod_interfaces.part_document import PartDocument
import wx
import wx.lib.dialogs
import ctypes

def _bring_to_front(window):
    u32 = ctypes.windll.user32
    hwnd = window.GetHandle()
    fg_hwnd = u32.GetForegroundWindow()
    fg_tid = u32.GetWindowThreadProcessId(fg_hwnd, None)
    our_tid = ctypes.windll.kernel32.GetCurrentThreadId()
    if fg_tid != our_tid:
        u32.AttachThreadInput(fg_tid, our_tid, True)
    u32.BringWindowToTop(hwnd)
    u32.SetForegroundWindow(hwnd)
    if fg_tid != our_tid:
        u32.AttachThreadInput(fg_tid, our_tid, False)

'''
    This function searches for a hybrid body by name and return is.

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
    This function recursively collects all shape names from a geometric set and its children.

    Inputs:
        hybrid_body     The geometric set to scan
        name_list       The list to append found names to (name, set_name) tuples

    output:
        None - appends directly to name_list
'''
def collect_all_names(hybrid_body, name_list):
    hybrid_shapes = hybrid_body.hybrid_shapes                                                                   #Get all hybrid shapes in this set
    for index in range(hybrid_shapes.count):                                                                    #Loop through shapes
        shape = hybrid_shapes.item(index + 1)                                                                   #Get shape
        name_list.append((shape.name, hybrid_body.name))                                                        #Append (name, parent set name) tuple

    for child_index in range(hybrid_body.hybrid_bodies.count):                                                  #Loop through child geometric sets
        collect_all_names(hybrid_body.hybrid_bodies.item(child_index + 1), name_list)                           #Recurse into child sets

if __name__ == "__main__":
    #Anchoring relavent components
    caa = catia()                                                                                               #Catia application instance
    active_doc = caa.active_document                                                                            #Current Document

    app = wx.App(None)                                                                                          #Initilize wx application

    object_filter = ("HybridBody",)                                                                             #Set user selection filter (Geometric Set)
    selectionSet = caa.active_document.selection                                                                #Create container for selection
    status = selectionSet.select_element3(object_filter, "Select geometric set to check for duplicate names", False, 2, False) #Runs an interactive selection command, exhaustive version.
    if status != "Normal":                                                                                      #Check if selection was succesful
        _dlg = wx.MessageDialog(None, "You must select a geometric set.", "Error", wx.OK | wx.ICON_ERROR)
        wx.CallAfter(_bring_to_front, _dlg)
        _dlg.ShowModal()
        _dlg.Destroy()                                                                                          #Show error dialog
        exit()

    selected_item = selectionSet.item(1)                                                                        #Get selected item
    geo_set_name = selected_item.value.name                                                                     #Get name of selected geometric set

    if type(active_doc) is PartDocument:                                                                        #If document is part document
        part = active_doc.part
        part_document: PartDocument = active_doc
    else:                                                                                                       #Else get part from product structure
        leaf_product = selected_item.com_object.LeafProduct                                                     #Get leaf product
        part_document = PartDocument(leaf_product.ReferenceProduct.Parent)                                      #Get part document
        part = part_document.part                                                                               #Get new part object

    hybrid_bodies = part.hybrid_bodies                                                                          #Set off all top level geometric sets

    target_hb = searchHybridBody(geo_set_name, hybrid_bodies)                                                   #Find the selected geometric set
    if target_hb is None:                                                                                       #If not found
        _dlg = wx.MessageDialog(None, f"Error: Could not find geometric set '{geo_set_name}'.", "Error", wx.OK | wx.ICON_ERROR)
        wx.CallAfter(_bring_to_front, _dlg)
        _dlg.ShowModal()
        _dlg.Destroy()                                                                                          #Show error dialog
        exit()

    all_names = []                                                                                              #List to store all (name, set) tuples
    collect_all_names(target_hb, all_names)                                                                     #Collect all names recursively

    name_counts = {}                                                                                            #Dict to count occurrences of each name
    for name, set_name in all_names:                                                                            #Loop through all names
        if name not in name_counts:                                                                             #If name not seen before
            name_counts[name] = []                                                                              #Initialise list
        name_counts[name].append(set_name)                                                                      #Append parent set name

    duplicates = {name: sets for name, sets in name_counts.items() if len(sets) > 1}                           #Filter to only duplicates

    if len(duplicates) == 0:                                                                                    #If no duplicates
        _dlg = wx.MessageDialog(None,
                f"No duplicate names found in '{geo_set_name}'.\n\n{len(all_names)} element(s) scanned.",
                "Check Duplicate Names - No Duplicates Found", wx.OK | wx.ICON_INFORMATION)
        wx.CallAfter(_bring_to_front, _dlg)
        _dlg.ShowModal()
        _dlg.Destroy()                                                                                          #Show result dialog
    else:                                                                                                       #If duplicates found
        report_lines = []                                                                                       #List to build report lines
        report_lines.append(f"Found {len(duplicates)} duplicate name(s) in '{geo_set_name}'.")
        report_lines.append(f"{len(all_names)} element(s) scanned.\n")
        report_lines.append("-" * 60)

        for name, sets in sorted(duplicates.items()):                                                           #Loop through each duplicate
            report_lines.append(f"\n'{name}' appears {len(sets)} time(s):")
            for set_name in sets:                                                                               #Loop through each parent set
                report_lines.append(f"    in: '{set_name}'")

        report_text = "\n".join(report_lines)                                                                   #Join report lines into single string

        _dlg = wx.lib.dialogs.ScrolledMessageDialog(None, report_text,
                "Check Duplicate Names - Duplicates Found",
                size=(500, 400))
        wx.CallAfter(_bring_to_front, _dlg)
        _dlg.ShowModal()
        _dlg.Destroy()                                                                                          #Show scrollable report dialog
