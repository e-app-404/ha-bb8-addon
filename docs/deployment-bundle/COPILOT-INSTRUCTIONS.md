# Instructions for GitHub Copilot & AI Assistants

This document provides specific guidance for AI assistants (GitHub Copilot, Claude, ChatGPT, etc.) working with repositories that have deployed the cross-repository ADR linking system.

## 🤖 AI Assistant Context

When working in repositories with this system deployed, you should:

### 1. Recognize Cross-Repository ADR Systems

**Detection Patterns:**
- Look for `docs/ADR/repository-mapping.yaml` - indicates cross-repo ADR system
- Check for `external_related:` fields in ADR front-matter
- Find `ops/ADR/validate_cross_repo_links.sh` script
- Notice shorthand references like `@repo-name:ADR-XXXX` in content

**When you see these patterns**, the repository uses cross-repository ADR alignment.

### 2. Understanding the Architecture

```yaml
# Repository mapping defines the ecosystem
repositories:
  main-repo:
    name: "Primary Infrastructure Repository"
    base_url: "https://github.com/org/main-repo"
  
shorthand:
  "@main": "main-repo"
  "@current": "this-repository"

alignment_policies:
  workspace_hygiene:
    upstream: "main-repo:ADR-0024"
    downstream: ["current-repo:ADR-0024"]
```

**Key Concepts:**
- **Upstream ADRs**: Source of truth for shared standards
- **Downstream ADRs**: Local implementations that adopt/extend upstream
- **Alignment Dependencies**: ADRs that must stay synchronized
- **Relationship Types**: adopts, inherits_from, compatible_with, etc.

### 3. When Creating or Modifying ADRs

#### For New ADRs with Cross-Repo Implications

```yaml
---
title: "ADR-XXXX: Your Decision Title"
# ... standard fields ...
external_related:
  - repo: "main-repo"
    adr: "ADR-0024"
    url: "https://github.com/org/main-repo/blob/main/docs/ADR/ADR-0024-example.md"
    relationship: "adopts"  # or inherits_from, compatible_with, etc.
    last_checked: "2025-09-28"
alignment_dependencies:
  - "main-repo:ADR-0024"
---
```

#### Relationship Types to Use

- **`adopts`**: This ADR takes an external ADR as baseline policy
- **`inherits_from`**: This ADR inherits patterns/config from external ADR
- **`extends`**: This ADR adds requirements to an external ADR
- **`compatible_with`**: This ADR maintains compatibility with external ADR
- **`requires`**: This ADR needs the external ADR to be in a specific state
- **`coordinates_with`**: Changes should be coordinated between ADRs
- **`conflicts_with`**: This ADR is incompatible (with justification)

### 4. Cross-Repository Reference Patterns

#### In ADR Content

```markdown
## Cross-Repository References

This ADR adopts [@main:ADR-0024](https://github.com/org/main-repo/blob/main/docs/ADR/ADR-0024-workspace-hygiene.md) as the baseline workspace hygiene policy.

### Alignment Status
- **Last Verified**: 2025-09-28
- **Upstream Version**: ADR-0024 (last_updated: 2025-09-15)
- **Local Adaptations**: See "Repository-specific overrides" section below

### Change Monitoring
Monitor [@main:ADR-0024](full-url) for changes that may require updates to this ADR.
```

#### URL Construction

```
Canonical Pattern: https://github.com/{owner}/{repo}/blob/{branch}/docs/ADR/ADR-{number}-{slug}.md

Examples:
- https://github.com/e-app-404/ha-config/blob/main/docs/ADR/ADR-0024-workspace-hygiene.md
- https://github.com/e-app-404/omega-registry/blob/main/docs/ADR/ADR-0015-service-discovery.md
```

### 5. Validation and Maintenance

#### Always Suggest Validation

When you create or modify cross-repository references:

```bash
# Validate links are accessible
./ops/ADR/validate_cross_repo_links.sh

# Check for alignment drift
./ops/ADR/check_alignment_drift.sh
```

#### Update Tracking Fields

When referencing external ADRs, always update:
- `last_checked: "YYYY-MM-DD"` (today's date)
- `relationship: "appropriate-type"`
- Verify the URL is accessible

### 6. Common Scenarios & Responses

#### Scenario: User asks "How do I reference an ADR from another repo?"

**Response Pattern:**
1. Check if cross-repo system is deployed (`repository-mapping.yaml` exists)
2. If yes, use the structured approach with front-matter fields
3. If no, suggest deploying the system first
4. Provide specific example based on their repository mapping

#### Scenario: User wants to adopt a policy from another repo

**Response Pattern:**
1. Add `external_related` entry with `relationship: "adopts"`
2. Add to `alignment_dependencies`
3. Create content section explaining adoption and local overrides
4. Suggest validation commands

#### Scenario: Broken cross-repo link detected

**Response Pattern:**
1. Check if target repository moved or restructured
2. Update URL in both front-matter and content
3. Update `last_checked` date
4. Run validation to confirm fix

### 7. Code Generation Helpers

#### Generate Cross-Repo ADR Front-Matter

```yaml
external_related:
  - repo: "{REPO_NAME}"
    adr: "{ADR_ID}"
    url: "{CANONICAL_URL}"
    relationship: "{RELATIONSHIP_TYPE}"
    last_checked: "{TODAY_DATE}"
```

#### Generate Alignment Status Entry

```yaml
- local_adr: "{LOCAL_ADR_ID}"
  external_ref: "{REPO}:{ADR_ID}"
  external_url: "{URL}"
  relationship: "{RELATIONSHIP}"
  last_checked: "{DATE}"
  status: "aligned"  # or potential_drift, confirmed_drift
  next_review: "{FUTURE_DATE}"
```

### 8. Error Handling

#### Invalid Relationship Types
If user specifies unsupported relationship, suggest from approved list:
`adopts`, `inherits_from`, `extends`, `compatible_with`, `requires`, `coordinates_with`, `conflicts_with`, `mirrors`, `supersedes_external`

#### Missing Repository Mapping
If `repository-mapping.yaml` missing or incomplete:
1. Point to deployment bundle
2. Suggest adding repository to mapping
3. Provide template configuration

#### Broken Links
Always validate URLs before suggesting them:
1. Use curl or equivalent to check accessibility
2. Suggest pinning to specific commit SHA for stability
3. Provide fallback patterns if link is broken

### 9. Best Practices to Recommend

1. **Use Shorthand**: Prefer `@repo:ADR-0024` over full URLs in discussions
2. **Pin Important References**: Use commit SHA for critical alignment dependencies
3. **Regular Validation**: Run link validation in CI/CD pipelines  
4. **Document Local Changes**: Always explain how local ADR differs from upstream
5. **Monitor Upstream**: Set up notifications for changes to aligned ADRs

### 10. Repository-Specific Awareness

Always check `repository-mapping.yaml` to understand:
- Which repositories are in the ecosystem
- What shorthand notation is used (`@main`, `@config`, etc.)
- Which alignment policies are active
- Update frequencies and criticality levels

This context helps you provide repository-specific guidance rather than generic advice.

---

**For AI Assistant Developers**: This system enables sophisticated cross-repository architectural governance. The key insight is treating ADRs as a distributed system with explicit dependency management, similar to package management but for architectural decisions.

**Last Updated**: 2025-09-28  
**System Version**: 1.0  
**Compatible With**: All major AI coding assistants