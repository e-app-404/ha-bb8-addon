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

_Last updated: 2025-08-24_
