# ADR-0001-A1 — Minimal `.github` Allowed in Add-on Repos (Structure Gate Only)

Status: ACCEPTED
Date: 2025-11-01

Amends ADR-0001 to allow a minimal `.github` in add-on repositories containing only:
- `.github/workflows/adr-structure.yml` (structure gate workflow)

Constraints:
- No other `.github` content is permitted in add-on repos.
- All other ADR-0001 constraints remain unchanged.
- The structure workflow must validate this exception itself (allow only `.github/workflows/adr-structure.yml`).

Rationale:
- Add-on repos otherwise cannot host CI, preventing ADR-0001 conformance checks from running on PRs.
- This narrow exception enables automated enforcement without reintroducing broader `.github` usage at add-on roots.
