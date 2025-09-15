#!/usr/bin/env bash
set -euo pipefail

echo "=== B1) Build move plan ==="
python3 - <<'PY'
import os, json, pathlib, shutil
plan = []

# Root services.d => addon/services.d
root_svc = pathlib.Path("services.d")
if root_svc.exists():
    for svc in root_svc.iterdir():
        if svc.is_dir():
            for p in svc.rglob("*"):
                if p.is_file():
                    dst = pathlib.Path("addon/services.d")/svc.name/p.relative_to(svc)
                    plan.append({"src": str(p), "dst": str(dst), "reason": "root services.d is forbidden; move under addon/services.d"})

# Classify tools
def classify_py(path: pathlib.Path):
    try:
        src = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return "generic"
    if "import addon.bb8_core" in src:
        return "addon-runtime"
    if "import bb8_core" in src:
        return "legacy-import"
    if "__main__" in src:
        return "cli-tool"
    for needle in ("docker","paho","git","ha ","boto3","google"):
        if f"import {needle}" in src or f"from {needle} " in src:
            return "ops-tooling"
    return "generic"

tools_root = pathlib.Path("tools")
if tools_root.exists():
    for p in tools_root.rglob("*"):
        if p.is_file():
            if p.suffix in (".py",".sh",".bash"):
                cat = classify_py(p) if p.suffix == ".py" else "sh-generic"
                if cat in ("addon-runtime","cli-tool"):
                    dst = pathlib.Path("addon/tools")/p.relative_to(tools_root)
                    plan.append({"src": str(p), "dst": str(dst), "reason": f"{cat} → addon/tools"})
                elif cat == "ops-tooling":
                    dst = pathlib.Path("ops/tools")/p.relative_to(tools_root)
                    plan.append({"src": str(p), "dst": str(dst), "reason": f"{cat} → ops/tools"})
            else:
                # Non-code files: leave in place for manual review
                pass

print("TOKEN: MOVE_PLAN")
print(json.dumps(plan, indent=2))
PY

echo
echo "=== B2) Preview plan ==="
# Capture the output of the Python script to a temporary file
python3 - <<'PY' > /tmp/move_plan.json
import os, json, pathlib, shutil
plan = []

# Root services.d => addon/services.d
root_svc = pathlib.Path("services.d")
if root_svc.exists():
    for svc in root_svc.iterdir():
        if svc.is_dir():
            for p in svc.rglob("*"):
                if p.is_file():
                    dst = pathlib.Path("addon/services.d")/svc.name/p.relative_to(svc)
                    plan.append({"src": str(p), "dst": str(dst), "reason": "root services.d is forbidden; move under addon/services.d"})

# Classify tools
def classify_py(path: pathlib.Path):
    try:
        src = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return "generic"
    if "import addon.bb8_core" in src:
        return "addon-runtime"
    if "import bb8_core" in src:
        return "legacy-import"
    if "__main__" in src:
        return "cli-tool"
    for needle in ("docker","paho","git","ha ","boto3","google"):
        if f"import {needle}" in src or f"from {needle} " in src:
            return "ops-tooling"
    return "generic"

tools_root = pathlib.Path("tools")
if tools_root.exists():
    for p in tools_root.rglob("*"):
        if p.is_file():
            if p.suffix in (".py",".sh",".bash"):
                cat = classify_py(p) if p.suffix == ".py" else "sh-generic"
                if cat in ("addon-runtime","cli-tool"):
                    dst = pathlib.Path("addon/tools")/p.relative_to(tools_root)
                    plan.append({"src": str(p), "dst": str(dst), "reason": f"{cat} → addon/tools"})
                elif cat == "ops-tooling":
                    dst = pathlib.Path("ops/tools")/p.relative_to(tools_root)
                    plan.append({"src": str(p), "dst": str(dst), "reason": f"{cat} → ops/tools"})
            else:
                # Non-code files: leave in place for manual review
                pass

print(json.dumps(plan, indent=2))
PY

jq -r '.[] | "\(.src)  ->  \(.dst)   # \(.reason)"' /tmp/move_plan.json || true
echo

read -r -p "Apply move plan? [y/N] " YN
if [[ "${YN:-N}" != [Yy] ]]; then
  echo "Aborted."
  exit 0
fi

echo "=== B3) Execute plan ==="
python3 - <<'PY'
import json, pathlib, shutil, sys, os
import subprocess

# Re-load plan from previous python (stored in shell? We'll rebuild quickly)
plan = []
# reconstruct plan exactly as before
def classify_py(path: pathlib.Path):
    try:
        src = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return "generic"
    if "import addon.bb8_core" in src:
        return "addon-runtime"
    if "import bb8_core" in src:
        return "legacy-import"
    if "__main__" in src:
        return "cli-tool"
    for needle in ("docker","paho","git","ha ","boto3","google"):
        if f"import {needle}" in src or f"from {needle} " in src:
            return "ops-tooling"
    return "generic"

# Root services.d
root_svc = pathlib.Path("services.d")
if root_svc.exists():
    for svc in root_svc.iterdir():
        if svc.is_dir():
            for p in svc.rglob("*"):
                if p.is_file():
                    dst = pathlib.Path("addon/services.d")/svc.name/p.relative_to(svc)
                    plan.append({"src": str(p), "dst": str(dst), "reason": "root services.d forbidden → addon/services.d"})

# tools/
tools_root = pathlib.Path("tools")
if tools_root.exists():
    for p in tools_root.rglob("*"):
        if p.is_file():
            if p.suffix in (".py",".sh",".bash"):
                cat = classify_py(p) if p.suffix == ".py" else "sh-generic"
                if cat in ("addon-runtime","cli-tool"):
                    dst = pathlib.Path("addon/tools")/p.relative_to(tools_root)
                    plan.append({"src": str(p), "dst": str(dst), "reason": f"{cat} → addon/tools"})
                elif cat == "ops-tooling":
                    dst = pathlib.Path("ops/tools")/p.relative_to(tools_root)
                    plan.append({"src": str(p), "dst": str(dst), "reason": f"{cat} → ops/tools"})

moves = 0
for item in plan:
    src = pathlib.Path(item["src"])
    dst = pathlib.Path(item["dst"])
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.exists():
        shutil.move(str(src), str(dst))
        print(f"MOVED: {src} -> {dst}  # {item['reason']}")
        moves += 1
print(f"TOKEN: MOVES={moves}")
PY

echo
echo "=== B4) Git stage & commit ==="
git add -A
git commit -m "repo-shape: rehome root services.d & tools into canonical locations; no prod code changes"
echo "Done."