#!/usr/bin/env bash
# HA‑BB8 — SSH deploy to Home Assistant add-on runtime (ADR‑0003/0008/0024 compliant)
# - Idempotent rsync to /addons/local/beep_boop_bb8 (fallback /config/addons/local/beep_boop_bb8)
# - Supervisor CLI rebuild/start (preferred); HA API restart fallback
# - Emits receipts on HA host under /config/ha-bb8/deploy/<UTC_TS>/
# - Mirrors receipts locally under reports/ops/ssh/<UTC_TS>/ (no secrets)
set -euo pipefail

# ---------- Bootstrap & ENV ----------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if WS="$(git -C "$SCRIPT_DIR/../.." rev-parse --show-toplevel 2>/dev/null)"; then
  PROJECT_ROOT="$WS"
else
  PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
fi

# Source .env (canonical) and optionally .evidence.env without echoing secrets
if [ -f "$PROJECT_ROOT/.env" ]; then set -a; source "$PROJECT_ROOT/.env"; set +a; fi
if [ -f "$PROJECT_ROOT/.evidence.env" ]; then set -a; source "$PROJECT_ROOT/.evidence.env"; set +a; fi

CONFIG_ROOT="${CONFIG_ROOT:-/config}"
REMOTE_HOST_ALIAS="${REMOTE_HOST_ALIAS:-${HA_SSH_HOST_ALIAS:-}}"
HA_URL="${HA_URL:-}"
HA_LLAT_KEY_NAME="${HA_LLAT_KEY:-HA_LLAT_KEY}"
REMOTE_SLUG="${HA_REMOTE_SLUG:-local_beep_boop_bb8}"
ADDON_FOLDER="beep_boop_bb8"

usage() { echo "Usage: $0 [deploy]" >&2; exit 64; }
CMD="${1:-deploy}"
[[ "$CMD" == "deploy" ]] || usage

# ---------- Helpers ----------
ts_utc() { date -u +%Y%m%dT%H%M%SZ; }
iso_utc() { date -u +%Y-%m-%dT%H:%M:%SZ; }

# ssh wrapper (BatchMode=yes to avoid prompts)
run_ssh() { ssh -o BatchMode=yes "$REMOTE_HOST_ALIAS" "$@"; }

select_reachable_alias() {
  # Try explicit env-provided aliases first, then common defaults
  local candidates=()
  [ -n "${REMOTE_HOST_ALIAS:-}" ] && candidates+=("$REMOTE_HOST_ALIAS")
  [ -n "${HA_SSH_HOST_ALIAS:-}" ] && candidates+=("$HA_SSH_HOST_ALIAS")
  candidates+=(homeassistant ha-host home-assistant hass)
  local c
  for c in "${candidates[@]}"; do
    if ssh -o BatchMode=yes "$c" true >/dev/null 2>&1; then
      REMOTE_HOST_ALIAS="$c"
      echo "$REMOTE_HOST_ALIAS" > /dev/null
      return 0
    fi
  done
  return 1
}

ensure_ssh_alias() {
  if select_reachable_alias; then return 0; fi
  cat >&2 <<EOF
ERROR: No reachable SSH alias found among:
  REMOTE_HOST_ALIAS='$REMOTE_HOST_ALIAS' HA_SSH_HOST_ALIAS='$HA_SSH_HOST_ALIAS' [homeassistant, ha-host, home-assistant, hass]
Add an SSH config entry like:

Host homeassistant
  HostName <home-assistant-ip-or-hostname>
  User root
  IdentityFile ~/.ssh/id_ed25519
  IdentitiesOnly yes
  ForwardAgent yes

Then test:
  ssh -o BatchMode=yes homeassistant true
EOF
  exit 255
}

detect_runtime_path() {
  run_ssh "test -d /addons/local/$ADDON_FOLDER && echo /addons/local/$ADDON_FOLDER || { test -d /config/addons/local/$ADDON_FOLDER && echo /config/addons/local/$ADDON_FOLDER || echo ''; }"
}

ensure_ha_cli() {
  if run_ssh 'command -v ha >/dev/null 2>&1'; then echo 1; else echo 0; fi
}

rsync_workspace_addon() {
  local runtime="$1"
  local excl="$PROJECT_ROOT/ops/rsync_runtime.exclude"
  local base_excludes=(
    "--exclude=.git/" "--exclude=.gitignore" "--exclude=.gitattributes"
    "--exclude=.venv/" "--exclude=__pycache__/" "--exclude=.pytest_cache/"
    "--exclude=.ruff_cache/" "--exclude=.mypy_cache/" "--exclude=.coverage"
    "--exclude=htmlcov/" "--exclude=logs/" "--exclude=reports/" "--exclude=scratch/"
    "--exclude=.DS_Store" "--exclude=node_modules/"
  )
  if [ -f "$excl" ]; then
    rsync -avz --delete --exclude-from "$excl" "$PROJECT_ROOT/addon/" "$REMOTE_HOST_ALIAS:$runtime/"
  else
    rsync -avz --delete "${base_excludes[@]}" "$PROJECT_ROOT/addon/" "$REMOTE_HOST_ALIAS:$runtime/"
  fi
}

get_llat_token_value() {
  # Remote: read /addons/local/<slug>/secrets.yaml key (no printing locally)
  run_ssh "awk -v k='$HA_LLAT_KEY_NAME' -F: 'BEGIN{IGNORECASE=0} /^[[:space:]]*#/ {next} \$0 ~ \"^[[:space:]]*[\"\\\'\"]*\"k\"[\"\\\'\"]*[[:space:]]*:\" {line=\$0; sub(/^[^:]*:[\\t ]*/ ,\"\",line); sub(/[\\t ]*#.*$/ ,\"\",line); gsub(/^[ \\t]+|[ \\t]+$/ ,\"\",line); gsub(/^\'|^\"/,\"\",line); gsub(/\'$/ ,\"\",line); gsub(/\"$/ ,\"\",line); print line; exit }' /addons/local/$ADDON_FOLDER/secrets.yaml 2>/dev/null || true"
}

# ---------- Execution ----------
ensure_ssh_alias

UTC_TS="$(ts_utc)"
REMOTE_RECEIPTS_DIR="$CONFIG_ROOT/ha-bb8/deploy/$UTC_TS"
LOCAL_RECEIPTS_DIR="$PROJECT_ROOT/reports/ops/ssh/$UTC_TS"
mkdir -p "$LOCAL_RECEIPTS_DIR"

# Prepare receipts dir and mark SSH readiness
run_ssh "mkdir -p '$REMOTE_RECEIPTS_DIR' && echo 'TOKEN: SSH_READY' | tee -a '$REMOTE_RECEIPTS_DIR/deploy_receipt.txt' >/dev/null"

# Resolve runtime path
RUNTIME_PATH="$(detect_runtime_path)"
if [ -z "$RUNTIME_PATH" ]; then
  cat >&2 <<EOF
ERROR: Could not find add-on runtime folder on HA host.
Checked: /addons/local/$ADDON_FOLDER and /config/addons/local/$ADDON_FOLDER
Remediation: Create the local add-on at one of those paths, then run:
  ha addons reload && ha addons rebuild local_beep_boop_bb8
EOF
  exit 2
fi
run_ssh "{ echo 'RUNTIME_PATH=$RUNTIME_PATH'; echo 'SSH_ALIAS=$REMOTE_HOST_ALIAS'; } > '$REMOTE_RECEIPTS_DIR/context.env' && echo 'TOKEN: RUNTIME_PATH_OK' | tee -a '$REMOTE_RECEIPTS_DIR/deploy_receipt.txt' >/dev/null"

# Rsync workspace addon → runtime
run_ssh "mkdir -p '$RUNTIME_PATH'"
rsync_workspace_addon "$RUNTIME_PATH"
run_ssh "echo 'TOKEN: RSYNC_OK' | tee -a '$REMOTE_RECEIPTS_DIR/deploy_receipt.txt' >/dev/null"

# Supervisor rebuild/start
CLI_OK="$(ensure_ha_cli)"
STATE="unknown"
REBUILD_OK=0
START_OK=0
if [ "$CLI_OK" = "1" ]; then
  run_ssh "ha addons reload >/dev/null 2>&1 || true"
  if run_ssh "ha addons rebuild '$REMOTE_SLUG'"; then
    REBUILD_OK=1
    run_ssh "echo 'TOKEN: REBUILD_OK' | tee -a '$REMOTE_RECEIPTS_DIR/deploy_receipt.txt' >/dev/null"
  fi
  if run_ssh "ha addons start '$REMOTE_SLUG' >/dev/null 2>&1 || true"; then
    START_OK=1
    run_ssh "echo 'TOKEN: START_OK' | tee -a '$REMOTE_RECEIPTS_DIR/deploy_receipt.txt' >/dev/null"
  fi
  STATE=$(run_ssh "ha addons info '$REMOTE_SLUG' | awk -F: '/^state:/ {gsub(/ /,\"\",\$2); print \$2}' || true")
else
  # Fallback: attempt HA API restart if URL+token available
  TOKEN_VALUE="$(get_llat_token_value)"
  if [ -n "$TOKEN_VALUE" ] && [ -n "$HA_URL" ]; then
    run_ssh "curl -fsS -H 'Authorization: Bearer [MASKED]' -H 'Content-Type: application/json' -X POST \"$HA_URL/api/services/hassio/addon_restart\" -d '{\"addon\":\"$REMOTE_SLUG\"}' >/dev/null 2>&1 || true"
    START_OK=1
    run_ssh "echo 'TOKEN: START_OK' | tee -a '$REMOTE_RECEIPTS_DIR/deploy_receipt.txt' >/dev/null"
  fi
fi

# Logs tail and DEPLOY_OK
run_ssh "ha addons logs '$REMOTE_SLUG' --lines 120 | tail -n 120 > '$REMOTE_RECEIPTS_DIR/addon_logs_tail.txt' 2>/dev/null || :"
run_ssh "echo 'TOKEN: DEPLOY_OK' | tee -a '$REMOTE_RECEIPTS_DIR/deploy_receipt.txt' >/dev/null"

# Mirror receipts locally
rsync -avz "$REMOTE_HOST_ALIAS:$REMOTE_RECEIPTS_DIR/" "$LOCAL_RECEIPTS_DIR/" >/dev/null || true

# Build local receipts.json (bash 3.2 compatible; no mapfile)
tokens_str=""
if [ -f "$LOCAL_RECEIPTS_DIR/deploy_receipt.txt" ]; then
  tokens_str=$(sed -n 's/^TOKEN: \(.*\)$/"\1"/p' "$LOCAL_RECEIPTS_DIR/deploy_receipt.txt" | paste -sd, -)
fi
LOG_TAIL_LEN=0
if [ -f "$LOCAL_RECEIPTS_DIR/addon_logs_tail.txt" ]; then
  LOG_TAIL_LEN="$(wc -l < "$LOCAL_RECEIPTS_DIR/addon_logs_tail.txt" | tr -d ' ')"
fi

STATUS="FAIL"
if echo "$tokens_str" | grep -q '"DEPLOY_OK"'; then STATUS="PASS"; fi
cat > "$LOCAL_RECEIPTS_DIR/receipts.json" <<JSON
{
  "ts": "$(iso_utc)",
  "host_alias": "$REMOTE_HOST_ALIAS",
  "runtime_path": "$RUNTIME_PATH",
  "slug": "$REMOTE_SLUG",
  "tokens": [${tokens_str}],
  "state": "${STATE:-unknown}",
  "logs_tail_len": ${LOG_TAIL_LEN:-0},
  "status": "$STATUS"
}
JSON

echo "SSH deploy complete → $STATUS"
echo "Host receipts: $REMOTE_RECEIPTS_DIR"
echo "Local receipts: $LOCAL_RECEIPTS_DIR"

