#!/usr/bin/env bash
set -euo pipefail

# Defaults (override with env if needed)
SRC_DEFAULT="/Volumes/HA/addons/local/beep_boop_bb8"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST_DIR="${REPO_ROOT}/addon"

SRC="${ADDON_SOURCE:-$SRC_DEFAULT}"

echo "[restore_addon] repo_root=${REPO_ROOT}"
echo "[restore_addon] source=${SRC}"
echo "[restore_addon] dest=${DEST_DIR}"

if [[ -d "${REPO_ROOT}/addons/local/beep_boop_bb8" ]]; then
  echo "[restore_addon] Removing stale ./addons/local/beep_boop_bb8"
  rm -rf "${REPO_ROOT}/addons/local/beep_boop_bb8"
fi

if [[ ! -d "${SRC}" ]]; then
  echo "[restore_addon][ERROR] Source directory not found: ${SRC}" >&2
  exit 1
fi

mkdir -p "${DEST_DIR}"

  # Mirror source -> ./addon (portable flags for macOS rsync)
  # Note: Drop -E -H -A -X to avoid unsupported flags on the system rsync.
  rsync -a --delete \
  --exclude ".DS_Store" \
  --exclude "__pycache__" \
  --exclude "*.pyc" \
  --exclude ".pytest_cache" \
  --exclude ".mypy_cache" \
  --exclude ".ruff_cache" \
  --exclude ".venv*" \
  "${SRC}/" "${DEST_DIR}/"

# Minimal verification of key paths
missing=0
check() {
  local p="${DEST_DIR}/$1"
  if [[ ! -e "$p" ]]; then
    echo "[restore_addon][MISSING] $1"
    missing=1
  else
    echo "[restore_addon][OK] $1"
  fi
}

check "Makefile"
check "ops/evidence/collect_stp4.py"
check "bb8_core/bridge_controller.py"
check "bb8_core/facade.py"
check "bb8_core/bb8_presence_scanner.py"

if [[ $missing -ne 0 ]]; then
  echo "[restore_addon][ERROR] One or more required files are missing after sync." >&2
  exit 2
fi

echo "[restore_addon] Sync complete."
exit 0
