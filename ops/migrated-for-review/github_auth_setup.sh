#!/usr/bin/env bash

set -euo pipefail

RUNTIME="/addons/local/beep_boop_bb8"
SECRETS="/config/secrets.yaml"
KEY="github_addons_bb8_auth"

TOKEN="${GITHUB_TOKEN:-}"
if [ -z "$TOKEN" ] && [ -f "$SECRETS" ]; then
  LINE="$(grep -E "^${KEY}:[[:space:]]*" "$SECRETS" || true)"
  if [ -n "$LINE" ]; then
    TOKEN="$(echo "$LINE" | sed -E "s/^${KEY}:[[:space:]]*\"?([^\"]*)\"?.*$/\1/")"
  fi
fi

if [ -z "$TOKEN" ]; then
  read -s -p "GitHub PAT (read-only): " TOKEN; echo
fi

if [ -z "$TOKEN" ]; then
  echo "ERROR: No token provided. Set GITHUB_TOKEN, add $KEY to $SECRETS, or enter interactively." >&2
  exit 2
fi


USER_NAME="${GITHUB_USERNAME:-x-access-token}"
# Make the credential store persistent across reboots
git config --global credential.helper 'store --file /config/.git-credentials'
install -m 600 /dev/null /config/.git-credentials
printf 'https://%s:%s@github.com\n' "$USER_NAME" "$TOKEN" > /config/.git-credentials

git -C "$RUNTIME" remote set-url origin "https://github.com/${repo_path}.git"

origin="$(git -C "$RUNTIME" remote get-url origin)"
repo_path="$(echo "$origin" | sed -E 's#(git@github.com:|https://([^@]+@)?github.com/)##; s#\.git$##')"
if [ -z "$repo_path" ]; then
  echo "ERROR: Could not parse origin URL: $origin" >&2
  exit 3
fi
git -C "$RUNTIME" remote set-url origin "https://github.com/${repo_path}.git"
( git -C "$RUNTIME" remote set-head origin -a >/dev/null 2>&1 || true )

if git -C "$RUNTIME" ls-remote origin >/dev/null 2>&1; then
  echo "AUTH_OK:HTTPS"
else
  echo "ERROR: Authentication failed. Check token scope (repo:read) and origin URL." >&2
  exit 4
fi
