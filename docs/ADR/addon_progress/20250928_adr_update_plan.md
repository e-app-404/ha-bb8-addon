---
title: "ADR Documentation Update Plan - Post Milestone 1"
date: 2025-09-28
session: "development/production-ready-20250928"
evidence_source: "Milestone 1 Operational Validation"
---

# ADR Documentation Update Plan

## Summary of Required Updates

Based on Milestone 1 operational validation, the following ADRs require updates with new evidence and learnings:

### 1. ADR-0032: MQTT/BLE Integration Architecture
**Update Type:** Evidence Addition + Technical Corrections

**New Evidence to Add:**
- **paho-mqtt v2 Compatibility Fix:** ReasonCode handling pattern
- **Production Echo Validation:** Live roundtrip evidence
- **Deployment Validation:** SSH-based testing methodology

**Technical Corrections:**
```python
# OLD (failing pattern):
def _on_disconnect(client, userdata, rc, properties=None):

# NEW (paho-mqtt v2 compatible):
def _on_disconnect(client, userdata, flags, rc, properties=None):
```

**Evidence Blocks to Add:**
```bash
# Production MQTT Echo Validation
mosquitto_pub -h 192.168.0.129 -u mqtt_bb8 -P mqtt_bb8 -t bb8/echo/cmd -m '{"test": true}'
# Response: {"ts": 1759098629.0950077, "value": 1}
# RTT: <2 seconds, validates P0 MQTT fixes deployment
```

### 2. ADR-0031: Supervisor-only Operations & Testing Protocol  
**Update Type:** Operational Evidence Extension

**New Evidence to Add:**
- **Container Stability Validation:** 3+ hour uptime evidence
- **Health Monitoring Patterns:** Dual heartbeat validation
- **SSH Deployment Method:** Alternative to `ha` CLI when auth fails

**Evidence Blocks to Add:**
```bash
# Container Stability Evidence
sudo docker ps | grep bb8
# Result: Up 3 hours (validates operational stability)

# Health Monitoring Evidence  
sudo docker logs addon_local_beep_boop_bb8 --tail 10
# Pattern: main_age=-0.1s echo_age=-0.1s interval=15s
```

### 3. ADR-0034: HA OS Infrastructure
**Update Type:** Authentication & Access Pattern Updates

**New Evidence to Add:**
- **Supervisor CLI Authentication Issues:** 401 errors with `ha` commands
- **Docker Direct Access:** Alternative validation method
- **SSH Key Management:** home-assistant alias usage

**Evidence Blocks to Add:**
```bash
# Supervisor CLI Authentication Limitation
ha addons info local_beep_boop_bb8
# Result: unexpected server response. Status code: 401

# Alternative: Direct Docker Access
sudo docker logs addon_local_beep_boop_bb8
# Works reliably for validation
```

### 4. New ADR Candidate: ADR-0037: Code Quality Automation & Lint Policy
**Justification:** 63% lint reduction (112→41 errors) demonstrates need for formal policy

**Proposed Content:**
- Automated lint fixing workflows (ruff, black, mypy)
- Quality gate thresholds and enforcement
- Import order standardization (especially for test files with warnings.filterwarnings)
- Line length and style consistency rules

## Implementation Priority

1. **HIGH:** ADR-0032 (MQTT architecture) - contains critical paho-mqtt v2 fix pattern
2. **HIGH:** ADR-0031 (supervisor ops) - validates milestone 1 completion  
3. **MEDIUM:** ADR-0034 (infrastructure) - improves troubleshooting guidance
4. **LOW:** ADR-0037 (new) - can be deferred to milestone 2

## Validation Tokens

Each update must include:
- **TOKEN_EVIDENCE_VERIFIED:** All command outputs independently verified
- **TOKEN_DEPLOYMENT_VALIDATED:** Changes tested in production environment  
- **TOKEN_BACKWARD_COMPATIBLE:** Existing guidance remains valid
- **TOKEN_CROSS_ADR_ALIGNED:** References updated consistently