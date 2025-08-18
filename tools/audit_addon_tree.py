from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = (
    Path(__file__).resolve().parents[1]
    if (Path(__file__).parent.name == "tools")
    else Path(__file__).resolve().parent
)
ADDON = ROOT / "addon"
REPORTS = ROOT / "reports"

REQUIRED_FILES = {
    "Dockerfile",
    "requirements.txt",
    "requirements.in",  # referenced by Dockerfile
    "run.sh",
    "VERSION",  # optional, allowed
    "config.yaml",  # HA add-on manifest (allowed if present)
}
REQUIRED_DIRS = {
    "bb8_core",
    "services.d",
    "app",  # referenced by Dockerfile for test_ble_adapter.py
}
OPTIONAL_FILES = {
    "apparmor",
    "apparmor.txt",  # allowed if used by config.yaml
}
FORBIDDEN_TOOLING = {
    "pytest.ini",
    "ruff.toml",
    "mypy",
    "mypy.ini",
    "tox.ini",
    ".editorconfig",
}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--strict", action="store_true")
    p.add_argument("--out", default=str(REPORTS / "addon_audit.json"))
    args = p.parse_args()

    if not ADDON.exists():
        print(f"ERROR: addon dir not found at {ADDON}", file=sys.stderr)
        sys.exit(2)
    REPORTS.mkdir(parents=True, exist_ok=True)

    entries = [(e.name, e) for e in sorted(ADDON.iterdir(), key=lambda x: x.name)]
    files = {name for name, e in entries if e.is_file()}
    dirs = {name for name, e in entries if e.is_dir()}

    missing_required = sorted([f for f in REQUIRED_FILES if f not in files])
    missing_required_dirs = sorted([d for d in REQUIRED_DIRS if d not in dirs])

    stray_forbidden = sorted([f for f in files if f in FORBIDDEN_TOOLING])

    allowed_files = REQUIRED_FILES | OPTIONAL_FILES
    generic_strays = sorted(
        [f for f in files if f not in allowed_files and f not in FORBIDDEN_TOOLING]
    )

    # flag duplicate trees under addon/
    duplicate_dirs = sorted(
        [d for d in ("tests", "tools", "reports") if (ADDON / d).exists()]
    )

    must_exist = []
    for probe in [
        "run.sh",
        "services.d/ble_bridge/run",
        "bb8_core",
        "requirements.txt",
    ]:
        must_exist.append((probe, (ADDON / probe).exists()))

    report = {
        "root": str(ROOT),
        "addon": str(ADDON),
        "present_files": sorted(list(files)),
        "present_dirs": sorted(list(dirs)),
        "missing_required_files": missing_required,
        "missing_required_dirs": missing_required_dirs,
        "forbidden_tooling": stray_forbidden,
        "duplicate_dirs": duplicate_dirs,
        "generic_strays": generic_strays,
        "dockerfile_probes": must_exist,
    }

    # decide PASS/FAIL
    fail = False
    reasons = []
    if missing_required:
        fail = True
        reasons.append(f"missing files: {missing_required}")
    if missing_required_dirs:
        fail = True
        reasons.append(f"missing dirs: {missing_required_dirs}")
    if stray_forbidden:
        fail = True
        reasons.append(f"forbidden tooling present: {stray_forbidden}")
    if duplicate_dirs:
        fail = True
        reasons.append(f"duplicate dirs present under addon/: {duplicate_dirs}")

    with open(args.out, "w") as fh:
        json.dump(report, fh, indent=2)

    if args.strict and fail:
        print("ADDON_CLEAN: FAIL", "; ".join(reasons))
        sys.exit(1)
    print("ADDON_CLEAN:", "PASS" if not fail else "SOFT-FAIL")


if __name__ == "__main__":
    main()
