# ════════════════════════════════════════════════════════════════
# ▶ SCRIPT: Git Push Logger ◀
# Synchronizes Home Assistant config to DSM Git mirror.
# path: /config/domain/shell_commands/git_push_logger.sh
# Tier: ζ  •  Domain: system  •  Last Updated: 2025-08-02
# ════════════════════════════════════════════════════════════════

#!/bin/bash
set -euo pipefail

REPO_DIR="/config"
SSH_CMD="ssh -F /config/.ssh/config"
REMOTE="dsm-git"
BRANCH="main"
BARE_REMOTE="ssh://dsm-git-host:/volume1/HA_MIRROR"


## Ensure IdentityFile in /config/.ssh/config is absolute and valid inside the container.
#if grep -E '^\s*IdentityFile\s+[^/]' /config/.ssh/config >/dev/null; then
#  echo "[git_push_logger] ❌ ERROR: IdentityFile in /config/.ssh/config must be an absolute path (e.g., /config/.#ssh/id_ed25519), not relative." >&2
#  exit 2
#fi

# Determine the effective IdentityFile used for dsm-git-host
EFFECTIVE_KEY="$(ssh -F /config/.ssh/config -G dsm-git-host | awk 'tolower($1)=="identityfile"{print $2; exit}')"
if [ -z "${EFFECTIVE_KEY:-}" ] || [ "${EFFECTIVE_KEY:0:1}" != "/" ]; then
  echo "[git_push_logger] ❌ ERROR: IdentityFile for dsm-git-host must be an absolute path (got: '${EFFECTIVE_KEY:-<none>}')." >&2
  exit 2
fi

# SSH & Git must use explicitly defined config in HA context
export GIT_SSH_COMMAND='ssh -F /config/.ssh/config -o UserKnownHostsFile=/config/.ssh/known_hosts'

BRANCH=$(git --git-dir=/config/.git --work-tree=/config rev-parse --abbrev-ref HEAD)
TIMESTAMP=$(date -Iseconds) # Supported by Busybox
NOTIFY_TITLE="🌀 Git Sync: $BRANCH → DSM"
LOG_FILE="/config/hestia/diagnostics/logs/git_sync_push_events.json"
PRECHECK_REMOTE="dsm-git"
REPO_PATH=/volume1/HA_MIRROR
PRECHECK_RETRIES=3
SLEEP_BETWEEN_RETRIES=5

echo "[git_push_logger] Verifying remote bare repo is reachable..." >&2
if ! ssh -F /config/.ssh/config dsm-git-host \
  "git --git-dir='$REPO_PATH' for-each-ref --format='%(refname:short)' refs/heads/main" >/dev/null 2>&1; then
  echo "[git_push_logger] ❌ Remote bare repo $REPO_PATH not accessible via SSH." >&2
  echo "[git_push_logger]    Try this manually from HA shell:" >&2
  echo "  ssh -F /config/.ssh/config dsm-git-host \"git --git-dir='$REPO_PATH' for-each-ref --format='%(objectname:short)' refs/heads/main\"" >&2
  exit 3
fi
PRECHECK_RETRIES=3
SLEEP_BETWEEN_RETRIES=5

echo "[git_push_logger] Initial delay to allow networking..." >&2
sleep 10

# Preflight SSH test loop
# Check SSH using same command Git will use
echo "[git_push_logger] Checking SSH access to $PRECHECK_REMOTE..." >&2
echo "[git_push_logger] Testing SSH connection with config: /config/.ssh/config"
ssh -v -F /config/.ssh/config dsm-git-host exit
for i in $(seq 1 "$PRECHECK_RETRIES"); do
  if git --git-dir=/config/.git --work-tree=/config ls-remote dsm-git &>/dev/null; then
  echo "[git_push_logger] ✅ SSH connection to dsm-git-host succeeded (attempt $i)" >&2
    break
  elif [[ $i -eq "$PRECHECK_RETRIES" ]]; then
    echo "[git_push_logger] ❌ SSH failed after $i attempts. Aborting." >&2
    echo "[git_push_logger] SSH to dsm-git failed. Full command used:" >> /config/hestia/diagnostics/logs/git_push_logger_errors.log
    echo "ssh -F /config/.ssh/config dsm-git exit" >> /config/hestia/diagnostics/logs/git_push_logger_errors.log
  echo "ssh -F /config/.ssh/config dsm-git-host exit" >> /config/hestia/diagnostics/logs/git_push_logger_errors.log
    curl -s -X POST http://localhost:8123/api/services/persistent_notification/create \
      -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiI2ZjNjMmE2YTc5NWQ0ODE1ODI4ZjBhNjgxYmYyZmYzMiIsImlhdCI6MTc1Mzc3NTY4OSwiZXhwIjoyMDY5MTM1Njg5fQ.KoxNPipk0INgbdbSZOZOQUt17x8LOLQrgcoSgzXAQ5M" \
      -H "Content-Type: application/json" \
      -d '{"title": "'"$NOTIFY_TITLE"'", "message": "SSH check to DSM remote failed after '"$i"' attempts at '"$TIMESTAMP"'"}'
    exit 3
  else
    echo "[git_push_logger] ⚠️ SSH attempt $i failed, retrying in $SLEEP_BETWEEN_RETRIES seconds..." >&2
    sleep "$SLEEP_BETWEEN_RETRIES"
  fi
done

# Attempt Git push
echo "[git_push_logger] Attempting git push..." >&2
if ! git -C "$REPO_DIR" -c core.sshCommand="$SSH_CMD" push "$REMOTE" "$BRANCH"; then
  echo "[git_push_logger] ❌ Git push to $BRANCH failed." >&2
  curl -s -X POST http://localhost:8123/api/services/persistent_notification/create \
    -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiI2ZjNjMmE2YTc5NWQ0ODE1ODI4ZjBhNjgxYmYyZmYzMiIsImlhdCI6MTc1Mzc3NTY4OSwiZXhwIjoyMDY5MTM1Njg5fQ.KoxNPipk0INgbdbSZOZOQUt17x8LOLQrgcoSgzXAQ5M" \
    -H "Content-Type: application/json" \
    -d '{"title": "'"$NOTIFY_TITLE"'", "message": "Git push to '"$BRANCH"' failed at '"$TIMESTAMP"'"}'
  exit 4
fi

# Log successful sync with commit metadata
LATEST_COMMIT_HASH=$(git --git-dir=/config/.git --work-tree=/config rev-parse "$BRANCH")
LATEST_COMMIT_MSG=$(git --git-dir=/config/.git --work-tree=/config log -1 --pretty=%s "$BRANCH")

jq -n --arg timestamp "$TIMESTAMP" \
      --arg commit_hash "$LATEST_COMMIT_HASH" \
      --arg commit_msg "$LATEST_COMMIT_MSG" \
      --arg result "success" \
      '{ timestamp: $timestamp, commit_hash: $commit_hash, commit_msg: $commit_msg, result: $result }' >> "$LOG_FILE"

# Push timestamp to input_datetime (optional)
curl -s -X POST http://localhost:8123/api/services/input_datetime/set_datetime \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiI2ZjNjMmE2YTc5NWQ0ODE1ODI4ZjBhNjgxYmYyZmYzMiIsImlhdCI6MTc1Mzc3NTY4OSwiZXhwIjoyMDY5MTM1Njg5fQ.KoxNPipk0INgbdbSZOZOQUt17x8LOLQrgcoSgzXAQ5M" \
  -H "Content-Type: application/json" \
  -d '{"entity_id": "input_datetime.git_last_push_timestamp", "datetime": "'"$TIMESTAMP"'"}'

echo "[git_push_logger] ✅ Completed successfully." >&2

# 🧠 Optional: Log latest remote commit (bare repo)
REMOTE_COMMIT_HASH=$(ssh -F /config/.ssh/config dsm-git-host \
  "git --git-dir=/volume1/HA_MIRROR for-each-ref --format='%(objectname)' refs/heads/main")

REMOTE_COMMIT_MSG=$(ssh -F /config/.ssh/config dsm-git-host \
  "git --git-dir=/volume1/HA_MIRROR show -s --format=%s refs/heads/main")

echo "[git_push_logger] ✅ Remote repo updated."
echo "[git_push_logger] 📦 Commit: $REMOTE_COMMIT_HASH"
echo "[git_push_logger] 📝 Message: $REMOTE_COMMIT_MSG"

exit 0

# NOTE: The SSH config at /config/.ssh/config must use absolute paths for IdentityFile, e.g.:
#   IdentityFile /config/.ssh/id_ed25519
# Relative paths will not work inside the container context.
# (If you use timeout for any command, lower from 60s to 20s for debugging)
