#!/usr/bin/env bash
set -euo pipefail

TARGET_BRANCH="${TARGET_BRANCH:-main}"

git rev-parse --is-inside-work-tree >/dev/null
git cat-file -e HEAD^{commit} >/dev/null || { echo "ERROR: No commits yet."; exit 2; }
[ -d addon ] || { echo "ERROR: ./addon directory not found in working tree."; exit 2; }
git cat-file -e HEAD:addon 2>/dev/null || { echo "ERROR: 'addon/' not present in HEAD."; exit 2; }

ORIGINAL_SHA="$(git rev-parse --short HEAD 2>/dev/null || echo unknown)"

REMOTE_URL="${REMOTE_URL:-}"
if [ -z "$REMOTE_URL" ]; then
  if git remote get-url origin >/dev/null 2>&1; then
    REMOTE_URL="$(git remote get-url origin)"
  else
    REMOTE_COUNT="$(git remote | wc -l | tr -d ' ')"
    if [ "$REMOTE_COUNT" = "1" ]; then
      ONLY_REMOTE="$(git remote)"
      REMOTE_URL="$(git remote get-url "$ONLY_REMOTE")"
    else
      echo "ERROR: Could not determine remote URL. Set REMOTE_URL='<https or ssh url>' and re-run."
      exit 3
    fi
  fi
fi

TMPDIR="$(mktemp -d)"
if git archive HEAD:addon >/dev/null 2>&1; then
  git archive HEAD:addon | tar -x -C "$TMPDIR"
else
  git archive HEAD addon | tar -x -C "$TMPDIR" --strip-components 1
fi


[ -e "$TMPDIR/config.yaml" ] || [ -e "$TMPDIR/Dockerfile" ] || {
  echo "ERROR: Export seems empty or wrong. Check that addon/ contains add-on files."; exit 4;
}

# Assert the source config.yaml contains the expected option
grep -q 'enable_health_checks' "$TMPDIR/config.yaml" || { echo "FATAL: enable_health_checks missing in source addon/config.yaml"; exit 1; }

# Idempotency: skip publish if no changes in addon/
if git diff --quiet HEAD^ HEAD -- addon; then
  echo "No changes in addon/. Skipping publish."
  exit 0
fi

(
  cd "$TMPDIR"
  git init -q
  git config user.name  "bb8-publisher"
  git config user.email "bb8-publisher@local"
  git add .
  git -c commit.gpgSign=false commit -m "Publish addon subtree @ ${ORIGINAL_SHA}"
  git remote add origin "$REMOTE_URL"
  git push -f origin HEAD:"${TARGET_BRANCH}"
)

echo "SUBTREE_PUBLISH_OK:${TARGET_BRANCH}@${ORIGINAL_SHA}"
