'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Create_Construction_Planes.py
    Version:        1.1
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Create a series of evenly spaced offset planes from a reference plane.
    Author:         Kai-Uwe Rathjen
    Date:           16.05.26
    Description:    This script will ask the user to select a reference plane, a step distance, and a
                    count. It will create N planes offset from the reference at regular intervals and add
                    them to a new geometric set named "Sections" inside the current in-work object.
                    Planes are named Section_001, Section_002, etc. Useful for generating cross-section
                    planes for analysis or pattern construction.
    dependencies = [
                    "pycatia",
                    "wxPython",
                    ]
    requirements:   Python >= 3.10
                    pycatia
                    wxPython
                    Catia V5 running with an open part document containing a reference plane.
                    This script needs an open part document.
    -----------------------------------------------------------------------------------------------------------------------

    Change:         16.05.26 1.1: Fix plane and body creation — use pycatia factory/append methods instead of com_object patterns.

    -----------------------------------------------------------------------------------------------------------------------
'''

#Imports
from pycatia import catia
from pycatia.mec_mod_interfaces.part_document import PartDocument
from pycatia.mec_mod_interfaces.hybrid_body import HybridBody
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

if __name__ == "__main__":
    caa = catia()
    active_doc = caa.active_document

    object_filter = ("AnyObject",)
    selectionSet = caa.active_document.selection
    status = selectionSet.select_element3(object_filter, "Select reference plane", False, 2, False)
    if status != "Normal":
        print("You must select a reference plane")
        exit()

    selected_item = selectionSet.item(1)

    if type(active_doc) is PartDocument:
        part = active_doc.part
        part_document: PartDocument = active_doc
    else:
        leaf_product = selected_item.com_object.LeafProduct
        part_document = PartDocument(leaf_product.ReferenceProduct.Parent)
        part = part_document.part

    hybrid_bodies = part.hybrid_bodies
    hybrid_shape_factory = part.hybrid_shape_factory

    ref_plane = selectionSet.item(1).reference                                                                    #Reference to the selected plane

    app = wx.App(None)

    dlg_step = wx.TextEntryDialog(None, "Enter step distance between planes (mm):", "Step Distance", "10.0",
            wx.OK | wx.CANCEL | wx.CENTRE | wx.STAY_ON_TOP)
    wx.CallAfter(_bring_to_front, dlg_step)
    if dlg_step.ShowModal() == wx.ID_OK:
        try:
            step = float(dlg_step.GetValue())
        except ValueError:
            print("You must enter a valid number for step distance")
            exit()
    else:
        dlg_step.Destroy()
        print("Cancelled")
        exit()
    dlg_step.Destroy()

    dlg_count = wx.TextEntryDialog(None, "Enter number of planes to create:", "Plane Count", "5",
            wx.OK | wx.CANCEL | wx.CENTRE | wx.STAY_ON_TOP)
    wx.CallAfter(_bring_to_front, dlg_count)
    if dlg_count.ShowModal() == wx.ID_OK:
        try:
            count = int(dlg_count.GetValue())
            if count < 1:
                print("Count must be at least 1")
                exit()
        except ValueError:
            print("You must enter a valid integer for count")
            exit()
    else:
        dlg_count.Destroy()
        print("Cancelled")
        exit()
    dlg_count.Destroy()

    in_work = part.in_work_object
    inwork_hb = None
    try:
        inwork_hb = HybridBody(in_work.com_object)
        inwork_hb.hybrid_shapes
    except Exception:
        inwork_hb = None
    if inwork_hb is None:
        try:
            inwork_hb = HybridBody(in_work.com_object.Parent)
            inwork_hb.hybrid_shapes
        except Exception:
            inwork_hb = None
    if inwork_hb is None:
        inwork_hb = hybrid_bodies.add()
        inwork_hb.name = "Construction_Planes"

    sections_hb = inwork_hb.hybrid_bodies.add()                                                                   #New child set for the planes
    sections_hb.name = "Sections"

    print(f"\n Creating {count} plane(s) with step {step} mm\n")

    for i in range(count):
        offset = step * (i + 1)                                                                                   #Cumulative offset from reference
        plane_name = f"Section_{str(i + 1).zfill(3)}"

        plane = hybrid_shape_factory.add_new_plane_offset(ref_plane, offset, False)
        plane.name = plane_name
        sections_hb.append_hybrid_shape(plane)
        part.update()

        print(f"  Created: {plane_name} at offset {offset} mm")

    part.update()
    print(f"\n\n Completed - {count} plane(s) created in 'Sections'\n\n")
