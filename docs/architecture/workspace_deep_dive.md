## Workspace deep dive — HA-BB8

This document summarizes the project's content model, file/folder taxonomy, relationships, and provides a machine-optimized prompt for Github Copilot (GPT-5 mini) to enable workspace architecture intelligence.

Goals
- Map where information is stored and why.
- Provide a pragmatic, machine-friendly taxonomy for indexing, search, and automated guardrails.
- Offer a compact prompt template for Copilot-style agents.

High-level categories
- Code (runtime): `addon/bb8_core/` — the add-on runtime logic (BLE, MQTT dispatcher, discovery, controllers).
- Add-on packaging: `addon/config.yaml`, `addon/Makefile`, `Dockerfile`, and add-on metadata used by Home Assistant Supervisor.
- Ops & Automation: `ops/` — scripts for evidence, ratchet, release, guardrails, and maintenance tools.
- Governance & ADRs: `docs/ADR/` — architectural decisions, tokens, and policy.
- Tests & CI: `addon/tests/`, `ops/guardrails/tests/`, `.github/workflows/`.
- Evidence & Reports: `reports/`, `docs/rehydration/`, `ops/evidence/` — artifacts, logs, and evidence bundles.
- Backups & Bundles: `_backups/`, `_bundles/` — archived snapshots and recovery artifacts.
- Configuration & Tooling: `pyproject.toml`, `.coveragerc`, `Makefile`, `requirements.txt`, `.github/`.

Inventory (machine-friendly JSONL)
- See `workspace_inventory.jsonl` for a line-delimited JSON map of files and metadata (path, category, tags, size-estimate, authoritative-flag, generated-flag, consumers).

Relationships and patterns (concise)
- `addon/bb8_core/*` produces runtime behaviors consumed by HA via MQTT discovery and by `run.sh` entrypoint. Primary consumers: Home Assistant Supervisor (container runtime), local `run.sh` and `bridge_controller.py`.
- `ops/ratchet/*` mutates `.coveragerc` and runs tests to enforce the coverage gate. The ratchet writes to `.coveragerc` and `coverage.xml` and may commit changes.
- `ops/guardrails/*` contain validators run by CI and pre-commit hooks. They consume repo sources and ADRs, and emit tokens/reports under `reports/`.
- `docs/ADR/*` contains governance tokens and drives enforcement logic inside guardrails; tokens used by `ops/guardrails/*` and CI workflows.
- `reports/` houses outputs consumed by human reviewers and some guard scripts (evidence-based checks).

Machine-optimized taxonomy (short)
- category: code.runtime — python modules under `addon/bb8_core`.
- category: code.tooling — scripts in `ops/`, `scripts/`, and `addon/tools/` used for build/test/release.
- category: infra.metadata — `pyproject.toml`, `config.yaml`, `addon/config.yaml`, `.coveragerc`, `Makefile`.
- category: governance — `docs/ADR/`, `ops/guardrails/` and `docs/rehydration`.
- category: artifacts — `reports/`, `_backups/`, `_bundles/`, `htmlcov/`.
- category: tests — `addon/tests/`, `ops/guardrails/tests/`, pytest configs.
- category: ci — `.github/workflows/*` and task runner files.
- category: docs — files under `docs/` that are tutorial/operational.

GPT-5-mini prompt template (for Copilot indexing + reasoning)

Prompt intent: Provide the model with a structured context and ask for architecture-aware operations (search, classify, refactor suggestions, guardrail synthesis).

Template (inject workspace metadata JSONL lines as 'SEED_FILES' up to token budget):

```
You are given a project workspace with files described by JSON objects (one per line) in SEED_FILES.
Each object has: path, category, tags, authoritative (true|false), generated (true|false), consumers (list of paths), producers (list of paths), brief (short text summary).

Task: Based on SEED_FILES, produce:
1) A normalized content taxonomy mapping categories -> canonical folders and recommended index keys.
2) For each category, list 3 automated agents or guardrails the repo should run (e.g., discovery validator, coverage ratchet, import enforcer), and the minimal input/output artifacts for each agent.
3) A minimal schema (JSON) for 'file metadata' to be used by workspace/indexer: fields, types, example.
4) A prioritized 5-step migration plan (low risk first) to restructure the repo for machine-optimized navigation and guardrails.

Constraints:
- Preserve ADR-driven governance; do not suggest incompatible changes to ADRs without explicit mapping.
- Prefer non-invasive steps (add index files, canonical metadata) before moving large folders.

Output format: JSON object with keys: taxonomy, agents, metadata_schema, migration_plan.

SEED_FILES:
<PASTE SEED JSONL LINES HERE>
```

How to use these artifacts
- Feed `workspace_inventory.jsonl` as SEED_FILES into Copilot/GPT-5-mini; it will produce a compact plan and machine schema for indexing.
- Add the resulting metadata schema as a file `docs/architecture/file_metadata_schema.json` and generate small per-folder `index.jsonl` files for fast runtime queries.

Appendix: Quick wins
- Add per-folder `index.jsonl` containing file metadata (path, sha256, category, tags). This enables O(1) topical search and fast Copilot seeding.
- Add `ops/guardrails/generate_index.py` to emit `docs/architecture/workspace_inventory.jsonl` regularly (pre-commit or CI job).
- Wire Copilot to use the index as 'context window' for code health suggestions and ADR-aligned refactors.

--- end

