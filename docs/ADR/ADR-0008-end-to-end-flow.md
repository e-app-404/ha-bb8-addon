---
id: ADR-0008
title: "End-to-End Development → Deploy Flow (Dual‑Clone & HA Supervisor)"
date: 2025-08-27
status: Accepted
author:
  - Promachos Governance
related:
  - ADR-0001
  - ADR-0003
  - ADR-0004
  - ADR-0034
  - docs/OPERATIONS_OVERVIEW.md
supersedes: []
last_updated: 2025-10-04
evidence_sessions:
  - 2025-10-04: "Verified deployment pipeline with file sync fixes, Alpine package compatibility, and HTTP API restart resolution"
---

# ADR‑0008: End‑to‑End Development → Deploy Flow (Dual‑Clone & HA Supervisor)

> Canonical, **machine‑friendly*- procedure to take a change from the developer workspace to a running Home Assistant add‑on container, and to publish/tag when ready. This ADR binds **what*- to **how*- (commands, tokens, receipts).


## 1. Context

- We use the **Dual-Clone topology*- (ADR-0001). All Git ops live in the **workspace**; the HA runtime folder `/addons/local/<slug>` is a **plain build context*- (no nested Git).
- Supervisor builds locally when `addon/config.yaml` contains a **`build:`*- block **and `image:` is absent**. Use `image:` **only for PUBLISH*- (pull from a registry).
- Runtime tools/scripts comply with **CRTP*- (ADR‑0004).
- Build patterns (base, venv, entrypoint) align with **ADR‑0003**.


## 2. Decision

We adopt a single, reproducible 4‑lane flow:

1. **Local Dev & Test (workspace)*- → validate structure, run tests, update docs.
2. **Sync to Runtime (HA)*- → copy `addon/` → `/addons/local/<slug>/`, reload & rebuild.
3. **Start & Verify (HA)*- → start add‑on, verify container invariants, emit tokens/receipts.
4. **Publish & Tag (optional)*- → subtree publish, tag, and (when used) promote image.

Each lane emits **greppable tokens*- and/or **JSON contracts*- under `reports/`.


## 3. Preconditions

- Workspace contains:

  - `addon/config.yaml` (mode-aware):

    **LOCAL_DEV (build locally; Supervisor does NOT pull):**
    ```yaml
    version: "YYYY.M.D.P"
    build:
      dockerfile: Dockerfile
      args:
        BUILD_FROM: "ghcr.io/home-assistant/{arch}-base-debian:bookworm"
    # image: (omit in LOCAL_DEV)
    ```

    **PUBLISH (Supervisor pulls from registry):**
    ```yaml
    version: "YYYY.M.D.P"
    image: "ghcr.io/your-org/ha-bb8-{arch}"
    # build: (optional/not used when pulling)
    ```
  - `addon/Dockerfile` (Alpine-compatible, venv at `/opt/venv`, use `apk add` not `apt-get`).
  - `addon/services.d/ble_bridge/run` → exec `/usr/bin/env bash /usr/src/app/run.sh`.
  - `addon/run.sh` → exec `"${VIRTUAL_ENV:-/opt/venv}/bin/python" -m bb8_core.main`.
- HA CLI available on the HA host (`ha ...`).
- Optional: macOS runtime mount at `/Volumes/HA/addons/local/beep_boop_bb8`.


## 4. Lane 1 — Local Dev & Test (workspace)

**Goal:*- validate changes before touching the HA box.

**Receipts/Tokens:**
- Structure validation tokens: `reports/paths_health_receipt.txt`
- Gate tokens: `reports/local_receipts.txt`

```bash
# 4.1 Structure + path map (tokens)
bash ops/workspace/validate_paths_map.sh | tee reports/paths_health_receipt.txt
grep -nE '^TOKEN:' reports/paths_health_receipt.txt

# 4.2 Dev setup
python3 -m venv .venv && source .venv/bin/activate
pip install -e addon
[ -f addon/requirements-dev.txt ] && pip install -r addon/requirements-dev.txt || true

# 4.3 Tests (warnings as errors except explicitly suppressed)
pytest -q -W error --maxfail=1 
  --cov=bb8_core --cov-report=xml:reports/coverage.xml --junitxml=reports/pytest-report.xml

# 4.4 Gate tokens
printf "TOKEN: WS_READYnTOKEN: STRUCTURE_OKn" | tee -a reports/local_receipts.txt
```

**Success criteria:*- `WS_READY`, tests pass, coverage ≥ policy threshold.


## 5. Lane 2 — Sync to Runtime (HA)

Use **one*- of the two paths. Prefer the **mounted volume**; fallback to **SSH rsync**.

### 5.A) Mounted volume (macOS Finder/AFPS/SMB)

```bash
# from workspace root on the workstation
rsync -av --delete 
  --exclude-from ops/rsync_runtime.exclude 
  --exclude '.DS_Store' 
  addon/ /Volumes/HA/addons/local/beep_boop_bb8/
```

### 5.B) SSH rsync (no mount)

```bash
# from workspace root on the workstation
RSYNC_EXC=ops/rsync_runtime.exclude
rsync -avz --delete 
  --exclude-from "$RSYNC_EXC" 
  -e "ssh" 
  addon/ user@<ha-host>:/addons/local/beep_boop_bb8/
```


**Receipts/Tokens:**
- Runtime sync token: `/config/reports/deploy_receipt.txt`

**Receipt (HA host):**
```bash
mkdir -p /config/reports && echo 'TOKEN: CLEAN_RUNTIME_OK' | tee -a /config/reports/deploy_receipt.txt
```


## 6. Lane 3 — Rebuild, Start & Verify (HA)

```bash
# 6.1 Register changes with Supervisor
ssh babylon-babes@homeassistant "ha addons reload"

# 6.2 Rebuild local image from runtime folder
ssh babylon-babes@homeassistant "ha addons rebuild local_beep_boop_bb8"

# 6.3 Start (idempotent)
ssh babylon-babes@homeassistant "ha addons start local_beep_boop_bb8" || true

# 6.4 Verify state & invariants
ssh babylon-babes@homeassistant "ha addons info local_beep_boop_bb8 | grep -E 'state:|version:'"

CID=$(docker ps --filter name=addon_local_beep_boop_bb8 --format '{{.ID}}' || true)
[ -n "$CID" ] && docker exec "$CID" bash -lc 'test -x /usr/src/app/run.sh && echo TOKEN: RUN_SH_PRESENT'
[ -n "$CID" ] && docker exec "$CID" /opt/venv/bin/python -c 'import bb8_core,sys;print("TOKEN: PY_OK", sys.version.split()[0])'


# 6.5 Emit verify token (receipt: `/config/reports/deploy_receipt.txt`)
echo 'TOKEN: DEPLOY_OK' | tee -a /config/reports/deploy_receipt.txt
```

**Notes:**

- If Supervisor shows *Install- instead of *Start*, the add‑on is registered; click **Install*- (no store repo needed for `local/`).
- If you see pull errors (`local/...` not found), ensure `config.yaml` contains a `build:` block.


## 7. Lane 4 — Publish & Tag (optional)

```bash
# 7.1 Subtree publish (workspace)
git subtree split -P addon -b __addon_pub_tmp
git push -f git@github.com:<org>/ha-bb8-addon.git __addon_pub_tmp:refs/heads/main
git branch -D __addon_pub_tmp


# Emit subtree publish token (receipt: `reports/publish_receipt.txt`)
echo 'TOKEN: SUBTREE_PUBLISH_OK' | tee -a reports/publish_receipt.txt

# 7.2 Tag in the add-on repo (GitHub UI or git tag+push)
# Ensure addon/config.yaml:version == tag
```


## 8. Troubleshooting (canonical)

- **“Add‑on not available inside store”**: ensure `/addons/local/beep_boop_bb8/config.yaml` exists, then UI → *Add‑on Store → HA‑BB8 (local)- → **Install**; or run `ssh babylon-babes@homeassistant "ha addons reload"`.
- **Supervisor tries to pull**: missing `build:` block → add it, then `ssh babylon-babes@homeassistant "ha addons reload" && rebuild`.
- **`run.sh` missing in container**: confirm `addon/run.sh` exists and is **copied*- by Dockerfile (`COPY run.sh /usr/src/app/run.sh`) and service executes it.
- **Permission denied on rsync**: prefer the mount owned by your user (SMB with `uid/gid` mapping) or use SSH rsync.

### P5-Footnote: Telemetry hardening (MQTT backoff, duplicate loop cleanup)

**Problem*-  
When the broker rejects connections (auth/ACL) or is unavailable, the responder can reconnect rapidly, causing CPU/memory churn and masking root-cause telemetry failures.

**Decision*-  
Introduce **bounded MQTT reconnect backoff*- and ensure a single loop entrypoint:

```python
# echo_responder.py (after client init + handlers)
  client.reconnect_delay_set(min_delay=1, max_delay=5)
except Exception:
  pass
LOG.info("Starting MQTT loop")
client.loop_forever()
```

**Optional configuration*-  
Expose `echo_max_inflight`, `echo_min_interval_ms` in `options:`; export in the echo responder s6 `run` script.

**Consequences*-  
- Stabilises behaviour during broker outages; prevents tight retry storms.  
- No change in nominal latency; optional knobs allow controlled throughput under test.

**Verification*-  
- Broker/auth OK markers present in logs: _Connected_ / _Subscribed_ lines.  
- STP5 artifacts show `window_ge_10s=true`, `min_echoes_ge_3=true`, `rtt_p95_le_250ms=true`, `verdict=true`.  
- Under induced broker outage, CPU/memory remain stable; responder retries with backoff (1–5s).


## 9. Emitted Tokens (grep‑able)

```
TOKEN: WS_READY
TOKEN: STRUCTURE_OK
TOKEN: CLEAN_RUNTIME_OK
TOKEN: DEPLOY_OK
TOKEN: VERIFY_OK
TOKEN: RUNTIME_TOPOLOGY_OK
TOKEN: SUBTREE_PUBLISH_OK
```


## 10. Consequences

- The flow is deterministic and **mode‑aware**. Changing only the workspace, you can rebuild locally on HA without a registry.
- Documents (OPERATIONS_OVERVIEW) can reference this ADR instead of duplicating the steps.


## 11. Adoption Plan

- Link from `docs/OPERATIONS_OVERVIEW.md` to this ADR.
- CI guard ensures `addon/config.yaml` has `build:` and a local `image:` in non‑publish PRs.
- Runners in `ops/` can emit the tokens above automatically.


## 12. Addendum: Verified Deployment Pipeline (2025-10-04)

### **Critical Issues Resolved**

#### **Issue 1: File Synchronization Failure**
**Problem**: Deployment script claimed success but was NOT copying files to remote system.
- Remote system showed old version (2025.8.21.50) while local had (2025.10.4.55+)
- Script only checked git status and restarted addon without file sync

**Root Cause**: `ops/release/deploy_ha_over_ssh.sh` checked for git repository but didn't copy files in "non-git runtime" mode.

**Solution**: Implemented robust `rsync` file synchronization with proper excludes:
```bash
# Create remote directory if needed
run_ssh "mkdir -p $REMOTE_RUNTIME"

# Robust file sync with cache exclusions
rsync -avz --delete \
  --exclude='.git*' --exclude='__pycache__' --exclude='*.pyc' \
  --exclude='.ruff_cache' --exclude='.pytest_cache' --exclude='.coverage' \
  --exclude='htmlcov' --exclude='.mypy_cache' \
  "$PROJECT_ROOT/addon/" "$REMOTE_HOST_ALIAS:$REMOTE_RUNTIME/"
```

#### **Issue 2: Alpine Package Compatibility**
**Problem**: Docker build failed with `py3-venv (no such package)` in Alpine Linux v3.22.

**Root Cause**: Package `py3-venv` doesn't exist in Alpine 3.22; modern Python3 includes venv by default.

**Solution**: Updated Dockerfile packages:
```dockerfile
# Before (BROKEN)
RUN apk add --no-cache python3 py3-pip py3-venv python3-dev build-base ca-certificates bash jq

# After (WORKING)  
RUN apk add --no-cache python3 py3-pip python3-dev build-base ca-certificates bash jq
```

#### **Issue 3: HTTP Fallback API Failures**
**Problem**: HTTP restart API calls failing with truncated URLs and wrong response validation.

**Root Cause**: 
- Empty `HA_URL` caused malformed candidate generation
- Script expected `"result": "ok"` but HA API returns `[]` on success

**Solution**: 
1. **Fixed HA_URL**: Set `HA_URL="http://192.168.0.129:8123"` in `.env`
2. **Simplified URL logic**: Use single primary URL instead of broken candidate iteration
3. **Fixed response validation**: Accept HTTP 200 as success for service calls

### **Verified Deployment Pipeline** 

#### **Automated Release Flow (PREFERRED)**
```bash
# Complete end-to-end release with version bump
make release-patch

# What happens internally:
# 1. ops/release/bump_version.sh patch      → version bump + git commit
# 2. ops/release/publish_addon_archive.sh  → GitHub subtree publish  
# 3. ops/release/deploy_ha_over_ssh.sh     → file sync + HA API restart
```

#### **Manual Deployment Flow**
```bash
# Deploy current state without version bump
REMOTE_HOST_ALIAS=home-assistant ops/release/deploy_ha_over_ssh.sh

# Diagnostic mode
REMOTE_HOST_ALIAS=home-assistant ops/release/deploy_ha_over_ssh.sh diagnose
```

#### **Configuration Requirements (.env)**
```bash
# HA DEPLOYMENT CONFIG
export HA_SSH_HOST_ALIAS=home-assistant
export HA_REMOTE_RUNTIME=/addons/local/beep_boop_bb8  
export HA_REMOTE_SLUG=local_beep_boop_bb8
export HA_SECRETS_PATH=/addons/local/beep_boop_bb8/secrets.yaml
export HA_URL="http://192.168.0.129:8123"  # CRITICAL: Must be set
export HA_LLAT_KEY=HA_LLAT_KEY
```

#### **Secrets File Format**
```yaml
# addon/secrets.yaml (synced to /addons/local/beep_boop_bb8/secrets.yaml)
HA_LLAT_KEY: eyJhbGciOiJIUzI1NiIs...  # Long-lived access token (unquoted)
```

### **Verified Success Indicators**
```
✅ SSH_HA_OK                        # SSH connection established
✅ Files synchronized successfully   # rsync completed without errors
✅ DEPLOY_OK — runtime sync via direct file copy
✅ Using HA Core API for restart at http://192.168.0.129:8123...
✅ HA API restart -> 200           # HTTP success
✅ VERIFY_OK — add-on restarted via HA API (HTTP 200)
✅ DEPLOY_SSH_OK                   # Complete deployment success
```

### **Docker Build Guardrails**
- **Alpine Compatibility**: Use only packages available in Alpine 3.22
- **No py3-venv**: Python3 includes venv by default in modern Alpine
- **Base Image**: HA Supervisor uses `ghcr.io/home-assistant/aarch64-base` (Alpine) regardless of Dockerfile BUILD_FROM
- **Package Manager**: Always use `apk add` not `apt-get` for HA Supervisor builds

### **Deployment Troubleshooting**
1. **Version Not Updating**: Check file sync with `ssh home-assistant 'grep version: /addons/local/beep_boop_bb8/config.yaml'`
2. **HTTP Restart Fails**: Ensure `HA_URL` is set correctly in `.env`
3. **Docker Build Fails**: Check Alpine package names and remove non-existent packages
4. **Permission Errors**: Use proper rsync excludes to skip cache directories

## 13. Appendix — Minimal File Invariants

- `addon/Dockerfile` (Alpine-compatible, `apk add` commands, venv at `/opt/venv`)
- `addon/services.d/ble_bridge/run` → `/usr/bin/env bash /usr/src/app/run.sh`
- `addon/run.sh` → exec venv python `-m bb8_core.main`
- `addon/config.yaml` → `image:` local + `build:` present, version synced
- `addon/secrets.yaml` → LLAT token for API access
- `.env` → HA_URL and deployment configuration

