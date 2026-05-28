'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Restore_CATIA_Settings.py
    Version:        1.0
    Code:           Python3.10+
    Release:        N/A
    Purpose:        Restore a CATSettings folder from a zip backup created by Backup_CATIA_Settings.py.
    Author:         Kai-Uwe Rathjen
    Date:           28.05.26
    Description:    Presents a file picker to select a CATSettings backup zip (as created by
                    Backup_CATIA_Settings.py). The target version and settings path are auto-detected
                    from the zip filename (e.g. CATSettings_R32_20260528_143000.zip) and confirmed by
                    the user. Optionally backs up the current settings before overwriting. The existing
                    settings folder is cleared and the zip is extracted in its place. CATIA must be
                    closed before restoring.
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
import zipfile
import ctypes
import datetime
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
    versions = {}
    if not os.path.isdir(CATENV_DIR):
        return versions
    for fname in os.listdir(CATENV_DIR):
        if not fname.lower().endswith('.txt'):
            continue
        match = re.search(r'\.(B(\d+))\.txt$', fname, re.IGNORECASE)
        if not match:
            continue
        version  = f"R{match.group(2)}"
        env_file = os.path.join(CATENV_DIR, fname)
        versions[version] = _read_settings_path(env_file, version)
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

def _detect_version_from_filename(fname):
    m = re.match(r'CATSettings_(R\d+)_', os.path.basename(fname), re.IGNORECASE)
    return m.group(1) if m else None

def zip_folder(src_dir, dest_zip):
    with zipfile.ZipFile(dest_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(src_dir):
            for file in files:
                abs_path = os.path.join(root, file)
                arcname  = os.path.relpath(abs_path, os.path.dirname(src_dir))
                zf.write(abs_path, arcname)

class RestoreDialog(wx.Dialog):
    def __init__(self, parent, zip_path, detected_version, versions):
        super().__init__(parent, title="Restore CATIA Settings",
                         style=wx.DEFAULT_DIALOG_STYLE | wx.STAY_ON_TOP)

        vbox = wx.BoxSizer(wx.VERTICAL)

        warn = wx.StaticText(self, label="Close CATIA before restoring. The current settings folder\nwill be replaced with the contents of the selected backup.")
        warn.SetForegroundColour(wx.Colour(180, 100, 0))
        vbox.Add(warn, 0, wx.ALL, 12)

        grid = wx.FlexGridSizer(3, 2, 8, 10)

        grid.Add(wx.StaticText(self, label="Backup file:"), 0, wx.ALIGN_CENTER_VERTICAL)
        zip_label = wx.StaticText(self, label=os.path.basename(zip_path))
        zip_label.SetToolTip(zip_path)
        grid.Add(zip_label, 1, wx.EXPAND)

        grid.Add(wx.StaticText(self, label="Restore to version:"), 0, wx.ALIGN_CENTER_VERTICAL)
        version_choices = sorted(versions.keys())
        self.version_choice = wx.Choice(self, choices=version_choices)
        if detected_version and detected_version in versions:
            self.version_choice.SetSelection(version_choices.index(detected_version))
        elif version_choices:
            self.version_choice.SetSelection(0)
        self.version_choice.Bind(wx.EVT_CHOICE, self._on_version_change)
        grid.Add(self.version_choice, 1, wx.EXPAND)

        grid.Add(wx.StaticText(self, label="Destination:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.dest_label = wx.StaticText(self, label="")
        grid.Add(self.dest_label, 1, wx.EXPAND)

        grid.AddGrowableCol(1, 1)
        vbox.Add(grid, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 12)

        self.chk_backup = wx.CheckBox(self, label="Back up current settings before overwriting")
        self.chk_backup.SetValue(True)
        vbox.Add(self.chk_backup, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)

        btn_sizer  = wx.StdDialogButtonSizer()
        btn_ok     = wx.Button(self, wx.ID_OK,     label="Restore")
        btn_cancel = wx.Button(self, wx.ID_CANCEL, label="Cancel")
        btn_ok.SetDefault()
        btn_sizer.AddButton(btn_ok)
        btn_sizer.AddButton(btn_cancel)
        btn_sizer.Realize()
        vbox.Add(btn_sizer, 0, wx.ALL | wx.EXPAND, 10)

        self._versions = versions
        self.SetSizer(vbox)
        vbox.Fit(self)
        self.Center()
        self._update_dest_label()

    def _on_version_change(self, _event):
        self._update_dest_label()

    def _update_dest_label(self):
        sel = self.version_choice.GetStringSelection()
        if sel and sel in self._versions:
            self.dest_label.SetLabel(self._versions[sel])
        else:
            self.dest_label.SetLabel("")

    def get_selected_version(self):
        return self.version_choice.GetStringSelection()

    def get_dest_path(self):
        sel = self.get_selected_version()
        return self._versions.get(sel, "")

if __name__ == "__main__":
    app = wx.App(None)

    versions = detect_versions()

    file_dlg = wx.FileDialog(
        None,
        message="Select a CATSettings backup zip",
        wildcard="Zip files (*.zip)|*.zip",
        style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST | wx.STAY_ON_TOP
    )
    wx.CallAfter(_bring_to_front, file_dlg)
    if file_dlg.ShowModal() != wx.ID_OK:
        file_dlg.Destroy()
        exit()
    zip_path = file_dlg.GetPath()
    file_dlg.Destroy()

    if not zipfile.is_zipfile(zip_path):
        wx.MessageDialog(None, f"The selected file is not a valid zip archive:\n{zip_path}",
                "Invalid File", wx.OK | wx.ICON_ERROR | wx.STAY_ON_TOP).ShowModal()
        exit()

    detected_version = _detect_version_from_filename(zip_path)

    if not versions:
        wx.MessageDialog(None,
            f"No CATIA V5 environment files found in:\n{CATENV_DIR}\n\n"
            "Cannot determine the restore destination automatically.",
            "No Versions Found", wx.OK | wx.ICON_WARNING | wx.STAY_ON_TOP).ShowModal()
        exit()

    dlg = RestoreDialog(None, zip_path, detected_version, versions)
    wx.CallAfter(_bring_to_front, dlg)
    if dlg.ShowModal() != wx.ID_OK:
        dlg.Destroy()
        exit()

    target_version = dlg.get_selected_version()
    dest_path      = dlg.get_dest_path()
    do_backup      = dlg.chk_backup.GetValue()
    dlg.Destroy()

    if not target_version or not dest_path:
        wx.MessageDialog(None, "No target version selected.", "Nothing to do",
                wx.OK | wx.ICON_WARNING | wx.STAY_ON_TOP).ShowModal()
        exit()

    confirm = wx.MessageDialog(None,
        f"Restore backup to:\n\n  {dest_path}\n\n"
        f"The current contents of this folder will be replaced.\nContinue?",
        "Confirm Restore", wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING | wx.STAY_ON_TOP)
    wx.CallAfter(_bring_to_front, confirm)
    if confirm.ShowModal() != wx.ID_YES:
        exit()

    if do_backup and os.path.isdir(dest_path):
        timestamp   = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"CATSettings_{target_version}_{timestamp}_pre_restore.zip"
        backup_dest = os.path.join(os.path.dirname(zip_path), backup_name)
        try:
            zip_folder(dest_path, backup_dest)
            print(f"Pre-restore backup saved: {backup_dest}")
        except Exception as e:
            warn = wx.MessageDialog(None,
                f"Could not save pre-restore backup:\n{e}\n\nContinue with restore anyway?",
                "Backup Failed", wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING | wx.STAY_ON_TOP)
            if warn.ShowModal() != wx.ID_YES:
                exit()

    if os.path.isdir(dest_path):
        try:
            shutil.rmtree(dest_path)
        except PermissionError:
            wx.MessageDialog(None,
                f"Cannot clear existing settings folder — permission denied.\nClose CATIA and try again.\n\n{dest_path}",
                "Permission Denied", wx.OK | wx.ICON_ERROR | wx.STAY_ON_TOP).ShowModal()
            exit()
        except Exception as e:
            wx.MessageDialog(None, f"Failed to clear existing settings folder:\n{e}",
                    "Error", wx.OK | wx.ICON_ERROR | wx.STAY_ON_TOP).ShowModal()
            exit()

    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(os.path.dirname(dest_path))
        print(f"Restored {zip_path} -> {dest_path}")
        wx.MessageDialog(None,
            f"Settings restored successfully for {target_version}.\n\n{dest_path}",
            "Restore Complete", wx.OK | wx.ICON_INFORMATION | wx.STAY_ON_TOP).ShowModal()
    except Exception as e:
        wx.MessageDialog(None, f"Failed to extract backup:\n{e}",
                "Error", wx.OK | wx.ICON_ERROR | wx.STAY_ON_TOP).ShowModal()

    print("\n\n Completed\n\n")
