#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE="${REPO_ROOT}/addon"

fail=0
req=(
  "Makefile"
  "ops/evidence/collect_stp4.py"
  "bb8_core/bridge_controller.py"
  "bb8_core/facade.py"
  "bb8_core/ble_link.py"
  "bb8_core/bb8_presence_scanner.py"
)
for r in "${req[@]}"; do
  if [[ ! -f "${BASE}/${r}" ]]; then
    echo "[verify_addon][MISSING] ${r}"
    fail=1
  else
    echo "[verify_addon][OK] ${r}"
  fi

done

if [[ $fail -ne 0 ]]; then
  echo "[verify_addon][ERROR] Verification failed." >&2
  exit 3
fi

echo "[verify_addon] All required files present."
exit 0
