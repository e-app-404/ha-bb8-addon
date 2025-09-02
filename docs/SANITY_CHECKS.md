# 6) MQTT Callback Compliance
grep -E '\[ \]' /addons/local/beep_boop_bb8/reports/callback_signature_matrix.md && echo "DRIFT: CALLBACK_SIGNATURE_MISMATCH" || echo "TOKEN: CALLBACK_SIGNATURE_OK"

# 7) Test Suite Health
cd /addons/local/beep_boop_bb8
pytest --maxfail=1 --disable-warnings -q && echo "TOKEN: TESTS_OK" || echo "DRIFT: TEST_FAILURE"

# 8) Resource Stability
grep -E 'Out of memory|DeprecationWarning|thread leak' /config/reports/ha_bb8_addon.log && echo "DRIFT: RESOURCE_ISSUE" || echo "TOKEN: RESOURCE_OK"

# 9) Warning Suppression Audit
grep -E 'filterwarnings|PYTHONWARNINGS' /addons/local/beep_boop_bb8/addon/bb8_core/*.py && echo "TOKEN: WARNING_SUPPRESSION_PRESENT"

# Add-on Health: Operational Sanity Checks


Run these commands via SSH as babylon-babes@homeassistant (or in the Terminal add-on):

```sh
# 1) Addressable name (Supervisor) and basic metadata
ssh babylon-babes@homeassistant "ha addons list | grep -E '^  slug:\s+local_beep_boop_bb8' && echo 'TOKEN: ADDON_LISTED'"

# 2) YAML view (works with default output)
ssh babylon-babes@homeassistant "ha addons info local_beep_boop_bb8 | yq '.slug, .version, .repository'"

# 3) Build context folder must exist and be plain (no .git)
ssh babylon-babes@homeassistant "ls -la /addons/local/beep_boop_bb8"
ssh babylon-babes@homeassistant "test -d /addons/local/beep_boop_bb8/.git && echo 'DRIFT: runtime_nested_git' || echo 'TOKEN: RUNTIME_PLAIN_OK'"

# 4) Rebuild & (re)start (only when you intend to refresh the image)
ssh babylon-babes@homeassistant "ssh babylon-babes@homeassistant "ha addons reload""
ssh babylon-babes@homeassistant "ssh babylon-babes@homeassistant "ha addons rebuild local_beep_boop_bb8""
ssh babylon-babes@homeassistant "ssh babylon-babes@homeassistant "ha addons start local_beep_boop_bb8""

# 5) Verify state + version
ssh babylon-babes@homeassistant "ha addons info local_beep_boop_bb8 | grep -E '^(state|version|version_latest):' && echo 'TOKEN: REBUILD_OK'"

# Or run the full check script (if present):
ssh babylon-babes@homeassistant "bash /config/hestia/work/utils/ha_addon_sanity_check.sh"
```

**Expected tokens/outcomes:**
- TOKEN: ADDON_LISTED
- TOKEN: RUNTIME_PLAIN_OK
- TOKEN: REBUILD_OK (after a successful rebuild/start)

_Last updated: 2025-08-27_
