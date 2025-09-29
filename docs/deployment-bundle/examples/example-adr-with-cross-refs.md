---
id: ADR-0024
title: "Workspace Hygiene - Adoption with Local Overrides"
date: 2025-09-28
status: Accepted
author:
  - Your Name
related:
  - ADR-0015  # Local ADRs this relates to
  - ADR-0023
external_related:
  - repo: "main-config"
    adr: "ADR-0024"
    url: "https://github.com/your-org/main-config/blob/main/docs/ADR/ADR-0024-workspace-hygiene.md"
    relationship: "adopts"
    last_checked: "2025-09-28"
alignment_dependencies:
  - "main-config:ADR-0024"
supersedes: []
last_updated: 2025-09-28
---

# ADR-0024: Workspace Hygiene - Adoption with Local Overrides

## Table of Contents
1. Context
2. Cross-Repository References
3. Decision
4. Local Overrides
5. Consequences
6. Token Block

## 1. Context

This repository accumulated editor backup files (`*.bak`, `*.perlbak`, temp/swap), ad-hoc tarballs/bundles, and restore artifacts at the repository root. This obscured important sources and risked large, noisy commits. The main configuration repository's **ADR-0024: Workspace Hygiene** already defines a strong policy for ignoring, retaining and gating such artifacts.

## 2. Cross-Repository References

This ADR adopts [@main-config:ADR-0024](https://github.com/your-org/main-config/blob/main/docs/ADR/ADR-0024-workspace-hygiene.md) as the baseline workspace hygiene policy.

### Alignment Status
- **Last Verified**: 2025-09-28
- **Upstream Version**: ADR-0024 (last_updated: 2025-09-15)
- **Local Adaptations**: See "Local Overrides" section below

### Change Monitoring
Monitor [@main-config:ADR-0024](https://github.com/your-org/main-config/blob/main/docs/ADR/ADR-0024-workspace-hygiene.md) for changes that may require updates to this ADR.

## 3. Decision

**Adopt the main repository's ADR-0024 as the normative policy** and apply the following **repository-specific overrides**:

### Base Policy Adoption
- All `.gitignore` patterns from upstream ADR-0024
- All backup file handling rules  
- All CI hygiene gate requirements

### Repository-Specific Overrides
- **Backup Retention**: Extended retention for project-specific artifacts
- **Additional Patterns**: Technology-specific ignore patterns
- **Custom Validation**: Additional hygiene checks for this repository type

## 4. Local Overrides

### Extended .gitignore (beyond upstream)
```gitignore
# Project-specific patterns
*.local
.env.local
dist/
build/

# Technology-specific
node_modules/
.venv/
*.pyc
__pycache__/
```

### Custom Hygiene Rules
- **Log files**: Keep ≤30 days (stricter than upstream 90d)
- **Build artifacts**: Immediate cleanup after CI runs
- **Test reports**: Archive after 7 days

## 5. Consequences

### Positive
- **Consistency**: Aligned with organization-wide hygiene standards
- **Local Adaptation**: Customized for this repository's specific needs
- **Automated Enforcement**: Leverages existing CI infrastructure

### Risks
- **Coordination Overhead**: Changes to upstream policy require local review
- **Complexity**: Additional layer of policy management

### Mitigation
- **Regular Review**: Quarterly alignment checks with upstream ADR
- **Automated Validation**: CI checks for policy compliance
- **Clear Documentation**: Explicit documentation of local overrides

## 6. Notes

This ADR adopts the main configuration repository's ADR-0024 verbatim as the baseline. If the upstream ADR-0024 changes, this repository follows it unless an explicit override is added here in a new "Amendment" section.

## Token Block

```yaml
TOKEN_BLOCK:
  accepted:
    - WORKSPACE_HYGIENE_OK
    - UPSTREAM_ALIGNMENT_OK
    - LOCAL_OVERRIDES_DOCUMENTED
  requires:
    - MAIN_CONFIG_ADR_0024
  drift:
    - DRIFT: upstream_policy_changed
    - DRIFT: local_overrides_invalid
```