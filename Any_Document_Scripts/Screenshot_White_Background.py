'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Screenshot_White_Background.py
    Version:        1.1
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Capture a screenshot of the active document with a white background.
    Author:         Kai-Uwe Rathjen
    Date:           21.05.26
    Description:    This script hides the specification tree, sets the viewer background to white,
                    captures the 3D or 2D viewer to an image file, then restores the original
                    background colour and layout. Output format is selected via file extension
                    (BMP, JPEG, TIFF). The image is captured at the current viewer resolution.
                    Useful for generating clean documentation images without manual UI adjustments.
    dependencies = [
                    "pycatia",
                    "wxPython",
                    ]
    requirements:   Python >= 3.10
                    pycatia
                    wxPython
                    Catia V5 running with an open document.
    -----------------------------------------------------------------------------------------------------------------------

    Change:         1.1 - Fixed capture API: use pycatia Viewer wrapper, capture_to_file(format, path)
                          with CatCaptureFormat enum. Fixed background colour API: get/put_background_color
                          with 0-1 float tuples. Removed unsupported width/height parameters. Replaced PNG
                          (not supported by CatCaptureFormat) with BMP/JPEG/TIFF.

    -----------------------------------------------------------------------------------------------------------------------
'''

#Imports
from pycatia import catia
from pycatia.in_interfaces.window import Window
from pycatia.enumeration.enums import CatCaptureFormat
from pathlib import Path
import wx
import ctypes

FORMAT_MAP = {                                                                                                      #File extension to CatCaptureFormat
    ".bmp":  CatCaptureFormat.catCaptureFormatBMP,
    ".jpg":  CatCaptureFormat.catCaptureFormatJPEG,
    ".jpeg": CatCaptureFormat.catCaptureFormatJPEG,
    ".tif":  CatCaptureFormat.catCaptureFormatTIFF,
    ".tiff": CatCaptureFormat.catCaptureFormatTIFF,
}

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
        super().__init__(parent, title="Screenshot Settings", size=(420, 160),
                         style=wx.DEFAULT_DIALOG_STYLE | wx.STAY_ON_TOP)

        vbox = wx.BoxSizer(wx.VERTICAL)
        grid = wx.FlexGridSizer(1, 3, 8, 8)

        self.path_ctrl = wx.TextCtrl(self, value=default_name)
        browse_btn     = wx.Button(self, label="Browse...")

        grid.AddMany([
            (wx.StaticText(self, label="Output file:")), (self.path_ctrl, 1, wx.EXPAND), (browse_btn,),
        ])
        grid.AddGrowableCol(1, 1)

        vbox.Add(grid, proportion=0, flag=wx.ALL | wx.EXPAND, border=12)
        vbox.Add(wx.StaticText(self, label="  Supported formats: BMP, JPEG, TIFF"),
                 flag=wx.LEFT | wx.BOTTOM, border=12)
        vbox.Add(self.CreateButtonSizer(wx.OK | wx.CANCEL), flag=wx.ALIGN_CENTER | wx.BOTTOM, border=10)
        self.SetSizer(vbox)
        browse_btn.Bind(wx.EVT_BUTTON, self.on_browse)

    def on_browse(self, event):
        dlg = wx.FileDialog(
            self, "Save screenshot as",
            wildcard="BMP files (*.bmp)|*.bmp|JPEG files (*.jpg)|*.jpg|TIFF files (*.tif)|*.tif",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        )
        if dlg.ShowModal() == wx.ID_OK:
            self.path_ctrl.SetValue(dlg.GetPath())
        dlg.Destroy()

    def get_values(self):
        path = self.path_ctrl.GetValue().strip()
        if not path:
            wx.MessageBox("Please specify an output file path.", "Error", wx.OK | wx.ICON_ERROR)
            return None
        ext = Path(path).suffix.lower()
        if ext not in FORMAT_MAP:
            wx.MessageBox(
                f"Unsupported extension '{ext}'.\nUse .bmp, .jpg, .tif, or .tiff.",
                "Error", wx.OK | wx.ICON_ERROR,
            )
            return None
        return path


if __name__ == "__main__":
    caa = catia()                                                                                                   #Catia application instance
    active_doc = caa.active_document                                                                               #Current open document

    doc_stem = Path(active_doc.name).stem
    doc_path_str = str(active_doc.path())
    if doc_path_str == active_doc.name:
        default_out = str(Path.home() / "Downloads" / (doc_stem + ".bmp"))
    else:
        default_out = str(Path(doc_path_str).parent / (doc_stem + ".bmp"))

    app = wx.App(None)
    dlg = ScreenshotDialog(None, default_out)
    wx.CallAfter(_bring_to_front, dlg)

    if dlg.ShowModal() != wx.ID_OK:
        dlg.Destroy()
        print("Cancelled")
        exit()

    output_path = dlg.get_values()
    dlg.Destroy()

    if output_path is None:
        exit()

    capture_format = FORMAT_MAP[Path(output_path).suffix.lower()]

    window     = Window(caa.application.active_window.com_object)                                                  #pycatia Window wrapper
    window_com = window.com_object                                                                                 #Raw COM for Layout (no pycatia property)
    viewer     = window.active_viewer                                                                              #pycatia Viewer wrapper

    orig_layout = None
    try:
        orig_layout = window_com.Layout                                                                            #Save current layout
        window_com.Layout = 2                                                                                      #catWindowGeomOnly — hide spec tree
    except Exception as e:
        print(f"  Note: Could not hide specification tree ({e})")

    orig_color = None
    try:
        orig_color = viewer.get_background_color()                                                                 #Returns (r, g, b) tuple in 0-1 range
        viewer.put_background_color((1.0, 1.0, 1.0))                                                              #White background
    except Exception as e:
        print(f"  Note: Could not set background colour ({e})")

    try:
        viewer.capture_to_file(capture_format, output_path)                                                        #Capture at current viewer resolution
        print(f"\n\n Completed - saved to: {output_path}\n\n")
    except Exception as e:
        print(f"Error: Capture failed. {e}")
    finally:
        try:
            if orig_color is not None:
                viewer.put_background_color(orig_color)                                                            #Restore original background colour
        except Exception:
            pass
        try:
            if orig_layout is not None:
                window_com.Layout = orig_layout                                                                    #Restore original layout
        except Exception:
            pass
