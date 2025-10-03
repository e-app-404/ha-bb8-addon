# Git Topology Synchronization Fix

## Problem
NAS mirror (`origin`) has diverged from GitHub (`github`), causing non-fast-forward rejections during addon publishing.

## Root Cause
- GitHub main: `8de2dd589d4e559f90c65629696f7fcf7d5cd7cd`
- NAS main: `eed64ccd2923a4536ee29679a57ce21458a8c312` 
- Divergence violates ADR-0019/ADR-0028 mirror policy

## Solution (ADR-0028 Compliant)

### Step 1: Backup Current States
`bash
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
echo \"Backup timestamp: $STAMP\"

# Backup GitHub main
git push github github/main:refs/heads/backup/main-github-$STAMP
git push github github/main:refs/tags/backup/main-github-$STAMP

# Backup NAS main  
git push origin origin/main:refs/heads/backup/main-nas-$STAMP
git push origin origin/main:refs/tags/backup/main-nas-$STAMP
`

### Step 2: Sync NAS Mirror to GitHub (ADR-0019 Pull-Through)
`bash
# Option A: NAS fetch from GitHub (preferred)
ssh gituser@ds220plus.reverse-beta.ts.net \"cd /volume1/git-mirrors/ha-config.git && git fetch --prune https://github.com/e-app-404/ha-bb8-addon.git +refs/heads/main:refs/heads/main\"

# Option B: If fetch blocked, admin low-level update (ADR-0028)
ssh gituser@ds220plus.reverse-beta.ts.net \"cd /volume1/git-mirrors/ha-config.git && git update-ref refs/heads/main 8de2dd589d4e559f90c65629696f7fcf7d5cd7cd\"
`

### Step 3: Verify Triad Synchronization (ADR-0028)
`bash
echo \"=== Verifying SHA alignment ===\"
echo \"Local HEAD: $(git rev-parse HEAD)\"
echo \"GitHub main: $(git ls-remote --heads github main | awk '{print $1}')\"
echo \"NAS main: $(git ls-remote --heads origin main | awk '{print $1}')\"
# All should match after sync
`

### Step 4: Clean Workspace and Retry Release
`bash
# Clean workspace (remove unstaged changes)
git add docs/ADR/ADR-0033-dual-clone-topology-git-hygiene.md  # Keep ADR changes
git reset --hard HEAD
git clean -fd

# Retry release with synchronized topology
make release-patch
`

## Alternative: Fix publish_addon_archive.sh (Long-term)

The script violates ADR-0033 by creating orphan commits. Consider modifying it to:

1. **Use GitHub as primary remote** instead of origin
2. **Implement proper dual-clone synchronization** 
3. **Add SHA verification** before force-push

`bash
# In ops/release/publish_addon_archive.sh, replace:
# git push -f origin HEAD:\"${TARGET_BRANCH}\"

# With ADR-0033 compliant approach:
REMOTE_URL=\"$(git remote get-url github)\"
git push -f \"$REMOTE_URL\" HEAD:\"${TARGET_BRANCH}\"

# Then sync NAS mirror via pull-through
`

## Prevention (ADR-0019 Compliance)

1. **Always use GitHub as source of truth** for releases
2. **NAS mirror should be pull-only** (no direct pushes)
3. **Implement automated mirror sync** after GitHub updates
4. **Add topology validation** to release scripts

## Emergency Rollback

If sync fails:
`bash
# Restore GitHub main
git push --force-with-lease=main github backup/main-github-$STAMP:main

# Restore NAS main
git push --force-with-lease=main origin backup/main-nas-$STAMP:main
`

## Receipt
Date: 2025-09-29 
Action: Git topology synchronization per ADR-0028 
Reason: Fix non-fast-forward rejection in addon publishing 
Backup refs: `backup/main-github-$STAMP`, `backup/main-nas-$STAMP`
