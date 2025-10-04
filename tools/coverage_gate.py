import sys
import xml.etree.ElementTree as ET

if len(sys.argv) < 2:
    print("usage: coverage_gate.py coverage.xml")
    sys.exit(2)
xml = sys.argv[1]
r = ET.parse(xml).getroot()
line_rate = float(r.attrib.get("line-rate", "0"))
# Respect FAIL_UNDER env if provided; default 70
req = float(__import__("os").environ.get("FAIL_UNDER", "70")) / 100.0
if line_rate + 1e-9 < req:
    print(f"Coverage gate FAIL: {line_rate:.2%} < {req:.2%}")
    sys.exit(1)
print(f"Coverage gate OK: {line_rate:.2%}  {req:.2%}")
