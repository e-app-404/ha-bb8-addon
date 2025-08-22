#!/usr/bin/env bash
set -Eeuo pipefail

WS="/Users/evertappels/Projects/HA-BB8"
ADDON="${WS}/addon"
RUNTIME="/Volumes/addons/local/beep_boop_bb8"
REMOTE="git@github.com:e-app-404/ha-bb8-addon.git"
NOW="$(date +%Y%m%d_%H%M%S)"
REPORTS_DIR="${WS}/reports"
COLLISIONS_FILE="${REPORTS_DIR}/collisionstest_collisions_${NOW}.txt"

mkdir -p "${REPORTS_DIR}/collisions"

git -C "${ADDON}" rev-parse --is-inside-work-tree >/dev/null
if ! git -C "${ADDON}" remote | grep -qx origin; then
  git -C "${ADDON}" remote add origin "${REMOTE}"
fi
git -C "${ADDON}" remote set-url origin "${REMOTE}"
git -C "${ADDON}" fetch origin --prune

BR="$(git -C "${ADDON}" branch --show-current 2>/dev/null || true)"
if [ -z "${BR}" ] || [ "${BR}" = "HEAD" ]; then
  BR="$(git -C "${ADDON}" ls-remote --symref origin HEAD | awk '/^ref:/ {sub("refs\/heads\/","",$2); print $2; exit}')"
  [ -z "${BR}" ] && BR="main"
fi

echo "[start] consolidate ${NOW}"

echo "[step] unify reports"
if [ -d "${ADDON}/reports" ]; then
  mkdir -p "${REPORTS_DIR}/addon"
  rsync -a "${ADDON}/reports/" "${REPORTS_DIR}/addon/"
  if git -C "${ADDON}" ls-files --error-unmatch reports >/dev/null 2>&1; then
    git -C "${ADDON}" rm -r --quiet reports
    git -C "${ADDON}" commit -m "ADR-0001: unify reports to workspace"
  fi
fi

echo "[step] unify tools into ops"
mkdir -p "${WS}/ops"
if [ -d "${ADDON}/tools" ]; then
  rsync -a "${ADDON}/tools/" "${WS}/ops/"
  if git -C "${ADDON}" ls-files --error-unmatch tools >/dev/null 2>&1; then
    git -C "${ADDON}" rm -r --quiet tools
    git -C "${ADDON}" commit -m "ADR-0001: move tools to workspace ops"
  fi
fi
if [ -d "${WS}/tools" ]; then
  rsync -a "${WS}/tools/" "${WS}/ops/"
  if ! rmdir "${WS}/tools" 2>/dev/null; then
    echo "Warning: Could not remove ${WS}/tools (directory not empty or in use)" >&2
  fi
fi

echo "[step] canonicalize tests under addon/tests"
mkdir -p "${ADDON}/tests"
if [ -d "${WS}/tests" ]; then
  : > "${COLLISIONS_FILE}"
  find "${WS}/tests" -type f -print0 | while IFS= read -r -d '' f; do
    rel="${f#${WS}/tests/}"
    src="${WS}/tests/${rel}"
    dst="${ADDON}/tests/${rel}"
    if [ -f "${dst}" ] && ! cmp -s "${src}" "${dst}"; then
      echo "${rel}" >> "${COLLISIONS_FILE}"
    fi
  done
  rm -rf "${WS}/tests"
  git -C "${ADDON}" add tests
  if ! git -C "${ADDON}" diff --cached --quiet; then
    git -C "${ADDON}" commit -m "ADR-0001: canonicalize tests under addon/tests"
  fi
fi
if [ -f "${COLLISIONS_FILE}" ] && [ ! -s "${COLLISIONS_FILE}" ]; then rm -f "${COLLISIONS_FILE}"; fi

echo "[step] push and realign"
GIT_TERMINAL_PROMPT=0 GIT_SSH_COMMAND='ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15' git -C "${ADDON}" push origin "HEAD:refs/heads/${BR}"
git -C "${RUNTIME}" fetch --all --prune
git -C "${RUNTIME}" checkout -B "${BR}" "origin/${BR}"
git -C "${RUNTIME}" reset --hard "origin/${BR}"

WSH="$(git -C "${ADDON}" rev-parse --short HEAD)"
RTH="$(git -C "${RUNTIME}" rev-parse --short HEAD)"
bash "${WS}/ops/audit/check_structure.sh" >/dev/null && echo "STRUCTURE_OK"
echo "DEPLOY_OK runtime_head=${RTH} branch=${BR}"
echo "VERIFY_OK ws_head=${WSH} runtime_head=${RTH} remote=${REMOTE}"
echo "WS_READY addon_ws=git_clone_ok runtime=git_clone_ok reports=ok wrappers=ok ops=ok"
