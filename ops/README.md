# ops/ - Operations and Development Scripts

## Overview

The `ops/` directory contains operational scripts organized by functional purpose. This structure provides clear separation of concerns and makes it easy to find the right tool for each task.

## Directory Structure

```
ops/
├── ADR/              # Architecture Decision Record management
├── build/            # Compilation, testing, CI/CD pipeline  
├── deploy/           # Deployment orchestration and environments
├── diag/             # Diagnostics and troubleshooting
├── evidence/         # Evidence collection and attestation
├── release/          # Version management and publishing
├── utils/            # General utilities and helpers
├── validation/       # Code quality and compliance checking
└── workspace/        # Workspace setup and maintenance
```

## Functional Categories

### 🏗️ **Development Workflow**
- **`build/`** - Compile, test, and validate code
- **`validation/`** - Quality assurance and compliance
- **`workspace/`** - Development environment management

### 🚀 **Release & Deployment** 
- **`release/`** - Version bumping, changelog, publishing
- **`deploy/`** - Environment deployment and orchestration

### 📊 **Operations & Support**
- **`diag/`** - System diagnostics and troubleshooting  
- **`evidence/`** - Operational evidence and attestation
- **`utils/`** - General-purpose utilities

### 📚 **Documentation & Governance**
- **`ADR/`** - Architecture decisions and cross-repo linking

## Quick Reference

### Common Operations

```bash
# Development workflow
ops/build/compile_test_gate_bleep.sh    # Full CI pipeline
ops/validation/check_structure.sh       # Structure validation
ops/workspace/one_shot_setup.sh        # Environment setup

# Release workflow  
ops/release/bump_version.sh patch       # Version bump
ops/release/publish_addon_archive.sh    # Publish to repository
ops/release/deploy_ha_over_ssh.sh       # Deploy to Home Assistant

# Operations
ops/diag/collect_ha_bb8_diagnostics.sh  # Collect diagnostics
ops/evidence/run_evidence_stp4.sh       # Evidence collection
ops/utils/check_workspace_quiet.sh      # Silent health check
```

### Integration with Makefile

The Makefile integrates with ops/ scripts:

```makefile
release-patch: ops/release/bump_version.sh patch && \\
               ops/release/publish_addon_archive.sh && \\
               ops/release/deploy_ha_over_ssh.sh
```

## Script Standards

All scripts follow these conventions:

1. **Executable permissions**: `chmod +x script.sh`
2. **Shebang line**: `#!/usr/bin/env bash` or `#!/usr/bin/env python3`
3. **Usage documentation**: Header comment with usage examples
4. **Error handling**: `set -euo pipefail` for shell scripts
5. **Exit codes**: 0=success, 1=failure, 2=error, 3=config error

## Dependencies

### Global Requirements
- `git` - Version control operations
- `ssh` - Remote deployment access 
- `curl` - HTTP API interactions
- `python3` - Python script execution

### Development Requirements  
- Python virtual environment (`.venv/`)
- `pytest`, `coverage` - Testing and coverage
- `ruff`, `mypy` - Linting and type checking

### Deployment Requirements
- SSH access to Home Assistant instance
- Home Assistant Long-Lived Access Token (LLAT)
- Docker access (for container operations)

## Security Considerations

- **No secrets in logs**: Scripts avoid printing sensitive information
- **SSH key authentication**: No password-based authentication
- **Token validation**: LLAT presence checked before API calls
- **Safe defaults**: Scripts fail safely rather than destructively

## Troubleshooting

### Common Issues

1. **Permission denied**: Run `chmod +x script.sh`
2. **SSH connection failed**: Verify SSH config and keys
3. **Python import errors**: Ensure virtual environment is activated
4. **Missing dependencies**: Check README.md in specific directory

### Debug Mode

Most scripts support debug mode:
```bash
BASH_XTRACES=1 ./script.sh  # Enable bash tracing
DEBUG=1 ./script.py         # Enable debug logging
```

## Development Guidelines

### Adding New Scripts

1. Choose appropriate directory based on function
2. Follow naming convention (prefer hyphens over underscores)  
3. Add usage documentation to script header
4. Update directory README.md
5. Add integration tests if applicable

### Modifying Existing Scripts

1. Test changes in development environment first
2. Maintain backward compatibility when possible
3. Update documentation for interface changes
4. Consider impact on Makefile and CI/CD

## Directory Details

See individual README.md files in each directory for detailed information:

- [ADR/README.md](ADR/README.md) - Architecture Decision Records
- [build/README.md](build/README.md) - Build and CI pipeline
- [deploy/README.md](deploy/README.md) - Deployment orchestration  
- [diag/README.md](diag/README.md) - Diagnostics collection
- [evidence/README.md](evidence/README.md) - Evidence and attestation
- [release/README.md](release/README.md) - Release management
- [utils/README.md](utils/README.md) - Utilities and helpers
- [validation/README.md](validation/README.md) - Quality and compliance
- [workspace/README.md](workspace/README.md) - Workspace management

---

*This directory structure follows ADR-0019 three-tier documentation taxonomy and supports the complete HA-BB8 addon development and operational lifecycle.*