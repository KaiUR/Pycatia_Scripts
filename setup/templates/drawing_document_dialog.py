'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Your_Script_Name.py
    Version:        1.1
    Code:           Python3.10.4, Pycatia 0.9.6
    Release:        V5R32
    Purpose:        EDIT: One line summary shown on the script button.
    Author:         EDIT: Your Name
    Date:           EDIT: DD.MM.YY
    Description:    EDIT: Full description of what the script does.
                    EDIT: Continuation lines must be indented.
    dependencies = [
                    "pycatia",
                    "wxPython",
                    ]
    requirements:   Python >= 3.10
                    pycatia
                    wxPython
                    Catia V5 running with an open CATDrawing document.
    -----------------------------------------------------------------------------------------------------------------------

    Change:         31.05.26 1.1: Use vbox.Fit(self) for dialog sizing.

    -----------------------------------------------------------------------------------------------------------------------
'''

#Imports
from pycatia import catia
from pycatia.drafting_interfaces.drawing_document import DrawingDocument
from pathlib import Path
import wx
import wx.lib.dialogs
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


class ScriptDialog(wx.Dialog):
    def __init__(self, parent, title):
        super().__init__(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.STAY_ON_TOP)

        vbox = wx.BoxSizer(wx.VERTICAL)
        grid = wx.FlexGridSizer(2, 2, 10, 10)                                                                  #EDIT: First arg = number of parameter rows

        # EDIT: Add one StaticText + TextCtrl pair per input. Duplicate rows as needed.
        grid.Add(wx.StaticText(self, label="EDIT Parameter 1:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.param_1 = wx.TextCtrl(self, value="EDIT default")                                                 #EDIT: Set field default value
        grid.Add(self.param_1, 1, wx.EXPAND)

        grid.Add(wx.StaticText(self, label="EDIT Parameter 2:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.param_2 = wx.TextCtrl(self, value="EDIT default")                                                 #EDIT: Set field default value
        grid.Add(self.param_2, 1, wx.EXPAND)

        grid.AddGrowableCol(1, 1)
        vbox.Add(grid, 1, wx.ALL | wx.EXPAND, 15)

        btn_sizer = wx.StdDialogButtonSizer()
        btn_ok     = wx.Button(self, wx.ID_OK,     label="OK")
        btn_cancel = wx.Button(self, wx.ID_CANCEL, label="Cancel")
        btn_ok.SetDefault()
        btn_sizer.AddButton(btn_ok)
        btn_sizer.AddButton(btn_cancel)
        btn_sizer.Realize()
        vbox.Add(btn_sizer, 0, wx.ALL | wx.EXPAND, 10)

        self.SetSizer(vbox)
        vbox.Fit(self)
        self.Center()

if __name__ == "__main__":
    caa = catia()                                                                                               #Catia application instance
    active_doc = caa.active_document                                                                           #Current active document
    app = wx.App(None)                                                                                         #Initialize wx application

    try:                                                                                                       #Check that a CATDrawing is active
        drawing_doc = DrawingDocument(active_doc.com_object)
        _ = drawing_doc.drawing_root
    except Exception:
        wx.MessageDialog(None, "A CATDrawing document must be the active document.", "Error",
                wx.OK | wx.ICON_ERROR | wx.STAY_ON_TOP).ShowModal()
        exit()

    drawing_root = drawing_doc.drawing_root                                                                    #Root drawing object
    sheets       = drawing_root.sheets                                                                         #All sheets in the drawing
    sheet        = sheets.active_sheet                                                                         #Currently active sheet

    dlg = ScriptDialog(None, "EDIT: Dialog Title")                                                             #EDIT: Set dialog title
    wx.CallAfter(_bring_to_front, dlg)
    if dlg.ShowModal() != wx.ID_OK:                                                                            #If user cancelled
        dlg.Destroy()
        exit()

    param_1 = dlg.param_1.GetValue().strip()                                                                   #EDIT: Get each field value
    param_2 = dlg.param_2.GetValue().strip()                                                                   #EDIT: Get each field value
    dlg.Destroy()                                                                                              #Destroy dialog

    # EDIT: Validate inputs
    if not param_1:
        wx.MessageDialog(None, "EDIT: Parameter 1 cannot be empty.", "Error",
                wx.OK | wx.ICON_ERROR | wx.STAY_ON_TOP).ShowModal()
        exit()

    # TODO: Add script logic here using param_1, param_2, drawing_root, sheets, sheet.
    #
    # Common access patterns:
    #   sheet.name                                          — sheet name
    #   sheet.get_paper_width(), sheet.get_paper_height()   — paper dimensions in mm
    #   sheet.com_object.GetBackgroundView()                — background view (title block layer)
    #   sheet.com_object.Views.Item(1)                      — main working view
    #   bg_view.Factory2D                                   — 2D geometry factory
    #   bg_view.Texts                                       — text items in the view
    #   bg_view.SaveEdition()                               — must be called after editing a background view
    #
    # To show large text results use ScrolledMessageDialog:
    #   wx.lib.dialogs.ScrolledMessageDialog(None, result_text, "Results", size=(500, 400)).ShowModal()
    #
    # File I/O alongside the document:
    #   doc_name    = drawing_doc.name.removesuffix('.CATDrawing')
    #   output_path = str(Path(str(drawing_doc.path())).parent / (doc_name + "_output.csv"))
    #   try:
    #       with open(output_path, "w") as f:
    #           f.write(...)
    #   except PermissionError:
    #       wx.MessageDialog(None, "Permission denied. Is the file open in another program?", "Error",
    #               wx.OK | wx.ICON_ERROR | wx.STAY_ON_TOP).ShowModal()
    #   except Exception as e:
    #       wx.MessageDialog(None, f"Could not write file: {e}", "Error",
    #               wx.OK | wx.ICON_ERROR | wx.STAY_ON_TOP).ShowModal()

    print("\n\n Completed\n\n")
