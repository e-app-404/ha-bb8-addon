#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

fail=0

# Files that should exist at repo root
repo_req=(
  "Makefile"
  "ops/evidence/collect_stp4.py"
)

for r in "${repo_req[@]}"; do
  if [[ ! -f "${REPO_ROOT}/${r}" ]]; then
    echo "[verify_addon][MISSING] ${r}"
    fail=1
  else
    echo "[verify_addon][OK] ${r}"
  fi
done

# Files that should exist under addon/
addon_req=(
  "bb8_core/bridge_controller.py"
  "bb8_core/facade.py"
  "bb8_core/ble_link.py"
  "bb8_core/bb8_presence_scanner.py"
)
for r in "${addon_req[@]}"; do
  if [[ ! -f "${REPO_ROOT}/addon/${r}" ]]; then
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
