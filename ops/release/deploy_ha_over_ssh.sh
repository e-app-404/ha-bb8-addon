#!/usr/bin/env bash
# Deploy add-on over SSH. Never prints secrets. Supports subcommands:
#   - deploy (default)
#   - test-llat (reports presence only; never prints token)
set -euo pipefail

CMD="${1:-deploy}"

REMOTE_HOST_ALIAS="${REMOTE_HOST_ALIAS:-home-assistant}"    # SSH alias (user: babylon-babes)
REMOTE_SCRIPT="${REMOTE_SCRIPT:-/config/domain/shell_commands/addons_runtime_fetch.sh}"
REMOTE_RUNTIME="${REMOTE_RUNTIME:-/addons/local/beep_boop_bb8}"
REMOTE_SLUG="${REMOTE_SLUG:-local_beep_boop_bb8}"
HA_URL="${HA_URL:-}"                                        # if empty, remote tries smart defaults
HA_LLAT_KEY="${HA_LLAT_KEY:-ha_llat}"

run_ssh() { ssh "$REMOTE_HOST_ALIAS" "$@"; }

# Silent presence check (no secrets printed)
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
    run_ssh 'echo SSH_HA_OK'
    remote_llat_probe
    echo "DEPLOY_SSH_OK"
    ;;

  diagnose)
    # Prints connectivity + HTTP codes for each candidate + whether hassio service is exposed
    run_ssh env REMOTE_RUNTIME="$REMOTE_RUNTIME" REMOTE_SLUG="$REMOTE_SLUG" HA_URL="$HA_URL" HA_LLAT_KEY="$HA_LLAT_KEY" sh -eu <<'REMOTE'
echo "SSH_HA_OK"
SECRETS="/config/secrets.yaml"; KEY="${HA_LLAT_KEY:-ha_llat}"

# Discover token presence (no value printed)
if awk -v k="$KEY" '/^[[:space:]]*#/ {next} $1 ~ "^[[:space:]]*"k"[[:space:]]*$" {found=1; exit} END{exit found?0:1}' "$SECRETS" >/dev/null 2>&1; then
  echo "LLAT_PRESENT"
  TOKEN_OK=1
else
  echo "LLAT_MISSING"
  TOKEN_OK=0
fi

# URL candidates (Core via Core proxy) – both http/https possibilities
CANDS=""
[ -n "${HA_URL:-}" ] && CANDS="$HA_URL"
CANDS="${CANDS}
http://homeassistant:8123
https://homeassistant:8123
http://homeassistant.local:8123
https://homeassistant.local:8123
http://172.30.32.1:8123
https://172.30.32.1:8123"

# Test reachability & services exposure with LLAT (codes only)
if [ "$TOKEN_OK" -eq 1 ]; then
  echo "== Core API reachability (LLAT) =="
  IFS='\n'
  for base in $CANDS; do
    base="$(echo "$base" | tr -d '[:space:]')"; [ -n "$base" ] || continue
    code=$(curl -k -sS -o /dev/null -w "%{http_code}" -H "Authorization: Bearer REACTOR" "$base/api/" 2>/dev/null || true)
    echo "CAND $base /api/ -> $code"
  done

  echo "== Services endpoint & hassio domain (LLAT) =="
  for base in $CANDS; do
    base="$(echo "$base" | tr -d '[:space:]')"; [ -n "$base" ] || continue
    code=$(curl -k -sS -o /tmp/sv.json -w "%{http_code}" -H "Authorization: Bearer REACTOR" "$base/api/services" 2>/dev/null || true)
    has=$(grep -o '"domain"[[:space:]]*:[[:space:]]*"hassio"' /tmp/sv.json >/dev/null 2>&1 && echo yes || echo no)
    echo "CAND $base /api/services -> $code hassio=$has"
  done

  echo "== Hassio addons list (LLAT) =="
  for base in $CANDS; do
    base="$(echo "$base" | tr -d '[:space:]')"; [ -n "$base" ] || continue
    code=$(curl -k -sS -o /dev/null -w "%{http_code}" -H "Authorization: Bearer REACTOR" "$base/api/hassio/addons" 2>/dev/null || true)
    echo "CAND $base /api/hassio/addons -> $code"
  done
fi

# Supervisor token path (only if add-on exposes SUPERVISOR_TOKEN and Protection mode allows it)
if [ -n "${SUPERVISOR_TOKEN:-}" ]; then
  echo "SUPERVISOR_TOKEN_PRESENT"
  code=$(curl -sS -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $SUPERVISOR_TOKEN" http://supervisor/ping 2>/dev/null || true)
  echo "supervisor /ping -> $code"
  code=$(curl -sS -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $SUPERVISOR_TOKEN" http://supervisor/info 2>/dev/null || true)
  echo "supervisor /info -> $code"
else
  echo "SUPERVISOR_TOKEN_MISSING"
fi
REMOTE
    echo "DEPLOY_SSH_OK"
    ;;

  deploy)
    run_ssh 'echo SSH_HA_OK'
    if run_ssh 'ha core info >/dev/null 2>&1'; then
      run_ssh "bash ${REMOTE_SCRIPT}"
    else
      run_ssh env REMOTE_RUNTIME="$REMOTE_RUNTIME" REMOTE_SLUG="$REMOTE_SLUG" HA_URL="$HA_URL" HA_LLAT_KEY="$HA_LLAT_KEY" sh -eu <<'REMOTE'
cd "$REMOTE_RUNTIME"
git fetch origin
git reset --hard origin/main
echo "DEPLOY_OK — runtime hard-reset to origin/main"

SECRETS="/config/secrets.yaml"; KEY="${HA_LLAT_KEY:-ha_llat}"
# LLAT extract (silent)
TOKEN="$(awk -v k="$KEY" 'BEGIN{FS=":"} /^[[:space:]]*#/ {next} $1 ~ "^[[:space:]]*"k"[[:space:]]*$" {line=$0; sub(/^[^:]*:[ \t]*/,"",line); sub(/[ \t]*#.*$/,"",line); gsub(/^[ \t]+|[ \t]+$/,"",line); gsub(/^'\''|^"/,"",line); gsub(/'\''$|"$/,"",line); print line; exit}' "$SECRETS" 2>/dev/null || true)"
# URL candidates for Core
CANDS=""
[ -n "${HA_URL:-}" ] && CANDS="$HA_URL"
CANDS="${CANDS}
http://homeassistant:8123
https://homeassistant:8123
http://homeassistant.local:8123
https://homeassistant.local:8123
http://172.30.32.1:8123
https://172.30.32.1:8123"

# Attempt restart via Core (services API, then hassio API), printing codes only (no secrets)
ok=0
IFS='\n'
if [ -n "$TOKEN" ]; then
  for base in $CANDS; do
    base="$(echo "$base" | tr -d '[:space:]')"; [ -n "$base" ] || continue
    code=$(curl -k -sS -o /tmp/resp.json -w "%{http_code}" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -X POST "$base/api/services/hassio/addon_restart" -d "{\"addon\":\"$REMOTE_SLUG\"}" 2>/dev/null || true)
    echo "TRY services $base -> $code"
    if [ "$code" = "200" ] && grep -q '"result"[[:space:]]*:[[:space:]]*"ok"' /tmp/resp.json; then
      echo "VERIFY_OK — add-on restarted via Services API ($base)"
      ok=1; break
    fi
    code=$(curl -k -sS -o /tmp/resp.json -w "%{http_code}" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -X POST "$base/api/hassio/addons/$REMOTE_SLUG/restart" 2>/dev/null || true)
    echo "TRY supervisor-proxy $base -> $code"
    if [ "$code" = "200" ] && grep -q '"result"[[:space:]]*:[[:space:]]*"ok"' /tmp/resp.json; then
      echo "VERIFY_OK — add-on restarted via Supervisor API ($base)"
      ok=1; break
    fi
  done
fi

# Supervisor token direct path (if available)
if [ "$ok" -ne 1 ] && [ -n "${SUPERVISOR_TOKEN:-}" ]; then
  code=$(curl -sS -o /tmp/resp.json -w "%{http_code}" -H "Authorization: Bearer $SUPERVISOR_TOKEN" -H "Content-Type: application/json" -X POST "http://supervisor/addons/$REMOTE_SLUG/restart" 2>/dev/null || true)
  echo "TRY supervisor-socket http://supervisor -> $code"
  if [ "$code" = "200" ] && grep -q '"result"[[:space:]]*:[[:space:]]*"ok"' /tmp/resp.json; then
    echo "VERIFY_OK — add-on restarted via Supervisor socket"
    ok=1
  fi
fi

[ "$ok" -eq 1 ] || { echo "ERROR: HTTP fallback restart failed across all paths"; exit 1; }
REMOTE
    fi
    echo "DEPLOY_SSH_OK"
    ;;

  *)
    echo "Usage: $0 [deploy|test-llat|diagnose]" >&2
    exit 64
    ;;
esac

