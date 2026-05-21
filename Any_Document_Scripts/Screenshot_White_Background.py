'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Screenshot_White_Background.py
    Version:        1.0
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Capture a screenshot of the active document with a white background.
    Author:         Kai-Uwe Rathjen
    Date:           21.05.26
    Description:    This script hides the specification tree, sets the viewer background to white,
                    captures the 3D or 2D viewer to a PNG file, then restores the original background
                    colour and layout. The output resolution can be set in the dialog. Useful for
                    generating clean documentation images without manual UI adjustments.
    dependencies = [
                    "pycatia",
                    "wxPython",
                    ]
    requirements:   Python >= 3.10
                    pycatia
                    wxPython
                    Catia V5 running with an open document.
    -----------------------------------------------------------------------------------------------------------------------

    Change:

    -----------------------------------------------------------------------------------------------------------------------
'''

#Imports
from pycatia import catia
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


class ScreenshotDialog(wx.Dialog):
    def __init__(self, parent, default_name):
        super().__init__(parent, title="Screenshot Settings", size=(420, 220),
                         style=wx.DEFAULT_DIALOG_STYLE | wx.STAY_ON_TOP)

        vbox  = wx.BoxSizer(wx.VERTICAL)
        grid  = wx.FlexGridSizer(4, 3, 8, 8)

        self.path_ctrl   = wx.TextCtrl(self, value=default_name)
        browse_btn       = wx.Button(self, label="Browse...")
        self.width_ctrl  = wx.TextCtrl(self, value="1920")
        self.height_ctrl = wx.TextCtrl(self, value="1080")

        grid.AddMany([
            (wx.StaticText(self, label="Output file:")), (self.path_ctrl, 1, wx.EXPAND), (browse_btn,),
            (wx.StaticText(self, label="Width (px):")),  (self.width_ctrl, 1, wx.EXPAND),  (wx.StaticText(self, label="px")),
            (wx.StaticText(self, label="Height (px):")), (self.height_ctrl, 1, wx.EXPAND), (wx.StaticText(self, label="px")),
        ])
        grid.AddGrowableCol(1, 1)

        vbox.Add(grid, proportion=0, flag=wx.ALL | wx.EXPAND, border=12)
        vbox.Add(self.CreateButtonSizer(wx.OK | wx.CANCEL), flag=wx.ALIGN_CENTER | wx.BOTTOM, border=10)
        self.SetSizer(vbox)
        browse_btn.Bind(wx.EVT_BUTTON, self.on_browse)

    def on_browse(self, event):
        dlg = wx.FileDialog(self, "Save screenshot as", wildcard="PNG files (*.png)|*.png|BMP files (*.bmp)|*.bmp|JPG files (*.jpg)|*.jpg",
                            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
        if dlg.ShowModal() == wx.ID_OK:
            self.path_ctrl.SetValue(dlg.GetPath())
        dlg.Destroy()

    def get_values(self):
        try:
            w = int(self.width_ctrl.GetValue())
            h = int(self.height_ctrl.GetValue())
        except ValueError:
            wx.MessageBox("Width and Height must be integers.", "Error", wx.OK | wx.ICON_ERROR)
            return None
        if w <= 0 or h <= 0:
            wx.MessageBox("Width and Height must be greater than zero.", "Error", wx.OK | wx.ICON_ERROR)
            return None
        path = self.path_ctrl.GetValue().strip()
        if not path:
            wx.MessageBox("Please specify an output file path.", "Error", wx.OK | wx.ICON_ERROR)
            return None
        return path, w, h


if __name__ == "__main__":
    caa = catia()                                                                                                   #Catia application instance
    active_doc = caa.active_document                                                                               #Current open document

    doc_stem = Path(active_doc.name).stem
    doc_path_str = str(active_doc.path())
    if doc_path_str == active_doc.name:
        default_out = str(Path.home() / "Downloads" / (doc_stem + ".png"))
    else:
        default_out = str(Path(doc_path_str).parent / (doc_stem + ".png"))

    app = wx.App(None)
    dlg = ScreenshotDialog(None, default_out)
    wx.CallAfter(_bring_to_front, dlg)

    if dlg.ShowModal() != wx.ID_OK:
        dlg.Destroy()
        print("Cancelled")
        exit()

    result = dlg.get_values()
    dlg.Destroy()

    if result is None:
        exit()

    output_path, img_width, img_height = result

    window_com = caa.application.active_window.com_object                                                         #Active CATIA window COM object

    original_layout = None
    orig_r = orig_g = orig_b = None

    try:
        original_layout = window_com.Layout                                                                        #Save current layout
        window_com.Layout = 2                                                                                      #catWindowGeomOnly — hide spec tree
    except Exception as e:
        print(f"  Note: Could not hide specification tree ({e})")

    viewer_com = None
    try:
        viewer_com = window_com.Viewers.ActiveViewer                                                               #Active viewer COM object
        bg = viewer_com.BackGroundColor
        orig_r, orig_g, orig_b = bg.Red, bg.Green, bg.Blue                                                        #Save original background colour
        bg.Red   = 255                                                                                             #Set background to white
        bg.Green = 255
        bg.Blue  = 255
    except Exception as e:
        print(f"  Note: Could not set background colour ({e})")

    try:
        if viewer_com:
            viewer_com.CaptureToFile(output_path, img_width, img_height)                                          #Capture viewer to file
            print(f"\n\n Completed - saved to: {output_path}\n\n")
        else:
            print("Error: Could not access the active viewer.")
    except Exception as e:
        print(f"Error: Capture failed. {e}")
    finally:
        try:
            if orig_r is not None:
                bg = viewer_com.BackGroundColor
                bg.Red, bg.Green, bg.Blue = orig_r, orig_g, orig_b                                                #Restore original background colour
        except Exception:
            pass
        try:
            if original_layout is not None:
                window_com.Layout = original_layout                                                                #Restore original layout
        except Exception:
            pass
