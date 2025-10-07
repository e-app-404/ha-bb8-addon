#!/usr/bin/env bash
# INT-HA-CONTROL Step B: QA Roll-up and Final Report Generator
# Aggregates all test results into final qa_report.json

set -euo pipefail

CHECKPOINT_DIR="$(pwd)/reports/checkpoints/INT-HA-CONTROL"
QA_REPORT="$CHECKPOINT_DIR/qa_report.json"
TIMESTAMP=$(date -Iseconds)

echo "=== INT-HA-CONTROL Step B: QA Roll-up ==="
echo "Timestamp: $TIMESTAMP"
echo "Generating final QA report..."

# Check if required artifact files exist and read results
check_file() {
    local file="$1"
    local name="$2"
    if [[ -f "$file" ]]; then
        echo "✓ $name: Found"
        return 0
    else
        echo "✗ $name: Missing"
        return 1
    fi
}

# Check echo test results (from previous Gate A)
ECHO_OK=false
if check_file "$CHECKPOINT_DIR/mqtt_roundtrip.log" "MQTT Echo Test"; then
    # Check if we have 5 successful pings
    ECHO_COUNT=$(grep -c '"ok": true' "$CHECKPOINT_DIR/mqtt_roundtrip.log" 2>/dev/null || echo "0")
    if [[ $ECHO_COUNT -eq 5 ]]; then
        ECHO_OK=true
        echo "✓ Echo test: 5/5 successful pings"
    else
        echo "✗ Echo test: $ECHO_COUNT/5 successful pings"
    fi
fi

# Check P0 stability results
P0_OK=false
P0_DURATION="unknown"
P0_NEW_ERRORS=0
if check_file "$CHECKPOINT_DIR/error_count_comparison.json" "P0 Stability Monitor"; then
    P0_RESULT=$(python3 -c "
import json
try:
    with open('$CHECKPOINT_DIR/error_count_comparison.json') as f:
        data = json.load(f)
    result = data.get('result', 'UNKNOWN')
    duration = data.get('window_minutes', 'unknown')
    new_errors = data.get('new_errors', 999)
    print(f'{result}|{duration}|{new_errors}')
except:
    print('UNKNOWN|unknown|999')
")
    IFS='|' read -r P0_STATUS P0_DURATION P0_NEW_ERRORS <<< "$P0_RESULT"
    
    if [[ "$P0_STATUS" == "OK" && $P0_NEW_ERRORS -eq 0 ]]; then
        P0_OK=true
        echo "✓ P0 stability: $P0_DURATION minutes, 0 new errors"
    else
        echo "✗ P0 stability: $P0_STATUS, $P0_NEW_ERRORS new errors"
    fi
fi

# Check persistence test results
PERSISTENCE_OK=false
RECOVERY_TIME="unknown"
if check_file "$CHECKPOINT_DIR/mqtt_persistence.log" "Entity Persistence Test"; then
    # Parse persistence test results (check for both methods)
    PERSISTENCE_RESULT=$(grep -E "Entity recovery|Recovery time" "$CHECKPOINT_DIR/mqtt_persistence.log" | head -2)
    if echo "$PERSISTENCE_RESULT" | grep -q "SUCCESS" && echo "$PERSISTENCE_RESULT" | grep -qE "Recovery time: [0-9]+s"; then
        RECOVERY_TIME=$(echo "$PERSISTENCE_RESULT" | grep "Recovery time" | sed -E 's/.*Recovery time: ([0-9]+)s.*/\1/')
        if [[ "$RECOVERY_TIME" -le 10 ]]; then
            PERSISTENCE_OK=true
            echo "✓ Entity persistence: Recovery in ${RECOVERY_TIME}s"
        else
            echo "✗ Entity persistence: Recovery took ${RECOVERY_TIME}s (>10s limit)"
        fi
    else
        echo "✗ Entity persistence: Failed or >10s recovery"
    fi
fi

# Check ownership results
OWNERSHIP_OK=false
if check_file "$CHECKPOINT_DIR/discovery_ownership_check.txt" "Discovery Ownership Check"; then
    if grep -q "OK: single owner" "$CHECKPOINT_DIR/discovery_ownership_check.txt"; then
        OWNERSHIP_OK=true
        echo "✓ Discovery ownership: Single owner confirmed"
    else
        echo "✗ Discovery ownership: Duplicate owners detected"
    fi
fi

# Check LED gating results
LED_GATE_OK=false
if check_file "$CHECKPOINT_DIR/led_entity_schema_validation.json" "LED Discovery Gating"; then
    LED_STATUS=$(python3 -c "
import json
try:
    with open('$CHECKPOINT_DIR/led_entity_schema_validation.json') as f:
        data = json.load(f)
    status = data.get('status', 'UNKNOWN')
    gated = data.get('led_discovery_gated', False)
    print(f'{status}|{gated}')
except:
    print('UNKNOWN|False')
")
    IFS='|' read -r LED_STATUS LED_GATED <<< "$LED_STATUS"
    
    if [[ "$LED_STATUS" == "PASS" && "$LED_GATED" == "True" ]]; then
        LED_GATE_OK=true
        echo "✓ LED discovery gating: Properly gated (PUBLISH_LED_DISCOVERY=0)"
    else
        echo "✗ LED discovery gating: $LED_STATUS, gated=$LED_GATED"
    fi
fi

# Calculate overall pass status
OVERALL_PASS=false
if [[ "$ECHO_OK" == true && "$P0_OK" == true && "$PERSISTENCE_OK" == true && "$OWNERSHIP_OK" == true && "$LED_GATE_OK" == true ]]; then
    OVERALL_PASS=true
fi

# Generate comprehensive QA report
cat > "$QA_REPORT" <<EOF
{
  "timestamp": "$TIMESTAMP",
  "test_phase": "INT-HA-CONTROL Step B",
  "summary": {
    "echo_ok": $ECHO_OK,
    "p0_ok": $P0_OK,
    "persistence_ok": $PERSISTENCE_OK,
    "ownership_ok": $OWNERSHIP_OK,
    "led_gate_ok": $LED_GATE_OK,
    "overall_pass": $OVERALL_PASS
  },
  "details": {
    "echo_test": {
      "status": "$([ "$ECHO_OK" = true ] && echo "PASS" || echo "FAIL")",
      "description": "MQTT echo roundtrip test (5/5 pings ≤1000ms)"
    },
    "p0_stability": {
      "status": "$([ "$P0_OK" = true ] && echo "PASS" || echo "FAIL")",
      "duration_minutes": "$P0_DURATION",
      "new_errors": $P0_NEW_ERRORS,
      "description": "Runtime stability monitoring (TypeError/coroutine errors)"
    },
    "entity_persistence": {
      "status": "$([ "$PERSISTENCE_OK" = true ] && echo "PASS" || echo "FAIL")",
      "recovery_time_seconds": "$RECOVERY_TIME",
      "description": "Entity persistence through MQTT broker restart (≤10s recovery)"
    },
    "discovery_ownership": {
      "status": "$([ "$OWNERSHIP_OK" = true ] && echo "PASS" || echo "FAIL")",
      "description": "No duplicate discovery owners after restart"
    },
    "led_discovery_gating": {
      "status": "$([ "$LED_GATE_OK" = true ] && echo "PASS" || echo "FAIL")",
      "description": "LED discovery properly gated when PUBLISH_LED_DISCOVERY=0"
    }
  },
  "artifacts": {
    "mqtt_roundtrip.log": "MQTT echo test results",
    "p0_monitor.log": "P0 stability monitoring log",
    "error_count_comparison.json": "Error count analysis",
    "entity_persistence_test.log": "Entity persistence test log",
    "mqtt_persistence.log": "MQTT persistence results",
    "discovery_ownership_check.txt": "Ownership validation",
    "led_entity_schema_validation.json": "LED discovery gating results",
    "device_block_audit.log": "Device block compliance audit"
  },
  "exit_criteria": {
    "all_tests_pass": $OVERALL_PASS,
    "p0_stability_120min": "$([ "$P0_DURATION" = "120" ] && echo "true" || echo "false (demo: ${P0_DURATION}min)")",
    "entity_recovery_10s": "$([ "$RECOVERY_TIME" != "unknown" ] && [ "$RECOVERY_TIME" -le 10 ] && echo "true" || echo "false")",
    "zero_duplicate_owners": $OWNERSHIP_OK,
    "led_gating_enforced": $LED_GATE_OK
  }
}
EOF

echo
echo "=== QA Roll-up Results ==="
echo "Echo Test: $([ "$ECHO_OK" = true ] && echo "✅ PASS" || echo "❌ FAIL")"
echo "P0 Stability: $([ "$P0_OK" = true ] && echo "✅ PASS" || echo "❌ FAIL") (${P0_DURATION} min, ${P0_NEW_ERRORS} errors)"
echo "Entity Persistence: $([ "$PERSISTENCE_OK" = true ] && echo "✅ PASS" || echo "❌ FAIL") (${RECOVERY_TIME}s recovery)"
echo "Discovery Ownership: $([ "$OWNERSHIP_OK" = true ] && echo "✅ PASS" || echo "❌ FAIL")"
echo "LED Discovery Gating: $([ "$LED_GATE_OK" = true ] && echo "✅ PASS" || echo "❌ FAIL")"
echo
echo "OVERALL RESULT: $([ "$OVERALL_PASS" = true ] && echo "✅ PASS" || echo "❌ FAIL")"
echo
echo "QA Report generated: $QA_REPORT"

# Exit with appropriate code
if [ "$OVERALL_PASS" = true ]; then
    echo "🎉 INT-HA-CONTROL Step B: COMPLETE"
    exit 0
else
    echo "❌ INT-HA-CONTROL Step B: FAILED - Review individual test results"
    exit 1
fi