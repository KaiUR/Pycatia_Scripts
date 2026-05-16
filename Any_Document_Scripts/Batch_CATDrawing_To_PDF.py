'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Batch_CATDrawing_To_PDF.py
    Version:        1.0
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Export all CATDrawing files in a selected folder to PDF.
    Author:         Kai-Uwe Rathjen
    Date:           16.05.26
    Description:    This script will open a folder selection dialog. For every .CATDrawing file found
                    in the selected folder, it will open the drawing, export it as a PDF to a subfolder
                    named "PDF_Export" inside the selected folder, and close the drawing. Already-open
                    documents in CATIA are not affected.
    dependencies = [
                    "pycatia",
                    "wxPython",
                    ]
    requirements:   Python >= 3.10
                    pycatia
                    wxPython
                    Catia V5 running (no specific open document required).
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

if __name__ == "__main__":
    caa = catia()

    app = wx.App(None)
    dlg = wx.DirDialog(None, "Select folder containing CATDrawing files",
            style=wx.DD_DEFAULT_STYLE | wx.STAY_ON_TOP)
    wx.CallAfter(_bring_to_front, dlg)

    if dlg.ShowModal() != wx.ID_OK:
        dlg.Destroy()
        print("Cancelled")
        exit()

    source_folder = Path(dlg.GetPath())
    dlg.Destroy()

    drawing_files = list(source_folder.glob("*.CATDrawing"))                                                      #Find all CATDrawing files

    if not drawing_files:
        print(f"No CATDrawing files found in: {source_folder}")
        exit()

    output_folder = source_folder / "PDF_Export"
    output_folder.mkdir(parents=True, exist_ok=True)                                                              #Create output folder

    print(f"\n Found {len(drawing_files)} CATDrawing file(s)\n")
    print(f" Output folder: {output_folder}\n")

    success = 0
    failed  = 0

    for drawing_path in drawing_files:
        doc_name = drawing_path.stem
        pdf_path = output_folder / (doc_name + ".pdf")
        print(f"  Processing: {drawing_path.name}")

        try:
            doc = caa.documents.open(str(drawing_path))                                                           #Open the drawing
            caa.active_document.export_data(str(pdf_path), "PDF", overwrite=True)                                 #Export as PDF
            caa.active_document.close()                                                                           #Close the drawing
            print(f"    Saved: {pdf_path.name}")
            success += 1
        except Exception as e:
            print(f"    Failed: {e}")
            failed += 1
            try:
                caa.active_document.close()                                                                       #Attempt to close even if export failed
            except Exception:
                pass

    print(f"\n\n Completed - {success} exported, {failed} failed\n\n")
