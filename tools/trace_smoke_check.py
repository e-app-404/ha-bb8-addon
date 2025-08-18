import json
import os
import sys


# Accept file path as argument, else auto-find most recent trace
def find_latest_trace():
    reports_dir = os.path.join(os.path.dirname(__file__), "..", "reports")
    reports_dir = os.path.abspath(reports_dir)
    if not os.path.isdir(reports_dir):
        print(f"Reports directory not found: {reports_dir}")
        sys.exit(1)
    subfolders = [
        f
        for f in os.listdir(reports_dir)
        if os.path.isdir(os.path.join(reports_dir, f))
    ]
    if not subfolders:
        print(f"No subfolders found in reports directory: {reports_dir}")
        sys.exit(1)
    # Sort subfolders by timestamp in name (descending)
    subfolders.sort(reverse=True)
    for folder in subfolders:
        trace_file = os.path.join(reports_dir, folder, "ha_mqtt_trace_snapshot.json")
        if os.path.exists(trace_file):
            return trace_file
    print("No ha_mqtt_trace_snapshot.json found in any reports subfolder.")
    sys.exit(1)


if len(sys.argv) > 1:
    trace_path = sys.argv[1]
    if not os.path.exists(trace_path):
        print(f"Trace file not found: {trace_path}")
        sys.exit(1)
else:
    trace_path = find_latest_trace()

print(f"[INFO] Using trace file: {trace_path}")


with open(trace_path, encoding="utf-8") as f:
    if trace_path.endswith(".jsonl"):
        lines = [json.loads(line) for line in f if line.strip()]
    else:
        lines = json.load(f)
        if not isinstance(lines, list):
            lines = [lines]

# 1a) No 'source':'facade'
for entry in lines:
    if isinstance(entry, dict) and entry.get("source") == "facade":
        print("FAIL: Found source='facade' in trace.")
        sys.exit(1)

# 1b) At least one 'source':'device' on scalar topics
found_device_scalar = False
for entry in lines:
    if (
        isinstance(entry, dict)
        and entry.get("source") == "device"
        and isinstance(entry.get("value"), int | float | str)
    ):
        found_device_scalar = True
        break
if not found_device_scalar:
    print("FAIL: No source='device' scalar found.")
    sys.exit(1)

# 1c) LED entries match {"r":int,"g":int,"b":int}
for entry in lines:
    if (
        isinstance(entry, dict)
        and all(k in entry for k in ("r", "g", "b"))
        and not all(isinstance(entry[k], int) for k in ("r", "g", "b"))
    ):
        print(f"FAIL: LED entry not int: {entry}")
        sys.exit(1)

print("PASS: Trace smoke check OK.")
