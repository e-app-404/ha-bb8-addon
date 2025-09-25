# Git Remote Strategy

## Instructions

Please fill out the YAML (one per project) plus the diagnostics snippets’ outputs, so we can:

	•	Propose the remote topology (which remotes push vs fetch-only, and why)
	•	Drop in guardrails (validators, CI checks, size/symlink/nested-git gates)
	•	Provide NAS/Tailnet mirror settings (incl. Synology ACL notes)
	•	Generate a tailored .env.sample, workspace samples, and acceptance tests
	•	Specify merge & backup strategy (snapshot branches/tags) aligned with your ADR-0016 rules

⸻

## Requirements checklist

1) Repo basics
	•	Purpose & runtime context (addon, registry, docs only, etc.)
	•	Default branch, branching model (trunk, GitFlow, release branches)
	•	Where it’s hosted now (GitHub/GitLab/Synology bare repo/path)

2) Remote topology & network
	•	All remotes (URLs, which one is primary for push)
	•	Will a NAS/Tailnet mirror be used? If yes: host/IP, path, shell restrictions (e.g., Synology git-shell)
	•	Who pushes from where (LAN only? Tailnet allowed? fetch-only mirrors?)

3) Access & governance
	•	Users/roles that need push/pull
	•	Protected branches/tags requirements
	•	Commit signing (required? GPG/Sigstore?)
	•	PR requirements (reviewers, checks that must pass)

4) Files & storage
	•	Expected large/binary artifacts (need Git LFS?)
	•	Biggest files / size caps you want enforced
	•	Any submodules / vendored repos
	•	Symlinks expected or forbidden?

5) Workspace & paths
	•	Any absolute paths hard-coded (e.g., /config, /data, /n/ha) that should be parametric or intentionally literal (containers often require literal /config//data)
	•	Do you want an .env.sample and validators like we added to HA?

6) CI/CD & automation
	•	Existing CI (GitHub Actions, etc.) and what must run on PRs
	•	Build/release packaging (tags/semver), changelog policy, artifact publishing

7) NAS specifics (if mirroring)
	•	Bare repo path on NAS (e.g., /volume1/git-mirrors/<name>.git)
	•	Ownership/ACL expectations (gituser:users, g+rx on parents)
	•	Whether Synology Git package wrappers are in play (fetch-only advisories, etc.)

8) Backup & recovery
	•	Mirror/backup cadence (push on every main? nightly? tags only?)
	•	Snapshot/backup branches/tags you want (e.g., backup/<name>-<ts>)

⸻

## HA BB-8 Addon Workspace Config Info

```yaml
project: "BB8 Addon"
purpose: "addon"
default_branch: "main"
branch_model: "trunk"
remotes:
	primary_push: "ssh://gituser@ds220plus.reverse-beta.ts.net/volume1/git-mirrors/ha-config.git"
	additional:
		- name: "origin"
			url: "ssh://gituser@ds220plus.reverse-beta.ts.net/volume1/git-mirrors/ha-config.git"
			push: true
		- name: "(none)"
			url: "(no tailnet configured)"
			push: false
network:
	lan_ip: "192.168.0.0/24 (example)"
	tailnet_ip: "(none configured)"
	synology_git_shell_wrapped: true
governance:
	protected_branches: ["main"]
	commit_signing_required: false
	pr_checks_required: ["lint", "tests", "guardrails/index-regeneration"]
files:
	expects_large_binaries: false
	git_lfs_needed: false
	allows_symlinks: false
paths:
	uses_container_literals: true
	must_parameterize_host_paths: true
ci_cd:
	platform: "github-actions"
	release_tags: "semver"
nas_mirror:
	path: "/volume1/git-mirrors/ha-config.git"
	owner: "gituser:users"
	parents_g_rx: true
backup_policy:
	push_to_mirror_on: ["main"]
	create_backup_tags: true
```

---

## Diagnostics output (captured)

```bash
# Quick diagnostics output captured on: 2025-09-25T00:40:11Z

=== git remote -v
origin	ssh://gituser@ds220plus.reverse-beta.ts.net/volume1/git-mirrors/ha-config.git (fetch)
origin	ssh://gituser@ds220plus.reverse-beta.ts.net/volume1/git-mirrors/ha-config.git (push)

=== git rev-parse --abbrev-ref HEAD
chore/restructure-bb8-addon

=== git config --get init.defaultBranch || true
main

=== git branch -r | sed -n '1,50p'
	origin/feat/motion-mvp-tidy
	origin/feature/oom-recorder-policy
	origin/feature/oom-recorder-policy-adr-only
	origin/main
	origin/meta/rehydration/68b5e5e1-archive
	origin/recover/stash-2025-09-20
	origin/restore/adr-to-core-architecture

=== git lfs env 2>/dev/null | sed -n '1,80p' || echo 'no-git-lfs'
git-lfs/3.7.0 (GitHub; darwin arm64; go 1.24.4)
git version 2.39.5 (Apple Git-154)

Endpoint=https://ds220plus.reverse-beta.ts.net/volume1/git-mirrors/ha-config.git/info/lfs (auth=none)
	SSH=gituser@ds220plus.reverse-beta.ts.net:/volume1/git-mirrors/ha-config.git
LocalWorkingDir=/Users/evertappels/Projects/HA-BB8
LocalGitDir=/Users/evertappels/Projects/HA-BB8/.git
LocalGitStorageDir=/Users/evertappels/Projects/HA-BB8/.git
LocalMediaDir=/Users/evertappels/Projects/HA-BB8/.git/lfs/objects
LocalReferenceDirs=
TempDir=/Users/evertappels/Projects/HA-BB8/.git/lfs/tmp
ConcurrentTransfers=8
TusTransfers=false
BasicTransfersOnly=false
SkipDownloadErrors=false
FetchRecentAlways=false
FetchRecentRefsDays=7
FetchRecentCommitsDays=0
FetchRecentRefsIncludeRemotes=true
PruneOffsetDays=3
PruneVerifyRemoteAlways=false
PruneVerifyUnreachableAlways=false
PruneRemoteName=origin
LfsStorageDir=/Users/evertappels/Projects/HA-BB8/.git/lfs
AccessDownload=none
AccessUpload=none
DownloadTransfers=basic,lfs-standalone-file,ssh
UploadTransfers=basic,lfs-standalone-file,ssh
GIT_ASKPASS=/Applications/Visual Studio Code - Insiders.app/Contents/Resources/app/extensions/git/dist/askpass.sh
GIT_EXEC_PATH=/Applications/Xcode.app/Contents/Developer/usr/libexec/git-core
GIT_PAGER=cat
git config filter.lfs.process = "git-lfs filter-process"
git config filter.lfs.smudge = "git-lfs smudge -- %f"
git config filter.lfs.clean = "git-lfs clean -- %f"

=== git submodule status 2>/dev/null || echo 'no-submodules'

=== git config --list | grep -E 'user.signingkey|commit.gpgsign|tag.gpgsign' || true

=== top 20 largest files
xargs: command line cannot be assembled, too long
152108 coverage.xml
48461 addon/CHANGELOG.md
47963 CHANGELOG.md
44354 docs/legacy/ha_mqtt_configuration_info.md
39552 addon/bb8_core/mqtt_dispatcher.py
38878 addon/bb8_core/bb8_presence_scanner.py
32661 addon/bb8_core/ble_bridge.py
19422 addon/bb8_core/bridge_controller.py
17810 docs/legacy/CHANGELOG_legacy.md
17263 addon/bb8_core/controller.py
16203 docs/legacy/ha_addon.config.info.md
13802 addon/bb8_core/facade.py
13171 docs/legacy/mac_version_A.patch
12198 addon/bb8_core/echo_responder.py
11354 addon/tests/test_auto_detect.py
11249 docs/ADR/INDEX.md
10806 docs/ADR/ADR-0023-bb8-integration.md
10781 addon/tests/test_facade.py
10763 addon/tests/test_bb8_presence_scanner.py
9483 docs/legacy/ADDON_DEVELOPMENT_CHECKLIST_v1.1.md

=== symlinks
./.venv/bin/python3
./.venv/bin/python
./.venv/bin/python3.13

=== nested .git

=== path probes
./_backups/docs/directives/directive.run_pack_strict_led_on.md.autofix.perlbak:143:*(This run is operational-toggle only—no code diffs expected. If you did change code/config, replace the empty arrays accordingly.)*
./_backups/docs/directives/directive.run_pack_strict_led_on.md.autofix.bak:143:*(This run is operational-toggle only—no code diffs expected. If you did change code/config, replace the empty arrays accordingly.)*
./_backups/docs/ADR/_autofix_backups/ADR-0020-motion-safety-and-mqtt-contract.md.autofix.bak:32:Publish each config to `homeassistant/number/<unique_id>/config` with `retain=True` on publish (not in JSON).
./_backups/docs/ADR/_autofix_backups/ADR-0020-motion-safety-and-mqtt-contract.md.autofix.bak:96:Publish to homeassistant/button/<unique_id>/config with `retain=True` on publish. 
./_backups/docs/ADR/_autofix_backups/INDEX.md.autofix.bak:10:| [ADR-0004-runtime-tools-policy.md](ADR-0004-runtime-tools-policy.md) | "ADR-0004: Conditional Runtime Tools Policy (CRTP) & Workspace Drift Enforcement" | Accepted | 2025-08-26 | Strategos | ADR-0001,ADR-0009 |  | 2025-09-13 | TOKEN_BLOCK: accepted: - TOOLS_ALLOWED - SCRIPTS_ALLOWED - STRUCTURE_GUARD_OK drift: - DRIFT: tools_unreferenced_in_dockerfile - DRIFT: scripts_unreferenced_in_dockerfile - DRIFT: structure_guard_failed - name: Structure guard (ADR-0001 + CRTP) run: \| set -euo pipefail test -d addon \|\| (echo addon/ missing && exit 2) if [ -d addon/.git ]; then echo addon is a repo (forbidden); exit 3; fi # Forbidden workspace-only dirs (always) for d in .github docs ops reports addon; do if [ -e addon/$d ]; then echo DRIFT:forbidden_in_addon:$d; exit 4; fi done # Required files + mode test -f addon/config.yaml \|\| (echo DRIFT:missing_config_yaml && exit 5) if rg -n ^\s*image:\s* addon/config.yaml >/dev/null; then echo MODE: PUBLISH rg -n ^\s*version:\s* addon/config.yaml >/dev/null \|\| (echo DRIFT:version_missing_in_publish_mode && exit 7) else echo MODE: LOCAL_DEV test -f addon/Dockerfile \|\| (echo DRIFT:dockerfile_missing_in_local_dev && exit 6) echo TOKEN: DEV_LOCAL_BUILD_FORCED fi # CRTP: tools/ allowed if referenced by Dockerfile or marker present if [ -d addon/tools ]; then if ! grep -Ei (COPY\|ADD\|RUN\|ENTRYPOINT\|CMD).*tools/ addon/Dockerfile >/dev/null 2>&1   && [ ! -f addon/.allow_runtime_tools ]; then echo DRIFT:tools_unreferenced_in_dockerfile; exit 8 else echo TOKEN: TOOLS_ALLOWED fi fi echo TOKEN: STRUCTURE_OK CRTP-ALLOW: path: addon/tools/ reason: container health probe invoked by s6 longrun referenced_by: run.sh:23 safety: shellcheck-clean, no-secrets, bounded-exit owner: pythagoras CRTP-MARKER: file: addon/.allow_runtime_tools entries: - addon/tools/diag_snapshot.sh reason: on-device diagnostics; manual invocation on support safety: shellcheck-clean, ≤100KB, no elevated privileges | - |
./_backups/docs/ADR/_autofix_backups/ADR-0008-end-to-end-flow.md.autofix.perlbak:24:- Supervisor builds locally when `addon/config.yaml` contains a **`build:`*- block **and `image:` is absent**. Use `image:` **only for PUBLISH*- (pull from a registry).
./_backups/docs/ADR/_autofix_backups/ADR-0008-end-to-end-flow.md.autofix.perlbak:45:  - `addon/config.yaml` (mode-aware):
./_backups/docs/ADR/_autofix_backups/ADR-0008-end-to-end-flow.md.autofix.perlbak:126:- Runtime sync token: `/config/reports/deploy_receipt.txt`
./_backups/docs/ADR/_autofix_backups/ADR-0008-end-to-end-flow.md.autofix.perlbak:130:mkdir -p /config/reports && echo 'TOKEN: CLEAN_RUNTIME_OK' | tee -a /config/reports/deploy_receipt.txt
./_backups/docs/ADR/_autofix_backups/ADR-0008-end-to-end-flow.md.autofix.perlbak:154:# 6.5 Emit verify token (receipt: `/config/reports/deploy_receipt.txt`)
./_backups/docs/ADR/_autofix_backups/ADR-0008-end-to-end-flow.md.autofix.perlbak:155:echo 'TOKEN: DEPLOY_OK' | tee -a /config/reports/deploy_receipt.txt
./_backups/docs/ADR/_autofix_backups/ADR-0008-end-to-end-flow.md.autofix.perlbak:177:# Ensure addon/config.yaml:version == tag
./_backups/docs/ADR/_autofix_backups/ADR-0008-end-to-end-flow.md.autofix.perlbak:183:- **“Add‑on not available inside store”**: ensure `/addons/local/beep_boop_bb8/config.yaml` exists, then UI → *Add‑on Store → HA‑BB8 (local)- → **Install**; or run `ssh babylon-babes@homeassistant "ha addons reload"`.
./_backups/docs/ADR/_autofix_backups/ADR-0008-end-to-end-flow.md.autofix.perlbak:240:- CI guard ensures `addon/config.yaml` has `build:` and a local `image:` in non‑publish PRs.
./_backups/docs/ADR/_autofix_backups/ADR-0008-end-to-end-flow.md.autofix.perlbak:249:- `addon/config.yaml` → `image:` local + `build:` present
./_backups/docs/ADR/_autofix_backups/ADR-0004-runtime-tools-policy.md.autofix.bak:81:    test -f addon/config.yaml || (echo "DRIFT:missing_config_yaml" && exit 5)
./_backups/docs/ADR/_autofix_backups/ADR-0004-runtime-tools-policy.md.autofix.bak:82:    if rg -n '^\s*image:\s*' addon/config.yaml >/dev/null; then
./_backups/docs/ADR/_autofix_backups/ADR-0004-runtime-tools-policy.md.autofix.bak:84:      rg -n '^\s*version:\s*' addon/config.yaml >/dev/null || (echo "DRIFT:version_missing_in_publish_mode" && exit 7)
./_backups/docs/ADR/_autofix_backups/ADR-0008-end-to-end-flow.md.autofix.bak:24:- Supervisor builds locally when `addon/config.yaml` contains a **`build:`*- block **and `image:` is absent**. Use `image:` **only for PUBLISH*- (pull from a registry).
./_backups/docs/ADR/_autofix_backups/ADR-0008-end-to-end-flow.md.autofix.bak:45:  - `addon/config.yaml` (mode-aware):
./_backups/docs/ADR/_autofix_backups/ADR-0008-end-to-end-flow.md.autofix.bak:67:- Optional: macOS runtime mount at `/n/ha/addons/local/beep_boop_bb8`.
./_backups/docs/ADR/_autofix_backups/ADR-0008-end-to-end-flow.md.autofix.bak:110:  addon/ /n/ha/addons/local/beep_boop_bb8/
./_backups/docs/ADR/_autofix_backups/ADR-0008-end-to-end-flow.md.autofix.bak:126:- Runtime sync token: `/config/reports/deploy_receipt.txt`
./_backups/docs/ADR/_autofix_backups/ADR-0008-end-to-end-flow.md.autofix.bak:130:mkdir -p /config/reports && echo 'TOKEN: CLEAN_RUNTIME_OK' | tee -a /config/reports/deploy_receipt.txt
./_backups/docs/ADR/_autofix_backups/ADR-0008-end-to-end-flow.md.autofix.bak:154:# 6.5 Emit verify token (receipt: `/config/reports/deploy_receipt.txt`)
./_backups/docs/ADR/_autofix_backups/ADR-0008-end-to-end-flow.md.autofix.bak:155:echo 'TOKEN: DEPLOY_OK' | tee -a /config/reports/deploy_receipt.txt
./_backups/docs/ADR/_autofix_backups/ADR-0008-end-to-end-flow.md.autofix.bak:177:# Ensure addon/config.yaml:version == tag
./_backups/docs/ADR/_autofix_backups/ADR-0008-end-to-end-flow.md.autofix.bak:183:- **“Add‑on not available inside store”**: ensure `/addons/local/beep_boop_bb8/config.yaml` exists, then UI → *Add‑on Store → HA‑BB8 (local)- → **Install**; or run `ssh babylon-babes@homeassistant "ha addons reload"`.
./_backups/docs/ADR/_autofix_backups/ADR-0010-unified-supervision-and-diag.md.autofix.bak:21:2. Emit deterministic DIAG events for runloop attempts, process starts, and child exits; persist to `/data/reports/ha_bb8_addon.log`.  
./_backups/docs/ADR/ADR-0008-end-to-end-flow.md.autofix.bak:24:- Supervisor builds locally when `addon/config.yaml` contains a **`build:`*- block **and `image:` is absent**. Use `image:` **only for PUBLISH*- (pull from a registry).

=== .github workflows
total 104
drwxr-xr-x@ 15 evertappels  staff   480 Sep 22 18:26 .
drwxr-xr-x@  6 evertappels  staff   192 Sep 22 16:28 ..
-rw-r--r--@  1 evertappels  staff   623 Aug 23 12:41 addon-audit.yml
-rw-r--r--@  1 evertappels  staff   505 Sep 13 20:56 adr-governance.yml
-rw-r--r--@  1 evertappels  staff  2860 Sep 19 13:38 adr-structure.yml
-rw-r--r--@  1 evertappels  staff   813 Aug 23 12:41 governance-gates.yaml
-rw-r--r--@  1 evertappels  staff  2787 Sep 22 19:21 index.jsonl
-rw-r--r--@  1 evertappels  staff   610 Sep 21 11:34 log_sanity.yml
-rw-r--r--@  1 evertappels  staff  1157 Sep 23 22:37 regenerate_indexes.yml
-rw-r--r--@  1 evertappels  staff   677 Sep  5 14:45 repo-guards.yml
-rw-r--r--@  1 evertappels  staff  1435 Sep 21 04:35 shape.yml
-rw-r--r--@  1 evertappels  staff   866 Sep 21 04:47 smoke_mqtt.yml
-rw-r--r--@  1 evertappels  staff   367 Sep 13 16:23 snapshot-policy-check.yml
-rw-r--r--@  1 evertappels  staff  2328 Sep 14 03:19 snapshot.yml
-rw-r--r--@  1 evertappels  staff   603 Sep 13 14:56 tests.yml
```

---

## Decision

BB-8 is lean, container-centric — keep NAS-primary, no Git LFS, and apply light guardrails.

### Why
- No big binaries; LFS is not necessary.
- Add-on code should keep container paths like `/config` literal (don't parameterize container internals).
- The repo still benefits from size/symlink guards and an optional fetch-only Tailnet/NAS mirror for resilience.

### Minimal, safe changes
- Add a small `.env.sample` for host-side development parameters (do not parameterize in-container literals).
- Install a size/symlink guard (pre-commit hook + CI workflow).

### Apply (copy/paste)
Create a `.env.sample` for host params:

```bash
printf '%s\n' \
'export BB8_WORKDIR="${BB8_WORKDIR:-$PWD}"' \
'export BB8_CONFIG_MOUNT="${BB8_CONFIG_MOUNT:-/config}"' \
> .env.sample
git add .env.sample
git commit -m "chore: add .env.sample (host params only)"
```

Create the validator and hook:

```bash
mkdir -p tools/validators
cat > tools/validators/guard_size_symlinks.sh <<'SH'
#!/usr/bin/env bash
set -euo pipefail

# Fail if symlinks are tracked
BAD_SYMS=$(git ls-files -s | awk '$1 ~ /^120/ {print $4}')
if [ -n "$BAD_SYMS" ]; then
	echo "ERROR: Symlinks tracked in Git"
	echo "$BAD_SYMS"
	exit 2
fi

# Fail if staged files exceed 50MB
git diff --cached --name-only --diff-filter=AM | while read -r f; do
	[ -f "$f" ] || continue
	sz=$(wc -c < "$f")
	[ "$sz" -gt 52428800 ] && echo "ERROR: Large file staged (>50MB): $f ($sz bytes)" && exit 3
done

echo "OK: size/symlink guard passed"
SH

chmod +x tools/validators/guard_size_symlinks.sh
mkdir -p .git/hooks
cat > .git/hooks/pre-commit <<'H'
#!/usr/bin/env bash
set -e
tools/validators/guard_size_symlinks.sh
H
chmod +x .git/hooks/pre-commit
```

Add a CI workflow that runs the same check on PRs and pushes:

```yaml
name: Size/Symlink Guard
on: [push, pull_request]
jobs:
	guard:
		runs-on: ubuntu-latest
		steps:
			- uses: actions/checkout@v4
			- run: bash tools/validators/guard_size_symlinks.sh
```

Install and commit the guard artifacts:

```bash
mkdir -p .github/workflows
cat > .github/workflows/guard-size-symlinks.yml <<'YML'
name: Size/Symlink Guard
on: [push, pull_request]
jobs:
	guard:
		runs-on: ubuntu-latest
		steps:
			- uses: actions/checkout@v4
			- run: bash tools/validators/guard_size_symlinks.sh
YML

git add tools/validators/guard_size_symlinks.sh .github/workflows/guard-size-symlinks.yml
git commit -m "guardrails: size/symlink pre-commit + CI"
git push -u origin HEAD:main
```

⸻

## Setup Block

```
set -euo pipefail
cd "$HOME/Projects/HA-BB8"

git remote set-url origin ssh://gituser@ds220plus.reverse-beta.ts.net/volume1/git-mirrors/ha-config.git

cat > .env.sample <<'ENV'
export BB8_WORKDIR="${BB8_WORKDIR:-$PWD}"
export BB8_CONFIG_MOUNT="${BB8_CONFIG_MOUNT:-/config}"
ENV
git add .env.sample
git commit -m "chore: add .env.sample (host params only)" || true

mkdir -p tools/validators
cat > tools/validators/guard_size_symlinks.sh <<'SH'
#!/usr/bin/env bash
set -euo pipefail
BAD_SYMS=$(git ls-files -s | awk '$1 ~ /^120/ {print $4}')
if [ -n "$BAD_SYMS" ]; then echo "ERROR: symlinks tracked in Git"; echo "$BAD_SYMS"; exit 2; fi
git diff --cached --name-only --diff-filter=AM | while read -r f; do
  [ -f "$f" ] || continue
  sz=$(wc -c < "$f")
  if [ "$sz" -gt 52428800 ]; then echo "ERROR: Large file staged (>50MB): $f ($sz bytes)"; exit 3; fi
done
echo "OK: size/symlink guard passed"
SH
chmod +x tools/validators/guard_size_symlinks.sh

mkdir -p .git/hooks
cat > .git/hooks/pre-commit <<'H'
#!/usr/bin/env bash
set -e
tools/validators/guard_size_symlinks.sh
H
chmod +x .git/hooks/pre-commit

mkdir -p .github/workflows
cat > .github/workflows/guard-size-symlinks.yml <<'YML'
name: Size/Symlink Guard
on: [push, pull_request]
jobs:
  guard:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: bash tools/validators/guard_size_symlinks.sh
YML

git add tools/validators/guard_size_symlinks.sh .github/workflows/guard-size-symlinks.yml
git commit -m "guardrails: size/symlink pre-commit + CI" || true
git push -u origin HEAD:main || true
```

## Setup Block v2

```
#!/usr/bin/env bash
set -euo pipefail

# 0) Ensure repo + clean branch context
git rev-parse --is-inside-work-tree >/dev/null
BRANCH="chore/guard-size-symlinks"
if git show-ref --quiet "refs/heads/$BRANCH"; then
  git switch "$BRANCH"
else
  git switch -c "$BRANCH"
fi

# 1) Install/update validator + CI workflow + local pre-commit (backup with timestamp)
mkdir -p tools/validators .github/workflows
ts=$(date +%Y%m%d-%H%M%S)
[ -f .git/hooks/pre-commit ] && mv .git/hooks/pre-commit ".git/hooks/pre-commit.bak.$ts" || true

cat > tools/validators/guard_size_symlinks.sh <<'SH'
#!/usr/bin/env bash
set -euo pipefail

thresh=$((50*1024*1024))   # 50 MB
mode="local"; [ "${CI:-}" = "true" ] && mode="ci"
fail(){ printf '%s\n' "$*" >&2; exit 1; }

# 1) Block tracked symlinks
BAD_SYMS="$(git ls-files -s | awk '$1 ~ /^120/ {print $4}')"
[ -n "$BAD_SYMS" ] && fail "ERROR: symlinks tracked in Git:\n$BAD_SYMS"

# 2) Build NUL-delimited list of files to check
declare -a DIFF_CMD
if [ "$mode" = "local" ]; then
  DIFF_CMD=(git diff --cached --name-only --diff-filter=AM -z)
else
  if [ -n "${GITHUB_BASE_REF:-}" ]; then
    base_ref="$GITHUB_BASE_REF"
    git fetch origin "$base_ref" --depth=1 || true
    DIFF_CMD=(git diff --name-only "origin/${base_ref}...HEAD" -z)
  else
    git fetch origin main --depth=1 || true
    DIFF_CMD=(git diff --name-only origin/main...HEAD -z)
  fi
fi

ok=1
# Use process substitution to preserve 'ok' in current shell
if ! "${DIFF_CMD[@]}" >/dev/null 2>&1 || [ -z "$("${DIFF_CMD[@]}" | tr -d '\0')" ]; then
  # Fallback: scan all tracked files (CI safety)
  while IFS= read -r -d '' f; do
    [ -f "$f" ] || continue
    sz=$(wc -c < "$f")
    if [ "$sz" -gt "$thresh" ]; then
      printf 'ERROR: Large file (>50MB): %s (%d bytes)\n' "$f" "$sz" >&2
      ok=0
    fi
  done < <(git ls-files -z)
else
  while IFS= read -r -d '' f; do
    [ -f "$f" ] || continue
    sz=$(wc -c < "$f")
    if [ "$sz" -gt "$thresh" ]; then
      printf 'ERROR: Large file (>50MB): %s (%d bytes)\n' "$f" "$sz" >&2
      ok=0
    fi
  done < <("${DIFF_CMD[@]}")
fi

[ "$ok" -eq 1 ] && echo "OK: size/symlink guard passed" || exit 3
SH
chmod +x tools/validators/guard_size_symlinks.sh

cat > .github/workflows/guard-size-symlinks.yml <<'YML'
name: Guard: block large files & symlinks
on: [push, pull_request]
jobs:
  guard:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - name: Run validator
        run: bash tools/validators/guard_size_symlinks.sh
YML

cat > .git/hooks/pre-commit <<'H'
#!/usr/bin/env bash
set -e
bash tools/validators/guard_size_symlinks.sh
H
chmod +x .git/hooks/pre-commit

# 2) Commit only if something changed, then push feature branch
git add tools/validators/guard_size_symlinks.sh .github/workflows/guard-size-symlinks.yml || true
if [ -n "$(git status --porcelain)" ]; then
  git commit -m "guardrails(bb8): size/symlink pre-commit + CI (CI-aware, filename-safe)"
else
  echo "No changes to commit."
fi

# Prefer 'github' if present, else 'origin'
if git remote get-url github >/dev/null 2>&1; then
  git push -u github "$BRANCH"
else
  git push -u origin "$BRANCH"
fi

echo "✅ Done. Open a PR from '$BRANCH'. Local pre-commit installed; backup saved if one existed."
```