#!/usr/bin/env bash
export WORKSPACE_ROOT="/Users/evertappels/Projects/HA-BB8"
export REPORT_ROOT="/Users/evertappels/Projects/HA-BB8/reports"
set -Eeuo pipefail
export GIT_TERMINAL_PROMPT=0
WS="${WORKSPACE_ROOT:-/Users/evertappels/Projects/HA-BB8}"
ADDON="${WS}/addon"
RUNTIME="/Volumes/addons/local/beep_boop_bb8"
REMOTE="git@github.com:e-app-404/ha-bb8-addon.git"

test -d "${ADDON}/.git" || { echo "[fail] addon not a git repo"; exit 1; }
git -C "${ADDON}" remote set-url origin "${REMOTE}"

BR="$(git -C "${ADDON}" rev-parse --abbrev-ref HEAD)"
git -C "${ADDON}" fetch --all
git -C "${ADDON}" push origin "${BR}"

if [ ! -d "${RUNTIME}/.git" ]; then echo "[fail] runtime not a git repo: ${RUNTIME}"; exit 2; fi
git -C "${RUNTIME}" remote set-url origin "${REMOTE}"
git -C "${RUNTIME}" fetch --all --prune
git -C "${RUNTIME}" checkout -B "${BR}" "origin/${BR}"
git -C "${RUNTIME}" reset --hard "origin/${BR}"

RHEAD="$(git -C "${RUNTIME}" rev-parse --short HEAD)"
echo "DEPLOY_OK runtime_head=${RHEAD} branch=${BR}"
