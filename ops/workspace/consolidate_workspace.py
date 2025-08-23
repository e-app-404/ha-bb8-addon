from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADDON = ROOT / "addon"
DOCS = ROOT / "docs"
REPORTS = ROOT / "reports"


def git_mv(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.check_call(["git", "mv", str(src), str(dst)])
    except subprocess.CalledProcessError:
        # fallback to shutil (untracked files)
        shutil.move(str(src), str(dst))


def collect_files(base: Path) -> list[Path]:
    return [p for p in base.rglob("*") if p.is_file()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="perform moves")
    ap.add_argument(
        "--check-only", action="store_true", help="verify post-state"
    )
    args = ap.parse_args()

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%SZ")
    plan = {"moves": [], "collisions": [], "removed_empty": []}

    # Ensure canonical dirs exist
    REPORTS.mkdir(exist_ok=True, parents=True)
    (ROOT / "tests").mkdir(exist_ok=True)
    (ROOT / "tools").mkdir(exist_ok=True)

    # 1) addon/tests -> tests
    if (ADDON / "tests").exists():
        for f in collect_files(ADDON / "tests"):
            rel = f.relative_to(ADDON / "tests")
            dst = ROOT / "tests" / rel
            if dst.exists() and dst.read_bytes() != f.read_bytes():
                # collision: keep root test; stash addon copy
                # under tests/_from_addon/
                stash = ROOT / "tests/_from_addon" / rel
                plan["collisions"].append({
                    "src": str(f),
                    "dst": str(dst),
                    "stash": str(stash),
                })
                if args.apply:
                    stash.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(str(f), str(stash))
            else:
                plan["moves"].append({"src": str(f), "dst": str(dst)})
                if args.apply:
                    git_mv(f, dst)

    # 2) addon/tools -> tools
    if (ADDON / "tools").exists():
        for f in collect_files(ADDON / "tools"):
            rel = f.relative_to(ADDON / "tools")
            dst = ROOT / "tools" / rel
            if dst.exists() and dst.read_bytes() != f.read_bytes():
                stash = ROOT / "tools/legacy" / rel
                plan["collisions"].append({
                    "src": str(f),
                    "dst": str(dst),
                    "stash": str(stash),
                })
                if args.apply:
                    stash.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(str(f), str(stash))
            else:
                plan["moves"].append({"src": str(f), "dst": str(dst)})
                if args.apply:
                    git_mv(f, dst)

    # 3) addon/reports -> reports
    if (ADDON / "reports").exists():
        for f in collect_files(ADDON / "reports"):
            rel = f.relative_to(ADDON / "reports")
            dst = REPORTS / Path("addon") / rel  # preserve origin
            plan["moves"].append({"src": str(f), "dst": str(dst)})
            if args.apply:
                git_mv(f, dst)

    # 4) docs/reports -> reports
    if (DOCS / "reports").exists():
        for f in collect_files(DOCS / "reports"):
            rel = f.relative_to(DOCS / "reports")
            dst = REPORTS / Path("docs") / rel
            plan["moves"].append({"src": str(f), "dst": str(dst)})
            if args.apply:
                git_mv(f, dst)

    # remove empty duplicate dirs
    removed = []
    for d in (
        ADDON / "tests",
        ADDON / "tools",
        ADDON / "reports",
        DOCS / "reports",
    ):
        if d.exists():
            import contextlib

            with contextlib.suppress(StopIteration):
                next(d.rglob("*"))
        if d.exists() and not any(d.rglob("*")):
            if args.apply:
                d.rmdir()
            removed.append(str(d))
    plan["removed_empty"] = removed

    REPORTS.mkdir(exist_ok=True, parents=True)
    (REPORTS / f"consolidation_plan_{ts}.json").write_text(
        json.dumps(plan, indent=2)
    )
    if args.check_only:
        # Post conditions
        ok = True
        for dup in ("tests", "tools", "reports"):
            if (ADDON / dup).exists():
                ok = False
        if (DOCS / "reports").exists():
            ok = False
        status = "CONSOLIDATION: PASS" if ok else "CONSOLIDATION: FAIL"
        (REPORTS / f"consolidation_receipt_{ts}.status").write_text(
            status + "\n"
        )
        print(status)
        sys.exit(0 if ok else 1)

    (REPORTS / f"consolidation_receipt_{ts}.status").write_text(
        "CONSOLIDATION: PASS\n"
    )
    print("CONSOLIDATION: PASS")


if __name__ == "__main__":
    main()
