````markdown
# ADR-0001: Enforce Device-Originated Echoes for STP4 Strict

**Session Evidence Source:** User message “rehydration_seed” → `acceptance_criteria_next_checkpoint` and `integration architecture` notes; Assistant reply “Execution Mandate” JSON and “Delta Contract” YAML.

## Context
The project is graduating from STP4 with shim to **STP4 strict** where device-originated echoes are required for scalar topics. LED/state is explicitly exempt.

**Problem Statement:** Strict graduation requires evidence that MQTT scalar states originate from the device (not the shim/bridge), while keeping LED/state as pure RGB JSON.

**Investigation Method:** Requirements and contracts were stated and agreed in-session (no execution yet).

**Evidence Gathered:**
- Must include `source: 'device'` for power/stop/drive/heading/speed when `REQUIRE_DEVICE_ECHO=1`.  
- LED/state remains `{r,g,b}` only and is exempt from the `source` gate.  
- MQTT namespace policy: flat `bb8/<behavior>/<action>`; discovery ownership: **scanner only**.  
(All from user seed and assistant contracts.)

## Decision
**Technical Choice:**  
Adopt strict device-echo enforcement for scalar topics with retain=false; LED/state remains `{r,g,b}` (retain=false) and **no** `source` field.

**Command/Configuration:**  
Topics (examples from seed):  
- `bb8/presence/state` (retain=true)  
- `bb8/rssi/state` (retain=true)  
- `bb8/power/state` (retain=false, must carry device echo)  
- `bb8/led/state` (retain=false, payload `{"r","g","b"}` only)

**Validation Results:**  
Not executed in-session. Validation is defined as part of the next checkpoint.

## Consequences

### Positive
- Clear provenance for critical scalar states.
- Consistency of LED payload for UI integrations.

### Negative
- Additional schema enforcement may reject messages without `source:'device'`.

### Unknown/Untested
- Impact on downstream consumers if they previously relied on shim-originated echoes.

## Implementation Evidence

### Commands Verified
```bash
# None executed during this session (pre-execution planning only)
````

### Configuration Discovered

```yaml
environment_toggles:
  MQTT_BASE: "bb8"
  ENABLE_BRIDGE_TELEMETRY: 1
  REQUIRE_DEVICE_ECHO: 1
  EVIDENCE_TIMEOUT_SEC: 3.0
```

### Log Patterns Observed

```
None observed in-session.
```

## Gaps Requiring Further Investigation

* Runtime confirmation that all scalar topics include `source:'device'`.
* Evidence that LED/state remains `{r,g,b}` without extra fields.

## References

* Source: User “rehydration_seed” (MQTT patterns, acceptance criteria, toggles)
* Source: Assistant “Execution Mandate” / “Delta Contract” (enforcement reiteration)
* Tests Performed: None (pre-execution)

---

**Extraction Date:** 2025-09-28
**Session ID/Reference:** STP4-STRICT pre-execution briefing
**Evidence Quality:** Partial (requires validation)

````

---

```markdown
# ADR-0002: Dedicated AsyncIO Event-Loop Thread for BLE

**Session Evidence Source:** User message “known_gaps”; Assistant “Execution Mandate” and “Delta Contract”.

## Context
A prior warning “There is no current event loop” was identified as a risk. The session mandates moving BLE coroutines to a dedicated event-loop thread.

**Problem Statement:** Avoid runtime warnings/deadlocks due to incorrect asyncio loop usage in BLE layer.

**Investigation Method:** Gap identification and mandate issued in-session; no code/logs examined here.

**Evidence Gathered:**  
- Known gap: “BLE event loop must run on dedicated thread (no get_event_loop warning)”.  
- Acceptance must include **no** “There is no current event loop” warnings.

## Decision
**Technical Choice:**  
Run BLE coroutines on a **dedicated asyncio event-loop thread** with clean startup/shutdown hooks.

**Command/Configuration:**  
Not provided as code; requirement stated as acceptance criterion.

**Validation Results:**  
Pending execution; success criterion is absence of the specific warning.

## Consequences

### Positive
- Predictable concurrency model for BLE operations.
- Eliminates known event-loop warning class.

### Negative
- Additional complexity for thread–loop lifecycle management.

### Unknown/Untested
- Performance impact and shutdown edge cases.

## Implementation Evidence

### Commands Verified
```bash
# None executed during this session
````

### Configuration Discovered

```yaml
acceptance_criteria_next_checkpoint.must_meet:
  - "No 'There is no current event loop' warnings"
```

### Log Patterns Observed

```
None observed in-session (warning string specified as a must-not-appear criterion).
```

## Gaps Requiring Further Investigation

* Concrete implementation pattern (e.g., loop-in-thread starter, signal handling).
* Tests asserting the absence of the warning under load.

## References

* Source: User “known_gaps”, “acceptance_criteria_next_checkpoint”
* Source: Assistant “Execution Mandate” / “Delta Contract”

---

**Extraction Date:** 2025-09-28
**Session ID/Reference:** STP4-STRICT pre-execution briefing
**Evidence Quality:** Partial (requires validation)

````

---

```markdown
# ADR-0003: Evidence & QA Gates for STP4 Strict Graduation

**Session Evidence Source:** User “acceptance_criteria_next_checkpoint” and “execution_handoff.qa_suite”; Assistant “Execution Mandate”.

## Context
The session establishes explicit QA commands and binary acceptance gates for graduation.

**Problem Statement:** Define verifiable criteria and QA steps to approve STP4 strict merge.

**Investigation Method:** Requirements captured from seed and restated in mandate.

**Evidence Gathered:**
- QA suite commands listed (format, lint, type-check, tests, security).
- Binary gates: `qa_report.verdict == PASS`, `coverage >= 80%`, “lint clean & types ok & no high-sev security findings”.
- Evidence artifacts to attach: `evidence_manifest.json`, `.jsonl` MQTT trace, discovery dump.

## Decision
**Technical Choice:**  
Adopt the specified QA pipeline and evidence bundle as **must-pass** gates for merge.

**Command/Configuration (as stated):**
```bash
black --check .
ruff check .
mypy --install-types --non-interactive .
pytest -q --maxfail=1 --disable-warnings --cov=bb8_core --cov-report=term-missing
bandit -q -r bb8_core || true
safety check --full-report || true
````

**Validation Results:**
Not run in-session; execution will be performed by Pythagoras and returned as `qa_report_contract_v1`.

## Consequences

### Positive

* Enforces binary acceptance with measurable outputs.
* Ensures baseline test coverage and static analysis.

### Negative

* Pipeline may gate on type stubs or flaky tests if not stabilized.

### Unknown/Untested

* Actual coverage percentage and failure modes under strict mode.

## Implementation Evidence

### Commands Verified

```bash
# Listed commands are mandated; none executed during this session
```

### Configuration Discovered

```yaml
artifacts_index.evidence:
  - "reports/<latest>/evidence_manifest.json"
  - "reports/<latest>/ha_mqtt_trace_snapshot.jsonl"
  - "reports/<latest>/ha_discovery_dump.json"
```

### Log Patterns Observed

```
None observed in-session; results pending qa_report.
```

## Gaps Requiring Further Investigation

* Real qa_report outputs and coverage numbers.
* Schema of evidence_manifest roundtrip and validation logs.

## References

* Source: User “execution_handoff.qa_suite”, “artifacts_index”
* Source: Assistant “Execution Mandate”

---

**Extraction Date:** 2025-09-28
**Session ID/Reference:** STP4-STRICT pre-execution briefing
**Evidence Quality:** Partial (requires validation)

````

---

```markdown
# ADR-0004: Deployment & Rollback Strategy for STP4 Graduation

**Session Evidence Source:** Assistant “Execution Mandate” (risk & rollback), User “runbook_next_actions”.

## Context
Strict mode requires disabling the shim and increasing telemetry; a rollback path is defined.

**Problem Statement:** Enable strict testing safely and provide a clear rollback to restore baseline.

**Investigation Method:** Review of runbook and mandate sections agreed in-session.

**Evidence Gathered:**
- Runbook: disable shim; set `REQUIRE_DEVICE_ECHO=1`, `ENABLE_BRIDGE_TELEMETRY=1`; execute mandate; attach evidence; stamp checkpoint.
- Rollback (pre & post failure) steps specified in mandate.

## Decision
**Technical Choice:**  
Follow the four-step runbook; use environment toggles to switch to strict; if failure, revert to previous commit and re-run with shim.

**Command/Configuration:**  
Environment toggles (from seed) and rollback steps (from mandate).

**Validation Results:**  
Not performed in-session.

## Consequences

### Positive
- Clear, reversible path for trialing strict mode.
- Telemetry increased during first strict run for better evidence.

### Negative
- Additional overhead in evidence collection and coordination.

### Unknown/Untested
- Time to recover in worst-case rollback scenario.

## Implementation Evidence

### Commands Verified
```bash
# None executed during this session
````

### Configuration Discovered

```yaml
environment_toggles:
  ENABLE_BRIDGE_TELEMETRY: 1
  REQUIRE_DEVICE_ECHO: 1
```

### Log Patterns Observed

```
None observed in-session.
```

## Gaps Requiring Further Investigation

* Exact commit hash for rollback point.
* Whether telemetry sampling window needs tuning for `.jsonl` traces.

## References

* Source: User “runbook_next_actions”, “environment_toggles”
* Source: Assistant “Execution Mandate” (rollback)

---

**Extraction Date:** 2025-09-28
**Session ID/Reference:** STP4-STRICT pre-execution briefing
**Evidence Quality:** Partial (requires validation)

````

---

```markdown
# ADR-0005: Discovery Ownership & MQTT Namespace Policy

**Session Evidence Source:** User “discovery_policy” and “namespace_policy” in seed; Assistant confirmation in readiness note.

## Context
The scanner is the single source of truth for discovery; dispatcher discovery remains disabled. Namespace stays flat.

**Problem Statement:** Avoid conflicting discovery events and topic sprawl during strict graduation.

**Investigation Method:** Policy statements captured in-session.

**Evidence Gathered:**
- `discovery_policy.owner: scanner (single source of truth)`  
- `namespace_policy: Remain in flat 'bb8/...'`  
- Pattern examples provided for presence, rssi, power, led topics with retain flags.

## Decision
**Technical Choice:**  
Maintain scanner-only discovery; keep MQTT topics under flat `bb8/...` with stated retain behaviors.

**Command/Configuration:**  
As per examples in the seed (retain flags per topic).

**Validation Results:**  
Not validated in runtime during this session.

## Consequences

### Positive
- Predictable topic map and ownership boundaries.
- Easier evidence collection and filtering.

### Negative
- Less flexibility if new components need to publish discovery.

### Unknown/Untested
- Interactions with Home Assistant discovery if enabled elsewhere.

## Implementation Evidence

### Commands Verified
```bash
# None executed during this session
````

### Configuration Discovered

```yaml
discovery_policy:
  owner: "scanner (single source of truth)"
  pattern_examples:
    presence: "bb8/presence/state  (retain=true)"
    rssi:     "bb8/rssi/state      (retain=true)"
    power:    "bb8/power/state     (retain=false)"
    led:      "bb8/led/state       (retain=false, payload={'r','g','b'})"
```

### Log Patterns Observed

```
None observed in-session.
```

## Gaps Requiring Further Investigation

* Verification that dispatcher discovery remains disabled in code/config.
* Conformance checks that all publishers use the flat namespace.

## References

* Source: User “discovery_policy” and “guardrails.namespace_policy”
* Source: Assistant readiness confirmation (policy restatement)

---

**Extraction Date:** 2025-09-28
**Session ID/Reference:** STP4-STRICT pre-execution briefing
**Evidence Quality:** Partial (requires validation)

```

---

## Final Validation Checklist (Applied)
- [x] Every technical detail traces to session evidence (seed + assistant contracts)
- [x] Commands/configs taken verbatim from session; none executed here
- [x] Gaps and unknowns explicitly called out
- [x] No invented operational results or logs
- [x] References point to specific session sections
- [x] Evidence quality labeled as Partial pending execution

**Note:** No runtime logs, source-code excerpts, or deployment receipts were produced in this session; all ADRs above are decisions captured and bounded by acceptance criteria, pending empirical validation during the next run.
```
