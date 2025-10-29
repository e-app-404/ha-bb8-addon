---
description: 'Extract a concise "decision" string from an ADR body to populate frontmatter (min 20, max 300 chars)'
agent: gpt-5-beast
tools: ['runCommands', 'edit', 'search']
---

# Extract ADR decision field

## Mission
Produce a single, concise decision summary for an ADR, suitable for frontmatter field `decision` per docs/meta/adr.toml constraints.

## Scope & Preconditions
- Input is one ADR Markdown document (full text), which may or may not contain frontmatter.
- You must extract the decision from the body text (preferred sources: a section titled “Decision”, then “Context/Decision/Summary”, else infer from content).
- Comply with constraints from adr.toml:
  - 20–300 characters, sentence case, no trailing whitespace, no backticks.
  - 1–2 sentences; avoid implementation details and citations.
  - Summarize the architectural choice and its scope/impact.

## Inputs
- markdown: Full ADR markdown content
- id: ADR identifier (e.g., ADR-0031) for reference only

## Workflow
1) Try exact section extraction in order:
   - Heading matching /^(##\s*(?:\d+\.\s*)?Decision)/ with following paragraph(s).
   - Next, a block under headings containing both “Context” and “Decision” where the decision sentence is explicit.
2) If not found, infer the decision from the document’s problem/choice/consequence narrative (goal: the architectural choice, not the rationale alone).
3) Normalize the text:
   - Trim; sentence case; collapse whitespace; remove code ticks/backticks.
   - Limit to 1–2 sentences, 20–300 chars. Prefer the crispest summary.
4) Validate length; if <20 chars, minimally expand with scope or effect. If >300 chars, truncate at sentence boundary ≤300.

## Output Expectations
- Return only the decision text, no surrounding quotes or markdown.
- Do not include headings, code, citations, or lists.
- It must be self-contained and understandable out of context.

## Quality Assurance
- Check: 20–300 chars; ends with period; sentence case; no backticks.
- States the architectural choice explicitly (what we will do), not only problem/rationale.
- Avoid vendor/product names unless essential to the choice.

## Example
Input (abridged):
  - Title: ADR-0031 Supervisor-only Operations & Testing Protocol
  - Body includes “## Decision … Adopt a comprehensive Supervisor-only operational model …”

Good Output:
  Adopt a Supervisor-only operational model for deployment and testing, validating health and MQTT via Supervisor interfaces.

Bad Output:
  - “We investigated options and ran tests.” (too vague)
  - “See section Decision.” (not a decision)

## Return Format
Plaintext line containing only the decision string.
