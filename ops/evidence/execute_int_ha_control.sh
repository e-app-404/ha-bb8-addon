#!/bin/bash
# execute_int_ha_control.sh
# Harmonized INT-HA-CONTROL v1.1.1 Execution Script
# Repo-relative execution with mandatory artifact validation

set -euo pipefail

# Determine repository root via git
if ! command -v git >/dev/null 2>&1; then
    echo "ERROR: git command not found - required for repo-relative execution"
    exit 1
fi

if ! git rev-parse --git-dir >/dev/null 2>&1; then
    echo "ERROR: Not in a git repository"
    exit 1
fi

ROOT="$(git rev-parse --show-toplevel)"
if [[ ! -d "$ROOT" ]]; then
    echo "ERROR: Could not determine repository root"
    exit 1
fi

echo "Repository root: $ROOT"

# Verify we're in HA-BB8 repository
if [[ ! -f "$ROOT/addon/config.yaml" ]] || [[ ! -f "$ROOT/addon/run.sh" ]]; then
    echo "ERROR: Not in HA-BB8 repository (missing addon/config.yaml or addon/run.sh)"
    exit 1
fi

# Change to repository root
cd "$ROOT"

# Define framework directory
FRAMEWORK_DIR="$ROOT/reports/checkpoints/INT-HA-CONTROL"

if [[ ! -d "$FRAMEWORK_DIR" ]]; then
    echo "ERROR: INT-HA-CONTROL framework not found at $FRAMEWORK_DIR"
    exit 1
fi

# Operator credential validation
echo "INT-HA-CONTROL v1.1.1 Harmonized Execution"
echo "=========================================="

# Check for required environment variables or prompt
if [[ -z "${HOST:-}" ]]; then
    read -p "Enter MQTT Host (e.g., 192.168.0.129): " HOST
    export HOST
fi

if [[ -z "${PORT:-}" ]]; then
    read -p "Enter MQTT Port (default: 1883): " PORT
    PORT=${PORT:-1883}
    export PORT
fi

if [[ -z "${USER:-}" ]]; then
    read -p "Enter MQTT Username: " USER
    export USER
fi

if [[ -z "${PASS:-}" ]]; then
    read -s -p "Enter MQTT Password: " PASS
    echo
    export PASS
fi

if [[ -z "${BASE:-}" ]]; then
    read -p "Enter Base Topic (default: bb8): " BASE
    BASE=${BASE:-bb8}
    export BASE
fi

echo
echo "Configuration:"
echo "  Host: $HOST"
echo "  Port: $PORT"  
echo "  User: $USER"
echo "  Base Topic: $BASE"
echo

# Preflight checks
echo "Preflight Checks:"
echo "-----------------"

# Check Python virtual environment
if [[ -z "${VIRTUAL_ENV:-}" ]]; then
    echo "WARNING: No virtual environment detected"
    echo "  Run: python3 -m venv .venv && source .venv/bin/activate"
fi

# Check required Python packages
python3 -c "import pytest, paho.mqtt.client" 2>/dev/null || {
    echo "ERROR: Missing required Python packages (pytest, paho-mqtt)"
    echo "  Run: pip install pytest pytest-cov paho-mqtt"
    exit 1
}

# Check MQTT connectivity (basic)
timeout 5 nc -z "$HOST" "$PORT" 2>/dev/null || {
    echo "WARNING: Cannot connect to MQTT broker at $HOST:$PORT"
    echo "  Continuing with framework execution..."
}

echo "✓ Preflight checks completed"
echo

# Execute INT-HA-CONTROL framework
echo "Executing INT-HA-CONTROL Framework:"
echo "-----------------------------------"

cd "$FRAMEWORK_DIR"

# Execute with error handling and artifact collection
if ./execute_int_ha_control.sh; then
    echo "✓ INT-HA-CONTROL framework execution completed successfully"
    
    # Verify mandatory artifacts
    echo
    echo "Artifact Validation:"
    echo "-------------------"
    
    MISSING_ARTIFACTS=0
    
    if [[ -f "$ROOT/addon/coverage.json" ]]; then
        echo "✓ Coverage report: addon/coverage.json"
    else
        echo "✗ Missing: addon/coverage.json"
        ((MISSING_ARTIFACTS++))
    fi
    
    if [[ -f "$ROOT/reports/addon_restart.log" ]]; then
        echo "✓ Restart log: reports/addon_restart.log"
    else
        echo "✗ Missing: reports/addon_restart.log"
        ((MISSING_ARTIFACTS++))
    fi
    
    if [[ -f "$ROOT/reports/mqtt_health_echo.log" ]]; then
        echo "✓ MQTT health log: reports/mqtt_health_echo.log"
    else
        echo "✗ Missing: reports/mqtt_health_echo.log"
        ((MISSING_ARTIFACTS++))
    fi
    
    if [[ -f "$ROOT/reports/entity_audit_results.json" ]]; then
        echo "✓ Entity audit: reports/entity_audit_results.json"
    else
        echo "✗ Missing: reports/entity_audit_results.json"
        ((MISSING_ARTIFACTS++))
    fi
    
    if [[ $MISSING_ARTIFACTS -gt 0 ]]; then
        echo
        echo "WARNING: $MISSING_ARTIFACTS mandatory artifacts missing"
        echo "Framework execution may be incomplete"
        exit 2
    else
        echo
        echo "✓ All mandatory artifacts validated"
        echo "INT-HA-CONTROL v1.1.1 execution successful"
    fi
    
else
    echo "✗ INT-HA-CONTROL framework execution failed"
    echo "Check logs in reports/ directory for details"
    exit 1
fi