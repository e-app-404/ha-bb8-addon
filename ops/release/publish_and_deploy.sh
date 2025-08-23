#!/usr/bin/env bash
set -euo pipefail

ADDON_DIR="addon"
ADDON_REMOTE_NAME="${ADDON_REMOTE_NAME:-addon-publish}"
ADDON_REMOTE_URL="${ADDON_REMOTE_URL:-https://github.com/e-app-404/ha-bb8-addon.git}"
REMOTE_HOST_ALIAS="${REMOTE_HOST_ALIAS:-home-assistant}"
DEPLOY_SCRIPT="ops/release/deploy_ha_over_ssh.sh"

[ -d "$ADDON_DIR" ] || { echo "ERROR: $ADDON_DIR/ not found"; exit 2; }
git rev-parse --show-toplevel >/dev/null || { echo "ERROR: not a git repo"; exit 2; }
git symbolic-ref -q HEAD >/dev/null || { echo "ERROR: detached HEAD"; exit 2; }
[ -x "$DEPLOY_SCRIPT" ] || { echo "ERROR: $DEPLOY_SCRIPT missing or not executable"; exit 2; }

git remote get-url "$ADDON_REMOTE_NAME" >/dev/null 2>&1 || git remote add "$ADDON_REMOTE_NAME" "$ADDON_REMOTE_URL"

TMP_BRANCH="__addon_pub_tmp"
git branch -D "$TMP_BRANCH" >/dev/null 2>&1 || true
SPLIT_SHA="$(git subtree split -P "$ADDON_DIR" -b "$TMP_BRANCH")"
git push "$ADDON_REMOTE_NAME" "$TMP_BRANCH:refs/heads/main" --force
git branch -D "$TMP_BRANCH" || true
echo "SUBTREE_PUBLISH_OK:main@${SPLIT_SHA}"

REMOTE_HOST_ALIAS="$REMOTE_HOST_ALIAS" "$DEPLOY_SCRIPT"
echo "PUBLISH_AND_DEPLOY_OK"
