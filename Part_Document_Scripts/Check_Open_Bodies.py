'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Check_Open_Bodies.py
    Version:        1.1
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Check all solid bodies in the active part for open or invalid geometry.
    Author:         Kai-Uwe Rathjen
    Date:           21.05.26
    Description:    This script iterates all solid bodies in the active CATPart and uses the SPA
                    workbench to attempt a volume measurement on each one. A body that fails the
                    measurement or returns a zero volume is flagged as potentially open or invalid.
                    Results are shown in a scrollable wx dialog. Useful as a geometry quality check
                    before downstream use such as FEA, manufacturing, or STEP export.
    dependencies = [
                    "pycatia",
                    "wxPython",
                    ]
    requirements:   Python >= 3.10
                    pycatia
                    wxPython
                    Catia V5 running with an open part document.
    -----------------------------------------------------------------------------------------------------------------------

    Change:         22.05.26 1.1: Fixed meas.volume (snake_case); converted m³→mm³ for display; replaced print output with custom ResultDialog.

    -----------------------------------------------------------------------------------------------------------------------
'''

#Imports
from pycatia import catia
from pycatia.mec_mod_interfaces.part_document import PartDocument
from pycatia.space_analyses_interfaces.spa_workbench import SPAWorkbench
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


class ResultDialog(wx.Dialog):
    def __init__(self, parent, text, title):
        super().__init__(parent, title=title, size=(760, 400),
                         style=wx.DEFAULT_DIALOG_STYLE | wx.STAY_ON_TOP | wx.RESIZE_BORDER)
        mono = wx.Font(10, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        txt = wx.TextCtrl(self, value=text,
                          style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_DONTWRAP | wx.HSCROLL)
        txt.SetFont(mono)
        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(txt, proportion=1, flag=wx.EXPAND | wx.ALL, border=8)
        vbox.Add(self.CreateButtonSizer(wx.OK), flag=wx.ALIGN_CENTER | wx.BOTTOM, border=8)
        self.SetSizer(vbox)
        self.CenterOnScreen()


if __name__ == "__main__":
    caa = catia()                                                                                                   #Catia application instance
    active_doc = caa.active_document                                                                               #Current open document

    app = wx.App(None)

    if type(active_doc) is not PartDocument:
        wx.MessageDialog(None, "A CATPart document must be the active document.", "Error",
                wx.OK | wx.ICON_ERROR | wx.STAY_ON_TOP).ShowModal()
        exit()

    part_document: PartDocument = active_doc
    part = part_document.part
    bodies = part.bodies
    body_count = bodies.count

    if body_count == 0:
        wx.MessageDialog(None, "No solid bodies found in this part document.", "Check Open Bodies",
                wx.OK | wx.ICON_INFORMATION | wx.STAY_ON_TOP).ShowModal()
        exit()

    spa = SPAWorkbench(active_doc.com_object)                                                                      #SPA workbench for geometry analysis

    ok_count      = 0
    warning_count = 0
    error_count   = 0
    report_lines  = []

    col_name  = 32
    col_vol   = 18
    col_stat  = 24

    header = f"  {'Body Name':<{col_name}} {'Volume (mm³)':>{col_vol}} {'Status':<{col_stat}}"
    sep    = f"  {'-'*col_name} {'-'*col_vol} {'-'*col_stat}"
    report_lines.append(header)
    report_lines.append(sep)

    for i in range(body_count):
        body      = bodies.item(i + 1)
        body_name = body.name
        status    = ""
        volume_str = ""

        try:
            body_ref = part.create_reference_from_object(body)
            meas     = spa.get_measurable(body_ref)
            volume   = meas.volume                                                                                  #snake_case pycatia property

            volume_mm3 = volume * 1e9                                                                              #API returns m³; convert to mm³ for display

            if volume is None or volume == 0.0:
                status     = "WARNING — zero volume"
                volume_str = "0.00"
                warning_count += 1
            elif volume < 0.0:
                status     = "WARNING — negative volume"
                volume_str = f"{volume_mm3:.2f}"
                warning_count += 1
            else:
                status     = "OK"
                volume_str = f"{volume_mm3:.2f}"
                ok_count   += 1

        except Exception as e:
            status     = f"ERROR — {e}"
            volume_str = "N/A"
            error_count += 1

        report_lines.append(f"  {body_name:<{col_name}} {volume_str:>{col_vol}} {status:<{col_stat}}")

    summary = (
        f"Checked {body_count} body(ies):  "
        f"{ok_count} OK  |  {warning_count} Warning(s)  |  {error_count} Error(s)"
    )

    report_lines.insert(0, summary + "\n" + "-" * 70 + "\n")

    if warning_count > 0 or error_count > 0:
        report_lines.append("")
        report_lines.append("Bodies with warnings or errors may be:")
        report_lines.append("  - Open shells (no enclosed volume)")
        report_lines.append("  - Bodies with missing or failed features")
        report_lines.append("  - Bodies that require a part update to resolve")

    report_text = "\n".join(report_lines)

    title = "Check Open Bodies — Issues Found" if (warning_count + error_count) > 0 else "Check Open Bodies — All OK"

    dlg = ResultDialog(None, report_text, title)
    wx.CallAfter(_bring_to_front, dlg)
    dlg.ShowModal()
    dlg.Destroy()
