## Supervisor-only Operations
- Control plane: single (run.sh). `s6` echo_responder is DOWN by design.
- Observability: Supervisor logs only (`ha addons logs`). No docker exec required.
- Heartbeats: Python writes `/tmp/bb8_heartbeat_main|echo`; run.sh prints `HEALTH_SUMMARY` with ages every 15s.
- Restart policy: supervised in run.sh; `RESTART_LIMIT=0` (unlimited). Creating `/tmp/bb8_restart_disabled` halts restarts (requires container shell; not used in Supervisor-only ops).
# Operations Overview — HA-BB8 Add-on

## Runtime supervision & DIAG
The add-on is supervised by `run.sh` (single control-plane). It logs:
- `RUNLOOP attempt #N`
- `Started bb8_core.main PID=…`
- `Started bb8_core.echo_responder PID=…`
- `Child exited: dead=… exit_code=…`

Heartbeats:
- `/tmp/bb8_heartbeat_main`
- `/tmp/bb8_heartbeat_echo`

## Daily health check (one-liners)
```
CID=$(docker ps --filter "name=addon_local_beep_boop_bb8" --format '{{.ID}}' | head -n1)
LOGF=/data/reports/ha_bb8_addon.log
docker exec "$CID" sh -lc '
  echo "--- DIAG tail ---"; tail -n 200 '"$LOGF"' | sed -n "/RUNLOOP attempt/I p; /Child exited/I p; /Started bb8_core\\./I p" | tail -n 40
  echo "--- heartbeats ---"
  for f in /tmp/bb8_heartbeat_main /tmp/bb8_heartbeat_echo; do
    t1=$(tail -1 "$f"); sleep 6; t2=$(tail -1 "$f"); awk -v n="$f" -v a="$t1" -v b="$t2" '"'"'BEGIN{printf "%s drift=%.2fs\n", n, (b-a)}'"'"'
  done
'
```

## Restart/backoff policy
- Default `RESTART_BACKOFF=5s`, `RESTART_LIMIT=0` (unlimited).  
- Set `/tmp/bb8_restart_disabled` to halt auto-respawn for investigations.

# Operations Overview — HA-BB8 Add-on

## Runtime supervision & DIAG
The add-on is supervised by `run.sh` (single control-plane). It logs:
- `RUNLOOP attempt #N`
- `Started bb8_core.main PID=…`
- `Started bb8_core.echo_responder PID=…`
- `Child exited: dead=… exit_code=…`

Heartbeats:
- `/tmp/bb8_heartbeat_main`
- `/tmp/bb8_heartbeat_echo`

## Daily health check (one-liners)
```
CID=$(docker ps --filter "name=addon_local_beep_boop_bb8" --format '{{.ID}}' | head -n1)
LOGF=/data/reports/ha_bb8_addon.log
docker exec "$CID" sh -lc '
  echo "--- DIAG tail ---"; tail -n 200 '"$LOGF"' | sed -n "/RUNLOOP attempt/I p; /Child exited/I p; /Started bb8_core\\./I p" | tail -n 40
  echo "--- heartbeats ---"
  for f in /tmp/bb8_heartbeat_main /tmp/bb8_heartbeat_echo; do
    t1=$(tail -1 "$f"); sleep 6; t2=$(tail -1 "$f"); awk -v n="$f" -v a="$t1" -v b="$t2" '"'"'BEGIN{printf "%s drift=%.2fs\n", n, (b-a)}'"'"'
  done
'
```

## Restart/backoff policy
- Default `RESTART_BACKOFF=5s`, `RESTART_LIMIT=0` (unlimited).  
- Set `/tmp/bb8_restart_disabled` to halt auto-respawn for investigations.

# OPERATIONS_OVERVIEW — HA‑BB8 (Hardened)

> **Machine‑friendly handbook** for structure, flows, tokens, and contracts. Optimized for parsing by CI, GitHub Copilot, and LLM assistants.
>
> Baseline Tag: `v2025.8.21.1`
> Project: **BB‑8 Bridge (HA‑BB8)**
> Add‑on Slug: `beep_boop_bb8`
> Runtime Add‑on Path (HA OS): `/addons/local/beep_boop_bb8`
> Current runtime mode: **PUBLISH** @ **2025.8.21.4**
---

## 0. Contents (anchors)

* [Topology & Layout](#1-topology--layout)
* [Roles & Originators](#2-roles--originators)
* [Governance Tokens](#3-governance-tokens)
* [Output Contracts (JSON)](#4-output-contracts-json)
* [Process Flows (A→F)](#5-process-flows-a→f)
* [Versioning & Publish/Deploy](#6-versioning--publishdeploy)
* [Telemetry (STP5)](#7-telemetry-stp5)
* [Troubleshooting Playbook](#8-troubleshooting-playbook)
* [Operational Checklists](#9-operational-checklists)
* [POSIX‑only Helpers (HA‑OS compatible)](#10-posixonly-helpers-haos-compatible)
* [Assumptions & Environment Matrix](#11-assumptions--environment-matrix)

---

## 1. Topology & Layout

> **Dual‑clone (ADR‑0001)** — All Git operations happen in the **workspace**. The HA runtime holds a **plain build context** (explicitly excludes `.git` and workspace-only directories such as `.github`, `docs`, `ops`, `reports`; no nested git) used by Supervisor to build a local image.

```text
WORKSPACE (developer machine)
├─ addon/                 # shipped subtree (container context)
│  ├─ bb8_core/           # runtime code
│  ├─ config.yaml         # add-on manifest (has version + build + image)
│  ├─ Dockerfile          # container build recipe (Debian base only)
│  ├─ run.sh              # s6 entry wrapper (invoked by services.d)
│  └─ tests/              # test suite (pytest)
├─ ops/                   # scripts & runners (not shipped)
├─ reports/               # evidence sink (QA, telemetry, receipts)
├─ scripts/               # wrappers (verify/deploy)
└─ .github/               # CI workflows

HA RUNTIME (Home Assistant OS)
└─ /addons/local/beep_boop_bb8/   # plain folder (config.yaml + Dockerfile + code), no .git
```

# 12. End-to-End Operational Workflow (Machine-Friendly)

## Canonical Deployment & Governance (2025.8.21+)

- **Deployment is performed via SSH and rsync only.** No git required on runtime; all git operations are workspace-only.
- **Canonical runtime path:** `/addons/local/beep_boop_bb8` (Home Assistant OS)
- **Governance tokens** are emitted in operational receipts for CI and attestation:
  - `SUBTREE_PUBLISH_OK`, `CLEAN_RUNTIME_OK`, `DEPLOY_OK`, `VERIFY_OK`, `RUNTIME_TOPOLOGY_OK` (see `reports/deploy_receipt.txt`)
- **Release workflow:**
  - Build and publish from workspace (subtree split/push)
  - Rsync to runtime (no .git, no workspace-only dirs)
  - Supervisor API restart and health check
  - All steps emit machine-readable tokens for governance and CI

## Operational Health & Attestation

- All operational steps are validated by emitted tokens and receipts.
- Health checks and attestation scripts (`ops/run_strict_attestation.sh`) produce machine-readable evidence and contracts.
- See `reports/qa_report_contract_v1.json`, `reports/patch_bundle_contract_v1.json`, and `reports/evidence_manifest.json` for attestation outputs.

## Troubleshooting & Remediation

- All errors and status are logged with explicit tokens and receipts for CI/governance parsing.
- See `reports/deploy_receipt.txt` and `reports/qa_report_contract_v1.json` for step-by-step status and health.

# ENV: LOCAL_DEV (workspace)
**Key rules**

* addon/ is **not** a git repo; publish to a separate add‑on repository via **`git subtree`**.
* _(Enforced by CI guard — see [Flow E: Structure guard](#flow-e--ci-token-gate-pr-time))_
```
## Step 1: Workspace Hygiene & Commit
**Key rules:**
* addon/ is **not** a git repo; publish to a separate add‑on repository via **`git subtree`**.
* _(Enforced by CI guard — see [Flow E: Structure guard](#flow-e--ci-token-gate-pr-time))_
```sh
# ENV: LOCAL_DEV (workspace)
find addon/ -type d -name .git && echo "ERROR: .git found in addon/" || echo "OK: no .git in addon/"
pytest -q -W error --maxfail=1 --cov=bb8_core --cov-report=term:skip-covered
```

## Step 2: Subtree Publish (ADR-0001)
# ENV: LOCAL_DEV (workspace)
* **Canonical run chain:** `s6` → `/etc/services.d/ble_bridge/run` → `/usr/src/app/run.sh` → `python -m bb8_core.main`.
  - The Dockerfile copies the entire `services.d/` directory, which must contain the `ble_bridge` subdirectory and its `run` file (`services.d/ble_bridge/run`), ensuring `/etc/services.d/ble_bridge/run` exists in the container.
* **Canonical run chain:** `s6` → `/etc/services.d/ble_bridge/run` → `/usr/src/app/run.sh` → `python -m bb8_core.main`.
```
**Canonical run chain:** `s6` → `/etc/services.d/ble_bridge/run` → `/usr/src/app/run.sh` → `python -m bb8_core.main`.
The Dockerfile copies the entire `services.d/` directory, which must contain the `ble_bridge` subdirectory and its `run` file (`services.d/ble_bridge/run`), ensuring `/etc/services.d/ble_bridge/run` exists in the container.
```sh
# ENV: LOCAL_DEV (workspace)
ORG=<your-org>
git subtree split -P addon -b __addon_pub_tmp
git push -f git@github.com:$ORG/ha-bb8-addon.git __addon_pub_tmp:refs/heads/main
git branch -D __addon_pub_tmp
echo 'TOKEN: SUBTREE_PUBLISH_OK' >> reports/publish_receipt.txt
```

## Step 3: Sync to HA Runtime (LOCAL_DEV)
# ENV: LOCAL_DEV (workspace)
```sh
rsync -av --delete addon/ babylon-babes@homeassistant:/data/addons/local/beep_boop_bb8/
```

## Step 4: Build Context & .git Status
# ENV: HA Runtime
```sh
ssh babylon-babes@homeassistant "ls -lah /addons/local/beep_boop_bb8"
ssh babylon-babes@homeassistant "(test -f /addons/local/beep_boop_bb8/config.yaml && echo OK) || echo MISSING-config"
(test -f /addons/local/beep_boop_bb8/Dockerfile && echo OK) || echo MISSING-dockerfile
find /addons/local/beep_boop_bb8 -type d -name .git && echo "ERROR: .git found in runtime" || echo "OK: no .git in runtime"
```

## Step 5: Rebuild & Start Add-on
# ENV: HA Runtime
```sh
ssh babylon-babes@homeassistant "ha addons reload"
ssh babylon-babes@homeassistant "ha addons rebuild local_beep_boop_bb8"
ssh babylon-babes@homeassistant "ha addons start local_beep_boop_bb8"
```

## Step 6: Sanity Checks (Operational Health)

# ENV: HA Runtime
```sh
grep -E '^TOKEN:' /config/reports/deploy_receipt.txt
```

## 2. Roles & Originators

| -------------- | ------------------------------- | --------------------------------------------- |
| **Strategos**  | Governance & acceptance gates   | Delta contracts; binary acceptance; CI policy |
| **Pythagoras** | Code & QA execution             | Patch bundles; tests; QA/evidence contracts   |
| **Copilot**    | Implementation surface (assist) | Applied diffs; scripted runs                  |
| **Supervisor** | Runtime container lifecycle     | Build logs; start/stop; error diagnostics     |
**Machine tags**: `ORIGINATOR: Strategos` / `ORIGINATOR: Pythagoras` appear in receipts for attribution.

## 3. Governance Tokens

## Step 7: Manual Functional Test (MQTT Event Handling)

> Tokens are single‑line markers emitted in receipts/logs for **binary** step validation.

**Machine tags:** `ORIGINATOR: Strategos` / `ORIGINATOR: Pythagoras` appear in receipts for attribution.


## Step 8: Monitor Resource Usage

* `WS_READY` — workspace prepared (structure, tools, wrappers)
* `STRUCTURE_OK` — ADR‑0001 layout valid; add‑on subtree clean
* `SUBTREE_PUBLISH_OK` — add‑on subtree pushed to remote

## Step 9: Attestation & Evidence

* `CLEAN_RUNTIME_OK` — runtime folder synchronized (no stray files, no .git)
* `DEPLOY_OK` — Supervisor rebuilt image successfully


## Step 10: Troubleshooting & Remediation

* `VERIFY_OK` — runtime health checks passed
* `RUNTIME_TOPOLOGY_OK` — runtime path & image/tag aligned


## Step 11: Final Verification

```
| Token/Gate              | Meaning/Trigger                                 | Section/Flow(s) Emitted/Validated                |
|-------------------------|-------------------------------------------------|--------------------------------------------------|
| STRUCTURE_OK            | ADR-0001 layout valid, add-on subtree clean     | Flow E (CI Token Gate), Checklist 9.5            |
| SUBTREE_PUBLISH_OK      | Add-on subtree pushed to remote                 | Flow B (Publish Subtree), Checklist 9.2          |
| CLEAN_RUNTIME_OK        | Runtime folder synchronized, no stray files     | Flow C (Deploy), Checklist 9.3                   |
| DEPLOY_OK               | Supervisor rebuilt image successfully           | Flow C (Deploy), Checklist 9.3                   |
| VERIFY_OK               | Runtime health checks passed                    | Flow C (Deploy), Flow E (CI), Checklist 9.3, 9.5 |
| RUNTIME_TOPOLOGY_OK     | Runtime path & image/tag aligned                | Flow C (Deploy), Section 6 (Versioning)          |
| TOOLS_ALLOWED           | tools/ allowed in add-on (CRTP)                 | Flow E (CI Token Gate)                           |
| SCRIPTS_ALLOWED         | scripts/ allowed in add-on (CRTP)               | Flow E (CI Token Gate)                           |
```
* `RUNTIME_TOPOLOGY_OK` — runtime path & image/tag aligned

---

**Greppable form:**

```
TOKEN: WS_READY
TOKEN: STRUCTURE_OK
TOKEN: SUBTREE_PUBLISH_OK
TOKEN: CLEAN_RUNTIME_OK
TOKEN: DEPLOY_OK
TOKEN: VERIFY_OK
TOKEN: RUNTIME_TOPOLOGY_OK
```

---
ARG BUILD_FROM=ghcr.io/home-assistant/aarch64-base-debian:bookworm

## 4. Output Contracts (JSON)

> Contracts are machine‑readable summaries placed under `reports/`.

### 4.1 QA Report
..other required packages... \

```json
{
  "verdict": "PASS",
  "coverage": 82.0,

  "tests": {"total": 54, "failures": 0, "errors": 0, "skipped": 0},
  "tokens": ["WS_READY","STRUCTURE_OK","DEPLOY_OK","VERIFY_OK"],
  "echoes": {"strict_scalar_retain_false": true, "evidence_file": "ha_mqtt_trace_snapshot.json", "present": true},
  "discovery": {"led_enabled_by_default": true, "file": "ha_discovery_dump.json", "present": true},
  "telemetry": {"snapshot": "telemetry_snapshot.jsonl", "metrics": "metrics_summary.json"},
  "head_commit": "<gitsha>",
  "tag": "v2025.8.21.1",
  "criteria": {
    "coverage_ge_80": true,
    "no_test_failures": true,
    "mqtt_trace_present": true,
    "discovery_dump_present": true,
    "tokens_ok": true
  },
  "ts": 1692810834
}
```

### 4.2 Patch Bundle

Minimal example; additional files may be present

```json
{
  "contract": "patch_bundle_contract_v1",
  "head_target": "<gitsha>",
  "tag": "v2025.8.21.1",
  "target_files": ["addon/bb8_core/ble_link.py","addon/bb8_core/mqtt_probe.py"], 
  "diffs_applied": ["BLE loop thread + exponential backoff","Probe instrumentation"],
  "tests_affected": ["addon/tests"],
  "coverage_delta": 0.3,
  "rollback_notes": "Revert files or reset to tag"
}
```

### 4.3 Evidence Manifest

```json
{
  "manifest": "evidence_manifest.json",
  "strict": true,
  "head_commit": "<gitsha>",
  "tag": "v2025.8.21.1",
  "generated_at": "2025-08-23T20:53:54+01:00",
  "artifacts": [
    {"path": "reports/deploy_receipt.txt", "sha256": "<…>"},
    {"path": "reports/verify_receipt.txt", "sha256": "<…>"},
    {"path": "reports/tokens.json", "sha256": "<…>"},
    {"path": "reports/coverage.json", "sha256": "<…>"},
    {"path": "reports/pytest-report.xml", "sha256": "<…>"},
    {"path": "reports/ha_mqtt_trace_snapshot.json", "sha256": "<…>"},
    {"path": "reports/ha_discovery_dump.json", "sha256": "<…>"},
    {"path": "reports/telemetry_snapshot.jsonl", "sha256": "<…>"},
    {"path": "reports/metrics_summary.json", "sha256": "<…>"},
    {"path": "reports/qa_report_contract_v1.json", "sha256": "<…>"},
    {"path": "reports/patch_bundle_contract_v1.json", "sha256": "<…>"}
  ]
}
```
> **Note:** The `"sha256"` values in the `"artifacts"` array above are placeholders (`"<…>"`). In actual evidence manifests, these should be replaced with the real SHA-256 hashes of each artifact file.


---

## 5. Process Flows (A→F)

### Flow A — Local Development & Testing (Originator: Pythagoras)

```bash
# Create/activate venv, then:
pip install -e addon
pip install -r addon/requirements-dev.txt

# Run tests with warnings-as-errors (except paho v1 deprecation in pytest.ini)
pytest -q -W error --maxfail=1 \
  --cov=bb8_core --cov-report=term:skip-covered
```

**Emit:** coverage + JUnit under `reports/` (when using runners).
**Gate:** No warnings except explicitly suppressed policy lines.
**Token:** `WS_READY` when dev toolchain validated.

---

### Flow B — Publish the Add‑on Subtree (Originator: Strategos)

```bash
# From workspace root
# The following command creates a temporary branch containing only the history of the addon/ subtree,
# Replace <org> with your actual GitHub organization or username
git push -f git@github.com:<org>/ha-bb8-addon.git __addon_pub_tmp:refs/heads/main
git subtree split -P addon -b __addon_pub_tmp
git branch -D __addon_pub_tmp

echo 'TOKEN: SUBTREE_PUBLISH_OK' >> reports/publish_receipt.txt
echo 'TOKEN: SUBTREE_PUBLISH_OK' | tee -a reports/publish_receipt.txt
```

**Emit:** `reports/publish_receipt.txt` with `SUBTREE_PUBLISH_OK`.

---

### Flow C — Deploy to HA Runtime (Originator: Strategos → Exec: Pythagoras)

**Option 1: rsync to local add‑ons**

```bash
# On workstation (adjust path or use Samba). Ensure write perms.
rsync -av --delete --exclude '.DS_Store' addon/ /Volumes/addons/local/beep_boop_bb8/

# On HA box
ssh babylon-babes@homeassistant "ha addons reload"
ssh babylon-babes@homeassistant "ha addons rebuild local_beep_boop_bb8"
# See [Versioning & Publish/Deploy](#6-versioning--publishdeploy) for details on correct usage of `image:` and `build:` in `config.yaml`.
ha addons start  local_beep_boop_bb8

mkdir -p /config/reports
echo 'TOKEN: CLEAN_RUNTIME_OK' >> /config/reports/deploy_receipt.txt
echo 'TOKEN: DEPLOY_OK'         >> /config/reports/deploy_receipt.txt
echo 'TOKEN: VERIFY_OK'         >> /config/reports/deploy_receipt.txt
```

**Option 2: runtime clone reset** (if your deploy path uses a clone)

> **Warning:** This will overwrite any local changes in the runtime repo. Ensure you have committed or backed up any important modifications before running these commands.

```bash
# In runtime repo
git fetch --all --prune
git checkout -B main origin/main
git reset --hard origin/main
ssh babylon-babes@homeassistant "ha addons rebuild local_beep_boop_bb8"
```

**Gate (mode‑aware):** `config.yaml` has `build:`; `image:` is either `local/{arch}-addon-beep_boop_bb8` (LOCAL_DEV) **or** a registry URL with a published tag (PUBLISH).
**Emit:** `deploy_receipt.txt` with `CLEAN_RUNTIME_OK`, `DEPLOY_OK`, `VERIFY_OK`.

---

### Flow D — Strict Attestation (STP4) & Binary Acceptance (Originator: Strategos)

```bash
# One-shot runner (example path)
bash ops/run_strict_attestation.sh
```

**Produces**

* `qa_report_contract_v1.json` (**PASS/FAIL**)
* `patch_bundle_contract_v1.json`
* `evidence_manifest.json`
* Echo & discovery artifacts: `ha_mqtt_trace_snapshot.json`, `ha_discovery_dump.json`

**PASS criteria**

* coverage ≥ **80%**
* **No asyncio event‑loop warnings**
* Device‑originated echoes (retain=false)
* LED discovery present; **no dupes**; unique_id stable
* Tokens present: `STRUCTURE_OK`, `DEPLOY_OK`, `VERIFY_OK`, `WS_READY`

---


### Flow E — CI Token Gate (PR time)

```yaml
# .github/workflows/repo-guards.yml (excerpt, CRTP-hardened)
- name: Structure guard (ADR-0001 + CRTP)
  run: |
    set -euo pipefail
    test -d addon || (echo "addon/ missing" && exit 2)
    if [ -d addon/.git ]; then echo "addon is a repo (forbidden)"; exit 3; fi

    # Forbidden workspace-only dirs (always)
    for d in .github docs ops reports; do
      if [ -e "addon/$d" ]; then echo "DRIFT:forbidden_in_addon:$d"; exit 4; fi
    done

    # CRTP: tools/ allowed only if referenced in Dockerfile or marker present
    if [ -d addon/tools ]; then
      if ! grep -Ei '(COPY|ADD|RUN|ENTRYPOINT|CMD).*tools/' addon/Dockerfile >/dev/null 2>&1 
         && [ ! -f addon/.allow_runtime_tools ]; then
        echo "DRIFT:tools_unreferenced_in_dockerfile"; exit 5
      else
        echo "TOKEN: TOOLS_ALLOWED"
      fi
    fi

    # CRTP: scripts/ allowed only if referenced in Dockerfile or marker present
    if [ -d addon/scripts ]; then
      if ! grep -Ei '(COPY|ADD|RUN|ENTRYPOINT|CMD).*scripts/' addon/Dockerfile >/dev/null 2>&1 
         && [ ! -f addon/.allow_runtime_scripts ]; then
        echo "DRIFT:scripts_unreferenced_in_dockerfile"; exit 6
      else
        echo "TOKEN: SCRIPTS_ALLOWED"
      fi
    fi

    # Required build context
    test -f addon/config.yaml || (echo "DRIFT:missing_config_yaml" && exit 7)
    test -f addon/Dockerfile  || (echo "DRIFT:missing_Dockerfile" && exit 8)
    # Mode-aware guard:
    if grep -Eq '^[[:space:]]*image:[[:space:]]*' addon/config.yaml; then
      echo "MODE: PUBLISH"
      grep -Eq '^[[:space:]]*version:[[:space:]]*' addon/config.yaml || (echo "DRIFT:version_missing_in_publish_mode" && exit 9)
    else
      echo "MODE: LOCAL_DEV"
      test -f addon/Dockerfile || (echo "DRIFT:dockerfile_missing_in_local_dev" && exit 10)
      echo "TOKEN: DEV_LOCAL_BUILD_FORCED"
    fi

    echo "TOKEN: STRUCTURE_OK"
- name: Pytest (warnings as errors)
  run: pytest -q -W error --maxfail=1 --cov=bb8_core --cov-report=term-missing
- name: Emit CI tokens
  run: echo '{"tokens":["STRUCTURE_OK","VERIFY_OK","TOOLS_ALLOWED","SCRIPTS_ALLOWED"]}' > tokens.ci.json
```

**Note:** CI intentionally **does not** emit `DEPLOY_OK`.

---

### Flow F — Local Add‑on Version Bump & Rebuild

```bash
# Edit runtime file on HA box
sed -i 's/^version:.*/version: "2025.8.21.4"/' /addons/local/beep_boop_bb8/config.yaml
ssh babylon-babes@homeassistant "ha addons reload"
ssh babylon-babes@homeassistant "ha addons rebuild local_beep_boop_bb8"
ha addons info local_beep_boop_bb8 | grep -E 'version:|version_latest:'
```

**Gotcha:** Without `build:` in `config.yaml`, Supervisor tries to **pull** a `local/` image → 404. Always include `build:`.

---

## 6. Versioning & Publish/Deploy

**In `addon/config.yaml` (mode‑aware)**

```yaml
# LOCAL_DEV (build locally; Supervisor DOES NOT pull):
version: "2025.8.21.4"
build:
  dockerfile: Dockerfile
  args:
    BUILD_FROM: "ghcr.io/home-assistant/{arch}-base-debian:bookworm"
# image: (omit in LOCAL_DEV)

# PUBLISH (Supervisor pulls from registry):
version: "2025.8.21.4"  # Ensure 'version:' is present and uncommented in actual publish mode
image: "ghcr.io/your-org/ha-bb8-{arch}"
# (build: ignored when image: is set for PUBLISH mode; Supervisor pulls image from registry)
```

**Canonical Dockerfile (Debian base + s6 + venv + jq/bash)**

```dockerfile
ARG BUILD_FROM=ghcr.io/home-assistant/aarch64-base-debian:bookworm
FROM ${BUILD_FROM}

ENV PYTHONUNBUFFERED=1 \
  PIP_DISABLE_PIP_VERSION_CHECK=1 \
  PIP_NO_CACHE_DIR=1 \
  VIRTUAL_ENV=/opt/venv \
  PATH="/opt/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

WORKDIR /usr/src/app
# Narrow copies (no COPY .)
COPY bb8_core/     /usr/src/app/bb8_core/
COPY app/          /usr/src/app/app/
COPY services.d/   /etc/services.d/
COPY run.sh        /usr/src/app/run.sh
COPY requirements.txt* /usr/src/app/

# Debian base deps; ensure bash + jq exist for run.sh
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      bash jq python3 python3-venv python3-pip ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Create venv and install into venv
RUN python3 -m venv "/opt/venv" && \
    /opt/venv/bin/pip install --no-cache-dir -U pip setuptools wheel && \
    if [ -f /usr/src/app/requirements.txt ]; then \
      /opt/venv/bin/pip install --no-cache-dir -r /usr/src/app/requirements.txt ; \
    fi && \
    chmod +x /usr/src/app/run.sh


Mode Matrix (LOCAL_DEV vs PUBLISH)

| Mode | image: value | Dockerfile | Build Context | Supervisor Action |
|-----------|----------------------------|--------------|---------------------|--------------------|
| LOCAL_DEV | Absent | Present | Local plain folder | Builds locally |
| PUBLISH | Registry URL (ghcr.io/…) | Optional | Registry image/tag | Pulls from registry|

_Refer to the earlier example for the correct `addon/config.yaml` configuration in LOCAL_DEV and PUBLISH modes._

```yaml
version: "2025.8.21.4"
build:
  dockerfile: Dockerfile
  args:
    BUILD_FROM: "ghcr.io/home-assistant/{arch}-base-debian:bookworm"
# image: (omit for LOCAL_DEV; set to ghcr for PUBLISH)
```

run.sh (entrypoint wrapper for Python app in container)

```bash
#!/usr/bin/with-contenv bash
set -euo pipefail
export PYTHONUNBUFFERED=1
cd /usr/src/app
OPTIONS=/data/options.json
JQ=${JQ:-/usr/bin/jq}
VENV=${VIRTUAL_ENV:-/opt/venv}
PY="$VENV/bin/python"; command -v "$PY" >/dev/null 2>&1 || PY="$(command -v python3 || command -v python)"
if command -v "$JQ" >/dev/null 2>&1 && [ -f "$OPTIONS" ]; then
  export ENABLE_BRIDGE_TELEMETRY="$($JQ -r '.enable_bridge_telemetry // 0' "$OPTIONS" 2>/dev/null || echo 0)"
fi
exec "$PY" -m bb8_core.main
```

**s6 run file — `addon/services.d/ble_bridge/run`**

```bash
#!/usr/bin/with-contenv bash
set -euo pipefail
exec /usr/bin/env bash /usr/src/app/run.sh
```

---

## 8. Telemetry (STP5)

**Module:** `addon/bb8_core/telemetry.py`

```python
import json, time, os
TELEMETRY_BASE = os.environ.get("MQTT_BASE", "bb8") + "/telemetry"
ret=False
def now():
    return int(time.time())
def publish(mqtt, name, data):
    """
    Publish telemetry data to MQTT.
    mqtt.publish(f"{TELEMETRY_BASE}/{name}", json.dumps({**data, "ts": now()}), qos=0, retain=ret)
    Args:
def echo_roundtrip(mqtt, ms, outcome):
    """
    Send echo roundtrip latency and outcome telemetry.
    """
    publish(mqtt, "echo_roundtrip", {"ms": ms, "outcome": outcome})

def ble_connect_attempt(mqtt, try_no, backoff_s):
    """
    Report BLE connection attempt number and backoff seconds.
    """
    publish(mqtt, "ble_connect_attempt", {"try": try_no, "backoff_s": backoff_s})

def led_discovery(mqtt, unique_id, duplicates):
    """
    Emit LED discovery telemetry including unique_id and duplicate count.
    """
    publish(mqtt, "led_discovery", {"unique_id": unique_id, "duplicates": duplicates})
    """Send echo roundtrip latency and outcome telemetry."""
    publish(mqtt, "echo_roundtrip", {"ms": ms, "outcome": outcome})

def ble_connect_attempt(mqtt, try_no, backoff_s):
    """Report BLE connection attempt number and backoff seconds."""
    publish(mqtt, "ble_connect_attempt", {"try": try_no, "backoff_s": backoff_s})

def led_discovery(mqtt, unique_id, duplicates):
    """Emit LED discovery telemetry including unique_id and duplicate count."""
    publish(mqtt, "led_discovery", {"unique_id": unique_id, "duplicates": duplicates})
```

**Runner adds telemetry capture**

* `telemetry_snapshot.jsonl` (from `mosquitto_sub -v`)
* `metrics_summary.json` (p50/p95 echo latency; BLE attempts/hour; max dupe count)

**SLOs (recommendation)**

* `echo_roundtrip_ms_p50 ≤ 150`
* `echo_roundtrip_ms_p95 ≤ 500`
* `ble_connect_attempts_per_hour ≤ 6`
* `discovery_dupe_count == 0`

### 8.1 Telemetry hardening (MQTT backoff + tidy)

**Why**  
Under broker outages or auth errors, the responder can enter rapid reconnect cycles. Add a bounded **MQTT reconnect backoff** and remove a duplicate loop call to keep CPU/memory stable and startup clean.

**Change (Python, `addon/bb8_core/echo_responder.py`)**

```python
# ... after client = mqtt.Client(...), handlers assigned
try:
    client.reconnect_delay_set(min_delay=1, max_delay=5)
except Exception:
    pass

LOG.info("Starting MQTT loop")
client.loop_forever()  # (ensure this appears only once)
```

**Optional responder knobs (rate/concurrency)**  
Expose and export from options → env for controlled throughput during attestation bursts:

```yaml
# addon/config.yaml
options:
  enable_echo: true
  echo_max_inflight: 8
  echo_min_interval_ms: 5
schema:
  enable_echo: bool
  echo_max_inflight: int?
  echo_min_interval_ms: int?
```

```bash
# addon/services.d/echo_responder/run (snippet)
JQ=/usr/bin/jq; OPTS=/data/options.json
[ -f "$OPTS" ] || exec sleep infinity
E_MAX="$($JQ -r '.echo_max_inflight // empty' "$OPTS" 2>/dev/null || true)"
E_MIN="$($JQ -r '.echo_min_interval_ms // empty' "$OPTS" 2>/dev/null || true)"
[ -n "$E_MAX" ] && export ECHO_MAX_INFLIGHT="$E_MAX"
[ -n "$E_MIN" ] && export ECHO_MIN_INTERVAL_MS="$E_MIN"
exec /usr/bin/env bash /usr/src/app/run.sh
```

**Validation (quick)**

```bash
# MQTT connectivity markers
ha addons logs local_beep_boop_bb8 | grep -E "Connected to MQTT broker|Subscribed to .*echo/cmd" \
  && echo "TOKEN: ADDON_MQTT_OK" || echo "FAIL: ADDON_MQTT"

# Attestation (example)
export MQTT_HOST=127.0.0.1 MQTT_PORT=1883 MQTT_USERNAME=mqtt_bb8 MQTT_PASSWORD=mqtt_bb8 MQTT_BASE=bb8
export WINDOW=15 COUNT=30
/config/domain/shell_commands/attest/attest_stp5_telemetry.sh
# Expect: TOKEN: TELEMETRY_ATTEST_OK
```

**Failure modes → remedies**

* `Connection Refused: not authorised` → fix broker creds/ACL; retry with backoff active.  
* No echoes observed (`echo_count=0`) → ensure responder service enabled, topics/prefix match, and broker reachable.  
* High CPU / memory spikes under outage → confirm `reconnect_delay_set(1,5)` present and only one `loop_forever()`. 

---

## 8. Troubleshooting Playbook


### Issue: File transfer to HA runtime fails (rsync/scp permission or temp-file errors)

**Symptom:**  
File (e.g., `bb8_core/echo_responder.py`) missing from `/addons/local/<slug>/` after sync.  
`rsync` or `scp` fails with permission or temp-file errors.

**Checklist:**

1. **Confirm mode:**
   - LOCAL_DEV: `image:` absent in `config.yaml` → direct file placement and rebuild allowed.
   - PUBLISH: `image:` present → must build/push new image; local file placement is ignored.

2. **If LOCAL_DEV:**
   - If `rsync` fails with `mkstemp` or permission errors:
     - Use direct file creation:
       ```sh
       cat > /addons/local/<slug>/bb8_core/echo_responder.py <<'PY'
       # Paste file contents here
       PY
       ```
     - Or use tar over ssh:
       ```sh
       tar -C addon -cf - bb8_core/echo_responder.py | ssh <user>@<HA_IP> 'tar -C /addons/local/<slug> -xf -'
       ```
     - Or use the File Editor/Samba share.

   - Rebuild and start:
     ```sh
     ha addons rebuild local_<slug>
     ha addons start local_<slug>
     ```

3. **If PUBLISH:**
   - Add file to source, commit, tag, build, and push new image.
   - Update `config.yaml` with new `version:` and `image:`.
   - Reload and restart add-on.

4. **Verify:**
   - File exists:
     ```sh
     test -f /addons/local/<slug>/bb8_core/echo_responder.py && echo OK:host
     ```
   - In-container import:
     ```sh
     CID=$(docker ps --filter name=addon_local_<slug> -q)
     docker exec "$CID" python -c "import bb8_core.echo_responder as m; print(m.__file__)"
     ```

**Note:**  
If standard tools fail, fallback methods (cat, tar, File Editor) bypass temp-file creation and work reliably on restrictive filesystems.

### Issue: Add‑on restarts every ~1–2s

**Detect:** repeated `Starting bridge controller…` lines.
**Fix:** keep controller in foreground with SIGTERM handler; on exit, `ble_link.stop(); ble_link.join()`.

### Issue: Supervisor tries to **pull** `local/…` image (404)

**Detect:** `pull access denied for local/aarch64-addon-beep_boop_bb8`
**Fix:** ensure `config.yaml` has `build:` and a present `Dockerfile`; then `ssh babylon-babes@homeassistant "ha addons reload" && rebuild`.

### Issue: `git pull` fails under `/addons/local/...`

**Detect:** `fatal: not a git repository`

**Fix:** correct — runtime folder is a **plain directory**. Sync from workspace via rsync or use runtime clone path.

### Issue: BLE event loop warnings / unawaited coroutines

**Fix:** dedicated BLE loop thread; `_cancel_and_drain()`; graceful `stop()+join()`.


### Issue: MQTT callback deprecation

**Fix:**
- Pin `paho-mqtt` policy; pass `CallbackAPIVersion.VERSION1`.
- Refactored all code to instantiate `mqtt.Client` only inside functions or classes, never at module level. This ensures warning filters can be set before any client is created, fully suppressing import-time DeprecationWarnings.
- All functions and event loops now accept a `client` argument, and the main entrypoint creates, configures, and passes the client instance explicitly.
- Callback assignments (e.g., `on_connect`) are now performed via a dedicated setup function after client instantiation.
- No global side effects or warnings during import; code is more testable and maintainable.

**Operational impact:**
- No import-time warnings; pytest and CI can reliably filter/suppress deprecation warnings.
- Improved code hygiene and explicit dependency management.
- All entrypoints (CLI, service, tests) must instantiate and pass the client instance.

### Issue: LED discovery dupes/missing

**Fix:** discovery ON by default; unique_id stable; validate via discovery dump.

### Quick Mode & Build Context Checks

**On the HA box:**
```sh
CFG=/addons/local/beep_boop_bb8/config.yaml
if sed 's/#.*$//' "$CFG" | grep -Eq '^[[:space:]]*image:[[:space:]]*'; then
  echo "MODE: PUBLISH"
else
  echo "MODE: LOCAL_DEV"
fi
```

**In your local workspace (VS Code):**
```sh
CFG=addon/config.yaml
if sed 's/#.*$//' "$CFG" | grep -Eq '^[[:space:]]*image:[[:space:]]*'; then
  echo "MODE: PUBLISH"
else
  echo "MODE: LOCAL_DEV"
fi
```

**Quick “behavior” check (HA):**
```sh
ssh babylon-babes@homeassistant "ha addons rebuild local_beep_boop_bb8" >/dev/null 2>&1 && echo "LOCAL_DEV" || echo "PUBLISH"
# If it prints "PUBLISH", Supervisor refused because image: is set.
```

**Tip:** In LOCAL_DEV, also confirm build context is valid:
```sh
test -f /addons/local/beep_boop_bb8/Dockerfile && echo "BUILDABLE: yes" || echo "BUILDABLE: no"
```
---

## 9. Operational Checklists
### MQTT Callback Compliance & Stability Checklist

1. Audit all files for MQTT callback signature compliance (see reports/callback_signature_matrix.md)
2. Patch all callback functions to match VERSION2 requirements (add 'properties' argument, etc.)
3. Add runtime and CI tests for callback compatibility and resource stability
4. Review and refactor threading, reconnect, and semaphore logic to prevent leaks and runaway loops
5. If stability cannot be achieved with VERSION2, revert to VERSION1 and reinstate warning suppression (document rationale)
6. Update documentation and callback signature matrix after every migration or audit
7. Confirm all acceptance criteria in STP5_callback_signature.yaml are met

#### Verification Steps
- Run all unit and integration tests (pytest)
- Check for runtime errors, warnings, and resource usage in logs and CI
- Perform manual functional tests for MQTT event handling
- Review callback signature matrix for compliance
- Audit for warning suppression and document exceptions
### 9.1 Pre‑Publish

* [ ] `addon/` contains only shippable files (no `.git`, no workspace dirs)
* [ ] Tests pass locally (`pytest -W error`), coverage ≥ 80%
* [ ] `config.yaml` `version` bumped if releasing

### 9.2 Publish (subtree)

* [ ] `git subtree split -P addon` → push to add‑on repo `main`
* [ ] Receipt contains `TOKEN: SUBTREE_PUBLISH_OK`

### 9.3 Deploy (runtime)

* [ ] `/addons/local/beep_boop_bb8/` contains `config.yaml` + `Dockerfile`
* [ ] `config.yaml` contains `build:` and no `image:` (LOCAL_DEV)
* [ ] `ssh babylon-babes@homeassistant "ha addons reload" && ha addons rebuild` succeed
* [ ] Receipt contains `TOKEN: CLEAN_RUNTIME_OK`, `TOKEN: DEPLOY_OK`, `TOKEN: VERIFY_OK`

### 9.4 Attestation (STP4)

* [ ] `qa_report_contract_v1.json` = PASS
* [ ] `ha_mqtt_trace_snapshot.json` present (retain=false scalar echo)
* [ ] `ha_discovery_dump.json` present (LED unique_id stable; no dupes)
* [ ] `evidence_manifest.json` lists all artifacts with SHA-256

### 9.5 CI Gate (PR)

* [ ] `STRUCTURE_OK` emitted (ADR‑0001 checks)
* [ ] `VERIFY_OK` emitted (pytest OK; warnings as errors)

---

## 10. POSIX‑only Helpers (HA‑OS compatible)
---

## Canonical Sync Procedure (ADR-0001 / ops/release)


> **COMMAND_BLOCK: SYNC_LOCAL_DEV_ADDON**
> To sync the updated add-on to the LOCAL_DEV runtime (machine-friendly):
>
> ```sh
> rsync -av --delete addon/ babylon-babes@homeassistant:/data/addons/local/beep_boop_bb8/
> ```
>
> # If you need to exclude forbidden files per ADR-0001:
> ```sh
> rsync -av --delete addon/ babylon-babes@homeassistant:/data/addons/local/beep_boop_bb8/
> ```
>
> # Ensure the target path is `/addons/local/beep_boop_bb8/` for local development.

**Notes:**
- This method is robust, idempotent, and matches ADR-0001 and operational best practices.
- Always verify permissions and workspace hygiene before syncing.

# Regex helpers for workspace (developer use only)
rg -n '^TOKEN:[[:space:]]*(WS_READY|STRUCTURE_OK|SUBTREE_PUBLISH_OK|CLEAN_RUNTIME_OK|DEPLOY_OK|VERIFY_OK|RUNTIME_TOPOLOGY_OK|TOOLS_ALLOWED|SCRIPTS_ALLOWED)' reports/

# Version desync check (workspace)
# Note: 'rg' (ripgrep) required; fallback to 'grep' if unavailable
if command -v rg >/dev/null 2>&1; then
  sed -n '1,40p' addon/config.yaml | rg '^version:'
  ha addons info local_beep_boop_bb8 | rg 'version'
else
  sed -n '1,40p' addon/config.yaml | grep -E '^version:'
  ha addons info local_beep_boop_bb8 | grep -E 'version'
fi

```bash
# Tokens from receipts (POSIX, no ripgrep)
grep -nE '^TOKEN:[[:space:]]*(WS_READY|STRUCTURE_OK|SUBTREE_PUBLISH_OK|CLEAN_RUNTIME_OK|DEPLOY_OK|VERIFY_OK|RUNTIME_TOPOLOGY_OK|TOOLS_ALLOWED|SCRIPTS_ALLOWED)' reports/* 2>/dev/null || true

# Version desync check (runtime vs info)
sed -n '1,40p' /addons/local/beep_boop_bb8/config.yaml | grep -E '^version:'
ha addons info local_beep_boop_bb8 | grep -E 'version'

# Supervisor build-context sanity
ssh babylon-babes@homeassistant "ls -lah /addons/local/beep_boop_bb8"
ssh babylon-babes@homeassistant "(test -f /addons/local/beep_boop_bb8/config.yaml && echo OK) || echo MISSING-config"
(test -f /addons/local/beep_boop_bb8/Dockerfile && echo OK) || echo MISSING-dockerfile

# Telemetry capture (best‑effort)
mosquitto_sub -h "$MQTT_HOST" -p "$MQTT_PORT" -v -t 'bb8/telemetry/#' -C 100 -W 10 
  | awk '{topic=$1; $1=""; sub(/^ /,""); gsub(/"/, "\\\"", $0); payload=$0; print "{\"topic\":\""topic"\",\"payload\":\"" payload "\"}"}' 
  > reports/telemetry_snapshot.jsonl
```

---

## 11. Assumptions & Environment Matrix

```json
{
  "assumptions": {
    "arch": "aarch64",
    "build_from": "ghcr.io/home-assistant/{arch}-base-debian:bookworm",
    "supervisor_s6_entrypoint": true,
    "posix_only_on_ha_host": true,
    "jq_required_in_container": true,
    "bash_required_in_container": true
  },
  "verify": {
    "s6_runfile": "test -f /etc/services.d/ble_bridge/run",
    "wrapper": "test -f /usr/src/app/run.sh",
    "jq_bash": "command -v jq && command -v bash",
    "venv": "test -x /opt/venv/bin/python",
    "local_dev_build": "grep -q '^build:' addon/config.yaml"
  }
}
```

---

**End of OPERATIONS_OVERVIEW** — Keep this file in `docs/OPERATIONS_OVERVIEW.md`. Adhere to ADR‑0001 layout, emit tokens & contracts, and every step becomes provable and automatable.
