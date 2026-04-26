# Security Policy

## Supported Versions

This repository contains Python scripts — there are no versioned releases. The `main` branch always contains the latest scripts.

## Reporting a Vulnerability

**Please do not report security vulnerabilities as public GitHub issues.**

If you discover a security issue in one of the scripts (for example, a script that could be exploited to execute unintended code or access unintended files), please report it privately.

**To report a vulnerability:**

1. Go to the [Security Advisories](https://github.com/KaiUR/Pycatia_Scripts/security/advisories) page
2. Click **Report a vulnerability**
3. Describe the issue clearly, including which script is affected and the potential impact

Alternatively, contact the maintainer directly via GitHub: [@KaiUR](https://github.com/KaiUR)

## Scope

Scripts in this repository interact with CATIA V5 via COM automation and read/write local files. Potential security concerns include:

- A script reading from or writing to unintended file paths
- A script exposing sensitive data via exported files
- A script executing unexpected system commands

Scripts that only interact with CATIA V5 geometry and export standard file formats (CSV, XYZ, STEP, IGES) are considered low risk.

## Notes

These scripts are run locally on your own machine. They do not make network connections, transmit data, or interact with any external services. The [CatiaMenuWin32](https://github.com/KaiUR/CatiaMenuWin32) launcher verifies each script's SHA hash before execution to ensure scripts have not been tampered with since download.

---

**Maintainer:** [Kai-Uwe Rathjen](https://github.com/KaiUR)
