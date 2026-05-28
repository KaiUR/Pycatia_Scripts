'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Set_CATIA_Environment_Variable.py
    Version:        1.0
    Code:           Python3.10+
    Release:        N/A
    Purpose:        Add or update any key=value entry in CATIA V5 environment files for selected versions.
    Author:         Kai-Uwe Rathjen
    Date:           28.05.26
    Description:    Scans C:\\ProgramData\\DassaultSystemes\\CATEnv\\ for installed CATIA V5 environment
                    files. Presents a dialog to select target versions, enter a variable name and value,
                    and choose whether to add the key if missing or only update it if it already exists.
                    Useful for setting CATTemp, CATReport, CATReferenceSettingPath, or any other
                    documented CATIA environment variable across multiple versions at once.
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
import ctypes
import wx
import wx.lib.dialogs

CATENV_DIR = r"C:\ProgramData\DassaultSystemes\CATEnv"

COMMON_KEYS = [
    "CATTemp",
    "CATReport",
    "CATReferenceSettingPath",
    "CATUserSettingPath",
    "CATNoStartDocument",
    "CATInstallPath",
]

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
        versions.append({
            'version':  f"R{match.group(2)}",
            'env_file': os.path.join(CATENV_DIR, fname),
            'filename': fname,
        })
    return versions

def apply_env_variable(env_file, key, value, add_if_missing):
    try:
        with open(env_file, 'r', encoding='latin-1') as f:
            content = f.read()

        pattern     = re.compile(rf'^{re.escape(key)}\s*=.*$', re.MULTILINE)
        replacement = f"{key}={value}"
        has_key     = bool(pattern.search(content))

        if has_key:
            new_content = pattern.sub(replacement, content)
            if new_content == content:
                return False, "Already set — no change needed"
        elif add_if_missing:
            new_content = content.rstrip('\r\n') + f'\n{replacement}\n'
        else:
            return False, "Key not present (add-if-missing is off)"

        with open(env_file, 'w', encoding='latin-1') as f:
            f.write(new_content)
        return True, ""

    except PermissionError:
        return False, "Permission denied — run as Administrator"
    except Exception as e:
        return False, str(e)

class SetVarDialog(wx.Dialog):
    def __init__(self, parent, versions):
        super().__init__(parent, title="Set CATIA Environment Variable",
                         style=wx.DEFAULT_DIALOG_STYLE | wx.STAY_ON_TOP)

        vbox = wx.BoxSizer(wx.VERTICAL)

        vbox.Add(wx.StaticText(self, label="Select versions to update:"), 0, wx.LEFT | wx.RIGHT | wx.TOP, 12)
        self.checklist = wx.CheckListBox(self, choices=[
            f"{v['version']}  —  {v['filename']}" for v in versions
        ])
        for i in range(len(versions)):
            self.checklist.Check(i, True)
        vbox.Add(self.checklist, 1, wx.ALL | wx.EXPAND, 12)

        grid = wx.FlexGridSizer(2, 2, 8, 10)

        grid.Add(wx.StaticText(self, label="Variable name:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.key_ctrl = wx.ComboBox(self, choices=COMMON_KEYS, style=wx.CB_DROPDOWN)
        self.key_ctrl.SetToolTip("Enter a key name or choose a common one from the list.")
        grid.Add(self.key_ctrl, 1, wx.EXPAND)

        grid.Add(wx.StaticText(self, label="Value:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.val_ctrl = wx.TextCtrl(self)
        self.val_ctrl.SetToolTip("Value to assign. Use CSIDL_APPDATA for %%APPDATA%% paths.")
        grid.Add(self.val_ctrl, 1, wx.EXPAND)

        grid.AddGrowableCol(1, 1)
        vbox.Add(grid, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 12)

        self.chk_add = wx.CheckBox(self, label="Add key if not already present in the environment file")
        self.chk_add.SetValue(True)
        vbox.Add(self.chk_add, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)

        btn_sizer  = wx.StdDialogButtonSizer()
        btn_ok     = wx.Button(self, wx.ID_OK,     label="Apply")
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

    dlg = SetVarDialog(None, versions)
    wx.CallAfter(_bring_to_front, dlg)
    if dlg.ShowModal() != wx.ID_OK:
        dlg.Destroy()
        exit()

    checked        = dlg.checklist.GetCheckedItems()
    key            = dlg.key_ctrl.GetValue().strip()
    value          = dlg.val_ctrl.GetValue().strip()
    add_if_missing = dlg.chk_add.GetValue()
    dlg.Destroy()

    if not checked:
        wx.MessageDialog(None, "No versions selected.", "Nothing to do",
                wx.OK | wx.ICON_INFORMATION | wx.STAY_ON_TOP).ShowModal()
        exit()

    if not key:
        wx.MessageDialog(None, "No variable name entered.", "Nothing to do",
                wx.OK | wx.ICON_WARNING | wx.STAY_ON_TOP).ShowModal()
        exit()

    lines = []
    for i in checked:
        v = versions[i]
        changed, err = apply_env_variable(v['env_file'], key, value, add_if_missing)
        if err:
            status = f"SKIPPED — {err}"
        elif changed:
            status = f"Updated  ->  {key}={value}"
        else:
            status = "No change"
        lines.append(f"  {v['version']}  ({v['filename']})  :  {status}")
        print(f"  {v['version']}: {status}")

    result_text = "\n".join(lines)
    results_dlg = wx.lib.dialogs.ScrolledMessageDialog(None, result_text, "Results", size=(560, 300))
    wx.CallAfter(_bring_to_front, results_dlg)
    results_dlg.ShowModal()

    print("\n\n Completed\n\n")
