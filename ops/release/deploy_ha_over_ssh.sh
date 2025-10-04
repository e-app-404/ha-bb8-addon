#!/usr/bin/env bash
# Deploy add-on over SSH. Never prints secrets. Supports subcommands:
#   - deploy (default)
#   - test-llat (reports presence only; never prints token)
set -euo pipefail

# Load configuration from central .env file
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
if [ -f "$PROJECT_ROOT/.env" ]; then
    # Source .env file with bash compatibility
    set -a  # automatically export all variables
    source "$PROJECT_ROOT/.env"
    set +a  # disable auto-export
fi

CMD="${1:-deploy}"

# Use environment variables from .env with fallbacks for backward compatibility
REMOTE_HOST_ALIAS="${HA_SSH_HOST_ALIAS:-${REMOTE_HOST_ALIAS:-home-assistant}}"
REMOTE_SCRIPT="${HA_REMOTE_SCRIPT:-${REMOTE_SCRIPT:-/config/domain/shell_commands/addons_runtime_fetch.sh}}"
REMOTE_RUNTIME="${HA_REMOTE_RUNTIME:-${REMOTE_RUNTIME:-/addons/local/beep_boop_bb8}}"
REMOTE_SLUG="${HA_REMOTE_SLUG:-${REMOTE_SLUG:-local_beep_boop_bb8}}"
SECRETS_PATH="${HA_SECRETS_PATH:-/config/secrets.yaml}"
LLAT_KEY="${HA_LLAT_KEY:-ha_llat}"

run_ssh() { ssh "$REMOTE_HOST_ALIAS" "$@"; }

# Silent presence check (no secrets printed) - using addon secrets file
remote_llat_probe() {
  run_ssh env SECRETS_PATH="$SECRETS_PATH" LLAT_KEY="$LLAT_KEY" sh -eu <<'REMOTE'
SECRETS="${SECRETS_PATH:-/addons/local/beep_boop_bb8/secrets.yaml}"; KEY="${LLAT_KEY:-HA_LLAT_KEY}"
# Check if the secrets file exists and is readable
if [ ! -r "$SECRETS" ]; then
  echo "LLAT_NO_ACCESS (secrets file not found at $SECRETS)"
  exit 2
fi
# Simple pattern to match key followed by colon (format: HA_LLAT_KEY: value)
if grep -E "^[[:space:]]*${KEY}[[:space:]]*:" "$SECRETS" >/dev/null 2>&1; then
  echo "LLAT_PRESENT"
else
  echo "LLAT_MISSING (key '$KEY' not found in $SECRETS)"
  exit 2
fi
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
    run_ssh env REMOTE_RUNTIME="$REMOTE_RUNTIME" REMOTE_SLUG="$REMOTE_SLUG" HA_URL="$HA_URL" SECRETS_PATH="$SECRETS_PATH" LLAT_KEY="$LLAT_KEY" sh -eu <<'REMOTE'
echo "SSH_HA_OK"
SECRETS="${SECRETS_PATH:-/addons/local/beep_boop_bb8/secrets.yaml}"; KEY="${LLAT_KEY:-HA_LLAT_KEY}"

# Discover token presence (no value printed)
if awk -v k="$KEY" '/^[[:space:]]*#/ {next} $0 ~ "^[[:space:]]*[\"'\'']*"k"[\"'\'']*[[:space:]]*:" {found=1; exit} END{exit found?0:1}' "$SECRETS" >/dev/null 2>&1; then
  echo "LLAT_PRESENT"
  TOKEN_OK=1
else
  echo "LLAT_MISSING"
  TOKEN_OK=0
fi

# Use primary HA_URL if set, otherwise use standard candidate
if [ -n "${HA_URL:-}" ]; then
  MAIN_URL="$HA_URL"
else
  MAIN_URL="http://192.168.0.129:8123"
fi
# Additional candidates for diagnostics
CANDS="$MAIN_URL
http://homeassistant:8123
https://homeassistant:8123
http://homeassistant.local:8123
https://homeassistant.local:8123"

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
      run_ssh env REMOTE_RUNTIME="$REMOTE_RUNTIME" REMOTE_SLUG="$REMOTE_SLUG" HA_URL="$HA_URL" SECRETS_PATH="$SECRETS_PATH" LLAT_KEY="$LLAT_KEY" sh -eu <<'REMOTE'
# ADR-0033: Check if runtime is a git repository before git operations
if [ -d "$REMOTE_RUNTIME/.git" ]; then
  echo "Git repository detected, performing dual-clone sync..."
  cd "$REMOTE_RUNTIME"
  git fetch origin
  git reset --hard origin/main
  echo "DEPLOY_OK — runtime hard-reset to origin/main"
else
  echo "Non-git runtime detected, using addon restart method..."
  echo "DEPLOY_OK — runtime sync via addon restart (non-git mode)"
fi

SECRETS="${SECRETS_PATH:-/addons/local/beep_boop_bb8/secrets.yaml}"; KEY="${LLAT_KEY:-HA_LLAT_KEY}"
# LLAT extract (silent) - handles quoted and unquoted keys
TOKEN="$(awk -v k="$KEY" 'BEGIN{FS=":"} /^[[:space:]]*#/ {next} $0 ~ "^[[:space:]]*[\"'\'']*"k"[\"'\'']*[[:space:]]*:" {line=$0; sub(/^[^:]*:[ \t]*/,"",line); sub(/[ \t]*#.*$/,"",line); gsub(/^[ \t]+|[ \t]+$/,"",line); gsub(/^'\''|^"/,"",line); gsub(/'\''$|"$/,"",line); print line; exit}' "$SECRETS" 2>/dev/null || true)"
# Use primary HA_URL if set, otherwise try standard candidates
if [ -n "${HA_URL:-}" ]; then
  PRIMARY_URL="$HA_URL"
else
  # Standard HA API candidates - use first reachable one
  PRIMARY_URL="http://192.168.0.129:8123"
fi

# Use Supervisor API directly (preferred in SSH context)
ok=0
if [ -n "${SUPERVISOR_TOKEN:-}" ]; then
  echo "Using Supervisor API for restart..."
  if curl -fsS -H "Authorization: Bearer $SUPERVISOR_TOKEN" \
       http://supervisor/ping >/dev/null 2>&1; then
    code=$(curl -sS -o /tmp/resp.json -w "%{http_code}" \
           -H "Authorization: Bearer $SUPERVISOR_TOKEN" \
           -H "Content-Type: application/json" \
           -X POST "http://supervisor/addons/$REMOTE_SLUG/restart" 2>/dev/null || true)
    echo "Supervisor restart -> $code"
    if [ "$code" = "200" ] && grep -q '"result"[[:space:]]*:[[:space:]]*"ok"' /tmp/resp.json; then
      echo "VERIFY_OK — add-on restarted via Supervisor API"
      ok=1
    fi
  else
    echo "Supervisor ping failed, falling back to HA API..."
  fi
fi

# Fallback to HA API if Supervisor not available
if [ "$ok" -ne 1 ] && [ -n "$TOKEN" ]; then
  echo "Using HA Core API for restart at $PRIMARY_URL..."
  code=$(curl -k -sS -o /tmp/resp.json -w "%{http_code}" \
         -H "Authorization: Bearer $TOKEN" \
         -H "Content-Type: application/json" \
         -X POST "$PRIMARY_URL/api/services/hassio/addon_restart" \
         -d "{\"addon\":\"$REMOTE_SLUG\"}" 2>/dev/null || true)
  echo "HA API restart -> $code"
  if [ "$code" = "200" ]; then
    # HA API returns empty array [] on successful service call, not "result": "ok"
    echo "VERIFY_OK — add-on restarted via HA API (HTTP 200)"
    ok=1
  else
    echo "HA API response: $(cat /tmp/resp.json 2>/dev/null || echo 'no response file')"
  fi
fi

[ "$ok" -eq 1 ] || { echo "ERROR: Add-on restart failed (no valid API path)"; exit 1; }
REMOTE
    fi
    echo "DEPLOY_SSH_OK"
    ;;

  *)
    echo "Usage: $0 [deploy|test-llat|diagnose]" >&2
    exit 64
    ;;
esac

