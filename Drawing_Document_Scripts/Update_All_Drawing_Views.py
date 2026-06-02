'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Update_All_Drawing_Views.py
    Version:        1.0
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Force update all views across all sheets in the active drawing document.
    Author:         Kai-Uwe Rathjen
    Date:           28.05.26
    Description:    This script calls the CATIA drawing document Update method which regenerates
                    all generative views on all sheets. Useful after the linked 3D model has been
                    modified and the drawing views are out of date. A count of sheets and views
                    found is printed before the update so the user can confirm the correct document
                    is active.
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

if __name__ == "__main__":
    caa = catia()                                                                                                    #Catia application instance
    active_doc = caa.active_document                                                                                 #Current active document

    try:
        drawing_doc = DrawingDocument(active_doc.com_object)                                                         #Cast to DrawingDocument
        _ = drawing_doc.drawing_root                                                                                  #Access drawing root to confirm doc type
    except Exception:
        print("A CATDrawing document must be the active document.")
        exit()

    sheet_count = drawing_doc.drawing_root.sheets.count                                                              #Number of sheets

    print(f"\n Found {sheet_count} sheet(s) — updating all views...\n")

    drawing_doc.update()                                                                                             #Update all views on all sheets

    print("\n\n Completed\n\n")
