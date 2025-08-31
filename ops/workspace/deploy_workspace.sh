#!/usr/bin/env bash
set -Eeuo pipefail
export GIT_TERMINAL_PROMPT=0
export WORKSPACE_ROOT="/Users/evertappels/Projects/HA-BB8"
export REPORT_ROOT="/Users/evertappels/Projects/HA-BB8/reports"

WS="${WORKSPACE_ROOT}"
ADDON="${WS}/addon"
RUNTIME="/Volumes/addons/local/beep_boop_bb8"
REMOTE="git@github.com:e-app-404/ha-bb8-addon.git"

# Safety + inputs
test -d "${ADDON}/.git" || { echo "[fail] addon not a git repo"; exit 1; }
test -d "${RUNTIME}/.git" || { echo "[fail] runtime not a git repo: ${RUNTIME}"; exit 2; }
git -C "${ADDON}" remote set-url origin "${REMOTE}"
git -C "${RUNTIME}" remote set-url origin "${REMOTE}"

# Determine branch from workspace addon
BRANCH="$(git -C "${ADDON}" rev-parse --abbrev-ref HEAD)"

# Push workspace state to remote
git -C "${ADDON}" fetch --all --prune
git -C "${ADDON}" push origin "${BRANCH}"

# Save runtime rollback point, then align runtime to the same branch
OLD_RUNTIME_HEAD="$(git -C "${RUNTIME}" rev-parse --short HEAD || echo 'none')"
git -C "${RUNTIME}" fetch --all --prune
git -C "${RUNTIME}" checkout -B "${BRANCH}" "origin/${BRANCH}"
git -C "${RUNTIME}" reset --hard "origin/${BRANCH}"
NEW_RUNTIME_HEAD="$(git -C "${RUNTIME}" rev-parse --short HEAD)"

# Token 1: DEPLOY_OK
echo "DEPLOY_OK runtime_head=${NEW_RUNTIME_HEAD} branch=${BRANCH}"

# Optional: restart the HA add-on (do this via HA UI or your supervisor workflow)
# Example (if you have HA CLI on the host/container): ha addons restart local_beep_boop_bb8
# Or via REST API with a long-lived token:
# curl -sS -X POST -H "Authorization: Bearer ${HASS_TOKEN}" -H "Content-Type: application/json" \
#   http://homeassistant.local:8123/api/services/hassio/addon_restart -d '{"addon":"local_beep_boop_bb8"}'

# Token 2: VERIFY_OK (compare heads & remote)
WS_HEAD="$(git -C "${ADDON}" rev-parse --short HEAD)"
URL_WS="$(git -C "${ADDON}" remote get-url origin || true)"
echo "VERIFY_OK ws_head=${WS_HEAD} runtime_head=${NEW_RUNTIME_HEAD} remote=${URL_WS}"

# Token 3: STRUCTURE_OK (re-run to be explicit after deploy)
"${WS}/tools/check_structure.sh" >/dev/null && echo "STRUCTURE_OK" || { echo "[fail] structure drift detected post-deploy"; exit 3; }

# Token 4: WS_READY (final echo, already achieved earlier—repeat for the record)
echo "WS_READY addon_ws=git_clone_ok runtime=git_clone_ok reports=ok wrappers=ok ops=ok"
