'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Add_Border_And_Title_Block_With_Values.py
    Version:        1.1
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Add an ISO border and title block with user-entered values to the active sheet.
    Author:         Kai-Uwe Rathjen
    Date:           21.05.26
    Description:    Draws an ISO 5457 border and an ISO 7200-inspired title block on the
                    background view of the active sheet in the currently open CATDrawing document.
                    A dialog lets the user enter values for all title block fields (Company, Title,
                    Part Number, Material, Scale, Sheet, Revision, Drawn By, Date, Approved)
                    before drawing begins. Entered values are written directly into the named
                    text items. The paper size is read from the existing sheet.
                    Fields left blank remain empty and can be filled later using the
                    Update_Title_Block_From_Properties script.
    dependencies = [
                    "pycatia",
                    "wxPython",
                    ]
    requirements:   Python >= 3.10
                    pycatia
                    wxPython
                    Catia V5 running with an open CATDrawing document.
    -----------------------------------------------------------------------------------------------------------------------

    Change:

    -----------------------------------------------------------------------------------------------------------------------
'''

#Imports
from pycatia import catia
from pycatia.drafting_interfaces.drawing_document import DrawingDocument
from pycatia.enumeration.enums import CatTextAnchorPosition
import wx
import ctypes

#Title block fields: (internal name, dialog label)
TB_FIELDS = [
    ("Company",     "Company Name"),
    ("Title",       "Title"),
    ("Part_Number", "Part Number"),
    ("Material",    "Material"),
    ("Scale",       "Scale"),
    ("Sheet",       "Sheet"),
    ("Revision",    "Revision"),
    ("Drawn_By",    "Drawn By"),
    ("Date",        "Date"),
    ("Approved",    "Approved"),
]

#ISO 5457 border margins (mm)
MARGIN_LEFT   = 20.0
MARGIN_TOP    = 10.0
MARGIN_RIGHT  = 10.0
MARGIN_BOTTOM = 10.0

#Title block dimensions (mm)
TB_WIDTH  = 180.0
TB_HEIGHT = 55.0

TB_ROW_H_DRAWN   = 10.0
TB_ROW_H_SCALE   = 10.0
TB_ROW_H_PARTNO  = 10.0
TB_ROW_H_TITLE   = 15.0
TB_ROW_H_COMPANY = 10.0


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


class ValuesDialog(wx.Dialog):
    def __init__(self, parent, sheet_name, sheet_w, sheet_h):
        super().__init__(parent,
                         title=f"Title Block Values  —  {sheet_name}  ({sheet_w:.0f} x {sheet_h:.0f} mm)",
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER | wx.STAY_ON_TOP)
        panel = wx.Panel(self)
        grid  = wx.FlexGridSizer(len(TB_FIELDS), 2, 8, 10)
        grid.AddGrowableCol(1, 1)

        self.controls = {}
        for name, label in TB_FIELDS:
            grid.Add(wx.StaticText(panel, label=label + ":"), flag=wx.ALIGN_CENTER_VERTICAL)
            tc = wx.TextCtrl(panel, size=(220, -1))
            grid.Add(tc, flag=wx.EXPAND)
            self.controls[name] = tc

        panel_sizer = wx.BoxSizer(wx.VERTICAL)
        panel_sizer.Add(grid, proportion=1, flag=wx.EXPAND | wx.ALL, border=14)
        panel.SetSizer(panel_sizer)

        dlg_sizer = wx.BoxSizer(wx.VERTICAL)
        dlg_sizer.Add(panel, proportion=1, flag=wx.EXPAND)
        dlg_sizer.Add(self.CreateButtonSizer(wx.OK | wx.CANCEL), flag=wx.ALIGN_CENTER | wx.ALL, border=10)
        self.SetSizer(dlg_sizer)
        self.Fit()
        self.SetMinSize(self.GetSize())

    def get_values(self):
        return {name: tc.GetValue().strip() for name, tc in self.controls.items()}


def _line(factory, x1, y1, x2, y2):
    factory.CreateLine(x1, y1, x2, y2)


def _label(view_com, text, x, y, size=2.0, bold=0,
           anchor=CatTextAnchorPosition.catTopLeft):
    t = view_com.Texts.Add(text, x, y)
    try:
        t.AnchorPosition = anchor
        tp = t.TextProperties
        tp.FontSize = size
        tp.Bold     = bold
        tp.Update()
    except Exception:
        pass
    return t


def _value(view_com, name, x, y, size=3.5,
           anchor=CatTextAnchorPosition.catMiddleLeft, initial=""):
    t = view_com.Texts.Add(initial, x, y)
    try:
        t.Name           = name
        t.AnchorPosition = anchor
        tp = t.TextProperties
        tp.FontSize = size
        tp.Update()
    except Exception:
        pass
    return t


def _draw_border(factory, w, h):
    x1 = MARGIN_LEFT
    y1 = MARGIN_BOTTOM
    x2 = w - MARGIN_RIGHT
    y2 = h - MARGIN_TOP

    _line(factory, x1, y1, x2, y1)                                                                                  #Bottom
    _line(factory, x2, y1, x2, y2)                                                                                  #Right
    _line(factory, x2, y2, x1, y2)                                                                                  #Top
    _line(factory, x1, y2, x1, y1)                                                                                  #Left

    return x1, y1, x2, y2


def _draw_title_block(factory, view_com, bx1, by1, bx2, by2, values):
    r    = bx2
    left = r - TB_WIDTH
    b    = by1

    rows = [
        b,
        b + TB_ROW_H_DRAWN,
        b + TB_ROW_H_DRAWN + TB_ROW_H_SCALE,
        b + TB_ROW_H_DRAWN + TB_ROW_H_SCALE + TB_ROW_H_PARTNO,
        b + TB_ROW_H_DRAWN + TB_ROW_H_SCALE + TB_ROW_H_PARTNO + TB_ROW_H_TITLE,
        b + TB_HEIGHT,
    ]

    vy = [rows[i] + (rows[i + 1] - rows[i]) * 0.3 for i in range(5)]

    _line(factory, left, rows[0], r, rows[0])
    _line(factory, r, rows[0], r, rows[5])
    _line(factory, r, rows[5], left, rows[5])
    _line(factory, left, rows[5], left, rows[0])

    for y in rows[1:5]:
        _line(factory, left, y, r, y)

    c0 = left + TB_WIDTH / 3
    c1 = left + 2 * TB_WIDTH / 3

    _line(factory, c0, rows[0], c0, rows[1])
    _line(factory, c1, rows[0], c1, rows[1])

    _label(view_com, "DRAWN BY:",  left + 1, rows[1] - 1)
    _label(view_com, "DATE:",      c0 + 1,   rows[1] - 1)
    _label(view_com, "APPROVED:",  c1 + 1,   rows[1] - 1)

    _value(view_com, "Drawn_By",  left + 1, vy[0], initial=values.get("Drawn_By",  ""))
    _value(view_com, "Date",      c0 + 1,   vy[0], initial=values.get("Date",      ""))
    _value(view_com, "Approved",  c1 + 1,   vy[0], initial=values.get("Approved",  ""))

    _line(factory, c0, rows[1], c0, rows[2])
    _line(factory, c1, rows[1], c1, rows[2])

    _label(view_com, "SCALE:",    left + 1, rows[2] - 1)
    _label(view_com, "SHEET:",    c0 + 1,   rows[2] - 1)
    _label(view_com, "REVISION:", c1 + 1,   rows[2] - 1)

    _value(view_com, "Scale",    left + 1, vy[1], initial=values.get("Scale",    ""))
    _value(view_com, "Sheet",    c0 + 1,   vy[1], initial=values.get("Sheet",    ""))
    _value(view_com, "Revision", c1 + 1,   vy[1], initial=values.get("Revision", ""))

    mid = left + 2 * TB_WIDTH / 3
    _line(factory, mid, rows[2], mid, rows[3])

    _label(view_com, "PART NUMBER:", left + 1, rows[3] - 1)
    _label(view_com, "MATERIAL:",    mid + 1,  rows[3] - 1)

    _value(view_com, "Part_Number", left + 1, vy[2], initial=values.get("Part_Number", ""))
    _value(view_com, "Material",    mid + 1,  vy[2], initial=values.get("Material",    ""))

    _label(view_com, "TITLE:", left + 1, rows[4] - 1)
    _value(view_com, "Title",  left + 1, vy[3], size=5.0, initial=values.get("Title", ""))

    _value(view_com, "Company",
           left + TB_WIDTH / 2,
           (rows[4] + rows[5]) / 2,
           size=5.0,
           anchor=CatTextAnchorPosition.catMiddleCenter,
           initial=values.get("Company", ""))


if __name__ == "__main__":
    caa = catia()                                                                                                    #CATIA application instance
    active_doc = caa.active_document

    try:
        drawing_doc = DrawingDocument(active_doc.com_object)
        _ = drawing_doc.drawing_root
    except Exception:
        print("A CATDrawing document must be the active document.")
        exit()

    sheet     = drawing_doc.drawing_root.sheets.item(1)
    sheet_com = sheet.com_object
    sheet_w   = sheet.get_paper_width()
    sheet_h   = sheet.get_paper_height()

    app = wx.App(None)
    dlg = ValuesDialog(None, sheet.name, sheet_w, sheet_h)
    wx.CallAfter(_bring_to_front, dlg)

    if dlg.ShowModal() != wx.ID_OK:
        dlg.Destroy()
        print("Cancelled.")
        exit()

    values = dlg.get_values()
    dlg.Destroy()

    print(f"\n Active sheet: {sheet.name}  |  {sheet_w:.0f} x {sheet_h:.0f} mm")

    try:
        bg_view = sheet_com.GetBackgroundView()
    except Exception:
        bg_view = sheet_com.Views.Item(2)

    bg_view.Activate()

    factory = bg_view.Factory2D

    bx1, by1, bx2, by2 = _draw_border(factory, sheet_w, sheet_h)
    _draw_title_block(factory, bg_view, bx1, by1, bx2, by2, values)

    bg_view.SaveEdition()

    sheet_com.Views.Item(1).Activate()                                                                               #Return to main view
    caa.active_window.active_viewer.reframe()                                                                        #Zoom to fit entire sheet

    filled = sum(1 for v in values.values() if v)
    print(f"  Border and title block added  ({filled} of {len(values)} fields populated).")
    print(f"  Border:      ({bx1:.0f}, {by1:.0f}) to ({bx2:.0f}, {by2:.0f}) mm")
    print(f"  Title block: {TB_WIDTH:.0f} x {TB_HEIGHT:.0f} mm at lower-right of border\n")
