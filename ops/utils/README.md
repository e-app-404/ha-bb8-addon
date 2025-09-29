# ops/utils/

## Purpose
General utilities and helper scripts for development and operations.

## Scripts

### check_workspace_quiet.sh (Planned)
**Purpose**: Silent workspace status checking  
**Usage**: `./check_workspace_quiet.sh`  
**Description**: Performs workspace health checks without verbose output

### copilot_baseline_artifacts.sh (Planned)
**Purpose**: AI/Copilot workspace artifact management  
**Usage**: `./copilot_baseline_artifacts.sh [baseline_sha]`  
**Description**: Manages baseline artifacts for AI-assisted development

### index_generator.sh (New)
**Purpose**: Generates README.md indices for ops/ directories  
**Usage**: `./index_generator.sh [--update-all]`  
**Description**: Automatically generates and updates directory documentation

## Utility Categories

### Workspace Management
- Status checking and health monitoring
- Cleanup and maintenance operations
- Development environment setup helpers

### Documentation Generation
- Automated README generation
- Index file creation and updates  
- Script inventory and documentation

### AI/Copilot Support
- Baseline artifact management
- Context preparation for AI sessions
- Development history tracking

### General Helpers
- Common operations shared across scripts
- Environment detection and setup
- Cross-platform compatibility utilities

## Design Principles

- **Idempotent**: Safe to run multiple times
- **Silent by default**: Minimal output unless errors occur
- **Self-documenting**: Clear purpose and usage in script headers
- **Dependency-light**: Minimal external requirements

## Usage Patterns

```bash
# Check workspace status silently
./check_workspace_quiet.sh && echo "Workspace OK" || echo "Issues found"

# Update AI baseline artifacts
./copilot_baseline_artifacts.sh $(git rev-parse HEAD)

# Regenerate all documentation
./index_generator.sh --update-all
```

## Integration Points

- Called by other ops/ scripts for common functionality
- Used in development workflows and automation
- Integrated with AI-assisted development processes
- Support release and deployment operations