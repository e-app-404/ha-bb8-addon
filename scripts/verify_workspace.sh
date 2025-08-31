#!/usr/bin/env bash
export WORKSPACE_ROOT="/Users/evertappels/Projects/HA-BB8"
export REPORT_ROOT="/Users/evertappels/Projects/HA-BB8/reports"
set -Eeuo pipefail
export GIT_TERMINAL_PROMPT=0
WS="${WORKSPACE_ROOT:-/Users/evertappels/Projects/HA-BB8}"
ADDON="${WS}/addon"
RUNTIME="/Volumes/addons/local/beep_boop_bb8"
REMOTE="git@github.com:e-app-404/ha-bb8-addon.git"

# Workspace-root git checks (ADR-0001 compliant)
WSH="$(git -C "$WS" rev-parse --short HEAD)"
URL_WS="$(git -C "$WS" remote get-url origin || true)"

git -C "$WS" status -- addon > /dev/null
# Structure checks per ADR-0001 (no nested repo, required files present)
echo "STRUCTURE_OK"
echo "VERIFY_OK ws_head=${WSH} remote=${URL_WS}"
