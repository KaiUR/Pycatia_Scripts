'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Backup_CATIA_Settings.py
    Version:        1.0
    Code:           Python3.10+
    Release:        N/A
    Purpose:        Zip up the CATSettings folder for selected CATIA V5 versions to a chosen backup location.
    Author:         Kai-Uwe Rathjen
    Date:           28.05.26
    Description:    Scans C:\\ProgramData\\DassaultSystemes\\CATEnv\\ for installed CATIA V5 versions and
                    reads the CATUserSettingPath for each. Presents a dialog to select which versions to
                    back up and where to save the zip files. Each version is saved as a separate zip named
                    CATSettings_<version>_<timestamp>.zip. Use before upgrades, migrations, or settings
                    changes to preserve a restorable snapshot.
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
import zipfile
import ctypes
import datetime
import wx
import wx.lib.dialogs

CATENV_DIR   = r"C:\ProgramData\DassaultSystemes\CATEnv"
DEFAULT_DEST = os.path.join(os.path.expanduser("~"), "Desktop")

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
        build   = match.group(1)
        version = f"R{match.group(2)}"
        env_file = os.path.join(CATENV_DIR, fname)
        settings_path = _read_settings_path(env_file, version)
        versions.append({
            'build':         build,
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

def zip_folder(src_dir, dest_zip):
    with zipfile.ZipFile(dest_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(src_dir):
            for file in files:
                abs_path = os.path.join(root, file)
                arcname  = os.path.relpath(abs_path, os.path.dirname(src_dir))
                zf.write(abs_path, arcname)

class BackupDialog(wx.Dialog):
    def __init__(self, parent, versions):
        super().__init__(parent, title="Backup CATIA Settings",
                         style=wx.DEFAULT_DIALOG_STYLE | wx.STAY_ON_TOP)

        vbox = wx.BoxSizer(wx.VERTICAL)

        vbox.Add(wx.StaticText(self, label="Select versions to back up:"), 0, wx.LEFT | wx.RIGHT | wx.TOP, 12)
        self.checklist = wx.CheckListBox(self, choices=[
            f"{v['version']}  —  {v['settings_path']}" for v in versions
        ])
        for i in range(len(versions)):
            self.checklist.Check(i, True)
        vbox.Add(self.checklist, 1, wx.ALL | wx.EXPAND, 12)

        dest_row = wx.BoxSizer(wx.HORIZONTAL)
        dest_row.Add(wx.StaticText(self, label="Save to:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.dest_ctrl = wx.TextCtrl(self, value=DEFAULT_DEST)
        dest_row.Add(self.dest_ctrl, 1, wx.EXPAND)
        btn_browse = wx.Button(self, label="Browse...")
        btn_browse.Bind(wx.EVT_BUTTON, self._on_browse)
        dest_row.Add(btn_browse, 0, wx.LEFT, 6)
        vbox.Add(dest_row, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 12)

        btn_sizer  = wx.StdDialogButtonSizer()
        btn_ok     = wx.Button(self, wx.ID_OK,     label="Backup")
        btn_cancel = wx.Button(self, wx.ID_CANCEL, label="Cancel")
        btn_ok.SetDefault()
        btn_sizer.AddButton(btn_ok)
        btn_sizer.AddButton(btn_cancel)
        btn_sizer.Realize()
        vbox.Add(btn_sizer, 0, wx.ALL | wx.EXPAND, 10)

        self.SetSizer(vbox)
        vbox.Fit(self)
        self.Center()

    def _on_browse(self, _event):
        dlg = wx.DirDialog(self, "Choose backup destination", self.dest_ctrl.GetValue(),
                           style=wx.DD_DEFAULT_STYLE | wx.STAY_ON_TOP)
        if dlg.ShowModal() == wx.ID_OK:
            self.dest_ctrl.SetValue(dlg.GetPath())
        dlg.Destroy()

if __name__ == "__main__":
    app = wx.App(None)

    versions = detect_versions()

    if not versions:
        wx.MessageDialog(None,
            f"No CATIA V5 environment files found in:\n{CATENV_DIR}",
            "No Versions Found", wx.OK | wx.ICON_WARNING | wx.STAY_ON_TOP).ShowModal()
        exit()

    dlg = BackupDialog(None, versions)
    wx.CallAfter(_bring_to_front, dlg)
    if dlg.ShowModal() != wx.ID_OK:
        dlg.Destroy()
        exit()

    checked  = dlg.checklist.GetCheckedItems()
    dest_dir = dlg.dest_ctrl.GetValue().strip()
    dlg.Destroy()

    if not checked:
        wx.MessageDialog(None, "No versions selected.", "Nothing to do",
                wx.OK | wx.ICON_INFORMATION | wx.STAY_ON_TOP).ShowModal()
        exit()

    if not os.path.isdir(dest_dir):
        wx.MessageDialog(None, f"Destination folder does not exist:\n{dest_dir}", "Error",
                wx.OK | wx.ICON_ERROR | wx.STAY_ON_TOP).ShowModal()
        exit()

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    lines     = []

    for i in checked:
        v    = versions[i]
        src  = v['settings_path']
        name = f"CATSettings_{v['version']}_{timestamp}.zip"
        dest = os.path.join(dest_dir, name)

        if not os.path.isdir(src):
            lines.append(f"  {v['version']}  :  SKIPPED — settings folder not found:\n    {src}")
            print(f"  {v['version']}: SKIPPED — folder not found: {src}")
            continue

        try:
            zip_folder(src, dest)
            lines.append(f"  {v['version']}  :  Saved  ->  {dest}")
            print(f"  {v['version']}: Saved -> {dest}")
        except Exception as e:
            lines.append(f"  {v['version']}  :  ERROR — {e}")
            print(f"  {v['version']}: ERROR — {e}")

    result_text = "\n".join(lines)
    results_dlg = wx.lib.dialogs.ScrolledMessageDialog(None, result_text, "Backup Results", size=(560, 320))
    wx.CallAfter(_bring_to_front, results_dlg)
    results_dlg.ShowModal()

    print("\n\n Completed\n\n")
