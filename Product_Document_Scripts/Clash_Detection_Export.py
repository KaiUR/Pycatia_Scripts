'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Clash_Detection_Export.py
    Version:        1.1
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Run interference/clash detection on the active assembly and export results to CSV.
    Author:         Kai-Uwe Rathjen
    Date:           21.05.26
    Description:    This script accesses the SPA workbench to create a clash check between all
                    components in the active CATProduct. After running the analysis it shows results
                    in a wx dialog and exports detected conflicts (type, status, component pair, and
                    value) to a CSV file next to the CATProduct. Requires the DMU Space Analysis or
                    DMU Navigator module licence.
    dependencies = [
                    "pycatia",
                    "wxPython",
                    ]
    requirements:   Python >= 3.10
                    pycatia
                    wxPython
                    Catia V5 running with an open CATProduct document.
                    DMU Space Analysis or DMU Navigator licence required.
    -----------------------------------------------------------------------------------------------------------------------

    Change:         1.1 - Fixed workbench access: use SPAWorkbench → clashes → Clash → conflicts.
                          Use pycatia Clash/Conflict wrappers and CatConflictType/CatConflictStatus
                          enums. Renamed Volume_mm3 → Value_mm (value is penetration length or
                          clearance distance, not a volume). Added wx dialog output.

    -----------------------------------------------------------------------------------------------------------------------
'''

#Imports
from pycatia import catia, CatWorkModeType
from pycatia.product_structure_interfaces.product_document import ProductDocument
from pycatia.space_analyses_interfaces.spa_workbench import SPAWorkbench
from pycatia.enumeration.enums import CatConflictType, CatConflictStatus, CatClashComputationType
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
        txt  = wx.TextCtrl(self, value=text,
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

    if type(active_doc) is not ProductDocument:
        wx.MessageDialog(None, "A CATProduct document must be the active document.", "Error",
                wx.OK | wx.ICON_ERROR | wx.STAY_ON_TOP).ShowModal()
        exit()

    product_document: ProductDocument = active_doc
    product = product_document.product

    product.activate_terminal_node(product.products)                                                               #Activate all terminal nodes
    product.apply_work_mode(CatWorkModeType.DESIGN_MODE)                                                           #Put assembly in design mode

    doc_name     = product_document.name.removesuffix('.CATProduct')
    doc_path_str = str(product_document.path())

    if doc_path_str == product_document.name:
        output_path = Path.home() / "Downloads" / (doc_name + "_ClashReport.csv")
    else:
        output_path = Path(doc_path_str).parent / (doc_name + "_ClashReport.csv")

    try:
        spa_wb = SPAWorkbench(active_doc.com_object)                                                               #SPA workbench (hosts Clashes collection)
        clashes = spa_wb.clashes
    except Exception as e:
        wx.MessageDialog(None,
                f"Could not access the SPA workbench.\n\n{e}\n\n"
                "Ensure the DMU Space Analysis or DMU Navigator module is installed and licenced.",
                "Error", wx.OK | wx.ICON_ERROR | wx.STAY_ON_TOP).ShowModal()
        exit()

    rows = []

    try:
        if clashes.count == 0:
            clash = clashes.add()                                                                                   #Create a new clash check
        else:
            clash = clashes.item(1)                                                                                #Re-use the first existing check

        clash.name             = "Python_Clash_Check"
        clash.computation_type = CatClashComputationType.catClashComputationTypeBetweenAll

        clash.compute()                                                                                            #Run the analysis

        conflicts = clash.conflicts

        for ci in range(conflicts.count):
            conflict = conflicts.item(ci + 1)

            try:
                conflict_type = CatConflictType(conflict.type).name.replace('catConflictType', '')
            except Exception:
                conflict_type = str(conflict.type)

            try:
                status = CatConflictStatus(conflict.status).name.replace('catConflictStatus', '')
            except Exception:
                status = str(conflict.status)

            try:
                comp1 = conflict.first_product.name
            except Exception:
                comp1 = ""

            try:
                comp2 = conflict.second_product.name
            except Exception:
                comp2 = ""

            try:
                value = round(conflict.value, 6)
            except Exception:
                value = ""

            rows.append({
                "Type":       conflict_type,
                "Component1": comp1,
                "Component2": comp2,
                "Value_mm":   value,
                "Status":     status,
            })

    except Exception as e:
        wx.MessageDialog(None, f"Error during clash analysis:\n\n{e}",
                "Clash Detection Error", wx.OK | wx.ICON_ERROR | wx.STAY_ON_TOP).ShowModal()
        exit()

    if not rows:
        wx.MessageDialog(None, "No clashes or interferences detected.",
                "Clash Detection — All Clear",
                wx.OK | wx.ICON_INFORMATION | wx.STAY_ON_TOP).ShowModal()
        exit()

    col_type  = 20
    col_comp  = 30
    col_val   = 12
    col_stat  = 16
    lines     = []
    lines.append(f"Clash analysis complete — {len(rows)} conflict(s) found")
    lines.append("-" * 80)
    lines.append("")
    lines.append(f"  {'Type':<{col_type}} {'Component 1':<{col_comp}} {'Component 2':<{col_comp}} {'Value (mm)':>{col_val}} {'Status':<{col_stat}}")
    lines.append(f"  {'-'*col_type} {'-'*col_comp} {'-'*col_comp} {'-'*col_val} {'-'*col_stat}")

    for row in rows:
        lines.append(
            f"  {row['Type']:<{col_type}} {row['Component1']:<{col_comp}} "
            f"{row['Component2']:<{col_comp}} {str(row['Value_mm']):>{col_val}} {row['Status']:<{col_stat}}"
        )

    csv_note = ""
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("Type,Component1,Component2,Value_mm,Status\n")
            for row in rows:
                f.write(
                    f"\"{row['Type']}\","
                    f"\"{row['Component1']}\","
                    f"\"{row['Component2']}\","
                    f"\"{row['Value_mm']}\","
                    f"\"{row['Status']}\"\n"
                )
        csv_note = f"\nCSV saved to: {output_path}"
    except Exception as e:
        csv_note = f"\nCould not write CSV: {e}"

    if csv_note:
        lines.append("")
        lines.append(csv_note)

    dlg = ResultDialog(None, "\n".join(lines), "Clash Detection — Results")
    wx.CallAfter(_bring_to_front, dlg)
    dlg.ShowModal()
    dlg.Destroy()
