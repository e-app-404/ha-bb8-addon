import sys, pathlib
repo = pathlib.Path(__file__).resolve().parents[2]
pkg  = repo / "addon"
if str(pkg) not in sys.path:
    sys.path.insert(0, str(pkg))
