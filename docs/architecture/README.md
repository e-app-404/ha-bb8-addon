Workspace architecture and indexing README

This folder contains generated and authored artifacts that document the repository
and provide compact machine-readable indices for LLM-assisted workflows.

Key artifacts
- `workspace_inventory.jsonl` 3 global seed list of high-signal files
- `index.jsonl` (per-folder) 3 contains file-level metadata (path, sha256, category, language, tags, generated, meta)
- `relationships.json` 3 mapping of python modules to imports, producers, and consumers (MQTT topics)
- `reports/relationship_graph.dot` 3 DOT visualization of module import and topic edges

Notes and metadata
- `index.jsonl` entries now include a `meta` object for manifest-derived hints (project_name, author) and may include `binary=true` for files that are images/binaries to avoid LLM reading.
- `relationships.json` includes `producers` and `consumers` arrays per module; producers are modules that publish topics, consumers subscribe or react to topics.

How to regenerate

```bash
python3 ops/guardrails/generate_index.py
python3 ops/guardrails/build_relationships.py
```

CI integration

See `.github/workflows/regenerate_indexes.yml` for an example workflow that runs the generators and fails if the committed artifacts are out-of-date.

If you prefer the indexes to be generated in CI but not committed, adjust the workflow to attach the generated artifacts instead of failing on diffs. Committing indexes improves reproducibility for model seeding.

Contact: ops/guardrails team

---

Workspace organization recommendations

1) Folder mapping and responsibilities
- `addon/` — runtime add-on code (bb8_core and related modules). Treat as production runtime.
	- Ownership: runtime maintainers; add `CODEOWNERS`/`OWNERS` for `addon/`.
	- Policy: ADR checks required for changes affecting discovery or MQTT topics.
- `ops/` — tooling, guardrails, ratchets, and deployment scripts. These are repo-maintenance tools.
	- Ownership: ops team; run in CI.
- `docs/` (including `docs/architecture/`) — canonical documentation and machine-readable indices.
	- Ownership: docs/architecture maintainers; commit indexes for reproducibility or make CI the source of truth and upload artifacts.
- `reports/` — generated artifacts (coverage, DOT graphs). Prefer CI-only or commit only curated historical reports.
- `_backups/` and `_bundles/` — archived backups and bundles. Do not store new runtime caches at repo root.

2) Naming and file placement conventions
- Keep runtime code in `addon/` with clear module boundaries; tests may live alongside modules or under `tests/`.
- Topic constants: centralize MQTT topic templates as `CMD_TOPICS`, `STATE_TOPICS`, or `TOPIC_BASE` to help static analysis and ownership mapping.
- Manifests at repo root (`pyproject.toml`, `package.json`) should be parsed to populate `meta.project_name` and `meta.author`.

3) Ownership and discoverability
- Add `CODEOWNERS` or `OWNERS` entries for top-level folders to route reviews and automate assignment:
	- `addon/ @team/runtime`
	- `ops/ @team/ops`
	- `docs/ @team/docs`
- Encourage README.md in subfolders describing purpose and owner; run the indexer to capture those docs as high-signal entries.

4) CI and governance (practical)
- Decide on index policy:
	- Option A (recommended): commit `index.jsonl` files and enforce freshness in CI via a regenerate-and-diff step. This improves reproducibility for LLM seeding and offline workflows.
	- Option B: keep indexes generated-only in CI and upload artifacts on each run. This reduces repository churn but requires reliable CI.
- The provided workflow `.github/workflows/regenerate_indexes.yml` sketches the regenerate-and-diff approach.

5) Short prioritized action plan
- High: Parse manifests with `tomllib`/`json` to fill `meta` reliably and rerun generator (improves coverage quickly).
- High: Add an unannotated-files report to identify remaining blind spots and prioritize heuristic extension.
- Medium: Implement AST-based detection of `.publish` / `.subscribe` calls to reduce MQTT topic misses.
- Medium: Add `CODEOWNERS` and update PR templates to require owner review for critical folders.

6) Operational recipes (quick how-to)
- Adding a new MQTT topic: put topic constants in the producing module, run `python3 ops/guardrails/build_relationships.py`, verify `docs/architecture/relationships.json`, and document ownership.
- Adding a new component/folder: create a short `README.md` in the folder describing purpose and owner, run the indexer, and ensure it appears in `workspace_inventory.jsonl`.

7) Governance rules to codify (recommend adding to ADRs or docs)
- Any change to public discovery payloads or canonical MQTT topic names must include an ADR check and update `docs/architecture/relationships.json`.
- Do not commit runtime caches or generated ephemeral artifacts to repository root (use `_backups/` or ignore via `.gitignore`).

Contact and next steps
- If you'd like, I can implement the high-priority items now (manifest parsing, unannotated report) and update indexes and the README accordingly.

