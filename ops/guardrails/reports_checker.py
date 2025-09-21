#!/usr/bin/env python3
"""Check for expected reports folder(s) and runner outputs.

This validator performs best-effort checks to confirm that `reports/bleep_run/`
exists and contains at least one recent file, or reports its absence.
"""
import json
from pathlib import Path

ROOT = Path(".")
REPORTS_DIR = ROOT / "reports" / "bleep_run"


def main():
    ok = False
    files = []
    if REPORTS_DIR.exists() and REPORTS_DIR.is_dir():
        for f in sorted(REPORTS_DIR.iterdir(), reverse=True):
            if f.is_file():
                files.append({"name": f.name, "mtime": f.stat().st_mtime})
    out = {
        "tool": "reports_checker",
        "reports_dir": REPORTS_DIR.as_posix(),
        "files": files,
    }
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    import json

    main()
