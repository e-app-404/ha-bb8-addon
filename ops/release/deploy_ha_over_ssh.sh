#!/usr/bin/env bash
# Deploy add-on over SSH. Never prints secrets. Supports subcommands:
#   - deploy (default)
#   - test-llat (reports presence only; never prints token)
set -euo pipefail

CMD="${1:-deploy}"

REMOTE_HOST_ALIAS="${REMOTE_HOST_ALIAS:-home-assistant}"      # your working alias (user: babylon-babes)
REMOTE_SCRIPT="${REMOTE_SCRIPT:-/config/domain/shell_commands/addons_runtime_fetch.sh}"
REMOTE_RUNTIME="${REMOTE_RUNTIME:-/addons/local/beep_boop_bb8}"
REMOTE_SLUG="${REMOTE_SLUG:-local_beep_boop_bb8}"
HA_URL="${HA_URL:-http://127.0.0.1:8123}"                      # loopback on HA host avoids mDNS flakiness
HA_LLAT_KEY="${HA_LLAT_KEY:-ha_llat}"

run_ssh() { ssh "$REMOTE_HOST_ALIAS" "$@"; }

# Helper: robust LLAT extraction on the remote (no token output)
remote_llat_probe() {
  run_ssh env HA_LLAT_KEY="$HA_LLAT_KEY" sh -eu <<'REMOTE'
SECRETS="/config/secrets.yaml"; KEY="${HA_LLAT_KEY:-ha_llat}"
# Extract: value after "key:", strip quotes/comments/whitespace
VAL="$(awk -v k="$KEY" '
  BEGIN{FS=":"}
  /^[[:space:]]*#/ {next}
  $1 ~ "^[[:space:]]*"k"[[:space:]]*$" {
    line=$0
    sub(/^[^:]*:[ \t]*/,"",line)
    sub(/[ \t]*#.*$/,"",line)
    gsub(/^[ \t]+|[ \t]+$/,"",line)
    gsub(/^'\''|^"/,"",line)
    gsub(/'\''$|"$/,"",line)
    print line; exit
  }' "$SECRETS" 2>/dev/null || true)"
[ -n "$VAL" ] && echo "LLAT_PRESENT" || { echo "LLAT_MISSING"; exit 2; }
REMOTE
}

case "$CMD" in
  test-llat)
    # Connectivity ping first
    run_ssh 'echo SSH_HA_OK'
    remote_llat_probe
    echo "DEPLOY_SSH_OK"
    ;;

  deploy)
    # Connectivity ping
    run_ssh 'echo SSH_HA_OK'
    # Try built-in script (uses `ha`); if blocked, do manual deploy + HTTP restart
    if run_ssh 'ha core info >/dev/null 2>&1'; then
      run_ssh "bash ${REMOTE_SCRIPT}"
    else
      run_ssh env REMOTE_RUNTIME="$REMOTE_RUNTIME" REMOTE_SLUG="$REMOTE_SLUG" HA_URL="$HA_URL" HA_LLAT_KEY="$HA_LLAT_KEY" sh -eu <<'REMOTE'
cd "$REMOTE_RUNTIME"
git fetch origin
git reset --hard origin/main
echo "DEPLOY_OK — runtime hard-reset to origin/main"

SECRETS="/config/secrets.yaml"; KEY="${HA_LLAT_KEY:-ha_llat}"
TOKEN="$(awk -v k="$KEY" '
  BEGIN{FS=":"}
  /^[[:space:]]*#/ {next}
  $1 ~ "^[[:space:]]*"k"[[:space:]]*$" {
    line=$0
    sub(/^[^:]*:[ \t]*/,"",line)
    sub(/[ \t]*#.*$/,"",line)
    gsub(/^[ \t]+|[ \t]+$/,"",line)
    gsub(/^'\''|^"/,"",line)
    gsub(/'\''$|"$/,"",line)
    print line; exit
  }' "$SECRETS" 2>/dev/null || true)"
[ -n "$TOKEN" ] || { echo "ERROR: No LLAT token found in $SECRETS under key $KEY" >&2; exit 2; }

# Never echo $TOKEN. Use it only in the header:
curl -sS -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
     -X POST "$HA_URL/api/services/hassio/addon_restart" \
     -d "{\"addon\":\"$REMOTE_SLUG\"}" | grep -q '"result"[[:space:]]*:[[:space:]]*"ok"' \
     && echo "VERIFY_OK — add-on restarted and running (HTTP)" \
     || { echo "ERROR: HTTP fallback restart failed" >&2; exit 1; }
REMOTE
    fi
    echo "DEPLOY_SSH_OK"
    ;;

  *)
    echo "Usage: $0 [deploy|test-llat]" >&2
    exit 64
    ;;
esac

