You are Copilot operating quiet and repo-only. Find BB-8 workspace artifacts **in this repository** (no SSH, no network, no HA host). Produce a deterministic manifest and a ≤10-line receipt.

## TARGET ARTIFACT BASENAMES (search repo-wide)
- addon_20251009T105938Z.tar.gz
- BB8-FUNC-B2-artifacts.tar.gz
- BB8-BLE-TEST.tar.gz
- ha_ble_diag_hci0_20251009T131211Z.tar.gz
- architecture.tar.gz
- ADR.tar.gz
- config.tar.gz
- prompt_registry.tar.gz
- 20250813_strategos_v1.4.yaml
- 20250803_xp_strategos_v1.6.yaml
- dual_mode_xp_v1_250813.yaml
- system_instruction.yaml

## DO EXACTLY (repo-only; quiet)
1) Search the repo (exclude: .git, .venv, node_modules, dist, build, htmlcov, reports/checkpoints/**):
   - For each basename above, locate the *single best* match if present; prefer under `reports/artifacts/` if multiple.
2) For every found file, compute metadata:
   - `repo_path` (POSIX), `size_bytes`, `mtime_iso`, `sha256` (use `shasum -a 256` or a short Python one-liner).
3) Write JSON manifest at:
   - `reports/artifacts/workspace_artifacts_manifest.json`
   - Shape:
   ```json
   {
     "resolution_policy": { "order": ["repo"], "on_missing": "request_reupload", "verify_checksums": true },
     "items": [
       { "id": "addon-snapshot-20251009", "basename": "addon_20251009T105938Z.tar.gz", "repo_path": "<path-or-null>", "size_bytes": <int-or-null>, "mtime_iso": "<iso-or-null>", "sha256": "<hex-or-null>", "found": <true|false> },
       { "id": "b2-artifacts", "basename": "BB8-FUNC-B2-artifacts.tar.gz", ... },
       { "id": "ble-diagnostics-hci0", "basename": "ha_ble_diag_hci0_20251009T131211Z.tar.gz", ... },
       { "id": "adr-bundle", "basename": "ADR.tar.gz", ... },
       { "id": "system-protocols", "basename": "system_instruction.yaml", ... },
       { "id": "architecture-bundle", "basename": "architecture.tar.gz", ... },
       { "id": "config-bundle", "basename": "config.tar.gz", ... },
       { "id": "prompt-registry", "basename": "prompt_registry.tar.gz", ... },
       { "id": "persona-core", "basename": "20250813_strategos_v1.4.yaml", ... },
       { "id": "persona-xp", "basename": "20250803_xp_strategos_v1.6.yaml", ... },
       { "id": "dual-mode-xp", "basename": "dual_mode_xp_v1_250813.yaml", ... },
       { "id": "bb8-ble-test", "basename": "BB8-BLE-TEST.tar.gz", ... }
     ]
   }
