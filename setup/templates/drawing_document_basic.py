'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Your_Script_Name.py
    Version:        1.0
    Code:           Python3.10.4, Pycatia 0.10.0
    Release:        V5R32
    Purpose:        EDIT: One line summary shown on the script button.
    Author:         EDIT: Your Name
    Date:           EDIT: DD.MM.YY
    Description:    EDIT: Full description of what the script does.
                    EDIT: Continuation lines must be indented.
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
    caa = catia()                                                                                               #Catia application instance
    active_doc = caa.active_document                                                                           #Current active document

    try:                                                                                                       #Check that a CATDrawing is active
        drawing_doc = DrawingDocument(active_doc.com_object)
        _ = drawing_doc.drawing_root
    except Exception:
        print("A CATDrawing document must be the active document.")
        exit()

    drawing_root = drawing_doc.drawing_root                                                                    #Root drawing object
    sheets       = drawing_root.sheets                                                                         #All sheets in the drawing
    sheet        = sheets.active_sheet                                                                         #Currently active sheet

    # TODO: Add script logic here.
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
    # Iterating all sheets:
    #   for i in range(1, sheets.count + 1):
    #       s = sheets.item(i)
    #
    # File I/O alongside the document:
    #   doc_name    = drawing_doc.name.removesuffix('.CATDrawing')
    #   output_path = str(Path(str(drawing_doc.path())).parent / (doc_name + "_output.csv"))
    #   try:
    #       with open(output_path, "w") as f:
    #           f.write(...)
    #   except PermissionError:
    #       print("Error: Permission denied. Is the file already open in another program?")
    #   except IOError as e:
    #       print(f"Error: Could not write to file. {e}")
    #   except Exception as e:
    #       print(f"An unexpected error occurred: {e}")

    print("\n\n Completed\n\n")
