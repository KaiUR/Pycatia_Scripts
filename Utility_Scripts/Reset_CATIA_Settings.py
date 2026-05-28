'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Reset_CATIA_Settings.py
    Version:        1.0
    Code:           Python3.10+
    Release:        N/A
    Purpose:        Delete the CATSettings folder for selected CATIA V5 versions to force a clean defaults reset.
    Author:         Kai-Uwe Rathjen
    Date:           28.05.26
    Description:    Scans C:\\ProgramData\\DassaultSystemes\\CATEnv\\ for installed CATIA V5 versions and
                    reads the CATUserSettingPath for each. After confirmation, deletes the settings folder
                    for each selected version. CATIA will regenerate a fresh defaults folder on next
                    launch. Use to resolve persistent settings corruption or to start from a clean slate.
                    Consider running Backup_CATIA_Settings.py first.
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
import shutil
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

class ResetDialog(wx.Dialog):
    def __init__(self, parent, versions):
        super().__init__(parent, title="Reset CATIA Settings",
                         style=wx.DEFAULT_DIALOG_STYLE | wx.STAY_ON_TOP)

        vbox = wx.BoxSizer(wx.VERTICAL)

        warn = wx.StaticText(self, label=(
            "Warning: This permanently deletes the selected settings folders.\n"
            "CATIA will reset to factory defaults on next launch.\n"
            "Run Backup_CATIA_Settings.py first if you want to preserve current settings."
        ))
        warn.SetForegroundColour(wx.Colour(180, 40, 40))
        vbox.Add(warn, 0, wx.ALL, 12)

        vbox.Add(wx.StaticText(self, label="Select versions to reset:"), 0, wx.LEFT | wx.RIGHT, 12)
        self.checklist = wx.CheckListBox(self, choices=[
            f"{v['version']}  —  {v['settings_path']}" for v in versions
        ])
        vbox.Add(self.checklist, 1, wx.ALL | wx.EXPAND, 12)

        btn_sizer  = wx.StdDialogButtonSizer()
        btn_ok     = wx.Button(self, wx.ID_OK,     label="Reset")
        btn_cancel = wx.Button(self, wx.ID_CANCEL, label="Cancel")
        btn_ok.SetDefault()
        btn_sizer.AddButton(btn_ok)
        btn_sizer.AddButton(btn_cancel)
        btn_sizer.Realize()
        vbox.Add(btn_sizer, 0, wx.ALL | wx.EXPAND, 10)

        self.SetSizer(vbox)
        vbox.Fit(self)
        self.Center()

if __name__ == "__main__":
    app = wx.App(None)

    versions = detect_versions()

    if not versions:
        wx.MessageDialog(None,
            f"No CATIA V5 environment files found in:\n{CATENV_DIR}",
            "No Versions Found", wx.OK | wx.ICON_WARNING | wx.STAY_ON_TOP).ShowModal()
        exit()

    dlg = ResetDialog(None, versions)
    wx.CallAfter(_bring_to_front, dlg)
    if dlg.ShowModal() != wx.ID_OK:
        dlg.Destroy()
        exit()

    checked = dlg.checklist.GetCheckedItems()
    dlg.Destroy()

    if not checked:
        wx.MessageDialog(None, "No versions selected.", "Nothing to do",
                wx.OK | wx.ICON_INFORMATION | wx.STAY_ON_TOP).ShowModal()
        exit()

    names = "\n".join(f"  {versions[i]['version']}  ({versions[i]['settings_path']})" for i in checked)
    confirm = wx.MessageDialog(None,
        f"Permanently delete settings for:\n\n{names}\n\nThis cannot be undone. Continue?",
        "Confirm Reset", wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING | wx.STAY_ON_TOP)
    wx.CallAfter(_bring_to_front, confirm)
    if confirm.ShowModal() != wx.ID_YES:
        exit()

    lines = []
    for i in checked:
        v   = versions[i]
        src = v['settings_path']
        if not os.path.isdir(src):
            lines.append(f"  {v['version']}  :  SKIPPED — folder not found:\n    {src}")
            print(f"  {v['version']}: SKIPPED — folder not found: {src}")
            continue
        try:
            shutil.rmtree(src)
            lines.append(f"  {v['version']}  :  Deleted  —  {src}")
            print(f"  {v['version']}: Deleted — {src}")
        except PermissionError:
            lines.append(f"  {v['version']}  :  ERROR — Permission denied (close CATIA first)")
            print(f"  {v['version']}: ERROR — Permission denied")
        except Exception as e:
            lines.append(f"  {v['version']}  :  ERROR — {e}")
            print(f"  {v['version']}: ERROR — {e}")

    result_text = "\n".join(lines)
    wx.MessageDialog(None, result_text, "Reset Results",
            wx.OK | wx.ICON_INFORMATION | wx.STAY_ON_TOP).ShowModal()

    print("\n\n Completed\n\n")
