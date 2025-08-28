# OPERATIONS_CLOSEOUT.md — End-to-End Closeout Plan (LOCAL_DEV)

> Canonical, machine-friendly checklist for session closeout, suitable for manual execution or automation. Use this as your reference for future sessions and as a basis for scripting.

> related script: ops/closeout_plan.sh

---

## A) Workspace Sanity & Sync

1. **Validate workspace structure and tokens:**
   - `bash ops/workspace/validate_paths_map.sh | tee reports/paths_health_receipt.txt`
   - Check for all expected `TOKEN:` lines in `reports/paths_health_receipt.txt`.

2. **Sync add-on subtree to HA runtime (prefer SMB mount):**
   - `rsync -av --inplace --delete --exclude '.DS_Store' --exclude-from ops/rsync_runtime.exclude addon/ /Volumes/addons/local/beep_boop_bb8/`
   - Emit: `TOKEN: SYNC_OK`

   **Gate A:**
   - Pass if `TOKEN: PATHS_MAP_OK` and `TOKEN: SYNC_OK` are present.

   **Fix & Re-run:**
   - If rsync fails due to permissions, use the SMB mount and re-run the sync.

---

## B) HA Box (Runtime) Setup

3. **Ensure report sink exists:**
   - `mkdir -p /config/reports && echo "TOKEN: REPORT_SINK_OK" | tee -a /config/reports/deploy_receipt.txt`

4. **Verify LOCAL_DEV mode in config:**
   - `sed -n '1,60p' /addons/local/beep_boop_bb8/config.yaml | grep -E '^(version:|image:|build:)'`
   - Expect: `version:` and `build:` present, no uncommented `image:`.

5. **Reload and rebuild add-on:**
   - `ha addons reload`
   - `ha addons rebuild local_beep_boop_bb8`
   - `ha addons start local_beep_boop_bb8 || true`

6. **Check add-on state and version:**
   - `ha addons info local_beep_boop_bb8 | grep -E 'state:|version:'`

   **Gate B:**
   - Pass if `state: started`, correct `version`, and no "not available inside store" message.

   **Fix & Re-run:**
   - If not available, reload the add-on store in HA UI and repeat steps 4–6.

---

## C) Container & Runtime Verification

7. **Verify container and entrypoint:**
   - `CID=$(docker ps --filter name=addon_local_beep_boop_bb8 --format '{{.ID}}')`
   - `docker exec "$CID" bash -lc 'test -f /usr/src/app/run.sh && echo TOKEN: RUNTIME_RUN_SH_PRESENT || echo FAIL: RUN_SH_MISSING'`
   - `docker exec "$CID" bash -lc 'echo "PY=$(command -v python)"; python -c "import sys; print(sys.executable)"'`
   - `docker exec "$CID" bash -lc '/opt/venv/bin/python -c "import bb8_core.main as m; print(\"TOKEN: MODULE_OK\")"'`

8. **Check add-on logs for expected lines:**
   - `ha addons logs local_beep_boop_bb8 --lines 100 | grep -E 'version_probe|Starting bridge controller' || true`

9. **Record runtime receipts:**
   - `echo "TOKEN: CLEAN_RUNTIME_OK"`
   - `echo "TOKEN: DEPLOY_OK"`
   - `echo "TOKEN: VERIFY_OK" | tee -a /config/reports/deploy_receipt.txt`

   **Gate C:**
   - Pass if `TOKEN: RUNTIME_RUN_SH_PRESENT`, Python executable is `/opt/venv/bin/python`, and logs show expected lines.

   **Fix & Re-run:**
   - If run.sh or Python checks fail, verify Dockerfile and rebuild.

---

## D) Minimal Function Checks (Optional, Soft Gate)

10. **Discovery topic existence:**
    - `mosquitto_sub -h 127.0.0.1 -p 1883 -v -t 'homeassistant/#' -C 1 -W 3 || echo "INFO: no discovery in 3s window"`

11. **Echo scalar roundtrip:**
    - `mosquitto_pub -h 127.0.0.1 -p 1883 -t 'bb8/echo/cmd' -m '{"value":1,"ts":'$(date +%s)'}'`
    - `mosquitto_sub -h 127.0.0.1 -p 1883 -v -t 'bb8/echo/#' -C 1 -W 3 || echo "INFO: no echo observed in 3s"`

    **Gate D:**
    - Pass if any discovery or echo line observed (does not block closure).

---

## E) Final Acceptance

- All gates (A, B, C) pass.
- `ha addons info local_beep_boop_bb8` shows correct version and state.
- `/config/reports/deploy_receipt.txt` contains all required tokens.

---

## What NOT to Change

- Do not toggle `image:` in `addon/config.yaml` (stay in LOCAL_DEV).
- Do not add new patches.
- Do not rebuild outside HA Supervisor except for diagnostics.

---

## If Blocked

- Use HA UI to rebuild/start add-on.
- If Supervisor warns "removed from repository", reload the store and ensure `/addons/local/beep_boop_bb8` exists.

---

## Session Closeout

Once Gate C receipts are captured and the add-on is **started**, the session is considered stable and closed. Further work (telemetry, CI) should be scheduled for a new session.
