# BB‑8 Addon — QA Report (STP4, PR Stabilization)

> **Purpose:** Single‑file QA artifact you can fill by pasting the outputs you just collected. Designed to be committed under `reports/qa_<timestamp>/QA_REPORT.md`.

---

## 0) Metadata

* **Project:** Beep Boop BB‑8 Addon
* **Branch:** `feat/strict-stp4-device-echo`
* **Commit SHA:** `<paste git rev-parse --short HEAD>`
* **Runner host:** `<OS & version>`
* **Python:** `<python --version>`
* **Timestamp:** `<YYYY-MM-DD HH:MM:SS TZ>`
* **Log dir:** `<absolute path, e.g., /Volumes/addons/local/beep_boop_bb8/reports/qa_YYYYMMDD_HHMMSS>`

## 1) Environment & Toggles

* **MQTT_HOST:** `<expected broker ip, e.g., 192.168.0.129>`
* **MQTT_BASE:** `bb8`
* **ENABLE_BRIDGE_TELEMETRY:** `<0|1>`
* **REQUIRE_DEVICE_ECHO:** `<0|1>`
* **EVIDENCE_TIMEOUT_SEC:** `3.0`
* **Notes:** `<any env overrides / .env file used>`

---

## 2) Lint / Style / Types

### 2.1 black

* **Command:** `black . | tee "$logdir/black.log"`
* **Summary:** `<e.g., 0 files reformatted, 4 files would be reformatted>`
* **Attach excerpt:**

```text
<paste from $logdir/black.log>
```

### 2.2 ruff

* **Command:** `ruff check . | tee "$logdir/ruff.log"`
* **Summary:** `<e.g., 0 errors, 0 warnings, N fixed>`
* **Attach excerpt:**

```text
<paste from $logdir/ruff.log>
```

### 2.3 mypy

* **Command:**

  ```bash
  cd /Volumes/addons/local
  PYTHONPATH=/Volumes/addons/local mypy beep_boop_bb8 | tee "$logdir/mypy.log"
  cd -
  ```

* **Summary:** `<e.g., Success: no issues found in X source files>`
* **Attach excerpt:**

```text
<paste from $logdir/mypy.log>
```

---

## 3) Tests & Coverage

### 3.1 pytest (all)

* **Command:** `pytest -q --maxfail=1 | tee "$logdir/pytest.log"`
* **Summary:** `<e.g., 124 passed, 3 skipped, 0 failed>`
* **Failures (if any):**

  * `<test::name> — <short reason>`
* **Attach excerpt:**

```text
<paste from $logdir/pytest.log>
```

### 3.2 Coverage snapshot (if used)

* **Overall:** `<%>`
* **Key files:**

  * `bb8_core/mqtt_dispatcher.py`: `<%>`
  * `bb8_core/bb8_presence_scanner.py`: `<%>`
  * `bb8_core/facade.py`: `<%>`
* **Method:** `<pytest-cov, other, or N/A>`

---

## 4) Discovery & Seam Verification (binary)

* [ ] **Seam active:** log contains `scanner_pub_source=hook` **or** explicit seam patch invocation confirmed.
* [ ] **Idempotency:** second call to discovery yields **0** new publishes (`test_idempotency`).
* [ ] **Gate off respected:** when disabled, **0** publishes (`test_gate_off`).
* [ ] **Smoke log compat:** found `discovery: published` **or** legacy `Published HA discovery`.
* [ ] **State echo topics:** command triggers publish to expected `bb8/<device>/state/*` topics in smoke test.

**Evidence snippets:**

```text
<paste relevant lines proving each checkbox>
```

---

## 5) Security & Static Checks

* **bandit:** `<summary>`
* **safety:** `<summary>`
* **Notes:** `<any ignores or justifications>`

---

## 6) Acceptance Gate (PR Stabilization)

* [ ] Lint/style clean (black/ruff OK)
* [ ] Types green (mypy OK)
* [ ] Tests pass (no unexpected failures; seam & smoke tests green)
* [ ] No high‑severity security findings
* [ ] Evidence for discovery behavior attached (below)

**Verdict:** `<PASS | FAIL>`

**Reviewer notes:**

> `<brief human notes on risk, regressions, or TODOs>`

---

## 7) Artifacts to Attach

* `$logdir/black.log`
* `$logdir/ruff.log`
* `$logdir/mypy.log`
* `$logdir/pytest.log`
* (optional) Coverage report files
* Evidence dump(s):

  * `reports/<ts>/evidence_manifest.json`
  * `reports/<ts>/ha_mqtt_trace_snapshot.jsonl` (or `.json`)
  * `reports/<ts>/ha_discovery_dump.json`

---

## 8) Known Issues / Follow‑ups

* `<e.g., BLE loop thread refactor pending, facade circular import, coverage to 80%>`

---

## 9) Next Session Hook (STP4 strict)

* **When resuming:**

  * Disable shim; set `REQUIRE_DEVICE_ECHO=1`, `ENABLE_BRIDGE_TELEMETRY=1`.
  * Implement device‑originated echoes for power/stop/drive/heading/speed (retain=false).
  * LED/state remains `{r,g,b}` only (retain=false).
  * Run BLE coroutines on dedicated event‑loop thread.

**Hand‑off intent:** Once this QA report is PASS, cut a continuity checkpoint and start a fresh session for **STP4 strict graduation**.
