---
id: ADR-0040
title: Layered Deployment Model for Testing & Version Provenance
date: 2025-10-03
status: Accepted
decision: '### **Mandatory Release Process for Testing Cycles** Every INT-HA-CONTROL
  cycle must begin with a version release to establish code provenance:.'
author:
- Evert Appels
- GitHub Copilot
related:
- ADR-0031
- ADR-0032
- ADR-0033
- ADR-0036
- ADR-0008
- ADR-0041
supersedes: []
last_updated: 2025-10-04
tags:
- deployment
- testing
- provenance
- versions
- supervisor
- docker
evidence_sessions:
- 2025-10-04: SSH deployment reliability fixes with centralized configuration and
    accessible secrets
---

# ADR-0040: Layered Deployment Model for Testing & Version Provenance

## Context

The INT-HA-CONTROL milestone requires proper version provenance and deployment integrity to ensure validation occurs against the actual deployed code. This ADR establishes the standard deployment model and version tracking process for all testing cycles.

### BB8 Add-on ⇄ Docker ⇄ Supervisor ⇄ Home Assistant Core Architecture

**Layered Mental Model (top → bottom):**

1. **Home Assistant Core (the app)**
   - Python application providing automations, integrations, UI, entities
   - Runs as Docker container (HA OS/Supervised) or bare Python process (Core installs)
   - Sees BB8 through MQTT integration - subscribes to discovery topics

2. **Supervisor (the orchestrator)**
   - Management service controlling add-ons and HA Core lifecycles
   - Uses Docker Engine for container management (pull, create, start/stop)
   - Provides configuration (`/data/options.json`), tokens, internal DNS

3. **Docker (the runtime)**
   - Container engine providing isolation, networking, volumes
   - Runs containers for HA Core and each add-on (including BB8)
   - Supervisor is "the boss," Docker is "the machinery"

4. **Add-ons (containers managed by Supervisor)**
   - BB8 add-on publishes MQTT Discovery and state
   - Reads config from `/data/options.json` and environment variables
   - Should NOT write directly to HA; uses MQTT for communication

### Architecture Diagram

```
  Operator
     │
     ▼
┌─────────────┐     manages      ┌──────────────┐     runs containers      ┌───────────────┐
│  Supervisor │ ───────────────▶ │   Docker     │ ───────────────────────▶ │ Containers    │
│ (orchestr.) │                  │ (engine)     │                          │ (HA Core,     │
└─────┬───────┘                  └────┬─────────┘                          │  BB8, MQTT)  │
      │  API/Ingress                   │                                   └────┬──────────┘
      │                                │                                        │
      │                                │  network                               │
      ▼                                ▼                                        ▼
  Home Assistant Core  ◀────────────── MQTT Broker ◀────────────── BB8 add-on (publishes discovery/state)
```

## Decision

### **Mandatory Release Process for Testing Cycles**

Every INT-HA-CONTROL cycle must begin with a version release to establish code provenance:

```bash
# STEP 1: Version Bump & Release (MANDATORY)
cd /Users/evertappels/actions-runner/Projects/HA-BB8
source .env
make release-patch

# Expected tokens:
# ✅ BUMP_OK:2025.8.21.XX
# ✅ SUBTREE_PUBLISH_OK:main@<sha>
# ⚠️ DEPLOY_OK (may require manual restart)
```

**Documentation Standard:** Log the released version at start of each cycle:
```
📋 INT-HA-CONTROL Cycle Started - YYYY-MM-DD HH:MM
✅ Released Version: 2025.8.21.XX
✅ Code Provenance: GitHub commit <sha>
✅ Deployment Status: [AUTO|MANUAL] restart required
```

### **Deployment Paths**

Two clean paths to deploy and test the BB8 codebase:

**A) Supervisor/HA OS Path (Preferred, Production-like)**  
**B) Standalone Dev Runner (No Supervisor; Quick iteration)**

Both produce the same PASS/FAIL artifacts under `reports/checkpoints/INT-HA-CONTROL/`.

### **Acceptance Gates**

- **P0 stability**: 120-min window, **0** TypeError/coroutine errors → `error_count_comparison.json`
- **MQTT persistence**: presence+rssi recover ≤10s after broker and HA core restarts → `entity_persistence_test.log`, `entity_audit.json`
- **Single-owner discovery**: `duplicates_detected == 0` → `discovery_ownership_audit.json`
- **LED alignment**: toggle-gated; strict `{r,g,b}`; same device block → `led_entity_schema_validation.json`
- **Config defaults**: `MQTT_BASE=bb8`, `REQUIRE_DEVICE_ECHO=1`, `PUBLISH_LED_DISCOVERY=0` → `config_env_validation.json`

### **Version Provenance Requirements**

**Before Starting INT-HA-CONTROL:**
1. Run `make release-patch` to bump version and publish code
2. Document released version (e.g., `2025.8.21.50`) 
3. Manual restart BB-8 addon in HA Supervisor UI if auto-deploy fails
4. Verify new version is running: `ha addons info local_beep_boop_bb8`

**Version Tracking Log:**
```bash
echo "📋 INT-HA-CONTROL Cycle - $(date)" 
echo "✅ Released Version: $(grep version addon/config.yaml | cut -d':' -f2 | tr -d ' ')"
echo "✅ Deployment Method: [SUPERVISOR_RESTART|SSH_DEPLOY]"
echo "✅ Container Status: $(docker ps | grep bb8 | awk '{print $7,$8}')"
```

## Implementation

### **Supervisor/HA OS Path (Production-like)**

```bash
# 0. Prepare environment on your workstation
cd /Users/evertappels/actions-runner/Projects/HA-BB8
python3 -m venv .venv && source .venv/bin/activate
python -m pip install -U pip paho-mqtt pytest pytest-cov
set -a && source .env && set +a

# 1. Sync code via rsync deployment
REMOTE_HOST_ALIAS=home-assistant ops/release/deploy_ha_over_ssh.sh

# 2. In Home Assistant UI (Supervisor):
#    - Open Add-ons → BB8 → "REBUILD" or "RESTART"
#    - Confirm logs show the new version starting

# 3. Run evidence collection scripts
python reports/checkpoints/INT-HA-CONTROL/mqtt_health_echo_test.py \
  --host "$MQTT_HOST" --port "${MQTT_PORT:-1883}" \
  --user "$MQTT_USER" --password "$MQTT_PASSWORD" \
  --base "$MQTT_BASE" --sla-ms 1000 \
  --out reports/checkpoints/INT-HA-CONTROL/mqtt_roundtrip.log

# 4. Execute restart sequence and validation
# [Additional validation steps follow ADR-0031 protocol]
```

### **Standalone Dev Runner Path**

```bash
# Run BB8 core logic as normal Python process
cd /Users/evertappels/actions-runner/Projects/HA-BB8
python3 -m venv .venv && source .venv/bin/activate
set -a && source .env && set +a

# Execute same evidence scripts (works without Supervisor)
python reports/checkpoints/INT-HA-CONTROL/discovery_ownership_audit.py \
  --topics 'homeassistant/#' \
  --output reports/checkpoints/INT-HA-CONTROL/discovery_ownership_audit.json
```

### **SSH Deployment Reliability Fix (2025-10-04)**

**Problem Identified:**
SSH deployment was failing due to:
1. SSH user `babylon-babes` cannot access `/config/secrets.yaml`
2. LLAT verification failing, blocking deployment
3. Hardcoded configuration scattered across scripts

**Solution Implemented:**
- Centralized configuration in `.env` file
- Accessible secrets file at `/addons/local/beep_boop_bb8/secrets.yaml`
- Enhanced deployment script with better error handling

## Consequences

### **Positive**
- **Version Traceability**: Every test cycle has documented version with Git provenance
- **Code Integrity**: Tests run against known, released code rather than workspace artifacts  
- **Deployment Validation**: Manual restart ensures addon is actually running new version
- **Audit Trail**: Clear documentation of what version was tested for compliance
- **Enhanced Reliability**: LLAT detection now works consistently
- **Better Security**: No hardcoded credentials in scripts

### **Negative**
- **Additional Step**: Requires version bump before every test cycle
- **Manual Intervention**: SSH deployment failure requires manual addon restart
- **Version Proliferation**: More frequent version increments in development

### **Implementation Requirements**
- Update INT-HA-CONTROL documentation to include mandatory release step
- Train operators on version verification process
- Establish rollback procedures if released version has issues
- Maintain `.env` file with current deployment configuration

## References

### **Communication Paths**
- **BB8 → MQTT Broker**: Discovery topics under `homeassistant/...` (retained) and runtime state under `bb8/...`
- **HA Core MQTT Integration → MQTT Broker**: Consumes discovery & state; creates/updates entities
- **Operator → Supervisor**: Start/stop/restart BB8 and broker add-ons; read logs; configure options

### **Lifecycle & Persistence**
- **Broker restart**: Retained discovery/state allows HA Core to keep/restore entities quickly (≤10s SLA)
- **HA Core restart**: On reconnect, Core re-subscribes and rehydrates entities from retained messages
- **Add-on restart**: BB8 republishes discovery/state idempotently; LWT ensures stale ownership cleared

### **Related ADRs**
- **ADR-0008**: End-to-End Development → Deploy Flow (deployment automation)
- **ADR-0031**: Supervisor-only Operations & Testing Protocol (operational validation)
- **ADR-0032**: MQTT/BLE Integration Architecture (communication patterns)
- **ADR-0041**: Centralized Environment Configuration (deployment configuration)

## TOKEN_BLOCK

```yaml
TOKEN_BLOCK:
  accepted:
    - DEPLOYMENT_MODEL_ESTABLISHED
    - VERSION_PROVENANCE_REQUIRED
    - RELEASE_PROCESS_MANDATORY
    - TESTING_INTEGRITY_ENFORCED
    - CENTRALIZED_CONFIG_IMPLEMENTED
    - ACCESSIBLE_SECRETS_WORKFLOW
    - ARCHITECTURE_LAYERS_DOCUMENTED
  produces:
    - WATERTIGHT_TESTING_CYCLES
    - CODE_DEPLOYMENT_TRACEABILITY
    - VERSION_AUDIT_CAPABILITY
    - RELIABLE_SSH_DEPLOYMENT
    - PRODUCTION_DEPLOYMENT_MODEL
  requires:
    - ADR_SCHEMA_V1
    - RELEASE_AUTOMATION_FUNCTIONAL
    - SUPERVISOR_ACCESS_AVAILABLE
    - ADDON_SECRETS_FILE_PRESENT
  drift:
    - DRIFT: manual-deployment-dependency
    - DRIFT: version-proliferation-concern
```