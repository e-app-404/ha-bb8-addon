#!/usr/bin/env bash
export WORKSPACE_ROOT="/Users/evertappels/Projects/HA-BB8"
export REPORT_ROOT="/Users/evertappels/Projects/HA-BB8/reports"
set -Eeuo pipefail
export GIT_TERMINAL_PROMPT=0
WS="${WORKSPACE_ROOT:-/Users/evertappels/Projects/HA-BB8}"
ADDON="${WS}/addon"
RUNTIME="/Volumes/HA/addons/local/beep_boop_bb8"
REMOTE="git@github.com:e-app-404/ha-bb8-addon.git"

test -d "${ADDON}/.git" || { echo "[fail] addon not a git repo"; exit 1; }
test -d "${RUNTIME}/.git" || { echo "[fail] runtime not a git repo"; exit 2; }

WSH="$(git -C "${ADDON}" rev-parse --short HEAD)"
RH="$(git -C "${RUNTIME}" rev-parse --short HEAD)"
URL_WS="$(git -C "${ADDON}" remote get-url origin || true)"

echo "VERIFY_OK ws_head=${WSH} runtime_head=${RH} remote=${URL_WS}"
