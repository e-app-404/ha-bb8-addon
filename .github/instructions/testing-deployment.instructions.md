# Deployment options for testing — clarity pass (no guesswork, binary steps)

You’ve got two clean paths to deploy and test the BB8 codebase:

A) **Supervisor/HA OS path (preferred, production-like)**
B) **Standalone dev runner (no Supervisor; quick iteration)**

Both produce the same PASS/FAIL artifacts under `reports/checkpoints/INT-HA-CONTROL/`. Coverage is informative only (per our delta contract); INT-HA-CONTROL acceptance is purely operational.

Acceptance gates (unchanged)
- P0 stability: 120-min window, **0** TypeError/coroutine errors → `error_count_comparison.json`
- MQTT persistence: presence+rssi recover ≤10s after **broker** and **HA core** restarts → `entity_persistence_test.log`, `entity_audit.json`, `mqtt_roundtrip.log`, `mqtt_persistence.log`
- Single-owner discovery: `duplicates_detected == 0` → `discovery_ownership_audit.json`, summary `.txt`
- LED alignment: toggle-gated; strict `{r,g,b}`; same device block → `led_entity_schema_validation.json`, `device_block_audit.log`
- Config defaults: `MQTT_BASE=bb8`, `REQUIRE_DEVICE_ECHO=1`, `PUBLISH_LED_DISCOVERY=0` → `config_env_validation.json`

Rollbacks
- Supervisor path: “Rebuild” to previous tag or revert `/addons/local/...` folder; restart add-on
- Dev runner: stop containers/processes; `git restore -SW .` to last good commit

Below is the exact, ready-to-run process for both paths.

```
# BB8 Deploy-for-Testing Process (Supervisor + Standalone) — copy/paste runnable

################################################################################
# A) SUPERVISOR / HA OS PATH (production-like)
#    Use this when you want the real HA + Supervisor + Mosquitto orchestration.
################################################################################

# PREREQS (run on your workstation with repo checked out)
# - You can SSH/Samba/VS Code into the HA host, or use the Studio Code Server add-on
# - Your add-on lives under HA's local add-ons path (example below)

# 0. Prepare environment on your workstation
cd /Users/evertappels/Projects/HA-BB8
python3 -m venv .venv && source .venv/bin/activate
python -m pip install -U pip paho-mqtt pytest pytest-cov
set -a && source .evidence.env && set +a

# 1. Sync code to HA local add-on (adjust path to your HA host):
#    Example HA path: /addons/local/beep_boop_bb8/bb8_core/
#    Use one of the following options:

# Option 1: VS Code (remote) – copy the whole repo's add-on folder into HA path
# Option 2: rsync (from workstation to HA host; replace HA_HOST):
# rsync -av --delete addon/  ha@HA_HOST:/addons/local/beep_boop_bb8/bb8_core/

# 2. In Home Assistant UI (Supervisor):
#    - Open Add-ons → BB8 → "REBUILD" or "RESTART" (rebuild if Dockerfile changed)
#    - Confirm logs show the new version starting

# 3. Start P0 stability window (120 min) from your repo root (workstation)
bash reports/checkpoints/INT-HA-CONTROL/start_p0_monitoring.sh & disown

#    Within 2 minutes, in HA UI:
#    - Restart the BB8 add-on (Supervisor → Add-ons → BB8 → Restart)

# 4. Run operational evidence collection from your workstation
python reports/checkpoints/INT-HA-CONTROL/mqtt_health_echo_test.py \
  --host "$MQTT_HOST" --port "${MQTT_PORT:-1883}" \
  --user "$MQTT_USER" --password "$MQTT_PASSWORD" \
  --base "$MQTT_BASE" --sla-ms 1000 \
  --out reports/checkpoints/INT-HA-CONTROL/mqtt_roundtrip.log

# 5. Restart sequence (authorized)
#    - T+10 min: Restart MQTT broker add-on (Mosquitto)
#    - T+20 min: Restart Home Assistant Core
#    After each restart, run the entity audit collector:
python reports/checkpoints/INT-HA-CONTROL/entity_persistence_audit.py \
  --ha-url "$HA_URL" --token "$HA_TOKEN" \
  --out-json reports/checkpoints/INT-HA-CONTROL/entity_audit.json \
  --out-log  reports/checkpoints/INT-HA-CONTROL/entity_persistence_test.log

# 6. Single-owner discovery (prevent + detect)
python reports/checkpoints/INT-HA-CONTROL/discovery_ownership_audit.py \
  --topics 'homeassistant/#' \
  --output reports/checkpoints/INT-HA-CONTROL/discovery_ownership_audit.json \
  --summary reports/checkpoints/INT-HA-CONTROL/discovery_ownership_check.txt

# 7. LED alignment (toggle-gated)
#    First ensure PUBLISH_LED_DISCOVERY=0 in add-on options → validator asserts LED ABSENT.
#    Then set =1 → restart BB8 → validate schema + device block:
python reports/checkpoints/INT-HA-CONTROL/led_entity_alignment_test.py \
  --base "$MQTT_BASE" \
  --out-json reports/checkpoints/INT-HA-CONTROL/led_entity_schema_validation.json \
  --out-log  reports/checkpoints/INT-HA-CONTROL/device_block_audit.log

# 8. Config defaults proof
python reports/checkpoints/INT-HA-CONTROL/emit_config_env_validation.py \
  --out reports/checkpoints/INT-HA-CONTROL/config_env_validation.json

# 9. Finalize milestone report (coverage is informative; not blocking Gate A)
./ops/evidence/execute_int_ha_control.sh || true

# EXPECTED PASS ARTIFACTS (to sign INT-HA-CONTROL)
# - error_count_comparison.json
# - mqtt_roundtrip.log, mqtt_persistence.log
# - entity_persistence_test.log, entity_audit.json
# - discovery_ownership_audit.json, discovery_ownership_check.txt
# - led_entity_schema_validation.json, device_block_audit.log
# - config_env_validation.json
# - qa_report.json (reflecting operational criteria only)


################################################################################
# B) STANDALONE DEV RUNNER (no Supervisor) — fast local iteration
#    Use this to debug logic against a reachable broker (your .evidence.env).
################################################################################

# This mode runs the BB8 core logic as a normal Python process or ad-hoc container.
# It does NOT manage HA Core/add-ons; you still point at the same MQTT broker.

# 0. Local env
cd /Users/evertappels/Projects/HA-BB8
python3 -m venv .venv && source .venv/bin/activate
python -m pip install -U pip paho-mqtt
set -a && source .evidence.env && set +a

# 1. (Optional) run BB8 publisher loop directly (example entrypoint pattern)
#    Replace with your actual run module or a thin shim that calls into bb8_core.
PYTHONPATH="$PWD" python - <<'PY'
from addon.bb8_core import mqtt_dispatcher
# Example: start a minimal loop or publish a discovery once for a device_id
# (Adapt this to your dispatcher API; ensure idempotent retained discovery)
print("Publishing minimal retained discovery for dry-run…")
PY

# 2. Execute the same evidence scripts (works without Supervisor)
python reports/checkpoints/INT-HA-CONTROL/mqtt_health_echo_test.py \
  --host "$MQTT_HOST" --port "${MQTT_PORT:-1883}" \
  --user "$MQTT_USER" --password "$MQTT_PASSWORD" \
  --base "$MQTT_BASE" --sla-ms 1000 \
  --out reports/checkpoints/INT-HA-CONTROL/mqtt_roundtrip.log

python reports/checkpoints/INT-HA-CONTROL/discovery_ownership_audit.py \
  --topics 'homeassistant/#' \
  --output reports/checkpoints/INT-HA-CONTROL/discovery_ownership_audit.json \
  --summary reports/checkpoints/INT-HA-CONTROL/discovery_ownership_check.txt

# 3. To simulate restarts without Supervisor:
#    - Broker restart: restart your local Mosquitto/container
#    - HA Core restart: restart your HA Docker container
#    Then run the same persistence audit (requires HA_URL + HA_TOKEN).

# 4. LED alignment validation still applies (toggle variable is env-driven here).
python reports/checkpoints/INT-HA-CONTROL/led_entity_alignment_test.py \
  --base "$MQTT_BASE" \
  --out-json reports/checkpoints/INT-HA-CONTROL/led_entity_schema_validation.json \
  --out-log  reports/checkpoints/INT-HA-CONTROL/device_block_audit.log


################################################################################
# COMMON PITFALLS & GUARDS
################################################################################
# - Absolute paths in scripts: ensure all call repo-relative paths; fix with ROOT="$(git rev-parse --show-toplevel)" fallback
# - Missing deps in HA add-on: rebuild the add-on if Python deps changed (Supervisor → Rebuild)
# - MQTT DNS names: on HA OS, prefer service names (e.g., core-mosquitto); from workstation, use your .evidence.env IP
# - Retained payloads: if duplicates appear, purge stale retained topics under homeassistant/# before re-test
# - Coverage zero: harmless for Gate A; for Gate B (QG-TEST-80), add minimal sanity tests and compatibility shims

################################################################################
# WHAT TO HAND BACK FOR SIGN-OFF
################################################################################
# After running A) Supervisor path (preferred):
# 1) Upload or paste PASS artifacts list above (especially entity/ownership/LED artifacts)
# 2) Confirm the 120-min P0 window result is PASS (zero TypeError/coroutine)
# Strategos will issue formal INT-HA-CONTROL acceptance and open QG-TEST-80 work items.
```

## HTTP Fallback Diagnostics & Fixes (copy/paste)

```bash
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
```
