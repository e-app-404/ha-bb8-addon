---
title: "ADR-0008: End-to-End Development → Deploy Flow (Dual‑Clone & HA Supervisor)"
date: 2025-08-27
status: Accepted
author:
  - Promachos Governance
related:
  - ADR-0001
  - ADR-0003
  - ADR-0004
  - docs/OPERATIONS_OVERVIEW.md
supersedes: []
last_updated: 2025-08-27
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
  - `addon/Dockerfile` (Debian base, venv at `/opt/venv`, no `apk`).
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


## 12. Appendix — Minimal File Invariants

- `addon/Dockerfile` (Debian, `apt-get`, venv at `/opt/venv`)
- `addon/services.d/ble_bridge/run` → `/usr/bin/env bash /usr/src/app/run.sh`
- `addon/run.sh` → exec venv python `-m bb8_core.main`
- `addon/config.yaml` → `image:` local + `build:` present

