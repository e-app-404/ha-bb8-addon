---
id: ADR-0033
title: "Dual-Clone Deployment Topology & Git Hygiene"
date: 2025-09-28
status: Accepted
author:
  - Operational Evidence Analysis
related: ["ADR-0001", "ADR-0008", "ADR-0031", "ADR-0032"]
supersedes: []
last_updated: 2025-09-28
tags: ["deployment", "topology", "git", "hygiene", "tokens", "governance", "automation"]
---

# ADR-0033: Dual-Clone Deployment Topology & Git Hygiene

**Session Evidence Sources:**
- `WS-RESTORE-ADDON-DUAL-CLONE` (`ws-restore-2025-08-21`) - Complete dual-clone implementation
- `STP4-STRICT` pre-execution briefing - Rollback and deployment strategies
- Multiple tokenized deployment confirmations with Git SHA verification

## Context

**Problem Statement:** Establish a deterministic deployment topology that maintains workspace and runtime as separate Git clones while ensuring perfect synchronization, eliminating historical drift issues caused by symlinks and duplicated directories.

**Investigation Method:** 
- Iterative deployment testing with Git SHA verification
- Tokenized validation system implementation
- Repository hygiene procedures with `.gitignore` guards
- SSH connectivity and rebase conflict resolution

**Evidence Gathered:**

### Successful Deployment Sequences
```bash
# Example deployment token sequence
DEPLOY_OK runtime_head=243c989 branch=main
VERIFY_OK ws_head=243c989 runtime_head=243c989 remote=git@github.com:e-app-404/ha-bb8-addon.git
STRUCTURE_OK
WS_READY addon_ws=git_clone_ok runtime=git_clone_ok reports=ok wrappers=ok ops=ok

# Final confirmation after hygiene procedures
DEPLOY_OK runtime_head=6e2e2e2 branch=main  
VERIFY_OK ws_head=6e2e2e2 runtime_head=6e2e2e2 remote=git@github.com:e-app-404/ha-bb8-addon.git
STRUCTURE_OK
WS_READY addon_ws=git_clone_ok runtime=git_clone_ok reports=ok wrappers=ok ops=ok
```

### Repository Hygiene Evidence
```bash
# Successful workspace-only directory removal
[repo ok]
[runtime ok]
[ok] no tracked workspace-only files
[ok] gitignore guards present
[ok] runtime clean
```

### Git Connectivity Validation
```bash
# Remote reachability confirmation
GIT_TERMINAL_PROMPT=0 GIT_SSH_COMMAND='ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15' 
git ls-remote "git@github.com:e-app-404/ha-bb8-addon.git" >/dev/null && echo "[ok] remote reachable"
[ok] remote reachable
```

## Decision

**Technical Choice:** Implement a **dual-clone deployment topology** with Git-based synchronization, tokenized validation, and automated repository hygiene enforcement.

### 1. Dual-Clone Architecture

**Core Deployment Pattern:**
```bash
# Workspace → Remote → Runtime synchronization
git -C "$ADDON" push origin HEAD:main              # Push workspace changes
git -C "$RUNTIME" fetch --all --prune              # Fetch all remote changes  
git -C "$RUNTIME" checkout -B main origin/main     # Create/switch to main branch
git -C "$RUNTIME" reset --hard origin/main         # Hard reset to remote state
```

**Path Structure:**
- **Workspace:** `/Users/evertappels/Projects/HA-BB8/addon` (development)
- **Runtime:** `/Volumes/addons/local/beep_boop_bb8` (Home Assistant execution)
- **Remote:** `git@github.com:e-app-404/ha-bb8-addon.git` (single source of truth)

### 2. Tokenized Validation System

**Four-Token Validation Gates:**
```bash
# Required tokens for successful deployment
STRUCTURE_OK    # Repository structure validation
VERIFY_OK       # SHA synchronization confirmation  
WS_READY        # Workspace health check
DEPLOY_OK       # Deployment completion confirmation

# Token extraction command
grep -hE 'STRUCTURE_OK|VERIFY_OK|WS_READY|DEPLOY_OK' reports/{structure_check_run_*,verify_workspace_run_*}.log
```

### 3. Repository Hygiene Enforcement

**Workspace-Only Directory Removal:**
```bash
# Remove workspace-only directories from addon repository
git -C "$ADDON" rm -r --ignore-unmatch docs scripts tools reports addon .github
rm -rf "$ADDON"/{docs,scripts,tools,reports,addon,.github}

# Add .gitignore guards to prevent reintroduction
printf "\n/docs/\n/scripts/\n/tools/\n/reports/\n/addon/\n/.github/\n" >> "$ADDON/.gitignore"
git -C "$ADDON" push origin HEAD:main

# Clean runtime of workspace-only artifacts
rm -rf "$RUNTIME"/{docs,scripts,tools,reports,addon,.github}
git -C "$RUNTIME" clean -fdX
```

### 4. SSH Connectivity & Conflict Resolution

**Non-Interactive Git Operations:**
```bash
# Safe SSH configuration for automated operations
GIT_TERMINAL_PROMPT=0 
GIT_SSH_COMMAND='ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15'

# Qualified refspec to prevent orphan HEAD creation
git -C "$ADDON" push origin HEAD:main  # NOT: git push origin HEAD

# Rebase conflict resolution (unionize .gitignore rulesets)
git -C "$ADDON" rebase origin/main
```

### 5. Release Tagging Integration

**Version-Tagged Releases:**
```bash
# Tag releases with version alignment
git -C "$ADDON" tag -a v2025.8.21 -m "Release 2025.8.21"
git -C "$ADDON" push --tags

# Verify version consistency
grep "version:" "$ADDON/config.yaml"  # version: "2025.08.21"
```

## Consequences

### Positive
- **Deterministic deployments** with branch-based hard reset eliminating drift
- **Token-based validation** provides clear success/failure signals
- **Repository hygiene** prevents workspace-only artifacts from entering runtime
- **Non-interactive Git operations** suitable for automation and CI/CD
- **SHA synchronization verification** ensures workspace and runtime alignment
- **Rollback safety** through Git history and tag-based release points

### Negative
- **Runtime edits discarded** by design unless explicitly promoted to workspace
- **Discipline required** to maintain workspace-only asset boundaries
- **Additional complexity** in deployment scripts for dual-clone management
- **SSH key management** required for automated Git operations

### Unknown/Untested
- **Automated HA restart integration** (only "HA Restarted" message observed)
- **CI enforcement** of token validation on PRs
- **Large repository performance** with frequent hard resets
- **Concurrent deployment handling** if multiple operators deploy simultaneously

## Implementation Evidence

### Commands Verified
```bash
# Complete deployment sequence (executed successfully)
git -C "/Users/evertappels/Projects/HA-BB8/addon" push origin HEAD:main
git -C "/Volumes/addons/local/beep_boop_bb8" fetch --all --prune
git -C "/Volumes/addons/local/beep_boop_bb8" checkout -B main origin/main
git -C "/Volumes/addons/local/beep_boop_bb8" reset --hard origin/main
git -C "/Users/evertappels/Projects/HA-BB8/addon" tag -a v2025.8.21 -m "Release 2025.8.21"
git -C "/Users/evertappels/Projects/HA-BB8/addon" push --tags

# Repository hygiene commands (executed successfully) 
git -C "$ADDON" rm -r --ignore-unmatch docs scripts tools reports addon .github
printf "\n/docs/\n/scripts/\n/tools/\n/reports/\n/addon/\n/.github/\n" >> "$ADDON/.gitignore"
rm -rf "$RUNTIME"/{docs,scripts,tools,reports,addon,.github}
git -C "$RUNTIME" clean -fdX

# Testing integration (executed successfully)
python3 -m pytest -q "/Users/evertappels/Projects/HA-BB8/addon/tests"
bash "/Users/evertappels/Projects/HA-BB8/ops/audit/check_structure.sh"
bash "/Users/evertappels/Projects/HA-BB8/scripts/verify_workspace.sh"
```

### Configuration Discovered
```yaml
# addon/config.yaml version alignment
version: "2025.08.21"

# .gitignore guards (added)
/docs/
/scripts/
/tools/
/reports/
/addon/
/.github/
```

### Log Patterns Observed
```bash
# Successful deployment tokens
DEPLOY_OK runtime_head=<sha> branch=<branch>
VERIFY_OK ws_head=<sha> runtime_head=<sha> remote=git@github.com:e-app-404/ha-bb8-addon.git
STRUCTURE_OK
WS_READY addon_ws=git_clone_ok runtime=git_clone_ok reports=ok wrappers=ok ops=ok

# Repository hygiene validation  
[repo ok]
[runtime ok]
[ok] no tracked workspace-only files
[ok] gitignore guards present
[ok] runtime clean

# Git operation patterns
[ok] remote reachable
error: The destination you provided is not a full refname ... (resolved)
fatal: 'HEAD' is not a valid branch name (resolved)

# Test integration success
...................                                                                                                               [100%]
```

## Rollback & Recovery Procedures

### Emergency Rollback Strategy
```bash
# Pre-failure rollback (if deployment issues detected)
git -C "$RUNTIME" reset --hard <previous_good_sha>
git -C "$ADDON" reset --hard <previous_good_sha>

# Post-failure rollback (restore from known good state)
git -C "$RUNTIME" fetch --all --prune
git -C "$RUNTIME" checkout -B main origin/main
git -C "$RUNTIME" reset --hard <rollback_tag>  # e.g., v2025.8.20

# Environment toggle rollback (for STP4 strict failures)
export REQUIRE_DEVICE_ECHO=0
export ENABLE_BRIDGE_TELEMETRY=0
# Re-run deployment with shim enabled
```

### Token Validation for Rollback Success
```bash
# Verify rollback completed successfully
grep -hE 'STRUCTURE_OK|VERIFY_OK|WS_READY|DEPLOY_OK' reports/rollback_*.log

# Expected output confirms successful rollback
DEPLOY_OK runtime_head=<rollback_sha> branch=main
VERIFY_OK ws_head=<rollback_sha> runtime_head=<rollback_sha>
STRUCTURE_OK
WS_READY addon_ws=git_clone_ok runtime=git_clone_ok reports=ok wrappers=ok ops=ok
```

## Integration with Existing ADRs

### ADR-0031 Integration
- **Token validation** feeds into comprehensive operational validation
- **Deployment automation** supports release pipeline with explicit success markers
- **Testing integration** ensures pytest validation before deployment

### ADR-0032 Integration  
- **Repository hygiene** supports clean MQTT/BLE integration without workspace artifacts
- **SSH connectivity validation** ensures reliable Git operations for integration testing
- **Version synchronization** maintains consistency between integration and deployment

## Gaps Requiring Further Investigation

### Critical
- **CI token enforcement** on PRs to prevent broken deployments
- **Automated HA restart integration** beyond observed "HA Restarted" message
- **Concurrent deployment conflict resolution** for multi-operator scenarios

### Secondary
- **Performance optimization** for large repository hard resets
- **Deployment notification integration** (Slack, email) for team coordination
- **Deployment metrics** (timing, success rates, rollback frequency)

## References

**Source Files Examined:**
- `addon/config.yaml` (version alignment)
- `.gitignore` (hygiene guards)
- Deployment logs with token validation
- Git operation outputs with SHA verification

**Commands Executed:**
- Complete dual-clone deployment sequence with token validation
- Repository hygiene procedures with verification
- SSH connectivity testing and conflict resolution
- Integration with pytest validation

**Tests Performed:**
- End-to-end deployment with SHA synchronization verification
- Repository hygiene validation with workspace-only directory removal
- Token extraction and validation for deployment success
- Git rebase conflict resolution and `.gitignore` union merge

**Session References:**
- WS-RESTORE-ADDON-DUAL-CLONE: Complete implementation and validation
- STP4-STRICT pre-execution briefing: Rollback strategies and environment toggles
- Multiple deployment confirmations: Token sequences and SHA verification
- 2025-10-04: Active workspace content merge strategy implementation (see ADR-0017)

---

**Extraction Date:** 28 September 2025, Updated: 4 October 2025
**Session ID/Reference:** Synthesis of dual-clone deployment validation sessions
**Evidence Quality:** Complete for deployment topology; Partial for CI integration and concurrent operations