#!/usr/bin/env bash
# SSH into Home Assistant and run the runtime fetch/reset+restart script.
# Uses either explicit env (HA_HOST/HA_SSH_USER/HA_SSH_PORT/HA_SSH_KEY) or
# falls back to your ~/.ssh/config host alias "home-assistant".

set -euo pipefail

REMOTE_SCRIPT="${REMOTE_SCRIPT:-/config/domain/shell_commands/addons_runtime_fetch.sh}"

use_env=false
if [[ -n "${HA_HOST:-}" && -n "${HA_SSH_USER:-}" && -n "${HA_SSH_KEY:-}" ]]; then
  use_env=true
  : "${HA_SSH_PORT:=22}"
  [[ -f "$HA_SSH_KEY" ]] || { echo "ERROR: HA_SSH_KEY not found: $HA_SSH_KEY"; exit 2; }
fi

# Connectivity probe
if $use_env; then
  ssh -i "$HA_SSH_KEY" -p "$HA_SSH_PORT" -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new \
    "${HA_SSH_USER}@${HA_HOST}" "ha core info >/dev/null && echo SSH_HA_OK"
else
  # rely on local ~/.ssh/config 'Host home-assistant'
  ssh home-assistant "ha core info >/dev/null && echo SSH_HA_OK"
fi

# Deploy (fetch + hard-reset + restart add-on)
if $use_env; then
  ssh -i "$HA_SSH_KEY" -p "$HA_SSH_PORT" -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new \
    "${HA_SSH_USER}@${HA_HOST}" "bash ${REMOTE_SCRIPT}"
else
  ssh home-assistant "bash ${REMOTE_SCRIPT}"
fi

echo "DEPLOY_SSH_OK"
