---
title: ADR-0004: Conditional Runtime Tools Policy (CRTP) & Workspace Drift Enforcement
date: 2025-08-26
status: Approved
---

# ADR-0004 — Conditional Runtime Tools Policy (CRTP) & Workspace Drift Enforcement

**Status:** Accepted
**Date:** 2025-08-26
**Authors:** Strategos
**Related:** ADR-0001 (Dual-Clone Topology), ADR-0002 (Dependency Policy)
**Supersedes/Clarifies:** Any prior ad‑hoc guidance on `addon/tools/` and `addon/scripts/` allowance

---

## 1. Context

The project ships a Home Assistant add‑on from the `addon/` subtree (ADR‑0001). We need a consistent rule for when helper scripts may live **inside** the shipped subtree (`addon/tools/`, `addon/scripts/`) versus remaining **workspace‑only** (`ops/`, `scripts/`). Inconsistent guidance led to CI drift flags and confusion.

---

## 2. Decision (CRTP — Conditional Runtime Tools Policy)

A script (or helper directory) may **remain in the shipped add‑on subtree** only when at least one of the following is true:

1. **Referenced by the image build or entry**: The script is used to build or run the image and is referenced by `Dockerfile` (`COPY|ADD|RUN|ENTRYPOINT|CMD`), **or**
2. **Invoked at runtime**: The container calls it (e.g., from `run.sh`, s6 service, or Python entrypoints), **or**
3. **Explicitly whitelisted**: A marker file exists in the subtree:

   * `addon/.allow_runtime_tools` (allows `addon/tools/`)
   * `addon/.allow_runtime_scripts` (allows `addon/scripts/`)

> If none apply, the asset belongs in the **workspace** and must not ship in `addon/`.

---

## 3. Enforcement & Tokens

### 3.1 Always‑forbidden in `addon/`

* `.github`, `docs`, `ops`, `reports`, nested `addon/`, any nested `.git`

### 3.2 Conditionally‑allowed (CRTP)

* `addon/tools/`, `addon/scripts/` — allowed **only** via (1) Dockerfile/entry reference, (2) runtime invocation, or (3) marker file.

### 3.3 CI/Guard Behavior (machine‑friendly)

**Canonical token catalog:** see **ADR-0001 §Governance Tokens**.
**CRTP-specific tokens (success):** `TOKEN: TOOLS_ALLOWED`, `TOKEN: SCRIPTS_ALLOWED`.
**Typical drift codes (failure):** `DRIFT: tools_unreferenced_in_dockerfile`, `DRIFT: scripts_unreferenced_in_dockerfile`.
Other drift/error codes (e.g., config/dockerfile missing) are defined and enforced by repo guards referencing ADR-0001.

---

## 4. CI Guard (canonical snippet)

```yaml
- name: Structure guard (ADR-0001 + CRTP)
  run: |
    set -euo pipefail
    test -d addon || (echo "addon/ missing" && exit 2)
    if [ -d addon/.git ]; then echo "addon is a repo (forbidden)"; exit 3; fi

    # Forbidden workspace-only dirs (always)
    for d in .github docs ops reports addon; do
      if [ -e "addon/$d" ]; then echo "DRIFT:forbidden_in_addon:$d"; exit 4; fi
    done

    # Required files + mode
    test -f addon/config.yaml || (echo "DRIFT:missing_config_yaml" && exit 5)
    if rg -n '^\s*image:\s*' addon/config.yaml >/dev/null; then
      echo "MODE: PUBLISH"
      rg -n '^\s*version:\s*' addon/config.yaml >/dev/null || (echo "DRIFT:version_missing_in_publish_mode" && exit 7)
    else
      echo "MODE: LOCAL_DEV"
      test -f addon/Dockerfile  || (echo "DRIFT:dockerfile_missing_in_local_dev" && exit 6)
      echo "TOKEN: DEV_LOCAL_BUILD_FORCED"
    fi

    # CRTP: tools/ allowed if referenced by Dockerfile or marker present
    if [ -d addon/tools ]; then
      if ! grep -Ei '(COPY|ADD|RUN|ENTRYPOINT|CMD).*tools/' addon/Dockerfile >/dev/null 2>&1 \
         && [ ! -f addon/.allow_runtime_tools ]; then
        echo "DRIFT:tools_unreferenced_in_dockerfile"; exit 8
      else
        echo "TOKEN: TOOLS_ALLOWED"
      fi
    fi

    # CRTP: scripts/ allowed if referenced by Dockerfile or marker present
    if [ -d addon/scripts ]; then
      if ! grep -Ei '(COPY|ADD|RUN|ENTRYPOINT|CMD).*scripts/' addon/Dockerfile >/dev/null 2>&1 \
         && [ ! -f addon/.allow_runtime_scripts ]; then
        echo "DRIFT:scripts_unreferenced_in_dockerfile"; exit 9
      else
        echo "TOKEN: SCRIPTS_ALLOWED"
      fi
    fi

    echo "TOKEN: STRUCTURE_OK"
```

---

## 5. PR Annotation (for acceptance)

Include a machine‑parsable block when keeping a script in `addon/`:

```
CRTP-ALLOW:
  path: addon/tools/healthcheck.sh
  reason: container health probe invoked by s6 longrun
  referenced_by: run.sh:23
  safety: shellcheck-clean, no-secrets, bounded-exit
  owner: pythagoras
```

Marker‑based whitelist example:

```
CRTP-MARKER:
  file: addon/.allow_runtime_tools
  entries:
    - addon/tools/diag_snapshot.sh
  reason: on-device diagnostics; manual invocation on support
  safety: shellcheck-clean, ≤100KB, no elevated privileges
```

---

## 6. Safety Gate (must pass)

* No hardcoded secrets/credentials
* Minimal privileges (no `sudo`/package install at runtime unless justified)
* Bounded execution; non‑zero exit on failure
* Static analysis clean (e.g., `shellcheck` for sh)
* Reasonable size budget (guideline: ≤ 1 MB total for `addon/tools/` unless justified)
* License headers for third‑party code

---

## 7. Migration & Roll‑out

1. **Inventory** current `addon/tools/` and `addon/scripts/` assets.
2. **Decide** per CRTP: keep, move to `ops/`, or mark via `.allow_runtime_*`.
3. **Add references** in Dockerfile or entrypoint where appropriate.
4. **Annotate PR** with `CRTP-ALLOW` / `CRTP-MARKER`.
5. **Enable CI guard** (Section 4).
6. **Verify** drift checker emits `TOKEN: TOOLS_ALLOWED`/`SCRIPTS_ALLOWED` and no `DRIFT:*`.

Rollback: Remove markers and/or Dockerfile references; move unneeded scripts back to workspace paths.

---

## 8. Rationale & Consequences

* Keeps the shipped image minimal and predictable.
* Preserves developer ergonomics via explicit whitelisting (markers) when runtime diagnostics are needed.
* Makes CI and local drift checks **deterministic**, with clear tokens and failure codes.

---

## 9. Backwards Compatibility

* Existing images with `addon/tools/` continue to work if either referenced by Dockerfile/entrypoint or whitelisted via marker.
* CI will begin flagging unreferenced tools/scripts as drift; follow Migration to resolve.

---

## 10. Acceptance Tests (Binary)

* Given `addon/tools/` exists and `Dockerfile` references it → CI emits `TOKEN: TOOLS_ALLOWED` and passes.
* Given `addon/tools/` exists and marker `addon/.allow_runtime_tools` exists → CI emits `TOKEN: TOOLS_ALLOWED` and passes.
* Given `addon/tools/` exists with neither reference nor marker → CI emits `DRIFT: tools_unreferenced_in_dockerfile` and fails.

---

## 11. Operational Hooks

* Update `docs/OPERATIONS_OVERVIEW.md` to reference ADR‑0004 (Key rules + CI snippet).
* Ensure `ops/check_workspace_drift.sh` matches CRTP logic (tokens and drift codes).

---

## 12. Appendix — Quick Checks

```bash
# Detect Dockerfile references to tools/scripts
grep -Ei '(COPY|ADD|RUN|ENTRYPOINT|CMD).*tools/' addon/Dockerfile
grep -Ei '(COPY|ADD|RUN|ENTRYPOINT|CMD).*scripts/' addon/Dockerfile

# Find runtime invocations
rg -n '/tools/' addon/run.sh addon/bb8_core -g '!**/__pycache__/**' -g '!**/*.pyc'

# Marker presence
test -f addon/.allow_runtime_tools    && echo 'TOKEN: TOOLS_MARKER_PRESENT'
test -f addon/.allow_runtime_scripts  && echo 'TOKEN: SCRIPTS_MARKER_PRESENT'
```

## Last updated
_Last updated: 2025-08-26_