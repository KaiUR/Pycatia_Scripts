# Pycatia Scripts

A collection of [PyCATIA](https://github.com/evereux/pycatia) scripts for automating CATIA V5, designed to be used with [CatiaMenuWin32](https://github.com/KaiUR/CatiaMenuWin32) — a native Windows launcher that syncs and runs these scripts directly from this repository.

## 📋 Requirements

**Python:** 3.9+

**Packages:**
```
pip install pycatia wxPython xlsxwriter
```

Or use the **↓ Deps** button in CatiaMenuWin32 to install automatically.

**CATIA V5** must be running before executing scripts that interact with it.

---

## 📂 Scripts

### Any Document Scripts

| Script | Description |
|--------|-------------|
| `Hide_Planes_And_Axis_Systems.py` | Hides all planes and axis systems in a Part or Product document |
| `Rename_Hybrid_Shapes.py` | Rename hybrid shapes interactively via message box |
| `Replace_Name_Hybrid_Shapes.py` | Search and replace any hybrid shape name |

### Part Document Scripts

| Script | Description |
|--------|-------------|
| `Create_ISM_OSM_STEP_Files.py` | Select two faces/surfaces, extract in tangency and export as ISM and OSM STEP files |
| `Export_Points_Select_Axis_and_Geo_Set_To_CSV.py` | Export points from a geometric set relative to a selected axis system to CSV |
| `Export_Points_Select_Axis_and_Geo_Set_To_XYZ.py` | Export points from a geometric set relative to a selected axis system to XYZ (PCDimms format) |
| `Export_Points_Select_Geo_Set_To_CSV.py` | Export points from a geometric set relative to absolute axis to CSV |
| `Export_Points_Select_Geo_Set_To_XYZ.py` | Export points from a geometric set relative to absolute axis to XYZ (PCDimms format) |
| `IGES_Export_Curve_AXIS.py` | Export curve to IGES after moving from a reference axis system to absolute |
| `Insert_Points_Catia.py` | Insert points into active part from tab-separated or CSV file |
| `Insert_Points_Catia_With_Names.py` | Insert named points into active part from tab-separated or CSV file |
| `Involute_Gear_Generator_Mathamatical.py` | Generate an involute gear profile from user-defined parameters |
| `Join_Explicit_No_Connect.py` | Join curves or surfaces without connex check, as datum |
| `Join_Explicit_No_Connect_Curve.py` | Join curves without connex check, as datum |
| `Join_Explicit_No_Connect_Surface.py` | Join surfaces without connex check, as datum |
| `Measure_Curve_With_3_PTS_AS_CIRCLE.py` | Measure curve radius using a 3-point circle |
| `Measure_Curve_With_3_PTS_AS_CIRCLE_Keep_Con.py` | Measure curve radius using a 3-point circle without removing construction elements |
| `Measure_Radius_Surface.py` | Measure surface radius using intersection and 3-point circle without removing construction |
| `Axis_To_Axis_Keep_Name.py` | Axis-to-axis transformation keeping the original hybrid shape name |
| `Translate_Direction_Distance_Keep_Name.py` | Translate hybrid shapes keeping their original names |

### Process Document Scripts

| Script | Description |
|--------|-------------|
| `Export_Process_Table_Parameters.py` | Export machining program parameters to Excel |
| `Export_ResourceList.py` | Export names of all resources in a process document to CSV |

### Product Document Scripts

| Script | Description |
|--------|-------------|
| `Save_Child_Parts_To_STEP.py` | Save all parts in a product to separate STEP files |

---

## 🚀 Usage with CatiaMenuWin32

[CatiaMenuWin32](https://github.com/KaiUR/CatiaMenuWin32) is a native Windows launcher that syncs directly from this repository and presents each script as a clickable button. No manual path setup required.

1. Download [CatiaMenuWin32](https://github.com/KaiUR/CatiaMenuWin32/releases/latest)
2. Launch the app — scripts sync automatically
3. Click any button to run the script

---

## ✍️ Script Header Format

Every script includes a structured metadata header that CatiaMenuWin32 reads to display script information in its tooltip:

```python
'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Script_Name.py
    Version:        1.0
    Code:           Python3.10.4, Pycatia 0.8.3
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

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on adding new scripts.

---

## 📄 License

MIT License — Copyright © 2025 Kai-Uwe Rathjen

---

## 🔗 Links

- [CatiaMenuWin32](https://github.com/KaiUR/CatiaMenuWin32) — the launcher app for these scripts
- [PyCATIA](https://github.com/evereux/pycatia) — the Python CATIA V5 automation library
- [PyCATIA Documentation](https://pycatia.readthedocs.io/)

---

**Author:** [Kai-Uwe Rathjen](https://github.com/KaiUR)
