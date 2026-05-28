'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Downgrade_CATIA_File_Version.py
    Version:        1.0
    Code:           Python3.10+
    Release:        N/A
    Purpose:        Patch CATIA V5 files to open in an older release of CATIA.
    Author:         Kai-Uwe Rathjen
    Date:           28.05.26
    Description:    Reads the embedded version tag from .CATPart, .CATProduct, .CATProcess
                    and .CATDrawing files and rewrites it to a lower release number, allowing
                    the file to be opened in an older CATIA V5 installation. A patched copy
                    is saved alongside the original — the original is never modified.
                    Note: if the file uses geometry or features introduced in the saved
                    release, CATIA may still fail to load it even after patching.
    dependencies = [
                    "wxPython",
                    ]
    requirements:   Python >= 3.10
                    wxPython
    -----------------------------------------------------------------------------------------------------------------------

    Change:

    -----------------------------------------------------------------------------------------------------------------------
'''

import os
import re
import ctypes
import wx
import wx.lib.dialogs

V5_MAGIC = (b'V5_CFV2', b'V5_CFV4')

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

def detect_version(data):
    if not any(data.startswith(m) for m in V5_MAGIC):
        return None, None, None
    m = re.search(rb'V5R(\d+)SP(\d+)HF(\d+)', data)
    if m:
        return int(m.group(1)), int(m.group(2)), int(m.group(3))
    return None, None, None

def _replace_bytes(data, old, new):
    result = bytearray(data)
    olen = len(old)
    i = 0
    while True:
        idx = result.find(old, i)
        if idx == -1:
            break
        result[idx:idx + olen] = new
        i = idx + olen
    return bytes(result)

def patch_data(data, src_release, tgt_release):
    src_r = str(src_release).encode()
    tgt_r = str(tgt_release).encode()

    # Replace every V5RxxSPxHFx variant (SP/HF digits may vary; keep them as-is)
    prefix_len = len(b'V5R') + len(src_r)
    for variant in set(re.findall(rb'V5R' + src_r + rb'SP\d+HF\d+', data)):
        new_variant = b'V5R' + tgt_r + variant[prefix_len:]
        data = _replace_bytes(data, variant, new_variant)

    # Replace CATIAV5Rxx  (MinimalVersionToRead / VersionToRead values)
    data = _replace_bytes(data, b'CATIAV5R' + src_r, b'CATIAV5R' + tgt_r)

    # Replace <Release>xx/<Release>  in the save-version XML block
    data = _replace_bytes(data,
        b'<Release>' + src_r + b'/<Release>',
        b'<Release>' + tgt_r + b'/<Release>')

    return data

def output_path(src_path, tgt_release):
    stem, ext = os.path.splitext(src_path)
    return f'{stem}_R{tgt_release}{ext}'

class PatchDialog(wx.Dialog):
    def __init__(self, parent, file_info):
        super().__init__(parent, title="Downgrade CATIA File Version",
                         style=wx.DEFAULT_DIALOG_STYLE | wx.STAY_ON_TOP)

        vbox = wx.BoxSizer(wx.VERTICAL)

        vbox.Add(wx.StaticText(self, label="Files to patch:"), 0, wx.LEFT | wx.RIGHT | wx.TOP, 12)

        self.list_ctrl = wx.ListCtrl(self, size=(520, 120), style=wx.LC_REPORT | wx.BORDER_SIMPLE)
        self.list_ctrl.InsertColumn(0, "File",            width=230)
        self.list_ctrl.InsertColumn(1, "Current version", width=140)
        self.list_ctrl.InsertColumn(2, "Status",          width=130)

        self.valid = []
        max_release = 11
        for path, release, sp, hf in file_info:
            row = self.list_ctrl.GetItemCount()
            self.list_ctrl.InsertItem(row, os.path.basename(path))
            if release is not None:
                self.list_ctrl.SetItem(row, 1, f"R{release}  SP{sp}  HF{hf}")
                self.list_ctrl.SetItem(row, 2, "Ready")
                self.valid.append((path, release, sp, hf))
                if release > max_release:
                    max_release = release
            else:
                self.list_ctrl.SetItem(row, 1, "—")
                self.list_ctrl.SetItem(row, 2, "Not a V5 file")

        vbox.Add(self.list_ctrl, 0, wx.ALL | wx.EXPAND, 12)

        spin_row = wx.BoxSizer(wx.HORIZONTAL)
        spin_row.Add(wx.StaticText(self, label="Target release:  R"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.spin = wx.SpinCtrl(self, min=10, max=max_release - 1,
                                value=str(max_release - 1), size=(60, -1))
        spin_row.Add(self.spin, 0, wx.ALIGN_CENTER_VERTICAL)
        vbox.Add(spin_row, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)

        note = wx.StaticText(self,
            label="Patched copies are saved alongside the originals. Originals are not modified.\n"
                  "Note: this may not always work — if the file uses features or data structures\n"
                  "introduced in the saved release, CATIA may still refuse to open it.")
        note.SetForegroundColour(wx.Colour(128, 128, 128))
        vbox.Add(note, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)

        btn_sizer  = wx.StdDialogButtonSizer()
        btn_ok     = wx.Button(self, wx.ID_OK,     label="Patch")
        btn_cancel = wx.Button(self, wx.ID_CANCEL, label="Cancel")
        btn_ok.SetDefault()
        btn_sizer.AddButton(btn_ok)
        btn_sizer.AddButton(btn_cancel)
        btn_sizer.Realize()
        vbox.Add(btn_sizer, 0, wx.ALL | wx.EXPAND, 10)

        self.SetSizer(vbox)
        vbox.Fit(self)
        self.Center()

if __name__ == '__main__':
    app = wx.App(None)

    wildcard = "CATIA V5 Files|*.CATPart;*.CATProduct;*.CATProcess;*.CATDrawing|All Files|*.*"
    picker = wx.FileDialog(None, "Select CATIA files to patch",
                           wildcard=wildcard,
                           style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST | wx.FD_MULTIPLE)
    if picker.ShowModal() != wx.ID_OK:
        picker.Destroy()
        exit()
    paths = picker.GetPaths()
    picker.Destroy()

    file_info = []
    for path in paths:
        with open(path, 'rb') as f:
            data = f.read()
        release, sp, hf = detect_version(data)
        file_info.append((path, release, sp, hf))

    if not any(r is not None for _, r, _, _ in file_info):
        wx.MessageDialog(None, "None of the selected files are valid CATIA V5 files.",
                         "Error", wx.OK | wx.ICON_ERROR | wx.STAY_ON_TOP).ShowModal()
        exit()

    dlg = PatchDialog(None, file_info)
    wx.CallAfter(_bring_to_front, dlg)
    if dlg.ShowModal() != wx.ID_OK:
        dlg.Destroy()
        exit()

    tgt_release = dlg.spin.GetValue()
    valid_files  = dlg.valid
    dlg.Destroy()

    lines = []
    for path, src_release, sp, hf in valid_files:
        if tgt_release >= src_release:
            lines.append(f"  {os.path.basename(path)}  :  SKIPPED — R{tgt_release} is not older than R{src_release}")
            continue
        if len(str(tgt_release)) != len(str(src_release)):
            lines.append(f"  {os.path.basename(path)}  :  SKIPPED — R{src_release} and R{tgt_release} have different digit counts")
            continue
        try:
            with open(path, 'rb') as f:
                data = f.read()
            patched = patch_data(data, src_release, tgt_release)
            out = output_path(path, tgt_release)
            with open(out, 'wb') as f:
                f.write(patched)
            lines.append(f"  {os.path.basename(path)}  ->  {os.path.basename(out)}")
            print(f"  Patched: {path} -> {out}")
        except Exception as e:
            lines.append(f"  {os.path.basename(path)}  :  ERROR — {e}")
            print(f"  ERROR: {path}: {e}")

    result_dlg = wx.lib.dialogs.ScrolledMessageDialog(
        None, "\n".join(lines), "Patch Results", size=(560, 280))
    wx.CallAfter(_bring_to_front, result_dlg)
    result_dlg.ShowModal()

    print("\n\n Completed\n\n")
