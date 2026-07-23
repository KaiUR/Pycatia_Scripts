# Pycatia Scripts

A collection of [PyCATIA](https://github.com/evereux/pycatia) scripts for automating CATIA V5. Each script runs standalone and can be launched from the terminal or directly from the scripts folder — no launcher required. [CatiaMenuWin32](https://github.com/KaiUR/CatiaMenuWin32) is an optional native Windows launcher that syncs and presents these scripts as clickable buttons.

## 📋 Requirements

**Python:** 3.9+

**Packages:**

Run the included setup script:
```
setup\setup.bat
```

Or install from the included requirements file:
```
pip install -r setup\requirements.txt
```

Or, if using [CatiaMenuWin32](https://github.com/KaiUR/CatiaMenuWin32), use the **↓ Deps** button to install automatically.

**CATIA V5** must be running before executing scripts that interact with it.

---

## 📂 Scripts

### Any Document Scripts

| Script | Description |
|--------|-------------|
| `Copy_Name_and_Colour.py` | Copy the name, colour, line weight and line type from one element to a selection of elements |
| `Export_Properties_To_CSV.py` | Export standard and user-defined document properties to CSV |
| `Find_And_Select_By_Name.py` | Find and select all hybrid shapes whose names contain a search string |
| `Hide_Planes_And_Axis_Systems.py` | Hides all planes and axis systems in a Part or Product document |
| `Rename_Hybrid_Shapes.py` | Rename hybrid shapes interactively via message box |
| `Replace_Name_Hybrid_Shapes.py` | Search and replace any hybrid shape name |
| `Reset_Visual_Properties.py` | Reset colour, line weight, line type and opacity of selected elements to CATIA defaults |
| `Screenshot_White_Background.py` | Capture a white-background screenshot of the active 3D view to PNG |
| `Swap_Names.py` | Swap the names of two selected elements |
| `Toggle_Show_Hide_Geometric_Set.py` | Toggle the visibility of the contents and children of a selected geometric set (the set itself is unchanged) |

### Drawing Document Scripts

| Script | Description |
|--------|-------------|
| `Add_Border_And_Title_Block.py` | Add an ISO 5457 border and title block to the active sheet of an open CATDrawing |
| `Add_Border_And_Title_Block_With_Values.py` | Add an ISO 5457 border and title block to the active sheet, with a dialog to enter field values |
| `Batch_CATDrawing_To_DXF.py` | Export all CATDrawing files in a selected folder to DXF |
| `Batch_CATDrawing_To_PDF.py` | Export all CATDrawing files in a selected folder to PDF |
| `Create_Drawing_Border_And_Title_Block.py` | Create a new CATDrawing with an ISO 5457 border and ISO 7200-style title block for A0–A4 paper sizes |
| `Create_Drawing_Border_And_Title_Block_With_Values.py` | Create a new CATDrawing with an ISO 5457 border and title block, with a dialog to enter field values |
| `Export_Drawing_Dimensions_To_CSV.py` | Export all dimensions from the active CATDrawing to CSV |
| `Update_All_Drawing_Views.py` | Force update all views across all sheets in the active drawing document |
| `Update_Title_Block_From_Properties.py` | Map document properties to drawing title block text fields via a GUI dialog |
| `Update_Title_Block_Headings.py` | Edit the heading labels in the title block of the active CATDrawing sheet |

### Part Document Scripts

| Script | Description |
|--------|-------------|
| `Axis_To_Axis_Keep_History.py` | Axis-to-axis transformation keeping the original hybrid shape name and parametric history |
| `Axis_To_Axis_Keep_History_And_Structure.py` | Axis-to-axis transformation on all shapes in a geometric set, preserving names, structure and parametric history |
| `Axis_To_Axis_Keep_Name.py` | Axis-to-axis transformation keeping the original hybrid shape name |
| `Axis_To_Axis_Keep_Name_And_Structure.py` | Axis-to-axis transformation on all shapes in a geometric set, preserving names and structure |
| `Batch_Isolate_Geometric_Set.py` | Isolate every element in a geometric set as a datum in one operation |
| `Check_Duplicate_Names_In_Geometric_Set.py` | Scan a geometric set and report any elements that share a name |
| `Colour_Code_By_Geometric_Set.py` | Assign a unique colour from an HSV palette to every shape in each child geometric set |
| `Copy_Geometric_Set_To_New_Part.py` | Copy a selected geometric set and all its contents into a new blank CATPart |
| `Create_Construction_Planes.py` | Create a series of offset planes from a reference plane at a user-defined step and count |
| `Create_ISM_OSM_STEP_Files.py` | Select two faces/surfaces, extract in tangency and export as ISM and OSM STEP files |
| `Create_Spline_From_Coordinates.py` | Create a GSD point set and spline from X Y (or X Y Z) coordinates loaded from a file or pasted into the dialog |
| `Delete_Deactivated_Features.py` | Delete all deactivated hybrid shapes inside a selected geometric set |
| `Delete_Hidden_Elements_In_Geometric_Set.py` | Delete all hidden shapes and hidden child geometric sets inside a selected geometric set |
| `Check_Open_Bodies.py` | Check all solid bodies in the active part for open (zero-volume) geometry |
| `Copy_Parameters_Between_Parts.py` | Copy selected parameters from one open CATPart to another via a GUI dialog |
| `Export_3D_Annotations_To_CSV.py` | Export all FTA 3D annotations from the active part to CSV |
| `Export_All_Parameters_To_CSV.py` | Export all parameters from the active part to CSV |
| `Export_Holes_To_CSV.py` | Export all holes from the active part with type, diameter, depth, thread, and position to CSV |
| `Export_Curve_Lengths_Surface_Areas_To_CSV.py` | Export curve lengths and surface areas from a geometric set to CSV |
| `Export_Geometric_Set_Structure_To_CSV.py` | Export the full geometric set tree and its contents to CSV |
| `Export_Mass_CoG_Inertia_To_CSV.py` | Export mass, centre of gravity and inertia tensor from all solid bodies to CSV |
| `Export_Parameter_Dependencies_To_CSV.py` | Export all parameters with their formula dependencies to a CSV file |
| `Export_Points_Select_Axis_and_Geo_Set_To_CSV.py` | Export points from a geometric set relative to a selected axis system to CSV |
| `Export_Points_Select_Axis_and_Geo_Set_To_XYZ.py` | Export points from a geometric set relative to a selected axis system to XYZ (PCDimms format) |
| `Export_Points_Select_Geo_Set_To_CSV.py` | Export points from a geometric set relative to absolute axis to CSV |
| `Export_Points_Select_Geo_Set_To_XYZ.py` | Export points from a geometric set relative to absolute axis to XYZ (PCDimms format) |
| `Export_Sketch_Constraints_To_CSV.py` | Export all sketch constraints and dimensions from the active part to a CSV file |
| `Extract_Boundary_Curves.py` | Extract boundary edges of a selected surface as datum curves |
| `IGES_Export_Curve_AXIS.py` | Export curve to IGES after moving from a reference axis system to absolute |
| `Insert_Points_Catia.py` | Insert points into active part from tab-separated or CSV file as datums |
| `Insert_Points_Catia_Keep_History.py` | Insert points into active part from tab-separated or CSV file, preserving parametric history |
| `Insert_Points_Catia_With_Names.py` | Insert named points into active part from tab-separated or CSV file as datums |
| `Insert_Points_Catia_With_Names_Keep_History.py` | Insert named points into active part from tab-separated or CSV file, preserving parametric history |
| `Join_Explicit_No_Connect.py` | Join curves or surfaces without connex check, as datum |
| `Join_Explicit_No_Connect_Curve.py` | Join curves without connex check, as datum |
| `Join_Explicit_No_Connect_Surface.py` | Join surfaces without connex check, as datum |
| `List_Properties_To_CSV.py` | Export name, type, colour, line weight, line type and opacity for all shapes in a geometric set to CSV |
| `Match_Properties_In_Geometric_Set.py` | Apply the visual properties of a source element to all shapes in a selected geometric set |
| `Measure_Curve_With_3_PTS_AS_CIRCLE.py` | Measure curve radius using a 3-point circle |
| `Measure_Curve_With_3_PTS_AS_CIRCLE_Keep_Con.py` | Measure curve radius using a 3-point circle without removing construction elements |
| `Measure_Radius_Surface.py` | Measure surface radius using intersection and 3-point circle without removing construction |
| `Measure_Radius_Surface_Keep_Con.py` | Measure surface radius using intersection and 3-point circle, keeping all construction elements |
| `Measure_Radius_Surface_Keep_Con_Auto_Edge.py` | Measure radius of all border edges of a surface automatically via intersection and 3-point circle, keeping construction geometry |
| `Mirror_Keep_History.py` | Mirror hybrid shapes about a plane keeping their original names and parametric history |
| `Mirror_Keep_History_And_Structure.py` | Mirror all shapes in a geometric set about a plane, preserving names, structure and parametric history |
| `Mirror_Keep_Name.py` | Mirror hybrid shapes about a plane keeping their original names |
| `Mirror_Keep_Name_And_Structure.py` | Mirror all shapes in a geometric set about a plane, preserving names and structure |
| `Publish_Hybrid_Shapes_In_Geometric_Set.py` | Publish all hybrid shapes in a selected geometric set |
| `Reorder_Geometric_Set_Alphabetically.py` | Sort all elements inside a geometric set alphabetically by name |
| `Rotate_Angle_Keep_History.py` | Rotate hybrid shapes by an angle around an axis keeping their original names and parametric history |
| `Rotate_Angle_Keep_History_And_Structure.py` | Rotate all shapes in a geometric set by an angle, preserving names, structure and parametric history |
| `Rotate_Angle_Keep_Name.py` | Rotate hybrid shapes by an angle around an axis keeping their original names |
| `Rotate_Angle_Keep_Name_And_Structure.py` | Rotate all shapes in a geometric set by an angle, preserving names and structure |
| `Rotate_Three_Points_Keep_History.py` | Rotate hybrid shapes using three points definition keeping their original names and parametric history |
| `Rotate_Three_Points_Keep_History_And_Structure.py` | Rotate all shapes in a geometric set using three points, preserving names, structure and parametric history |
| `Rotate_Three_Points_Keep_Name.py` | Rotate hybrid shapes using three points definition keeping their original names |
| `Rotate_Three_Points_Keep_Name_And_Structure.py` | Rotate all shapes in a geometric set using three points, preserving names and structure |
| `Scale_Keep_History.py` | Scale hybrid shapes about a center point while keeping their original names and parametric history |
| `Scale_Keep_History_And_Structure.py` | Scale all shapes in a geometric set about a center point, preserving names, structure and parametric history |
| `Scale_Keep_Name.py` | Scale hybrid shapes about a center point while keeping their original names |
| `Scale_Keep_Name_And_Structure.py` | Scale all shapes in a geometric set about a center point, preserving names and structure |
| `Select_By_Colour.py` | Select all shapes in a geometric set whose colour matches a chosen source element |
| `Spline_Through_Points_In_Geometric_Set.py` | Create a spline through all points in a selected geometric set |
| `Translate_Direction_Distance_Keep_History.py` | Translate hybrid shapes keeping their original names and parametric history |
| `Translate_Direction_Distance_Keep_History_And_Structure.py` | Translate all shapes in a geometric set by direction and distance, preserving names, structure and parametric history |
| `Translate_Direction_Distance_Keep_Name.py` | Translate hybrid shapes keeping their original names |
| `Translate_Direction_Distance_Keep_Name_And_Structure.py` | Translate all shapes in a geometric set by direction and distance, preserving names and structure |

### Shape Generation Scripts

| Script | Description |
|--------|-------------|
| `Custom_Coordinate_Airfoil_Generator.py` | Generate a GSD point set and spline from user-supplied X Y (or X Y Z) coordinates loaded from a .dat / .csv file or pasted directly into the dialog |
| `Ellipse_Generator.py` | Generate an ellipse as a point set and closed GSD spline from semi-major and semi-minor axes |
| `Hole_Size_Test_Plate_Generator.py` | Generate a rectangular test plate with a grid of through-holes of incrementally increasing diameter for testing drill bits, gauges, or clearance fits |
| `Involute_Gear_Generator_Mathamatical.py` | Generate an involute gear profile from user-defined parameters |
| `NACA_4_Digit_Airfoil_Generator.py` | Generate a NACA 4-digit series airfoil (e.g. 0010, 2412) as a point set and closed GSD spline at a user-defined chord length and resolution |
| `NACA_5_Digit_Airfoil_Generator.py` | Generate a NACA 5-digit series airfoil (e.g. 23012) as a point set and closed GSD spline at a user-defined chord length and resolution |
| `Plot_2D_Function.py` | Plot y = f(x) as a GSD point set and spline from a user-entered math expression over a specified X range |
| `Plot_3D_Parametric_Curve.py` | Plot a 3D parametric curve x(t), y(t), z(t) as a GSD point set and spline from user-entered expressions |
| `Regular_Polygon_Generator.py` | Generate a regular polygon (triangle, hexagon, etc.) as vertices, edges, and a joined wire; supports custom plane and centre point selection |
| `Sine_Wave_Curve_Generator.py` | Generate a sine wave curve as a point set and GSD spline from amplitude, period, phase, and X range |
| `Spring_Generator.py` | Generate a parametric helical spring solid from wire diameter, coil diameter, free length, and coil count; optional closed (compressed) ends |

### Utility Scripts

| Script | Description |
|--------|-------------|
| `Backup_CATIA_Settings.py` | Zip up the CATSettings folder for selected CATIA V5 versions to a chosen backup location |
| `Clear_Script_Settings.py` | Delete all persistent saved settings for pycatia_scripts, resetting every script to factory defaults |
| `Clear_CATIA_Temp_Files.py` | Delete accumulated files from CATTemp and CATReport folders for selected CATIA V5 versions |
| `Configure_CATIA_Version_Settings.py` | Configure per-version settings paths and window titles for all installed CATIA V5 versions |
| `Kill_CATIA_Processes.py` | Force-close all running CATIA processes to clear stale COM registrations |
| `Open_CATIA_Settings_Folder.py` | Open the CATSettings folder for a selected CATIA V5 version in Windows Explorer |
| `Reset_CATIA_Settings.py` | Delete the CATSettings folder for selected CATIA V5 versions to force a clean defaults reset |
| `Restore_CATIA_Settings.py` | Restore a CATSettings folder from a zip backup created by Backup_CATIA_Settings.py |
| `Set_CATIA_Environment_Variable.py` | Add or update any key=value entry in CATIA V5 environment files for selected versions |
| `Show_CATIA_File_Info.py` | Display file name, creation/modified dates, owner and full CATIA V5 version (release, service pack, hotfix) for selected files |
| `Toggle_CATIA_No_Start_Document.py` | Add or remove CATNoStartDocument=yes in CATIA V5 environment files to control blank document on startup |

### Process Document Scripts

| Script | Description |
|--------|-------------|
| `Check_Operation_Parameters_Against_Limits.py` | Check all operation parameters against predefined min/max limits and flag violations |
| `Export_NC_Program_Names_To_CSV.py` | Export all manufacturing program names and descriptions to CSV |
| `Export_Process_Table_Parameters.py` | Export machining program parameters to Excel (includes operation type, tool, stepover, tolerances, depths, offsets) |
| `Export_ResourceList.py` | Export names of all resources in a process document to CSV |
| `Export_Tool_List_From_Process.py` | Export all cutting tools from a process document to Excel |
| `Manage_Program_Names_And_Comments.py` | Review the machining tree and set program and operation names and comments from template lists; metal, master and spotting per part operation, program names built and renumbered per part operation, comments composed with the machined offset, PP instructions set on PPInstruction activities, several rows editable together as a group, and stepover, depth of cut and part offset checked against editable limits with values that are off shown on red |
| `Manage_Tooling_Catalog.py` | Spreadsheet-style editor for NC tooling catalogs; edit tools in a grid and build the .catalog |
| `Rename_Operations_From_Tool_Name.py` | Automatically rename each operation to match the assigned tool name |

### Product Document Scripts

| Script | Description |
|--------|-------------|
| `Batch_Instance_Name_Equal_Part_Number.py` | Set every instance name in the active product tree to match its part number |
| `Batch_Rename_Instances.py` | Batch rename all first-level instances in the active product with a configurable prefix, number, and suffix |
| `BOM_Export_To_CSV.py` | Export a bill of materials from the active product to a CSV file |
| `BOM_Export_With_Materials.py` | Export a bill of materials enriched with material name and mass from the active product to CSV |
| `Check_Missing_Files.py` | Check all component file references in the assembly for missing or broken links |
| `Clash_Detection_Export.py` | Run interference/clash detection on the active assembly and export results to CSV |
| `Export_Assembly_As_STEP.py` | Export the active product assembly as a single STEP file |
| `Export_Component_Positions_To_CSV.py` | Export the position matrix and translation of every component in the active assembly to CSV |
| `Save_Child_Parts_To_STEP.py` | Save all parts in a product to separate STEP files |
| `Save_Child_Parts_To_STL.py` | Save all parts in a product to separate STL files |

---

## 🚀 Running Scripts

Scripts run standalone — no launcher required.

**From the terminal:**
```
python path\to\script.py
```

**By double-clicking in File Explorer:**

Scripts can be run directly by double-clicking the .py file in File Explorer, provided Python is associated with .py files (it is by default if you checked "Add Python to PATH" during installation). CATIA must already be running before you double-click.

**Using CatiaMenuWin32 (optional):**

[CatiaMenuWin32](https://github.com/KaiUR/CatiaMenuWin32) is a native Windows launcher that syncs directly from this repository and presents each script as a clickable button. No manual path setup required.

1. Download [CatiaMenuWin32](https://github.com/KaiUR/CatiaMenuWin32/releases/latest)
2. Launch the app — scripts sync automatically
3. Click any button to run the script

---

## 🔄 Updating Dependencies

Run the included update script to upgrade all packages to their latest versions:
```
setup\update.bat
```

Or run pip directly:
```
pip install -r setup\requirements.txt --upgrade
```

The `--upgrade` flag tells pip to check for newer versions of each package and install them, even if a version is already installed.

---

## ✍️ Script Header Format

Every script includes a structured metadata header that CatiaMenuWin32 reads to display script information in its tooltip:

```python
'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Script_Name.py
    Version:        1.0
    Code:           Python3.10.4, Pycatia 0.10.0
    Release:        V5R32
    Purpose:        One line summary shown on the script button.
    Author:         Your Name
    Date:           DD.MM.YY
    Description:    Full description of what the script does.
                    Continuation lines must be indented.
    dependencies = [
                    "pycatia",
                    ]
    requirements:   Python >= 3.10
                    pycatia
                    Catia V5 running with an open document.
    -----------------------------------------------------------------------------------------------------------------------
'''
```

---

## 🤝 Contributing

Contributions are welcome! Starting points and guidance:

- **[Script Templates](setup/templates/)** — copy a ready-to-use template from `setup/templates/` and follow the `EDIT:` and `# TODO:` markers
- **[Writing Scripts](https://github.com/KaiUR/Pycatia_Scripts/wiki/Writing-Scripts)** — folder structure, header format, naming conventions, and the persistent data pattern
- **[Script Templates (wiki)](https://github.com/KaiUR/Pycatia_Scripts/wiki/Script-Templates)** — how to choose the right template and step-by-step setup guide
- **[Common Functions](https://github.com/KaiUR/Pycatia_Scripts/wiki/Common-Functions)** — reusable helpers available in `setup/templates/common_functions.py`
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — pull request process and code style

---

## 📄 License

MIT License — Copyright © 2025 Kai-Uwe Rathjen

---

## 🔗 Links

- [CatiaMenuWin32](https://github.com/KaiUR/CatiaMenuWin32) — the launcher app for these scripts
- [Wiki](https://github.com/KaiUR/Pycatia_Scripts/wiki) — full documentation including script guides and templates
- [PyCATIA](https://github.com/evereux/pycatia) — the Python CATIA V5 automation library
- [PyCATIA Documentation](https://pycatia.readthedocs.io/)

---

**Author:** [Kai-Uwe Rathjen](https://github.com/KaiUR)
