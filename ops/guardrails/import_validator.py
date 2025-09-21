#!/usr/bin/env python3
"""AST-based import validator.

Scans .py files under addon/ and ops/ and reports any imports from the forbidden
top-level module `bb8_core` (should use `addon.bb8_core` instead).

Outputs JSON to stdout with a list of offending files and import lines.
"""
import ast
import json
from pathlib import Path

ROOT = Path(".")
SEARCH_PATHS = [ROOT / "addon", ROOT / "ops"]


def find_py_files(paths):
    for p in paths:
        if not p.exists():
            continue
        for f in p.rglob("*.py"):
            yield f


def check_file(path: Path):
    try:
        src = path.read_text(encoding="utf-8")
    except Exception:
        return []
    tree = ast.parse(src)
    offenders = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                if n.name == "bb8_core" or n.name.startswith("bb8_core."):
                    offenders.append((path.as_posix(), node.lineno, f"import {n.name}"))
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "bb8_core" or module.startswith("bb8_core."):
                offenders.append(
                    (path.as_posix(), node.lineno, f"from {module} import ...")
                )
    return offenders


def main():
    results = []
    for f in find_py_files(SEARCH_PATHS):
        off = check_file(f)
        if off:
            results.extend(off)
    out = {
        "tool": "import_validator",
        "offenders": [{"file": r[0], "line": r[1], "hint": r[2]} for r in results],
    }
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
