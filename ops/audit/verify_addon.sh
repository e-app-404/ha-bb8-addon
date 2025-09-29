#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BASE="${REPO_ROOT}/addon"

fail=0
req=(
  "Makefile"
  "bb8_core/bridge_controller.py"
  "bb8_core/facade.py"
  "bb8_core/ble_link.py"
  "bb8_core/bb8_presence_scanner.py"
)
# Check addon files
for r in "${req[@]}"; do
  if [[ ! -f "${BASE}/${r}" ]]; then
    echo "[verify_addon][MISSING] ${r}"
    fail=1
  else
    echo "[verify_addon][OK] ${r}"
  fi
done

# Check ops evidence file separately (different base path)
if [[ ! -f "${REPO_ROOT}/ops/evidence/collect_stp4.py" ]]; then
  echo "[verify_addon][MISSING] ops/evidence/collect_stp4.py"
  fail=1
else
  echo "[verify_addon][OK] ops/evidence/collect_stp4.py"
fi

if [[ $fail -ne 0 ]]; then
  echo "[verify_addon][ERROR] Verification failed." >&2
  exit 3
fi

echo "[verify_addon] All required files present."
exit 0
