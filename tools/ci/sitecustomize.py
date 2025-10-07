# Ensures addon package is importable and measured identically in all runners.
import os, sys, pathlib
root = pathlib.Path(__file__).resolve().parents[2]  # repo root
pkg  = root / "addon"
if str(pkg) not in sys.path:
    sys.path.insert(0, str(pkg))