'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Copy_Parameters_Between_Parts.py
    Version:        1.1
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Copy selected parameters from one open CATPart to another.
    Author:         Kai-Uwe Rathjen
    Date:           21.05.26
    Description:    This script lists all open CATPart documents in CATIA. The user selects a source
                    part and a destination part, then chooses which parameters to copy. Selected
                    parameters are created (or updated if they already exist) in the destination part.
                    Only user-accessible parameters (Read/Write) are shown. Formulas are not copied —
                    only the current numeric or string value is transferred.
    dependencies = [
                    "pycatia",
                    "wxPython",
                    ]
    requirements:   Python >= 3.10
                    pycatia
                    wxPython
                    Catia V5 running with at least two open CATPart documents.
    -----------------------------------------------------------------------------------------------------------------------

    Change:         1.1 - Fixed AddMany tuple syntax (positional flags, not keyword args).
                          Moved CreateButtonSizer to dialog-level sizer so buttons are
                          correctly parented to the dialog.

    -----------------------------------------------------------------------------------------------------------------------
'''

#Imports
from pycatia import catia
from pycatia.mec_mod_interfaces.part_document import PartDocument
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


def _get_readable_params(part):
    params = part.parameters
    result = []
    for i in range(params.count):
        p = params.item(i + 1)
        try:
            value_str = p.value_as_string()
            result.append({"name": p.name, "value": value_str, "param": p})
        except Exception:
            pass
    return result


class CopyParamsDialog(wx.Dialog):
    def __init__(self, parent, part_names):
        super().__init__(parent, title="Copy Parameters Between Parts", size=(600, 520),
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER | wx.STAY_ON_TOP)

        self.part_names = part_names

        panel = wx.Panel(self)
        vbox  = wx.BoxSizer(wx.VERTICAL)

        top_grid = wx.FlexGridSizer(2, 2, 6, 8)
        top_grid.AddGrowableCol(1, 1)

        self.src_combo  = wx.Choice(panel, choices=part_names)
        self.dest_combo = wx.Choice(panel, choices=part_names)
        self.src_combo.SetSelection(0)
        self.dest_combo.SetSelection(min(1, len(part_names) - 1))

        top_grid.AddMany([
            (wx.StaticText(panel, label="Source part:"),      0, wx.ALIGN_CENTER_VERTICAL),
            (self.src_combo,  1, wx.EXPAND),
            (wx.StaticText(panel, label="Destination part:"), 0, wx.ALIGN_CENTER_VERTICAL),
            (self.dest_combo, 1, wx.EXPAND),
        ])
        vbox.Add(top_grid, flag=wx.ALL | wx.EXPAND, border=10)

        load_btn = wx.Button(panel, label="Load Source Parameters")
        vbox.Add(load_btn, flag=wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, border=10)

        self.param_list = wx.CheckListBox(panel, choices=[])
        vbox.Add(self.param_list, proportion=1, flag=wx.EXPAND | wx.LEFT | wx.RIGHT, border=10)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        sel_all_btn   = wx.Button(panel, label="Select All")
        desel_all_btn = wx.Button(panel, label="Deselect All")
        btn_row.Add(sel_all_btn,   flag=wx.RIGHT, border=5)
        btn_row.Add(desel_all_btn, flag=wx.RIGHT, border=5)
        vbox.Add(btn_row, flag=wx.LEFT | wx.TOP | wx.BOTTOM, border=10)

        panel.SetSizer(vbox)
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(panel, proportion=1, flag=wx.EXPAND)
        main_sizer.Add(self.CreateButtonSizer(wx.OK | wx.CANCEL), flag=wx.ALIGN_CENTER | wx.BOTTOM, border=10)
        self.SetSizer(main_sizer)

        self.param_data = []

        load_btn.Bind(wx.EVT_BUTTON,     self.on_load)
        sel_all_btn.Bind(wx.EVT_BUTTON,  self.on_select_all)
        desel_all_btn.Bind(wx.EVT_BUTTON, self.on_deselect_all)

    def on_load(self, event):
        self.param_list.Clear()
        self.param_data = []
        src_idx = self.src_combo.GetSelection()
        if src_idx < 0:
            return
        wx.GetApp()._src_name = self.part_names[src_idx]
        event.Skip()
        wx.PostEvent(self, wx.PyCommandEvent(wx.EVT_BUTTON.typeId, wx.ID_HIGHEST + 1))

    def populate_params(self, params):
        self.param_list.Clear()
        self.param_data = params
        labels = [f"{p['name']}  =  {p['value']}" for p in params]
        self.param_list.Set(labels)
        for i in range(len(labels)):
            self.param_list.Check(i, True)

    def on_select_all(self, event):
        for i in range(self.param_list.GetCount()):
            self.param_list.Check(i, True)

    def on_deselect_all(self, event):
        for i in range(self.param_list.GetCount()):
            self.param_list.Check(i, False)

    def get_selections(self):
        src_name  = self.part_names[self.src_combo.GetSelection()]  if self.src_combo.GetSelection()  >= 0 else None
        dest_name = self.part_names[self.dest_combo.GetSelection()] if self.dest_combo.GetSelection() >= 0 else None
        checked   = [self.param_data[i] for i in range(self.param_list.GetCount()) if self.param_list.IsChecked(i)]
        return src_name, dest_name, checked


if __name__ == "__main__":
    caa = catia()                                                                                                   #Catia application instance

    part_docs = {doc.name: doc for doc in caa.documents if doc.name.endswith('.CATPart')}                         #Find all open CATPart documents

    if len(part_docs) < 2:
        print("At least two open CATPart documents are required.")
        exit()

    part_names = list(part_docs.keys())

    app = wx.App(None)

    dlg = CopyParamsDialog(None, part_names)
    wx.CallAfter(_bring_to_front, dlg)

    source_params = []

    def load_source_params():
        src_idx = dlg.src_combo.GetSelection()
        if src_idx < 0:
            return
        src_name = part_names[src_idx]
        src_doc  = part_docs[src_name]
        try:
            src_part = PartDocument(src_doc.com_object).part
            params   = _get_readable_params(src_part)
            dlg.populate_params(params)
            print(f"  Loaded {len(params)} parameters from '{src_name}'")
        except Exception as e:
            wx.MessageBox(f"Could not read parameters: {e}", "Error", wx.OK | wx.ICON_ERROR)

    dlg.Bind(wx.EVT_BUTTON, lambda e: load_source_params() if e.GetId() == wx.ID_HIGHEST + 1 else e.Skip())
    dlg.Bind(wx.EVT_BUTTON, lambda e: (load_source_params(), None)[1] if hasattr(e, 'GetId') and "Load" in str(e.GetEventObject().GetLabel()) else e.Skip())

    for child in dlg.GetChildren():
        if isinstance(child, wx.Panel):
            for grandchild in child.GetChildren():
                if isinstance(grandchild, wx.Button) and grandchild.GetLabel() == "Load Source Parameters":
                    grandchild.Bind(wx.EVT_BUTTON, lambda e: load_source_params())
                    break

    if dlg.ShowModal() != wx.ID_OK:
        dlg.Destroy()
        print("Cancelled")
        exit()

    src_name, dest_name, selected_params = dlg.get_selections()
    dlg.Destroy()

    if src_name == dest_name:
        print("Source and destination parts must be different.")
        exit()

    if not selected_params:
        print("No parameters selected.")
        exit()

    dest_doc  = part_docs[dest_name]
    dest_part = PartDocument(dest_doc.com_object).part
    dest_params = dest_part.parameters

    print(f"\n Copying {len(selected_params)} parameter(s) from '{src_name}' to '{dest_name}'\n")

    copied  = 0
    updated = 0
    failed  = 0

    for p_info in selected_params:
        p_name  = p_info['name']
        p_value = p_info['value']
        p_param = p_info['param']

        try:
            existing = None
            try:
                existing = dest_params.item(p_name)                                                               #Check if parameter already exists
            except Exception:
                pass

            if existing is not None:
                try:
                    existing.value_as_string()                                                                     #Test writability
                    existing.com_object.Value = p_param.com_object.Value                                          #Update existing parameter value
                    print(f"  Updated: {p_name} = {p_value}")
                    updated += 1
                except Exception as e:
                    print(f"  Skipped (read-only): {p_name} — {e}")
                    failed += 1
            else:
                try:
                    float_val = float(p_value)
                    dest_params.create_real(p_name, float_val)                                                     #Create new real parameter
                    print(f"  Copied (real): {p_name} = {p_value}")
                    copied += 1
                except ValueError:
                    dest_params.create_string(p_name, p_value)                                                    #Create new string parameter
                    print(f"  Copied (string): {p_name} = {p_value}")
                    copied += 1

        except Exception as e:
            print(f"  Failed: {p_name} — {e}")
            failed += 1

    try:
        dest_part.update()                                                                                         #Update destination part
    except Exception:
        pass

    print(f"\n\n Completed - {copied} copied, {updated} updated, {failed} failed\n\n")
