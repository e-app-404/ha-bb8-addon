---
id: ADR-0030
title: Cross-Repository ADR Alignment and Linking Standard
date: 2025-09-28
status: Accepted
decision: 'We establish a standardized system for cross-repository ADR references
  that enables: 1. **Canonical URL-based references** to ADRs in other repositories
  2.'
author:
- Evert Appels
- GitHub Copilot
related:
- ADR-0009
- ADR-0024
supersedes: []
last_updated: 2025-09-28
tags:
- adr
- cross-repository
- linking
- alignment
- governance
- tokens
---

# ADR-0030: Cross-Repository ADR Alignment and Linking Standard

## Table of Contents
1. Context
2. Decision
3. Canonical URL Patterns
4. Cross-Repository Reference Types
5. Alignment Tracking
6. Enforcement and Validation
7. Consequences
8. Token Block

## 1. Context

This project operates within an ecosystem of multiple repositories that need coordinated architectural decisions. We currently have:

- **HA-BB8 Add-on Repository** (this repo): Contains add-on-specific ADRs
- **Main HA Configuration Repository**: Contains infrastructure-wide ADRs (referenced in ADR-0024)
- **Additional Project Repositories**: Future repositories that may share architectural concerns

The need for cross-repository ADR alignment includes:
- **Policy Inheritance**: Some ADRs (like workspace hygiene) should be adopted across repositories with repo-specific overrides
- **Compatibility Requirements**: Architectural decisions in one repo may constrain or require specific decisions in others
- **Shared Standards**: Common technical standards (dependency policies, build processes) should be coordinated
- **Change Impact Analysis**: Understanding how changes to ADRs in one repository affect others

## 2. Decision

We establish a standardized system for cross-repository ADR references that enables:

1. **Canonical URL-based references** to ADRs in other repositories
2. **Structured relationship types** between ADRs across repositories
3. **Alignment tracking** to detect when referenced ADRs change
4. **Automated validation** of cross-repository links

### Core Principles

- **Explicit Over Implicit**: All cross-repository dependencies must be explicitly declared
- **Canonical URLs**: Use stable, versioned URLs that won't break over time
- **Bidirectional Awareness**: Both referencing and referenced repositories should be aware of the relationship
- **Graceful Degradation**: Broken external links should not prevent local ADR processing

## 3. Canonical URL Patterns

### GitHub Repository URLs

For ADRs hosted on GitHub, use this canonical pattern:
```
https://github.com/{owner}/{repo}/blob/{branch}/docs/ADR/ADR-{number}-{slug}.md
```

**Examples:**
- `https://github.com/e-app-404/ha-config/blob/main/docs/ADR/ADR-0024-workspace-hygiene.md`
- `https://github.com/e-app-404/omega-registry/blob/main/docs/ADR/ADR-0001-service-discovery.md`

### URL Stability Guidelines

- **Use `main` branch** for stable references unless specific version needed
- **Pin to specific commit SHA** for immutable references: `blob/{sha}/docs/ADR/...`
- **Use release tags** for major architectural alignment: `blob/v1.0.0/docs/ADR/...`

### Shorthand Notation

For frequently referenced repositories, define shorthand notation in the repository mapping:
- `@ha-config:ADR-0024` → Full GitHub URL
- `@omega:ADR-0001` → Full GitHub URL

## 4. Cross-Repository Reference Types

### 4.1 Extended Front-Matter Fields

Add these optional fields to ADR front-matter:

```yaml
# Existing fields...
related:
  - ADR-0009  # Internal references
external_related:
  - repo: "ha-config"
    adr: "ADR-0024"
    url: "https://github.com/e-app-404/ha-config/blob/main/docs/ADR/ADR-0024-workspace-hygiene.md"
    relationship: "adopts"
    last_checked: "2025-09-28"
  - repo: "omega-registry" 
    adr: "ADR-0015"
    url: "https://github.com/e-app-404/omega-registry/blob/main/docs/ADR/ADR-0015-service-mesh.md"
    relationship: "compatible_with"
    last_checked: "2025-09-28"
alignment_dependencies:
  - "ha-config:ADR-0024"  # This ADR requires alignment with external ADR
cross_repo_impacts:
  - "omega-registry:ADR-0015"  # Changes to this ADR may impact external ADR
```

### 4.2 Relationship Types

**Adoption Relationships:**
- `adopts`: This ADR adopts the external ADR as baseline policy
- `inherits_from`: This ADR inherits configuration/patterns from external ADR
- `extends`: This ADR extends the external ADR with additional requirements

**Compatibility Relationships:**
- `compatible_with`: This ADR maintains compatibility with external ADR
- `requires`: This ADR requires the external ADR to be in specific state
- `conflicts_with`: This ADR is incompatible with external ADR (with justification)

**Coordination Relationships:**
- `coordinates_with`: Changes to this ADR should be coordinated with external ADR
- `mirrors`: This ADR mirrors the external ADR with local adaptations
- `supersedes_external`: This ADR replaces functionality in external ADR

### 4.3 Content References

Within ADR content, use standardized reference format:

```markdown
## Cross-Repository References

This ADR adopts [@ha-config:ADR-0024](https://github.com/e-app-404/ha-config/blob/main/docs/ADR/ADR-0024-workspace-hygiene.md) as the baseline workspace hygiene policy.

### Alignment Status
- **Last Verified**: 2025-09-28
- **Upstream Version**: ADR-0024 (last_updated: 2025-09-15)
- **Local Adaptations**: See "BB-8-specific overrides" section below

### Change Monitoring
Monitor [@ha-config:ADR-0024](https://github.com/e-app-404/ha-config/blob/main/docs/ADR/ADR-0024-workspace-hygiene.md) for changes that may require updates to this ADR.
```

## 5. Alignment Tracking

### 5.1 Repository Mapping File

Create `docs/ADR/repository-mapping.yaml`:

```yaml
repositories:
  ha-config:
    name: "Home Assistant Configuration Repository"
    owner: "e-app-404"
    repo: "ha-config"
    base_url: "https://github.com/e-app-404/ha-config"
    adr_path: "docs/ADR"
    primary_contact: "evert@example.com"
    update_frequency: "monthly"
  
  omega-registry:
    name: "Omega Service Registry"
    owner: "e-app-404"
    repo: "omega-registry"
    base_url: "https://github.com/e-app-404/omega-registry"
    adr_path: "docs/ADR"
    primary_contact: "evert@example.com"
    update_frequency: "quarterly"

shorthand:
  "@ha-config": "ha-config"
  "@omega": "omega-registry"

alignment_policies:
  workspace_hygiene:
    upstream: "ha-config:ADR-0024"
    local_overrides_allowed: true
    review_frequency: "quarterly"
  
  dependency_management:
    upstream: "ha-config:ADR-0002" 
    local_overrides_allowed: false
    review_frequency: "monthly"
```

### 5.2 Alignment Status Tracking

Create `docs/ADR/alignment-status.yaml`:

```yaml
last_updated: "2025-09-28T10:00:00Z"
alignments:
  - local_adr: "ADR-0024"
    external_ref: "ha-config:ADR-0024"
    relationship: "adopts"
    last_checked: "2025-09-28"
    status: "aligned"
    upstream_version: "2025-09-15"
    local_modifications: true
    next_review: "2025-12-28"
  
  - local_adr: "ADR-0002"
    external_ref: "ha-config:ADR-0002"
    relationship: "inherits_from"
    last_checked: "2025-09-28"
    status: "drift_detected"
    upstream_version: "2025-09-20"
    action_required: "Review upstream changes to dependency policy"
    next_review: "2025-10-28"
```

## 6. Enforcement and Validation

### 6.1 Automated Link Validation

Create script `ops/ADR/validate_cross_repo_links.sh`:

```bash
#!/bin/bash
# Validate all cross-repository ADR links are accessible
# Check for alignment drift by comparing last_updated timestamps

echo "Validating cross-repository ADR links..."

# Extract URLs from all ADRs
grep -r "https://github.com/.*/docs/ADR/" docs/ADR/*.md | while read -r line; do
    url=$(echo "$line" | grep -o 'https://github.com[^)]*')
    echo "Checking: $url"
    
    if curl -f -s "$url" > /dev/null; then
        echo "✓ Accessible: $url"
    else
        echo "✗ BROKEN: $url"
        exit 1
    fi
done
```

### 6.2 CI Integration

Add to `.github/workflows/adr-validation.yml`:

```yaml
- name: Validate Cross-Repository Links
  run: |
    ops/ADR/validate_cross_repo_links.sh
    ops/ADR/check_alignment_drift.sh
```

### 6.3 Drift Detection

Create script `ops/ADR/check_alignment_drift.sh`:

```bash
#!/bin/bash
# Check if upstream ADRs have been updated since last alignment check
# Parse alignment-status.yaml and fetch upstream last_updated timestamps

echo "Checking for alignment drift..."

# Implementation would:
# 1. Parse alignment-status.yaml
# 2. Fetch upstream ADR front-matter
# 3. Compare last_updated timestamps  
# 4. Report drift and required actions
```

## 7. Consequences

### Positive Impacts

- **Improved Coordination**: Clear visibility into cross-repository architectural dependencies
- **Change Impact Analysis**: Understand how changes propagate across repository boundaries
- **Consistency Enforcement**: Automatic detection when shared standards diverge
- **Documentation Quality**: Explicit tracking of architectural relationships

### Potential Challenges

- **Link Maintenance**: External links may break if repositories are restructured
- **Coordination Overhead**: Changes may require coordination across multiple repositories
- **Complexity**: Additional metadata and validation processes increase complexity

### Mitigation Strategies

- **Graceful Degradation**: Broken links should not prevent ADR processing
- **Automated Monitoring**: Regular CI validation of cross-repository links
- **Clear Ownership**: Designated contacts for each repository relationship
- **Staged Rollout**: Implement cross-repository linking incrementally

## 8. Implementation Example

### Updated ADR-0024 Front-Matter

```yaml
---
id: ADR-0024
title: "Workspace Hygiene (BB-8 add-on) — Adoption of ADR-0024 with repo-specific overrides"
date: 2025-09-13
status: Accepted
author:
  - Evert Appels
related:
  - ADR-0027
external_related:
  - repo: "ha-config"
    adr: "ADR-0024"
    url: "https://github.com/e-app-404/ha-config/blob/main/docs/ADR/ADR-0024-workspace-hygiene.md"
    relationship: "adopts"
    last_checked: "2025-09-28"
alignment_dependencies:
  - "ha-config:ADR-0024"
supersedes: []
last_updated: 2025-09-28
---
```

## Token Block

```yaml
TOKEN_BLOCK:
  accepted:
    - CROSS_REPO_ADR_LINKING_OK
    - ALIGNMENT_TRACKING_OK
    - CANONICAL_URL_PATTERNS_OK
    - AUTOMATED_VALIDATION_OK
  requires:
    - ADR_SCHEMA_V1
    - REPOSITORY_MAPPING_OK
  drift:
    - DRIFT: cross_repo_link_broken
    - DRIFT: alignment_drift_detected  
    - DRIFT: external_adr_updated
```