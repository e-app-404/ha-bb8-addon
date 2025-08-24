# ADR: Home Assistant Add-on Local Build & Slug Management

## Context
Home Assistant Supervisor manages local add-ons using a combination of folder names and `config.yaml` fields. Correct configuration is essential for local builds, image tagging, and add-on lifecycle management.

## Rules & Patterns

### 1. Add-on Folder Naming
- Local add-ons must reside in `/addons/local/<slug>`.
- The folder name should match the intended add-on slug, typically prefixed with `local_`.
- Example: `/addons/local/local_beep_boop_bb8` for slug `local_beep_boop_bb8`.

### 2. Slug Field in config.yaml
- The `slug:` field in `config.yaml` must match the folder name.
- Example:
  ```yaml
  slug: "local_beep_boop_bb8"
  ```

### 3. Supervisor Slug Resolution
- Supervisor uses the folder name as the slug for local add-ons.
- If the folder is `/addons/local/beep_boop_bb8`, the slug is `local_beep_boop_bb8`.
- All Supervisor CLI commands must use the resolved slug.

### 4. Required Files
- Each add-on folder must contain at least:
  - `config.yaml`
  - `Dockerfile`
  - Entry script (e.g., `run.sh`)
  - App source files

### 5. config.yaml: Required Keys
- Must include:
  - `name`, `slug`, `version`, `arch`, `image`, `build:`
- `build:` must specify the Dockerfile and any build args.
- Example:
  ```yaml
  build:
    dockerfile: Dockerfile
    args:
      BUILD_FROM: "ghcr.io/home-assistant/{arch}-base-debian:bookworm"
  ```

### 6. Image Tagging
- The `image:` field should use the pattern:
  ```yaml
  image: "local/{arch}-addon-<slug>"
  ```
- Supervisor tags the built image as `local/{arch}-addon-<slug>:<version>`.

### 7. Add-on Lifecycle Commands
- Use the resolved slug for all Supervisor commands:
  ```bash
  ha addons reload
  ha addons rebuild local_beep_boop_bb8
  ha addons start local_beep_boop_bb8
  ha addons logs local_beep_boop_bb8
  ```

### 8. Troubleshooting
- If Supervisor cannot find the add-on, check:
  - Folder name matches `slug:`
  - All required files exist
  - Run `ha addons reload` after changes
  - Use `ha addons list` to confirm slug

## Expectations
- Consistent folder and slug naming prevents Supervisor errors.
- Always reload add-ons after changes to local add-on folders or config.
- Use the exact slug shown in `ha addons list` for all commands.

---

_Last updated: 2025-08-24_
