'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Batch_Rename_Instances.py
    Version:        1.1
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Batch rename all first-level instances in the active product with a pattern.
    Author:         Kai-Uwe Rathjen
    Date:           21.05.26
    Description:    This script renames all direct child instances of the active CATProduct using a
                    configurable prefix, start number, step increment, zero-padding width, and suffix.
                    A preview list is shown before applying. The sort order (current, alphabetical, or
                    reverse alphabetical) can be selected. Only the first level of the assembly tree
                    is renamed — sub-assemblies are not affected.
    dependencies = [
                    "pycatia",
                    "wxPython",
                    ]
    requirements:   Python >= 3.10
                    pycatia
                    wxPython
                    Catia V5 running with an open CATProduct document.
    -----------------------------------------------------------------------------------------------------------------------

    Change:         22.05.26 1.1: Moved CreateButtonSizer to dialog-level sizer so buttons are correctly parented to the dialog.

    -----------------------------------------------------------------------------------------------------------------------
'''

#Imports
from pycatia import catia
from pycatia.product_structure_interfaces.product_document import ProductDocument
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


class RenameDialog(wx.Dialog):
    def __init__(self, parent, instance_names):
        super().__init__(parent, title="Batch Rename Instances", size=(600, 540),
                         style=wx.DEFAULT_DIALOG_STYLE | wx.STAY_ON_TOP)

        self.instance_names = instance_names

        panel = wx.Panel(self)
        vbox  = wx.BoxSizer(wx.VERTICAL)

        grid = wx.FlexGridSizer(6, 3, 8, 8)
        grid.AddGrowableCol(1, 1)

        self.prefix_ctrl  = wx.TextCtrl(panel, value="Part")
        self.start_ctrl   = wx.TextCtrl(panel, value="1")
        self.step_ctrl    = wx.TextCtrl(panel, value="1")
        self.pad_ctrl     = wx.TextCtrl(panel, value="3")
        self.suffix_ctrl  = wx.TextCtrl(panel, value="")
        self.sort_ctrl    = wx.Choice(panel, choices=["Current order", "Alphabetical", "Reverse alphabetical"])
        self.sort_ctrl.SetSelection(0)

        grid.AddMany([
            (wx.StaticText(panel, label="Prefix:")),         (self.prefix_ctrl,  1, wx.EXPAND), (wx.StaticText(panel, label="")),
            (wx.StaticText(panel, label="Start number:")),   (self.start_ctrl,   1, wx.EXPAND), (wx.StaticText(panel, label="")),
            (wx.StaticText(panel, label="Step:")),           (self.step_ctrl,    1, wx.EXPAND), (wx.StaticText(panel, label="")),
            (wx.StaticText(panel, label="Zero-pad width:")), (self.pad_ctrl,     1, wx.EXPAND), (wx.StaticText(panel, label="digits")),
            (wx.StaticText(panel, label="Suffix:")),         (self.suffix_ctrl,  1, wx.EXPAND), (wx.StaticText(panel, label="")),
            (wx.StaticText(panel, label="Sort order:")),     (self.sort_ctrl,    1, wx.EXPAND), (wx.StaticText(panel, label="")),
        ])
        vbox.Add(grid, flag=wx.ALL | wx.EXPAND, border=10)

        preview_btn = wx.Button(panel, label="Preview")
        vbox.Add(preview_btn, flag=wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, border=10)

        self.preview_list = wx.ListCtrl(panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self.preview_list.InsertColumn(0, "Current Name", width=200)
        self.preview_list.InsertColumn(1, "New Name",     width=200)
        vbox.Add(self.preview_list, proportion=1, flag=wx.EXPAND | wx.LEFT | wx.RIGHT, border=10)

        panel.SetSizer(vbox)
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(panel, proportion=1, flag=wx.EXPAND)
        main_sizer.Add(self.CreateButtonSizer(wx.OK | wx.CANCEL), flag=wx.ALIGN_CENTER | wx.ALL, border=10)
        self.SetSizer(main_sizer)

        preview_btn.Bind(wx.EVT_BUTTON, self.on_preview)
        self.on_preview(None)

    def _get_sorted_names(self):
        sort_sel = self.sort_ctrl.GetSelection()
        names = list(self.instance_names)
        if sort_sel == 1:
            names.sort()
        elif sort_sel == 2:
            names.sort(reverse=True)
        return names

    def _build_new_names(self, sorted_names):
        try:
            start = int(self.start_ctrl.GetValue())
            step  = int(self.step_ctrl.GetValue())
            pad   = int(self.pad_ctrl.GetValue())
        except ValueError:
            return []
        prefix = self.prefix_ctrl.GetValue()
        suffix = self.suffix_ctrl.GetValue()
        result = []
        counter = start
        for name in sorted_names:
            num_str  = str(counter).zfill(pad)
            new_name = f"{prefix}{num_str}{suffix}"
            result.append((name, new_name))
            counter += step
        return result

    def on_preview(self, event):
        self.preview_list.DeleteAllItems()
        sorted_names = self._get_sorted_names()
        pairs        = self._build_new_names(sorted_names)
        for old, new in pairs:
            idx = self.preview_list.InsertItem(self.preview_list.GetItemCount(), old)
            self.preview_list.SetItem(idx, 1, new)

    def get_rename_pairs(self):
        sorted_names = self._get_sorted_names()
        return self._build_new_names(sorted_names)


if __name__ == "__main__":
    caa = catia()                                                                                                   #Catia application instance
    active_doc = caa.active_document                                                                               #Current open document

    if type(active_doc) is not ProductDocument:
        print("A CATProduct document must be the active document.")
        exit()

    product_document: ProductDocument = active_doc
    product = product_document.product

    children       = product.products
    instance_names = []

    for i in range(children.count):
        try:
            instance_names.append(children.item(i + 1).name)
        except Exception:
            pass

    if not instance_names:
        print("No child instances found in this product.")
        exit()

    print(f"\n Found {len(instance_names)} first-level instance(s)\n")

    app = wx.App(None)
    dlg = RenameDialog(None, instance_names)
    wx.CallAfter(_bring_to_front, dlg)

    if dlg.ShowModal() != wx.ID_OK:
        dlg.Destroy()
        print("Cancelled")
        exit()

    rename_pairs = dlg.get_rename_pairs()
    dlg.Destroy()

    if not rename_pairs:
        print("No valid rename pairs generated.")
        exit()

    old_to_new = {old: new for old, new in rename_pairs}

    renamed = 0
    failed  = 0

    for i in range(children.count):                                                                                #Apply renames
        try:
            child    = children.item(i + 1)
            old_name = child.name
            new_name = old_to_new.get(old_name)
            if new_name:
                child.name = new_name
                print(f"  Renamed: '{old_name}' -> '{new_name}'")
                renamed += 1
        except Exception as e:
            print(f"  Failed to rename '{old_name}': {e}")
            failed += 1

    print(f"\n\n Completed - {renamed} renamed, {failed} failed\n\n")
