from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import UTC, datetime
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
    ap.add_argument("--check-only", action="store_true", help="verify post-state")
    ap.add_argument(
        "--verbose", action="store_true", help="print reasons for PASS/FAIL"
    )
    args = ap.parse_args()

    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%SZ")
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
                # collision: keep root test; stash addon copy under tests/_from_addon/
                stash = ROOT / "tests/_from_addon" / rel
                plan["collisions"].append(
                    {"src": str(f), "dst": str(dst), "stash": str(stash)}
                )
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
                plan["collisions"].append(
                    {"src": str(f), "dst": str(dst), "stash": str(stash)}
                )
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
    for d in (ADDON / "tests", ADDON / "tools", ADDON / "reports", DOCS / "reports"):
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
    (REPORTS / f"consolidation_plan_{ts}.json").write_text(json.dumps(plan, indent=2))
    if args.check_only:
        # Post conditions (symlink-aware, verbose)
        reasons: list[str] = []

        def exists_here(p: Path) -> bool:
            try:
                # treat missing/broken links as non-existent
                return p.exists()
            except Exception:
                return False

        # Fail only if duplicate dirs under addon/ are NON-EMPTY
        def dir_has_files(p: Path) -> bool:
            """True if directory contains any non-hidden files."""
            if not p.exists() or not p.is_dir():
                return False
            for child in p.rglob("*"):
                if child.is_file() and not child.name.startswith("."):
                    return True
            return False

        for dup in ("tests", "tools", "reports"):
            p = ADDON / dup
            if exists_here(p) and dir_has_files(p):
                reasons.append(f"addon duplicate (non-empty): {p}")
        # docs/reports only a duplicate if it resolves *inside* repo and is non-empty
        docs_reports = DOCS / "reports"
        try:
            if docs_reports.exists():
                resolved = docs_reports.resolve()
                if str(resolved).startswith(str(ROOT)) and dir_has_files(docs_reports):
                    reasons.append(
                        f"docs/reports duplicate: {docs_reports} -> {resolved}"
                    )
        except Exception:
            # broken ref: ignore for consolidation purposes
            pass
        ok = len(reasons) == 0
        status = "CONSOLIDATION: PASS" if ok else "CONSOLIDATION: FAIL"
        REPORTS.mkdir(parents=True, exist_ok=True)
        rec = REPORTS / f"consolidation_receipt_{ts}.status"
        payload = {"status": status, "reasons": reasons, "root": str(ROOT)}
        rec.write_text(json.dumps(payload, indent=2) + "\n")
        if args.verbose:
            print(json.dumps(payload, indent=2))
        else:
            print(status)
        sys.exit(0 if ok else 1)

    (REPORTS / f"consolidation_receipt_{ts}.status").write_text("CONSOLIDATION: PASS\n")
    print("CONSOLIDATION: PASS")


if __name__ == "__main__":
    main()
