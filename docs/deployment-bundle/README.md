# Cross-Repository ADR Linking System - Deployment Bundle

This bundle contains everything needed to implement cross-repository ADR alignment and linking in your repository ecosystem.

## 📦 Bundle Contents

```
deployment-bundle/
├── README.md                           # This file - deployment instructions
├── COPILOT-INSTRUCTIONS.md            # Instructions for GitHub Copilot/AI assistants
├── templates/
│   ├── ADR-XXXX-cross-repo-standard.md   # ADR-0030 template for target repo
│   ├── ADR-template-enhanced.md           # Enhanced ADR template with cross-repo fields
│   ├── repository-mapping.yaml.template  # Repository mapping configuration
│   ├── alignment-status.yaml.template    # Alignment tracking template
│   └── gitignore-additions.txt           # .gitignore entries to add
├── scripts/
│   ├── deploy.sh                       # Automated deployment script
│   ├── validate_cross_repo_links.sh   # Link validation script
│   ├── check_alignment_drift.sh       # Drift detection script
│   └── post_deploy_validation.sh      # Verify deployment success
└── examples/
    ├── example-adr-with-cross-refs.md     # Sample ADR showing cross-repo references
    └── ci-workflow-addition.yml.sample    # GitHub Actions workflow snippet
```

## 🚀 Quick Start

### Option 1: Automated Deployment (Recommended)

```bash
# 1. Copy this bundle to your target repository
cp -r deployment-bundle /path/to/target-repo/

# 2. Navigate to target repository
cd /path/to/target-repo/

# 3. Run deployment script
./deployment-bundle/scripts/deploy.sh

# 4. Customize repository-specific settings
# Edit docs/ADR/repository-mapping.yaml with your repo details

# 5. Validate deployment
./deployment-bundle/scripts/post_deploy_validation.sh
```

### Option 2: Manual Deployment

If you prefer manual control or need to customize the deployment:

1. **Copy ADR Standard**: Copy `templates/ADR-XXXX-cross-repo-standard.md` to `docs/ADR/` and rename with next ADR number
2. **Update ADR Template**: Replace or enhance your existing `docs/ADR/ADR-template.md`
3. **Add Configuration**: Copy and customize `repository-mapping.yaml.template` 
4. **Add Scripts**: Copy validation scripts to `ops/ADR/` (create directory if needed)
5. **Update CI**: Add workflow snippets from `examples/ci-workflow-addition.yml.sample`

## 📋 Repository-Specific Customization

### 1. Repository Mapping Configuration

Edit `docs/ADR/repository-mapping.yaml`:

```yaml
repositories:
  # Add your repository ecosystem here
  main-repo:
    name: "Your Main Repository"
    owner: "your-github-org"
    repo: "main-repo-name"
    base_url: "https://github.com/your-github-org/main-repo-name"
    # ... other settings

shorthand:
  "@main": "main-repo"
  "@this": "current-repo-name"  # This repository
```

### 2. Alignment Policies

Configure which ADRs should be aligned across repositories:

```yaml
alignment_policies:
  your_policy_name:
    upstream: "main-repo:ADR-0024"
    downstream:
      - "current-repo:ADR-0024"
    local_overrides_allowed: true
    coordination_required: false
```

### 3. ADR Numbering

- Determine the next ADR number in your target repository
- Rename `ADR-XXXX-cross-repo-standard.md` to use that number
- Update the `id` field in the front-matter

## 🔧 Integration Steps

### Step 1: Core Files

```bash
# Create ADR directory if it doesn't exist
mkdir -p docs/ADR

# Copy and customize the cross-repo standard ADR
cp templates/ADR-XXXX-cross-repo-standard.md docs/ADR/ADR-0030-cross-repository-alignment.md

# Update or replace your ADR template  
cp templates/ADR-template-enhanced.md docs/ADR/ADR-template.md

# Add repository configuration
cp templates/repository-mapping.yaml.template docs/ADR/repository-mapping.yaml
```

### Step 2: Validation Scripts

```bash
# Create ops directory for scripts
mkdir -p ops/ADR

# Copy validation scripts
cp scripts/validate_cross_repo_links.sh ops/ADR/
cp scripts/check_alignment_drift.sh ops/ADR/

# Make scripts executable
chmod +x ops/ADR/*.sh
```

### Step 3: CI Integration

Add to your `.github/workflows/` (create workflow or add to existing):
See `examples/ci-workflow-addition.yml.sample` for complete examples.

```yaml
# Add this job to your workflow
- name: Validate Cross-Repository ADR Links
  run: |
    if [ -f "ops/ADR/validate_cross_repo_links.sh" ]; then
      ./ops/ADR/validate_cross_repo_links.sh
    fi
    
- name: Check ADR Alignment Drift  
  run: |
    if [ -f "ops/ADR/check_alignment_drift.sh" ]; then
      ./ops/ADR/check_alignment_drift.sh
    fi
```

### Step 4: Update .gitignore

Add these entries to your `.gitignore`:

```gitignore
# ADR alignment tracking (auto-generated)
docs/ADR/alignment-status.yaml

# Deployment bundle (remove after deployment)
deployment-bundle/
```

## 🔗 Creating Cross-Repository References

### In ADR Front-Matter

```yaml
external_related:
  - repo: "main-repo"
    adr: "ADR-0024"
    url: "https://github.com/your-org/main-repo/blob/main/docs/ADR/ADR-0024-example.md"
    relationship: "adopts"
    last_checked: "2025-09-28"

alignment_dependencies:
  - "main-repo:ADR-0024"
```

### In ADR Content

```markdown
## Cross-Repository References

This ADR adopts [@main:ADR-0024](https://github.com/your-org/main-repo/blob/main/docs/ADR/ADR-0024-example.md) as baseline policy.

### Alignment Status
- **Last Verified**: 2025-09-28
- **Upstream Version**: ADR-0024 (last_updated: 2025-09-15)
- **Local Adaptations**: See "Repository-specific overrides" section below
```

## ✅ Validation

After deployment, run validation:

```bash
# Validate all cross-repository links
./ops/ADR/validate_cross_repo_links.sh

# Check for alignment drift
./ops/ADR/check_alignment_drift.sh

# Full post-deployment validation
./deployment-bundle/scripts/post_deploy_validation.sh
```

## 🚨 Troubleshooting

### Common Issues

1. **Scripts not executable**: Run `chmod +x ops/ADR/*.sh`
2. **Missing directories**: Ensure `docs/ADR/` and `ops/ADR/` exist
3. **Broken links**: Update URLs in `repository-mapping.yaml`
4. **Permission errors**: Check file permissions and ownership

### Getting Help

1. Check the example ADR in `examples/example-adr-with-cross-refs.md`
2. Review the original implementation in the BB-8 addon repository
3. Validate your `repository-mapping.yaml` syntax
4. Test with a single cross-repo reference first

## 📚 Reference

- **Source Repository**: https://github.com/e-app-404/ha-bb8-addon
- **Original ADR-0030**: [Cross-Repository ADR Alignment Standard](https://github.com/e-app-404/ha-bb8-addon/blob/main/docs/ADR/ADR-0030-cross-repository-adr-alignment.md)
- **Working Example**: ADR-0024 in BB-8 addon repository

## 🔄 Maintenance

### Regular Tasks

1. **Weekly**: Run link validation to catch broken references
2. **Monthly**: Check for alignment drift with upstream ADRs
3. **Quarterly**: Review and update repository mapping configuration
4. **As needed**: Update cross-repo references when ADRs change

### Updating the System

To get updates to the cross-repository linking system:

1. Pull the latest deployment bundle from the source repository
2. Compare with your current implementation
3. Apply updates while preserving your repository-specific customizations
4. Re-run validation to ensure everything works

---

**Deployment Bundle Version**: 1.0  
**Generated From**: ha-bb8-addon repository  
**Date**: 2025-09-28  
**Compatible With**: GitHub repositories using ADR governance