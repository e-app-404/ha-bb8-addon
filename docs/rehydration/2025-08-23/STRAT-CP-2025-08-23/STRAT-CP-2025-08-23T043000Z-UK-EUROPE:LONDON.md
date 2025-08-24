# 🔗 SESSION ANCHOR — STRATEGOS

* **Anchor ID:** `STRAT-CP-2025-08-23T04:30:00Z-UK-EUROPE/LONDON`
* **Handoff Tag:** `HANDOFF/STRATEGOS_CONTINUITY_V1`
* **Scope:** HA-BB8 workspace ↔ add-on subtree (ha-bb8-addon) delivery + SSH deploy via LLAT

---

# 1) 🔖 Session Recap Summary (YAML)

```yaml
session:
  label: "HA-BB8 — Canonicalization, Subtree Publish, SSH Deploy"
  trace_id: "ha-bb8/023710d→runtime - ws:fix/stray-roots@da7c944"
personas:
  primary:
    id: "Strategos"
    role: "Executive Project Strategist & Integration Delivery Manager"
  operators:
    - "User: evertappels"
operational_context:
  mode: "governance + delivery"
  escalation: "intervention-mode when structural violations detected"
last_validated_checkpoint:
  runtime_head: "023710d (addon repo: Topology cleanup, PR #4)"
  deploy_tokens:
    - "SSH_HA_OK"
    - "DEPLOY_OK — runtime hard-reset to origin/main"
    - "VERIFY_OK — add-on restarted via Services API"
    - "DEPLOY_SSH_OK"
governance_traits_effective:
  binary_acceptance: true
  empirical_validation: true
  guardrails:
    - "ADR-0001 structure gate (workspace + addon)"
    - "pre-push hook (block structural violations)"
    - "publish is subtree-only; deploy over SSH via LLAT"
summary_unresolved_blockers:
  - id: "WS-MISSING-CONTENT"
    desc: "docs/, ops/, scripts/ largely missing vs earlier state; only minimal ops/release scripts present"
    status: "open"
  - id: "LEGACY-BACKUPS"
    desc: "Historic _backup/*.tar.gz mostly absent; only recent dedupe tgz present under _backups/"
    status: "open"
strategic_posture:
  intent: "rehydrate workspace artifacts, preserve delivery pipeline, maintain ADR compliance"
  next_focus: "recover docs/ops/scripts and historical tarballs, then lock guards against destructive cleans"
```

---

# 2) 📦 Artifact Reference Index

```yaml
artifacts:
  - name: "system_instruction.yaml"
    path: "/mnt/data/system_instruction.yaml"
    type: "yaml"
    role: "governance-core"
  - name: "20250813_strategos_v1.4.yaml"
    path: "/mnt/data/20250813_strategos_v1.4.yaml"
    type: "yaml"
    role: "persona-manifest"
  - name: "20250803_xp_strategos_v1.6.yaml"
    path: "/mnt/data/20250803_xp_strategos_v1.6.yaml"
    type: "yaml"
    role: "enhancement-pack"
  - name: "dual_mode_xp_v1_250813.yaml"
    path: "/mnt/data/dual_mode_xp_v1_250813.yaml"
    type: "yaml"
    role: "delivery-xp"
  - name: "rehydration_seed_20250819_032616Z.yaml"
    path: "/mnt/data/rehydration_seed_20250819_032616Z.yaml"
    type: "yaml"
    role: "seed/previous"
  - name: "bb8_build.json"
    path: "/data/addons/data/local_beep_boop_bb8/bb8_build.json"
    type: "json"
    role: "runtime-build-stamp"
  - name: "workspace backups (current)"
    path: "_backups/stray_app_*.tgz, _backups/stray_bb8_core_*.tgz"
    type: "tar.gz"
    role: "safety-snapshots"
  - name: "LLAT secret key"
    path: "/config/secrets.yaml key: ha_llat"
    type: "yaml:kv"
    role: "HTTP Services API auth"
  - name: "deploy_ha_over_ssh.sh"
    path: "ops/release/deploy_ha_over_ssh.sh"
    type: "bash"
    role: "runtime-deploy"
    status: "present"
  - name: "publish_and_deploy.sh"
    path: "ops/release/publish_and_deploy.sh"
    type: "bash"
    role: "subtree-publish + deploy"
    status: "present"
  - name: "ADR-0001"
    path: "docs/ADR/ADR-0001-workspace-topology.md"
    type: "md"
    role: "canonical-structure"
    status: "missing_in_ws (to restore)"
  - name: "add-on config"
    path: "addon/config.yaml"
    type: "yaml"
    role: "addon-definition"
  - name: "VERSION"
    path: "addon/VERSION"
    type: "text"
    role: "release-version"
commit_refs:
  addon_repo_current_head: "023710d (runtime)"
  ws_feature_branch: "fix/stray-roots@da7c944 (ahead of origin/main by 1 at time of diff)"
```

---

# 3) 🗺️ Phase + Output Registry

```yaml
phases:
  - id: P1
    label: "Backup normalization & topology gate"
    outputs: ["STRUCTURE_OK — backups normalized", "STRUCTURE_OK — topology", "WS_READY"]
    status: "completed"
  - id: P2
    label: "GitHub auth + runtime fetch"
    outputs: ["AUTH_OK:HTTPS", "DEPLOY_OK — runtime hard-reset to origin/main", "VERIFY_OK — running"]
    status: "completed"
  - id: P3
    label: "ADR enforcement & symlink/submodule purge"
    outputs: ["HOOKS_OK — pre-push installed", "ADR addenda applied", "CLEAN_RUNTIME_OK"]
    status: "completed"
  - id: P4
    label: "Subtree pivot to standalone addon repo"
    outputs: ["SUBTREE_PUBLISH_OK:main@<sha>", "RUNTIME_TOPOLOGY_OK"]
    status: "completed"
  - id: P5
    label: "SSH deploy over LLAT"
    outputs: ["SSH_HA_OK", "VERIFY_OK — add-on restarted via Services API", "DEPLOY_SSH_OK"]
    status: "completed"
  - id: P6
    label: "Dev env & test imports"
    outputs: ["VENV_OK", "RUNTIME_DEPS_OK", "DEV_DEPS_OK", "PAHO_PIN_OK", "PAHO_CODE_PATCH_OK", "TESTS_IMPORTS_OK", "MQTT_PATCH_COMMITTED"]
    status: "completed"
  - id: P7
    label: "Workspace normalization (prune stray roots)"
    outputs: ["WS_PUSH_OK:fix/stray-roots", "PR #4 merged in addon repo (topology)"]
    status: "completed"
  - id: P8
    label: "Content loss incident (docs/ops/scripts)"
    outputs: ["WS-MISSING-CONTENT", "LEGACY-BACKUPS low visibility"]
    status: "escalated"
pending_copilot_actions:
  - "Recover docs/, ops/, scripts/ from git history and working-tree snapshots"
  - "Restore legacy _backup tarballs into _backups/"
  - "Reinforce hooks to block destructive cleans by default"
```

---

# 4) 🧠 Memory Variables for Rehydration

```yaml
rehydration_memory:
  last_valid_patch: "deploy_ha_over_ssh.sh LLAT fix + successful restart (VERIFY_OK)"
  last_decision_checkpoint: "Subtree publish (no-op tolerant) + SSH deploy path locked"
  clustered_entities:
    count: 11
    aliases:
      - addon_slug: "local_beep_boop_bb8"
      - runtime_path: "/addons/local/beep_boop_bb8"
      - ws_root: "HA-BB8/"
      - subtree_repo: "e-app-404/ha-bb8-addon"
      - services_api: "/api/services/hassio/addon_restart"
      - llat_key: "ha_llat"
      - backups_dir: "_backups/"
      - adr_file: "docs/ADR/ADR-0001-workspace-topology.md"
      - publish_remote: "addon-publish"
      - ws_branch: "fix/stray-roots"
      - runtime_build_stamp: "/data/addons/data/<slug>/bb8_build.json"
  inclusion_coverage: "pipeline (publish→deploy), ADR guards, dev env, SSH auth, LLAT handling"
  semantic_summary: >
    Workspace was canonicalized to addon/ as single source of runtime packaging.
    Publishing occurs via git subtree split; deploy uses SSH + LLAT with HA Services API.
    ADR guardrails are active. A content loss incident requires restoration of docs/ops/scripts & old backups.
  open_validation_loops:
    - id: "RESTORE_DOCS_OPS_SCRIPTS"
      need: "Restore full content; confirm with WS_READY + inventory diff"
    - id: "RESTORE_LEGACY_BACKUPS"
      need: "Recover _backup/*.tar.gz into _backups/ and commit index"
```

---

# 5) 🔐 Rehydration Seed — Export Prompt (YAML)

> Paste this block into your next Strategos boot to instantly pick up context.

```yaml
# Rehydration Seed — Strategos Continuity
boot:
  session_anchor: "STRAT-CP-2025-08-23T04:30:00Z-UK"
  roles:
    - id: Strategos
      mode: governance+delivery
  governance:
    binary_acceptance: true
    empirical_validation: true
    acceptance_tokens:
      - WS_READY
      - STRUCTURE_OK
      - CLEAN_RUNTIME_OK
      - SUBTREE_PUBLISH_OK
      - DEPLOY_OK
      - VERIFY_OK
      - DEPLOY_SSH_OK
      - GOVERNANCE_STATE_OK
  topology:
    workspace_root: "HA-BB8/"
    addon_subtree: "addon/"
    runtime_path: "/addons/local/beep_boop_bb8"
    addon_slug: "local_beep_boop_bb8"
  auth:
    llat:
      source_file: "/config/secrets.yaml"
      key: "ha_llat"
    github:
      remote_addon: "https://github.com/e-app-404/ha-bb8-addon.git"
  recovery:
    restore_targets:
      - "docs/"
      - "ops/"
      - "scripts/"
      - "_backups/"
    history_refs:
      - "git rev-list --all -- docs ops scripts _backup"
  outputs_pointers:
    runtime_build_stamp: "/data/addons/data/local_beep_boop_bb8/bb8_build.json"
    deploy_script: "ops/release/deploy_ha_over_ssh.sh"
    publisher_script: "ops/release/publish_and_deploy.sh"
  next_steps:
    - "Recover artifacts from history/snapshots; confirm WS_READY"
    - "Run publish_and_deploy; verify VERIFY_OK"
```

---

# 6) 📄 Final Advisory

**Token advisory**

* Keep responses compact; reuse acceptance tokens (`WS_READY`, `SUBTREE_PUBLISH_OK`, `DEPLOY_OK`, `VERIFY_OK`) to assert progress without verbose logs.
* Prefer structured YAML or short command blocks for Copilot.

**Recommended next GPT startup config**

* Persona: **Strategos**
* Mode: **governance+delivery**
* Load: `system_instruction.yaml`, `20250813_strategos_v1.4.yaml`, `20250803_xp_strategos_v1.6.yaml`, `dual_mode_xp_v1_250813.yaml`
* Seed: *paste the “Rehydration Seed — Strategos Continuity” block above.*

**Assumptions / risks**

* `docs/`, `ops/`, `scripts/` content exists in Git history or local snapshots; if not, manual re-provisioning may be required.
* `_backup` tarballs may require recovery from other machines/cloud if missing from history.

**Guardrails to enforce**

* Block `git clean -fdX` unless `ALLOW_CLEAN=1`.
* Pre-push hook: deny pushes that delete `docs/`, `ops/`, `scripts/` without `FORCE_DOCS_DEL=1`.
* ADR-0001 CI gate remains mandatory.

**/beep\_boop\_bb8/ops/\_guidelines.md (content)**

```md
# BB-8 Delivery & Patch Etiquette (Strategos)

## Golden Rules
1. **Single source of packaging:** All runtime packaging comes from `addon/`.
2. **Publish is subtree-only:** Use `publish_and_deploy.sh`; never push add-on content from workspace root directly.
3. **Deploy via SSH + LLAT:** `deploy_ha_over_ssh.sh` restarts with HA Services API using `/config/secrets.yaml: ha_llat`.

## Do / Don’t
- ✅ Do commit `docs/`, `ops/`, `scripts/` (parents tracked).  
- ✅ Do ignore only artifacts (`_backups/*.tar.gz`, caches, `.DS_Store`).  
- ❌ Don’t run `git clean -fdX` without `ALLOW_CLEAN=1`.  
- ❌ Don’t delete `docs/`, `ops/`, `scripts/` on main—guarded by hook.

## Standard Flow
1. Edit code/docs.  
2. `make dev` (lint/typecheck/tests).  
3. Commit → `publish_and_deploy.sh` (handles subtree push, SSH deploy, restart).  
4. Expect: `SUBTREE_PUBLISH_OK → DEPLOY_OK → VERIFY_OK → DEPLOY_SSH_OK`.

## Incident Recovery (quick)
- `git rev-list -n 1 --all -- docs ops scripts` → `git checkout <sha> -- <path>`  
- Check snapshots: `_backups/wtree_*.tgz`  
- Push salvage branch: `salvage/restore-<ts>` → PR to `main`.

## Acceptance Tokens
- `WS_READY`, `STRUCTURE_OK`, `SUBTREE_PUBLISH_OK`, `DEPLOY_OK`, `VERIFY_OK`, `DEPLOY_SSH_OK`.
```

---

## ✅ Handoff Tag

`HANDOFF/STRATEGOS_CONTINUITY_V1 — READY`
