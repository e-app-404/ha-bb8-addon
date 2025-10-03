HA BB8 add-on ⇄ Docker ⇄ Supervisor ⇄ Home Assistant Core — who does what (and how they interact)

LAYERED MENTAL MODEL (top → bottom)
1) Home Assistant Core (the app)
   - What it is: The Python application that provides automations, integrations, UI, entities, etc.
   - Where it runs: As a Docker container when using HA OS/Supervised, or as a bare Python process for HA Core installs.
   - How it sees BB8: Through integrations (notably MQTT). HA Core subscribes to MQTT Discovery topics; if BB8 publishes valid discovery/state, Core creates/updates entities.

2) Supervisor (the orchestrator)
   - What it is: A management service that *controls* add-ons and HA Core lifecycles, networking, updates, backups, ingress, and provides the Supervisor API.
   - Relationship to Docker: Uses the Docker Engine to pull images, create containers, set networks/volumes, start/stop, health-check them.
   - Relationship to Core: Exposes services (Ingress, Add-on management, Backups). Core can call some Supervisor endpoints; Supervisor can restart Core and add-ons.
   - Relationship to add-ons: Owns their lifecycle, passes configuration (exposed as `/data/options.json` inside the add-on), provides tokens (e.g., `SUPERVISOR_TOKEN`) and internal DNS (e.g., `supervisor`, `core-mosquitto`).

3) Docker (the runtime)
   - What it is: Container engine providing isolation, networking, volumes.
   - Role here: Runs **containers** for HA Core and each add-on (including BB8 and, commonly, the Mosquitto broker). Supervisor is “the boss,” Docker is “the machinery.”

4) Add-ons (containers managed by Supervisor) — BB8 is one of these
   - What they are: Prepackaged services that extend HA. Each add-on is a Docker container with a contract (config schema, exposed ports, logs, options).
   - BB8 add-on specifics:
     - Talks to the MQTT broker (often another add-on like Mosquitto) to publish **Home Assistant MQTT Discovery** and state.
     - May need host capabilities (e.g., BLE access) via extra privileges/mounts as configured by the Supervisor.
     - Reads config from `/data/options.json` and environment variables injected by Supervisor (e.g., `MQTT_BASE`, feature toggles).
     - Should NOT directly “write into” Home Assistant; instead, it *publishes* discovery/state to MQTT, which HA Core consumes.

5) Other key players (common in HA OS/Supervised)
   - Mosquitto add-on: The MQTT broker container. BB8 publishes to it; HA Core’s MQTT integration subscribes. Retained discovery/state here ensures **entity persistence** across restarts.
   - Ingress proxy (via Supervisor): Provides web UIs for add-ons through HA’s frontend without exposing extra ports.
   - OS Agent / DNS / Multicast helpers: System services used by Supervisor and add-ons for networking/service discovery (transparent to BB8 logic but relevant for connectivity).

COMMUNICATION PATHS (day-to-day flows)
- BB8 → MQTT Broker (publish):
  - Discovery topics under `homeassistant/...` (retained) and runtime state under `bb8/...`.
  - Your **single-owner** strategy relies on retained discovery + LWT teardown to avoid duplicates.
- HA Core MQTT Integration → MQTT Broker (subscribe):
  - Consumes discovery & state; creates/updates entities (presence, rssi, optional LED).
- Operator → Supervisor:
  - Start/stop/restart BB8 and broker add-ons; read logs; configure options; trigger snapshots.
- BB8 ↔ Supervisor API (optional):
  - Add-on can call Supervisor endpoints (using `SUPERVISOR_TOKEN`) for controlled operations (e.g., service discovery), but typical BB8 flows don’t need to modify HA Core directly.

LIFECYCLE & PERSISTENCE (why your acceptance tests matter)
- Restarts:
  - **Broker restart**: Retained discovery/state should allow HA Core to keep/restore entities quickly (your ≤10s SLA).
  - **HA Core restart**: On reconnect, Core re-subscribes and rehydrates entities from retained messages.
  - **Add-on restart**: BB8 should republish discovery/state idempotently; LWT ensures stale ownership is cleared.
- Storage:
  - Add-on writable space is `/data` inside the container (managed by Supervisor). Your reports/artifacts live under your chosen repo paths at build-time; runtime logs go to Supervisor’s logging, and any persistent add-on data lives in `/data`.

INSTALL FLAVORS (why you sometimes “lose” add-ons)
- **Home Assistant OS** or **Supervised**: You have Supervisor + Add-ons + Docker all working together (this is the model we’re using).
- **Home Assistant Container** (Core in Docker without Supervisor): **No add-ons**; BB8 would have to be run as a plain Docker container and manually wired to MQTT.
- **Home Assistant Core** (Python venv on a generic OS): No Supervisor, no add-ons; everything manual.

SECURITY & CONFIG HANDOFFS
- Config: Supervisor injects add-on options and env vars; **your defaults** (MQTT_BASE=bb8, REQUIRE_DEVICE_ECHO=1, PUBLISH_LED_DISCOVERY=0) are enforced at add-on runtime.
- Tokens/Network: Add-ons run on the Supervisor-managed Docker network(s); can reach the broker by DNS service name (e.g., `core-mosquitto`) or IP. Access is scoped; Ingress is reverse-proxied by Supervisor.

HOW THIS MAPS TO INT-HA-CONTROL
- **Entity persistence across broker restart**: Retained discovery/state on MQTT + HA Core re-subscribe → validated via your restart harness.
- **Zero duplicate discovery owners**: Idempotent retained publish + LWT teardown (Supervisor ensures BB8 lifecycle; BB8 ensures topic hygiene).
- **LED entity alignment**: BB8 publishes discovery only when allowed, within the **same device block** as presence/rssi (HA Core enforces grouping; you provide correct discovery payload).

QUICK ASCII MAP
  Operator
     │
     ▼
┌─────────────┐     manages      ┌──────────────┐     runs containers      ┌───────────────┐
│  Supervisor │ ───────────────▶ │   Docker     │ ───────────────────────▶ │ Containers    │
│ (orchestr.) │                  │ (engine)     │                          │ (HA Core,     │
└─────┬───────┘                  └────┬─────────┘                          │  BB8, MQTT)  │
      │  API/Ingress                   │                                   └────┬──────────┘
      │                                │                                        │
      │                                │  network                               │
      ▼                                ▼                                        ▼
  Home Assistant Core  ◀────────────── MQTT Broker ◀────────────── BB8 add-on (publishes discovery/state)

If you want, I can tailor this to your exact deployment (HA OS vs Supervised) and annotate where your current scripts (P0 monitor, persistence audit, LED validator) plug into the flows. For now, you’re cleared to proceed with the approved operational steps—this map is the governance baseline for how components should (and do) interact.


HA BB8 add-on ⇄ Docker ⇄ Supervisor ⇄ Home Assistant Core — who does what (and how they interact)

LAYERED MENTAL MODEL (top → bottom)
1) Home Assistant Core (the app)
   - What it is: The Python application that provides automations, integrations, UI, entities, etc.
   - Where it runs: As a Docker container when using HA OS/Supervised, or as a bare Python process for HA Core installs.
   - How it sees BB8: Through integrations (notably MQTT). HA Core subscribes to MQTT Discovery topics; if BB8 publishes valid discovery/state, Core creates/updates entities.

2) Supervisor (the orchestrator)
   - What it is: A management service that *controls* add-ons and HA Core lifecycles, networking, updates, backups, ingress, and provides the Supervisor API.
   - Relationship to Docker: Uses the Docker Engine to pull images, create containers, set networks/volumes, start/stop, health-check them.
   - Relationship to Core: Exposes services (Ingress, Add-on management, Backups). Core can call some Supervisor endpoints; Supervisor can restart Core and add-ons.
   - Relationship to add-ons: Owns their lifecycle, passes configuration (exposed as `/data/options.json` inside the add-on), provides tokens (e.g., `SUPERVISOR_TOKEN`) and internal DNS (e.g., `supervisor`, `core-mosquitto`).

3) Docker (the runtime)
   - What it is: Container engine providing isolation, networking, volumes.
   - Role here: Runs **containers** for HA Core and each add-on (including BB8 and, commonly, the Mosquitto broker). Supervisor is “the boss,” Docker is “the machinery.”

4) Add-ons (containers managed by Supervisor) — BB8 is one of these
   - What they are: Prepackaged services that extend HA. Each add-on is a Docker container with a contract (config schema, exposed ports, logs, options).
   - BB8 add-on specifics:
     - Talks to the MQTT broker (often another add-on like Mosquitto) to publish **Home Assistant MQTT Discovery** and state.
     - May need host capabilities (e.g., BLE access) via extra privileges/mounts as configured by the Supervisor.
     - Reads config from `/data/options.json` and environment variables injected by Supervisor (e.g., `MQTT_BASE`, feature toggles).
     - Should NOT directly “write into” Home Assistant; instead, it *publishes* discovery/state to MQTT, which HA Core consumes.

5) Other key players (common in HA OS/Supervised)
   - Mosquitto add-on: The MQTT broker container. BB8 publishes to it; HA Core’s MQTT integration subscribes. Retained discovery/state here ensures **entity persistence** across restarts.
   - Ingress proxy (via Supervisor): Provides web UIs for add-ons through HA’s frontend without exposing extra ports.
   - OS Agent / DNS / Multicast helpers: System services used by Supervisor and add-ons for networking/service discovery (transparent to BB8 logic but relevant for connectivity).

COMMUNICATION PATHS (day-to-day flows)
- BB8 → MQTT Broker (publish):
  - Discovery topics under `homeassistant/...` (retained) and runtime state under `bb8/...`.
  - Your **single-owner** strategy relies on retained discovery + LWT teardown to avoid duplicates.
- HA Core MQTT Integration → MQTT Broker (subscribe):
  - Consumes discovery & state; creates/updates entities (presence, rssi, optional LED).
- Operator → Supervisor:
  - Start/stop/restart BB8 and broker add-ons; read logs; configure options; trigger snapshots.
- BB8 ↔ Supervisor API (optional):
  - Add-on can call Supervisor endpoints (using `SUPERVISOR_TOKEN`) for controlled operations (e.g., service discovery), but typical BB8 flows don’t need to modify HA Core directly.

LIFECYCLE & PERSISTENCE (why your acceptance tests matter)
- Restarts:
  - **Broker restart**: Retained discovery/state should allow HA Core to keep/restore entities quickly (your ≤10s SLA).
  - **HA Core restart**: On reconnect, Core re-subscribes and rehydrates entities from retained messages.
  - **Add-on restart**: BB8 should republish discovery/state idempotently; LWT ensures stale ownership is cleared.
- Storage:
  - Add-on writable space is `/data` inside the container (managed by Supervisor). Your reports/artifacts live under your chosen repo paths at build-time; runtime logs go to Supervisor’s logging, and any persistent add-on data lives in `/data`.

INSTALL FLAVORS (why you sometimes “lose” add-ons)
- **Home Assistant OS** or **Supervised**: You have Supervisor + Add-ons + Docker all working together (this is the model we’re using).
- **Home Assistant Container** (Core in Docker without Supervisor): **No add-ons**; BB8 would have to be run as a plain Docker container and manually wired to MQTT.
- **Home Assistant Core** (Python venv on a generic OS): No Supervisor, no add-ons; everything manual.

SECURITY & CONFIG HANDOFFS
- Config: Supervisor injects add-on options and env vars; **your defaults** (MQTT_BASE=bb8, REQUIRE_DEVICE_ECHO=1, PUBLISH_LED_DISCOVERY=0) are enforced at add-on runtime.
- Tokens/Network: Add-ons run on the Supervisor-managed Docker network(s); can reach the broker by DNS service name (e.g., `core-mosquitto`) or IP. Access is scoped; Ingress is reverse-proxied by Supervisor.

HOW THIS MAPS TO INT-HA-CONTROL
- **Entity persistence across broker restart**: Retained discovery/state on MQTT + HA Core re-subscribe → validated via your restart harness.
- **Zero duplicate discovery owners**: Idempotent retained publish + LWT teardown (Supervisor ensures BB8 lifecycle; BB8 ensures topic hygiene).
- **LED entity alignment**: BB8 publishes discovery only when allowed, within the **same device block** as presence/rssi (HA Core enforces grouping; you provide correct discovery payload).

QUICK ASCII MAP
  Operator
     │
     ▼
┌─────────────┐     manages      ┌──────────────┐     runs containers      ┌───────────────┐
│  Supervisor │ ───────────────▶ │   Docker     │ ───────────────────────▶ │ Containers    │
│ (orchestr.) │                  │ (engine)     │                          │ (HA Core,     │
└─────┬───────┘                  └────┬─────────┘                          │  BB8, MQTT)  │
      │  API/Ingress                   │                                   └────┬──────────┘
      │                                │                                        │
      │                                │  network                               │
      ▼                                ▼                                        ▼
  Home Assistant Core  ◀────────────── MQTT Broker ◀────────────── BB8 add-on (publishes discovery/state)

If you want, I can tailor this to your exact deployment (HA OS vs Supervised) and annotate where your current scripts (P0 monitor, persistence audit, LED validator) plug into the flows. For now, you’re cleared to proceed with the approved operational steps—this map is the governance baseline for how components should (and do) interact.

Deployment options for testing — clarity pass (no guesswork, binary steps)

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

```copilot
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

**No manual Docker work is needed right now.**

Why:
- You’re on the **Supervisor/HA OS** path. Supervisor is the orchestrator that talks to Docker **for you**. Your actions are via the **HA UI** (Rebuild/Restart) plus the repo scripts; no `docker …` commands are required.
- Our accepted plan is **operational-first**: restart add-ons via UI, run evidence scripts, collect PASS artifacts. All of that bypasses direct Docker usage.

When Docker would be needed (not in scope now):
- **HA Container install** (no Supervisor): you’d run/compose containers yourself.
- **Add-on base image changes** that fail a standard “Rebuild” from Supervisor (rare); still typically solvable via the UI.
- **Broker running outside Supervisor** and you choose to manage it with raw Docker commands (we’re not).

Proceed with the Supervisor UI actions and scripts as previously outlined. Once artifacts are PASS, we close INT-HA-CONTROL without ever touching Docker CLI.


```copilot
Execution (no Docker CLI):

1) Load env & prep
- `set -a && source .evidence.env && set +a`
- `python3 -m venv .venv && source .venv/bin/activate`
- `python -m pip install -U pip paho-mqtt`

2) Start P0 stability window (120 min)
- `bash reports/checkpoints/INT-HA-CONTROL/start_p0_monitoring.sh &`

3) Use **HA UI only** (
```