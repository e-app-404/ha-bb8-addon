---
id: "META-WORKSPACE-0001"
title: "Workspace Remediation Plan"
authors: "TODO"
source: "TODO"
slug: "workspace-remediation-plan"
tags: ["remediation", "workspace", "cleanup", "bb8"]
date: "2024-06-13"
last_updated: "2024-06-13"
---

# Workspace Remediation Plan

To fix the BB-8 add-on repo without guesswork, we must know exactly what junk files exist, where, and how big they are. This plan provides a minimal, read-only way to snapshot the current state of the repository and gather quick policy answers from the maintainers.

Below is a minimal, step-by-step checklist to run stepwise. Turn the outputs into a surgical cleanup plan that won’t remove anything important.

## A) Six Quick Policy Answers

Reply in bullets; short is fine:

1. **Retention windows you want by class:**

- Backups (e.g., `.bk.<UTC>`): keep ? days
- Editor temp/swap (`~`, `.swp`, `.perlbak`): keep ? days (often 0)
- Bundles/archives (`.tar.gz`, `.tgz`, `.zip`): keep ? days
- Logs/reports (generated): keep ? days

2. **Canonical backup style you prefer (pick one):**

- `*.bk.<UTC>` (recommended & consistent), or keep legacy suffixes?

3. **What must remain tracked in git (besides real source):**

- e.g., `hestia/vault/<…>` snapshots, ADRs, etc.

4. **Are there any generators (scripts/IDE add-ons) that should keep making backups?**

- List paths if yes.

5. **Any paths that are “runtime only” (must be ignored by git):**

- e.g., `artifacts/`, `.trash/`, `.quarantine/`, `hestia/reports/`, `__pycache__/`, etc.

6. **Comfort level with auto-moves:**

- OK to normalize file names to `*.bk.<UTC>`?
- OK to corral junk into `.trash/DATE/`?
- OK to add/update `.gitignore`?

## B) Safe Read-Only Repo Snapshot

Run from the BB-8 add-on repo root stepwise:.

### B0. Where am I / which branch?

```bash
git rev-parse --show-toplevel; git branch --show-current
```

### B1. Porcelain summary (how much churn)

```bash
git status --porcelain=1 -uall | awk '{c[$1]++} END{for(k in c) printf "%-3s %d\n", k, c[k]}' | sort
```

### B2. Snapshot of ignore rules (tail)

```bash
test -f .gitignore && tail -n 80 .gitignore || echo "(no .gitignore)"
```

### B3. Count & size by “messy” patterns

(Reads files only; no writes.)

```python
python3 - <<'PY'
import os,re,json
root='.'; skip=('/.git/','/node_modules/','/.venv','/deps/','/__pycache__/')
classes=[
  ('backupCanonical', r'\.bk\.\d{8}T\d{6}Z(\.__\d+)?$'),
  ('backupLegacy',    r'\.bak(\.|-|$)|\.perlbak$|_backup(\.|$)|_restore(\.|$)'),
  ('editorTemp',      r'(~$)|\.swp$|\.tmp$|\.temp$'),
  ('bundles',         r'\.(tar\.gz|tgz|zip)$'),
  ('logsReports',     r'\.(log|tsv|csv|jsonl)$'),
]
def classify(name):
  for k,rx in classes:
   if re.search(rx,name,flags=re.I): return k
  return None
from collections import Counter,defaultdict
counts=Counter(); sizes=Counter(); samples=defaultdict(list)
for d,_,fs in os.walk(root):
  p=d.replace('\\','/')
  if any(s in p for s in skip): continue
  for f in fs:
   rel=os.path.join(d,f).lstrip('./')
   k=classify(f)
   if not k: continue
   try: sz=os.path.getsize(rel)
   except: sz=0
   counts[k]+=1; sizes[k]+=sz
   if len(samples[k])<8: samples[k].append(rel)
print("COUNTS:", dict(counts))
print("SIZES:", {k: sizes[k] for k in sizes})
for k in counts:
  print(f"SAMPLE[{k}]:"); [print("  ", s) for s in samples[k]]
PY
```

### B4. Top 30 Biggest Non-Source Artifacts

(Helps spot time sinks in diffs and slow clones.)

```python
python3 - <<'PY'
import os,heapq
root='.'; skip=('/.git/','/node_modules/','/.venv','/deps/','/__pycache__/')
rows=[]
for d,_,fs in os.walk(root):
  p=d.replace('\\','/')
  if any(s in p for s in skip): continue
  for f in fs:
   rel=os.path.join(d,f).lstrip('./')
   try: sz=os.path.getsize(rel)
   except: continue
   # treat “likely source” as small files or known extensions
   if os.path.splitext(f)[1] in ('.py','.yaml','.yml','.json','.md','.jinja','.sh','.txt','.ts','.js','.vue','.env'):
    continue
   rows.append((sz,rel))
for sz,rel in heapq.nlargest(30, rows):
  print(f"{sz}\t{rel}")
PY
```

### B5. Are Any Junk Files Actually Tracked by Git?

```python
python3 - <<'PY'
import subprocess,os,re,sys
p=subprocess.check_output(['git','status','--porcelain=1','-z','-uall'])
tracked=set()
for e in p.split(b'\x00'):
  if not e: continue
  s=e.decode(errors='ignore')
  if len(s)>=4:
   tracked.add(s[3:].split(' -> ')[-1])
bad=re.compile(r'\.bak(\.|-|$)|\.perlbak$|_backup(\.|$)|_restore(\.|$)|(~$)|\.swp$|\.tmp$|\.bk\.\d{8}T\d{6}Z')
hit=[t for t in tracked if bad.search(t)]
print("TRACKED_JUNK_COUNT", len(hit))
for h in sorted(hit)[:60]:
  print("TRACKED", h)
PY
```

### B6. Generator Fingerprints (Who Is Creating These?)

(Helps distinguish editor/IDE vs scripts.)

```bash
grep -RniE 'backup|restore|\.bak|\.perlbak|mktemp|tempfile|Retention|reportkit' -- . \
  | sed -n '1,120p' || true
```

### B7. Add-on Specifics (Optional, If You Have a Running Container Shell)

Run inside the BB-8 add-on container:

```bash
echo "SHELL: $(readlink -f /proc/$$/exe 2>/dev/null || echo ash)"; uname -a
```

If the repo is mounted inside HA OS, print where it is:

```bash
mount | grep -Ei 'home-assistant|addons|config' || true
```

## Expected Output

- Map which patterns are prevalent, where, and how big.
- Identify any junk that is tracked in git (highest priority to fix).
- Propose a tight `.gitignore`, a single canonical backup naming (`*.bk.<UTC>`), and a simple retention sweep that you can run safely in small steps (preview → normalize → corral → git untrack → verify).
- If needed, add guardrails (pre-commit include-scan and a BusyBox-friendly “retention sweep”.
