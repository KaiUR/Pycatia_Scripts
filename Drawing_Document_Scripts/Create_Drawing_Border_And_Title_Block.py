'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Create_Drawing_Border_And_Title_Block.py
    Version:        1.1
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Create a standard ISO border and title block on a new CATDrawing sheet.
    Author:         Kai-Uwe Rathjen
    Date:           21.05.26
    Description:    Creates a new CATDrawing document and populates the background view with a
                    standard ISO 5457 border and an ISO 7200-inspired title block. A dialog
                    lets the user choose the paper size (A0, A1, A2, A3, A4 landscape, A4 portrait)
                    and the first-angle or third-angle projection symbol. The border follows ISO 5457
                    margins (left=20mm, top/right/bottom=10mm for all sizes). The title block is
                    180mm x 55mm and is placed at the lower-right corner of the border.
                    Five rows are created: Company Name, Title, Part Number / Material,
                    Scale / Sheet / Revision, and Drawn By / Date / Approved.
                    Each data field is created as a named empty text item so that the
                    Update_Title_Block_From_Properties script can populate the values automatically.
    dependencies = [
                    "pycatia",
                    "wxPython",
                    ]
    requirements:   Python >= 3.10
                    pycatia
                    wxPython
                    Catia V5 running.
    -----------------------------------------------------------------------------------------------------------------------

    Change:         03.06.26 1.1: Fix E741: rename ambiguous variable l to left in _draw_title_block.

    -----------------------------------------------------------------------------------------------------------------------
'''

#Imports
from pycatia import catia
from pycatia.drafting_interfaces.drawing_document import DrawingDocument
from pycatia.enumeration.enums import CatPaperOrientation, CatPaperSize, CatTextAnchorPosition
import wx
import ctypes

#Available paper options: (display name, CatPaperSize, CatPaperOrientation)
PAPER_OPTIONS = [
    ("A0 Landscape", CatPaperSize.catPaperA0, CatPaperOrientation.catPaperLandscape),
    ("A1 Landscape", CatPaperSize.catPaperA1, CatPaperOrientation.catPaperLandscape),
    ("A2 Landscape", CatPaperSize.catPaperA2, CatPaperOrientation.catPaperLandscape),
    ("A3 Landscape", CatPaperSize.catPaperA3, CatPaperOrientation.catPaperLandscape),
    ("A4 Landscape", CatPaperSize.catPaperA4, CatPaperOrientation.catPaperLandscape),
    ("A4 Portrait",  CatPaperSize.catPaperA4, CatPaperOrientation.catPaperPortrait),
]

#ISO 5457 border margins (mm)
MARGIN_LEFT   = 20.0
MARGIN_TOP    = 10.0
MARGIN_RIGHT  = 10.0
MARGIN_BOTTOM = 10.0

#Title block dimensions (mm)
TB_WIDTH  = 180.0
TB_HEIGHT = 55.0

#Row heights from bottom of title block (mm)
TB_ROW_H_DRAWN   = 10.0  # Drawn By / Date / Approved
TB_ROW_H_SCALE   = 10.0  # Scale / Sheet / Revision
TB_ROW_H_PARTNO  = 10.0  # Part Number / Material
TB_ROW_H_TITLE   = 15.0  # Title
TB_ROW_H_COMPANY = 10.0  # Company Name


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


class SetupDialog(wx.Dialog):
    def __init__(self, parent):
        super().__init__(parent, title="Create Drawing Border & Title Block",
                         size=(380, 200), style=wx.DEFAULT_DIALOG_STYLE | wx.STAY_ON_TOP)
        panel      = wx.Panel(self)
        panel_sizer = wx.BoxSizer(wx.VERTICAL)

        panel_sizer.Add(wx.StaticText(panel, label="Paper size:"), flag=wx.ALL, border=12)
        self.size_choice = wx.Choice(panel, choices=[o[0] for o in PAPER_OPTIONS])
        self.size_choice.SetSelection(3)                                                                             #Default: A3 Landscape
        panel_sizer.Add(self.size_choice, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, border=12)
        panel.SetSizer(panel_sizer)

        #Button sizer must live on the dialog, not on the panel
        dlg_sizer = wx.BoxSizer(wx.VERTICAL)
        dlg_sizer.Add(panel, proportion=1, flag=wx.EXPAND)
        dlg_sizer.Add(self.CreateButtonSizer(wx.OK | wx.CANCEL), flag=wx.ALIGN_CENTER | wx.ALL, border=10)
        self.SetSizer(dlg_sizer)

    def get_paper(self):
        return PAPER_OPTIONS[self.size_choice.GetSelection()]


def _line(factory, x1, y1, x2, y2):
    factory.CreateLine(x1, y1, x2, y2)


def _label(view_com, text, x, y, size=2.0, bold=0,
           anchor=CatTextAnchorPosition.catTopLeft):
    """Add a small field-name label. Returns the COM text object."""
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
           anchor=CatTextAnchorPosition.catMiddleLeft):
    """Add an empty named value field. Returns the COM text object."""
    t = view_com.Texts.Add("", x, y)
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
    """Draw the ISO 5457 border and return its corner coordinates."""
    x1 = MARGIN_LEFT
    y1 = MARGIN_BOTTOM
    x2 = w - MARGIN_RIGHT
    y2 = h - MARGIN_TOP

    _line(factory, x1, y1, x2, y1)                                                                                  #Bottom
    _line(factory, x2, y1, x2, y2)                                                                                  #Right
    _line(factory, x2, y2, x1, y2)                                                                                  #Top
    _line(factory, x1, y2, x1, y1)                                                                                  #Left

    return x1, y1, x2, y2


def _draw_title_block(factory, view_com, bx1, by1, bx2, by2):
    """Draw the title block and populate it with label and value text items.

    Layout (bottom to top, all y values are absolute sheet coordinates):

      Row 0 (10mm)  - DRAWN BY | DATE | APPROVED
      Row 1 (10mm)  - SCALE    | SHEET | REVISION
      Row 2 (10mm)  - PART NUMBER       | MATERIAL
      Row 3 (15mm)  - TITLE
      Row 4 (10mm)  - COMPANY NAME
    """

    r    = bx2                    #Right edge of border
    left = r - TB_WIDTH           #Left edge of title block
    b    = by1                    #Bottom edge

    #Row bottom y values (absolute)
    rows = [
        b,
        b + TB_ROW_H_DRAWN,
        b + TB_ROW_H_DRAWN + TB_ROW_H_SCALE,
        b + TB_ROW_H_DRAWN + TB_ROW_H_SCALE + TB_ROW_H_PARTNO,
        b + TB_ROW_H_DRAWN + TB_ROW_H_SCALE + TB_ROW_H_PARTNO + TB_ROW_H_TITLE,
        b + TB_HEIGHT,
    ]

    #Value text y positions: 30% from each cell bottom keeps values clear of the top labels
    vy = [rows[i] + (rows[i + 1] - rows[i]) * 0.3 for i in range(5)]

    #Outer rectangle
    _line(factory, left, rows[0], r, rows[0])
    _line(factory, r, rows[0], r, rows[5])
    _line(factory, r, rows[5], left, rows[5])
    _line(factory, left, rows[5], left, rows[0])

    #Horizontal dividers between rows
    for y in rows[1:5]:
        _line(factory, left, y, r, y)

    #--- Row 0: DRAWN BY | DATE | APPROVED (three equal columns) ---
    c0 = left + TB_WIDTH / 3
    c1 = left + 2 * TB_WIDTH / 3
    _line(factory, c0, rows[0], c0, rows[1])
    _line(factory, c1, rows[0], c1, rows[1])

    _label(view_com, "DRAWN BY:",  left + 1, rows[1] - 1)
    _label(view_com, "DATE:",      c0 + 1,   rows[1] - 1)
    _label(view_com, "APPROVED:",  c1 + 1,   rows[1] - 1)

    _value(view_com, "Drawn_By",   left + 1, vy[0])
    _value(view_com, "Date",       c0 + 1,   vy[0])
    _value(view_com, "Approved",   c1 + 1,   vy[0])

    #--- Row 1: SCALE | SHEET | REVISION (three equal columns) ---
    _line(factory, c0, rows[1], c0, rows[2])
    _line(factory, c1, rows[1], c1, rows[2])

    _label(view_com, "SCALE:",    left + 1, rows[2] - 1)
    _label(view_com, "SHEET:",    c0 + 1,   rows[2] - 1)
    _label(view_com, "REVISION:", c1 + 1,   rows[2] - 1)

    _value(view_com, "Scale",    left + 1, vy[1])
    _value(view_com, "Sheet",    c0 + 1,   vy[1])
    _value(view_com, "Revision", c1 + 1,   vy[1])

    #--- Row 2: PART NUMBER | MATERIAL (120mm / 60mm split) ---
    mid = left + 2 * TB_WIDTH / 3
    _line(factory, mid, rows[2], mid, rows[3])

    _label(view_com, "PART NUMBER:", left + 1, rows[3] - 1)
    _label(view_com, "MATERIAL:",    mid + 1,  rows[3] - 1)

    _value(view_com, "Part_Number", left + 1, vy[2])
    _value(view_com, "Material",    mid + 1,  vy[2])

    #--- Row 3: TITLE (full width, 15mm, larger value text) ---
    _label(view_com, "TITLE:", left + 1, rows[4] - 1)
    _value(view_com, "Title",  left + 1, vy[3], size=5.0)

    #--- Row 4: COMPANY NAME (full width, bold, centered — no label, centre is correct) ---
    _value(view_com, "Company",
           left + TB_WIDTH / 2,
           (rows[4] + rows[5]) / 2,
           size=5.0,
           anchor=CatTextAnchorPosition.catMiddleCenter)


if __name__ == "__main__":
    caa = catia()                                                                                                    #CATIA application instance

    app = wx.App(None)
    dlg = SetupDialog(None)
    wx.CallAfter(_bring_to_front, dlg)

    if dlg.ShowModal() != wx.ID_OK:
        dlg.Destroy()
        print("Cancelled.")
        exit()

    paper_name, cat_size, cat_orient = dlg.get_paper()
    dlg.Destroy()

    print(f"\n Creating new CATDrawing [{paper_name}] ...")

    caa.documents.add("Drawing")                                                                                     #Create new CATDrawing document (becomes active)
    drawing_doc = DrawingDocument(caa.active_document.com_object)

    #Use the pycatia DrawingSheet wrapper so property setters work correctly
    sheet     = drawing_doc.drawing_root.sheets.item(1)
    sheet_com = sheet.com_object

    sheet.paper_size  = cat_size
    sheet.orientation = cat_orient

    sheet_w = sheet.get_paper_width()
    sheet_h = sheet.get_paper_height()
    print(f"  Sheet size: {sheet_w:.0f} x {sheet_h:.0f} mm")

    #Retrieve the background view; try GetBackgroundView first then fall back to Views.Item(2)
    try:
        bg_view = sheet_com.GetBackgroundView()
    except Exception:
        bg_view = sheet_com.Views.Item(2)                                                                            #Background view is the second view on any sheet

    bg_view.Activate()

    factory = bg_view.Factory2D                                                                                      #2D geometry factory for drawing lines

    bx1, by1, bx2, by2 = _draw_border(factory, sheet_w, sheet_h)
    _draw_title_block(factory, bg_view, bx1, by1, bx2, by2)

    bg_view.SaveEdition()

    sheet_com.Views.Item(1).Activate()                                                                               #Return to main view, leaving background edit mode
    caa.active_window.active_viewer.reframe()                                                                        #Zoom to fit entire sheet

    print("  Border and title block created.")
    print(f"  Border:      ({bx1:.0f}, {by1:.0f}) to ({bx2:.0f}, {by2:.0f}) mm")
    print(f"  Title block: {TB_WIDTH:.0f} x {TB_HEIGHT:.0f} mm at lower-right of border")
    print("\n  Named value fields: Drawn_By, Date, Approved, Scale, Sheet, Revision,")
    print("  Part_Number, Material, Title, Company")
    print("\n  Use Update_Title_Block_From_Properties to populate values from model properties.\n")
