#!/usr/bin/env bash
set -euo pipefail

# Guardrail: detect Python files that import bb8_core directly instead of
# addon.bb8_core (which is required by ADR-0019 namespace rules).

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"

echo "Scanning for bare 'import bb8_core' or 'from bb8_core' usages..."

bad=()
while IFS= read -r -d '' py; do
  if grep -qE "^\s*(from|import)\s+bb8_core(\b|\.)" "$py"; then
    bad+=("$py")
  fi
done < <(find "$ROOT_DIR" -type f -name '*.py' -not -path '*/.venv/*' -print0)

if [ ${#bad[@]} -gt 0 ]; then
  echo "ERROR: Found bare bb8_core imports in the following files:" >&2
  for f in "${bad[@]}"; do echo " - $f" >&2; done
  echo "Please change imports to 'addon.bb8_core' or move code under addon/ as appropriate." >&2
  exit 2
fi

echo "OK: no bare bb8_core imports found"
exit 0
