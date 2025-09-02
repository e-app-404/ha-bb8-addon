# Patch plan: PATCH-BUNDLE-DOCS-20250826

--- 

> **Why these changes?**
> The official docs recommend **commenting out `image:` for local development** so Supervisor **builds locally** from your `Dockerfile`. When `image:` is present, Supervisor **pulls** from a registry. The “require `build:` in `config.yaml`” rule in a few of your docs/guards conflicts with this. We’ll switch to a **mode-aware** policy:
>
> * **LOCAL_DEV** = `image:` **absent** → build locally from `Dockerfile`
> * **PUBLISH** = `image:` **present** → pull the specified tag (must align with `version:`)
>   Sources: HA developer docs on add-on testing (comment out `image:` to force local build) and publishing (use `image:` + tag alignment). ([developers.home-assistant.io][1])

---

## 1) Patch — `docs/OPERATIONS_OVERVIEW.md`

```diff
--- a/docs/OPERATIONS_OVERVIEW.md
+++ b/docs/OPERATIONS_OVERVIEW.md
@@
-**Key rules**
-- `addon/` is **not** a git repo; publish to a separate add-on repository via **`git subtree`**.
-- Supervisor builds **local** images from `/addons/local/beep_boop_bb8` when `config.yaml` has a **`build:`** block.
+**Key rules**
+- `addon/` is **not** a git repo; publish to a separate add-on repository via **`git subtree`**.
+- Supervisor builds **locally** when `image:` is **absent** (commented out) and a `Dockerfile` is present. When `image:` is **present**, Supervisor **pulls** that tag from a registry.

@@
-**Gate:** `config.yaml` has `build:` + `image: local/{arch}-addon-beep_boop_bb8`.  
+**Gate (mode-aware):**
+  - **LOCAL_DEV:** `image:` is **absent** (commented); `Dockerfile` present → Supervisor builds locally.
+  - **PUBLISH:** `image:` is **present** and `version:` aligns with the published tag.

@@
-### Flow F — Local Add-on Version Bump & Rebuild
+### Flow F — Local Add-on Version Bump & Rebuild (LOCAL_DEV)

@@
-**Gotcha:** Without `build:` in `config.yaml`, Supervisor tries to **pull** a `local/` image → 404. Always include `build:`.
+**Gotcha:** If `image:` is present, Supervisor will **pull** from a registry.  
+For local dev builds, **comment out `image:`** in `config.yaml`.

@@
-## 6. Versioning & Publish/Deploy
-
-**In `addon/config.yaml`**
-```yaml
-version: "2025.8.21.3"
-image: "local/{arch}-addon-beep_boop_bb8"
-build:
-  dockerfile: Dockerfile
-  args:
-    BUILD_FROM: "ghcr.io/home-assistant/{arch}-base-debian:bookworm"
-```
+## 6. Versioning & Publish/Deploy
+
+**LOCAL_DEV (build locally):** `image:` **absent**, keep a valid `Dockerfile`.
+```yaml
+name: "HA-BB8"
+version: "2025.8.21.3"
+slug: "beep_boop_bb8"
+arch: ["aarch64"]
+init: false
+# image: ghcr.io/your-org/ha-bb8-{arch}   # ← commented out in LOCAL_DEV
+```
+
+**PUBLISH (pull from registry):** `image:` **present**; `version:` must equal the tag you pushed.
+```yaml
+name: "HA-BB8"
+version: "2025.8.21.3"                   # equals container tag
+slug: "beep_boop_bb8"
+arch: ["aarch64"]
+init: false
+image: "ghcr.io/your-org/ha-bb8-{arch}"
+```

@@
-**Minimal Dockerfile (Debian base)**
+**Minimal Dockerfile (base image via ARG)**
```dockerfile
-ARG BUILD_FROM=ghcr.io/home-assistant/aarch64-base-debian:bookworm
+ARG BUILD_FROM=ghcr.io/home-assistant/aarch64-base-debian:bookworm
 FROM ${BUILD_FROM}
@@
 CMD ["/bin/bash","-c","/usr/src/app/run.sh"]
```

@@
-### Issue: Supervisor tries to **pull** `local/…` image (404)
-**Detect:** `pull access denied for local/aarch64-addon-beep_boop_bb8`
-**Fix:** ensure `config.yaml` has `build:` and a present `Dockerfile`; then `ssh babylon-babes@homeassistant "ha addons reload" && rebuild`.
+### Issue: Supervisor tries to **pull** an image (404)
+**Detect:** `pull access denied ...`
+**Fix:** for LOCAL_DEV, **comment out `image:`** in `config.yaml` so Supervisor builds locally from `Dockerfile`; then `ssh babylon-babes@homeassistant "ha addons reload" && rebuild`.
```

---

## 2) Patch — `docs/PATHS_MAP.md`

```diff
--- a/docs/PATHS_MAP.md
+++ b/docs/PATHS_MAP.md
@@
-**S3. Buildability in place**  
-- `addon/config.yaml` **must** contain a `build:` block and `image: local/{arch}-addon-beep_boop_bb8`.  
-- `addon/Dockerfile` **must** exist and be valid.
+**S3. Build mode semantics (MUST)**  
+- **LOCAL_DEV:** `image:` is **absent** (commented). `addon/Dockerfile` **must** exist and be valid.  
+- **PUBLISH:** `image:` is **present** and `version:` **must** be set (semver-like) and aligned to the registry tag.

@@
-**Build context sanity (HA box)**
+**Build context sanity (HA box)**
@@
-**CRTP checks**
+**CRTP checks**
@@
-**Version sync check**
+**Mode detection & version checks**
 ```bash
-WS_VER=$(sed -n 's/^version:[[:space:]]*"?(.*)"*/1/p' "$ADDON_DIR/config.yaml" | head -1)
-RT_VER=$(sed -n 's/^version:[[:space:]]*"?(.*)"*/1/p' "$RUNTIME_MOUNT/config.yaml" | head -1 2>/dev/null || true)
-[ "$WS_VER" = "$RT_VER" ] && echo "TOKEN: VERSION_SYNC_OK:$WS_VER" || echo "DRIFT: version_mismatch ws=$WS_VER rt=$RT_VER"
+if rg -n '^s*image:s*' "$ADDON_DIR/config.yaml" >/dev/null; then
+  echo "MODE: PUBLISH"
+  rg -n '^s*version:s*' "$ADDON_DIR/config.yaml" >/dev/null || echo "DRIFT: version_missing_in_publish_mode"
+else
+  echo "MODE: LOCAL_DEV"
+  [ -f "$ADDON_DIR/Dockerfile" ] || echo "DRIFT: dockerfile_missing_in_local_dev"
+  echo "TOKEN: DEV_LOCAL_BUILD_FORCED"
+fi
+
+# Optional: version sync if runtime mount exists
+WS_VER=$(sed -n 's/^version:[[:space:]]*"?(.*)"*/1/p' "$ADDON_DIR/config.yaml" | head -1)
+RT_VER=$(sed -n 's/^version:[[:space:]]*"?(.*)"*/1/p' "$RUNTIME_MOUNT/config.yaml" | head -1 2>/dev/null || true)
+[ -n "$RT_VER" ] && { [ "$WS_VER" = "$RT_VER" ] && echo "TOKEN: VERSION_SYNC_OK:$WS_VER" || echo "DRIFT: version_mismatch ws=$WS_VER rt=$RT_VER"; }
```

---

## 3) Patch — `docs/ADR-0001-workspace-topology.md`

```diff
--- a/docs/ADR-0001-workspace-topology.md
+++ b/docs/ADR-0001-workspace-topology.md
@@
 ## Decision
 (dual-clone topology content …)
 
+## Build Mode Semantics (informative)
+Home Assistant Supervisor behavior:
+- **LOCAL_DEV**: If `image:` is **absent** in `addon/config.yaml`, Supervisor **builds locally** from the add-on `Dockerfile`.
+- **PUBLISH**: If `image:` is **present**, Supervisor **pulls** the specified image; ensure `version:` matches the tag published in the registry.
+This ADR treats both modes as valid; guards and checkers must detect the mode and validate accordingly.
```

*(No change needed to ADR-0004.)*

---

## 4) Patch — `.github/workflows/repo-guards.yml` (mode-aware)

```diff
--- a/.github/workflows/repo-guards.yml
+++ b/.github/workflows/repo-guards.yml
@@
-      - name: Structure guard (ADR-0001 + CRTP)
+      - name: Structure guard (ADR-0001 + CRTP + Mode)
         run: |
           set -euo pipefail
           test -d addon || (echo "addon/ missing" >&2; exit 2)
           if [ -d addon/.git ]; then echo "DRIFT: addon is a repo (forbidden)" >&2; exit 3; fi
@@
-          # Required build context files
-          test -f addon/config.yaml || (echo "DRIFT:missing_config_yaml" >&2; exit 5)
-          test -f addon/Dockerfile  || (echo "DRIFT:missing_Dockerfile" >&2; exit 6)
-          grep -qE '^s*build:' addon/config.yaml || (echo "DRIFT:config_yaml_missing_build_block" >&2; exit 7)
+          # Required files
+          test -f addon/config.yaml || (echo "DRIFT:missing_config_yaml" >&2; exit 5)
+
+          # Mode detection: LOCAL_DEV (no image) vs PUBLISH (image present)
+          if rg -n '^s*image:s*' addon/config.yaml >/dev/null; then
+            echo "MODE: PUBLISH"
+            rg -n '^s*version:s*' addon/config.yaml >/dev/null || (echo "DRIFT:version_missing_in_publish_mode" >&2; exit 7)
+          else
+            echo "MODE: LOCAL_DEV"
+            test -f addon/Dockerfile || (echo "DRIFT:dockerfile_missing_in_local_dev" >&2; exit 8)
+            echo "TOKEN: DEV_LOCAL_BUILD_FORCED"
+          fi
```

*(Leave the CRTP checks/tokens and tests steps as you already have them.)*

---

## 5) Patch — `ops/workspace/check_workspace_drift.sh` (mode-aware)

```diff
--- a/ops/workspace/check_workspace_drift.sh
+++ b/ops/workspace/check_workspace_drift.sh
@@
-# required build context files
-[ -f "$ADDON_DIR/config.yaml" ] || { STRUCT_OK=0; fail "missing_config_yaml"; }
-[ -f "$ADDON_DIR/Dockerfile"  ] || { STRUCT_OK=0; fail "missing_Dockerfile"; }
-grep -qE '^s*build:' "$ADDON_DIR/config.yaml" || { STRUCT_OK=0; fail "config_yaml_missing_build_block"; }
+# required files + mode detection
+[ -f "$ADDON_DIR/config.yaml" ] || { STRUCT_OK=0; fail "missing_config_yaml"; }
+if rg -n '^s*image:s*' "$ADDON_DIR/config.yaml" >/dev/null; then
+  echo "MODE: PUBLISH"
+  rg -n '^s*version:s*' "$ADDON_DIR/config.yaml" >/dev/null || { STRUCT_OK=0; fail "version_missing_in_publish_mode"; }
+else
+  echo "MODE: LOCAL_DEV"
+  [ -f "$ADDON_DIR/Dockerfile" ] || { STRUCT_OK=0; fail "dockerfile_missing_in_local_dev"; }
+  token "DEV_LOCAL_BUILD_FORCED"
+fi
```

---

## 6) Patch — `ops/workspace/validate_paths_and_contract.sh` (mode-aware)

```diff
--- a/ops/workspace/validate_paths_and_contract.sh
+++ b/ops/workspace/validate_paths_and_contract.sh
@@
-grep -qE '^s*build:' "$ADDON_DIR/config.yaml" || { say "DRIFT:config_yaml_missing_build_block"; DRIFT=1; }
-grep -qE '^s*image:s*"?local/{arch}-addon-beep_boop_bb8' "$ADDON_DIR/config.yaml" || { say "DRIFT:config_yaml_missing_local_image"; DRIFT=1; }
+# Mode detection: LOCAL_DEV (no image) vs PUBLISH (image present)
+if rg -n '^s*image:s*' "$ADDON_DIR/config.yaml" >/dev/null; then
+  say "MODE: PUBLISH"
+  rg -n '^s*version:s*' "$ADDON_DIR/config.yaml" >/dev/null || { say "DRIFT:version_missing_in_publish_mode"; DRIFT=1; }
+else
+  say "MODE: LOCAL_DEV"
+  [ -f "$ADDON_DIR/Dockerfile" ] || { say "DRIFT:dockerfile_missing_in_local_dev"; DRIFT=1; }
+  tok "DEV_LOCAL_BUILD_FORCED"
+fi
```

---

## 7) New helper — `ops/toggle_config_mode.sh` (optional)

```bash
#!/usr/bin/env bash
# Toggle addon/config.yaml between LOCAL_DEV (no image) and PUBLISH (image present).
set -euo pipefail
CFG="addon/config.yaml"
MODE="${1:-}"
if [ ! -f "$CFG" ]; then echo "missing $CFG"; exit 2; fi

if [ "$MODE" = "local" ]; then
  # comment out image
  sed -i.bak -E 's/^(s*)image:(.*)$/1# image:2/' "$CFG"
  echo "MODE: LOCAL_DEV → image commented"
elif [ "$MODE" = "publish" ]; then
  IMG="${2:-ghcr.io/your-org/ha-bb8-{arch}}"
  if rg -n '^s*image:s*' "$CFG" >/dev/null; then
    sed -i.bak -E "s#^(s*)#?image:.*#1image: "$IMG"#" "$CFG" || true
  else
    printf 'nimage: "%s"n' "$IMG" >> "$CFG"
  fi
  echo "MODE: PUBLISH → image set to $IMG"
else
  echo "usage: $0 <local|publish> [image]"
  exit 1
fi
```

---

## 8) Notes on base images (no change required)

Docs often show **Alpine** bases; you’re using HA’s **Debian** base (valid). Keep your Dockerfile’s `ARG BUILD_FROM` and `apt-get` usage consistent with Debian. (If you ever switch to Alpine, swap to `apk`.) ([developers.home-assistant.io][2])

---

## 9) Acceptance criteria (binary)

* **Docs:** Overview + PATHS_MAP updated to **mode-aware** behavior; ADR-0001 contains **Build Mode Semantics**.
* **CI & local guards:** No longer require `build:`; they **detect mode** and enforce LOCAL_DEV vs PUBLISH invariants; output `MODE:` + `TOKEN:` lines.
* **Helper present (optional):** `ops/toggle_config_mode.sh` allows deterministic flips without manual YAML edits.
* **No regressions:** CRTP logic, tokens, attestation, and evidence handling remain unchanged.

---

[1]: https://developers.home-assistant.io/docs/add-ons/testing?utm_source=chatgpt.com "Local add-on testing"
[2]: https://developers.home-assistant.io/docs/add-ons/configuration/?utm_source=chatgpt.com "Add-on configuration"
