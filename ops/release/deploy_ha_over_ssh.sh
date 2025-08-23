#!/usr/bin/env bash
# Deploy add-on over SSH. Never prints secrets. Supports subcommands:
#   - deploy (default)
#   - test-llat (reports presence only; never prints token)
set -euo pipefail

CMD="${1:-deploy}"

REMOTE_HOST_ALIAS="${REMOTE_HOST_ALIAS:-home-assistant}"    # user: babylon-babes
REMOTE_SCRIPT="${REMOTE_SCRIPT:-/config/domain/shell_commands/addons_runtime_fetch.sh}"
REMOTE_RUNTIME="${REMOTE_RUNTIME:-/addons/local/beep_boop_bb8}"
REMOTE_SLUG="${REMOTE_SLUG:-local_beep_boop_bb8}"
HA_URL="${HA_URL:-}"                                        # if empty, remote will try smart defaults
HA_LLAT_KEY="${HA_LLAT_KEY:-ha_llat}"

run_ssh() { ssh "$REMOTE_HOST_ALIAS" "$@"; }

# Silent presence check (awk exit code only; no stdout from secrets.yaml)
remote_llat_probe() {
  run_ssh env HA_LLAT_KEY="$HA_LLAT_KEY" sh -eu <<'REMOTE'
SECRETS="/config/secrets.yaml"; KEY="${HA_LLAT_KEY:-ha_llat}"
awk -v k="$KEY" '
  /^[[:space:]]*#/ {next}
  $1 ~ "^[[:space:]]*"k"[[:space:]]*$" {found=1; exit}
  END{exit found?0:1}
' "$SECRETS" >/dev/null 2>&1 && echo "LLAT_PRESENT" || { echo "LLAT_MISSING"; exit 2; }
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

# --- Extract LLAT (silent) ---
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
[ -n "$TOKEN" ] || { echo "ERROR: LLAT token parse failed from $SECRETS under key $KEY"; exit 2; }

# --- URL candidates that work from add-ons ---
CANDS=""
# If HA_URL provided from caller, try it first
if [ -n "${HA_URL:-}" ]; then CANDS="$HA_URL"; fi
# Internal DNS (Supervisor network)
CANDS="${CANDS}
http://homeassistant:8123
http://homeassistant.local:8123
http://172.30.32.1:8123"

# --- Functions: try Services API, then Supervisor API ---
try_service() {
  url="$1"
  code="$(curl -sS -o /tmp/resp.json -w "%{http_code}" \
    -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    -X POST "$url/api/services/hassio/addon_restart" \
    -d "{\"addon\":\"$REMOTE_SLUG\"}" || true)"
  if [ "$code" = "200" ] && grep -q '"result"[[:space:]]*:[[:space:]]*"ok"' /tmp/resp.json; then
    echo "VERIFY_OK — add-on restarted via Services API ($url)"
    return 0
  fi
  return 1
}

try_supervisor() {
  url="$1"
  code="$(curl -sS -o /tmp/resp.json -w "%{http_code}" \
    -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    -X POST "$url/api/hassio/addons/$REMOTE_SLUG/restart" || true)"
  if [ "$code" = "200" ] && grep -q '"result"[[:space:]]*:[[:space:]]*"ok"' /tmp/resp.json; then
    echo "VERIFY_OK — add-on restarted via Supervisor API ($url)"
    return 0
  fi
  return 1
}

# --- Attempt restart across candidates ---
ok=0
IFS='
'
for base in $CANDS; do
  base="$(echo "$base" | tr -d '[:space:]')" ; [ -n "$base" ] || continue
  if try_service "$base"; then ok=1; break; fi
  if try_supervisor "$base"; then ok=1; break; fi
done

if [ "$ok" -ne 1 ]; then
  # Surface last HTTP code/body for debugging without secrets
  echo "ERROR: HTTP fallback restart failed across candidates." >&2
  echo "INFO: last HTTP $(cat /tmp/resp.json 2>/dev/null | sed -E 's/\"(authorization|token)\":\"[^\"]+\"/\"\1\":\"***\"/g')" >&2 || true
  exit 1
fi
REMOTE
    fi
    echo "DEPLOY_SSH_OK"
    ;;

  *)
    echo "Usage: $0 [deploy|test-llat]" >&2
    exit 64
    ;;
esac

