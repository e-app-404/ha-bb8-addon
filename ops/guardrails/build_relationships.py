#!/usr/bin/env python3
"""Build a lightweight relationships map for the workspace.

Outputs:
- docs/architecture/relationships.json — JSON mapping producers -> consumers
- reports/relationship_graph.dot — DOT graph for visualization

This script performs static, best-effort analysis: Python import scanning and
regex-based MQTT topic literal extraction. It's not a full semantic analysis
but is useful for documentation and indexing.
"""
from __future__ import annotations

import ast
import json
import re
from pathlib import Path
# Using built-in generics (set[]) for annotations; no typing imports required

REPO = Path(__file__).resolve().parents[2]
OUT_JSON = REPO / "docs" / "architecture" / "relationships.json"
OUT_DOT = REPO / "reports" / "relationship_graph.dot"

PY_FILES = list(REPO.rglob("*.py"))

PUBLISH_RE = re.compile(
    r"\.(?:publish|publish_async)\s*\(\s*[\'\"]([^\'\"]+)[\'\"]"
)
SUBSCRIBE_RE = re.compile(r"\.(?:subscribe)\s*\(\s*[\'\"]([^\'\"]+)[\'\"]")
FMT_RE = re.compile(r"f?[\'\"]([^\'\"]*\{[^\}]+\}[^\'\"]*)[\'\"]")

def find_imports(py_path: Path) -> set[str]:
    try:
        src = py_path.read_text(encoding="utf-8")
        tree = ast.parse(src)
    except Exception:
        return set()
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                imports.add(n.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
    return imports


def literal_topics_from_text(txt: str) -> set[str]:
    topics: set[str] = set()
    for m in PUBLISH_RE.finditer(txt):
        topics.add(m.group(1))
    for m in SUBSCRIBE_RE.finditer(txt):
        topics.add(m.group(1))
    # detect simple f-strings or format usage that include topic-like patterns
    for m in FMT_RE.finditer(txt):
        topics.add(m.group(1))
    # cheap heuristic for CMD_TOPICS / STATE_TOPICS dicts or lists
    if "CMD_TOPICS" in txt or "STATE_TOPICS" in txt:
        for t in re.findall(r"\'([a-zA-Z0-9_\-/{}]+)\'", txt):
            topics.add(t)
    return topics


def find_mqtt_usages(py_path: Path) -> tuple[set[str], set[str]]:
    """Return (produced_topics, consumed_topics) as sets of topic strings.

    Best-effort static extraction: looks for .publish/.subscribe calls with literal
    first-arg topics, simple f-strings, and common topic-constant dicts.
    """
    try:
        txt = py_path.read_text(encoding="utf-8")
    except Exception:
        return set(), set()
    produced: set[str] = set()
    consumed: set[str] = set()

    # literal publishes/subscribes
    for m in PUBLISH_RE.finditer(txt):
        produced.add(m.group(1))
    for m in SUBSCRIBE_RE.finditer(txt):
        consumed.add(m.group(1))

    # fallback: scan text for topic-like literals (best-effort)
    literal_topics = literal_topics_from_text(txt)
    # if any publish-like verbs exist on the same line, mark as produced
    for line in txt.splitlines():
        if "publish(" in line or "publish_async(" in line:
            for t in re.findall(r"[\'\"]([a-zA-Z0-9_\-/{}]+)[\'\"]", line):
                produced.add(t)
        if "subscribe(" in line:
            for t in re.findall(r"[\'\"]([a-zA-Z0-9_\-/{}]+)[\'\"]", line):
                consumed.add(t)

    # include detected literal topics to either produced or consumed if unknown
    for t in literal_topics:
        if t not in produced and t not in consumed:
            # conservative default: add to produced
            produced.add(t)

    return produced, consumed


def main():
    producers: dict[str, dict] = {}
    # For each python file, collect imports and mqtt topics + producer/consumer roles
    for p in PY_FILES:
        rel = p.relative_to(REPO).as_posix()
        imps = sorted(find_imports(p))
        prod, cons = find_mqtt_usages(p)
        producers[rel] = {
            "imports": imps,
            "producers": sorted(prod),
            "consumers": sorted(cons),
        }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_DOT.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(producers, indent=2), encoding="utf-8")

    # Create a DOT graph where nodes are modules and edges indicate imports
    lines = ["digraph relationships {", "  rankdir=LR;"]
    for src, data in producers.items():
        lines.append(f'  "{src}" [shape=box];')
        for imp in data.get("imports", []):
            lines.append(f'  "{src}" -> "{imp}";')
        for topic in data.get("producers", []):
            topic_node = f"topic:{topic}"
            lines.append(f'  "{src}" -> "{topic_node}" [style=solid, color=green];')
        for topic in data.get("consumers", []):
            topic_node = f"topic:{topic}"
            lines.append(f'  "{topic_node}" -> "{src}" [style=dashed, color=blue];')
    lines.append("}")
    OUT_DOT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT_JSON} and {OUT_DOT}")


if __name__ == "__main__":
    main()
