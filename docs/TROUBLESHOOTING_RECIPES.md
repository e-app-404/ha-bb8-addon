---
title: "HA-BB8 — Troubleshooting Recipes"
status: "Operational"
version: "2025.8.21.4"
last_updated: "2025-08-28"
audience: ["Ops", "Dev", "CI"]
contract: "recipes_v1"
---

> Structured, machine-friendly recipes with fingerprints, root cause, decisive fixes, and verifications.

## Legend
- **MODE**: `LOCAL_DEV` (Supervisor builds from Dockerfile) vs `PUBLISH` (Supervisor pulls prebuilt image).
- **TOKENS**: Short strings echoed by scripts for CI/log parsing.
- **CTX**: Paths are relative to `addon/` unless prefixed with absolute host/container paths.

---

## TR-001 — “Can’t rebuild an image based add-on”
**Fingerprint**
- CLI: `Error: Can't rebuild a image based add-on`
- `ha addons info` shows `build: false` and `image:` present in `config.yaml`.

**Root Cause**
- Add-on in **PUBLISH** mode (has `image:`). Supervisor won’t rebuild.

**Fix (decisive)**
```bash
# On HA host
CFG=/addons/local/beep_boop_bb8/config.yaml
sed -i 's/^[[:space:]]*image:[[:space:]].*/# image: disabled for LOCAL_DEV/' "$CFG"
ha addons reload && ha addons rebuild local_beep_boop_bb8 && ha addons start local_beep_boop_bb8
```

## TR-002 — “apk: command not found” during build

**Fingerprint**

Build log: `/bin/bash: line 1: apk: command not found.`

**Root Cause**

Base image is Debian; Dockerfile uses Alpine’s apk.

**Fix (decisive)**
```Dockerfile
ARG BUILD_FROM=ghcr.io/home-assistant/aarch64-base-debian:bookworm
FROM ${BUILD_FROM}
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      python3 python3-venv python3-pip ca-certificates jq \
 && rm -rf /var/lib/apt/lists/*
```

**Verify**

Rebuild succeeds. No apk in logs.

## TR-003 — “COPY addon/… not found (build context)”

**Fingerprint**

Build fails: `COPY addon/bb8_core/echo_responder.py ...: not found.`

**Root Cause**

Build context is addon/; paths inside Dockerfile must be relative to addon/, not prefixed with addon/.

**Fix (decisive)**

- `COPY addon/bb8_core/echo_responder.py /usr/src/app/echo_responder.py`
# Already covered by:
  `COPY bb8_core/     /usr/src/app/bb8_core/`

**Verify**

Rebuild passes; file exists in container:

```bash
CID="$(docker ps --filter name=addon_local_beep_boop_bb8 --format '{{.ID}}')"
docker exec "$CID" bash -lc 'test -f /usr/src/app/bb8_core/echo_responder.py && echo TOKEN:ECHO_RESPONDER_PRESENT'
```

## TR-004 — rsync mkstemp permission denied

**Fingerprint**

`rsync: mkstemp ".../.file.XXXXXX" failed: Permission denied (13)`

Manual touch works, rsync fails.

**Root Cause**

Target FS denies temporary files used by rsync’s default atomic replace.

**Fix (choose one)**

In-place overwrite (best-effort)

```bash
rsync -av --inplace --delete --exclude-from ops/rsync_runtime.exclude \
  addon/ /Volumes/addons/local/beep_boop_bb8/
```

Direct write via SSH shell (fallback)

```bash
ssh homeassistant 'cat > /addons/local/beep_boop_bb8/bb8_core/echo_responder.py' < addon/bb8_core/echo_responder.py
```

**Verify**

```bash
ssh homeassistant 'test -f /addons/local/beep_boop_bb8/bb8_core/echo_responder.py && echo TOKEN:PRESENT'
```

## TR-005 — s6 restart loop (controller exits)

**Fingerprint**

Logs repeat every few seconds: Starting bridge controller… / version_probe.

Container restarts quickly; no steady run.

**Root Cause**

run.sh starts a module that exits (non-blocking).

**Fix (decisive) — wrapper blocks and supervises**

```bash
# addon/run.sh
#!/usr/bin/with-contenv bash
set -euo pipefail
export PYTHONUNBUFFERED=1
cd /usr/src/app
VENV=${VIRTUAL_ENV:-/opt/venv}
PY="$VENV/bin/python"; command -v "$PY" >/dev/null 2>&1 || PY="$(command -v python3 || command -v python)"
echo "$(date -Is) [BB-8] RUNLOOP start (ENABLE_BRIDGE_TELEMETRY=${ENABLE_BRIDGE_TELEMETRY:-0})"
exec "$PY" -m bb8_core.bridge_controller
```

s6 service

```bash
# addon/services.d/ble_bridge/run
#!/usr/bin/with-contenv bash
set -euo pipefail
exec /usr/bin/env bash /usr/src/app/run.sh
```

**Verify**

Single RUNLOOP start followed by steady logs, no rapid restarts.

## TR-006 — STP5 Telemetry attestation: no echoes observed

**Fingerprint**

`FAIL: TELEMETRY_ATTEST; metrics show echo_count: 0.`

**Root Cause**

Echo responder not running (no subscriber on bb8/echo/cmd).

**Fix (decisive) — add responder as s6 service**

```python
# addon/bb8_core/echo_responder.py  (minimal)
# Uses paho (v1 deprecation allowed in tests), replies and emits telemetry.
# [Place your working version here — omitted for brevity if already committed.]
```

```bash
# addon/services.d/echo_responder/run
#!/usr/bin/with-contenv bash
set -euo pipefail
cd /usr/src/app
VENV=${VIRTUAL_ENV:-/opt/venv}
PY="$VENV/bin/python"; command -v "$PY" >/dev/null 2>&1 || PY="$(command -v python3 || command -v python)"
exec "$PY" -m bb8_core.echo_responder
```

**Verify**

```bash
# In container
docker exec "$CID" bash -lc 'test -x /etc/services.d/echo_responder/run && echo TOKEN:ECHO_SERVICE_OK'
# Attest (≥10s window)
bash ops/attest/attest_stp5_telemetry.sh
# Expect: TELEMETRY_ATTEST_OK, echo_count >= 3, p95 RTT <= 250ms
```

## TR-007 — Quick MODE check (LOCAL_DEV vs PUBLISH)

**Detector**

```bash
CFG=/addons/local/beep_boop_bb8/config.yaml
sed 's/#.*$//' "$CFG" | grep -Eq '^[[:space:]]*image:[[:space:]]*' && echo "MODE:PUBLISH" || echo "MODE:LOCAL_DEV"
```

## TR-008 — “pull access denied / image … does not exist”

**Fingerprint**

pull access denied for local/...

Image local/...:tag does not exist

**Root Cause**

In PUBLISH mode without a pushed image for the requested tag.

**Fix (decisive)**

Switch to LOCAL_DEV (comment image:) or push image to registry with matching version:.

## TR-009 — Report sink missing

**Fingerprint**

tee: /config/reports/...: No such file or directory

**Fix**

```bash
mkdir -p /config/reports /data/reports
echo "TOKEN: REPORT_SINK_OK" | tee -a /config/reports/deploy_receipt.txt
```

---

## Shared Snippets

### A) Debian-only Dockerfile skeleton (venv)
```Dockerfile
ARG BUILD_FROM=ghcr.io/home-assistant/aarch64-base-debian:bookworm
FROM ${BUILD_FROM}

ENV PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1 \
    VIRTUAL_ENV=/opt/venv PATH="/opt/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

WORKDIR /usr/src/app
COPY bb8_core/   /usr/src/app/bb8_core/
COPY app/        /usr/src/app/app/
COPY services.d/ /etc/services.d/
COPY run.sh      /usr/src/app/run.sh
COPY requirements.txt* /usr/src/app/

RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 python3-venv python3-pip ca-certificates jq \
 && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv "/opt/venv" \
 && /opt/venv/bin/pip install -U pip setuptools wheel \
 && if [ -f /usr/src/app/requirements.txt ]; then /opt/venv/bin/pip install -r /usr/src/app/requirements.txt ; fi \
 && chmod +x /usr/src/app/run.sh

ENTRYPOINT ["/init"]
```

### B) Mode-aware config.yaml (LOCAL_DEV)
```yaml
name: "HA-BB8"
slug: "beep_boop_bb8"
version: "2025.8.21.4"
arch: ["aarch64"]
startup: services
init: false
# LOCAL_DEV: omit image:
build:
  dockerfile: Dockerfile
  args:
    BUILD_FROM: "ghcr.io/home-assistant/{arch}-base-debian:bookworm"
```

### Validation Checklist (copy-paste)
```bash
# MODE
CFG=/addons/local/beep_boop_bb8/config.yaml
sed 's/#.*$//' "$CFG" | grep -Eq '^[[:space:]]*image:[[:space:]]*' && echo "MODE:PUBLISH" || echo "MODE:LOCAL_DEV"

# Rebuild + Start
ha addons reload && ha addons rebuild local_beep_boop_bb8 && ha addons start local_beep_boop_bb8

# Container health
CID="$(docker ps --filter name=addon_local_beep_boop_bb8 --format '{{.ID}}')"
test -n "$CID" || { echo "FAIL: container not running"; exit 3; }
docker exec "$CID" bash -lc 'test -f /usr/src/app/run.sh && echo TOKEN:RUNNER_OK'
docker exec "$CID" bash -lc 'test -x /etc/services.d/ble_bridge/run && echo TOKEN:S6_BRIDGE_OK'
docker exec "$CID" bash -lc 'test -x /etc/services.d/echo_responder/run && echo TOKEN:S6_ECHO_OK'

# Telemetry STP5 (≥10s window)
bash ops/attest/attest_stp5_telemetry.sh
# Expect: TELEMETRY_ATTEST_OK
```

---

### tools/troubleshooting_index.json (new)

```json
{
  "contract": "troubleshooting_index_v1",
  "last_updated": "2025-08-28",
  "map": [
    {
      "id": "TR-001",
      "match_any": ["Can't rebuild a image based add-on"],
      "fix": "Comment out image: in config.yaml to enter LOCAL_DEV; reload/rebuild/start."
    },
    {
      "id": "TR-002",
      "match_any": ["apk: command not found"],
      "fix": "Use Debian-only apt-get in Dockerfile; ensure BUILD_FROM is *-base-debian:bookworm."
    },
    {
      "id": "TR-003",
      "match_any": ["COPY addon/", "checksum of ref ... not found"],
      "fix": "Paths in Dockerfile are relative to build context (addon/); remove COPY addon/* lines."
    },
    {
      "id": "TR-004",
      "match_any": ["mkstemp", "Permission denied (13)"],
      "fix": "Use rsync --inplace or SSH direct write fallback."
    },
    {
      "id": "TR-005",
      "match_any": ["Starting bridge controller…", "repeated version_probe"],
      "fix": "Make run.sh exec a blocking controller; ensure s6 service uses wrapper."
    },
    {
      "id": "TR-006",
      "match_any": ["FAIL: TELEMETRY_ATTEST", "echo_count: 0"],
      "fix": "Add s6 echo_responder service; re-run STP5 with ≥10s window."
    },
    {
      "id": "TR-008",
      "match_any": ["pull access denied", "image ... does not exist"],
      "fix": "Use LOCAL_DEV (comment image) or publish/push the image matching version."
    },
    {
      "id": "TR-009",
      "match_any": ["No such file or directory", "reports/deploy_receipt.txt"],
      "fix": "mkdir -p /config/reports before writing receipts."
    }
  ]
}
```

---

## Copilot-ready integration plan

```bash
# 1) Add new files
git add docs/TROUBLESHOOTING_RECIPES.md tools/troubleshooting_index.json

# 2) Link from OPERATIONS_OVERVIEW.md (optional but recommended)
# Insert a bullet under "Troubleshooting Playbook" section:
# - See docs/TROUBLESHOOTING_RECIPES.md for machine-friendly recipes and detectors.
git commit -m "docs(ops): add machine-friendly troubleshooting recipes + index map"

# 3) (Optional) CI artifact: ship index in releases
# If you have an ops packaging step, include tools/troubleshooting_index.json

# 4) Push + open PR
git push origin fix/docs-troubleshooting
# Then open PR; CI will lint and store artifacts.

# 5) After merge: sync to HA runtime (LOCAL_DEV)
rsync -av --delete --exclude-from ops/rsync_runtime.exclude addon/ /Volumes/addons/local/beep_boop_bb8/
# Rebuild + start
ssh homeassistant 'ha addons reload && ha addons rebuild local_beep_boop_bb8 && ha addons start local_beep_boop_bb8'
```

---

## Adaptation guidance (apply fixes to similar cases)

- **Build context mistakes:** Any path in Dockerfile must be within the build context (for HA LOCAL_DEV, the context is addon/). Remove any COPY addon/... lines—use COPY dir/ /dest/.
- **Mode confusion:** If you see pull/publish errors, you are in PUBLISH. Comment out image: to force LOCAL_DEV, or push/pin the registry image.
- **Base OS mismatch:** Pick one base family and stick to its package manager. For HA Debian base, use apt-get; never mix with apk.
- **s6 loops:** The process launched by s6 must block. Wrap controllers with a small runner that execs the Python module (no backgrounding).
- **rsync perms:** When atomic replace is blocked, use --inplace or an SSH “here-doc” fallback to write files directly.
