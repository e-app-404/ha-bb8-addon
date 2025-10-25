---
id: "DOC-STYLE-001"
title: "Document style and canonical frontmatter for hestia/workspace/operations/guides/ha_implementation"
authors:
    - "e-app-404"
slug: "doc-style"
date: "2025-10-24"
last_updated: "2025-10-24"
content_type: "style guide"
description: "Document style and canonical frontmatter for hestia/workspace/operations/guides/ha_implementation"
tags: ["documentation", "style guide", "frontmatter", "hestia", "ha_implementation"]
status: "published"
---

# Document style and canonical frontmatter for HA BB-8 Docs

This file provides an updated, workspace-aware YAML frontmatter template and concise Markdown style guide for files in `/config/hestia/library/ha_implementation` and related `ops/docs` folders. The template reflects repository structures used by HA‑BB8 (`addon/`, `reports/`, `docs/`, `ops/`) and enforces evidence and ADR hygiene.

## 1. Markdown Style Guide

### Canonical frontmatter (use this exact schema; adjust values)

Place this YAML block at the top of each document. Use valid YAML types (strings, lists, maps). Do not duplicate keys.

```yaml
---
id: "CAT-TOPIC-YYYYMMDD-NNN"        # unique id (recommended pattern)
title: "Short descriptive title"
authors:
    - "Author Name or Org"
source: "Upstream source or notes (optional)"
slug: "short-slug"                 # derived from filename where possible
version: "1.0"                     # semantic string
content_type: "manual|guide|implementation|template|reference|tutorial"
description: "Brief summary of document purpose and scope"
tags: ["keyword1", "keyword2", "keyword3", ...]
status: "draft|candidate|published|deprecated|archived|under review|to-do|flagged for review|active|completed"
date: "YYYY-MM-DD"                 # creation date (ISO date)
last_updated: "YYYY-MM-DD"         # last edited date (ISO date)
url: "https://original/upstream/url (optional)"
related:
    - "related-slug-1"
    - "related-slug-2"
adr:
    - "ADR-XXXX"
category: "category-name (optional)"
file: "/absolute/path/if/applicable (optional)"
entrypoint: "path/to/main/script (optional)"
installation: "path/to/install/location (optional)"
logs: "path/to/logs (optional)"
manifest_sha256: "manifest.sha256 filename or sha256sum (required for evidence dirs)"
evidence_path: "/config/ha-bb8/checkpoints/BB8-FUNC/<UTC_TS>/ (for evidence artifacts)"
runtime_model: "foreground|service|container (if applicable)"
service_list: []                   # keep empty array when none
device_identifiers:
    mac: "ED:ED:87:D7:27:50"         # if device/file-specific
    name: "BB-8 (S33...)"            # optional device metadata
base_topic: "bb8"                  # mqtt base topic if document describes MQTT behavior
---
```

Required keys (all documents): `id`, `title`, `authors`, `slug`, `date`, `last_updated`, `content_type`.
Additional required for evidence runs: `manifest_sha256`, `evidence_path`.
Do not repeat keys (the original template duplicated "version").

### Minimal Markdown style guide (workspace updates)

- **Encoding & line endings:** UTF-8, LF.
- **Headings:** Single H1 (`# Title`) only. Use H2/H3 for sections. Avoid multiple H1s.
- **Frontmatter:** Must be the very first content block in the file. Use the canonical schema above.
- **Dates & timestamps:**
    - Use ISO-8601 date: `YYYY-MM-DD` for `date`/`last_updated`.
    - For logs/evidence use RFC3339 / ISO-8601 with ms and timezone (e.g., `2025-10-24T14:05:03.123Z`).
- **Code blocks:** Fenced with language tag (e.g., `yaml`, `bash`, `json`). Preserve indentation inside fences.
- **YAML examples:** Wrap in `yaml` and ensure snippets are valid YAML (lint before commit).
- **Lists:** Use "- " for bullets. Keep a single blank line between paragraphs and lists.
- **Tags:** Represent as a YAML sequence (list), not a quoted, comma-separated string.
- **Images/links:** Use standard Markdown. Avoid raw HTML unless strictly necessary.
- **Admonitions:** Use blockquotes for simple notes:
    > **Note:** ...
    For richer admonitions, be consistent across repo.
- **Evidence & artifact rules:**
    - All governed evidence/witness artifacts must be written under `reports/checkpoints/BB8-FUNC/` or `/config/ha-bb8/checkpoints/BB8-FUNC/<UTC_TS>/` depending on run context.
    - Include `manifest_sha256` in frontmatter for evidence directories and provide a `manifest.sha256` file listing file names and checksums.
    - Timeline/log entries must use ISO-8601 ms timestamps and include topic/payload for MQTT evidence.
- **Sensitive data:** Never include secrets. Mask values like `MQTT_PASSWORD`, `HA_TOKEN`, `API_KEY` as `[MASKED]` if needed for examples.
- **File paths:** Use repository-relative paths in docs (e.g., `addon/scripts/b5_e2e_run.py`) and absolute HA Host paths only when describing host runtime rules.
- **Lint policy:** Run a markdown linter before committing. CI will enforce frontmatter presence for files in `ops/` and `reports/`.

## Linting & automation (examples)

Run linters locally; CI will run the same checks.

```bash
# remark-based lint
npm install -D remark-cli remark-frontmatter
npx remark . --frail

# markdownlint
npm install -D markdownlint-cli
npx markdownlint '**/*.md'
```

### Suggested automation

- **Pre-commit hook:** validate frontmatter keys and date format, ensure tags is a list.
- Small helper script (recommended) to:
    - Insert canonical frontmatter if missing.
    - Update `last_updated` to today when committing.
    - Derive slug from filename (kebab-case).
    - Ensure evidence docs include `manifest_sha256` and `evidence_path`.

## Applying frontmatter programmatically (recommended patterns)

- Use a small, **idempotent script** (Python or Node) that:
    - Reads existing frontmatter, merges missing keys with defaults.
    - Validates types (`tags` → list, `authors` → list).
    - Ensures unique id using pattern `CAT-TOPIC-YYYYMMDD-NNN`.
    - Updates `last_updated` to current date when changes are committed.
    - Refuses to write evidence files outside `reports/checkpoints/**` or `/config/ha-bb8/**`.
- When creating evidence runs, require `manifest.sha256` generation and include it in `frontmatter.manifest_sha256`.

## 2. TOML Style Guide

For TOML files in the repository (e.g., `addon/config.toml`), follow these conventions:

### TOML Style Guide (BB‑8 / HA‑BB8 repo)

**Purpose:** Formalize conventions when authoring repository TOML files (e.g., `docs/ops/BB8.toml`) so they map cleanly to the canonical YAML frontmatter and evidence rules used across the workspace.

**Principles**
- Canonical mapping: TOML keys must map 1:1 to frontmatter keys where applicable (`id`, `title`, `authors`, `slug`, `date`, `last_updated`, `content_type`, `description`, `tags`, `manifest_sha256`, `evidence_path`, `base_topic`, `device_identifiers`, `runtime_model`, `service_list`).
- Explicit types: prefer native TOML types (string, datetime, array, table) instead of stringified values for easier validation.
- Deterministic ordering: group keys by semantic section (metadata, evidence, runtime, device, mqtt) and keep consistent ordering for diff stability.

**Naming & Style**
- Keys: use snake_case (lowercase, underscores). Example: `manifest_sha256`, `evidence_path`, `last_updated`.
- Tables: use dotted table names for logical grouping:
    - `[device_identifiers]`
    - `[evidence]`
    - `[runtime]`
    - `[mqtt]`
- Arrays: use TOML arrays for lists (`authors = ["A", "B"]`, `tags = ["x","y"]`).
- Dates: use RFC 3339 / ISO 8601 datetimes for timestamp fields (T in value). Use date-only (`YYYY-MM-DD`) for `date`/`last_updated` where time not required. Use full datetime for log/evidence timestamps.
- Comments: use `#` for short notes; avoid long inline commentary inside production TOML files.

**Required keys & types (per document)**
- `id`: string (pattern `CAT-TOPIC-YYYYMMDD-NNN`)
- `title`: string
- `authors`: array of strings
- `slug`: string
- `date`: date (`YYYY-MM-DD`) or datetime
- `last_updated`: date (`YYYY-MM-DD`)
- `content_type`: string (`manual|guide|implementation|template|reference|tutorial`)
- `description`: string

**Evidence-run additional required keys**
- `manifest_sha256`: string (filename or sha256sum)
- `evidence_path`: string (absolute path under `/config/ha-bb8/checkpoints/BB8-FUNC/<UTC_TS>/`)
- Ensure these appear under an `[evidence]` table when present.

**Recommended structured tables**
```toml
# metadata
id = "CAT-BB8-20251024-001"
title = "BB8 E2E Evidence Run Instructions"
slug = "bb8-e2e-run"
authors = ["e-app-404"]
date = 2025-10-24
last_updated = 2025-10-24
content_type = "guide"
description = "E2E run and evidence capture conventions for BB‑8 add-on"
tags = ["evidence","b5","bb8","mqtt"]

# mqtt/runtime/device grouping
[mqtt]
base_topic = "bb8"
broker_host = "core-mosquitto"

[runtime]
runtime_model = "foreground"
service_list = []

[device_identifiers]
mac = "ED:ED:87:D7:27:50"
name = "BB-8 (S33 BB84 LE)"
identifiers = ["bb8_S33_BB84_LE"]

[evidence]
manifest_sha256 = "manifest.sha256"
evidence_path = "/config/ha-bb8/checkpoints/BB8-FUNC/2025-10-24T14:05:03Z/"
```

### CI / Tooling recommendations

- **Lint:** add toml-lint in pre-commit and CI pipelines.
- **Schema validation:** implement a small schema validator (Python/JSON Schema or custom) that:
    - Confirms required keys and types,
    - Verifies `evidence_path` is under allowed roots,
    - Validates MAC format and date formats,
    - Fails the build on violations.
- **Sorting:** use toml-sort or a canonical serializer to normalize file ordering for diffs.
- **Auto-insert helpers:** provide a script to populate minimal required keys when generating TOML from templates.

### Mapping to YAML frontmatter

- TOML tables → nested YAML maps
- Simple keys → top-level frontmatter keys
- Arrays → YAML sequences
- Keep `manifest_sha256` and `evidence_path` present for evidence docs to satisfy repo gate logic.

### Examples of common validation failures to catch

- `tags` as a comma string: `tags = "a,b,c"`  → reject
- `manifest_sha256` missing for an evidence doc → reject
- `evidence_path` outside `/config/ha-bb8` or `reports/checkpoints` → reject
- `device_identifiers.mac` in lowercase or missing colons → reject

**Minimal enforcement checklist (pre-commit):**
- Required keys present
- Types correct (string/array/date/table)
- `evidence_path` allowed root if evidence present
- MAC format correct
- `tags` is array
- No duplicate keys

End of TOML style guidance — keep TOML files small, typed, and machine-validated so they map reliably to the canonical YAML frontmatter and evidence rules used across HA‑BB8.

End of workspace-aware frontmatter & style guidance.
