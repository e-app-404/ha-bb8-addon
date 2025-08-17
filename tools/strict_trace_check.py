# tools/strict_trace_check.py
import json
import pathlib
import sys

p = pathlib.Path(sys.argv[1])
raw = json.loads(p.read_text())
data = raw if isinstance(raw, list) else raw.get("events", [])

facade = [e for e in data if e.get("source") == "facade"]
device = [e for e in data if e.get("source") == "device"]
led_ok = any(
    isinstance(e.get("state_payload"), dict)
    and all(k in e["state_payload"] for k in ("r", "g", "b"))
    for e in data
)

assert not facade, "Found facade echoes in strict run"
assert device, "No device-originated scalar echoes found"
assert led_ok, "No LED RGB JSON entries found"
print("Strict trace looks good.")
