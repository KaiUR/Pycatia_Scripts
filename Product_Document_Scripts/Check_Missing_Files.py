'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Check_Missing_Files.py
    Version:        1.1
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Check all component file references in the assembly for missing or broken links.
    Author:         Kai-Uwe Rathjen
    Date:           21.05.26
    Description:    This script recurses through the active CATProduct and checks whether the file
                    referenced by each component instance actually exists on disk. Components whose
                    files cannot be found are listed with their assembly path and last known file
                    location. Results are shown in a wx dialog. If issues are found a CSV is also
                    saved next to the CATProduct. Useful for troubleshooting broken assembly references.
    dependencies = [
                    "pycatia",
                    "wxPython",
                    ]
    requirements:   Python >= 3.10
                    pycatia
                    wxPython
                    Catia V5 running with an open CATProduct document.
    -----------------------------------------------------------------------------------------------------------------------

    Change:         1.1 - Replaced print output with wx ResultDialog / MessageDialog.

    -----------------------------------------------------------------------------------------------------------------------
'''

#Imports
from pycatia import catia
from pycatia.product_structure_interfaces.product_document import ProductDocument
from pathlib import Path
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
        super().__init__(parent, title=title, size=(900, 420),
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


def _check_files(product, parent_path, rows):
    try:
        children = product.products
    except Exception:
        return

    for i in range(children.count):
        try:
            child     = children.item(i + 1)
            inst_name = child.name
        except Exception:
            continue

        full_path = f"{parent_path}/{inst_name}" if parent_path else inst_name

        file_name  = ""
        file_exists = None

        try:
            file_name   = child.full_name                                                                          #Full file path stored in the product link
            file_exists = Path(file_name).exists()
        except Exception:
            try:
                file_name   = child.file_name                                                                      #Fallback to file name only
                file_exists = None                                                                                  #Cannot check existence with name only
            except Exception:
                file_name   = "(unknown)"
                file_exists = None

        if file_exists is False:
            status = "MISSING"
        elif file_exists is None:
            status = "UNRESOLVED"
        else:
            status = "OK"

        rows.append({
            "Path":     full_path,
            "Instance": inst_name,
            "File":     file_name,
            "Status":   status,
        })

        if child.products.count > 0:
            _check_files(child, full_path, rows)


if __name__ == "__main__":
    caa = catia()                                                                                                   #Catia application instance
    active_doc = caa.active_document                                                                               #Current open document

    app = wx.App(None)

    if not type(active_doc) is ProductDocument:
        wx.MessageDialog(None, "A CATProduct document must be the active document.", "Error",
                wx.OK | wx.ICON_ERROR | wx.STAY_ON_TOP).ShowModal()
        exit()

    product_document: ProductDocument = active_doc
    product = product_document.product

    doc_name     = product_document.name.removesuffix('.CATProduct')
    doc_path_str = str(product_document.path())

    if doc_path_str == product_document.name:
        output_path = Path.home() / "Downloads" / (doc_name + "_MissingFiles.csv")
    else:
        output_path = Path(doc_path_str).parent / (doc_name + "_MissingFiles.csv")

    rows = []
    _check_files(product, "", rows)

    total    = len(rows)
    ok_count = sum(1 for r in rows if r['Status'] == "OK")
    missing  = sum(1 for r in rows if r['Status'] == "MISSING")
    unres    = sum(1 for r in rows if r['Status'] == "UNRESOLVED")

    if missing == 0 and unres == 0:
        wx.MessageDialog(None,
                f"All {total} reference(s) resolved — no missing files found.",
                "Check Missing Files — All OK",
                wx.OK | wx.ICON_INFORMATION | wx.STAY_ON_TOP).ShowModal()
        exit()

    col_inst   = 30
    col_status = 12
    lines = []
    summary = f"Checked {total} reference(s):  {ok_count} OK  |  {missing} Missing  |  {unres} Unresolved"
    lines.append(summary)
    lines.append("-" * 80)
    lines.append("")
    lines.append(f"  {'Instance':<{col_inst}} {'Status':<{col_status}} File")
    lines.append(f"  {'-'*col_inst} {'-'*col_status} {'-'*50}")

    for row in rows:
        if row['Status'] != "OK":
            lines.append(f"  {row['Instance']:<{col_inst}} {row['Status']:<{col_status}} {row['File']}")

    csv_note = ""
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("Assembly Path,Instance Name,File Reference,Status\n")
            for row in rows:
                if row['Status'] != "OK":
                    f.write(
                        f"\"{row['Path']}\","
                        f"\"{row['Instance']}\","
                        f"\"{row['File']}\","
                        f"\"{row['Status']}\"\n"
                    )
        csv_note = f"\nCSV saved to: {output_path}"
    except Exception as e:
        csv_note = f"\nCould not write CSV: {e}"

    if csv_note:
        lines.append("")
        lines.append(csv_note)

    title = "Check Missing Files — Issues Found"
    dlg = ResultDialog(None, "\n".join(lines), title)
    wx.CallAfter(_bring_to_front, dlg)
    dlg.ShowModal()
    dlg.Destroy()
