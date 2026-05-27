'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Toggle_CATIA_No_Start_Document.py
    Version:        1.0
    Code:           Python3.10+
    Release:        N/A
    Purpose:        Add or remove CATNoStartDocument=yes in CATIA V5 environment files.
    Author:         Kai-Uwe Rathjen
    Date:           27.05.26
    Description:    Scans C:\\ProgramData\\DassaultSystemes\\CATEnv\\ for installed CATIA V5 environment
                    files and adds or removes the CATNoStartDocument=yes line for each selected
                    version. When the setting is present, CATIA opens without a blank document on
                    startup. When removed, CATIA reverts to its default behaviour of opening a new
                    blank document automatically.
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
        versions.append({
            'build':    match.group(1),
            'version':  f"R{match.group(2)}",
            'env_file': os.path.join(CATENV_DIR, fname),
            'filename': fname,
        })
    return versions

'''
    Adds or removes CATNoStartDocument=yes in the given environment file.
    If enable=True: adds the line (or replaces an existing CATNoStartDocument entry).
    If enable=False: removes any existing CATNoStartDocument line.
    Returns (changed: bool, error_msg: str).
'''
def apply_no_start_document(env_file, enable):
    try:
        with open(env_file, 'r', encoding='latin-1') as f:
            content = f.read()

        has_line = bool(re.search(r'^CATNoStartDocument\s*=', content, re.MULTILINE))

        if enable:
            if has_line:
                new_content = re.sub(
                    r'^CATNoStartDocument\s*=.*$',
                    'CATNoStartDocument=yes',
                    content,
                    flags=re.MULTILINE
                )
            else:
                new_content = content.rstrip('\r\n') + '\nCATNoStartDocument=yes\n'
        else:
            if not has_line:
                return False, "Setting not present"
            new_content = re.sub(
                r'^CATNoStartDocument\s*=[^\r\n]*\r?\n?',
                '',
                content,
                flags=re.MULTILINE
            )

        if new_content == content:
            return False, "Already set — no change needed"

        with open(env_file, 'w', encoding='latin-1') as f:
            f.write(new_content)
        return True, ""

    except PermissionError:
        return False, "Permission denied — run as Administrator"
    except Exception as e:
        return False, str(e)

class ToggleDialog(wx.Dialog):
    def __init__(self, parent, versions):
        super().__init__(parent, title="Toggle CATIA No Start Document",
                         size=(500, 380), style=wx.DEFAULT_DIALOG_STYLE | wx.STAY_ON_TOP)

        vbox = wx.BoxSizer(wx.VERTICAL)

        vbox.Add(wx.StaticText(self, label="Detected versions:"), 0, wx.LEFT | wx.RIGHT | wx.TOP, 12)
        self.checklist = wx.CheckListBox(self, choices=[
            f"{v['version']}  —  {v['filename']}" for v in versions
        ])
        for i in range(len(versions)):
            self.checklist.Check(i, True)                                                   #Check all by default
        vbox.Add(self.checklist, 1, wx.ALL | wx.EXPAND, 12)

        self.radio = wx.RadioBox(
            self, label="Action",
            choices=[
                "Add  —  stop CATIA opening with a blank document on startup",
                "Remove  —  restore blank document on startup",
            ],
            majorDimension=1, style=wx.RA_SPECIFY_COLS
        )
        vbox.Add(self.radio, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 12)

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

    dlg = ToggleDialog(None, versions)
    wx.CallAfter(_bring_to_front, dlg)
    if dlg.ShowModal() != wx.ID_OK:
        dlg.Destroy()
        exit()

    checked = dlg.checklist.GetCheckedItems()
    enable  = (dlg.radio.GetSelection() == 0)                                               #0 = Add, 1 = Remove
    dlg.Destroy()

    if not checked:
        wx.MessageDialog(None, "No versions selected.", "Nothing to do",
                wx.OK | wx.ICON_INFORMATION | wx.STAY_ON_TOP).ShowModal()
        exit()

    action_label = "Added" if enable else "Removed"
    lines = []
    for i in checked:
        v = versions[i]
        changed, err = apply_no_start_document(v['env_file'], enable)
        if err:
            status = f"SKIPPED — {err}"
        elif changed:
            status = action_label
        else:
            status = "No change"
        lines.append(f"  {v['version']}  ({v['filename']})  :  {status}")
        print(f"  {v['version']}: {status}")

    result_text = "\n".join(lines)
    wx.MessageDialog(None, result_text, "Results",
            wx.OK | wx.ICON_INFORMATION | wx.STAY_ON_TOP).ShowModal()

    print("\n\n Completed\n\n")
