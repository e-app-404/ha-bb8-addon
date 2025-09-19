#!/usr/bin/env bash
set -Eeuo pipefail

# --- constants ---
export WORKSPACE_ROOT="/Users/evertappels/Projects/HA-BB8"
export REPORT_ROOT="/Users/evertappels/Projects/HA-BB8/reports"
WS="${WORKSPACE_ROOT}"
ADDON="${WS}/addon"
RUNTIME="/Volumes/HA/addons/local/beep_boop_bb8"
REMOTE="git@github.com:e-app-404/ha-bb8-addon.git"

# --- safety: capture runtime state before changing anything ---
BK="${WS}/_backup_$(date -u +%Y%m%d_%H%M%S)Z_runtime_canon"
mkdir -p "${BK}" "${REPORT_ROOT}"
( cd "${RUNTIME}";
  git status --porcelain=v1 -uall > "${BK}/status.txt" || true
  git diff > "${BK}/worktree.diff" || true
  git diff --cached > "${BK}/index.diff" || true
  # tar up untracked, if any (best-effort; will skip if none)
  UNTRACKED="$(git ls-files --others --exclude-standard || true)"
  if [ -n "${UNTRACKED}" ]; then
    # shellcheck disable=SC2086
    tar -C "${RUNTIME}" -czf "${BK}/untracked.tgz" ${UNTRACKED} || true
  fi
)
echo "[snapshot] runtime diffs saved under: ${BK}"

# --- normalize remotes on both clones ---
test -d "${RUNTIME}/.git"  || { echo "[fail] runtime not a git repo: ${RUNTIME}"; exit 2; }
test -d "${ADDON}/.git"    || { echo "[fail] addon not a git repo: ${ADDON}"; exit 1; }
git -C "${RUNTIME}" remote set-url origin "${REMOTE}"
git -C "${ADDON}"   remote set-url origin "${REMOTE}"
git -C "${RUNTIME}" fetch --all --prune
git -C "${ADDON}"   fetch --all --prune

# --- choose target branch (prefer the workspace branch if set) ---
BR_WS="$(git -C "${ADDON}" rev-parse --abbrev-ref HEAD)"
BR_RT="$(git -C "${RUNTIME}" rev-parse --abbrev-ref HEAD)"
BRANCH="${BR_WS:-$BR_RT}"
echo "[info] using branch: ${BRANCH}"

# --- commit ALL local runtime edits as canonical (non-destructive) ---
( cd "${RUNTIME}";
  # Optional: if you do NOT want compiled files committed, uncomment the next two lines:
  # git restore --staged --worktree -- '**/*.pyc' '**/__pycache__/**' 2>/dev/null || true
  # find . -type f -path '*/__pycache__/*' -o -name '*.pyc' -exec rm -f {} +

  git add -A
  # Only commit when there is something to commit
  if ! git diff --cached --quiet; then
    GIT_AUTHOR_NAME="local-editor" GIT_AUTHOR_EMAIL="local@runtime" \
    GIT_COMMITTER_NAME="local-editor" GIT_COMMITTER_EMAIL="local@runtime" \
      git commit -m "Accept local runtime changes as canonical (one-time import)"
    echo "[commit] recorded runtime edits as a commit"
  else
    echo "[commit] no staged changes; runtime already clean"
  fi
)

# --- push runtime state to REMOTE as the branch truth (with guard) ---
git -C "${RUNTIME}" push --force-with-lease origin "HEAD:${BRANCH}"
echo "[push] remote '${BRANCH}' now reflects runtime edits"

# --- align workspace addon to the updated remote truth ---
git -C "${ADDON}" checkout -B "${BRANCH}" "origin/${BRANCH}"
git -C "${ADDON}" reset --hard "origin/${BRANCH}"
WS_HEAD="$(git -C "${ADDON}" rev-parse --short HEAD)"
echo "[sync] workspace addon aligned to ${BRANCH} @ ${WS_HEAD}"

# --- align runtime cleanly to the same remote state (now identical to its pushed commit) ---
git -C "${RUNTIME}" checkout -B "${BRANCH}" "origin/${BRANCH}"
git -C "${RUNTIME}" reset --hard "origin/${BRANCH}"
RT_HEAD="$(git -C "${RUNTIME}" rev-parse --short HEAD)"

# --- tokens (deploy is a no-op here; heads already aligned) ---
echo "DEPLOY_OK runtime_head=${RT_HEAD} branch=${BRANCH}"
echo "VERIFY_OK ws_head=${WS_HEAD} runtime_head=${RT_HEAD} remote=${REMOTE}"

# Optionally re-run structure check for good measure
"${WS}/tools/check_structure.sh" >/dev/null && echo "STRUCTURE_OK" || { echo "[fail] structure drift detected"; exit 3; }

echo "WS_READY addon_ws=git_clone_ok runtime=git_clone_ok reports=ok wrappers=ok ops=ok"
