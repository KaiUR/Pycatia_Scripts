"""
Validates that every .py script in the repository has the required
CatiaMenuWin32-compatible header fields.

Required fields (matched case-insensitively):
    Script name:  Version:  Purpose:  Author:  Date:

Exits with code 1 if any file is missing a required field, so the CI
check acts as a hard block on pull requests.

Excluded paths:
    setup/   — templates and helper scripts, not user-facing scripts
"""

import os
import sys

REQUIRED_FIELDS = ["Script name:", "Version:", "Purpose:", "Author:", "Date:"]

EXCLUDE_DIRS = {"setup"}


def check_file(path: str) -> list[str]:
    """Return a list of missing field names for the given script file."""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            # Only read the first 60 lines — headers are always near the top
            content = "\n".join(f.readline() for _ in range(60))
    except OSError as exc:
        return [f"(could not read file: {exc})"]

    return [
        field
        for field in REQUIRED_FIELDS
        if field.lower() not in content.lower()
    ]


def main() -> int:
    failures: list[tuple[str, list[str]]] = []

    for root, dirs, files in os.walk("."):
        # Skip excluded directories
        dirs[:] = [
            d for d in dirs
            if d not in EXCLUDE_DIRS and not d.startswith(".")
        ]

        for filename in files:
            if not filename.endswith(".py"):
                continue
            path = os.path.join(root, filename)
            missing = check_file(path)
            if missing:
                failures.append((path, missing))

    if failures:
        print(f"\n❌  Header validation failed — {len(failures)} file(s) with missing fields:\n")
        for path, missing in sorted(failures):
            print(f"  {path}")
            for field in missing:
                print(f"      missing: {field}")
        print(
            "\nAll scripts must include a header block with the fields above.\n"
            "See the Writing-Scripts wiki page for the required format.\n"
        )
        return 1

    print(f"✅  All script headers valid ({sum(1 for _ in _iter_scripts()) } files checked).")
    return 0


def _iter_scripts():
    """Helper used only by the success message to count files."""
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS and not d.startswith(".")]
        for f in files:
            if f.endswith(".py"):
                yield f


if __name__ == "__main__":
    sys.exit(main())
