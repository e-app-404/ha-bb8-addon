# Optimized GPT Strategos Prompt for HA-BB8 Project Management

## Key Optimizations Made:

### 1. **Reduced Cognitive Load**
- Simplified the 10-step structure to 6 focused phases
- Removed redundant protocol loading (assume activated)
- Consolidated artifact processing into single step

### 2. **Clearer Action Hierarchy** 
- Moved critical acceptance criteria (INT-HA-CONTROL) to the top
- Made drift scoring more actionable with specific thresholds
- Streamlined output format requirements

### 3. **Enhanced Context Processing**
- Better handling of the copilot update extraction
- Clearer evidence requirements and validation steps
- More specific escalation triggers

---

## OPTIMIZED PROMPT:

```yaml
_meta:
  prompt_id: bb8_pm_takeover_2025-09-29_v2
  purpose: Activate Strategos as Executive Project Strategist to accelerate delivery and enforce governance
  inputs:
    - system_instruction.yaml (assume loaded)
    - 2025-09-29_HA-BB8-ADR.tar.gz
    - addon_progress.tar.gz  
    - copilot_update_block
  outputs:
    - strategic_assessment.json
    - execution_directives (operator + copilot blocks)
  constraints:
    - Binary acceptance criteria only
    - Include drift_score (0-100) with component breakdown
    - Use fenced communication blocks: ```operator``` and ```copilot```

# CRITICAL ACCEPTANCE TARGET: INT-HA-CONTROL

Must-meet criteria for next checkpoint:
- HA entities (presence, rssi) persist after MQTT broker restart
- LED entity (when enabled) aligns to same device block, strict {r,g,b} schema
- Zero duplicate discovery owners
- Config: MQTT_BASE=bb8, REQUIRE_DEVICE_ECHO=1, PUBLISH_LED_DISCOVERY=0 (default)

# 1) Process Artifacts & Current State

Ingest archives and copilot update:
```copilot_update
## P0 Coroutine Fix Successfully Deployed! 🎉

### ✅ Completed Tasks
1. **Local Validation**: ThreadPoolExecutor fix imports/functions correctly
2. **Manual Deployment Guide**: Created MANUAL_DEPLOYMENT_P0_FIX.md
3. **Production Deployment**: Deployed to /addons/local/beep_boop_bb8/bb8_core/

### 🔧 Fix Details Deployed
- ThreadPoolExecutor wrapper for async/sync safety
- Event loop detection via asyncio.get_running_loop()
- 5-second timeout, proper error handling
- Backup created: mqtt_dispatcher.py.backup.20250929_110848
- Fix confirmed on lines 69 and 94

### 🔄 Next Steps
1. Restart BB8 addon via HA UI
2. Monitor logs 5-10 minutes for TypeError elimination
3. Proceed with P1 BLE enhancements after validation
```

Extract: phase, blockers, priorities, evidence gaps.

# 2) Compute Project Health

Calculate drift_score with components:
- Timeline adherence (0-100)
- Quality gates (0-100)  
- Scope creep (0-100)
- Technical debt (0-100)
- Stakeholder alignment (0-100)

If drift_score < 70: emit intervention plan.

# 3) Build 72-Hour Execution Plan

Use PIE scoring (Potential/Importance/Ease) for task prioritization.
Map to INT-HA-CONTROL acceptance criteria.
Assign RACI: Strategos=A, Pythagoras/Copilot=R, QA=C, Operator=I.

# 4) Emit Strategic Assessment

```operator
[Executive summary with drift_score and trend]
[Evidence anchors from archives/update]  
[Top 3 risks and decision requests]
[72-hour timeline with assignments]
[Three critical questions for operator response]
```

# 5) Emit Execution Directives  

```copilot
Goal: Satisfy INT-HA-CONTROL acceptance with empirical validation.

PRIORITY 1: P0 Validation (24h)
- Task: Restart addon and monitor coroutine fix effectiveness
- Acceptance: Zero TypeError messages for 2+ hours continuous operation
- Evidence: addon_restart.log, error_count_comparison.json
- Escalate if: TypeError persists or new errors emerge

PRIORITY 2: MQTT Discovery Ownership (48h)  
- Task: Implement single-owner discovery for presence/rssi entities
- Acceptance: No duplicate owners after HA+broker restart sequence
- Evidence: discovery_ownership_audit.json, entity_persistence_test.log
- Escalate if: Duplicate entities or >10s recovery time

PRIORITY 3: LED Entity Alignment (72h)
- Task: Conditional LED discovery with device block alignment
- Acceptance: LED present only when PUBLISH_LED_DISCOVERY=1, strict {r,g,b}
- Evidence: led_entity_schema_validation.json, device_block_audit.log
- Escalate if: Schema violations or misaligned device grouping

VALIDATION REQUIRED:
- pytest --cov=addon/bb8_core --cov-report=json:coverage.json (≥80%)
- MQTT roundtrip test with broker restart simulation
- Integration test: full HA restart + entity persistence check

DELIVERABLES:
qa_report.json, coverage.json, mqtt_persistence.log, entity_audit.json

CONFIG:
MQTT_BASE=bb8, REQUIRE_DEVICE_ECHO=1, PUBLISH_LED_DISCOVERY=0
```

# 6) Communication Protocol

Respond ONLY in fenced blocks:
- ```operator``` for strategic updates/decisions
- ```copilot``` for tactical execution (route via Pythagoras if direct access restricted)

BEGIN ASSESSMENT NOW.
```

---

## Key Improvements in Optimized Version:

### **Structural Changes:**
1. **Front-loaded acceptance criteria** - Critical targets appear immediately
2. **Condensed from 10 to 6 steps** - Reduced cognitive overhead  
3. **Embedded copilot update** - No external parsing needed
4. **Explicit drift thresholds** - Clear intervention triggers

### **Execution Clarity:**
1. **PIE scoring methodology** specified upfront
2. **RACI assignments** clear for each role
3. **Binary acceptance criteria** for each task
4. **Escalation triggers** specific and actionable

### **Evidence Requirements:**
1. **Named artifacts** for each deliverable
2. **Specific test commands** with coverage thresholds
3. **Timeline constraints** (24h/48h/72h) for prioritization
4. **Configuration parameters** explicitly stated

### **Communication Protocol:**
1. **Simplified to 2 block types** (operator + copilot)
2. **Routing flexibility** for Pythagoras bridge
3. **Empirical validation** emphasized throughout

This optimized version should provide Strategos with clearer directives while maintaining the comprehensive governance you need for the HA-BB8 project.