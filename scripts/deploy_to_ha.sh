#!/usr/bin/env bash
export WORKSPACE_ROOT="/Users/evertappels/Projects/HA-BB8"
export REPORT_ROOT="/Users/evertappels/Projects/HA-BB8/reports"
set -Eeuo pipefail
export GIT_TERMINAL_PROMPT=0
WS="${WORKSPACE_ROOT:-/Users/evertappels/Projects/HA-BB8}"
ADDON="${WS}/addon"
RUNTIME="/Volumes/addons/local/beep_boop_bb8"
REMOTE="git@github.com:e-app-404/ha-bb8-addon.git"

# Subtree publish: skip if addon/ unchanged
if git -C "$WS" diff --quiet HEAD -- addon; then
	echo "SUBTREE_NOOP (addon unchanged)"
else
	git -C "$WS" subtree split -P addon -b __addon_pub_tmp
	git -C "$WS" push -f "$REMOTE" __addon_pub_tmp:main
	git -C "$WS" branch -D __addon_pub_tmp || true
	echo "SUBTREE_PUBLISH_OK"
fi

# Runtime reset (ADR-0001 compliant)
BR="main"
if [ ! -d "${RUNTIME}/.git" ]; then echo "[fail] runtime not a git repo: ${RUNTIME}"; exit 2; fi
git -C "${RUNTIME}" remote set-url origin "${REMOTE}"
git -C "${RUNTIME}" fetch --all --prune
git -C "${RUNTIME}" checkout -B "${BR}" "origin/${BR}"
git -C "${RUNTIME}" reset --hard "origin/${BR}"

RHEAD="$(git -C "${RUNTIME}" rev-parse --short HEAD)"
echo "DEPLOY_OK runtime_head=${RHEAD} branch=${BR}"
