'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Export_Drawing_Dimensions_To_CSV.py
    Version:        1.1
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        Export all dimensions from a CATDrawing to a CSV file.
    Author:         Kai-Uwe Rathjen
    Date:           21.05.26
    Description:    This script iterates all sheets and views in the active CATDrawing document and
                    exports every dimension to a CSV file. Columns: Sheet, View, Dimension Name,
                    Type, Value. The CSV is saved next to the CATDrawing file, or in Downloads if
                    unsaved. Useful for design audits, tolerance checks, and drawing reviews.
    dependencies = [
                    "pycatia",
                    ]
    requirements:   Python >= 3.10
                    pycatia
                    Catia V5 running with an open CATDrawing document.
    -----------------------------------------------------------------------------------------------------------------------

    Change:         1.1 - Replaced hardcoded DIM_TYPES dict with CatDimType enum lookup (pycatia.enumeration.enums).
                        Fixes incorrect type labels for indices 3-9 and adds coverage for all 21 enum values (0-20).

    -----------------------------------------------------------------------------------------------------------------------
'''

#Imports
from pycatia import catia
from pycatia.drafting_interfaces.drawing_document import DrawingDocument
from pycatia.enumeration.enums import CatDimType
from pathlib import Path
import re

def _dim_type_name(type_int):                                                                                      #Convert CatDimType int to readable string via enum
    try:
        raw = CatDimType(type_int).name                                                                            #e.g. "catDimRadiusTangent"
        label = raw[6:]                                                                                            #strip "catDim" prefix
        return re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', label)                                                         #insert space before each capital run: "Radius Tangent"
    except ValueError:
        return f"Type {type_int}"

def _dim_value(dim_com):
    try:
        return round(dim_com.GetValue().GetMainValue(), 6)
    except Exception:
        try:
            params = dim_com.Parameters
            if params.Count > 0:
                return params.Item(1).ValueAsString()
        except Exception:
            pass
    return ""

if __name__ == "__main__":
    caa = catia()                                                                                                   #Catia application instance
    active_doc = caa.active_document                                                                               #Current open document

    try:
        drawing_doc = DrawingDocument(active_doc.com_object)                                                       #Cast to DrawingDocument
        _ = drawing_doc.drawing_root                                                                               #Test access — raises if not a drawing
    except Exception:
        print("A CATDrawing document must be the active document.")
        exit()

    doc_name = active_doc.name.removesuffix('.CATDrawing')
    doc_path_str = str(active_doc.path())

    if doc_path_str == active_doc.name:                                                                            #Unsaved — use Downloads
        output_path = Path.home() / "Downloads" / (doc_name + "_Dimensions.csv")
    else:
        output_path = Path(doc_path_str).parent / (doc_name + "_Dimensions.csv")

    sheets = drawing_doc.drawing_root.sheets
    rows   = []

    for si in range(sheets.count):                                                                                 #Iterate sheets
        sheet     = sheets.item(si + 1)
        sheet_name = sheet.name
        views     = sheet.views

        for vi in range(views.count):                                                                              #Iterate views
            view      = views.item(vi + 1)
            view_name = view.name
            dims      = view.dimensions

            for di in range(dims.count):                                                                           #Iterate dimensions
                dim     = dims.item(di + 1)
                dim_com = dim.com_object

                dim_name  = dim.name
                dim_type  = _dim_type_name(dim.dim_type)
                dim_value = _dim_value(dim_com)

                rows.append({
                    "Sheet":     sheet_name,
                    "View":      view_name,
                    "Name":      dim_name,
                    "Type":      dim_type,
                    "Value":     dim_value,
                })

    print(f"\n Found {len(rows)} dimension(s)\n")

    if not rows:
        print("No dimensions found in this drawing.")
        exit()

    try:
        with open(output_path, "w", encoding="utf-8") as f:                                                       #Write CSV
            f.write("Sheet,View,Name,Type,Value\n")
            for row in rows:
                f.write(
                    f"\"{row['Sheet']}\","
                    f"\"{row['View']}\","
                    f"\"{row['Name']}\","
                    f"\"{row['Type']}\","
                    f"\"{row['Value']}\"\n"
                )
                print(f"  {row['Sheet']} / {row['View']} — {row['Name']} ({row['Type']}): {row['Value']}")

        print(f"\n\n Completed - saved to: {output_path}\n\n")

    except PermissionError:
        print("Error: Permission denied. Is the output file already open in another program?")
    except IOError as e:
        print(f"Error: Could not write to file. {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
