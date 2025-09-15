#!/bin/bash
# stp4_evidence_validate.sh
# Run from /Volumes/HA/addons/local/beep_boop_bb8

set -e

REPORT_DIR=$(ls -dt reports/stp4_* | head -n1)
MANIFEST="$REPORT_DIR/evidence_manifest.json"
DISCOVERY="$REPORT_DIR/ha_discovery_dump.json"
TRACE="$REPORT_DIR/ha_mqtt_trace_snapshot.json"

# --- FAST-FAIL LOCAL VALIDATIONS ---

# A. Trace integrity checks (only ha_mqtt_trace_snapshot.json)
echo "[A] Trace integrity checks:"

# 1. Expect zero matches: "source":"facade"
if jq -c '.[] | select(.source == "facade")' "$TRACE" | grep .; then
    echo "ERROR: Found 'source:facade' in trace"; exit 1;
else
    echo "OK: no facade entries in trace"
fi

# 2. Expect ≥1 matches: "source":"device" on scalar state topics
if jq -c '.[] | select(.source == "device")' "$TRACE" | head -n1 | grep .; then
    echo "OK: found device source in trace"
else
    echo "ERROR: No device source entries in trace"; exit 1;
fi

# 3. LED state entries must be exact {"r":int,"g":int,"b":int} (no source)
if jq -c '.[] | select(.state_payload | type == "object" and has("r") and has("g") and has("b"))' "$TRACE" | head -n1 | grep .; then
    echo "OK: found LED state entries"
else
    echo "ERROR: No LED state entries found"; exit 1;
fi

# B. BLE loop sanity (only ha_mqtt_trace_snapshot.json)
echo "[B] BLE loop sanity:"
# Check for any event with entity containing 'ble_link_started'
if jq -c '.[] | select(.entity | test("ble_link_started"))' "$TRACE" | grep .; then
    echo "OK: ble_link_started present in trace"
else
    echo "MISSING ble_link_started in trace"; exit 1;
fi
# Check for any event with entity or note containing 'get_event_loop'
if jq -c '.[] | select((.entity // "") | test("get_event_loop") or (.note // "") | test("get_event_loop"))' "$TRACE" | grep .; then
    echo "ERROR: get_event_loop usage remains in trace"; exit 1;
else
    echo "OK: no get_event_loop warnings in trace"
fi

# C. Retain policy (only ha_mqtt_trace_snapshot.json)
echo "[C] Retain policy:"
if jq -c '.[] | select(.retain == false)' "$TRACE" | head -n1 | grep .; then
    echo "OK: retain=false found for commandable echoes"
else
    echo "ERROR: retain=false not found for commandable echoes"; exit 1;
fi

# D. Discovery config validity (ha_discovery_dump.json)
echo "[D] Discovery config validity:"
if jq 'to_entries[] | select(.value.valid == false)' "$DISCOVERY" | grep .; then
    echo "WARNING: Some discovery configs are invalid"
else
    echo "OK: All discovery configs valid"
fi

# E. Manifest structure (evidence_manifest.json)
echo "[E] Manifest structure:"
if jq '.files | index("ha_discovery_dump.json") and index("ha_mqtt_trace_snapshot.json")' "$MANIFEST" | grep true; then
    echo "OK: Manifest includes required evidence files"
else
    echo "ERROR: Manifest missing required evidence files"; exit 1;
fi

jq . "$MANIFEST" || { echo "Manifest JSON invalid"; exit 1; }

# All checks complete
echo "All validations passed."
