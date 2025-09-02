# PATHS_MAP

## Add-on Runtime Paths

| Path | Description |
|------|-------------|
| /addons/local/beep_boop_bb8 | Main add-on folder (config.yaml, Dockerfile, code) |
| /usr/src/app/bb8_core/      | Python runtime code (in container) |
| /usr/src/app/app/           | App scripts (in container) |
| /etc/services.d/            | s6 service scripts (in container) |
| /data/options.json          | Supervisor-generated config (in container) |
| /config/reports/            | Evidence, QA, telemetry, receipts |

## Workspace Paths

| Path | Description |
|------|-------------|
| addon/                 | Shipped subtree (container context) |
| addon/bb8_core/        | Runtime code |
| addon/config.yaml      | Add-on manifest |
| addon/Dockerfile       | Container build recipe |
| addon/run.sh           | Entrypoint wrapper |
| addon/tests/           | Test suite (pytest) |
| ops/                   | Scripts & runners (not shipped) |
| reports/               | Evidence sink (QA, telemetry, receipts) |
| scripts/               | Wrappers (verify/deploy) |
| .github/               | CI workflows |

## Operational Notes

- All paths and structure conform to OPERATIONS_OVERVIEW.md and TROUBLESHOOTING_RECIPES.md.
- For Dockerfile, run.sh, and s6 scripts, see OPERATIONS_OVERVIEW.md for canonical examples.
- All evidence and QA artifacts are written to reports/.
- Supervisor always uses /addons/local/beep_boop_bb8 as the runtime folder.
- No .git folders are present in runtime.

## 1) Canonical Paths Map (with examples)

| Subtree                              | Absolute path                                       | Ships?        | 2 example files (absolute)                                                                                                                           |
| ------------------------------------ | --------------------------------------------------- | ------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Workspace root**                   | `/Users/evertappels/Projects/HA-BB8`                | N/A           | `README.md` (if present); `pyproject.toml` (if present)                                                                                              |
| **Add‑on build context**             | `/Users/evertappels/Projects/HA-BB8/addon`          | **Yes**       | `/Users/evertappels/Projects/HA-BB8/addon/config.yaml`; `/Users/evertappels/Projects/HA-BB8/addon/Dockerfile`                                        |
| **Runtime code**                     | `/Users/evertappels/Projects/HA-BB8/addon/bb8_core` | **Yes**       | `/Users/evertappels/Projects/HA-BB8/addon/bb8_core/ble_link.py`; `/Users/evertappels/Projects/HA-BB8/addon/bb8_core/mqtt_probe.py`                   |
| **Add‑on tests**                     | `/Users/evertappels/Projects/HA-BB8/addon/tests`    | **Yes**       | `/Users/evertappels/Projects/HA-BB8/addon/tests/test_ble_event_loop.py`; `/Users/evertappels/Projects/HA-BB8/addon/tests/test_facade_attach_mqtt.py` |
| **Runtime tools (CRTP)**             | `/Users/evertappels/Projects/HA-BB8/addon/tools`    | **Conditional** | marker: `addon/.allow_runtime_tools`, or referenced by Dockerfile/run.sh |
| **Runtime scripts (CRTP)**           | `/Users/evertappels/Projects/HA-BB8/addon/scripts`  | **Conditional** | marker: `addon/.allow_runtime_scripts`, or referenced by Dockerfile/run.sh |
| **Workspace ops (not shipped)**      | `/Users/evertappels/Projects/HA-BB8/ops`            | **No**        | `/Users/evertappels/Projects/HA-BB8/ops/run_strict_attestation.sh`; `/Users/evertappels/Projects/HA-BB8/ops/check_workspace_drift.sh`                |
| **Evidence sink (not shipped)**      | `/Users/evertappels/Projects/HA-BB8/reports`        | **No**        | `/Users/evertappels/Projects/HA-BB8/reports/qa_report_contract_v1.json`; `/Users/evertappels/Projects/HA-BB8/reports/evidence_manifest.json`         |
| **Workspace scripts (not shipped)**  | `/Users/evertappels/Projects/HA-BB8/scripts`        | **No**        | `/Users/evertappels/Projects/HA-BB8/scripts/verify_workspace.sh`; `/Users/evertappels/Projects/HA-BB8/scripts/deploy_to_ha.sh`                       |
| **CI workflows (not shipped)**       | `/Users/evertappels/Projects/HA-BB8/.github`        | **No**        | `/Users/evertappels/Projects/HA-BB8/.github/workflows/repo-guards.yml`; another workflow file                                                        |
| **Docs (not shipped)**               | `/Users/evertappels/Projects/HA-BB8/docs`           | **No**        | `/Users/evertappels/Projects/HA-BB8/docs/OPERATIONS_OVERVIEW.md`; `/Users/evertappels/Projects/HA-BB8/docs/ADR-0004-runtime-tools-policy.md`         |
| **HA runtime (on HA box)**           | `/addons/local/beep_boop_bb8`                       | Build context | `/addons/local/beep_boop_bb8/config.yaml`; `/addons/local/beep_boop_bb8/Dockerfile`                                                                  |
| **Mounted runtime (on dev machine)** | `/Volumes/addons/local/beep_boop_bb8`               | Optional Mirror | `/Volumes/addons/local/beep_boop_bb8/config.yaml`; `/Volumes/addons/local/beep_boop_bb8/Dockerfile`                                                  |
| **Rootfs overlay (reserved)**        | `/Users/evertappels/Projects/HA-BB8/addon/rootfs`   | **Conditional** | s6 overlay, udev rules, etc. (see Flexible Guidelines)

**CRTP:** Conditionally allowed only if referenced by Dockerfile/entrypoint or whitelisted via marker (see ADR-0004).
If absent, drift checks MUST skip runtime diffs and still pass structure validation.

---

## 2) Strict Guidelines (MUST)

**S1. Dual‑clone topology**

* All Git operations occur at `WS_ROOT`.
* `addon/` **must not** contain `.git` or submodules.

**S2. Add‑on content boundary**

* Only shippable runtime content lives under `addon/` (code, config, Dockerfile, tests).
* The following **must not** appear under `addon/`: `.github/`, `docs/`, `ops/`, `reports/`, nested `addon/`, any `.git`.

**S3. Buildability in place**

**S3. Build mode semantics (MUST)**  
- **LOCAL_DEV:** `image:` is **absent** (commented). `addon/Dockerfile` **must** exist and be valid.  
- **PUBLISH:** `image:` is **present** and `version:` **must** be set (semver-like) and aligned to the registry tag.

**S4. Runtime path**

* HA runtime path is `/addons/local/beep_boop_bb8`. **Do not** run `git` there.
* Rebuild sequence on HA: `ssh babylon-babes@homeassistant "ha addons reload" && ssh babylon-babes@homeassistant "ha addons rebuild local_beep_boop_bb8"`.

**S5. Evidence location**

* All evidence artifacts (QA report, manifest, telemetry, receipts) live in `WS_ROOT/reports/`.

**S6. Tokens (canonical)**

* Token catalog is defined in ADR‑0001; CRTP tokens in ADR‑0004. Emit exact strings.

---

## 3) Flexible Guidelines (MAY) — Near‑term expansion

**F1. CRTP (Conditional Runtime Tools Policy)**

* `addon/tools/` and `addon/scripts/` are allowed **only if** referenced by `Dockerfile` (`COPY|ADD|RUN|ENTRYPOINT|CMD`), called by `run.sh`/code, **or** whitelisted via markers:

  * `addon/.allow_runtime_tools`
  * `addon/.allow_runtime_scripts`
* When allowed, emit tokens: `TOKEN: TOOLS_ALLOWED`, `TOKEN: SCRIPTS_ALLOWED`.

**F2. Reserved optional subtrees (future)**

- `addon/bin/` — small runtime utilities. **Gate:** referenced or marker `addon/.allow_runtime_bin`.
- `addon/assets/` — static files (schemas/icons). **Gate:** referenced or marker `addon/.allow_runtime_assets`.
- `addon/services/` — s6 service files if adopted. **Gate:** referenced by Dockerfile or entry.
- `addon/rootfs/` — root filesystem overlay for s6 services, udev rules, etc.  
  **Gate:** must follow HA add-on s6 overlay structure (`/etc/s6-overlay/...`) and be referenced by Dockerfile (`COPY rootfs/ /`).
  **Token on pass:** `TOKEN: ROOTFS_ALLOWED`
- Token on pass (if present and properly referenced):
  - BIN_ALLOWED / ASSETS_ALLOWED / SERVICES_ALLOWED / ROOTFS_ALLOWED

**F3. Size & safety budgets**

* Soft cap: ≤ **1 MB** aggregate for optional tool trees unless justified.
* No secrets in any shipped files; `shellcheck` clean for `*.sh`.

**F4. Dev‑only helpers**

* Place ad‑hoc dev helpers under `ops/` or `scripts/` (never in `addon/`).
* If a helper becomes runtime‑required, promote it with CRTP + references/marker.

---

## 4) Quick Path Validation (copy‑paste)

**Workspace vs runtime diff**

```bash
diff -ruN --exclude='__pycache__' --exclude='*.pyc' 
  "$WS_ROOT/addon" "$RUNTIME_MOUNT" || true
```

**Build context sanity (HA box)**

```bash
ssh babylon-babes@homeassistant "ls -lah /addons/local/beep_boop_bb8"
ssh babylon-babes@homeassistant "(test -f /addons/local/beep_boop_bb8/config.yaml && echo OK) || echo MISSING-config"
(test -f /addons/local/beep_boop_bb8/Dockerfile && echo OK) || echo MISSING-dockerfile
```

**Structure guard (local)**

```bash
[ -d "$WS_ROOT/addon/.git" ] && echo "DRIFT:addon_nested_git" && exit 1 || echo "TOKEN: STRUCTURE_OK"
```

**CRTP checks**

```bash
# tools/scripts referenced or markers present?
grep -Ei '(COPY|ADD|RUN|ENTRYPOINT|CMD).*tools/' "$ADDON_DIR/Dockerfile" || true
grep -Ei '(COPY|ADD|RUN|ENTRYPOINT|CMD).*scripts/' "$ADDON_DIR/Dockerfile" || true
[ -f "$ADDON_DIR/.allow_runtime_tools" ]   && echo "TOKEN: TOOLS_MARKER_PRESENT" || true
[ -f "$ADDON_DIR/.allow_runtime_scripts" ] && echo "TOKEN: SCRIPTS_MARKER_PRESENT" || true
```


**Mode detection & version/variant checks**
```bash
if rg -n '^\s*image:\s*' "$ADDON_DIR/config.yaml" >/dev/null; then
  echo "MODE: PUBLISH"
  rg -n '^\s*version:\s*' "$ADDON_DIR/config.yaml" >/dev/null || echo "DRIFT: version_missing_in_publish_mode"
else
  echo "MODE: LOCAL_DEV"
  [ -f "$ADDON_DIR/Dockerfile" ] || echo "DRIFT: dockerfile_missing_in_local_dev"
  echo "TOKEN: DEV_LOCAL_BUILD_FORCED"
fi

WS_VER=$(awk -F: '/^version:/ {gsub(/[ "\t]/,"",$2); print $2; exit}' "$ADDON_DIR/config.yaml")
RT_VER=$(awk -F: '/^version:/ {gsub(/[ "\t]/,"",$2); print $2; exit}' "$RUNTIME_MOUNT/config.yaml" 2>/dev/null || true)
[ -n "$RT_VER" ] && { [ "$WS_VER" = "$RT_VER" ] && echo "TOKEN: VERSION_SYNC_OK:$WS_VER" || echo "DRIFT: version_mismatch ws=$WS_VER rt=$RT_VER"; }

# Optional: detect that tests are excluded in release image context (heuristic)
grep -Eq 'COPY\s+\.(\s+)?/usr/src/app' "$ADDON_DIR/Dockerfile" || echo "INFO: consider narrowing COPY to exclude tests for release"

# Symlink guard in addon/ (portable: BSD/macOS find uses -type l, not -xtype)
find "$ADDON_DIR" -type l -not -path '*/.venv/*' -print -quit | grep -q . && echo "DRIFT: symlink_present_in_addon" || echo "TOKEN: NO_SYMLINKS_IN_ADDON"

# Emit paths map contract for tools/CI
python3 - <<'PY' > "$WS_ROOT/reports/paths_map_contract_v1.json"
import json, os
print(json.dumps({
  "contract": "paths_map_contract_v1",
  "ws_root": os.environ.get("WS_ROOT"),
  "addon_dir": os.environ.get("ADDON_DIR"),
  "runtime_mount": os.environ.get("RUNTIME_MOUNT"),
  "ha_runtime": os.environ.get("HA_RUNTIME"),
  "slug": os.environ.get("ADDON_SLUG"),
  "remote_addon": os.environ.get("REMOTE_ADDON"),
  "crtp_markers": [".allow_runtime_tools",".allow_runtime_scripts"],
  "reserved_subtrees": ["addon/bin","addon/assets","addon/services","addon/rootfs"],
}, indent=2))
PY
echo "TOKEN: PATHS_MAP_CONTRACT_EMITTED"

# PATHS_MAP_OK token: emit after all mandatory checks pass
# (example: after all above checks succeed)
echo "TOKEN: PATHS_MAP_OK"
```

---

## 5) Source of Truth

* **ADR‑0001 — Dual‑Clone Topology (canonical tokens + structure):** `docs/ADR-0001-workspace-topology.md`
* **ADR‑0004 — CRTP (tools/scripts rules):** `docs/ADR-0004-runtime-tools-policy.md`
* **Operations detail & evidence:** `docs/OPERATIONS_OVERVIEW.md`

---

## Unit-style doc test: path existence health probe

```python
import os, sys, json
MANDATORY = [
    os.environ.get("WS_ROOT"),
    os.environ.get("ADDON_DIR"),
    os.environ.get("HA_RUNTIME"),
]
OPTIONAL = [os.environ.get("RUNTIME_MOUNT")]
results = {}
for p in MANDATORY:
    results[p] = os.path.exists(p)
for p in OPTIONAL:
    if p: results[p] = os.path.exists(p)
print(json.dumps({"paths_health": results}))
if not all(results.values()):
    sys.exit(1)
```

## Last Updated

_Last updated: 2025-08-27_
