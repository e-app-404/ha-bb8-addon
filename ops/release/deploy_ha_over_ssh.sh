
#!/usr/bin/env bash
set -euo pipefail

REMOTE_HOST_ALIAS="${REMOTE_HOST_ALIAS:-home-assistant}"
RUNTIME="/addons/local/beep_boop_bb8"
export GIT_DISCOVERY_ACROSS_FILESYSTEM=1

# 1) SSH reachability
ssh -o BatchMode=yes "$REMOTE_HOST_ALIAS" 'echo SSH_HA_OK' 2>/dev/null

# 2) Rsync deployment: copy local addon files to remote runtime
echo "[INFO] Syncing addon files to $REMOTE_HOST_ALIAS:$RUNTIME via rsync..."
rsync -avz --delete ./addon/ "$REMOTE_HOST_ALIAS:$RUNTIME/" && \
  ssh "$REMOTE_HOST_ALIAS" "echo 'DEPLOY_OK — runtime rsync complete'" || {
    echo "ERROR: rsync to $REMOTE_HOST_ALIAS:$RUNTIME failed" >&2
    exit 2
  }

# Compute local checksum
LOCAL_SHA=$(sha256sum ./addon/config.yaml | awk '{print $1}')
echo "LOCAL config.yaml sha256=${LOCAL_SHA}"

# Verify remote config.yaml
REMOTE_SHA=$(ssh "$REMOTE_HOST_ALIAS" "sha256sum $RUNTIME/config.yaml 2>/dev/null | awk '{print \$1}' || true")
echo "REMOTE config.yaml sha256=${REMOTE_SHA}"
[ "${LOCAL_SHA}" = "${REMOTE_SHA}" ] || { echo 'FATAL: config.yaml checksum mismatch after deploy'; exit 1; }

# Assert option is present remotely
ssh "$REMOTE_HOST_ALIAS" "grep -q 'enable_health_checks' $RUNTIME/config.yaml || { echo 'FATAL: enable_health_checks missing in remote config.yaml'; exit 1; }"

# 3) Restart add-on via HA Core Services API using LLAT from /config/secrets.yaml (never prints token)
ssh "$REMOTE_HOST_ALIAS" 'bash -se' <<'RS'
set -euo pipefail
KEY="${HA_LLAT_KEY:-ha_llat}"   # <-- safe default; do NOT reference LLAT_KEY directly under set -u

# Extract the token (quoted or unquoted) without echoing it
LLAT="$(sed -nE "s/^[[:space:]]*${KEY}:[[:space:]]*\"?([^\"]+)\"?.*$/\1/p" /config/secrets.yaml | head -n1 || true)"
if [ -z "$LLAT" ]; then
  echo "ERROR: No LLAT token found in /config/secrets.yaml under key ${KEY}" >&2
  exit 3
fi

payload='{"addon":"local_beep_boop_bb8"}'
for base in ${HA_URL:-} http://homeassistant:8123 http://homeassistant.local:8123 http://172.30.32.1:8123; do
  [ -n "$base" ] || continue
  code=$(curl -sS -o /tmp/resp.json -w "%{http_code}" \
        -H "Authorization: Bearer ${LLAT}" -H "Content-Type: application/json" \
        -X POST "$base/api/services/hassio/addon_restart" -d "$payload" || true)
  # Accept HTTP 200 and either {"result": "ok"} or empty JSON {}
  if [ "$code" = "200" ]; then
  if grep -q '"result"[[:space:]]*:[[:space:]]*"ok"' /tmp/resp.json || grep -q '{[[:space:]]*}' /tmp/resp.json || grep -q '\[[[:space:]]*\]' /tmp/resp.json; then
      echo "VERIFY_OK — add-on restarted via Services API ($base)"
      echo "DEPLOY_SSH_OK"
      exit 0
    fi
  fi
done

echo "ERROR: HTTP fallback restart failed" >&2
echo "Response from API call:" >&2
cat /tmp/resp.json >&2
exit 4
RS
