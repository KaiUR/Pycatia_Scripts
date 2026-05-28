'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Clear_CATIA_Temp_Files.py
    Version:        1.0
    Code:           Python3.10+
    Release:        N/A
    Purpose:        Delete accumulated files from CATTemp and CATReport folders for selected CATIA V5 versions.
    Author:         Kai-Uwe Rathjen
    Date:           28.05.26
    Description:    Scans C:\\ProgramData\\DassaultSystemes\\CATEnv\\ for installed CATIA V5 versions and
                    resolves the CATTemp and CATReport paths from each environment file. Presents a dialog
                    to select which versions and which folder types to clear. Files inside are deleted;
                    the folders themselves are kept. Use when CATIA is sluggish or reporting unusual
                    behaviour due to accumulated temporary output. CATIA must be closed before clearing.
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

_CSIDL_MAP = {
    'CSIDL_APPDATA':    lambda: os.environ.get('APPDATA', ''),
    'CSIDL_LOCAL_APPDATA': lambda: os.environ.get('LOCALAPPDATA', ''),
    'CSIDL_PERSONAL':   lambda: os.path.expanduser('~\\Documents'),
}

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

def _resolve_env_path(raw):
    for token, resolver in _CSIDL_MAP.items():
        raw = raw.replace(token, resolver())
    return os.path.normpath(raw)

def _read_env_key(env_file, key):
    try:
        with open(env_file, 'r', encoding='latin-1') as f:
            for line in f:
                m = re.match(rf'{re.escape(key)}\s*=\s*(.+)', line.strip())
                if m:
                    return _resolve_env_path(m.group(1).strip())
    except Exception:
        pass
    return None

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
        tmp_path    = _read_env_key(env_file, 'CATTemp')
        report_path = _read_env_key(env_file, 'CATReport')
        versions.append({
            'version':       version,
            'env_file':      env_file,
            'filename':      fname,
            'CATTemp':       tmp_path,
            'CATReport':     report_path,
        })
    return versions

def _delete_folder_contents(folder):
    deleted = 0
    errors  = []
    for entry in os.scandir(folder):
        try:
            if entry.is_dir(follow_symlinks=False):
                import shutil
                shutil.rmtree(entry.path)
            else:
                os.remove(entry.path)
            deleted += 1
        except Exception as e:
            errors.append(f"{entry.name}: {e}")
    return deleted, errors

class ClearDialog(wx.Dialog):
    def __init__(self, parent, versions):
        super().__init__(parent, title="Clear CATIA Temp Files",
                         style=wx.DEFAULT_DIALOG_STYLE | wx.STAY_ON_TOP)

        vbox = wx.BoxSizer(wx.VERTICAL)

        warn = wx.StaticText(self, label="Close CATIA before clearing. Files inside the selected\nfolders will be deleted; the folders themselves are kept.")
        warn.SetForegroundColour(wx.Colour(180, 100, 0))
        vbox.Add(warn, 0, wx.ALL, 12)

        vbox.Add(wx.StaticText(self, label="Select versions to clear:"), 0, wx.LEFT | wx.RIGHT, 12)
        self.checklist = wx.CheckListBox(self, choices=[
            f"{v['version']}  —  {v['filename']}" for v in versions
        ])
        for i in range(len(versions)):
            self.checklist.Check(i, True)
        vbox.Add(self.checklist, 1, wx.ALL | wx.EXPAND, 12)

        self.chk_temp   = wx.CheckBox(self, label="Clear CATTemp   (temporary session files)")
        self.chk_report = wx.CheckBox(self, label="Clear CATReport  (batch reports and logs)")
        self.chk_temp.SetValue(True)
        self.chk_report.SetValue(True)
        vbox.Add(self.chk_temp,   0, wx.LEFT | wx.RIGHT, 12)
        vbox.Add(self.chk_report, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        btn_sizer  = wx.StdDialogButtonSizer()
        btn_ok     = wx.Button(self, wx.ID_OK,     label="Clear")
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

    dlg = ClearDialog(None, versions)
    wx.CallAfter(_bring_to_front, dlg)
    if dlg.ShowModal() != wx.ID_OK:
        dlg.Destroy()
        exit()

    checked     = dlg.checklist.GetCheckedItems()
    do_temp     = dlg.chk_temp.GetValue()
    do_report   = dlg.chk_report.GetValue()
    dlg.Destroy()

    if not checked:
        wx.MessageDialog(None, "No versions selected.", "Nothing to do",
                wx.OK | wx.ICON_INFORMATION | wx.STAY_ON_TOP).ShowModal()
        exit()

    if not do_temp and not do_report:
        wx.MessageDialog(None, "No folder types selected.", "Nothing to do",
                wx.OK | wx.ICON_INFORMATION | wx.STAY_ON_TOP).ShowModal()
        exit()

    lines = []
    for i in checked:
        v = versions[i]
        lines.append(f"=== {v['version']} ===")

        for key, do_it in [('CATTemp', do_temp), ('CATReport', do_report)]:
            if not do_it:
                continue
            path = v[key]
            if not path:
                lines.append(f"  {key}  :  SKIPPED — key not found in environment file")
                print(f"  {v['version']} {key}: SKIPPED — key not found")
                continue
            if not os.path.isdir(path):
                lines.append(f"  {key}  :  SKIPPED — folder not found:\n    {path}")
                print(f"  {v['version']} {key}: SKIPPED — not found: {path}")
                continue
            deleted, errors = _delete_folder_contents(path)
            if errors:
                lines.append(f"  {key}  :  {deleted} deleted, {len(errors)} error(s):")
                for err in errors:
                    lines.append(f"    {err}")
            else:
                lines.append(f"  {key}  :  {deleted} item(s) deleted")
            print(f"  {v['version']} {key}: {deleted} deleted, {len(errors)} error(s)")

        lines.append("")

    result_text = "\n".join(lines)
    results_dlg = wx.lib.dialogs.ScrolledMessageDialog(None, result_text, "Clear Results", size=(520, 360))
    wx.CallAfter(_bring_to_front, results_dlg)
    results_dlg.ShowModal()

    print("\n\n Completed\n\n")
