---
id: ADR-0041
title: Centralized Environment Configuration & Accessible Secrets Management
date: 2025-10-04
status: Accepted
decision: '### **Centralized .env Configuration** All deployment and operational configuration
  centralized in a single .env file at project root:.'
author:
- GitHub Copilot
- Evert Appels
related:
- ADR-0008
- ADR-0040
- ADR-0033
supersedes: []
last_updated: 2025-10-04
tags:
- configuration
- security
- deployment
- secrets
- env
---

# ADR-0041: Centralized Environment Configuration & Accessible Secrets Management

## Context

The HA-BB8 addon deployment scripts contained scattered configuration with hardcoded values, PII (Personally Identifiable Information), and inaccessible secrets causing deployment failures. The SSH deployment user `babylon-babes` cannot access Home Assistant's `/config/secrets.yaml` due to security restrictions, breaking LLAT (Long-Lived Access Token) verification.

### Problems Identified
1. **Scattered Configuration**: Deployment settings hardcoded across multiple scripts
2. **PII Exposure**: SSH usernames and host details in script comments
3. **Inaccessible Secrets**: `/config/secrets.yaml` not readable by SSH deployment user
4. **No Centralized Management**: Changes required editing multiple files
5. **Security Concerns**: Credentials and sensitive paths in version control

## Decision

### **Centralized .env Configuration**
All deployment and operational configuration centralized in a single `.env` file at project root:

```bash
# HA DEPLOYMENT CONFIG
export HA_SSH_HOST_ALIAS=home-assistant
export HA_SSH_USER=babylon-babes  
export HA_REMOTE_RUNTIME=/addons/local/beep_boop_bb8
export HA_REMOTE_SLUG=local_beep_boop_bb8
export HA_SECRETS_PATH=/addons/local/beep_boop_bb8/secrets.yaml
export HA_LLAT_KEY=HA_LLAT_KEY

# HA API configuration  
export HA_URL=""
export HA_API_CANDIDATES="http://homeassistant:8123 https://homeassistant:8123..."
```

### **Accessible Secrets File**
Create `addon/secrets.yaml` that syncs to the addon directory (accessible to SSH user):

```yaml
# addon/secrets.yaml - synced to /addons/local/beep_boop_bb8/secrets.yaml
HA_LLAT_KEY: string.string.string
```

### **Enhanced Deployment Script**
Update `ops/release/deploy_ha_over_ssh.sh` to:
- Auto-detect project root and load `.env`
- Use environment variables with backward compatibility fallbacks
- Handle accessible vs inaccessible secrets gracefully
- Provide clear error messages for missing configuration

```bash
#!/usr/bin/env bash
# Load configuration from central .env file
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
if [ -f "$PROJECT_ROOT/.env" ]; then
    set -a  # automatically export all variables
    source "$PROJECT_ROOT/.env"
    set +a  # disable auto-export
fi

# Use environment variables with fallbacks
REMOTE_HOST_ALIAS="${HA_SSH_HOST_ALIAS:-${REMOTE_HOST_ALIAS:-home-assistant}}"
SECRETS_PATH="${HA_SECRETS_PATH:-/addons/local/beep_boop_bb8/secrets.yaml}"
```

## Implementation

### **File Structure**
```
.env                               # Centralized configuration
addon/secrets.yaml                 # Accessible secrets file  
ops/release/deploy_ha_over_ssh.sh  # Enhanced deployment script
```

### **Security Measures**
1. **No PII in scripts**: All user/host info moved to .env
2. **Accessible secrets**: Stored in addon directory with proper permissions
3. **Configurable paths**: All deployment paths externalized
4. **Graceful degradation**: Script handles missing secrets appropriately

### **Backward Compatibility**
- Fallbacks to old environment variable names
- Existing scripts continue working
- Optional .env loading (won't break if file missing)

## Consequences

### **Positive**
- **Single source of truth**: All config in one place (.env)
- **Security improved**: No hardcoded PII or credentials
- **Reliability enhanced**: LLAT detection now works consistently  
- **Maintainability**: Changes only require editing .env
- **Flexibility**: Easy to override for different environments

### **Negative**
- **Additional file**: Must maintain .env file
- **Sync requirement**: addon/secrets.yaml must be synced to HA system
- **Learning curve**: Team must understand new configuration pattern

### **Risks Mitigated**
- **Deployment failures**: LLAT verification now reliable
- **Security exposure**: PII no longer in version control comments
- **Configuration drift**: Centralized management prevents inconsistencies

## Validation

### **Test Cases**
```bash
# 1. LLAT Detection
./ops/release/deploy_ha_over_ssh.sh test-llat
# Expected: SSH_HA_OK + LLAT_PRESENT + DEPLOY_SSH_OK

# 2. Configuration Loading
source .env && echo "Host: $HA_SSH_HOST_ALIAS"
# Expected: Host: home-assistant

# 3. Secrets Access  
ssh home-assistant "cat /addons/local/beep_boop_bb8/secrets.yaml"
# Expected: HA_LLAT_KEY: eyJhbGci...
```

### **Success Criteria**
- ✅ LLAT detection works consistently
- ✅ No hardcoded PII in scripts
- ✅ All deployment config centralized
- ✅ Scripts auto-load configuration
- ✅ Backward compatibility maintained

## Migration

### **Steps Completed**
1. Created `.env` with all deployment configuration
2. Created `addon/secrets.yaml` with LLAT token
3. Updated `ops/release/deploy_ha_over_ssh.sh` to load .env
4. Synced secrets file to HA system via rsync
5. Validated LLAT detection and configuration loading

### **Rollback Plan**
- Revert deployment script changes
- Use original hardcoded values
- Remove .env dependency

## Related Changes

- **ADR-0008**: Updated with centralized config workflow
- **ADR-0040**: Enhanced with reliable SSH deployment
- **Makefile**: No changes required (uses existing ops scripts)

## TOKEN_BLOCK

```yaml
TOKEN_BLOCK:
  accepted:
    - CENTRALIZED_CONFIG_IMPLEMENTED
    - ACCESSIBLE_SECRETS_WORKFLOW
    - PII_REMOVED_FROM_SCRIPTS
    - LLAT_DETECTION_RELIABLE
    - ENV_AUTO_LOADING_FUNCTIONAL
  produces:
    - SINGLE_SOURCE_OF_TRUTH_CONFIG
    - RELIABLE_SSH_DEPLOYMENT
    - IMPROVED_SECURITY_POSTURE
    - MAINTAINABLE_CONFIGURATION
  requires:
    - ADR_SCHEMA_V1
    - PROJECT_ROOT_ENV_FILE
    - ADDON_SECRETS_FILE_SYNCED
  drift:
    - DRIFT: env-file-missing
    - DRIFT: secrets-file-not-synced
    - DRIFT: configuration-scattered
```