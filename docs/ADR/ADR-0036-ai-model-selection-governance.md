---
id: ADR-0036
title: AI Model Selection and Governance for Development Automation
date: 2025-09-28
status: Accepted
decision: '### Model Assignment Matrix **GPT-4o mini: Operational Excellence** - QA
  pipeline failures (make qa, make testcov, make security) - Code formatting and linting
  issues - Test coverage improvements and test file maintenance - Configuration updates
  and environment variable management - Evidence collect.'
author:
- Development Automation Analysis
- Copilot Claude
related:
- ADR-0009
- ADR-0019
- ADR-0031
supersedes: []
last_updated: 2025-09-28
tags:
- ai-models
- development-automation
- guardrails
- governance
- gpt
- claude
references:
- Existing copilot_claude_bb8_development_prompt.md patterns
- Model capability analysis from workspace session evidence
---

# ADR-0036: AI Model Selection and Governance for Development Automation

## Context

The HA-BB8 add-on development process extensively uses AI coding assistants, primarily GPT-4o mini and Claude Sonnet 3.5. Analysis of development session patterns reveals distinct capabilities and failure modes between models that require formal governance to optimize development velocity while maintaining code quality and ADR compliance.

### Problem Statement

Without formal model selection guidance:
- **Inefficient model usage**: Complex architectural analysis assigned to GPT-4o mini, simple fixes assigned to Claude Sonnet
- **ADR governance violations**: GPT-4o mini creating malformed ADRs without proper TOKEN_BLOCK sections
- **Context switching overhead**: No formal handoff protocol when switching between models mid-session
- **Quality inconsistency**: Different models applying different standards to code quality gates

### Evidence from Development Sessions

**GPT-4o mini strengths observed:**
- Rapid tool orchestration for `make qa` pipeline fixes
- Efficient batch operations across multiple test files
- Reliable pattern recognition for import violations and formatting
- Fast structured logging and configuration updates

**Claude Sonnet 3.5 strengths observed:**
- Comprehensive ADR authoring with proper governance compliance
- Deep architectural analysis across service boundaries
- Complex debugging of BLE/MQTT integration issues
- Long-context reasoning for cross-file dependency resolution

## Decision

### Model Assignment Matrix

**GPT-4o mini: Operational Excellence**
- QA pipeline failures (`make qa`, `make testcov`, `make security`)
- Code formatting and linting issues
- Test coverage improvements and test file maintenance
- Configuration updates and environment variable management
- Evidence collection (`make evidence-stp4`) troubleshooting
- Import structure violations and module organization
- Small-scope refactoring (≤3 files)

**Claude Sonnet 3.5: Architectural Leadership**
- ADR creation, modification, and governance compliance
- Cross-component architectural changes
- Service boundary modifications (bridge_controller, mqtt_dispatcher, facade)
- Complex debugging requiring deep system understanding
- Documentation requiring technical depth and context
- Long-context analysis spanning multiple subsystems
- Root cause analysis for integration failures

### Dynamic Switching Protocol

**Context Preservation Requirements:**
```yaml
HANDOFF_CONTEXT:
  milestone: <current development phase>
  model_transition: <from_model> → <to_model>
  modified_files: [<file paths>]
  test_status: <coverage/qa results>
  adr_context: [<relevant ADR IDs>]
  next_priority: <immediate next actions>
```

**Switching Triggers:**
- **To GPT-4o mini**: Task becomes repetitive, tool-heavy, or scope-limited
- **To Claude Sonnet**: Requires architectural decision, ADR work, or deep analysis

### Model-Specific Guardrails

**GPT-4o mini Constraints:**
```yaml
CONSTRAINTS:
  scope_limit: 3_files_max_per_session
  adr_prohibition: no_canonical_adr_creation
  architecture_freeze: no_service_boundary_changes
  evidence_mandatory: run_stp4_for_mqtt_changes
  test_coverage: maintain_80_percent_threshold
```

**Claude Sonnet 3.5 Constraints:**
```yaml
CONSTRAINTS:
  adr_governance: strict_adr_0009_compliance
  token_validation: mandatory_token_blocks
  cross_reference: verify_adr_relationships
  evidence_integration: incorporate_operational_data
  supersession_chain: maintain_adr_lineage
```

### Anti-Pattern Prevention

**GPT-4o mini Anti-Patterns:**
- Creating ADRs without YAML front-matter and TOKEN_BLOCK sections
- Architectural decisions without evidence collection
- Batch changes exceeding coverage thresholds
- Import violations (`bb8_core` instead of `addon.bb8_core`)
- Tool chaining without intermediate validation

**Claude Sonnet 3.5 Anti-Patterns:**
- Over-engineering simple fixes suited for GPT-4o mini
- Analysis paralysis on established patterns
- Verbose documentation where concise patterns exist
- Ignoring guardrails for "theoretical best practices"
- Creating ADRs without operational evidence integration

## Consequences

### Positive Outcomes
- **Development velocity**: Optimal model assignment reduces iteration cycles
- **Quality consistency**: Model-specific guardrails prevent common failure modes
- **ADR governance**: Formal constraints ensure proper architectural documentation
- **Context preservation**: Handoff protocol maintains session continuity

### Implementation Requirements
- Update `.github/copilot-instructions.md` with model selection guidance
- Establish handoff templates for context switching
- Integrate model constraints into existing guardrails
- Document anti-patterns in development workflow

### Operational Integration
- Model selection becomes part of milestone planning
- Context handoffs tracked in development logs
- Guardrail violations flagged in QA pipeline
- Evidence collection tied to model-specific constraints

## TOKEN_BLOCK

**Accepted**: AI_MODEL_GOVERNANCE, DYNAMIC_MODEL_SWITCHING, MODEL_SPECIFIC_GUARDRAILS, HANDOFF_PROTOCOL_ESTABLISHED
**Produces**: OPTIMIZED_DEVELOPMENT_VELOCITY, CONSISTENT_CODE_QUALITY, ADR_GOVERNANCE_COMPLIANCE
**Requires**: ADR_0009_FORMATTING_COMPLIANCE, COPILOT_INSTRUCTIONS_INTEGRATION, GUARDRAIL_FRAMEWORK
**Drift**: Model assignment confusion, context switching overhead, guardrail violations, ADR quality degradation