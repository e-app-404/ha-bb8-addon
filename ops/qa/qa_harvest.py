# File: ops/qa/qa_harvest.py
import datetime
import json
import os
import pathlib
import re

# Determine workspace root dynamically
SCRIPT_DIR = pathlib.Path(__file__).parent
ROOT = SCRIPT_DIR.parent.parent  # ops/qa -> ops -> workspace_root
REPORTS = ROOT / "reports"


def _read(p: pathlib.Path):
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None


_TS_DIR_RX = re.compile(r"^qa_(\d{8})_(\d{6})$")


def find_latest_qa_dir():

    # 1) Prefer explicit QA_LOGDIR if provided and valid
    env_dir = os.getenv("QA_LOGDIR")
    if env_dir:
        p = pathlib.Path(env_dir)
        if p.exists() and p.is_dir():
            return p
    # 2) Otherwise, choose the newest qa_* directory (ignore files)
    candidates = [p for p in REPORTS.glob("qa_*") if p.is_dir()]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def parse_black(txt):
    if txt is None:
        return {"present": False, "pass": False, "detail": "missing"}
    ok = "reformatted 0 files" in txt or (
        "All done!" in txt
        and "1 file would be reformatted" not in txt
        and "would reformat" not in txt
    )
    return {"present": True, "pass": ok, "detail": "ok" if ok else txt.strip()[-400:]}


def parse_ruff(txt):
    if txt is None:
        return {"present": False, "pass": False, "detail": "missing"}
    fail = re.findall(r"\b([EFW]\d{3})\b", txt)
    ok = len(fail) == 0 and "error" not in txt.lower()
    return {
        "present": True,
        "pass": ok,
        "detail": {"counts_by_code": {k: fail.count(k) for k in set(fail)}},
    }


def parse_mypy(txt):
    if txt is None:
        return {"present": False, "pass": False, "errors": []}
    ok = "Success: no issues found" in txt
    errs = []
    if not ok:
        for line in txt.splitlines():
            if re.search(r": error:", line):
                errs.append(line.strip())
                if len(errs) >= 10:
                    break
    return {"present": True, "pass": ok, "errors": errs}


def parse_pytest(txt):
    if txt is None:
        return {"present": False, "pass": False, "summary": {}}
    summary = {
        "total": None,
        "passed": 0,
        "failed": 0,
        "errors": 0,
        "warnings": 0,
        "deselected": 0,
        "xfail": 0,
        "xpass": 0,
    }
    # Detect special outcome: no tests collected
    no_tests = ("collected 0 items" in txt) or ("no tests ran" in txt.lower())
    # Try multiple patterns for summary line
    summary_patterns = [
        r"=+ (\d+) failed, (\d+) passed.*?in .*s",
        r"=+ (\d+) passed, (\d+) warnings.*?in .*s",
        r"=+ (\d+) passed.*?in .*s",
        r"=+ (\d+) failed, (\d+) errors.*?in .*s",
        r"=+ (\d+) errors, (\d+) failed.*?in .*s",
    ]
    for pat in summary_patterns:
        m = re.search(pat, txt)
        if m:
            nums = [int(x) for x in m.groups() if x is not None]
            # Assign based on pattern
            if "failed" in pat and "passed" in pat and len(nums) == 2:
                summary["failed"], summary["passed"] = nums
            elif "passed" in pat and "warnings" in pat and len(nums) == 2:
                summary["passed"], summary["warnings"] = nums
            elif "passed" in pat and len(nums) == 1:
                summary["passed"] = nums[0]
            elif "failed" in pat and "errors" in pat and len(nums) == 2:
                summary["failed"], summary["errors"] = nums
            elif "errors" in pat and "failed" in pat and len(nums) == 2:
                summary["errors"], summary["failed"] = nums
            break
    # Try robust patterns for other keys
    for k in [
        "failed",
        "passed",
        "warnings",
        "errors",
        "deselected",
        "xfailed",
        "xpassed",
    ]:
        mm = re.search(rf"(\d+)\s+{k}", txt)
        if mm:
            key = {"xfailed": "xfail", "xpassed": "xpass"}.get(k, k)
            summary[key] = int(mm.group(1))
    # collect failing test names
    failing = re.findall(r"^_{5,}\s*(.+?)\s_{5,}$", txt, flags=re.M)
    # coverage if present
    cov = None
    mc = re.search(r"TOTAL\s+\d+\s+\d+\s+(\d+)%", txt)
    if mc:
        cov = int(mc.group(1))
    result = {
        "present": True,
        "pass": (summary["failed"] == 0 and summary["errors"] == 0 and not no_tests),
        "summary": summary,
        "failing": failing,
        "coverage_total_pct": cov,
    }
    if no_tests:
        result["reason"] = "no tests collected"
    return result


def parse_ini(path):
    txt = _read(path)
    out: dict[str, object] = {"present": txt is not None}
    if not txt:
        return out
    out["raw"] = txt
    return out


def main():
    latest = find_latest_qa_dir()
    result = {
        "latest_dir": str(latest) if latest else None,
        "missing_dir": latest is None,
    }
    # Context files
    ctx = {
        "mypy.ini": parse_ini(ROOT / "mypy.ini"),
        ".env": parse_ini(ROOT / ".env"),
        "pytest.ini": parse_ini(ROOT / "pytest.ini"),
    }
    result["context"] = ctx
    # Logs
    logs = {}
    names = ["black.log", "ruff.log", "mypy.log", "pytest.log"]
    for n in names:
        p = (latest / n) if (latest and latest.is_dir()) else None
        txt = _read(p) if p and p.exists() and p.is_file() else None
        if n == "black.log":
            logs[n] = parse_black(txt)
        elif n == "ruff.log":
            logs[n] = parse_ruff(txt)
        elif n == "mypy.log":
            logs[n] = parse_mypy(txt)
        elif n == "pytest.log":
            logs[n] = parse_pytest(txt)
    result["logs"] = logs
    # Acceptance
    result["acceptance"] = {
        "lint_black_pass": logs["black.log"]["present"] and logs["black.log"]["pass"],
        "lint_ruff_pass": logs["ruff.log"]["present"] and logs["ruff.log"]["pass"],
        "types_mypy_pass": logs["mypy.log"]["present"] and logs["mypy.log"]["pass"],
        "tests_pass": logs["pytest.log"]["present"] and logs["pytest.log"]["pass"],
        "coverage_bb8_core_pct": logs["pytest.log"].get("coverage_total_pct"),
        "missing_logs": [n for n in names if not logs.get(n, {}).get("present")],
    }
    # Write templated report copy
    ts = (
        latest.name.replace("qa_", "")
        if (latest and latest.is_dir())
        else datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    )
    template_path = ROOT / "reports" / "QA_REPORT.md"
    out_dir = latest if (latest and latest.is_dir()) else REPORTS
    out_path = out_dir / f"QA-STP4-STABILIZE-{ts}.md"
    template = _read(template_path) or "# QA Report (Template Missing)\n"
    # Minimal inject block at top
    header = f"<!-- auto:qa_harvest {ts} -->\n\n"
    header += "## Harvest Summary\n\n"
    header += f"- Latest dir: `{result['latest_dir']}`\n"
    header += (
        f"- Missing logs: {', '.join(result['acceptance']['missing_logs']) or 'none'}\n"
    )
    header += f"- Black PASS: {result['acceptance']['lint_black_pass']}\n"
    header += f"- Ruff PASS: {result['acceptance']['lint_ruff_pass']}\n"
    header += f"- Mypy PASS: {result['acceptance']['types_mypy_pass']}\n"
    header += f"- Tests PASS: {result['acceptance']['tests_pass']}\n"
    header += (
        f"- Coverage(total): "
        f"{result['logs']['pytest.log'].get('coverage_total_pct')}\n\n"
    )
    if not out_dir.exists():
        out_dir.mkdir(parents=True, exist_ok=True)
    out_path.write_text(header + template, encoding="utf-8")
    # Print deliverables
    # summary_md variable removed as it was unused
    print("\n```json\nqa_harvest_result =")
    print(json.dumps(result, indent=2))
    print("```")
    # Next actions
    na = []
    if not result["acceptance"]["lint_black_pass"]:
        na.append("Run: black . && git add -A && git commit -m 'style: black'")
    if not result["acceptance"]["lint_ruff_pass"]:
        na.append("Run: ruff check . && ruff --fix . (review diffs before commit)")
    if not result["acceptance"]["types_mypy_pass"]:
        na.append(
            "Investigate mypy.log top 10; add types or "
            "`# type: ignore[code]` with justification"
        )
    if not result["acceptance"]["tests_pass"]:
        failing = logs["pytest.log"].get("failing", [])
        if failing:
            na.append(
                f'Run focused: pytest -q -k "{" or ".join(failing[:3])}" --maxfail=1'
            )
        else:
            na.append("Investigate pytest.log for errors; no failing test names found.")
    print("### Next Actions\n")
    print("\n".join(f"- {x}" for x in (na or ["No actions; all green."])))


if __name__ == "__main__":
    main()
