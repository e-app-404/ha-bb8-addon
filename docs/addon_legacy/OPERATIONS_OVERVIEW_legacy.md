---
title: OPERATIONS_OVERVIEW — HA‑BB8 (CRTP Edition)
date: 2025-08-26
status: Informational
---

# OPERATIONS_OVERVIEW — HA‑BB8 (CRTP Edition)

> **Machine‑friendly handbook** for structure, flows, tokens, and contracts. Optimized for parsing by CI, GitHub Copilot, and LLM assistants.
>
> Baseline Tag: `v2025.8.21.1`
> Project: **BB‑8 Bridge (HA‑BB8)**
> Add‑on Slug: `beep_boop_bb8`
> Runtime Add‑on Path (HA OS): `/addons/local/beep_boop_bb8`

---

## Table of Contents
1. [Contents (anchors)](#1-contents-anchors)
2. [Topology & Layout](#2-topology--layout)
3. [Roles & Originators](#3-roles--originators)
4. [Governance Tokens](#4-governance-tokens)
5. [Output Contracts (JSON)](#5-output-contracts-json)
6. [Process Flows (A→F)](#6-process-flows-a→f)
7. [Versioning & Publish/Deploy](#7-versioning--publishdeploy)
8. [Telemetry (STP5)](#8-telemetry-stp5)
9. [Troubleshooting Playbook](#9-troubleshooting-playbook)
10. [Operational Checklists](#10-operational-checklists)
11. [Appendix: Regex & Grep Helpers](#11-appendix-regex--grep-helpers)
12. [Last updated](#12-last-updated)

---

## 1. Contents (anchors)

* [Topology & Layout](#2-topology--layout)
* [Roles & Originators](#3-roles--originators)
* [Governance Tokens](#4-governance-tokens)
* [Output Contracts (JSON)](#5-output-contracts-json)
* [Process Flows (A→F)](#6-process-flows-a→f)
* [Versioning & Publish/Deploy](#7-versioning--publishdeploy)
* [Telemetry (STP5)](#8-telemetry-stp5)
* [Troubleshooting Playbook](#9-troubleshooting-playbook)
* [Operational Checklists](#10-operational-checklists)
* [Appendix: Regex & Grep Helpers](#11-appendix-regex--grep-helpers)

---

## 2. Topology & Layout (summary)

**Canonical spec:** see **ADR-0001 — Dual-Clone Topology** (`docs/ADR-0001-workspace-topology.md`).

### Workspace Structure
| Path | Purpose |
|------|---------|
| `addon/` | Shipped subtree (no .git) |
| `app/` | App code (if present) |
| `bb8_core/` | Core logic |
| `services.d/` | s6 service scripts |
| `tools/` | Runtime tools (if referenced) |
| `scripts/` | Runtime scripts (if referenced) |
| `docs/` | Documentation |
| `ops/` | Operational scripts |
| `reports/` | Machine receipts, contracts |

### Runtime Layout (HA OS)
| Path | Purpose |
|------|---------|
| `/addons/local/beep_boop_bb8/` | Build context for local dev |
| `/config/reports/` | Receipts, tokens |

### Mode Matrix
| Mode | `image:` | `Dockerfile` | Build Context |
|------|----------|--------------|--------------|
| LOCAL_DEV | Absent/Commented | Present | Local build |
| PUBLISH   | Present          | Optional | Pull from registry |

### Quick toggle: image: for LOCAL_DEV vs PUBLISH
```sh
# LOCAL_DEV: comment out image:
sed -i '/^image:/s/^/# /' addon/config.yaml
# PUBLISH: uncomment image:
sed -i '/^# *image:/s/^# *//' addon/config.yaml
```

### Quick toggle: image: for LOCAL_DEV vs PUBLISH

```bash
# LOCAL_DEV: comment out image:
sed -i.bak '/^image:/s/^/# /' addon/config.yaml
# PUBLISH: uncomment image:
sed -i.bak '/^# *image:/s/^# *//' addon/config.yaml
```

## 3. Roles & Originators

| Role              | Scope                           | Primary Outputs                               |
| ----------------- | ------------------------------- | --------------------------------------------- |
| **Strategos**     | Governance & acceptance gates   | Delta contracts; binary acceptance; CI policy |
| **Pythagoras**    | Code & QA execution             | Patch bundles; tests; QA/evidence contracts   |
| **Copilot**       | Implementation surface (assist) | Applied diffs; scripted runs                  |
| **HA Supervisor** | Runtime container lifecycle     | Build logs; start/stop; error diagnostics     |

**Machine tags**: `ORIGINATOR: Strategos` / `ORIGINATOR: Pythagoras` appear in receipts for attribution.

## 4. Governance Tokens (pointer)

**Canonical catalog & semantics:** **ADR-0001 §Tokens** (`docs/ADR-0001-workspace-topology.md`).  
**CRTP-specific tokens** (tools/scripts): see **ADR-0004** (`docs/ADR-0004-runtime-tools-policy.md`).

## 5. Output Contracts (JSON)

> Contracts are machine‑readable summaries placed under `reports/`.

### 5.1 QA Report

```json
{
  "contract": "qa_report_contract_v1",
  "verdict": "PASS",
  "coverage": 82.0,
  "tests": {"total": 54, "failures": 0, "errors": 0, "skipped": 0},
  "tokens": ["STRUCTURE_OK","DEPLOY_OK","VERIFY_OK","WS_READY"],
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

### 5.2 Patch Bundle

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

### 5.3 Evidence Manifest

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

---

## 6. Process Flows (A→F)

### Flow A — Local Development & Testing (Originator: Pythagoras)

```bash
# Create/activate venv, then:
pip install -e addon
pip install -r addon/requirements-dev.txt

# Run tests with warnings-as-errors (except paho v1 deprecation in pytest.ini)
pytest -q -W error --maxfail=1 
  --cov=bb8_core --cov-report=term:skip-covered
```

**Emit:** coverage + JUnit under `reports/` (when using runners).
**Gate:** No warnings except explicitly suppressed policy lines.
**Token:** `WS_READY` when dev toolchain validated.

---

### Flow B — Publish the Add‑on Subtree (Originator: Strategos)

```bash
# From workspace root
git subtree split -P addon -b __addon_pub_tmp
git push -f git@github.com:<org>/ha-bb8-addon.git __addon_pub_tmp:refs/heads/main
git branch -D __addon_pub_tmp

echo 'TOKEN: SUBTREE_PUBLISH_OK' | tee -a reports/publish_receipt.txt
```

**Emit:** `reports/publish_receipt.txt` with `SUBTREE_PUBLISH_OK`.

---

### Flow C — Deploy to HA Runtime (Originator: Strategos → Exec: Pythagoras)

**Option 1: rsync to local add‑ons**

```bash
# On workstation
rsync -av --delete \
  --exclude-from ops/rsync_runtime.exclude \
  addon/ /Volumes/addons/local/beep_boop_bb8/

# On HA box
ssh babylon-babes@homeassistant "ha addons reload"
ssh babylon-babes@homeassistant "ha addons rebuild local_beep_boop_bb8"
ha addons start  local_beep_boop_bb8

echo 'TOKEN: CLEAN_RUNTIME_OK' >> /config/reports/deploy_receipt.txt || true
echo 'TOKEN: DEPLOY_OK'         >> /config/reports/deploy_receipt.txt || true
echo 'TOKEN: VERIFY_OK'         >> /config/reports/deploy_receipt.txt || true
```

**Option 2: runtime clone reset** (if your deploy path uses a clone)

```bash
# In runtime repo
git fetch --all --prune
git checkout -B main origin/main
git reset --hard origin/main
ssh babylon-babes@homeassistant "ha addons rebuild local_beep_boop_bb8"
```

**Gate (mode-aware):**
  - **LOCAL_DEV:** `image:` **absent/commented**; Supervisor builds locally from `Dockerfile` + `build.yaml`.
  - **PUBLISH:** `image:` **present** and tag exists; `version:` equals the pushed tag.
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

**Source of truth:** `.github/workflows/repo-guards.yml` (kept in repo).  
This workflow enforces ADR-0001 structure + ADR-0004 CRTP rules, runs pytest (warnings-as-errors policy), and emits machine-readable tokens.

```yaml
# .github/workflows/repo-guards.yml (excerpt)
- name: Structure guard (ADR-0001 + CRTP)
  run: |
    set -euo pipefail
    test -d addon || (echo "addon/ missing" && exit 2)
    if [ -d addon/.git ]; then echo "addon is a repo (forbidden)"; exit 3; fi

    # Forbidden workspace-only dirs (always)
    for d in .github docs ops reports addon; do
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
    if rg -n '^\s*image:\s*' addon/config.yaml >/dev/null; then
      echo "MODE: PUBLISH"
      rg -n '^\s*version:\s*' addon/config.yaml >/dev/null || (echo "DRIFT:version_missing_in_publish_mode" && exit 9)
    else
      echo "MODE: LOCAL_DEV"
      test -f addon/Dockerfile || (echo "DRIFT:dockerfile_missing_in_local_dev" && exit 10)
      echo "TOKEN: DEV_LOCAL_BUILD_FORCED"
    fi

    echo "TOKEN: STRUCTURE_OK"
- name: Pytest (warnings as errors)
  run: pytest -q -W error --maxfail=1 --cov=bb8_core --cov-report=term-missing
- name: Emit CI tokens
  run: echo '{"tokens":["STRUCTURE_OK","VERIFY_OK"]}' > tokens.ci.json
```

**Note:** CI intentionally **does not** emit `DEPLOY_OK`.

---

### Flow F — Local Add-on Version Bump & Rebuild (LOCAL_DEV)

```bash
# Edit runtime file on HA box
sed -i 's/^version:.*/version: "2025.8.21.3"/' /addons/local/beep_boop_bb8/config.yaml
ssh babylon-babes@homeassistant "ha addons reload"
ssh babylon-babes@homeassistant "ha addons rebuild local_beep_boop_bb8"
ha addons info local_beep_boop_bb8 | grep -E 'version:|version_latest:'
```

**Gotcha:** If `image:` is present in LOCAL_DEV, Supervisor will try to **pull** → 404. For LOCAL_DEV, **comment out `image:`**; let Supervisor build locally.

---

## 7. Versioning & Publish/Deploy

### LOCAL_DEV (build locally — `image:` absent)
```yaml
version: "2025.8.21.3"
# image: ghcr.io/your-org/ha-bb8-{arch}   # ← commented in LOCAL_DEV
build:
  dockerfile: Dockerfile
  args:
    BUILD_FROM: "ghcr.io/home-assistant/{arch}-base-debian:bookworm"
```

### PUBLISH (pull from registry — `image:` present)
```yaml
version: "2025.8.21.3"                   # equals container tag
image: "ghcr.io/your-org/ha-bb8-{arch}"
# build: may be left in place; Supervisor will prefer the image when present
```

### In `addon/config.yaml` (mode-aware)
```yaml
version: "2025.8.21.3"
# LOCAL_DEV: comment out image: to build locally
# PUBLISH:   uncomment image: and push matching tag to the registry
# image: "ghcr.io/your-org/ha-bb8-{arch}"
```

### Minimal Dockerfile (Debian base; HA-aligned via build.yaml)
```dockerfile
ARG BUILD_FROM
FROM $BUILD_FROM
WORKDIR /usr/src/app
# narrow COPYs (runtime only); tests/docs excluded by .dockerignore
COPY bb8_core/ /usr/src/app/bb8_core/
COPY app/      /usr/src/app/app/
COPY services.d/ /etc/services.d/
COPY run.sh    /usr/src/app/run.sh
```

### Entrypoint example (`run.sh`)

```bash
#!/usr/bin/env bash
set -euo pipefail
python3 -m bb8_core.main
```

---

## 8. Telemetry (STP5)

**Module:** `addon/bb8_core/telemetry.py`

```python
import json, time, os
TELEMETRY_BASE = os.environ.get("MQTT_BASE", "bb8") + "/telemetry"
RET=False
now=lambda:int(time.time())

def publish(mqtt, name, data):
    mqtt.publish(f"{TELEMETRY_BASE}/{name}", json.dumps({**data, "ts": now()}), qos=0, retain=RET)

def echo_roundtrip(mqtt, ms, outcome): publish(mqtt, "echo_roundtrip", {"ms": ms, "outcome": outcome})

def ble_connect_attempt(mqtt, try_no, backoff_s): publish(mqtt, "ble_connect_attempt", {"try": try_no, "backoff_s": backoff_s})

def led_discovery(mqtt, unique_id, duplicates): publish(mqtt, "led_discovery", {"unique_id": unique_id, "duplicates": duplicates})
```

**Runner adds telemetry capture**

* `telemetry_snapshot.jsonl` (from `mosquitto_sub -v`)
* `metrics_summary.json` (p50/p95 echo latency; BLE attempts/hour; max dupe count)

**SLOs (recommendation)**

* `echo_roundtrip_ms_p50 ≤ 150`
* `echo_roundtrip_ms_p95 ≤ 500`
* `ble_connect_attempts_per_hour ≤ 6`
* `discovery_dupe_count == 0`

---

## 9. Troubleshooting Playbook

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
**Fix:** policy in **ADR-0002 — Dependency Policy** (`docs/ADR-0002-dependency-policy.md`): pin `paho-mqtt`, use `CallbackAPIVersion.VERSION1`, and limit deprecation suppressions to tests.

### Issue: LED discovery dupes/missing

**Fix:** discovery ON by default; unique_id stable; validate via discovery dump.

---

## 10. Operational Checklists

### 10.1 Pre‑Publish

* [ ] `addon/` contains only shippable files (no `.git`, no workspace dirs)
* [ ] Tests pass locally (`pytest -W error`), coverage ≥ 80%
* [ ] `config.yaml` `version` bumped if releasing

### 10.2 Publish (subtree)

* [ ] `git subtree split -P addon` → push to add‑on repo `main`
* [ ] Receipt contains `TOKEN: SUBTREE_PUBLISH_OK`

### 10.3 Deploy (runtime)

* [ ] `/addons/local/beep_boop_bb8/` contains `config.yaml` + `Dockerfile`
* [ ] **LOCAL_DEV:** `image:` commented out; `Dockerfile` present  
* [ ] **PUBLISH:** `image:` present, tag exists; `version:` equals tag
* [ ] `ssh babylon-babes@homeassistant "ha addons reload" && ha addons rebuild` succeed
* [ ] Receipt contains `TOKEN: CLEAN_RUNTIME_OK`, `TOKEN: DEPLOY_OK`, `TOKEN: VERIFY_OK`
* [ ] **CRTP:** if `addon/tools/` or `addon/scripts/` exist → ensure Dockerfile references them or markers are present.

### 10.4 Attestation (STP4)

* [ ] `qa_report_contract_v1.json` = PASS
* [ ] `ha_mqtt_trace_snapshot.json` present (retain=false scalar echo)
* [ ] `ha_discovery_dump.json` present (LED unique_id stable; no dupes)
* [ ] `evidence_manifest.json` lists all artifacts with SHA-256

### 10.5 CI Gate (PR)

* [ ] `STRUCTURE_OK` emitted (ADR‑0001 + CRTP checks)
* [ ] `VERIFY_OK` emitted (pytest OK; warnings as errors)

---

## 11. Appendix: Regex & Grep Helpers

## 11. Appendix: POSIX & Regex Helpers

### POSIX Shell Helpers
```sh
# Check for required files
ssh babylon-babes@homeassistant "(test -f /addons/local/beep_boop_bb8/config.yaml && echo OK) || echo MISSING-config"
(test -f /addons/local/beep_boop_bb8/Dockerfile && echo OK) || echo MISSING-dockerfile

# Version desync check
sed -n '1,40p' /addons/local/beep_boop_bb8/config.yaml | grep '^version:'
ha addons info local_beep_boop_bb8 | grep 'version'

# Token grep
grep -E '^TOKEN:(WS_READY|STRUCTURE_OK|SUBTREE_PUBLISH_OK|CLEAN_RUNTIME_OK|DEPLOY_OK|VERIFY_OK|RUNTIME_TOPOLOGY_OK|TOOLS_ALLOWED|SCRIPTS_ALLOWED)' reports/*

# Telemetry capture (best-effort)
mosquitto_sub -h "$MQTT_HOST" -p "$MQTT_PORT" -v -t 'bb8/telemetry/#' -C 100 -W 10 \
  | awk '{topic=$1; $1=""; sub(/^ /,""); payload=$0; print "{\"topic\":\""topic"\",\"payload\":\"" payload "\"}"}' \
  > reports/telemetry_snapshot.jsonl
```

---

## 12. Last updated

_Last updated: 2025-08-27_
