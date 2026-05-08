# Privacy Policy

**Last updated: 8 May 2026**

Pycatia_Scripts is a free, open-source collection of Python scripts for automating CATIA V5. This policy explains what data these scripts access, store, and transmit.

---

## Data Collected

These scripts do **not** collect, transmit, or store any personal data on behalf of the developer. There is no telemetry, no analytics, and no tracking of any kind.

---

## What the Scripts Do

All scripts run entirely on your local machine. Depending on the script, they may:

- Read geometry, parameters, or document structure from an open CATIA V5 session via COM
- Write output files (CSV, STEP, IGES, XYZ, etc.) to locations you specify
- Modify geometry or document properties within CATIA V5

No data is sent over the network by any script in this repository.

---

## Files Written to Disk

Some scripts export files to your local file system (e.g. CSV exports, STEP/IGES files). The location is determined by the script logic or a dialog you interact with. No files are written anywhere other than your local machine.

---

## Third-Party Libraries

Scripts use the following third-party packages:

| Package | Purpose |
|---------|---------|
| [PyCATIA](https://github.com/evereux/pycatia) | COM interface to CATIA V5 |
| [wxPython](https://wxpython.org/) | GUI dialogs (used by some scripts) |
| [xlsxwriter](https://xlsxwriter.readthedocs.io/) | Excel file export (used by some scripts) |

These packages run locally. Refer to their respective projects for their own privacy information.

---

## Changes

If this policy changes, the updated version will be committed to the repository with a new **Last updated** date.

---

## Contact

For questions or concerns, open an issue at [github.com/KaiUR/Pycatia_Scripts/issues](https://github.com/KaiUR/Pycatia_Scripts/issues) or email [admiralkai@gmail.com](mailto:admiralkai@gmail.com).
