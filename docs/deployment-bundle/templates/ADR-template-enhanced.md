---
title: "ADR-XXXX: Short, Imperative Summary"
date: YYYY-MM-DD
status: Draft
author:
  - Your Name
related: []
external_related: []
# Optional: Cross-repository ADR references (see your Cross-Repository ADR Standard)
# external_related:
#   - repo: "main-repo"
#     adr: "ADR-0024"
#     url: "https://github.com/{your-org}/{main-repo}/blob/main/docs/ADR/ADR-0024-example.md"
#     relationship: "adopts"  # adopts|inherits_from|extends|compatible_with|requires|conflicts_with|coordinates_with|mirrors|supersedes_external
#     last_checked: "YYYY-MM-DD"
alignment_dependencies: []
# Optional: ADRs in other repositories that this ADR must align with
# alignment_dependencies:
#   - "main-repo:ADR-0024"
cross_repo_impacts: []
# Optional: ADRs in other repositories that may be impacted by changes to this ADR
# cross_repo_impacts:
#   - "other-repo:ADR-0015"
supersedes: []
last_updated: YYYY-MM-DD
tags: []
decision_type: architecture
visibility: internal
references: []
---

# ADR-XXXX: Short, Imperative Summary

## Table of Contents
1. Context
2. Decision
3. Consequences
4. Alternatives Considered
5. Enforcement
6. Token Block

## 1. Context
<Describe the problem and background concisely.>

<!-- Optional: Cross-Repository References Section -->
<!-- Use this section when your ADR relates to ADRs in other repositories -->
<!-- 
## Cross-Repository References

This ADR [adopts|inherits from|extends|coordinates with] [@repo-shorthand:ADR-XXXX](full-github-url) as [baseline policy|shared standard|compatibility requirement].

### Alignment Status
- **Last Verified**: YYYY-MM-DD
- **Upstream Version**: ADR-XXXX (last_updated: YYYY-MM-DD)
- **Local Adaptations**: [None|See section X below]

### Change Monitoring
Monitor [@repo-shorthand:ADR-XXXX](full-github-url) for changes that may require updates to this ADR.

-->

## 2. Decision
<State the decision. If this amends or supersedes another ADR, name it here and in front-matter.>

## 3. Consequences
<Intended and unintended outcomes, risks, trade-offs.>

## 4. Alternatives Considered
<Key alternatives and why they were rejected.>

## 5. Enforcement
<How this ADR will be validated and enforced (tests, checks, CI gates).>

## 6. Token Block
```yaml
TOKEN_BLOCK:
  accepted:
    - ADR_FORMAT_OK
  requires:
    - ADR_SCHEMA_V1
  drift:
    - DRIFT: adr_format_invalid
```