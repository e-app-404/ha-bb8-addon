#!/usr/bin/env bash
set -euo pipefail

# ENV Governance Check (ADR-0024 Compliance)
# Read-only validator for .env file against canonical path standards
# Exit non-zero on policy violations

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ENV_FILE="$REPO_ROOT/.env"
EVIDENCE_ENV_FILE="$REPO_ROOT/.evidence.env"

echo "=== ENV Governance Check (ADR-0024) ==="
echo "Repository: $REPO_ROOT"
echo "Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo

# Track violations
VIOLATIONS=0

# Helper function to report violations
report_violation() {
    local severity="$1"
    local message="$2"
    echo "[$severity] $message"
    ((VIOLATIONS++))
}

report_info() {
    local message="$1"
    echo "[INFO] $message"
}

report_ok() {
    local message="$1"
    echo "[OK] $message"
}

# Check 1: No secrets in .env
echo "--- Checking for secrets in .env ---"
if [[ -f "$ENV_FILE" ]]; then
    SECRET_PATTERNS=(
        "MQTT_HOST="
        "MQTT_PORT=" 
        "MQTT_USER="
        "MQTT_PASSWORD="
        "MQTT_BASE="
        "REQUIRE_DEVICE_ECHO="
        "ENABLE_BRIDGE_TELEMETRY="
        "EVIDENCE_TIMEOUT_SEC="
        "HA_TOKEN=ey"
        "HA_LLAT_KEY=ey"
        "HA_LONG_LIVED_ACCESS_TOKEN="
    )
    
    SECRETS_FOUND=0
    for pattern in "${SECRET_PATTERNS[@]}"; do
        if grep -q "^[[:space:]]*$pattern" "$ENV_FILE" || grep -q "^[[:space:]]*export[[:space:]]*$pattern" "$ENV_FILE"; then
            report_violation "CRITICAL" "Secret found in .env: $pattern"
            ((SECRETS_FOUND++))
        fi
    done
    
    if [[ $SECRETS_FOUND -eq 0 ]]; then
        report_ok "No secrets found in .env"
    else
        report_violation "CRITICAL" "$SECRETS_FOUND total secrets found in .env (should be in .evidence.env only)"
    fi
else
    report_violation "ERROR" ".env file not found at $ENV_FILE"
fi

# Check 2: CONFIG_ROOT canonical definition
echo
echo "--- Checking canonical path definitions ---"
if [[ -f "$ENV_FILE" ]]; then
    if grep -q "^[[:space:]]*export[[:space:]]*CONFIG_ROOT=/config" "$ENV_FILE"; then
        report_ok "CONFIG_ROOT=/config defined correctly"
    elif grep -q "CONFIG_ROOT=" "$ENV_FILE"; then
        report_violation "HIGH" "CONFIG_ROOT defined but not as /config"
    else
        report_violation "HIGH" "CONFIG_ROOT not defined (required by ADR-0024)"
    fi
    
    # Check for deprecated path variables
    DEPRECATED_VARS=(
        "HA_MOUNT="
        "HA_MOUNT_OPERATOR="
        "CONFIG_MOUNT="
    )
    
    for var in "${DEPRECATED_VARS[@]}"; do
        if grep -q "^[[:space:]]*export[[:space:]]*$var" "$ENV_FILE" && ! grep -q "^[[:space:]]*#.*$var" "$ENV_FILE"; then
            report_violation "HIGH" "Deprecated variable in use: $var (replace with CONFIG_ROOT per ADR-0024)"
        fi
    done
    
    # Check for path typos
    if grep -q "DIR_DOMAINS=" "$ENV_FILE" && ! grep -q "^[[:space:]]*#.*DIR_DOMAINS=" "$ENV_FILE"; then
        report_violation "MEDIUM" "Path typo: DIR_DOMAINS should be DIR_DOMAIN (singular)"
    fi
    
    if grep -q "DIR_DOMAIN=" "$ENV_FILE"; then
        report_ok "DIR_DOMAIN (singular) correctly defined"
    fi
    
    # Check blueprint path
    if grep -q "templates/blueprints" "$ENV_FILE" && ! grep -q "^[[:space:]]*#.*templates/blueprints" "$ENV_FILE"; then
        report_violation "MEDIUM" "Path error: HESTIA_BLUEPRINTS should be .../blueprints not .../templates/blueprints"
    fi
    
    # Check remote script location  
    if grep -q "domain/shell_commands/addons_runtime_fetch.sh" "$ENV_FILE" && ! grep -q "^[[:space:]]*#.*domain/shell_commands" "$ENV_FILE"; then
        report_violation "HIGH" "Script location error: HA_REMOTE_SCRIPT should be in hestia/tools/ not domain/shell_commands/"
    fi
    
    if grep -q "hestia/tools/addons_runtime_fetch.sh" "$ENV_FILE"; then
        report_ok "HA_REMOTE_SCRIPT correctly points to hestia/tools/"
    fi
fi

# Check 3: Evidence environment separation
echo
echo "--- Checking evidence environment separation ---"
if [[ -f "$EVIDENCE_ENV_FILE" ]]; then
    report_ok ".evidence.env exists for secrets"
    
    # Verify some expected secrets are in evidence env
    EXPECTED_IN_EVIDENCE=(
        "MQTT_HOST="
        "MQTT_PASSWORD="
        "HA_LLAT_KEY=ey"
    )
    
    for pattern in "${EXPECTED_IN_EVIDENCE[@]}"; do
        if grep -q "$pattern" "$EVIDENCE_ENV_FILE"; then
            report_ok "Secret properly in .evidence.env: $pattern"
        else
            report_info "Expected secret not found in .evidence.env: $pattern"
        fi
    done
else
    report_violation "MEDIUM" ".evidence.env not found (secrets should be separated from .env)"
fi

# Check 4: BB8 checkpoint paths
echo
echo "--- Checking BB8 checkpoint paths ---"
if [[ -f "$ENV_FILE" ]]; then
    if grep -q "INT-HA-CONTROL" "$ENV_FILE"; then
        report_ok "BB8 checkpoint paths reference INT-HA-CONTROL"
    else
        report_info "BB8 checkpoint paths may need verification"
    fi
fi

# Summary
echo
echo "=== Governance Check Summary ==="
if [[ $VIOLATIONS -eq 0 ]]; then
    report_ok "ENV file is ADR-0024 compliant"
    echo "Status: PASS"
    exit 0
else
    echo "Status: FAIL"
    echo "Total violations: $VIOLATIONS"
    echo
    echo "Recommended actions:"
    echo "1. Move secrets from .env to .evidence.env"
    echo "2. Add CONFIG_ROOT=/config to .env"
    echo "3. Remove deprecated HA_MOUNT* variables"
    echo "4. Fix path typos (DIR_DOMAINS -> DIR_DOMAIN, templates/blueprints -> blueprints)"
    echo "5. Move scripts from domain/shell_commands/ to hestia/tools/"
    echo
    echo "Review: reports/checkpoints/ENV-GOV/env_governance_report.json"
    echo "Diff: reports/checkpoints/ENV-GOV/env_patch.diff"
    exit 1
fi