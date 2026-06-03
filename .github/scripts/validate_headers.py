"""
Validates that every .py script in the repository has the required
CatiaMenuWin32-compatible header fields, and that scripts with a
version above 1.0 have a properly formatted Change log.

Required fields (matched case-insensitively):
    Script name:  Version:  Purpose:  Author:  Date:

Change log rule:
    When Version > 1.0 the Change: block must contain at least one
    entry in the format:  DD.MM.YY  V.V:  message
    Example:  03.06.26 1.3: Fix F841: rename app to _app.

    When Version == 1.0 the Change: block may be empty.

Exits with code 1 if any file fails a check, so the CI action acts
as a hard block on pull requests.

Excluded paths:
    setup/   — templates and helper scripts, not user-facing scripts
"""

import os
import re
import sys

REQUIRED_FIELDS = ["Script name:", "Version:", "Purpose:", "Author:", "Date:"]

EXCLUDE_DIRS = {"setup"}

# Matches a versioned change entry: DD.MM.YY  V.V:  anything
_CHANGE_ENTRY_RE = re.compile(r"\d{2}\.\d{2}\.\d{2}\s+\d+\.\d+\s*:")

# Extracts the version number from the Version: field line
_VERSION_RE = re.compile(r"Version:\s*([\d]+)\.([\d]+)", re.IGNORECASE)


def check_file(path: str) -> list[str]:
    """Return a list of error strings for the given script file."""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            # Read the first 80 lines — headers are always near the top
            lines = [f.readline() for _ in range(80)]
            content = "".join(lines)
    except OSError as exc:
        return [f"(could not read file: {exc})"]

    errors: list[str] = []

    # --- Required fields ---
    for field in REQUIRED_FIELDS:
        if field.lower() not in content.lower():
            errors.append(f"missing field: {field}")

    # --- Change log format (only when version > 1.0) ---
    version_match = _VERSION_RE.search(content)
    if version_match:
        major, minor = int(version_match.group(1)), int(version_match.group(2))
        if (major, minor) > (1, 0):
            # Find the Change: block — everything between "Change:" and the
            # next "---" separator line
            change_section = ""
            in_change = False
            for line in lines:
                if re.search(r"Change:", line, re.IGNORECASE):
                    in_change = True
                    change_section += line
                    continue
                if in_change:
                    if re.match(r"\s*-{10,}", line):
                        break
                    change_section += line

            if not _CHANGE_ENTRY_RE.search(change_section):
                errors.append(
                    f"Version {major}.{minor} > 1.0 but Change: block has no "
                    f"versioned entry — expected format: DD.MM.YY V.V: message"
                )

    return errors


def main() -> int:
    failures: list[tuple[str, list[str]]] = []

    for root, dirs, files in os.walk("."):
        dirs[:] = [
            d for d in dirs
            if d not in EXCLUDE_DIRS and not d.startswith(".")
        ]

        for filename in files:
            if not filename.endswith(".py"):
                continue
            path = os.path.join(root, filename)
            errs = check_file(path)
            if errs:
                failures.append((path, errs))

    if failures:
        print(f"\nFAIL  Header validation failed -- {len(failures)} file(s):\n")
        for path, errs in sorted(failures):
            print(f"  {path}")
            for err in errs:
                print(f"      {err}")
        print(
            "\nAll scripts must include a header with the required fields.\n"
            "Scripts with Version > 1.0 must have a Change: entry in the format:\n"
            "    DD.MM.YY V.V: description\n"
            "See the Writing-Scripts wiki page for the required format.\n"
        )
        return 1

    count = sum(1 for _ in _iter_scripts())
    print(f"OK  All script headers valid ({count} files checked).")
    return 0


def _iter_scripts():
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS and not d.startswith(".")]
        for f in files:
            if f.endswith(".py"):
                yield f


if __name__ == "__main__":
    sys.exit(main())
