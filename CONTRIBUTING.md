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
| `Part_Document_Scripts/` | Script requires an open Part document |
| `Process_Document_Scripts/` | Script requires an open Process document |
| `Product_Document_Scripts/` | Script requires an open Product document |

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

- Python 3.9+ compatible
- Use PyCATIA for all CATIA interactions — see [PyCATIA documentation](https://pycatia.readthedocs.io/)
- Use `wxPython` for any GUI dialogs (message boxes, file pickers)
- Keep scripts self-contained — one file per script
- Handle common errors (wrong document type, nothing selected, CATIA not running) with clear user messages

---

**Author:** [Kai-Uwe Rathjen](https://github.com/KaiUR)
