'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Clear_Script_Settings.py
    Version:        1.0
    Code:           Python3.10+
    Release:        N/A
    Purpose:        Delete all persistent saved settings for pycatia_scripts.
    Author:         Kai-Uwe Rathjen
    Date:           31.05.26
    Description:    Removes the %APPDATA%\\pycatia_scripts folder and all its contents, resetting
                    every script's saved user presets (dialog values, last-used parameters, etc.)
                    back to factory defaults. Each script will recreate its own subfolder the next
                    time it is run. A confirmation dialog lists all script folders that will be
                    removed before proceeding.
    dependencies = [
                    "wxPython",
                    ]
    requirements:   Python >= 3.10
                    wxPython
    -----------------------------------------------------------------------------------------------------------------------

    Change:

    -----------------------------------------------------------------------------------------------------------------------
'''

# Imports
import os
import shutil
import ctypes
import wx


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


if __name__ == "__main__":
    SETTINGS_ROOT = os.path.join(os.environ['APPDATA'], 'pycatia_scripts')

    app = wx.App(None)

    if not os.path.isdir(SETTINGS_ROOT):
        wx.MessageBox(
            f"No saved settings found.\n\n{SETTINGS_ROOT}\ndoes not exist.",
            "Nothing to Clear", wx.OK | wx.ICON_INFORMATION | wx.STAY_ON_TOP
        )
        print("\n No saved settings found — nothing to clear.\n\n Completed\n\n")
        exit()

    subfolders = sorted(
        e.name for e in os.scandir(SETTINGS_ROOT) if e.is_dir()
    )

    if subfolders:
        folder_list = "\n".join(f"  • {name}" for name in subfolders)
    else:
        folder_list = "  (folder is empty)"

    msg = (
        f"This will permanently delete all saved script settings:\n\n"
        f"{folder_list}\n\n"
        f"Location: {SETTINGS_ROOT}\n\n"
        f"Each script will revert to its factory defaults on next run.\n\n"
        f"Continue?"
    )

    dlg = wx.MessageDialog(
        None, msg, "Clear All Script Settings",
        wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING | wx.STAY_ON_TOP
    )
    wx.CallAfter(_bring_to_front, dlg)
    result = dlg.ShowModal()
    dlg.Destroy()

    if result != wx.ID_YES:
        print("\n Cancelled — no settings were deleted.\n\n Completed\n\n")
        exit()

    try:
        shutil.rmtree(SETTINGS_ROOT)
        print("\n Cleared saved settings.")
        for name in subfolders:
            print(f"   Removed: {name}")
        print("\n\n Completed\n\n")
        wx.MessageBox(
            f"All saved settings cleared.\n\n{len(subfolders)} script folder(s) removed.",
            "Done", wx.OK | wx.ICON_INFORMATION | wx.STAY_ON_TOP
        )
    except Exception as e:
        print(f"\n Error: Could not delete settings folder: {e}\n\n Completed\n\n")
        wx.MessageBox(
            f"Could not delete settings folder:\n\n{e}",
            "Error", wx.OK | wx.ICON_ERROR | wx.STAY_ON_TOP
        )
