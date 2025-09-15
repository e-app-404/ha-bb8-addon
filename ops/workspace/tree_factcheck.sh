#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

echo "=== A1) Tree snapshot (focused) ==="
echo "TOKEN: ROOT_DIRS"
find . -maxdepth 1 -type d -not -name ".git" -not -name ".*" -print | sort
echo

echo "TOKEN: ADDON_SUBDIRS"
find addon -maxdepth 2 -type d -not -name ".*" -print | sort
echo

echo "TOKEN: OPS_SUBDIRS"
find ops -maxdepth 2 -type d -not -name ".*" -print | sort
echo

echo "TOKEN: SERVICES_ROOT"
find services.d -type f 2>/dev/null | sed 's/^/services.d: /' || true
echo

echo "TOKEN: TOOLS_ROOT"
find tools -maxdepth 2 -type f 2>/dev/null | sed 's/^/tools: /' || true
echo

echo "=== A2) Shebang & file type scan ==="
python3 - <<'PY'
import os, re, json, pathlib, sys
roots = ["addon", "ops", "scripts", "services.d", "tools"]
r = []
for root in roots:
    if not os.path.isdir(root): continue
    for p in pathlib.Path(root).rglob("*"):
        if p.is_dir(): continue
        if p.name.startswith("."): continue
        kind = "other"
        shebang = None
        try:
            with p.open("rb") as f:
                head = f.read(200).decode("utf-8", "ignore")
            m = re.match(r"^#!\s*(\S.*)$", head)
            if m: shebang = m.group(1)
        except Exception:
            pass
        if p.suffix == ".py":
            kind = "py"
        elif p.suffix in (".sh",".bash"):
            kind = "sh"
        elif shebang:
            if "python" in shebang: kind="py"
            elif any(s in shebang for s in ("bash","sh","ash")): kind="sh"
        r.append({"path": str(p), "kind": kind, "shebang": shebang})
print("TOKEN: SHEBANG_SCAN")
print(json.dumps(r, indent=2))
PY
echo

echo "=== A3) Python import classification (addon-runtime vs ops) ==="
python3 - <<'PY'
import ast, pathlib, json, sys, re

def classify_py(path: pathlib.Path):
    src = path.read_text(encoding="utf-8", errors="ignore")
    try:
        tree = ast.parse(src, filename=str(path))
    except Exception as e:
        return {"path": str(path), "error": f"parse:{e}"}
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                imports.add(n.name)
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            imports.add(mod)
    cat = "generic"
    if any(m.startswith("addon.bb8_core") for m in imports):
        cat = "addon-runtime"
    elif any(m.startswith("bb8_core") for m in imports):
        cat = "legacy-import"  # forbidden
    elif any(m.split(".",1)[0] in ("docker","ha","paho","boto3","google","git") for m in imports):
        cat = "ops-tooling"
    elif "__main__" in src:
        cat = "cli-tool"
    return {"path": str(path), "category": cat, "imports": sorted(list(imports))}

paths = sorted([p for p in pathlib.Path(".").rglob("*.py") if not any(seg.startswith(".") for seg in p.parts)])
rows = [classify_py(p) for p in paths if p.parts[0] in ("addon","ops","scripts","tools","services.d")]
print("TOKEN: PY_CLASSIFY")
print(json.dumps(rows, indent=2))
PY
echo

echo "=== A4) s6/overlay service detection ==="
python3 - <<'PY'
import pathlib, json, os
svc = []
for root in ("addon/services.d","services.d"):
    d = pathlib.Path(root)
    if not d.exists(): continue
    for sub in d.iterdir():
        if not sub.is_dir(): continue
        files = [p.name for p in sub.iterdir() if p.is_file()]
        has_run = "run" in files
        has_log = (sub / "log" / "run").exists()
        svc.append({"root": root, "service": sub.name, "has_run": has_run, "has_log": has_log})
print("TOKEN: S6_SERVICES")
print(json.dumps(svc, indent=2))
PY
echo

echo "=== A5) Offenders: bare 'bb8_core' imports (should be 'addon.bb8_core') ==="
OFF=$(grep -R -n --include='*.py' -E '(^|[^/])\b(from|import)\s+bb8_core(\.|[[:space:]]|$)' addon ops scripts tools services.d 2>/dev/null || true)
echo "TOKEN: LEGACY_IMPORT_COUNT=$(printf "%s" "$OFF" | sed '/^$/d' | wc -l | tr -d ' ')"
[ -z "$OFF" ] || printf "%s\n" "$OFF"
echo

echo "=== A6) Quick counts ==="
echo "TOKEN: COUNT_addon_py=$(find addon -name '*.py' | wc -l | tr -d ' ')"
echo "TOKEN: COUNT_ops_py=$(find ops -name '*.py' | wc -l | tr -d ' ')"
echo "TOKEN: COUNT_scripts_py=$(find scripts -name '*.py' | wc -l | tr -d ' ')"
echo "TOKEN: COUNT_tools_py=$(find tools -name '*.py' | wc -l | tr -d ' ')"
echo "TOKEN: EXISTS_services_root=$(test -d services.d && echo 1 || echo 0)"
echo "TOKEN: EXISTS_tools_root=$(test -d tools && echo 1 || echo 0)"
