#!/usr/bin/env bash
set -euo pipefail


# Use repo root for all paths
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

echo "=== Step 2: remove duplicate root bb8_core safely; canonicalize imports ==="

# Safety branch
git fetch --all --prune
BR="rescue/remove-root-bb8_core-$(date +%Y%m%d-%H%M%S)"
git switch -c "$BR"

# Re-read audit tokens (or run step 1 first)
only_in_root=$(wc -l < reports/bb8_core_only_in_root.txt 2>/dev/null || echo 0)
divergents=$(wc -l < reports/bb8_core_hash_divergences.txt 2>/dev/null || echo 0)

# Hard stop if we found *real* unique code in root not present in addon (excluding __pycache__, DS_Store)
if [ "$only_in_root" -gt 0 ]; then
  echo "⚠️  Files exist only in root/bb8_core (reports/bb8_core_only_in_root.txt)."
  echo "    Review and manually relocate anything you need into addon/bb8_core, then re-run."
  exit 2
fi

# If divergences found, prefer canonical addon/ copy; log the differences for record
if [ "$divergents" -gt 0 ]; then
  echo "ℹ️  Divergent common files detected; keeping canonical addon/bb8_core versions."
  cp reports/bb8_core_hash_divergences.txt reports/bb8_core_hash_divergences.$(date +%s).txt
fi

# 2.a Remove root-level duplicate tree entirely
if [ -d bb8_core ]; then
  git rm -r --cached --ignore-unmatch bb8_core || true
  rm -rf bb8_core
  echo "/bb8_core/" >> .gitignore
fi

# 2.b Rewrite any lingering imports to canonical path
python - <<'PY'
import pathlib, re
root = pathlib.Path(".")
targets=[]
for p in root.rglob("*.py"):
    if any(seg in (".venv",".git","__pycache__") for seg in p.parts): 
        continue
    s = p.read_text(encoding="utf-8")
    orig=s
    # Replace "from bb8_core import X" -> "from addon.bb8_core import X"
    s = re.sub(r'(^|\n)\s*from\s+bb8_core(\s+import\s+)', r'\1from addon.bb8_core\2', s)
    # Replace "import bb8_core" (bare) -> "import addon.bb8_core as bb8_core"
    s = re.sub(r'(^|\n)\s*import\s+bb8_core(\s|$)', r'\1import addon.bb8_core as bb8_core\2', s)
    if s!=orig:
        p.write_text(s, encoding="utf-8")
        targets.append(str(p))
print("rewritten_files=", len(targets))
PY

# 2.c Remove junk files that keep creeping in
find addon/bb8_core -name ".DS_Store" -delete || true

# 2.d Commit
git add -A
git commit -m "repo-shape: remove legacy root-level bb8_core; enforce canonical addon/bb8_core; rewrite imports; ignore /bb8_core/"

# 2.e Quick import smoke
python - <<'PY'
import importlib
import sys
try:
    importlib.import_module("addon.bb8_core.core")
    importlib.import_module("addon.bb8_core.facade")
    print("import_smoke=OK")
except Exception as e:
    print("import_smoke=FAIL", e)
    sys.exit(1)
PY

echo "=== Step 2 complete. Push branch & open PR when ready. ==="
