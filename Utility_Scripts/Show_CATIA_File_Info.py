'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Show_CATIA_File_Info.py
    Version:        1.0
    Code:           Python3.10+
    Release:        N/A
    Purpose:        Show name, dates, owner and CATIA version for selected files.
    Author:         Kai-Uwe Rathjen
    Date:           28.05.26
    Description:    Reads filesystem metadata and the embedded version tag from
                    .CATPart, .CATProduct, .CATProcess and .CATDrawing files and
                    displays the file name, full path, creation date/time, last-
                    modified date/time, file owner, and the full CATIA V5 version
                    broken down into release, service pack and hotfix with a plain-
                    English summary. No CATIA session is required.
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
import ctypes.wintypes
from datetime import datetime
import wx

V5_MAGIC    = (b'V5_CFV2', b'V5_CFV4')
_OWNER_INFO = 0x00000001                                                                                        # OWNER_SECURITY_INFORMATION


def _bring_to_front(window):
    u32   = ctypes.windll.user32
    hwnd  = window.GetHandle()
    fg    = u32.GetForegroundWindow()
    fg_t  = u32.GetWindowThreadProcessId(fg, None)
    our_t = ctypes.windll.kernel32.GetCurrentThreadId()
    if fg_t != our_t:
        u32.AttachThreadInput(fg_t, our_t, True)
    u32.SetWindowLongW(hwnd, -20, u32.GetWindowLongW(hwnd, -20) | 0x0008)
    u32.BringWindowToTop(hwnd)
    u32.SetForegroundWindow(hwnd)
    if fg_t != our_t:
        u32.AttachThreadInput(fg_t, our_t, False)


def detect_version(data):
    if not any(data.startswith(m) for m in V5_MAGIC):
        return None, None, None
    m = re.search(rb'V5R(\d+)SP(\d+)HF(\d+)', data)
    if m:
        return int(m.group(1)), int(m.group(2)), int(m.group(3))
    return None, None, None


def get_file_owner(path):
    try:
        adv    = ctypes.windll.advapi32
        needed = ctypes.wintypes.DWORD(0)
        adv.GetFileSecurityW(path, _OWNER_INFO, None, 0, ctypes.byref(needed))
        buf = ctypes.create_string_buffer(needed.value)
        if not adv.GetFileSecurityW(path, _OWNER_INFO, buf, needed.value, ctypes.byref(needed)):
            return 'Unknown'
        sid     = ctypes.c_void_p()
        default = ctypes.wintypes.BOOL()
        adv.GetSecurityDescriptorOwner(buf, ctypes.byref(sid), ctypes.byref(default))
        name     = ctypes.create_unicode_buffer(256)
        domain   = ctypes.create_unicode_buffer(256)
        name_n   = ctypes.wintypes.DWORD(256)
        domain_n = ctypes.wintypes.DWORD(256)
        sid_type = ctypes.wintypes.DWORD()
        adv.LookupAccountSidW(None, sid, name, ctypes.byref(name_n),
                               domain, ctypes.byref(domain_n), ctypes.byref(sid_type))
        if domain.value:
            return f'{domain.value}\\{name.value}'
        return name.value or 'Unknown'
    except Exception:
        return 'Unknown'


def _fmt_dt(ts):
    return datetime.fromtimestamp(ts).strftime('%d.%m.%Y  %H:%M:%S')


class InfoDialog(wx.Dialog):
    def __init__(self, parent, file_info):
        super().__init__(parent, title='CATIA File Information',
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER | wx.STAY_ON_TOP)

        vbox = wx.BoxSizer(wx.VERTICAL)

        # ── File list ──────────────────────────────────────────────────────────────────────────────────────────────────
        vbox.Add(wx.StaticText(self, label='Files:'), 0, wx.LEFT | wx.RIGHT | wx.TOP, 12)

        self.list_ctrl = wx.ListCtrl(self, size=(780, 150),
                                     style=wx.LC_REPORT | wx.BORDER_SIMPLE | wx.LC_SINGLE_SEL)
        self.list_ctrl.InsertColumn(0, 'File Name',  width=230)
        self.list_ctrl.InsertColumn(1, 'Version',    width=130)
        self.list_ctrl.InsertColumn(2, 'Created',    width=145)
        self.list_ctrl.InsertColumn(3, 'Modified',   width=145)
        self.list_ctrl.InsertColumn(4, 'Owner',      width=120)

        self.file_info = file_info
        for fi in file_info:
            path, release, sp, hf, ctime, mtime, owner = fi
            row = self.list_ctrl.GetItemCount()
            self.list_ctrl.InsertItem(row, os.path.basename(path))
            ver_str = f'V5R{release} SP{sp} HF{hf}' if release is not None else 'Not a V5 file'
            self.list_ctrl.SetItem(row, 1, ver_str)
            self.list_ctrl.SetItem(row, 2, ctime)
            self.list_ctrl.SetItem(row, 3, mtime)
            self.list_ctrl.SetItem(row, 4, owner)

        vbox.Add(self.list_ctrl, 0, wx.ALL | wx.EXPAND, 12)

        # ── Version details ────────────────────────────────────────────────────────────────────────────────────────────
        detail_box = wx.StaticBoxSizer(wx.StaticBox(self, label='Version Details'), wx.VERTICAL)
        grid       = wx.FlexGridSizer(rows=5, cols=2, vgap=6, hgap=16)
        grid.AddGrowableCol(1)

        self._details = {}
        for label_text, key in [('Full path:',    'path'),
                                  ('Release:',     'release'),
                                  ('Service Pack:', 'sp'),
                                  ('Hotfix:',      'hf'),
                                  ('Summary:',     'summary')]:
            lbl  = wx.StaticText(self, label=label_text)
            font = lbl.GetFont()
            font.SetWeight(wx.FONTWEIGHT_BOLD)
            lbl.SetFont(font)
            val               = wx.StaticText(self, label='')
            self._details[key] = val
            grid.Add(lbl, 0, wx.ALIGN_CENTER_VERTICAL)
            grid.Add(val, 0, wx.ALIGN_CENTER_VERTICAL | wx.EXPAND)

        detail_box.Add(grid, 0, wx.ALL | wx.EXPAND, 8)
        vbox.Add(detail_box, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 12)

        # ── Close button ───────────────────────────────────────────────────────────────────────────────────────────────
        btn_sizer = wx.StdDialogButtonSizer()
        btn_close = wx.Button(self, wx.ID_OK, label='Close')
        btn_close.SetDefault()
        btn_sizer.AddButton(btn_close)
        btn_sizer.Realize()
        vbox.Add(btn_sizer, 0, wx.ALL | wx.EXPAND, 10)

        self.SetSizer(vbox)
        vbox.Fit(self)
        self.Center()

        self.list_ctrl.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_select)

        if self.list_ctrl.GetItemCount() > 0:
            self.list_ctrl.Select(0)
            self.list_ctrl.Focus(0)

    def _on_select(self, event):
        idx = event.GetIndex()
        if idx < 0 or idx >= len(self.file_info):
            return
        path, release, sp, hf, *_ = self.file_info[idx]
        self._details['path'].SetLabel(path)
        if release is not None:
            self._details['release'].SetLabel(f'R{release}  —  CATIA V5 Release {release}')
            self._details['sp'].SetLabel(f'SP{sp}  —  Service Pack {sp}')
            self._details['hf'].SetLabel(f'HF{hf}  —  Hotfix {hf}')
            self._details['summary'].SetLabel(
                f'CATIA V5 Release {release}, Service Pack {sp}, Hotfix {hf}')
        else:
            for key in ('release', 'sp', 'hf'):
                self._details[key].SetLabel('—')
            self._details['summary'].SetLabel('Not a CATIA V5 file')
        self.Layout()


if __name__ == '__main__':
    app = wx.App(None)

    wildcard = 'CATIA V5 Files|*.CATPart;*.CATProduct;*.CATProcess;*.CATDrawing|All Files|*.*'
    picker   = wx.FileDialog(None, 'Select CATIA files to inspect',
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
        stat  = os.stat(path)
        ctime = _fmt_dt(stat.st_ctime)
        mtime = _fmt_dt(stat.st_mtime)
        owner = get_file_owner(path)
        file_info.append((path, release, sp, hf, ctime, mtime, owner))

    dlg = InfoDialog(None, file_info)
    wx.CallAfter(_bring_to_front, dlg)
    dlg.ShowModal()

    print('\n\n Completed\n\n')
