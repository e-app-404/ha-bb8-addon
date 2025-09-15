#!/usr/bin/env bash
set -euo pipefail

echo "=== Canonicalize all bb8_core imports in Python files ==="

# Rewrite in *.py only; skip venv, git, caches, legacy reports/docs
python - <<'PY'
import pathlib, re

root = pathlib.Path(".")
rewritten = []

FROM_SUB = re.compile(r'(^|\n)(\s*)from\s+bb8_core\.([A-Za-z0-9_\.]+)\s+import\s+', re.M)
IMPORT_SUB = re.compile(r'(^|\n)(\s*)import\s+bb8_core\.([A-Za-z0-9_\.]+)(\s+as\s+[A-Za-z0-9_]+)?(\s|$)', re.M)
FROM_BARE = re.compile(r'(^|\n)(\s*)from\s+bb8_core\s+import\s+', re.M)
IMPORT_BARE = re.compile(r'(^|\n)(\s*)import\s+bb8_core(\s|$)', re.M)

def should_skip(p: pathlib.Path) -> bool:
    parts = set(p.parts)
    if ".git" in parts or ".venv" in parts or "__pycache__" in parts:
        return True
    # Only source code; skip docs, reports, ops outputs, legacy patches
    skip_roots = {"docs", "reports", "legacy", "ops", "rescue_staging", "app"}
        # Use repo root for all paths
    return p.parts[0] in skip_roots and not (len(p.parts) > 1 and p.parts[0]=="docs" and p.parts[1]=="ADR")

for p in root.rglob("*.py"):
    if should_skip(p):
        continue
    text = p.read_text(encoding="utf-8", errors="ignore")
    orig = text

    # from bb8_core.<sub> import X  -> from addon.bb8_core.<sub> import X
    text = FROM_SUB.sub(lambda m: f"{m.group(1)}{m.group(2)}from addon.bb8_core.{m.group(3)} import ", text)

    # import bb8_core.<sub> [as alias] -> import addon.bb8_core.<sub> [as alias]
    text = IMPORT_SUB.sub(lambda m: f"{m.group(1)}{m.group(2)}import addon.bb8_core.{m.group(3)}{m.group(4) or ''}{m.group(5)}", text)

    # from bb8_core import X -> from addon.bb8_core import X
    text = FROM_BARE.sub(lambda m: f"{m.group(1)}{m.group(2)}from addon.bb8_core import ", text)

    # import bb8_core -> import addon.bb8_core as bb8_core
    text = IMPORT_BARE.sub(lambda m: f"{m.group(1)}{m.group(2)}import addon.bb8_core as bb8_core{m.group(3)}", text)

    if text != orig:
        p.write_text(text, encoding="utf-8")
        rewritten.append(str(p))

print(f"rewritten_count={len(rewritten)}")
for f in rewritten:
    print(f" - {f}")
PY

# Remove stray duplicate env file; keep dotfile variant
if [ -f "env.bleep.example" ]; then
  git rm -f --cached env.bleep.example 2>/dev/null || true
  rm -f env.bleep.example
fi

git add -A
git commit -m "repo-shape: complete import canonicalization to addon.bb8_core.*; remove duplicate env.bleep.example" || true

echo "=== Re-run preflight audit to confirm zero code hits ==="
bash scripts/preflight_duplicate_bb8_core.sh

echo "=== If [token] forbidden_import_hits now reflects only non-code (docs/reports) or zero, proceed to step 3 ==="

        if [ -f "env.bleep.example" ]; then
          git rm -f --cached env.bleep.example 2>/dev/null || true
          rm -f env.bleep.example
        fi

