import json
import os
import pathlib
import site
import sys

print("PYBIN:", sys.executable)
print("VENV :", os.getenv("VIRTUAL_ENV"))
print("PYTHONPATH:", os.getenv("PYTHONPATH"))
try:
    import inspect

    import bb8_core  # noqa: F401

    print("import bb8_core: OK →", inspect.getsourcefile(bb8_core))
except Exception as e:
    print("import bb8_core: FAILED:", repr(e))
print("sys.path (first 6):", json.dumps(sys.path[:6], indent=2))
for k in ("MQTT_HOST", "MQTT_BASE", "REQUIRE_DEVICE_ECHO", "ENABLE_BRIDGE_TELEMETRY"):
    print(f"{k}:", os.getenv(k))
# enumerate .pth files that might inject stray paths
pths = []
for d in site.getsitepackages() + [site.getusersitepackages()]:
    p = pathlib.Path(d)
    pths += list(p.glob("*.pth"))
if pths:
    print("Found .pth files:")
    for f in pths:
        try:
            print(" -", f, "→", f.read_text().strip())
        except Exception:
            print(" -", f, "(unreadable)")
