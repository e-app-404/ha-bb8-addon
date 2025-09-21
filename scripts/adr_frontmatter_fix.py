#!/usr/bin/env python3
"""Fix ADR front-matter safely.

This script normalizes ADR front-matter and body text:

- Ensure front-matter contains the keys ``related`` (list) and
    ``supersedes`` (list), and a ``last_updated`` date (YYYY-MM-DD).
    If ``last_updated`` is missing, prefer the ADR's ``date`` field,
    otherwise use today's date.
- Replace occurrences of ``/Volumes/HA`` or ``/Volumes/ha`` in the
    body with ``/n/ha``.
- Write a backup file named ``<file>.autofix.bak`` before modifying any
    ADR file.
- Commit all modified ADR files with a single commit message.
"""
import datetime
import glob
import os
import re
import shutil
import subprocess
import sys

import yaml

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ADR_DIR = os.path.join(ROOT, "docs", "ADR")
files = sorted(glob.glob(os.path.join(ADR_DIR, "*.md")))
if not files:
    print("No ADR files found in", ADR_DIR)
    sys.exit(1)

changed_files = []
for p in files:
    with open(p, encoding="utf-8") as f:
        text = f.read()
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.DOTALL)
    if not m:
        print("Skipping (no front-matter):", p)
        continue
    fm_text = m.group(1)
    body = m.group(2)
    try:
        fm = yaml.safe_load(fm_text) or {}
    except Exception as e:
        print("YAML parse error in", p, e)
        continue
    modified = False
    # ensure related and supersedes
    if "related" not in fm or fm["related"] is None:
        fm["related"] = []
        modified = True
    if "supersedes" not in fm or fm["supersedes"] is None:
        fm["supersedes"] = []
        modified = True
    # ensure last_updated
    today = datetime.date.today().isoformat()
    if "last_updated" not in fm or fm.get("last_updated") in (None, ""):
        if "date" in fm and re.match(r"^\d{4}-\d{2}-\d{2}$", str(fm.get("date"))):
            fm["last_updated"] = str(fm["date"])
        else:
            fm["last_updated"] = today
        modified = True
    # replace /Volumes/HA or /Volumes/ha -> /n/ha in body and fm fields that are strings
    new_body = re.sub(r"/Volumes/HA", "/n/ha", body)
    new_body = re.sub(r"/Volumes/ha", "/n/ha", new_body)

    # Also replace occurrences in front-matter string values (rare)
    def replace_in_obj(o):
        changed = False
        if isinstance(o, str):
            newo = re.sub(r"/Volumes/HA", "/n/ha", o)
            newo = re.sub(r"/Volumes/ha", "/n/ha", newo)
            if newo != o:
                return newo, True
            return o, False
        if isinstance(o, dict):
            for k, v in list(o.items()):
                nv, c = replace_in_obj(v)
                if c:
                    o[k] = nv
                    changed = True
            return o, changed
        if isinstance(o, list):
            for i, v in enumerate(o):
                nv, c = replace_in_obj(v)
                if c:
                    o[i] = nv
                    changed = True
            return o, changed
        return o, False

    fm, fm_changed = replace_in_obj(fm)
    if fm_changed:
        modified = True
    if new_body != body:
        body = new_body
        modified = True
    if modified:
        bak = p + ".autofix.bak"
        shutil.copy2(p, bak)
        # Reconstruct front-matter preserving YAML formatting minimally
        fm_yaml = yaml.safe_dump(fm, sort_keys=False, allow_unicode=True)
        new_text = "---\n" + fm_yaml.strip() + "\n---\n" + body
        with open(p, "w", encoding="utf-8") as f:
            f.write(new_text)
        changed_files.append(p)
        print("Patched", p, "-> backup at", bak)
    else:
        print("No change for", p)

if not changed_files:
    print("No ADR files needed changes")
    sys.exit(0)

# Commit changes

subprocess.check_call(["git", "add"] + changed_files, cwd=ROOT)
msg = (
    "docs(ADR): normalize front-matter (add last_updated, related/supersedes) "
    "and canonicalize /Volumes->/n/ha"
)
subprocess.check_call(["git", "commit", "-m", msg], cwd=ROOT)
print("Committed changes:", changed_files)
print("Commit complete")
