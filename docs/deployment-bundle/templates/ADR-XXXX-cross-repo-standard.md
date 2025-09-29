---
id: ADR-XXXX
title: "Cross-Repository ADR Alignment and Linking Standard"
date: YYYY-MM-DD
status: Accepted
author:
  - Your Name
  - GitHub Copilot
related:
  - ADR-0009  # Update to your ADR governance ADR
supersedes: []
last_updated: YYYY-MM-DD
---

# ADR-XXXX: Cross-Repository ADR Alignment and Linking Standard

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

- **[Repository Name]** (this repo): Contains [description]-specific ADRs
- **[Other Repository Name]**: Contains [description] ADRs
- **Additional Project Repositories**: Future repositories that may share architectural concerns

The need for cross-repository ADR alignment includes:
- **Policy Inheritance**: Some ADRs should be adopted across repositories with repo-specific overrides
- **Compatibility Requirements**: Architectural decisions in one repo may constrain or require specific decisions in others
- **Shared Standards**: Common technical standards should be coordinated
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

**Examples (update with your actual repositories):**
- `https://github.com/{your-org}/{main-repo}/blob/main/docs/ADR/ADR-0024-workspace-hygiene.md`
- `https://github.com/{your-org}/{other-repo}/blob/main/docs/ADR/ADR-0001-service-discovery.md`

### URL Stability Guidelines

- **Use `main` branch** for stable references unless specific version needed
- **Pin to specific commit SHA** for immutable references: `blob/{sha}/docs/ADR/...`
- **Use release tags** for major architectural alignment: `blob/v1.0.0/docs/ADR/...`

### Shorthand Notation

For frequently referenced repositories, define shorthand notation in the repository mapping:
- `@main-repo:ADR-0024` → Full GitHub URL
- `@other-repo:ADR-0001` → Full GitHub URL

## 4. Cross-Repository Reference Types

### 4.1 Extended Front-Matter Fields

Add these optional fields to ADR front-matter:

```yaml
# Existing fields...
related:
  - ADR-0009  # Internal references
external_related:
  - repo: "main-repo"
    adr: "ADR-0024"
    url: "https://github.com/{your-org}/{main-repo}/blob/main/docs/ADR/ADR-0024-example.md"
    relationship: "adopts"
    last_checked: "YYYY-MM-DD"
  - repo: "other-repo" 
    adr: "ADR-0015"
    url: "https://github.com/{your-org}/{other-repo}/blob/main/docs/ADR/ADR-0015-example.md"
    relationship: "compatible_with"
    last_checked: "YYYY-MM-DD"
alignment_dependencies:
  - "main-repo:ADR-0024"  # This ADR requires alignment with external ADR
cross_repo_impacts:
  - "other-repo:ADR-0015"  # Changes to this ADR may impact external ADR
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

This ADR adopts [@main-repo:ADR-0024](https://github.com/{your-org}/{main-repo}/blob/main/docs/ADR/ADR-0024-example.md) as the baseline policy.

### Alignment Status
- **Last Verified**: YYYY-MM-DD
- **Upstream Version**: ADR-0024 (last_updated: YYYY-MM-DD)
- **Local Adaptations**: See "Repository-specific overrides" section below

### Change Monitoring
Monitor [@main-repo:ADR-0024](https://github.com/{your-org}/{main-repo}/blob/main/docs/ADR/ADR-0024-example.md) for changes that may require updates to this ADR.
```

## 5. Alignment Tracking

### 5.1 Repository Mapping File

Create `docs/ADR/repository-mapping.yaml`:

```yaml
repositories:
  main-repo:
    name: "Your Main Repository"
    owner: "{your-org}"
    repo: "{main-repo}"
    base_url: "https://github.com/{your-org}/{main-repo}"
    adr_path: "docs/ADR"
    primary_contact: "your-email@example.com"
    update_frequency: "monthly"
  
  other-repo:
    name: "Your Other Repository"
    owner: "{your-org}"
    repo: "{other-repo}"
    base_url: "https://github.com/{your-org}/{other-repo}"
    adr_path: "docs/ADR"
    primary_contact: "your-email@example.com"
    update_frequency: "quarterly"

shorthand:
  "@main": "main-repo"
  "@other": "other-repo"
```

## 6. Enforcement and Validation

### 6.1 Automated Link Validation

The validation script `ops/ADR/validate_cross_repo_links.sh` will:
- Validate all cross-repository URLs are accessible
- Check for alignment drift by comparing timestamps
- Report broken links and required actions

### 6.2 CI Integration

Add to your CI workflow:

```yaml
- name: Validate Cross-Repository Links
  run: |
    ops/ADR/validate_cross_repo_links.sh
    ops/ADR/check_alignment_drift.sh
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