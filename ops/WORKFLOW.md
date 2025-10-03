# ops/ Workflow Guide

## Development Workflow

Complete development lifecycle using ops/ scripts in logical sequence.

### 1. Environment Setup

```bash
# Initial workspace setup
ops/workspace/one_shot_setup.sh

# Check workspace health
ops/utils/check_workspace_quiet.sh

# Purge any stray symlinks (if needed)
ops/workspace/symlink_purge.sh
```

### 2. Development & Testing

```bash
# Full CI pipeline (compile → test → coverage → gates)
ops/build/compile_test_gate_bleep.sh

# Structure validation
ops/validation/check_structure.sh

# Quality assurance harvest
ops/validation/qa_harvest.py

# Addon verification
ops/validation/verify_addon.sh
```

### 3. Evidence Collection

```bash
# Evidence preflight check
ops/evidence/evidence_preflight.sh

# STP4 evidence collection
ops/evidence/run_evidence_stp4.sh

# MQTT probe testing
ops/evidence/mqtt_probe.py
```

### 4. Release Process

```bash
# Option A: Using Makefile (recommended)
make release-patch    # Automated patch release
make release-minor    # Automated minor release  
make release-major    # Automated major release
make release VERSION=1.2.3  # Specific version

# Option B: Manual step-by-step
ops/release/bump_version.sh patch     # Bump version
ops/release/publish_addon_archive.sh  # Publish to repo
ops/release/deploy_ha_over_ssh.sh     # Deploy to HA
```

### 5. Deployment Operations

```bash
# Dual-clone deployment
ops/deploy/deploy_dual_clone.sh

# Workspace deployment
ops/deploy/deploy_workspace.sh

# Runtime canonicalization
ops/deploy/accept_runtime_canonical.sh
```

### 6. Diagnostics & Troubleshooting

```bash
# Collect comprehensive diagnostics
ops/diag/collect_ha_bb8_diagnostics.sh home-assistant

# Evidence capture for issues
ops/evidence/capture_trace.py

# Shape guard validation
ops/validation/shape_guard.py
```

## Architecture Decision Records (ADR)

```bash
# Generate ADR index
ops/ADR/generate_adr_index.sh

# Validate ADR structure
ops/ADR/validate_adrs.sh

# Cross-repository link validation  
ops/ADR/validate_cross_repo_links.sh
```

## Script Dependencies

### Dependency Graph

```
Environment Setup (1)
         ↓
Development & Testing (2) ←→ Evidence Collection (3)
         ↓
Release Process (4)
         ↓
Deployment (5) ←→ Diagnostics (6)
```

### Prerequisites by Stage

**Environment Setup**
- Git repository initialized
- Python virtual environment
- SSH access configured

**Development & Testing**  
- Environment setup completed
- Source code in `addon/` directory
- Test suite in `addon/tests/`

**Evidence Collection**
- MQTT broker accessible  
- BLE hardware available (for full tests)
- Home Assistant instance reachable

**Release Process**
- All tests passing
- Git working directory clean
- Version files writable

**Deployment**
- SSH access to target environment
- Home Assistant API access (LLAT)
- Target runtime directory accessible

**Diagnostics**
- SSH access to Home Assistant
- Addon running or logs accessible

## Integration Points

### Makefile Integration

```makefile
# Build pipeline
qa: ops/build/compile_test_gate_bleep.sh

# Validation gates
validate: ops/validation/check_structure.sh && \\
          ops/validation/verify_addon.sh

# Evidence collection
evidence-stp4: ops/evidence/run_evidence_stp4.sh

# Release workflow (already implemented)
release-patch: ops/release/bump_version.sh patch && \\
               ops/release/publish_addon_archive.sh && \\
               ops/release/deploy_ha_over_ssh.sh
```

### CI/CD Integration

```yaml
# .github/workflows/ci.yml (example)
- name: Build & Test
  run: ops/build/compile_test_gate_bleep.sh
  
- name: Validate Structure  
  run: ops/validation/check_structure.sh
  
- name: Collect Evidence
  run: ops/evidence/run_evidence_stp4.sh
  
- name: Deploy to Staging
  run: ops/deploy/deploy_workspace.sh staging
```

## Error Handling

### Exit Code Standards

- **0**: Success - operation completed successfully
- **1**: Failure - operation failed, user action required  
- **2**: Error - script execution error, check configuration
- **3**: Config Error - configuration file or environment issue
- **64**: Usage Error - incorrect command line arguments

### Common Error Scenarios

**SSH Connection Issues**
```bash
# Debug SSH connectivity
ssh -v home-assistant echo \"Connection test\"

# Check SSH config
ops/release/deploy_ha_over_ssh.sh test-llat
```

**Permission Issues**
```bash
# Fix script permissions
find ops/ -name \"*.sh\" -exec chmod +x {} \\;

# Check file ownership
ls -la ops/release/
```

**Environment Issues**
```bash
# Verify workspace health
ops/utils/check_workspace_quiet.sh

# Reset workspace if needed
ops/workspace/one_shot_setup.sh --reset
```

## Best Practices

### Script Development

1. **Test locally first**: Always test scripts in development environment
2. **Use set -euo pipefail**: Enable strict error handling in bash
3. **Document usage**: Add clear usage examples in script headers
4. **Handle edge cases**: Consider failure modes and edge conditions
5. **Log appropriately**: Balance verbosity with usefulness

### Workflow Management

1. **Follow sequence**: Respect the dependency order in workflows
2. **Check prerequisites**: Verify environment before running scripts
3. **Clean working directory**: Ensure git status is clean before releases
4. **Validate results**: Check script outputs and exit codes
5. **Monitor logs**: Review operation logs for issues

### Security

1. **No secrets in logs**: Avoid logging sensitive information
2. **Use SSH keys**: Never use password authentication
3. **Validate tokens**: Check LLAT presence before API operations
4. **Principle of least privilege**: Scripts should have minimal required permissions

---

*This workflow documentation supports the complete HA-BB8 addon development, testing, release, and operational lifecycle using the organized ops/ directory structure.*