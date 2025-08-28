# HA-BB8 Add-on: Local Build & Supervisor Integration

## Local Add-on Folder Structure
- Place your add-on in `/addons/local/beep_boop_bb8` on the Home Assistant host.
- Required files:
  - `config.yaml` (with `slug: "beep_boop_bb8"`)
  - `Dockerfile` (case-sensitive)
  - All referenced files (e.g., `run.sh`, `bb8_core/`, etc.)

## Supervisor Slug Handling
- Supervisor automatically prefixes local add-on slugs with `local_`.
- Use `local_beep_boop_bb8` for all Supervisor CLI commands:
  ```bash
  ha addons reload
  ha addons update local_beep_boop_bb8
  ha addons start local_beep_boop_bb8
  ha addons logs local_beep_boop_bb8
  ```

## Version Bumping & Update
- When you change the `version:` in `config.yaml`, use:
  ```bash
  ha addons update local_beep_boop_bb8
  ```
- Do not use `rebuild` after a version bump; Supervisor expects `update`.

## Troubleshooting
- If Supervisor reports missing images or build errors:
  - Confirm all required files exist and are readable.
  - Folder name and `slug:` must match (`beep_boop_bb8`).
  - No nested `.git` directory or symlinks.
  - Run `ha addons reload` after any change.
  - Use `ha addons list` to confirm the slug Supervisor expects.
- If you see errors about missing images for old versions, you can safely ignore them if your add-on is running and logging as expected.

## Clean Up Old Images
- To remove unused images:
  ```bash
  docker images | grep beep_boop_bb8
  docker rmi <IMAGE_ID>
  ```

## Summary
- Folder: `/addons/local/beep_boop_bb8`
- `config.yaml`: `slug: "beep_boop_bb8"`
- Supervisor CLI: use `local_beep_boop_bb8` as the slug
- Use `update` for version changes
- All required files must exist in the folder


## Operational Sanity Checks (Run from Home Assistant)

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
