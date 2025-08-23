echo "DEPLOY_SSH_OK"

#!/usr/bin/env bash
set -euo pipefail

# Defaults for your environment; override via env if needed
REMOTE_HOST_ALIAS="${REMOTE_HOST_ALIAS:-home-assistant}"          # your working alias (babylon-babes)
REMOTE_SCRIPT="${REMOTE_SCRIPT:-/config/domain/shell_commands/addons_runtime_fetch.sh}"
REMOTE_RUNTIME="${REMOTE_RUNTIME:-/addons/local/beep_boop_bb8}"
REMOTE_SLUG="${REMOTE_SLUG:-local_beep_boop_bb8}"
HA_URL="${HA_URL:-http://homeassistant.local:8123}"

run_ssh() { ssh "$REMOTE_HOST_ALIAS" "$@"; }

# Connectivity ping
run_ssh 'echo SSH_HA_OK'

# Try the built-in script first (uses `ha`); if not available/authorized, fallback via HTTP+LLAT.
if run_ssh 'ha core info >/dev/null 2>&1'; then
  run_ssh "bash ${REMOTE_SCRIPT}"
else
  # Manual deploy + HTTP restart with LLAT from /config/secrets.yaml (no regex metachar globs)
  run_ssh env REMOTE_RUNTIME="$REMOTE_RUNTIME" REMOTE_SLUG="$REMOTE_SLUG" HA_URL="$HA_URL" sh -eu <<'REMOTE'
cd "$REMOTE_RUNTIME"
git fetch origin
git reset --hard origin/main
echo "DEPLOY_OK — runtime hard-reset to origin/main"

SECRETS="/config/secrets.yaml"
KEY="${HA_LLAT_KEY:-ha_llat}"
TOKEN="$(awk -v k="$KEY" '
  $1 ~ ("^" k ":") {
    line=$0
    sub(/^.*:[ \t]*/,"",line)
    gsub(/^"/,"",line); gsub(/"$/,"",line)
    print line; exit
  }' "$SECRETS" 2>/dev/null || true)"

if [ -z "$TOKEN" ]; then
  echo "ERROR: No LLAT token found in $SECRETS under key $KEY" >&2
  exit 2
fi

curl -sS -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
     -X POST "$HA_URL/api/services/hassio/addon_restart" \
     -d "{\"addon\":\"$REMOTE_SLUG\"}" | grep -q '"result":[[:space:]]*"ok"' \
     && echo "VERIFY_OK — add-on restarted and running (HTTP)" \
     || { echo "ERROR: HTTP fallback restart failed" >&2; exit 1; }
REMOTE
fi

