'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Open_CATIA_Settings_Folder.py
    Version:        1.0
    Code:           Python3.10+
    Release:        N/A
    Purpose:        Open the CATSettings folder for a selected CATIA V5 version directly in Explorer.
    Author:         Kai-Uwe Rathjen
    Date:           28.05.26
    Description:    Scans C:\\ProgramData\\DassaultSystemes\\CATEnv\\ for installed CATIA V5 versions and
                    reads the CATUserSettingPath for each. Presents a version picker and opens the
                    resolved settings folder in Windows Explorer. Useful for manually inspecting,
                    copying, or deleting individual settings files without navigating through AppData.
    dependencies = [
                    "wxPython",
                    ]
    requirements:   Python >= 3.10
                    wxPython
    -----------------------------------------------------------------------------------------------------------------------

    Change:

    -----------------------------------------------------------------------------------------------------------------------
'''

#Imports
import os
import re
import subprocess
import ctypes
import wx

CATENV_DIR = r"C:\ProgramData\DassaultSystemes\CATEnv"

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

def detect_versions():
    versions = []
    if not os.path.isdir(CATENV_DIR):
        return versions
    for fname in sorted(os.listdir(CATENV_DIR)):
        if not fname.lower().endswith('.txt'):
            continue
        match = re.search(r'\.(B(\d+))\.txt$', fname, re.IGNORECASE)
        if not match:
            continue
        version  = f"R{match.group(2)}"
        env_file = os.path.join(CATENV_DIR, fname)
        settings_path = _read_settings_path(env_file, version)
        versions.append({
            'version':       version,
            'env_file':      env_file,
            'filename':      fname,
            'settings_path': settings_path,
        })
    return versions

def _read_settings_path(env_file, version):
    try:
        with open(env_file, 'r', encoding='latin-1') as f:
            for line in f:
                m = re.match(r'CATUserSettingPath\s*=\s*(.+)', line.strip())
                if m:
                    raw = m.group(1).strip()
                    raw = raw.replace('CSIDL_APPDATA', os.environ.get('APPDATA', ''))
                    return os.path.normpath(raw)
    except Exception:
        pass
    return os.path.join(os.environ.get('APPDATA', ''), 'DassaultSystemes', f'CATSettings{version}')

class PickerDialog(wx.Dialog):
    def __init__(self, parent, versions):
        super().__init__(parent, title="Open CATIA Settings Folder",
                         style=wx.DEFAULT_DIALOG_STYLE | wx.STAY_ON_TOP)

        vbox = wx.BoxSizer(wx.VERTICAL)

        vbox.Add(wx.StaticText(self, label="Select a version to open:"), 0, wx.LEFT | wx.RIGHT | wx.TOP, 12)
        choices = [f"{v['version']}  —  {v['settings_path']}" for v in versions]
        self.listbox = wx.ListBox(self, choices=choices, style=wx.LB_SINGLE)
        self.listbox.SetSelection(0)
        self.listbox.Bind(wx.EVT_LISTBOX_DCLICK, self._on_dclick)
        vbox.Add(self.listbox, 1, wx.ALL | wx.EXPAND, 12)

        btn_sizer  = wx.StdDialogButtonSizer()
        btn_ok     = wx.Button(self, wx.ID_OK,     label="Open")
        btn_cancel = wx.Button(self, wx.ID_CANCEL, label="Cancel")
        btn_ok.SetDefault()
        btn_sizer.AddButton(btn_ok)
        btn_sizer.AddButton(btn_cancel)
        btn_sizer.Realize()
        vbox.Add(btn_sizer, 0, wx.ALL | wx.EXPAND, 10)

        self.SetSizer(vbox)
        vbox.Fit(self)
        self.Center()

    def _on_dclick(self, _event):
        self.EndModal(wx.ID_OK)

if __name__ == "__main__":
    app = wx.App(None)

    versions = detect_versions()

    if not versions:
        wx.MessageDialog(None,
            f"No CATIA V5 environment files found in:\n{CATENV_DIR}",
            "No Versions Found", wx.OK | wx.ICON_WARNING | wx.STAY_ON_TOP).ShowModal()
        exit()

    dlg = PickerDialog(None, versions)
    wx.CallAfter(_bring_to_front, dlg)
    if dlg.ShowModal() != wx.ID_OK:
        dlg.Destroy()
        exit()

    sel  = dlg.listbox.GetSelection()
    dlg.Destroy()

    if sel == wx.NOT_FOUND:
        exit()

    v    = versions[sel]
    path = v['settings_path']

    if not os.path.isdir(path):
        wx.MessageDialog(None,
            f"Settings folder does not exist yet for {v['version']}:\n\n{path}\n\n"
            "Launch CATIA once to generate it.",
            "Folder Not Found", wx.OK | wx.ICON_WARNING | wx.STAY_ON_TOP).ShowModal()
        exit()

    subprocess.Popen(["explorer", path])
    print(f"Opened: {path}")

    print("\n\n Completed\n\n")
