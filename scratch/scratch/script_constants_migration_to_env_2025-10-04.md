# Script Constants Migration to Centralized .env File

**Date**: 2025-10-04  
**Context**: ADR-0041 implementation and deployment pipeline stability improvements  
**Purpose**: Migrate hardcoded constants and path-related variables from ops scripts to centralized .env configuration

## Background

During the deployment pipeline restoration (ADR-0008, ADR-0041), we discovered numerous hardcoded values scattered across operational scripts that should be externalized to the centralized `.env` file for consistency, maintainability, and enhanced stability.

## Issues Identified

### 1. Hardcoded Host Information
**Files affected**: `ops/release/deploy_ha_over_ssh.sh`, `ops/diag/*`, `scripts/stp5_*`

**Current state**:
```bash
# Scattered across multiple files:
SSH_HOST="192.168.0.129"
MQTT_HOST="192.168.0.129" 
HA_URL="http://192.168.0.129:8123"
REMOTE_HOST_ALIAS="home-assistant"
SSH_USER="babylon-babes"
```

**Target state**: All host information centralized in `.env`:
```bash
# .env
export HA_HOST_IP="192.168.0.129"
export HA_SSH_HOST_ALIAS="home-assistant" 
export HA_SSH_USER="babylon-babes"
export HA_URL="http://192.168.0.129:8123"
export MQTT_HOST="192.168.0.129"
export MQTT_PORT="1883"
```

### 2. Path Constants
**Files affected**: `ops/release/*`, `ops/diag/*`, `ops/evidence/*`

**Current state**:
```bash
# Hardcoded in multiple scripts:
REMOTE_RUNTIME="/addons/local/beep_boop_bb8"
ADDON_SLUG="local_beep_boop_bb8"
PROJECT_ROOT="/Users/evertappels/actions-runner/Projects/HA-BB8"
REPORTS_DIR="reports/checkpoints/INT-HA-CONTROL"
```

**Target state**: Externalized to `.env`:
```bash
# .env
export HA_REMOTE_RUNTIME="/addons/local/beep_boop_bb8"
export HA_REMOTE_SLUG="local_beep_boop_bb8"
export HA_ADDON_NAME="beep_boop_bb8"
export PROJECT_REPORTS_DIR="reports/checkpoints/INT-HA-CONTROL"
```

### 3. MQTT Configuration
**Files affected**: `scripts/stp5_*`, `tools/bleep_run.py`, evidence collection scripts

**Current state**:
```bash
# Repeated in multiple locations:
MQTT_USER="mqtt_bb8"
MQTT_PASS="mqtt_bb8" 
BASE_TOPIC="bb8"
MQTT_TIMEOUT="30"
```

**Target state**: Centralized configuration:
```bash
# .env
export MQTT_USER="mqtt_bb8"
export MQTT_PASSWORD="mqtt_bb8"
export MQTT_BASE_TOPIC="bb8"
export MQTT_TIMEOUT_SECONDS="30"
export MQTT_QOS="1"
export MQTT_RETAIN="true"
```

### 4. Docker and Service Constants
**Files affected**: `ops/diag/collect_ha_bb8_diagnostics.sh`, deployment scripts

**Current state**:
```bash
# Multiple variations:
DOCKER_PATH="/usr/local/bin/docker"
ADDON_CONTAINER_PREFIX="addon_local_beep_boop_bb8"
HA_SUPERVISOR_API="http://supervisor/core/api"
```

**Target state**: Consistent naming in `.env`:
```bash
# .env
export HA_DOCKER_BINARY="/usr/local/bin/docker"
export HA_ADDON_CONTAINER_PREFIX="addon_local_beep_boop_bb8"
export HA_SUPERVISOR_API_BASE="http://supervisor"
export HA_CORE_API_BASE="http://supervisor/core/api"
```

## Migration Plan

### Phase 1: Core Infrastructure Constants (PRIORITY 1)
**Target files**: `ops/release/deploy_ha_over_ssh.sh`, `ops/release/bump_version.sh`

**Actions**:
1. Add comprehensive constants to `.env` file
2. Update scripts to source `.env` with error handling
3. Replace all hardcoded values with environment variables
4. Add fallback values for backward compatibility

### Phase 2: Diagnostic and Evidence Scripts (PRIORITY 2) 
**Target files**: `ops/diag/*`, `ops/evidence/*`, `scripts/stp5_*`

**Actions**:
1. Standardize MQTT connection parameters
2. Unify Docker path references
3. Centralize timeout and retry configurations
4. Add validation for required environment variables

### Phase 3: Testing and Validation Scripts (PRIORITY 3)
**Target files**: `tools/*`, `reports/checkpoints/*`

**Actions**:
1. Migrate test configuration constants
2. Standardize artifact output paths
3. Unify logging and reporting parameters
4. Add environment variable documentation

## Implementation Strategy

### Script Template Pattern
```bash
#!/usr/bin/env bash
# Standard .env loading pattern for all ops scripts

# Detect project root and load centralized configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Load centralized configuration with error handling
if [ -f "$PROJECT_ROOT/.env" ]; then
    set -a  # automatically export all variables
    source "$PROJECT_ROOT/.env"
    set +a  # disable auto-export
    echo "✅ Loaded configuration from $PROJECT_ROOT/.env"
else
    echo "❌ ERROR: Missing .env file at $PROJECT_ROOT/.env"
    echo "   Create .env file with required configuration variables"
    exit 1
fi

# Validate required variables (example)
REQUIRED_VARS=("HA_HOST_IP" "HA_SSH_HOST_ALIAS" "MQTT_HOST")
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ ERROR: Required environment variable $var is not set"
        exit 1
    fi
done
```

### Environment Variable Validation
```bash
# Add to .env loading section
validate_env_vars() {
    local required_vars=("$@")
    local missing_vars=()
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            missing_vars+=("$var")
        fi
    done
    
    if [ ${#missing_vars[@]} -gt 0 ]; then
        echo "❌ ERROR: Missing required environment variables:"
        printf "   %s\n" "${missing_vars[@]}"
        echo "   Update .env file with required configuration"
        return 1
    fi
    
    return 0
}
```

## Risk Mitigation

### Backward Compatibility
- Maintain fallback values for existing hardcoded constants
- Phase migration over multiple deployments  
- Add deprecation warnings for old patterns
- Document migration path for team members

### Testing Strategy
- Validate all scripts with new environment variables
- Test deployment pipeline with `.env` configuration
- Verify diagnostic scripts maintain functionality
- Confirm evidence collection continues working

### Rollback Plan
- Keep backup copies of original scripts
- Maintain old hardcoded values as fallbacks
- Document reversion procedure if issues arise
- Test rollback process before implementation

## Expected Benefits

### Maintenance
- **Single source of truth**: All configuration in one file
- **Easy updates**: Change values in one location
- **Clear documentation**: Environment variables self-document requirements
- **Reduced errors**: Eliminate inconsistencies between scripts

### Security  
- **Centralized secrets**: All sensitive values in one managed file
- **Environment isolation**: Easy to maintain different configurations
- **Access control**: Single file to secure and manage permissions
- **Audit trail**: Changes to configuration tracked in version control

### Operational Stability
- **Consistent behavior**: All scripts use same configuration values
- **Easier troubleshooting**: Known configuration location
- **Enhanced reliability**: Reduced chance of configuration drift
- **Better testing**: Environment-specific test configurations

## Implementation Evidence

This migration directly supports:
- **ADR-0041**: Centralized Environment Configuration & Accessible Secrets Management
- **ADR-0008**: End-to-End Development → Deploy Flow (enhanced reliability)
- **ADR-0040**: Layered Deployment Model for Testing & Version Provenance

## Success Criteria

### Phase 1 Complete
- ✅ All deployment scripts source `.env` file
- ✅ No hardcoded host information in ops/release/
- ✅ Deployment pipeline works with centralized configuration
- ✅ SSH deployment succeeds with environment variables

### Phase 2 Complete  
- ✅ All diagnostic scripts use centralized MQTT configuration
- ✅ Docker paths externalized to environment variables
- ✅ Evidence collection scripts updated with new constants
- ✅ STP5 attestation works with environment configuration

### Phase 3 Complete
- ✅ All testing scripts migrated to `.env` configuration
- ✅ Report generation uses centralized path constants
- ✅ Tool scripts updated with environment variables
- ✅ Documentation updated with new configuration patterns

## Next Actions

1. **Create comprehensive .env template** with all identified constants
2. **Update deployment scripts** (Phase 1) to use environment variables  
3. **Test deployment pipeline** with new configuration
4. **Migrate diagnostic scripts** (Phase 2) to centralized constants
5. **Update evidence collection** to use environment variables
6. **Document new patterns** for team adoption

---

**Status**: Planning Complete - Ready for Implementation  
**Priority**: High (supports deployment stability and operational excellence)  
**Dependencies**: ADR-0041 implementation, .env file creation  
**Timeline**: Phase 1 (deployment) → Phase 2 (diagnostics) → Phase 3 (testing)