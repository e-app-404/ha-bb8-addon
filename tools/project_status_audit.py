from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
TS = time.strftime("%Y%m%d_%H%M%SZ", time.gmtime())


def run(
    cmd: list[str], cwd: Path | None = None, timeout: int = 90
) -> tuple[int, str, str]:
    try:
        p = subprocess.run(
            cmd, cwd=str(cwd or ROOT), capture_output=True, text=True, timeout=timeout
        )
        return p.returncode, p.stdout.strip(), p.stderr.strip()
    except Exception as e:
        return 127, "", f"{type(e).__name__}: {e}"


def file_exists(rel: str) -> bool:
    return (ROOT / rel).exists()


def read_text_safe(p: Path) -> str:
    try:
        return p.read_text().strip()
    except Exception:
        return ""


def bool_to_pass(b: bool) -> str:
    return "PASS" if b else "FAIL"


def main():
    from typing import Any

    REPORTS.mkdir(parents=True, exist_ok=True)
    status: dict[str, Any] = {"ts": TS, "root": str(ROOT)}
    notes = []

    # --- Git info ---
    git_ok = shutil.which("git") is not None
    status["git_present"] = git_ok
    if git_ok and (ROOT / ".git").exists():
        rc, branch, _ = run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
        rc2, remote, _ = run(["git", "remote", "-v"])
        rc3, statp, _ = run(["git", "status", "--porcelain"])
        rc4, last_tag, _ = run(["git", "describe", "--tags", "--abbrev=0"])
        rc5, log, _ = run(["git", "log", "--oneline", "-n", "5"])
        status["git"] = {
            "branch": branch if rc == 0 else None,
            "remote": remote if rc2 == 0 else "",
            "dirty": bool(statp),
            "last_tag": last_tag if rc4 == 0 else None,
            "recent_commits": log.splitlines() if rc5 == 0 else [],
        }
    else:
        status["git"] = {
            "branch": None,
            "remote": "",
            "dirty": None,
            "last_tag": None,
            "recent_commits": [],
        }
        notes.append("git repo not initialized or git missing")

    # --- Version & key files ---
    addon_version = read_text_safe(ROOT / "addon" / "VERSION")
    status["addon_version"] = addon_version or None
    status["files"] = {
        "pytest.ini": file_exists("pytest.ini"),
        "ruff.toml": file_exists("ruff.toml"),
        "mypy.ini": file_exists("mypy.ini"),
        "bb8_core/__init__.py": file_exists("bb8_core/__init__.py"),
        "tools/verify_discovery.py": file_exists("tools/verify_discovery.py"),
    }

    # --- Duplicate dirs check (post-consolidation) ---
    dups = {
        "addon/tests": file_exists("addon/tests"),
        "addon/tools": file_exists("addon/tools"),
        "addon/reports": file_exists("addon/reports"),
        "docs/reports": file_exists("docs/reports"),
    }
    status["duplicate_dirs_present"] = {k: v for k, v in dups.items() if v}

    # --- Add-on tree audit ---
    audit_rc, audit_out, audit_err = run(
        [
            sys.executable,
            "tools/audit_addon_tree.py",
            "--strict",
            "--out",
            str(REPORTS / f"addon_audit_{TS}.json"),
        ]
    )
    status["addon_audit"] = {"rc": audit_rc, "stderr": audit_err}

    # --- Consolidation check ---
    cons_rc, cons_out, cons_err = run(
        [sys.executable, "tools/consolidate_workspace.py", "--check-only"]
    )
    status["consolidation"] = {"rc": cons_rc, "stderr": cons_err, "out": cons_out}

    # --- Import order / circular warnings tests (narrow) ---
    py = shutil.which("pytest")
    if py:
        imp_rc, imp_out, imp_err = run(
            [
                "pytest",
                "-q",
                "tests/test_import_order_warning.py",
                "tests/test_imports_no_cycles.py",
                "--disable-warnings",
                "-q",
            ]
        )
    else:
        imp_rc, imp_out, imp_err = (127, "", "pytest not installed")
    status["imports_tests"] = {"rc": imp_rc, "out": imp_out, "err": imp_err}

    # --- Lint/type smoke (lightweight) ---
    ruff_ok = shutil.which("ruff") is not None
    mypy_ok = shutil.which("mypy") is not None
    if ruff_ok:
        rf_rc, rf_out, _ = run(["ruff", "check", "bb8_core", "tests"])
    else:
        rf_rc, rf_out = (0, "(ruff not available)")
    if mypy_ok:
        mp_rc, mp_out, _ = run(["mypy", "bb8_core"])
    else:
        mp_rc, mp_out = (0, "(mypy not available)")
    status["lint"] = {
        "ruff_rc": rf_rc,
        "ruff_summary": rf_out.splitlines()[-3:] if rf_out else [],
        "mypy_rc": mp_rc,
        "mypy_summary": mp_out.splitlines()[-3:] if mp_out else [],
    }

    # --- Stub check: ensure bridge_controller.get_client stub is gone ---
    bc_path = ROOT / "bb8_core" / "bridge_controller.py"
    stub_present = (
        'NotImplementedError("get_client() is not yet implemented.")'
        in read_text_safe(bc_path)
    )
    status["bridge_client_stub_present"] = stub_present
    if stub_present:
        notes.append("bridge_controller.get_client stub still present")

    # --- __init__ eager import check ---
    init_txt = read_text_safe(ROOT / "bb8_core" / "__init__.py")
    eager = ("import bb8_core." in init_txt) or (
        "from . import " in init_txt and "TYPE_CHECKING" not in init_txt
    )
    status["eager_imports_in_init"] = eager

    # --- Discovery verifier (conditional on broker env) ---
    broker_env = {
        k: os.getenv(k)
        for k in ["MQTT_HOST", "MQTT_PORT", "MQTT_USERNAME", "MQTT_PASSWORD"]
    }
    if file_exists("tools/verify_discovery.py") and broker_env.get("MQTT_HOST"):
        vd_rc, vd_out, vd_err = run([sys.executable, "tools/verify_discovery.py"])
        status["verify_discovery"] = {
            "rc": vd_rc,
            "out_tail": vd_out.splitlines()[-6:],
            "err_tail": vd_err.splitlines()[-6:],
        }
    else:
        status["verify_discovery"] = {
            "rc": 0,
            "skipped": True,
            "reason": "no broker env or script missing",
        }

    # --- Overall verdict rules ---
    essentials = []
    essentials.append(audit_rc == 0)
    essentials.append(cons_rc == 0 and "PASS" in cons_out)
    essentials.append(not stub_present)
    essentials.append(not eager)
    # import tests allowed to be absent; if present, require success
    if py:
        essentials.append(imp_rc == 0)

    overall = "PASS" if all(essentials) else ("WARN" if any(essentials) else "FAIL")
    status["overall_verdict"] = overall
    status["notes"] = notes

    # --- Write JSON & MD & receipt ---
    json_path = REPORTS / f"project_status_audit_{TS}.json"
    md_path = REPORTS / f"project_status_audit_{TS}.md"
    rec_path = REPORTS / f"project_status_receipt_{TS}.status"

    json_path.write_text(json.dumps(status, indent=2))

    def b(v):
        return "✅" if v else "❌"

    md = []
    md.append(f"# Project Status Audit — {TS}")
    md.append(f"**Verdict:** {overall}")
    md.append("\n## Version")
    md.append(f"- addon/VERSION: `{addon_version or 'unknown'}`")
    md.append("\n## Git")
    g = status["git"]
    remote_val = g.get("remote")
    remote_str = remote_val if isinstance(remote_val, str) else ""
    remote_first_line = remote_str.splitlines()[0] if remote_str else ""
    md.append(
        f"- branch: `{g.get('branch')}`  "
        f"remote: `{remote_first_line}`  "
        f"dirty: `{g.get('dirty')}`  "
        f"last_tag: `{g.get('last_tag')}`"
    )
    md.append("\n## Files")
    for k, v in status["files"].items():
        md.append(f"- {k}: {b(v)}")
    md.append("\n## Duplicates (should be none)")
    for k, v in dups.items():
        md.append(f"- {k}: {b(not v)} (present={v})")
    md.append("\n## Add-on audit")
    md.append(f"- tools/audit_addon_tree.py --strict rc={audit_rc}")
    md.append("\n## Consolidation")
    md.append(f"- consolidate_workspace --check-only rc={cons_rc} out=`{cons_out}`")
    md.append("\n## Imports tests")
    md.append(f"- rc={imp_rc}")
    md.append("\n## Lint/Type")
    md.append(f"- ruff rc={rf_rc}  mypy rc={mp_rc}")
    md.append("\n## Bridge client stub removed")
    md.append(f"- stub_present={stub_present}")
    md.append("\n## __init__ eager imports")
    md.append(f"- eager_in_init={eager}")
    md.append("\n## Verify discovery (conditional)")
    vd = status["verify_discovery"]
    md.append(f"- rc={vd.get('rc')} skipped={vd.get('skipped', False)}")
    out_tail = vd.get("out_tail")
    if isinstance(out_tail, list) and all(isinstance(line, str) for line in out_tail):
        md.extend(["```\n" + "\n".join(out_tail) + "\n```"])
    if notes:
        md.append("\n## Notes\n- " + "\n- ".join(notes))

    md_path.write_text("\n".join(md))
    rec_path.write_text(
        f"PROJECT_STATUS: {overall}\nJSON: {json_path}\nMD: {md_path}\n"
    )

    print(f"PROJECT_STATUS: {overall}")
    print(f"JSON: {json_path}")
    print(f"MD: {md_path}")


if __name__ == "__main__":
    main()
