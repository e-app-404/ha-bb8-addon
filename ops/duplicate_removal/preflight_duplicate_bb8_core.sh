#!/usr/bin/env bash
set -euo pipefail

echo "=== Preflight: duplicate bb8_core audit ==="
mkdir -p reports

# Use repo root for all paths
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

# (a) List files in both trees (py + sh + yaml + md)
ROOT_DIR="bb8_core"
ADDON_DIR="addon/bb8_core"

root_list="$(mktemp)"; addon_list="$(mktemp)"
( cd "$ROOT_DIR" 2>/dev/null && find . -type f \( -name "*.py" -o -name "*.sh" -o -name "*.yaml" -o -name "*.yml" -o -name "*.md" \) | sed 's|^\./||' | sort ) > "$root_list" || true
( cd "$ADDON_DIR" 2>/dev/null && find . -type f \( -name "*.py" -o -name "*.sh" -o -name "*.yaml" -o -name "*.yml" -o -name "*.md" \) | sed 's|^\./||' | sort ) > "$addon_list" || true

echo "[token] root_has_files=$(wc -l < "$root_list" | tr -d ' ')"
echo "[token] addon_has_files=$(wc -l < "$addon_list" | tr -d ' ')"

# (b) Names present in root but missing in addon (should be 0 or only legacy junk)
comm -23 "$root_list" "$addon_list" | tee reports/bb8_core_only_in_root.txt
echo "[token] only_in_root=$(wc -l < reports/bb8_core_only_in_root.txt | tr -d ' ')"

# (c) Compare hashes for common files (detect divergence)
common_list="$(mktemp)"
comm -12 "$root_list" "$addon_list" > "$common_list" || true

divergences="$(mktemp)"
while IFS= read -r rel; do
  rsha=$(sha256sum "$ROOT_DIR/$rel" | cut -d' ' -f1 || true)
  asha=$(sha256sum "$ADDON_DIR/$rel" | cut -d' ' -f1 || true)
  if [ "$rsha" != "$asha" ]; then
    printf "%s %s %s\n" "$rel" "$rsha" "$asha" >> "$divergences"
  fi
done < "$common_list"

cp "$divergences" reports/bb8_core_hash_divergences.txt
echo "[token] divergent_common_files=$(wc -l < reports/bb8_core_hash_divergences.txt | tr -d ' ')"

# (d) Grep for forbidden imports that reference root-level bb8_core
grep -RIn --exclude-dir=.venv --exclude-dir=.git -E '(^|[^.])\b(from|import)\s+bb8_core(\b|[^.])' \
  | tee reports/bb8_core_forbidden_imports.txt || true
echo "[token] forbidden_import_hits=$(wc -l < reports/bb8_core_forbidden_imports.txt | tr -d ' ')"

# (e) Emit a JSON summary token for logs/artifacts
python - <<'PY'
import json, pathlib
def count(p): 
    f=pathlib.Path(p)
    return 0 if not f.exists() else sum(1 for _ in f.read_text().splitlines() if _.strip())
summary={
  "only_in_root": pathlib.Path("reports/bb8_core_only_in_root.txt").read_text().splitlines() if pathlib.Path("reports/bb8_core_only_in_root.txt").exists() else [],
  "divergent_common_files_count": count("reports/bb8_core_hash_divergences.txt"),
  "forbidden_import_hits_count": count("reports/bb8_core_forbidden_imports.txt"),
}
pathlib.Path("reports/bb8_core_dup_audit.json").write_text(json.dumps(summary, indent=2))
print("[token] audit_json=reports/bb8_core_dup_audit.json")
PY

echo "=== Preflight done. If tokens show zeros (or only legacy junk), proceed to step 2. ==="
