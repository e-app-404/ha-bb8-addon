# Environment Variable Governance (ADR-0024 Companion)

**Status:** Draft
**Created:** 2025-10-07
**ADR Alignment:** [ADR-0024 Canonical Config Path](../docs/ADR/ADR-0024-canonical-config-path.md)
**Scope:** HA-BB8 Add-on Repository `.env` standardization

## Overview

This document provides governance for environment variables in the HA-BB8 add-on repository, ensuring compliance with ADR-0024's canonical path requirements and proper separation of secrets from configuration.

## Canonical Variable Map

### Core Path Variables (REQUIRED)

```bash
# ADR-0024 Canonical Paths
export CONFIG_ROOT=/config                    # Single source of truth for HA config root
export WORKSPACE_ROOT="${WORKSPACE_ROOT:-$PWD}" # Repository operations root

# Hestia Structure (derived from CONFIG_ROOT)
export DIR_HESTIA="$CONFIG_ROOT/hestia"
export DIR_PACKAGES="$CONFIG_ROOT/packages"
export DIR_DOMAIN="$CONFIG_ROOT/domain"       # NOTE: singular, not "domains"
export HA_INCLUDES_DIR="$CONFIG_ROOT/includes"

# Hestia Four-Pillar Layout
export HESTIA_CONFIG="$DIR_HESTIA/config"
export HESTIA_LIBRARY="$DIR_HESTIA/library"
export HESTIA_TOOLS="$DIR_HESTIA/tools"      # Scripts live here per ADR-0024
export HESTIA_WORKSPACE="$DIR_HESTIA/workspace"

# Hestia Key Subdirectories
export HESTIA_ADR="$HESTIA_LIBRARY/docs/ADR"
export HESTIA_PLAYBOOKS="$HESTIA_LIBRARY/docs/playbooks"
export HESTIA_BLUEPRINTS="$HESTIA_LIBRARY/blueprints"  # NOT templates/blueprints
export HESTIA_DEVICES="$HESTIA_CONFIG/devices"
export HESTIA_NETWORK="$HESTIA_CONFIG/network"
export HESTIA_VAULT="$HESTIA_WORKSPACE/archive/vault"
export HESTIA_CACHE="$HESTIA_WORKSPACE/cache"
export HESTIA_SCRATCH="$HESTIA_CACHE/scratch"
export HESTIA_PROMPTS="$HESTIA_LIBRARY/prompts"
export HESTIA_GOVERNANCE="$HESTIA_LIBRARY/docs/governance"
export HESTIA_TODO="$HESTIA_WORKSPACE/todo"
export HESTIA_LOGS="$HESTIA_WORKSPACE/operations/logs"
export HESTIA_SCRIPTS="$HESTIA_TOOLS/scripts"
export HESTIA_UTILS="$HESTIA_TOOLS/utils"

# Template System
export TEMPLATE_CANONICAL="$CONFIG_ROOT/custom_templates/template.library.jinja"
```

### BB8 Add-on Variables (Repository-scoped)

```bash
# BB8 Repository Structure
export BB8_ROOT="${BB8_ROOT:-$WORKSPACE_ROOT}"
export BB8_CORE_DIR="${BB8_CORE_DIR:-$BB8_ROOT/bb8_core}"  # Note: lowercase per codebase
export BB8_TESTS_DIR="${BB8_TESTS_DIR:-$BB8_ROOT/tests}"
export BB8_REPORTS_DIR="${BB8_REPORTS_DIR:-$BB8_ROOT/reports}"

# BB8 Operations & Checkpoints
export BB8_QA_OPS_DIR="${BB8_QA_OPS_DIR:-$BB8_ROOT/ops/qa}"
export BB8_QA_LOGDIR="${BB8_QA_LOGDIR:-$BB8_REPORTS_DIR/latest/qa_logs}"
export BB8_QA_CHECKPOINTS_DIR="${BB8_QA_CHECKPOINTS_DIR:-$BB8_REPORTS_DIR/checkpoints}"
export BB8_HA_INT_CONTROL="$BB8_ROOT/reports/checkpoints/INT-HA-CONTROL"
export CHECKPOINT_DIR="$BB8_ROOT/reports/checkpoints/INT-HA-CONTROL"

# BB8 Documentation
export BB8_DOCS_ADR_DIR="${BB8_DOCS_ADR_DIR:-$BB8_ROOT/docs/ADR}"
```

### HA Deployment Variables

```bash
# SSH & Remote Access
export HA_SSH_HOST_ALIAS=home-assistant
export HA_SSH_USER=babylon-babes
export HA_SSH_HASS="ssh hass"

# HA Add-on Deployment (ADR-0024 compliant paths)
export HA_REMOTE_SCRIPT="/config/hestia/tools/addons_runtime_fetch.sh"  # Scripts in hestia/tools
export HA_REMOTE_RUNTIME=/addons/local/beep_boop_bb8
export HA_REMOTE_SLUG=local_beep_boop_bb8
export HA_SECRETS_PATH=/addons/local/beep_boop_bb8/secrets.yaml

# HA API Configuration (non-secret portions)
export HA_URL="http://192.168.0.129:8123"
export HA_LLAT_KEY=HA_LLAT_KEY  # Key name in secrets.yaml (actual token in .evidence.env)
export HA_API_CANDIDATES="http://homeassistant:8123 https://homeassistant:8123 http://homeassistant.local:8123 https://homeassistant.local:8123 http://172.30.32.1:8123 https://172.30.32.1:8123"
```

### Multi-Repository Convenience Variables

```bash
# ADR Cross-references (read-only mounts in VS Code)
export ADR_HA_Hestia="$HESTIA_ADR"
export ADR_HA_Omega="$OMEGA_ADR_DIR"  # When Omega workspace is open
export ADR_BB8="$BB8_DOCS_ADR_DIR"

# Repository Root Detection
export OMEGA_ROOT="${OMEGA_ROOT:-$WORKSPACE_ROOT}"  # Override when in Omega workspace
export OMEGA_ADR_DIR="${OMEGA_ADR_DIR:-$OMEGA_ROOT/project/docs/ADR}"
```

## Prohibited Variables in `.env`

### MUST NOT be in `.env` (keep in `.evidence.env` only)

```bash
# MQTT Credentials & Test Configuration
MQTT_HOST=*
MQTT_PORT=*
MQTT_USER=*
MQTT_PASSWORD=*
MQTT_BASE=*
REQUIRE_DEVICE_ECHO=*
ENABLE_BRIDGE_TELEMETRY=*
EVIDENCE_TIMEOUT_SEC=*

# HA Authentication Tokens
HA_LLAT_KEY=<actual_token>  # Key name OK in .env, actual token in .evidence.env
HA_TOKEN=*
HA_LONG_LIVED_ACCESS_TOKEN=*

# Any other credentials, passwords, API keys
```

### DEPRECATED (remove from `.env`)

```bash
# Non-canonical path roots (ADR-0024 violation)
HA_MOUNT=*           # Replace with CONFIG_ROOT=/config
HA_MOUNT_OPERATOR=*  # Replace with CONFIG_ROOT=/config
CONFIG_MOUNT=*       # Replace with CONFIG_ROOT=/config

# Host-dependent roots (keep WORKSPACE_ROOT only)
PROJECTS_ROOT=*      # Keep for repo ops but not in HA path derivations
```

## Migration Plan

### Phase 1: Safe Additions (Non-breaking)

```bash
# Add canonical root
echo 'export CONFIG_ROOT=/config' >> .env

# Add corrected paths
sed -i.bak 's/DIR_DOMAINS=/DIR_DOMAIN=/' .env
sed -i.bak 's|templates/blueprints|blueprints|g' .env
sed -i.bak 's|domain/shell_commands/addons_runtime_fetch.sh|hestia/tools/addons_runtime_fetch.sh|' .env
```

### Phase 2: Secret Migration (Manual)

1. **Review `.evidence.env`** - ensure it contains all MQTT/auth secrets:
   ```bash
   grep -E '^(MQTT_|HA_TOKEN|HA_LLAT_KEY=ey)' .evidence.env
   ```

2. **Remove secrets from `.env`**:
   ```bash
   sed -i.bak '/^MQTT_/d; /^HA_TOKEN=/d; /^HA_LLAT_KEY=ey/d; /^REQUIRE_DEVICE_ECHO=/d; /^ENABLE_BRIDGE_TELEMETRY=/d; /^EVIDENCE_TIMEOUT_SEC=/d' .env
   ```

3. **Update variable references** in scripts:
   ```bash
   # Replace HA_MOUNT usage with CONFIG_ROOT
   find ops/ -name "*.sh" -exec sed -i.bak 's|\$HA_MOUNT|\$CONFIG_ROOT|g' {} \;
   find ops/ -name "*.sh" -exec sed -i.bak 's|\${HA_MOUNT}|\${CONFIG_ROOT}|g' {} \;
   ```

### Phase 3: Cleanup (Remove deprecated)

```bash
# Remove deprecated variables
sed -i.bak '/^export HA_MOUNT=/d; /^export HA_MOUNT_OPERATOR=/d; /^export CONFIG_MOUNT=/d' .env
```

### Rollback Plan

All migration steps create `.bak` files. To rollback:

```bash
# Restore from backup
mv .env.bak .env

# Or selective rollback
git checkout HEAD -- .env
```

## Validation & Compliance

### Automated Validation

```bash
# Run governance check
make env-validate

# Print normalized variables
make env-print

# CI preflight check
ops/env/env_governance_check.sh
```

### Manual Validation Checklist

- [ ] **No secrets in `.env`**: `grep -E '(MQTT_|TOKEN|PASSWORD)' .env` returns empty
- [ ] **CONFIG_ROOT defined**: `grep '^export CONFIG_ROOT=/config' .env`
- [ ] **No deprecated roots**: `grep -E '(HA_MOUNT|CONFIG_MOUNT)' .env` returns empty
- [ ] **Correct path names**: `grep 'DIR_DOMAIN=' .env` (not DIR_DOMAINS)
- [ ] **Blueprint path fixed**: `grep 'HESTIA_BLUEPRINTS.*blueprints"' .env` (not templates/blueprints)
- [ ] **Script in hestia/tools**: `grep 'HA_REMOTE_SCRIPT.*hestia/tools' .env`
- [ ] **BB8 checkpoint paths**: `grep 'INT-HA-CONTROL' .env` points to reports/checkpoints/
- [ ] **Evidence env separate**: `.evidence.env` contains MQTT creds, not `.env`

### Integration Points

#### Makefile Targets

```make
env-print:
	@echo "CONFIG_ROOT=$${CONFIG_ROOT:-/config}"
	@grep -E '^(export )?[A-Z0-9_]+=' .env | sed 's/^export //'

env-validate:
	@bash ops/env/env_governance_check.sh | tee reports/checkpoints/ENV-GOV/env_validate.out
```

#### Pre-commit Hook

```yaml
- repo: local
  hooks:
    - id: env-governance
      name: ENV Governance Check
      entry: ops/env/env_governance_check.sh
      language: system
      files: '^\.env$'
      pass_filenames: false
```

#### CI/CD Integration

```yaml
- name: ENV Governance Check
  run: |
    source .env
    ops/env/env_governance_check.sh
    make env-validate
```

## Do's and Don'ts

### ✅ DO

- **Use CONFIG_ROOT=/config** as the single source of truth for HA config root
- **Derive all HA paths** from CONFIG_ROOT (e.g., `$CONFIG_ROOT/hestia`, `$CONFIG_ROOT/domain`)
- **Keep secrets in `.evidence.env`** - MQTT creds, tokens, test config
- **Use WORKSPACE_ROOT** for repository-scoped operations and paths
- **Place scripts in hestia/tools/** - shell_command.yaml files only declare HA entries
- **Validate with `make env-validate`** before committing .env changes
- **Use singular path names** - DIR_DOMAIN not DIR_DOMAINS
- **Document path derivations** - show how variables build from CONFIG_ROOT

### ❌ DON'T

- **Put secrets in `.env`** - no MQTT passwords, tokens, or test credentials
- **Use host-dependent paths** in HA config derivations (HA_MOUNT, ~/hass, $HOME/hass)
- **Hardcode non-canonical roots** - everything HA-related derives from CONFIG_ROOT
- **Put scripts in domain/shell_commands/** - that's for declarative YAML only
- **Use plural path names** inconsistently - prefer singular (domain not domains)
- **Mix repository paths with HA config paths** - keep WORKSPACE_ROOT and CONFIG_ROOT separate
- **Skip validation** - always run env-validate after changes
- **Commit .evidence.env** - it should remain local and excluded from git

## Implementation Status

- [ ] **ENV governance doc created** (this document)
- [ ] **Governance assessment JSON** generated
- [ ] **Non-destructive diff proposal** created
- [ ] **Validator script** implemented
- [ ] **Makefile targets** added
- [ ] **Migration executed** (requires approval)
- [ ] **CI integration** implemented
- [ ] **Documentation updated** across repository

## Related Documentation

- [ADR-0024: Canonical Config Path](../docs/ADR/ADR-0024-canonical-config-path.md) - Foundational path standardization
- [.evidence.env](./.evidence.env) - Secrets and test configuration (local only)
- [Makefile](./Makefile) - Build targets including env-validate
- [ops/env/env_governance_check.sh](./ops/env/env_governance_check.sh) - Validation script

---

**Next Steps:** Review governance assessment report and diff proposal in `reports/checkpoints/ENV-GOV/` before implementing changes.
