#!/usr/bin/env bash
# Hardened macOS SMB mount helper for HA mirror
# - Reads credentials from /etc/ha_mount_credentials (root-owned) or environment
# - Uses macOS mount_smbfs syntax (//user[:pass]@host/share)
# - URL-encodes password to avoid shell/URL issues
# - Logs to /var/log/ha-mount.log
# - Runs smbutil and mount checks and does a write test as TARGET_USER

set -euo pipefail

LOG=/var/log/ha-mount.log
MOUNT_POINT=/private/var/ha_real
# Defaults (can be overridden by /etc/ha_mount_credentials or environment)
HA_MOUNT_USER=${HA_MOUNT_USER:-babylonrobot}
HA_MOUNT_PASS=${HA_MOUNT_PASS:-}
HA_MOUNT_HOST=${HA_MOUNT_HOST:-192.168.0.104}
HA_MOUNT_SHARE=${HA_MOUNT_SHARE:-HA_MIRROR}
TARGET_USER=${TARGET_USER:-$(stat -f "%Su" /dev/console || echo root)}

timestamp() { printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"; }

log() {
    timestamp "$*" >> "$LOG"
}

# Load credential file if present (root-owned expected)
if [ -r /etc/ha_mount_credentials ]; then
    # shellcheck disable=SC1090
    . /etc/ha_mount_credentials
    log "Loaded /etc/ha_mount_credentials"
fi

log "=== ha_mount_helper invocation ==="
log "Target user: ${TARGET_USER}"

if ! id "$TARGET_USER" >/dev/null 2>&1; then
    log "WARNING: TARGET_USER '$TARGET_USER' not found; falling back to root"
    TARGET_USER=root
fi

UID_OF_TARGET=$(id -u "$TARGET_USER") || UID_OF_TARGET=0
GID_OF_TARGET=$(id -g "$TARGET_USER") || GID_OF_TARGET=0
log "Resolved TARGET_USER=$TARGET_USER UID=$UID_OF_TARGET GID=$GID_OF_TARGET"

mkdir -p "$MOUNT_POINT"

# URL-encode password if present using python3 (portable on macOS with python3 installed)
urlencode() {
    local raw="$1"
    if [ -z "$raw" ]; then
        printf ''
        return
    fi
    if command -v python3 >/dev/null 2>&1; then
        python3 - <<PY
import sys, urllib.parse
print(urllib.parse.quote(sys.argv[1], safe=''))
PY
    else
        # Fallback: rudimentary percent-encode of space and #%&+/:?@[]
        echo "$raw" | sed -e 's/%/%25/g' -e 's/ /%20/g' -e 's/#/%23/g' -e 's/\&/%26/g' -e "s/\+/\%2B/g" -e "s/\//%2F/g" -e "s/:/%3A/g" -e "s/?/%3F/g" -e "s/@/%40/g" -e "s/\[/\%5B/g" -e "s/\]/\%5D/g"
    fi
}

ENC_PASS=""
if [ -n "${HA_MOUNT_PASS:-}" ]; then
    ENC_PASS=$(urlencode "$HA_MOUNT_PASS")
fi

try_mount() {
    local url="$1"
    log "Attempting mount: $url -> $MOUNT_POINT"
    # capture stderr for diagnostics
    if /sbin/mount_smbfs "$url" "$MOUNT_POINT" 2>>"$LOG"; then
        log "mount_smbfs succeeded"
        return 0
    else
        log "mount_smbfs failed (see log for details)"
        return 1
    fi
}

# First, try an authenticated mount if password is present
if [ -n "$ENC_PASS" ]; then
    SMB_URL="//${HA_MOUNT_USER}:${ENC_PASS}@${HA_MOUNT_HOST}/${HA_MOUNT_SHARE}"
    if try_mount "$SMB_URL"; then
        MOUNT_OK=1
    else
        MOUNT_OK=0
    fi
else
    # Try without embedding password (may prompt/interact; in launchd this will fail)
    SMB_URL="//${HA_MOUNT_USER}@${HA_MOUNT_HOST}/${HA_MOUNT_SHARE}"
    if try_mount "$SMB_URL"; then
        MOUNT_OK=1
    else
        MOUNT_OK=0
    fi
fi

if [ "$MOUNT_OK" -ne 1 ]; then
    log "ERROR: mount attempts failed. Capturing diagnostics."
    log "mount output:"; mount | grep "on ${MOUNT_POINT} " || log "(not mounted)"
    log "smbutil status:"; smbutil status 2>>"$LOG" || true
    log "smbutil statshares -a:"; smbutil statshares -a 2>>"$LOG" || true
    log "End diagnostics"
    log "ERROR: all mount attempts failed. Inspect server-side ACLs, credentials, and $LOG"
    exit 1
fi

# Verify the mount is present
if mount | grep "on ${MOUNT_POINT} " >/dev/null 2>&1; then
    log "Mount confirmed: $(mount | grep "on ${MOUNT_POINT} ")"
else
    log "ERROR: expected mount not present after mount_smbfs returned success"
    exit 1
fi

# Run smbutil statshares for the specific mount
if command -v smbutil >/dev/null 2>&1; then
    log "smbutil statshares -m $MOUNT_POINT output:"; smbutil statshares -m "$MOUNT_POINT" 2>>"$LOG" || true
fi

# Test writeability as TARGET_USER
TEST_FILE="$MOUNT_POINT/ha_mount_test_$(date +%s)_$$.txt"
if sudo -u "$TARGET_USER" sh -c "umask 022; echo 'ha-mount-test' > '$TEST_FILE'" 2>>"$LOG"; then
    log "WRITE_OK: Successfully wrote $TEST_FILE as $TARGET_USER"
    # Clean up test file
    rm -f "$TEST_FILE" 2>>"$LOG" || true
    log "Mount and write test OK"
    exit 0
else
    log "WRITE_FAIL: Could not write $TEST_FILE as $TARGET_USER. Inspect server ACLs or user mapping."
    exit 2
fi
