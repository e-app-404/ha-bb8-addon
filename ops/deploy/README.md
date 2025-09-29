# ops/deploy/

## Purpose
Deployment orchestration and environment management scripts.

## Scripts

### deploy_dual_clone.sh (Planned)
**Purpose**: Dual-clone deployment model implementation  
**Usage**: `./deploy_dual_clone.sh`  
**Description**: Implements ADR-0001 dual-clone deployment topology

### deploy_workspace.sh (Planned) 
**Purpose**: Workspace deployment and synchronization  
**Usage**: `./deploy_workspace.sh [target]`  
**Description**: Deploys workspace changes to target environment

### accept_runtime_canonical.sh (Planned)
**Purpose**: Runtime canonicalization acceptance  
**Usage**: `./accept_runtime_canonical.sh`  
**Description**: Accepts and validates runtime canonical state

## Deployment Targets

- **Development**: Local development environment
- **Staging**: Home Assistant test instance  
- **Production**: Live Home Assistant instance (`192.168.0.129`)

## Environment Variables

- `REMOTE_HOST_ALIAS`: SSH alias for target (default: `home-assistant`)
- `REMOTE_RUNTIME`: Target runtime path (default: `/addons/local/beep_boop_bb8`)
- `TARGET_BRANCH`: Git branch for deployment (default: `main`)

## Security

- All scripts use SSH key authentication
- No secrets are logged or printed
- LLAT (Long-Lived Access Token) validation included
- Uses Home Assistant Supervisor API when available

## Workflow Integration

Called by:
- `make release-*` targets
- Manual deployment procedures
- CI/CD deployment stages
- Emergency deployment procedures