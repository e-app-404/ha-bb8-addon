# Missing ADRs for HA BB-8 Add-on

Based on my comprehensive investigation of the HA BB-8 add-on repository, I recommend canonicalizing the following information into ADR form to capture critical operational knowledge and decision rationale:

## High-Priority ADR Recommendations

### 1. **ADR-XXXX: Home Assistant Add-on Testing & Validation Protocol**
**Rationale**: The testing methodology I developed reveals complex interdependencies between build, deployment, banner debugging, and validation that aren't documented anywhere.

**Should canonicalize**:
- Exact banner message patterns that indicate successful startup
- Required log sequences for pass/fail determination  
- Specific diagnostic collection procedures
- Network connectivity test protocols (MQTT, BLE, API)
- Container health validation steps

**Current gap**: Testing is ad-hoc; no canonical acceptance criteria exist.

### 2. **ADR-XXXX: Add-on Deployment Topology & SSH Operations** 
**Rationale**: Multiple deployment methods exist (rsync, SSH, UI, API) but no guidance on when to use each.

**Should canonicalize**:
- Four deployment strategies with specific use cases
- SSH authentication requirements and security model
- Rollback procedures and backup strategies  
- Version synchronization between workspace and runtime
- Risk mitigation for production deployments

**Current gap**: Makefile references missing `ops/release/` scripts; deployment knowledge is scattered.

### 3. **ADR-XXXX: Container Supervision & Process Management**
**Rationale**: The run.sh analysis reveals sophisticated dual-supervision logic (run.sh vs S6) that could confuse operators.

**Should canonicalize**:
- When run.sh spawns echo_responder vs when S6 manages it
- Restart loop behavior and RESTART_LIMIT policies
- Health heartbeat file locations and freshness criteria
- Signal handling (SIGTERM/SIGINT) and graceful shutdown
- Debug tracing activation (`DIAG_TRACE=1`) procedures

**Current gap**: ADR-0010 mentions supervision but not the dual-control-plane complexity.

### 4. **ADR-XXXX: MQTT Integration Architecture & Troubleshooting**
**Rationale**: MQTT connectivity is critical but failure modes aren't well documented.

**Should canonicalize**:
- MQTT broker connectivity prerequisites and validation
- Home Assistant discovery topic patterns and timing
- Authentication failure vs network failure diagnostics
- Retry/reconnection behavior and backoff strategies
- Echo responder command/response flow validation

**Current gap**: MQTT details are in code comments, not architectural decisions.

### 5. **ADR-XXXX: BLE Hardware Access & Permissions Model**
**Rationale**: BLE device access requires specific container privileges that impact security.

**Should canonicalize**:
- Required `udev: true`, `privileged: [NET_ADMIN]`, `devices: [/dev/hci0]` rationale
- BLE adapter detection and validation procedures
- Permission denied troubleshooting (most common failure)
- Multi-adapter scenarios and adapter selection logic
- Container vs host BLE stack interaction

**Current gap**: BLE requirements scattered across config.yaml and troubleshooting.

## Medium-Priority ADR Recommendations

### 6. **ADR-XXXX: Add-on Configuration Schema & Validation**
**Rationale**: 40+ configuration options with legacy field fallbacks create complexity.

**Should canonicalize**:
- Canonical vs legacy field mappings (`mqtt_host` vs `mqtt_broker`)
- Required vs optional configuration with defaults
- Configuration validation and error messaging standards
- Schema evolution strategy for backward compatibility

### 7. **ADR-XXXX: Logging, Diagnostics & Observability Standards**
**Rationale**: Multiple log outputs (stdout, file, health heartbeats) need coordination.

**Should canonicalize**:
- Log redaction patterns for sensitive data (from logging_setup.py)
- Structured vs unstructured logging for operator tools
- Diagnostics collection automation and retention
- Telemetry data collection policies and privacy considerations

### 8. **ADR-XXXX: Build System Architecture & Multi-Arch Support**
**Rationale**: Complex build.yaml + Dockerfile + Makefile interdependencies.

**Should canonicalize**:
- Local build vs registry pull decision criteria
- Multi-architecture build strategy (aarch64 primary)
- Version injection mechanisms (`BUILD_VERSION` arg)
- Build caching and optimization strategies

## Implementation Strategy

### Phase 1: Critical Operational ADRs
Start with **Testing & Validation Protocol** and **Deployment Topology** since these directly impact operator success and are currently undocumented.

### Phase 2: Technical Architecture ADRs  
Follow with **Container Supervision** and **MQTT Integration** to capture complex behavioral decisions.

### Phase 3: Supporting Infrastructure ADRs
Complete with **BLE Hardware Access** and configuration/logging standards.

## ADR Content Structure Recommendation

Each ADR should include:

**Context**: What problem does this solve? What alternatives were considered?

**Decision**: Specific technical choices made (exact commands, file paths, message patterns)

**Consequences**: Operational impact, troubleshooting implications, maintenance burden

**Implementation**: Copy-paste ready commands and scripts for operators

**Examples**: Real log outputs, successful test runs, failure scenarios

**Related**: Cross-references to existing ADRs (especially ADR-0003, ADR-0008, ADR-0010)

This approach would transform the scattered operational knowledge I discovered into canonical, searchable, maintainable architectural decisions that future operators and maintainers can rely on.