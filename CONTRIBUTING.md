# Contributing to Pycatia Scripts

Thank you for your interest in contributing. This repository is a collection of PyCATIA scripts for CATIA V5 automation, used with [CatiaMenuWin32](https://github.com/KaiUR/CatiaMenuWin32).

## Ways to Contribute

- **Report a bug** — open a [Bug Report](https://github.com/KaiUR/Pycatia_Scripts/issues/new?template=bug_report.md) issue
- **Suggest a script** — open a [Feature Request](https://github.com/KaiUR/Pycatia_Scripts/issues/new) issue
- **Submit a new script** — follow the guidelines below and open a pull request
- **Fix or improve an existing script** — open a pull request with your changes

---

## Adding a New Script

### 1. Choose the right folder

| Folder | Use when |
|--------|----------|
| `Any_Document_Scripts/` | Script works on any open CATIA document |
| `Drawing_Document_Scripts/` | Script requires an open CATDrawing document |
| `Part_Document_Scripts/` | Script requires an open Part document |
| `Process_Document_Scripts/` | Script requires an open Process document |
| `Product_Document_Scripts/` | Script requires an open Product document |
| `Shape_Generation_Scripts/` | Script generates geometry into the active CATPart document |

If your script doesn't fit any existing folder, propose a new one in your pull request.

### 2. Name your script

Use `Snake_Case_Descriptive_Name.py`. The launcher converts underscores to spaces automatically — `Export_Points_To_CSV.py` becomes "Export Points To CSV" in the app.

### 3. Include the required header

Every script **must** include a properly formatted metadata header as the first item in the file. CatiaMenuWin32 reads this to display the script name, purpose, and description in its tooltip:

```python
'''
    -----------------------------------------------------------------------------------------------------------------------
    Script name:    Your_Script_Name.py
    Version:        1.0
    Code:           Python3.10.4, Pycatia 0.8.3
    Release:        V5R32
    Purpose:        One line summary — shown on the script button in CatiaMenuWin32.
    Author:         Your Name
    Date:           DD.MM.YY
    Description:    Full description of what the script does, what inputs it needs,
                    and what outputs it produces. Continuation lines must be indented.
    dependencies = [
                    "pycatia",
                    ]
    requirements:   Python >= 3.10
                    pycatia
                    Catia V5 running with an open part document.
    -----------------------------------------------------------------------------------------------------------------------
'''
```

**Header rules:**
- Must be inside a triple-quoted string at the top of the file
- `Purpose` — keep to one line, shown as subtitle on the script button
- `Description` — full detail, continuation lines must be indented
- `dependencies` — list all pip packages required
- `requirements` — describe the CATIA state needed to run the script

### 4. Update dependencies

If your script requires packages not already in `setup/requirements.txt`, add them.

### 5. Test your script

- Test with CATIA V5 running
- Test with CatiaMenuWin32 if possible — confirm the tooltip shows correctly
- Make sure the script handles errors gracefully (e.g. wrong document type open)

---

## Pull Request Process

1. Fork the repository
2. Create a branch: `git checkout -b feat/my-new-script`
3. Add your script to the correct folder
4. Update `setup/requirements.txt` if needed
5. Commit with a clear message: `feat: add Export_Points_To_CSV script`
6. Push and open a pull request against `main`

---

## Code Style

- Python 3.10+ compatible
- Use PyCATIA for all CATIA interactions — see [PyCATIA documentation](https://pycatia.readthedocs.io/)
- Use `wxPython` for any GUI dialogs (message boxes, file pickers)
- Keep scripts self-contained — one file per script
- Handle common errors (wrong document type, nothing selected, CATIA not running) with clear user messages
- Store all user-configurable settings in `%APPDATA%\pycatia_scripts\<Script_Name>\` using the persistent data pattern — never ask users to edit a script directly (CatiaMenuWin32 verifies script hashes before running)
- All dialog scripts must include the `_bring_to_front` helper and call it via `wx.CallAfter` before `ShowModal()` — CATIA holds the foreground lock and a plain dialog will appear behind it

---

## Linting

CI runs **[ruff](https://docs.astral.sh/ruff/)** on every push and pull request. Your script must pass before it can be merged.

### Rules enforced

| Category | Rules |
|---|---|
| `E` — pycodestyle | Syntax errors, indentation, whitespace, statement structure |
| `F` — pyflakes | Undefined names, unused imports, redefined variables |

### What is ignored

| Rule | Reason |
|---|---|
| `E501` | Line length — scripts use right-aligned inline comments; not enforced |

### Common things that will fail

- **Unused imports** (F401) — only import what your script actually uses
- **Undefined names** (F821) — check all variable references, especially after renaming
- **Unused local variables** (F841) — if you must suppress, prefix with `_` (e.g. `_app = wx.App(None)`)
- **Multiple statements on one line** (E701) — `if x: y` must be split to two lines

### Running ruff locally

```
pip install ruff
ruff check .
```

The `setup/` and `.github/` directories are excluded.

---

**Author:** [Kai-Uwe Rathjen](https://github.com/KaiUR)
