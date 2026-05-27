'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Kill_CATIA_Processes.py
    Version:        1.0
    Code:           Python3.10+
    Release:        N/A
    Purpose:        Force-close all running CATIA processes to clear stale COM registrations.
    Author:         Kai-Uwe Rathjen
    Date:           27.05.26
    Description:    Terminates all CNEXT.exe processes via taskkill. Use this when CATIA is running
                    but scripts fail to connect due to a stale COM entry in the Windows Running
                    Object Table (ROT). After running, reopen CATIA before using any document scripts.
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
import subprocess
import wx
import ctypes

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
    app = wx.App(None)                                                                                              #Initialize wx application

    warn_dlg = wx.MessageDialog(
        None,
        "This will force-close all running CATIA processes.\n\nAny unsaved work will be lost.\n\nContinue?",
        "Kill CATIA Processes",
        wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING | wx.STAY_ON_TOP
    )
    wx.CallAfter(_bring_to_front, warn_dlg)
    if warn_dlg.ShowModal() != wx.ID_YES:                                                                           #User cancelled
        warn_dlg.Destroy()
        exit()
    warn_dlg.Destroy()

    result = subprocess.run(
        ["taskkill", "/F", "/IM", "CNEXT.exe"],
        capture_output=True,
        text=True
    )                                                                                                               #Force-terminate all CNEXT.exe processes

    output = (result.stdout + result.stderr).strip()
    if output:
        print(output)                                                                                               #Print taskkill output to console/log

    if result.returncode == 0:
        wx.MessageDialog(None, "All CATIA processes terminated successfully.", "Done",
                wx.OK | wx.ICON_INFORMATION | wx.STAY_ON_TOP).ShowModal()
    elif result.returncode == 128:
        wx.MessageDialog(None, "No running CATIA processes found.", "Done",
                wx.OK | wx.ICON_INFORMATION | wx.STAY_ON_TOP).ShowModal()
    else:
        wx.MessageDialog(None, f"taskkill returned an unexpected error:\n\n{result.stderr.strip()}", "Error",
                wx.OK | wx.ICON_ERROR | wx.STAY_ON_TOP).ShowModal()

    print("\n\n Completed\n\n")
