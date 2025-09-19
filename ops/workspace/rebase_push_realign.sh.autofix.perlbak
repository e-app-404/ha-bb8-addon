#!/usr/bin/env bash
set -Eeuo pipefail
export WORKSPACE_ROOT="/Users/evertappels/Projects/HA-BB8"
export REPORT_ROOT="/Users/evertappels/Projects/HA-BB8/reports"
WS="${WORKSPACE_ROOT}"
ADDON="${WS}/addon"
RUNTIME="/Volumes/HA/addons/local/beep_boop_bb8"
REMOTE="git@github.com:e-app-404/ha-bb8-addon.git"
BRANCH="main"

# 0) Make sure .gitignore has cache rules (won't duplicate if already there)
grep -qxF "__pycache__/" "${ADDON}/.gitignore" 2>/dev/null || printf "\n# Python cache\n__pycache__/\n*.pyc\n" >> "${ADDON}/.gitignore"
git -C "${ADDON}" add .gitignore
if ! git -C "${ADDON}" diff --cached --quiet; then
  git -C "${ADDON}" commit -m "chore: ensure .gitignore excludes Python caches"
fi

# 1) Update refs and REBASE local commits on top of origin/main
git -C "${ADDON}" fetch origin --prune
git -C "${ADDON}" rebase "origin/${BRANCH}"

# If the rebase stops for conflicts, resolve them, then:
#   git -C "${ADDON}" add <files>
#   git -C "${ADDON}" rebase --continue
# (Re-run this block from the 'push' step after finishing.)

# 2) Ensure no cached *.pyc remain tracked (robust pathspecs; no zsh globbing)
git -C "${ADDON}" rm -r --cached --ignore-unmatch ':(glob)**/*.pyc' ':(glob)**/__pycache__/**' || true
if ! git -C "${ADDON}" diff --cached --quiet; then
  git -C "${ADDON}" commit -m "chore: drop tracked Python cache files"
fi

# 3) Push workspace to remote (fast-forward now)
git -C "${ADDON}" push origin "HEAD:${BRANCH}"

# 4) Align runtime to the same remote HEAD
git -C "${RUNTIME}" fetch --all --prune
git -C "${RUNTIME}" checkout -B "${BRANCH}" "origin/${BRANCH}"
git -C "${RUNTIME}" reset --hard "origin/${BRANCH}"

# 5) Emit tokens
WSH="$(git -C "${ADDON}" rev-parse --short HEAD)"
RTH="$(git -C "${RUNTIME}" rev-parse --short HEAD)"
echo "DEPLOY_OK runtime_head=${RTH} branch=${BRANCH}"
echo "VERIFY_OK ws_head=${WSH} runtime_head=${RTH} remote=${REMOTE}"
"${WS}/tools/check_structure.sh" >/dev/null && echo "STRUCTURE_OK" || { echo "[fail] structure drift detected"; exit 3; }
echo "WS_READY addon_ws=git_clone_ok runtime=git_clone_ok reports=ok wrappers=ok ops=ok"
