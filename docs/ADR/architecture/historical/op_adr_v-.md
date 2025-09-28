# ADR-000A: STP5 Telemetry Attestation Protocol (Observed)

**Session Evidence Source:** 
- Attestation run showing `TOKEN: TELEMETRY_ATTEST_OK` and artifacts paths; metrics excerpt with `echo_count: 762`, `echo_rtt_ms_p95: 129` and criteria booleans all `true`.  
- Runner invocations exporting `MQTT_HOST/PORT/USERNAME/PASSWORD/MQTT_BASE/WINDOW/COUNT` and executing `/config/domain/shell_commands/attest/attest_stp5_telemetry.sh`.

## Context
The add-on must prove telemetry health by emitting echo round-trip events over MQTT during a fixed window.

**Problem Statement:** Early attempts produced `FAIL: TELEMETRY_ATTEST` (no echoes).  
**Investigation Method:** Run STP5 shell runner; observe artifacts and broker/add-on logs; adjust echo responder service availability.  
**Evidence Gathered:** 
- Successful run emitted:
  - `SNAP: /config/reports/stp5/telemetry_snapshot.jsonl`
  - `METRICS: /config/reports/stp5/metrics_summary.json`
  - Token `TOKEN: TELEMETRY_ATTEST_OK`.
- Metrics JSON included:  
  ```json
  {"window_duration_sec":15.0,"echo_count":762,"echo_rtt_ms_p95":129,
   "criteria":{"window_ge_10s":true,"min_echoes_ge_3":true,"rtt_p95_le_250ms":true},
   "verdict":true}
Decision
Technical Choice: Use an attestation script that publishes N commands and subscribes to telemetry for a ≥10s window.
Command/Configuration:
Environment then runner:

bash
Copy code
export MQTT_HOST=127.0.0.1
export MQTT_PORT=1883
export MQTT_USERNAME=mqtt_bb8
export MQTT_PASSWORD=mqtt_bb8
export MQTT_BASE=bb8
export WINDOW=15
export COUNT=6   # also tested higher
/config/domain/shell_commands/attest/attest_stp5_telemetry.sh
Validation Results: Attestation returned TOKEN: TELEMETRY_ATTEST_OK and wrote the two artifacts.

Consequences
Positive
Clear, machine-verifiable PASS with artifacts.

P95 ≤ 250 ms confirmed (129 ms observed).

Negative
Prior failures observed when echo worker not running or broker auth failing.

Unknown/Untested
Long-duration stability of telemetry under degraded broker conditions.

Implementation Evidence
Commands Verified
bash
Copy code
# Broker auth check
mosquitto_sub -h 127.0.0.1 -p 1883 -u mqtt_bb8 -P mqtt_bb8 -t '$SYS/#' -C 1 -q 0
# Attestation runner (as above)
Configuration Discovered
/data/options.json contained:

json
Copy code
{
  "mqtt_broker":"192.168.0.129","mqtt_port":1883,
  "mqtt_username":"mqtt_bb8","mqtt_password":"mqtt_bb8",
  "mqtt_topic_prefix":"bb8","enable_bridge_telemetry":false,
  "enable_echo": true
}
Log Patterns Observed
vbnet
Copy code
Connected to MQTT broker with rc=0
Subscribed to bb8/echo/cmd
Gaps Requiring Further Investigation
Confirm echo responder enablement is explicitly controlled per test window to avoid unintended load.

Capture standardized QA JSON contract alongside artifacts for each run.

References
Commands Executed: Broker auth, attestation runner (as above).

Tests Performed: STP5 runs yielding PASS/FAIL with artifacts.

Session Sections: Attestation success block with token and metrics; broker/add-on logs showing connection/subscription.

Extraction Date: 2025-08-29
Session ID/Reference: SESS-8F2C7C94
Evidence Quality: Complete

ADR-000B: Add-on Mode Switching & Build Behavior (LOCAL_DEV vs PUBLISH)
Session Evidence Source:

Mode detection command returning MODE: LOCAL_DEV:

bash
Copy code
CFG=/addons/local/beep_boop_bb8/config.yaml
sed 's/#.*$//' "$CFG" | grep -Eq '^[[:space:]]*image:[[:space:]]*' && echo "MODE: PUBLISH" || echo "MODE: LOCAL_DEV"
Supervisor errors:

Error: Can't rebuild a image based add-on

Error: Image local/aarch64-addon-beep_boop_bb8:2025.8.21.4 does not exist…

Successful runtime after commenting image: and rebuilding, with build: true.

Context
Supervisor treats add-ons with image: as PUBLISH (pull image); without image:, it builds from local context.

Problem Statement: Rebuilds failed in PUBLISH mode without a published image; LOCAL_DEV required for local changes.
Investigation Method: Grep-based mode detection, ha addons reload/rebuild/start, inspect ha addons info fields.
Evidence Gathered: build: true observed for LOCAL_DEV; rebuild error when image: present.

Decision
Technical Choice: Use LOCAL_DEV (no image:) during development; only set image: for published images.
Command/Configuration:
config.yaml (excerpt verified):

yaml
Copy code
version: "2025.8.21.4"
# image: "ghcr.io/your-org/ha-bb8-{arch}"   # commented for LOCAL_DEV
build:
  dockerfile: Dockerfile
  args:
    BUILD_FROM: "ghcr.io/home-assistant/{arch}-base-debian:bookworm"
Validation Results: ha addons rebuild succeeded in LOCAL_DEV; PUBLISH rebuild refused or failed if image was missing.

Consequences
Positive
Deterministic local builds; clear toggle via presence/absence of image:.

Negative
PUBLISH requires registry push before Supervisor can start.

Unknown/Untested
None.

Implementation Evidence
Commands Verified
bash
Copy code
ha addons reload
ha addons rebuild local_beep_boop_bb8
ha addons start  local_beep_boop_bb8
ha addons info local_beep_boop_bb8 | grep -E 'build:|state:|version:'
Log Patterns Observed
vbnet
Copy code
Error: Can't rebuild a image based add-on
Error: Image local/aarch64-addon-beep_boop_bb8:2025.8.21.4 does not exist…
Gaps Requiring Further Investigation
None; behavior consistent.

References
config.yaml snapshots; Supervisor CLI outputs.

Extraction Date: 2025-08-29
Session ID/Reference: SESS-8F2C7C94
Evidence Quality: Complete

ADR-000C: Python Runtime & Dockerfile Base (Debian + /opt/venv)
Session Evidence Source:

Build failure on Alpine command: apk: command not found when base was Debian.

Dockerfile updates: apt-get install python3/python3-venv; create venv /opt/venv; install with /opt/venv/bin/pip.

Runtime checks:

Early: /usr/bin/python

Later: PY=/opt/venv/bin/python and /opt/venv/bin/python printed.

Context
Base image switched to Debian; Alpine apk not available.

Problem Statement: Mixed package managers caused build failure; system Python used instead of venv.
Investigation Method: Build logs; container exec printing sys.executable; review of Dockerfile and run.sh.
Evidence Gathered:

Error snippet:

pgsql
Copy code
RUN apk add --no-cache … 
/bin/bash: line 1: apk: command not found
Success after switching to apt and venv; container echo: PY=/opt/venv/bin/python.

Decision
Technical Choice: Debian base only; create and use /opt/venv.
Command/Configuration: Dockerfile (observed structure):

dockerfile
Copy code
ARG BUILD_FROM=ghcr.io/home-assistant/aarch64-base-debian:bookworm
FROM ${BUILD_FROM}

RUN apt-get update && apt-get install -y --no-install-recommends \
      python3 python3-venv python3-pip ca-certificates \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/app
COPY bb8_core/ /usr/src/app/bb8_core/
COPY app/      /usr/src/app/app/
COPY services.d/ /etc/services.d/
COPY run.sh    /usr/src/app/run.sh
COPY requirements.txt* /usr/src/app/

RUN python3 -m venv /opt/venv \
 && /opt/venv/bin/pip install -U pip setuptools wheel \
 && if [ -f /usr/src/app/requirements.txt ]; then /opt/venv/bin/pip install -r /usr/src/app/requirements.txt; fi \
 && chmod +x /usr/src/app/run.sh
run.sh launches "$VIRTUAL_ENV/bin/python" -m bb8_core.main.

Validation Results: Venv path reported; module imports succeeded (TOKEN: MODULE_OK).

Consequences
Positive
Reproducible builds; isolated Python deps.

Negative
None observed.

Unknown/Untested
None.

Implementation Evidence
Commands Verified
bash
Copy code
docker exec "$CID" bash -lc 'python -c "import sys; print(sys.executable)"'
# Output before: /usr/bin/python ; after: /opt/venv/bin/python
Log Patterns Observed
swift
Copy code
PY=/opt/venv/bin/python
/opt/venv/bin/python
Gaps Requiring Further Investigation
Migrate paho to newer callback API to remove deprecation warning.

References
Build log error; Dockerfile content; container exec outputs.

Extraction Date: 2025-08-29
Session ID/Reference: SESS-8F2C7C94
Evidence Quality: Complete

ADR-000D: Process Supervision & Restart Loop Fix
Session Evidence Source:

Repeated bursts:

scss
Copy code
[BB-8] Starting bridge controller… (ENABLE_BRIDGE_TELEMETRY=0)
bb8_core.main loaded
After fix:

csharp
Copy code
[BB-8] RUNLOOP start (ENABLE_BRIDGE_TELEMETRY=0)
[BB-8] CHILD_EXIT rc=0
services.d/ble_bridge/run exec’d run.sh; run.sh became a blocking wrapper supervising controller.

Context
s6 restarts the service when the process exits; initial main exited quickly, causing loop.

Problem Statement: Controller exited; s6 restarted rapidly.
Investigation Method: Log pattern analysis; verifying importability; changing wrapper behavior.
Evidence Gathered: Transition from frequent starts to single RUNLOOP start with wrapper holding process.

Decision
Technical Choice: Make run.sh a blocking supervisor that execs the controller (long-running), not a short task.
Command/Configuration:

services.d/ble_bridge/run:

bash
Copy code
#!/usr/bin/with-contenv bash
set -euo pipefail
cd /usr/src/app
exec /bin/bash /usr/src/app/run.sh
run.sh loads options, resolves venv python, and exec "$PY" -m bb8_core.main (post-fix wrapper blocks).

Validation Results: No rapid restarts; saw RUNLOOP start and managed CHILD_EXIT rc=0.

Consequences
Positive
Stable, contract-compliant single start with supervisor holding the service.

Negative
None observed.

Unknown/Untested
None.

Implementation Evidence
Log Patterns Observed
csharp
Copy code
bb8_core.main loaded
[BB-8] Starting bridge controller…
# after fix:
[BB-8] RUNLOOP start (ENABLE_BRIDGE_TELEMETRY=0)
[BB-8] CHILD_EXIT rc=0
Gaps Requiring Further Investigation
None.

References
Service and wrapper scripts; logs before/after.

Extraction Date: 2025-08-29
Session ID/Reference: SESS-8F2C7C94
Evidence Quality: Complete

ADR-000E: MQTT Integration & Echo Responder Behavior
Session Evidence Source:

/data/options.json excerpt shows broker 192.168.0.129, user/pass mqtt_bb8, prefix bb8.

Broker auth test:

nginx
Copy code
mosquitto_sub -h 127.0.0.1 -p 1883 -u mqtt_bb8 -P mqtt_bb8 -t '$SYS/#' -C 1 -q 0
TOKEN: BROKER_AUTH_OK
Add-on logs:

vbnet
Copy code
Connected to MQTT broker with rc=0
Subscribed to bb8/echo/cmd
Echo responder module present (TOKEN:ECHO_RESPONDER_PRESENT).

Context
Echo responder publishes ACK/STATE/telemetry on command.

Problem Statement: Early attestation windows saw zero echoes when responder not active or broker rejected auth; later resolved.
Investigation Method: Inspect options/env, broker auth checks, add-on logs, run attestation.
Evidence Gathered: Successful connection/subscription + attestation artifacts.

Decision
Technical Choice: Use responder that:

Subscribes to bb8/echo/cmd

Publishes to bb8/echo/ack, bb8/echo/state, bb8/telemetry/echo_roundtrip

Uses paho-mqtt CallbackAPIVersion.VERSION1 (deprecation warning observed)

Configuration Discovered (runtime options):

json
Copy code
{
  "mqtt_broker":"192.168.0.129","mqtt_port":1883,
  "mqtt_username":"mqtt_bb8","mqtt_password":"mqtt_bb8",
  "mqtt_topic_prefix":"bb8","enable_echo": true
}
Validation Results: Attestation PASS with high echo_count.

Consequences
Positive
Confirmed end-to-end MQTT path; telemetry emitted.

Negative
Deprecation warning:

vbnet
Copy code
DeprecationWarning: Callback API version 1 is deprecated
Unknown/Untested
Migration to new paho API not done in this session.

Implementation Evidence
Commands Verified
bash
Copy code
mosquitto_sub -h 127.0.0.1 -p 1883 -u mqtt_bb8 -P mqtt_bb8 -t '$SYS/#' -C 1 -q 0
ha addons logs local_beep_boop_bb8 | grep -E "Connected to MQTT broker|Subscribed to .*/echo/cmd"
Log Patterns Observed
vbnet
Copy code
Connected to MQTT broker with rc=0
Subscribed to bb8/echo/cmd
Gaps Requiring Further Investigation
Update to new paho callback API.

References
options.json snapshot; broker/add-on logs; attestation result.

Extraction Date: 2025-08-29
Session ID/Reference: SESS-8F2C7C94
Evidence Quality: Complete

ADR-000F: OOM Incidents & Echo Load Hardening
Session Evidence Source:

Photo/screen showing repeated Out of memory: Killed process … lines.

Subsequent containment instructions executed (stop heavy add-ons; stop BB-8) and observation that memory stabilized.

Echo responder implementation shows concurrency guard:

python
Copy code
MAX_INFLIGHT = int(os.environ.get("ECHO_MAX_INFLIGHT", "16"))
_inflight = threading.BoundedSemaphore(MAX_INFLIGHT)
MIN_INTERVAL_MS = float(os.environ.get("ECHO_MIN_INTERVAL_MS", "0"))
options contained "enable_echo": true at one point; disabling echo during recovery was advised and used for stable run windows.

Context
High echo rates or unstable broker can trigger excess work and memory pressure.

Problem Statement: System hit kernel OOM while add-on active; suspect workload spikes from echo handling.
Investigation Method: Kernel OOM messages, service stop sequence, echo gating; code inspection of responder limits.
Evidence Gathered: OOM photo; responder has inflight/rate knobs; stability improved once load contained.

Decision
Technical Choice: Operate with echo disabled by default, enable only for attestation windows; rely on bounded inflight and optional throttle.
Command/Configuration:

Gate via options enable_echo: false (when not testing).

Use envs ECHO_MAX_INFLIGHT and ECHO_MIN_INTERVAL_MS to bound load.

Service present under services.d/echo_responder/; presence token observed (TOKEN:ECHO_RESPONDER_SERVICE).

Validation Results: After containment and proper enablement window, attestation passed; no immediate OOM observed during short windows.

Consequences
Positive
Predictable load; safer steady state.

Negative
Manual enable/disable step for tests.

Unknown/Untested
Long-term memory profiling with echo enabled continuously.

Implementation Evidence
Log Patterns Observed
arduino
Copy code
Out of memory: Killed process …  (kernel)
Configuration Discovered
Responder code snippet with BoundedSemaphore and interval throttle.

Gaps Requiring Further Investigation
Persistent down file for service not explicitly confirmed in build context.

Automating post-attestation disablement in ops scripts.

References
OOM screenshot; responder code excerpt; options snippets; operational results.

Extraction Date: 2025-08-29
Session ID/Reference: SESS-8F2C7C94
Evidence Quality: Partial

markdown
Copy code

**Final Validation Checklist (met):**
- Every technical detail above traces to session evidence.
- Commands and configurations match observed snippets.
- Gaps are explicitly listed.
- No invented procedures included.
::contentReference[oaicite:0]{index=0}
You've reached the maximum length for this conversation, but you can keep talking by starting a new chat.


Retry