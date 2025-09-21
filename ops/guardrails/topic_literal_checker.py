#!/usr/bin/env python3
"""Detect literal MQTT topic strings containing wildcard characters in source YAML/Python.

Scans .py and .yaml/.yml files under `addon/` and `ops/` for literal strings that
match `bb8/...` and contain `#` or `+`. Outputs JSON with matches.
"""
import ast
import json
import re
from pathlib import Path

ROOT = Path(".")
SEARCH_PATHS = [ROOT / "addon", ROOT / "ops"]
TOPIC_RE = re.compile(r'bb8/[^\s"\']*[#\+]')


def find_files(paths):
    for p in paths:
        if not p.exists():
            continue
        for f in p.rglob("*"):
            # Skip test directories (tests can intentionally use wildcards)
            parts = f.parts
            if "tests" in parts or "addon" in parts and "tests" in parts:
                continue
            if f.suffix in (".py", ".yaml", ".yml"):
                yield f


def scan_py(path: Path):
    try:
        src = path.read_text(encoding="utf-8")
    except Exception:
        return []
    matches = []
    try:
        tree = ast.parse(src)
    except Exception:
        return []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if TOPIC_RE.search(node.value):
                matches.append(
                    {"file": path.as_posix(), "line": node.lineno, "value": node.value}
                )
    return matches


def scan_yaml(path: Path):
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return []
    matches = []
    for m in TOPIC_RE.finditer(text):
        # approximate line number
        idx = m.start()
        line = text.count("\n", 0, idx) + 1
        matches.append({"file": path.as_posix(), "line": line, "value": m.group(0)})
    return matches


def main():
    results = []
    for f in find_files(SEARCH_PATHS):
        if f.suffix == ".py":
            results.extend(scan_py(f))
        else:
            results.extend(scan_yaml(f))
    out = {"tool": "topic_literal_checker", "matches": results}
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
