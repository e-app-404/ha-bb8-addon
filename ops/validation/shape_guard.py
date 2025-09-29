import pathlib
import re
import sys

errors = []
root = pathlib.Path(".").resolve()

# 1) no root-level bb8_core
if (root / "bb8_core").exists():
    errors.append("Found forbidden root-level 'bb8_core/' (use 'addon/bb8_core/').")

# 2) imports must reference addon.bb8_core
bad = []
for p in root.rglob("*.py"):
    if any(seg in (".git", ".venv", "__pycache__", "node_modules") for seg in p.parts):
        continue
    s = p.read_text(encoding="utf-8", errors="ignore")
    if re.search(r"(^|\n)\s*from\s+bb8_core\s+import\s+", s) or re.search(
        r"(^|\n)\s*import\s+bb8_core(\s|$)", s
    ):
        bad.append(str(p))
if bad:
    errors.append(
        "Forbidden imports referencing bare 'bb8_core' found in:\n  - "
        + "\n  - ".join(sorted(bad))
    )

# 3) DS_Store junk
junk = [str(p) for p in root.rglob(".DS_Store")]
if junk:
    errors.append("macOS junk files present:\n  - " + "\n  - ".join(junk))

if errors:
    print("WORKSPACE SHAPE GUARD FAILED\n" + "\n\n".join(errors))
    sys.exit(2)

print("shape_guard=OK")
