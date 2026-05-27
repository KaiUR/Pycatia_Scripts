'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Configure_CATIA_Version_Settings.py
    Version:        1.0
    Code:           Python3.10+
    Release:        N/A
    Purpose:        Configure per-version settings paths and window titles for all installed CATIA V5 versions.
    Author:         Kai-Uwe Rathjen
    Date:           27.05.26
    Description:    Scans C:\\ProgramData\\DassaultSystemes\\CATEnv\\ for installed CATIA V5 environment
                    files and applies two optional changes to each selected version:
                    1. Updates CATUserSettingPath to a version-specific folder so settings are
                       preserved independently between versions (e.g. CATSettingsR32).
                    2. Updates the window title in CATIA.CATNls so each version displays its
                       release number in the title bar (e.g. CATIA V5 R32).
                    Note: The first time the settings path is changed, CATIA will reset to defaults
                    for that version. Reopen CATIA once after applying to regenerate the settings.
                    Administrator privileges are required to write the window title (Program Files).
    dependencies = [
                    "wxPython",
                    ]
    requirements:   Python >= 3.10
                    wxPython
                    Administrator privileges required for window title changes (writes to Program Files).
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

CATENV_DIR   = r"C:\ProgramData\DassaultSystemes\CATEnv"
DASSAULT_DIR = r"C:\Program Files\Dassault Systemes"

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

'''
    Scans the CATEnv directory for CATIA environment files and returns a list of
    detected versions, each as a dict with keys: build, version, env_file, filename.
    e.g. CATIA_P3.V5-6R2022.B32.txt -> build="B32", version="R32"
'''
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
        build   = match.group(1)                                                            #e.g. "B32"
        version = f"R{match.group(2)}"                                                      #e.g. "R32"
        versions.append({
            'build':    build,
            'version':  version,
            'env_file': os.path.join(CATENV_DIR, fname),
            'filename': fname,
        })
    return versions

'''
    Updates the CATUserSettingPath line in the given environment file to use new_suffix.
    Handles the case where the path has already been modified with a previous suffix.
    Returns (changed: bool, error_msg: str).
'''
def apply_settings_path(env_file, new_suffix):
    try:
        with open(env_file, 'r', encoding='latin-1') as f:
            content = f.read()
        replacement = f"CATUserSettingPath=CSIDL_APPDATA\\DassaultSystemes\\CATSettings{new_suffix}"
        new_content, n = re.subn(
            r'CATUserSettingPath=CSIDL_APPDATA\\DassaultSystemes\\CATSettings[^\r\n]*',
            lambda m: replacement,
            content
        )
        if n == 0:
            return False, "CATUserSettingPath line not found"
        if new_content == content:
            return False, "Already set — no change needed"
        with open(env_file, 'w', encoding='latin-1') as f:
            f.write(new_content)
        return True, ""
    except PermissionError:
        return False, "Permission denied — run as Administrator"
    except Exception as e:
        return False, str(e)

'''
    Updates ApplicationFrame.Title in the CATIA.CATNls file for the given build.
    Returns (changed: bool, error_msg: str).
'''
def apply_window_title(build, new_title):
    nls_path = os.path.join(DASSAULT_DIR, build, 'win_b64', 'resources', 'msgcatalog', 'CATIA.CATNls')
    if not os.path.isfile(nls_path):
        return False, f"CATIA.CATNls not found at {nls_path}"
    try:
        with open(nls_path, 'r', encoding='latin-1') as f:
            content = f.read()
        new_content, n = re.subn(
            r'(ApplicationFrame\.Title\s*=\s*")[^"]*(")',
            lambda m: f'{m.group(1)}{new_title}{m.group(2)}',
            content
        )
        if n == 0:
            return False, "ApplicationFrame.Title line not found"
        if new_content == content:
            return False, "Already set — no change needed"
        with open(nls_path, 'w', encoding='latin-1') as f:
            f.write(new_content)
        return True, ""
    except PermissionError:
        return False, "Permission denied — run as Administrator"
    except Exception as e:
        return False, str(e)

class ConfigDialog(wx.Dialog):
    def __init__(self, parent, versions):
        super().__init__(parent, title="Configure CATIA Version Settings",
                         size=(540, 460), style=wx.DEFAULT_DIALOG_STYLE | wx.STAY_ON_TOP)

        vbox = wx.BoxSizer(wx.VERTICAL)

        warn = wx.StaticText(self, label=(
            "Warning: Changing the settings path will reset CATIA settings to\n"
            "defaults for that version on first launch. Administrator privileges\n"
            "are required for window title changes."
        ))
        warn.SetForegroundColour(wx.Colour(180, 100, 0))
        vbox.Add(warn, 0, wx.ALL, 12)

        vbox.Add(wx.StaticText(self, label="Detected versions:"), 0, wx.LEFT | wx.RIGHT, 12)
        self.checklist = wx.CheckListBox(self, choices=[
            f"{v['version']}  —  {v['filename']}" for v in versions
        ])
        for i in range(len(versions)):
            self.checklist.Check(i, True)                                                   #Check all by default
        vbox.Add(self.checklist, 1, wx.ALL | wx.EXPAND, 12)

        grid = wx.FlexGridSizer(2, 2, 8, 10)

        grid.Add(wx.StaticText(self, label="Settings folder suffix:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.settings_fmt = wx.TextCtrl(self, value="{version}")
        self.settings_fmt.SetToolTip(
            "Appended to CATSettings — {version} is replaced with e.g. R32.\n"
            "Default {version} gives CATSettingsR32."
        )
        grid.Add(self.settings_fmt, 1, wx.EXPAND)

        grid.Add(wx.StaticText(self, label="Window title:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.title_fmt = wx.TextCtrl(self, value="CATIA V5 {version}")
        self.title_fmt.SetToolTip("{version} is replaced with e.g. R32.")
        grid.Add(self.title_fmt, 1, wx.EXPAND)

        grid.AddGrowableCol(1, 1)
        vbox.Add(grid, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 12)

        self.chk_settings = wx.CheckBox(self, label="Update settings path (CATEnv files)")
        self.chk_title    = wx.CheckBox(self, label="Update window title (CATIA.CATNls)")
        self.chk_settings.SetValue(True)
        self.chk_title.SetValue(True)
        vbox.Add(self.chk_settings, 0, wx.LEFT | wx.RIGHT, 12)
        vbox.Add(self.chk_title,    0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        btn_sizer  = wx.StdDialogButtonSizer()
        btn_ok     = wx.Button(self, wx.ID_OK,     label="Apply")
        btn_cancel = wx.Button(self, wx.ID_CANCEL, label="Cancel")
        btn_ok.SetDefault()
        btn_sizer.AddButton(btn_ok)
        btn_sizer.AddButton(btn_cancel)
        btn_sizer.Realize()
        vbox.Add(btn_sizer, 0, wx.ALL | wx.EXPAND, 10)

        self.SetSizer(vbox)
        self.Center()

if __name__ == "__main__":
    app = wx.App(None)                                                                      #Initialize wx application

    versions = detect_versions()

    if not versions:
        wx.MessageDialog(None,
            f"No CATIA V5 environment files found in:\n{CATENV_DIR}",
            "No Versions Found", wx.OK | wx.ICON_WARNING | wx.STAY_ON_TOP).ShowModal()
        exit()

    dlg = ConfigDialog(None, versions)
    wx.CallAfter(_bring_to_front, dlg)
    if dlg.ShowModal() != wx.ID_OK:
        dlg.Destroy()
        exit()

    checked  = dlg.checklist.GetCheckedItems()
    sfx_fmt  = dlg.settings_fmt.GetValue().strip()
    ttl_fmt  = dlg.title_fmt.GetValue().strip()
    do_sfx   = dlg.chk_settings.GetValue()
    do_ttl   = dlg.chk_title.GetValue()
    dlg.Destroy()

    if not checked:
        wx.MessageDialog(None, "No versions selected.", "Nothing to do",
                wx.OK | wx.ICON_INFORMATION | wx.STAY_ON_TOP).ShowModal()
        exit()

    lines = []
    for i in checked:
        v       = versions[i]
        ver     = v['version']
        suffix  = sfx_fmt.replace("{version}", ver)
        title   = ttl_fmt.replace("{version}", ver)

        lines.append(f"=== {ver} ({v['filename']}) ===")

        if do_sfx:
            changed, err = apply_settings_path(v['env_file'], suffix)
            if err:
                lines.append(f"  Settings path : SKIPPED — {err}")
                print(f"  {ver} settings path: SKIPPED — {err}")
            elif changed:
                lines.append(f"  Settings path : Updated  ->  CATSettings{suffix}")
                print(f"  {ver} settings path: Updated -> CATSettings{suffix}")
            else:
                lines.append(f"  Settings path : No change")
                print(f"  {ver} settings path: No change")

        if do_ttl:
            changed, err = apply_window_title(v['build'], title)
            if err:
                lines.append(f"  Window title  : SKIPPED — {err}")
                print(f"  {ver} window title : SKIPPED — {err}")
            elif changed:
                lines.append(f"  Window title  : Updated  ->  \"{title}\"")
                print(f"  {ver} window title : Updated -> \"{title}\"")
            else:
                lines.append(f"  Window title  : No change")
                print(f"  {ver} window title : No change")

        lines.append("")

    result_text = "\n".join(lines)

    results_dlg = wx.lib.dialogs.ScrolledMessageDialog(None, result_text, "Results", size=(520, 380))
    wx.CallAfter(_bring_to_front, results_dlg)
    results_dlg.ShowModal()

    print("\n\n Completed\n\n")
