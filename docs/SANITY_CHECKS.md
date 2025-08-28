
# Add-on Health: Operational Sanity Checks

Run these commands directly on your Home Assistant box (SSH or Terminal add-on):

```sh
# 1) Addressable name (Supervisor) and basic metadata
ha addons list | grep -E '^  slug:\s+local_beep_boop_bb8' && echo "TOKEN: ADDON_LISTED"

# 2) YAML view (works with default output)
ha addons info local_beep_boop_bb8 | yq '.slug, .version, .repository'

# 3) Build context folder must exist and be plain (no .git)
ls -la /addons/local/beep_boop_bb8
test -d /addons/local/beep_boop_bb8/.git && echo "DRIFT: runtime_nested_git" || echo "TOKEN: RUNTIME_PLAIN_OK"

# 4) Rebuild & (re)start (only when you intend to refresh the image)
ha addons reload
ha addons rebuild local_beep_boop_bb8
ha addons start  local_beep_boop_bb8

# 5) Verify state + version
ha addons info local_beep_boop_bb8 | grep -E '^(state|version|version_latest):' && echo "TOKEN: REBUILD_OK"

# Or run the full check script (if present):
bash /config/hestia/work/utils/ha_addon_sanity_check.sh
```

**Expected tokens/outcomes:**
- TOKEN: ADDON_LISTED
- TOKEN: RUNTIME_PLAIN_OK
- TOKEN: REBUILD_OK (after a successful rebuild/start)

_Last updated: 2025-08-27_
