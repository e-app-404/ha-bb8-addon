# HTTP fallback diagnostics & fixes (copy/paste)

# 0) Decide execution context
#    A) Run inside HA OS / an add-on shell  → use SUPERVISOR proxy (no 8123 needed)
#    B) Run from your workstation/CI       → use HA Core API at http(s)://<host>:8123

# 1A) If you choose INSIDE HA (Supervisor proxy path)
#    Open an add-on shell (or SSH into HA OS), then:
export SUPERVISOR_TOKEN=$(bash -c 'echo "$SUPERVISOR_TOKEN"')  # should already exist in add-on shells
curl -sS -H "Authorization: Bearer $SUPERVISOR_TOKEN" http://supervisor/ping
# Expect: {"result": "ok"}  → if not, you’re not in a Supervisor context.

# Restart BB8 add-on via Supervisor API (adjust slug as needed)
ADDON_SLUG=local_beep_boop_bb8
curl -sS -X POST -H "Authorization: Bearer $SUPERVISOR_TOKEN" \
  "http://supervisor/addons/$ADDON_SLUG/restart"

# Restart Core (optional step in your sequence)
curl -sS -X POST -H "Authorization: Bearer $SUPERVISOR_TOKEN" \
  http://supervisor/core/restart

# 1B) If you choose WORKSTATION/CI (HA Core API path)
#    Create a long-lived token in HA user profile and set:
export HA_URL="http://homeassistant.local:8123"   # or http://192.168.0.129:8123
export HA_TOKEN="eyJ0eXAiOiJKV1QiLCJhbGciOi..."   # long-lived access token

# Sanity ping:
curl -sS -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/"
# Expect JSON metadata. If this fails, fix HA_URL / network / token.

# Restart BB8 add-on via HA's hassio service proxy:
ADDON_SLUG=local_beep_boop_bb8
curl -sS -X POST -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" \
  -d "{\"addon\":\"$ADDON_SLUG\"}" \
  "$HA_URL/api/services/hassio/addon_restart"

# Restart Core:
curl -sS -X POST -H "Authorization: Bearer $HA_TOKEN" \
  "$HA_URL/api/services/homeassistant/restart"

# 2) Fix your deploy script variables (prevent the 'homeassista' truncation and 000 spam)
# In .evidence.env (or your makefile), set ONE canonical URL and stick to it:
HA_URL=http://192.168.0.129:8123
# Remove multi-try concatenations; use exactly one path depending on context.

# 3) Minimal, robust restart helper (drop-in)
cat > ops/evidence/restart_helpers.sh <<'SH'
#!/usr/bin/env bash
set -euo pipefail

mode="${1:-auto}"
addon="${2:-local_beep_boop_bb8}"

if [[ "$mode" == "supervisor" || ( "$mode" == "auto" && -n "${SUPERVISOR_TOKEN:-}" ) ]]; then
  curl -fsS -H "Authorization: Bearer $SUPERVISOR_TOKEN" http://supervisor/ping >/dev/null
  curl -fsS -X POST -H "Authorization: Bearer $SUPERVISOR_TOKEN" "http://supervisor/addons/$addon/restart"
  echo "OK: supervisor add-on restart"
  exit 0
fi

if [[ -n "${HA_URL:-}" && -n "${HA_TOKEN:-}" ]]; then
  curl -fsS -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/" >/dev/null
  curl -fsS -X POST -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" \
       -d "{\"addon\":\"$addon\"}" "$HA_URL/api/services/hassio/addon_restart"
  echo "OK: HA API add-on restart"
  exit 0
fi

echo "ERR: No valid context (need SUPERVISOR_TOKEN or HA_URL+HA_TOKEN)"; exit 2
SH
chmod +x ops/evidence/restart_helpers.sh

# 4) Replace the HTTP fallback block in your deploy with:
#    (pick one context explicitly; stop trying many broken hostnames)
ops/evidence/restart_helpers.sh supervisor local_beep_boop_bb8 \
  || ops/evidence/restart_helpers.sh ha local_beep_boop_bb8

# 5) One-liner checks to avoid '000'
# DNS:
getent hosts homeassistant.local || echo "DNS for homeassistant.local not resolved"
# Port reachability from workstation:
nc -vz 192.168.0.129 8123 || echo "HA :8123 not reachable from here"

# 6) Tie back to your flow
# After the restart succeeds via the verified path, run your evidence scripts:
python reports/checkpoints/INT-HA-CONTROL/mqtt_health_echo_test.py ...
python reports/checkpoints/INT-HA-CONTROL/entity_persistence_audit.py ...
# etc.

Summary
- HTTP fallback = “use HTTP API to force restarts” when git/Supervisor hooks aren’t available.
- Use **Supervisor proxy inside HA** or **HA Core API from outside**—don’t mix.
- Your 000s came from bad host strings and using internal addresses externally.
- Lock a single, explicit context + token and the fallback will be reliable.
