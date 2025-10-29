---
id: ADR-0009
title: ADR Governance, Redaction, and Formatting Policy
date: 2025-09-13
status: Draft
decision: '- All ADRs must comply with standardized structure, formatting, and machine-parseability
  requirements. - Redaction, definition, and generation of ADRs must follow explicit,
  documented procedures.'
author:
- Evert Appels
- Github Copilot
related:
- ADR-0001
- ADR-0004
- ADR-0008
- ADR-0017
- ADR-0018
last_updated: 2025-09-13
supersedes: []
tags:
- governance
- adr
- formatting
- redaction
- tokens
- automation
---

# ADR-0009: ADR Governance, Redaction, and Formatting Policy

## Table of Contents
1. Context
2. Decision
3. Lifecycle & Status Model
4. Identification, Slugs, and Filenames
5. Required Front-Matter (Schema v1)
6. Redaction & Supersession
7. Definition & Generation Rules
9. Machine-Parseable Blocks
10. Enforcement
11. Token Block

## 1. Context

The project requires robust, machine-friendly governance for ADRs, including clear rules for redaction, definition, generation, and formatting. This ensures consistency, auditability, and automation for all architectural decisions.

## 2. Decision

- All ADRs must comply with standardized structure, formatting, and machine-parseability requirements.
- Redaction, definition, and generation of ADRs must follow explicit, documented procedures.
- Token blocks and machine-parseable markers are mandatory for governance automation.
 - Lifecycle and status transitions are explicitly defined and enforced.

## 3. Lifecycle & Status Model

**Allowed `status` values (canonical):**

- `Draft` → `Proposed` → `Accepted` → (`Amended`)* → `Deprecated` → `Superseded`
- Terminal: `Rejected`, `Withdrawn`
- *`Amended` applies to Accepted ADRs when a follow-up ADR narrows/clarifies scope without replacing it.*

**Rules**
- Only `Draft` and `Proposed` may change text substantially without a superseding ADR.
- Moving from `Accepted` requires either `Amended`, `Deprecated`, or `Superseded` with links.
- `Approved` (legacy) is treated as an alias of `Accepted` in automation but SHOULD NOT be used.

**Maintenance fields**
- `last_updated` (ISO-8601) MUST change on any edit.
- Optional: `last_reviewed` (ISO-8601) for periodic audits; ADRs older than 365 days SHOULD be reviewed.

## 4. Identification, Slugs, and Filenames

- **ID format**: `ADR-XXXX` (zero-padded, monotonically increasing).
- **Title format**: "ADR-XXXX: Short, Imperative Summary".
- **Slug**: derived from the short summary, kebab-case, ASCII only.
- **Filename**: `docs/ADR/ADR-XXXX-<slug>.md` (enforced by tooling).
- **Cross-links**: any ID in `related`, `supersedes`, or body MUST match `ADR-\d{4}`.

## 5. Required Front-Matter (Schema v1)

Required keys: `title`, `date`, `status`, `author`, `related`, `supersedes`, `last_updated`

Optional keys (recommended):

**Constraints**

**YAML Formatting Rules**
- Indentation: Use spaces only (no tabs) for all YAML front-matter. Indent lists with two spaces per level.
- Key Order: Required keys MUST appear in the following order:
  1. `title`
  2. `date`
  3. `status`
  4. `author`
  5. `related`
  6. `supersedes`
  7. `last_updated`
  Optional keys (if present) follow after required keys.
- No Duplicate Keys: Each YAML key MUST appear only once in the front-matter block. If a key is present multiple times, automation and CI will reject the ADR until corrected.

## 6. Redaction & Supersession

- Redactions MUST be documented in the header `supersedes` and a dedicated **Redaction** section.
- Redacted ADRs are replaced with a stub preserving front-matter, keeping `status: Superseded`, and adding:
  - `superseded_by: ADR-YYYY`
  - A brief reason and date.
- All redactions MUST be auditable via git history and the generated index.

## 7. Definition & Generation Rules

- New ADRs MUST use the canonical template (see `ADR-TEMPLATE.md`).
- Numbers are assigned by automation; manual numbering is discouraged.
- ADRs MUST include context, decision, consequences, and enforcement details.

- Redactions must be documented in the ADR header (`supersedes` field) and in a dedicated section.
- Redacted ADRs are replaced with a stub referencing the superseding ADR.
- All redactions must be auditable and traceable via commit history and index.

## 4. Definition & Generation Rules

- New ADRs must use the canonical template, including YAML front-matter and section headers.
- ADR numbers are assigned sequentially and referenced in the index.
- ADRs must be generated with clear context, decision rationale, consequences, and enforcement details.

## 5. Formatting Standards

- Use Markdown for all ADRs.
- Start with a YAML front-matter block containing title, date, status, author, related, supersedes, last_updated.
- Use clear section headers (`##`) for Context, Decision, Consequences, Enforcement, etc.
- Include a Table of Contents for ADRs longer than one page.
- All code, token, and marker blocks must be fenced with triple backticks and specify the language (`yaml` or `json`).

## 9. Machine-Parseable Blocks

- Every ADR that defines tokens, drift codes, or governance signals must include a fenced `TOKEN_BLOCK:` YAML code block at the end.
- CRTP markers, whitelists, and other governance signals must use fenced YAML/JSON blocks labeled with the marker type.
- Example:
  **TOKEN_BLOCK schema (v1)**
  - `accepted` (list of UPPER_SNAKE tokens)
  - `produces` (optional list)
  - `requires` (optional list)
  - `drift` (list of `DRIFT: <kebab>` codes)

## 10. Enforcement

- Git hooks and CI must validate ADR structure, formatting, and presence of machine-parseable blocks.
- ADR index automation should extract metadata and token blocks for governance and reporting.
- Non-compliant ADRs are flagged and must be corrected before merge.

## 11. Token Block

```yaml
TOKEN_BLOCK:
  accepted:
    - ADR_FORMAT_OK
    - ADR_REDACTION_OK
    - ADR_GENERATION_OK
    - TOKEN_BLOCK_OK
  requires:
    - ADR_SCHEMA_V1
  drift:
    - DRIFT: adr_format_invalid
    - DRIFT: missing_token_block
    - DRIFT: adr_redaction_untracked
```
