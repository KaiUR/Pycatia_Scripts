'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Update_Title_Block_Headings.py
    Version:        1.0
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Edit the heading labels in the title block of the active CATDrawing sheet.
    Author:         Kai-Uwe Rathjen
    Date:           21.05.26
    Description:    Reads all heading label texts (items whose current text ends with a colon,
                    e.g. "DRAWN BY:", "TITLE:", "PART NUMBER:") from the background view of the
                    active drawing sheet. A dialog displays each heading with an editable text
                    field pre-filled with its current value. Confirmed changes are written back
                    immediately. Fields left unchanged are skipped. Only the active sheet is
                    processed.
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


def _get_heading_texts_from_view(view_com):
    """Return {name: current_text} for all text items whose text ends with ':'."""
    headings = {}
    try:
        texts_col = view_com.Texts
        for i in range(texts_col.Count):
            t = texts_col.Item(i + 1)
            try:
                if t.Text.strip().endswith(":"):
                    headings[t.Name] = t.Text
            except Exception:
                pass
    except Exception:
        pass
    return headings


class HeadingsDialog(wx.Dialog):
    def __init__(self, parent, headings):
        super().__init__(parent, title="Edit Title Block Headings",
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER | wx.STAY_ON_TOP)

        self.original = headings

        panel = wx.Panel(self)
        vbox  = wx.BoxSizer(wx.VERTICAL)

        info = wx.StaticText(panel, label=f"Found {len(headings)} heading(s). Edit the text for each heading below.\n"
                                          "Fields left unchanged will be skipped.")
        vbox.Add(info, flag=wx.ALL, border=10)

        grid = wx.FlexGridSizer(len(headings), 2, 8, 10)
        grid.AddGrowableCol(1, 1)

        self.controls = {}
        for name, current_text in sorted(headings.items(), key=lambda x: x[1]):
            grid.Add(wx.StaticText(panel, label="Current:  " + current_text), flag=wx.ALIGN_CENTER_VERTICAL)
            tc = wx.TextCtrl(panel, value=current_text, size=(260, -1))
            grid.Add(tc, flag=wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)
            self.controls[name] = tc

        vbox.Add(grid, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, border=14)
        panel.SetSizer(vbox)

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(panel, proportion=1, flag=wx.EXPAND)
        main_sizer.Add(self.CreateButtonSizer(wx.OK | wx.CANCEL), flag=wx.ALIGN_CENTER | wx.ALL, border=10)
        self.SetSizer(main_sizer)
        self.Fit()
        self.SetMinSize(self.GetSize())

    def get_changes(self):
        """Return {name: new_text} only for headings whose text was changed."""
        changes = {}
        for name, tc in self.controls.items():
            new_val = tc.GetValue()
            if new_val != self.original[name]:
                changes[name] = new_val
        return changes


if __name__ == "__main__":
    caa = catia()                                                                                                     #CATIA application instance
    active_doc = caa.active_document

    try:
        drawing_doc = DrawingDocument(active_doc.com_object)
        _ = drawing_doc.drawing_root
    except Exception:
        print("A CATDrawing document must be the active document.")
        exit()

    active_sheet_com = None
    try:
        active_sheet_com = drawing_doc.drawing_root.com_object.Sheets.ActiveSheet
    except Exception:
        sheets = drawing_doc.drawing_root.sheets
        if sheets.count > 0:
            active_sheet_com = sheets.item(1).com_object

    if active_sheet_com is None:
        print("Could not access the active drawing sheet.")
        exit()

    all_headings = {}

    try:
        bg_view = active_sheet_com.GetBackgroundView()
        all_headings.update(_get_heading_texts_from_view(bg_view))
    except Exception:
        pass

    try:
        views_com = active_sheet_com.Views
        for vi in range(views_com.Count):
            view_com = views_com.Item(vi + 1)
            all_headings.update(_get_heading_texts_from_view(view_com))
    except Exception as e:
        print(f"  Warning: Could not read views ({e})")

    if not all_headings:
        print("No heading labels found in the active drawing sheet.")
        exit()

    print(f"\n Found {len(all_headings)} heading(s)\n")

    app = wx.App(None)
    dlg = HeadingsDialog(None, all_headings)
    wx.CallAfter(_bring_to_front, dlg)

    if dlg.ShowModal() != wx.ID_OK:
        dlg.Destroy()
        print("Cancelled.")
        exit()

    changes = dlg.get_changes()
    dlg.Destroy()

    if not changes:
        print("No changes made.")
        exit()

    updated = 0
    failed  = 0

    for text_name, new_text in changes.items():
        try:
            found = False
            try:
                bg_view   = active_sheet_com.GetBackgroundView()
                texts_com = bg_view.Texts
                for ti in range(texts_com.Count):
                    t = texts_com.Item(ti + 1)
                    if t.Name == text_name:
                        t.Text = new_text
                        found  = True
                        break
            except Exception:
                pass

            if not found:
                views_com = active_sheet_com.Views
                for vi in range(views_com.Count):
                    view_com  = views_com.Item(vi + 1)
                    try:
                        texts_com = view_com.Texts
                        for ti in range(texts_com.Count):
                            t = texts_com.Item(ti + 1)
                            if t.Name == text_name:
                                t.Text = new_text
                                found  = True
                                break
                    except Exception:
                        pass
                    if found:
                        break

            if found:
                print(f"  Updated: '{all_headings[text_name]}' -> '{new_text}'")
                updated += 1
            else:
                print(f"  Not found: '{text_name}' (skipped)")
                failed += 1

        except Exception as e:
            print(f"  Failed to update '{text_name}': {e}")
            failed += 1

    print(f"\n Completed — {updated} updated, {failed} skipped/failed\n")
