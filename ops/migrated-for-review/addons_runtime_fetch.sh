#!/usr/bin/env bash

set -euo pipefail

CANDIDATES=()
[ -n "${RUNTIME:-}" ] && CANDIDATES+=("$RUNTIME")
CANDIDATES+=(
  "/addons/local/beep_boop_bb8"
  "/mnt/data/supervisor/addons/local/beep_boop_bb8"
  "/usr/share/hassio/addons/local/beep_boop_bb8"
)

find_runtime() {
  local p
  for p in "${CANDIDATES[@]}"; do
    if [ -d "$p" ] && [ -f "$p/config.yaml" ] && [ -f "$p/Dockerfile" ]; then
      echo "$p"; return 0
    fi
  done
  return 1
}

runtime_path="$(find_runtime || true)"
if [ -z "${runtime_path:-}" ]; then
  echo "ERROR: Could not locate runtime clone. Set RUNTIME=<path> and re-run." >&2
  exit 2
fi
echo "Runtime path: $runtime_path"

if git -C "$runtime_path" rev-parse --abbrev-ref HEAD >/dev/null 2>&1; then
  BRANCH="$(git -C "$runtime_path" rev-parse --abbrev-ref HEAD)"
else
  BRANCH="$(git -C "$runtime_path" symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null | sed 's@^origin/@@' || true)"
  [ -n "$BRANCH" ] || BRANCH="main"
fi
echo "Using branch: $BRANCH"

SECRETS="/config/secrets.yaml"
TOK_KEYS=("github_addons_bb8_auth" "github_repo_bb8-classic")

get_token() {
  if [ -n "${GITHUB_TOKEN:-}" ]; then echo "$GITHUB_TOKEN"; return; fi
  if [ -f "/config/.github_token" ]; then tr -d '\r\n' < /config/.github_token; return; fi
  if [ -f "$SECRETS" ]; then
    local k line val
    for k in "${TOK_KEYS[@]}"; do
      line="$(grep -E "^${k}:[[:space:]]*" "$SECRETS" || true)"
      if [ -n "$line" ]; then
        # shellcheck disable=SC2001
        val="$(echo "$line" | sed -E "s/^${k}:[[:space:]]*\"?([^\"]*)\"?.*$/\1/")"
        [ -n "$val" ] && { echo "$val"; return; }
      fi
    done
  fi
  echo ""
}

normalize_https_origin() {
  local origin repo_path
  origin="$(git -C "$runtime_path" remote get-url origin)"
  # shellcheck disable=SC2001
  repo_path="$(echo "$origin" | sed -E 's#(git@github.com:|https://([^@]+@)?github.com/)##; s#\.git$##')"
  [ -n "$repo_path" ] || { echo "ERROR: Could not parse origin URL: $origin" >&2; return 1; }
  git -C "$runtime_path" remote set-url origin "https://github.com/${repo_path}.git"
}

has_ssh_key() { [ -f "$HOME/.ssh/id_ed25519" ] || [ -f "/config/.ssh/id_ed25519" ]; }

install_ssh_key_if_present() {
  if [ -f "/config/.ssh/id_ed25519" ]; then
    mkdir -p "$HOME/.ssh" && chmod 700 "$HOME/.ssh"
    cp /config/.ssh/id_ed25519* "$HOME/.ssh/" 2>/dev/null || true
    chmod 600 "$HOME/.ssh/id_ed25519" 2>/dev/null || true
    chmod 644 "$HOME/.ssh/id_ed25519.pub" 2>/dev/null || true
    ssh-keyscan -t ed25519 github.com >> "$HOME/.ssh/known_hosts" 2>/dev/null || true
  fi
}

try_auth() {
  if git -C "$runtime_path" ls-remote --exit-code origin >/dev/null 2>&1; then
    if git -C "$runtime_path" remote get-url origin | grep -q '^git@github.com:'; then
      echo "AUTH_OK:SSH"; return 0
    else
      echo "AUTH_OK:HTTPS"; return 0
    fi
  fi

  local token; token="$(get_token)"
  if [ -n "$token" ]; then
    git config --global credential.helper 'store --file /config/.git-credentials'
    install -m 600 /dev/null /config/.git-credentials 2>/dev/null || true
    printf 'https://%s:%s@github.com\n' "${GITHUB_USERNAME:-x-access-token}" "$token" > /config/.git-credentials
    chmod 600 /config/.git-credentials
    normalize_https_origin || true
    if git -C "$runtime_path" ls-remote --exit-code origin >/dev/null 2>&1; then
      echo "AUTH_OK:HTTPS"; return 0
    fi
  fi

  if has_ssh_key; then
    install_ssh_key_if_present
    if git -C "$runtime_path" ls-remote --exit-code origin >/dev/null 2>&1; then
      echo "AUTH_OK:SSH"; return 0
    fi
  fi

  echo "ERROR: Git auth failed. Provide a PAT in /config/.github_token or secrets.yaml, or install SSH deploy key in /config/.ssh/id_ed25519." >&2
  return 1
}

try_auth

git -C "$runtime_path" fetch --all --prune
git -C "$runtime_path" reset --hard "origin/${BRANCH}"
echo "DEPLOY_OK — runtime hard-reset to origin/${BRANCH}"

command -v ha >/dev/null 2>&1 || { echo "ERROR: 'ha' CLI not found in PATH." >&2; exit 5; }

BASE_SLUG="$(sed -nE 's/^[[:space:]]*slug:[[:space:]]*\"?([^\"#]+)\"?.*$/\1/p' "$runtime_path/config.yaml" | head -n1)"
if [ -z "$BASE_SLUG" ]; then
  echo "ERROR: Could not read 'slug' from $runtime_path/config.yaml" >&2
  exit 6
fi

if [[ "$BASE_SLUG" == local_* ]]; then
  FULL_SLUG="$BASE_SLUG"
else
  FULL_SLUG="local_${BASE_SLUG}"
fi

echo "Restarting add-on: ${FULL_SLUG}"
ha addons restart "$FULL_SLUG"

sleep 2
STATE="$(ha addons info "$FULL_SLUG" | awk -F': ' '/state:/ {print $2}' | tr -d '\r')"
echo "Add-on state: ${STATE}"
if [ "$STATE" = "started" ]; then
  echo "VERIFY_OK — add-on restarted and running"
else
  echo "ERROR: Add-on state is '${STATE}', expected 'started'." >&2
  exit 4
fi
