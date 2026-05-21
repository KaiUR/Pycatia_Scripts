'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Add_Border_And_Title_Block.py
    Version:        1.0
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Add a standard ISO border and title block to the active CATDrawing sheet.
    Author:         Kai-Uwe Rathjen
    Date:           21.05.26
    Description:    Draws an ISO 5457 border and an ISO 7200-inspired title block on the
                    background view of the active sheet in the currently open CATDrawing document.
                    The paper size is read from the existing sheet — no new document is created.
                    Border margins follow ISO 5457 (left=20mm, top/right/bottom=10mm).
                    The title block is 180mm x 55mm at the lower-right corner of the border.
                    Each data field is created as a named empty text item so that the
                    Update_Title_Block_From_Properties script can populate values automatically.
    dependencies = [
                    "pycatia",
                    ]
    requirements:   Python >= 3.10
                    pycatia
                    Catia V5 running with an open CATDrawing document.
    -----------------------------------------------------------------------------------------------------------------------

    Change:

    -----------------------------------------------------------------------------------------------------------------------
'''

#Imports
from pycatia import catia
from pycatia.drafting_interfaces.drawing_document import DrawingDocument
from pycatia.enumeration.enums import CatTextAnchorPosition

#ISO 5457 border margins (mm)
MARGIN_LEFT   = 20.0
MARGIN_TOP    = 10.0
MARGIN_RIGHT  = 10.0
MARGIN_BOTTOM = 10.0

#Title block dimensions (mm)
TB_WIDTH  = 180.0
TB_HEIGHT = 55.0

#Row heights from bottom of title block (mm)
TB_ROW_H_DRAWN   = 10.0
TB_ROW_H_SCALE   = 10.0
TB_ROW_H_PARTNO  = 10.0
TB_ROW_H_TITLE   = 15.0
TB_ROW_H_COMPANY = 10.0


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
           anchor=CatTextAnchorPosition.catMiddleLeft):
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
    r  = bx2
    l  = r - TB_WIDTH
    b  = by1

    rows = [
        b,
        b + TB_ROW_H_DRAWN,
        b + TB_ROW_H_DRAWN + TB_ROW_H_SCALE,
        b + TB_ROW_H_DRAWN + TB_ROW_H_SCALE + TB_ROW_H_PARTNO,
        b + TB_ROW_H_DRAWN + TB_ROW_H_SCALE + TB_ROW_H_PARTNO + TB_ROW_H_TITLE,
        b + TB_HEIGHT,
    ]

    vy = [rows[i] + (rows[i + 1] - rows[i]) * 0.3 for i in range(5)]

    _line(factory, l, rows[0], r, rows[0])
    _line(factory, r, rows[0], r, rows[5])
    _line(factory, r, rows[5], l, rows[5])
    _line(factory, l, rows[5], l, rows[0])

    for y in rows[1:5]:
        _line(factory, l, y, r, y)

    c0 = l + TB_WIDTH / 3
    c1 = l + 2 * TB_WIDTH / 3
    _line(factory, c0, rows[0], c0, rows[1])
    _line(factory, c1, rows[0], c1, rows[1])

    _label(view_com, "DRAWN BY:",  l  + 1, rows[1] - 1)
    _label(view_com, "DATE:",      c0 + 1, rows[1] - 1)
    _label(view_com, "APPROVED:",  c1 + 1, rows[1] - 1)

    _value(view_com, "Drawn_By",   l  + 1, vy[0])
    _value(view_com, "Date",       c0 + 1, vy[0])
    _value(view_com, "Approved",   c1 + 1, vy[0])

    _line(factory, c0, rows[1], c0, rows[2])
    _line(factory, c1, rows[1], c1, rows[2])

    _label(view_com, "SCALE:",    l  + 1, rows[2] - 1)
    _label(view_com, "SHEET:",    c0 + 1, rows[2] - 1)
    _label(view_com, "REVISION:", c1 + 1, rows[2] - 1)

    _value(view_com, "Scale",    l  + 1, vy[1])
    _value(view_com, "Sheet",    c0 + 1, vy[1])
    _value(view_com, "Revision", c1 + 1, vy[1])

    mid = l + 2 * TB_WIDTH / 3
    _line(factory, mid, rows[2], mid, rows[3])

    _label(view_com, "PART NUMBER:", l   + 1, rows[3] - 1)
    _label(view_com, "MATERIAL:",    mid + 1, rows[3] - 1)

    _value(view_com, "Part_Number", l   + 1, vy[2])
    _value(view_com, "Material",    mid + 1, vy[2])

    _label(view_com, "TITLE:", l + 1, rows[4] - 1)
    _value(view_com, "Title",  l + 1, vy[3], size=5.0)

    _value(view_com, "Company",
           l + TB_WIDTH / 2,
           (rows[4] + rows[5]) / 2,
           size=5.0,
           anchor=CatTextAnchorPosition.catMiddleCenter)


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

    sheet_w = sheet.get_paper_width()
    sheet_h = sheet.get_paper_height()
    print(f"\n Active sheet: {sheet.name}  |  {sheet_w:.0f} x {sheet_h:.0f} mm")

    try:
        bg_view = sheet_com.GetBackgroundView()
    except Exception:
        bg_view = sheet_com.Views.Item(2)

    bg_view.Activate()

    factory = bg_view.Factory2D

    bx1, by1, bx2, by2 = _draw_border(factory, sheet_w, sheet_h)
    _draw_title_block(factory, bg_view, bx1, by1, bx2, by2)

    bg_view.SaveEdition()

    sheet_com.Views.Item(1).Activate()                                                                               #Return to main view
    caa.active_window.active_viewer.reframe()                                                                        #Zoom to fit entire sheet

    print(f"  Border and title block added.")
    print(f"  Border:      ({bx1:.0f}, {by1:.0f}) to ({bx2:.0f}, {by2:.0f}) mm")
    print(f"  Title block: {TB_WIDTH:.0f} x {TB_HEIGHT:.0f} mm at lower-right of border\n")
