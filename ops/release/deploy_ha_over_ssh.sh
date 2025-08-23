
#!/usr/bin/env bash
set -euo pipefail

REMOTE_HOST_ALIAS="${REMOTE_HOST_ALIAS:-home-assistant}"
RUNTIME="/addons/local/beep_boop_bb8"

# 1) SSH reachability
ssh -o BatchMode=yes "$REMOTE_HOST_ALIAS" 'echo SSH_HA_OK' 2>/dev/null

# 2) Hard reset runtime to origin/main
ssh "$REMOTE_HOST_ALIAS" "set -euo pipefail; git -C '$RUNTIME' fetch origin; git -C '$RUNTIME' reset --hard origin/main; echo 'DEPLOY_OK — runtime hard-reset to origin/main'"

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
