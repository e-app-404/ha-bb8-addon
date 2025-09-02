
#!/bin/bash
set -euo pipefail

if ! command -v jq >/dev/null 2>&1; then
  echo "ERROR: 'jq' is required for QA contract validation but is not installed." >&2
  exit 5
fi

# --- Canonical paths
SINK_BASE="/config/reports"
OUT_DIR="$SINK_BASE/stp5"
SNAP="$OUT_DIR/telemetry_snapshot.jsonl"
METRICS="$OUT_DIR/metrics_summary.json"
QA="$SINK_BASE/qa_contract_telemetry_STP5.json"
RECEIPT="$SINK_BASE/deploy_receipt.txt"


mkdir -p "$OUT_DIR"


CFG="/addons/local/beep_boop_bb8/config.yaml"
BASE="${BASE:-bb8}"
TELEMETRY_DURATION="${TELEMETRY_DURATION:-15}"  # Default to 15 seconds if not set


if [ ! -f "$CFG" ]; then
  echo "FATAL: Config file not found at $CFG" >&2
  exit 1
fi



# Extracts a config value from a YAML file (basic, not full YAML parser)
# Strips type hints (e.g., 'str', 'int?') and blank lines
extract_config_value() {
  local key="$1"
  local file="$2"
  local value
  value=$(sed -n -E "s/^ *${key}:[[:space:]]*\"?(.*)\"?$/\1/p" "$file" | sed 's/^ *//')
  # Remove type hints (e.g., 'str', 'int?') only if they appear at the end of the value
  value=$(echo "$value" | head -n1 | sed 's/[[:space:]]*\(str\|int\|str\?\|int\?\)[[:space:]]*$//')
  echo "$value"
}



if command -v yq >/dev/null 2>&1; then
  extract_yq_value() {
    local key="$1"
    local val
    val=$(yq e ".$key" "$CFG" 2>/dev/null | head -n1 | sed 's/[[:space:]]*\(str\|int\|str\?\|int\?\)[[:space:]]*$//')
    # If yq returns "null" or empty, return empty string
    if [ "$val" = "null" ] || [ -z "$val" ]; then
      echo ""
    else
      echo "$val"
    fi
  }
  HOST="$(extract_yq_value 'mqtt_broker')"
  PORT="$(extract_yq_value 'mqtt_port')"
  USER="$(extract_yq_value 'mqtt_username')"
  PASS="$(extract_yq_value 'mqtt_password')"
else
  HOST="$(extract_config_value 'mqtt_broker' "$CFG")"
  PORT="$(extract_config_value 'mqtt_port' "$CFG")"
  USER="$(extract_config_value 'mqtt_username' "$CFG")"
  PASS="$(extract_config_value 'mqtt_password' "$CFG")"
fi



strip_quotes_whitespace() {
  local s="$1"
  # Remove leading/trailing whitespace and quotes
  echo "$s" | sed 's/^ *//;s/ *$//;s/^"//;s/"$//'
}

PORT="${PORT:-1883}"
USER="${USER:-}"
PASS="${PASS:-}"
USER=$(strip_quotes_whitespace "$USER")
PASS=$(strip_quotes_whitespace "$PASS")
HOST=$(strip_quotes_whitespace "$HOST")
PORT=$(strip_quotes_whitespace "$PORT")


AUTH=()
if [ -n "$USER" ]; then AUTH+=(-u "$USER"); fi
if [ -n "$PASS" ]; then AUTH+=(-P "$PASS"); fi
echo "AUTH: ${AUTH[@]}"
echo "AUTH (safe): ${AUTH[*]}"


CID=$(ssh babylon-babes@homeassistant "docker ps --filter name=addon_local_beep_boop_bb8 --format '{{.ID}}'")
if [ -z "$CID" ]; then
# Try to send echo command, retry up to 3 times if needed
MOSQUITTO_PUB_ERR_LOG="$OUT_DIR/mosquitto_pub_error.log"
for attempt in 1 2 3; do
  ERR_MSG=$(mosquitto_pub -h "$HOST" -p "$PORT" "${AUTH[@]}" -t "${BASE}/echo/cmd" -m '{"value":1}' -q 1 2>&1)
  EXIT_CODE=$?
  if [ $EXIT_CODE -eq 0 ]; then
    if [ $attempt -gt 1 ]; then
      echo "mosquitto_pub succeeded on attempt $attempt"
    fi
    break
  else
    echo "WARNING: mosquitto_pub failed to send echo command (attempt $attempt)" >&2
    echo "mosquitto_pub error output: $ERR_MSG" >&2
    echo "[$(date -u)] Attempt $attempt: $ERR_MSG" >> "$MOSQUITTO_PUB_ERR_LOG"
    if [ $attempt -eq 3 ]; then
      echo "FATAL: mosquitto_pub failed after 3 attempts" >&2
      echo "See $MOSQUITTO_PUB_ERR_LOG for details." >&2
      exit 3
    fi
  fi
done
fi
TMP_SUB_FILE="$(mktemp "$OUT_DIR/mqtt_sub_raw.XXXXXX")"
echo "[PROGRESS] Subscribing for telemetry for $TELEMETRY_DURATION seconds... (waiting)"
mosquitto_sub -h "$HOST" -p "$PORT" "${AUTH[@]}" -v -t "${BASE}/#" -W "$TELEMETRY_DURATION" > "$TMP_SUB_FILE"
echo "[PROGRESS] Telemetry subscription complete. Processing results..."


python3 /config/python_scripts/mqtt_to_jsonl.py "$TMP_SUB_FILE" "$SNAP"
rm -f "$TMP_SUB_FILE"
if ! test -s "$SNAP"; then
  echo "FATAL: empty telemetry snapshot" >&2
  echo "Possible causes:" >&2
  echo " - MQTT broker unreachable (host: $HOST, port: $PORT)" >&2
  echo " - Device not responding to echo command" >&2
  echo " - Network issues or misconfiguration" >&2
  echo " - Incorrect MQTT credentials" >&2
  # Always emit a QA contract, even on failure
  python3 /config/python_scripts/emit_qa_contract.py "$QA" "$SNAP" "$METRICS"
    if [ ! -s "$QA" ]; then
      echo "ERROR: QA contract file was not written!" >&2
    exit 99
  fi
  exit 4
fi
echo "[DEBUG] Telemetry snapshot written to $SNAP"
echo "TOKEN: TELEMETRY_SNAPSHOT_OK"

# --- Compute metrics & QA

# Python block: metrics and QA analysis
python3 <<EOF
import sys, json, re, time, os, math

snap = "${SNAP}"
metrics = "${METRICS}"
qa = "${QA}"

# Allow echo topics to be set via environment variable, fallback to defaults
echo_topics_env = os.environ.get("ECHO_TOPICS")
if echo_topics_env:
    echo_topics = echo_topics_env.split(",")
else:
    echo_topics = [r".*/echo/resp$", r".*/echo/cmd$"]

lines = []
with open(snap, 'r') as f:
    for l in f:
        l = l.strip()
        if l:
            try:
                lines.append(json.loads(l))
            except Exception as e:
                print(f'JSON decode error: {e} in line: {l}', file=sys.stderr)

rtts = []
echo_count = 0
ts_first = None
ts_last = None

def mqtt_topic_match(pattern, topic):
    # Escape regex special chars except MQTT wildcards (+, #)
    def escape_except_wildcards(s):
        return re.sub(r'([.^$*?{}\[\]\\|()])', r'\\\1', s)
    pattern = escape_except_wildcards(pattern)
    pattern = pattern.replace('+', '[^/]+').replace('#', '.*')
    return re.fullmatch(pattern, topic) is not None

for e in lines:
    t = e.get('topic', '')
    p = e.get('payload', '')
    m_ts = re.search(r'"ts"\s*:\s*([0-9]+)', p)
    ts = int(m_ts.group(1)) if m_ts else None
    if ts is not None:
        if ts_first is None:
            ts_first = ts
        ts_last = ts
    if t in echo_topics or any(mqtt_topic_match(et, t) for et in echo_topics):
        echo_count += 1
        m = re.search(r'"ms"\s*:\s*([0-9]+)', p)
        if m:
            try:
                rtts.append(int(m.group(1)))
            except Exception:
                pass

window = ((ts_last - ts_first) / 1000) if (ts_first is not None and ts_last is not None) else 0

if rtts:
    rtts_sorted = sorted(rtts)
    n = len(rtts_sorted)
    if n > 0:
        k = int(round(0.95 * (n - 1)))
        p95 = rtts_sorted[k]
    else:
        p95 = None
else:
    p95 = None

def safe_utc(ts):
    if ts is None or ts == 0:
        return None
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(ts/1000))

summary = {
    'window_start_utc': safe_utc(ts_first),
    'window_end_utc': safe_utc(ts_last),
    'window_duration_sec': window,
    'echo_count': echo_count,
    'criteria': {
        'window_ge_10s': window >= 10,
        'min_echoes_ge_3': echo_count >= 3,
        'rtt_p95_le_250ms': (p95 is not None and p95 <= 250)
    }
}
# Verdict is "PASS" only if all acceptance criteria are met:
# - Window duration is at least 10 seconds
# - At least 3 echo ping/pong cycles are observed
# - 95th percentile echo RTT is less than or equal to 250ms
summary['verdict'] = "PASS" if all(summary['criteria'].values()) else "FAIL"

with open(metrics, 'w') as f:
    f.write(json.dumps(summary, indent=2))

qa_doc = {
    'contract_id': 'QA-TELEMETRY-STP5-001',
    'phase': 'P5-TELEMETRY-STP5',
    'objective': 'Echo/telemetry attestation >=10s',
    'acceptance_criteria': [
        'Window duration >= 10s',
        'At least 3 echo ping/pong cycles observed',
        'p95 echo RTT <= 250ms',
        'Artifacts: telemetry_snapshot.jsonl, metrics_summary.json'
    ],
    'artifacts': {
        'telemetry_snapshot': snap,
        'metrics_summary': metrics
    },
    'timestamp_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
    'verdict': summary['verdict']
}

with open(qa, 'w') as f:
    f.write(json.dumps(qa_doc, indent=2))

print(f"WROTE metrics file to: {metrics} (full path: {metrics})")
print(f"WROTE QA contract file to: {qa} (full path: {qa})")
EOF


echo "[PROGRESS] Metrics/QA analysis complete."

if ! test -s "$QA"; then
  echo "ERROR: QA contract file ($QA) does not exist or is empty. This file is required for attestation." >&2
  exit 6
fi

# jq is already checked at the start of the script; redundant check removed.

if ! jq empty "$QA" >/dev/null 2>&1; then
  echo "ERROR: $QA is not valid JSON." >&2
  exit 7
elif ! jq -e '(.verdict | type == "string")' "$QA" >/dev/null 2>&1; then
  echo "ERROR: .verdict field is missing or is not a string in $QA. (Check for presence and correct type: should be a string.)" >&2
  exit 8
else
  if jq -e '.verdict == "PASS"' "$QA" >/dev/null 2>&1; then
    echo "-----"
    echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')]"
    echo "TOKEN: TELEMETRY_ATTEST_OK"
  else
    echo "STP5 FAIL — Criteria breakdown:" >&2
    window_actual=$(jq -r '.window_duration_sec' "$METRICS")
    window_pass=$(jq -r '.criteria.window_ge_10s' "$METRICS")
    echo_count_actual=$(jq -r '.echo_count' "$METRICS")
    echo_count_pass=$(jq -r '.criteria.min_echoes_ge_3' "$METRICS")
    rtt_p95_pass=$(jq -r '.criteria.rtt_p95_le_250ms' "$METRICS")
    rtt_p95_actual=$(jq -r '.rtts | if . != null and (type=="array") and (. | length > 0) then (.[-1]) else "N/A" end' "$METRICS")
    echo " - Window duration >= 10s: $window_pass (actual: ${window_actual}s, expected: >=10s)" >&2
    echo " - At least 3 echo ping/pong cycles: $echo_count_pass (actual: ${echo_count_actual}, expected: >=3)" >&2
    echo " - p95 echo RTT <= 250ms: $rtt_p95_pass (actual: ${rtt_p95_actual}ms, expected: <=250ms)" >&2
    echo " - MQTT broker unreachable or misconfigured" >&2
    echo " - Device not responding to echo command" >&2
    echo " - Incorrect MQTT credentials" >&2
    echo "Check the following files for troubleshooting details:" >&2
    echo " - Telemetry snapshot: $SNAP" >&2
    echo " - Metrics summary: $METRICS" >&2
    echo " - QA contract: $QA" >&2
    echo " - Receipt: $RECEIPT" >&2
    echo " - Output directory: $OUT_DIR" >&2
    echo " - QA contract: $QA" >&2
    echo " - Receipt: $RECEIPT" >&2
    echo " - Output directory: $OUT_DIR" >&2
  fi
fi