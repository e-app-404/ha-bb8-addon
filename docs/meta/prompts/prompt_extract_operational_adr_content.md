# ChatGPT Prompt: Extract Operational ADR Content from Session

## Instructions for ChatGPT Assistant

You are tasked with extracting empirically verifiable architectural decisions and operational knowledge from an active conversation/session for canonicalization into Architectural Decision Records (ADRs). 

**CRITICAL CONSTRAINTS:**
- Extract ONLY information that was explicitly discovered, tested, or verified in the session
- Do NOT invent, assume, or extrapolate information that wasn't directly observed
- Include exact commands, file paths, log messages, and outputs only if they appeared in the conversation
- Cite specific conversation points where information was gathered
- Mark any gaps or missing information explicitly

## Target ADR Categories

Based on the session analysis, focus on these ADR categories if evidence exists:

### 1. Testing & Validation Protocol
**Extract if present:**
- Exact banner message patterns observed in logs
- Specific command sequences that were executed and their results
- Pass/fail criteria that were actually tested
- Diagnostic collection procedures that were implemented
- Network connectivity tests that were performed

**Required evidence:** Actual log outputs, command executions, test results

### 2. Deployment Topology & Operations  
**Extract if present:**
- Deployment methods that were actually used or referenced
- SSH commands that were executed or documented in files
- Version synchronization procedures that were observed
- Rollback strategies that were implemented or tested
- Risk assessments based on actual operational experience

**Required evidence:** Working commands, file configurations, deployment receipts

### 3. Container Supervision & Process Management
**Extract if present:**
- Process management logic discovered in source code analysis
- Supervision patterns observed in configuration files
- Restart behaviors documented in scripts
- Health check mechanisms found in implementation
- Signal handling discovered in code review

**Required evidence:** Source code excerpts, configuration files, script analysis

### 4. Integration Architecture (MQTT/BLE/API)
**Extract if present:**
- Connection patterns discovered in configuration
- Authentication mechanisms found in code
- Error handling observed in implementation
- Protocol specifications extracted from source
- Hardware requirements discovered in manifests

**Required evidence:** Config files, source code, manifest specifications

## Output Format Template

```markdown
# ADR-XXXX: [Title from session context]

**Session Evidence Source:** [Conversation timestamp/section where this was discovered]

## Context
[Only include context that was explicitly discussed or discovered in session]

**Problem Statement:** [What specific operational challenge was identified?]
**Investigation Method:** [How was this information discovered - code review, testing, file analysis?]
**Evidence Gathered:** [What concrete evidence supports this decision?]

## Decision
[Only include decisions that were made or validated during the session]

**Technical Choice:** [Specific implementation that was observed/tested]
**Command/Configuration:** [Exact commands, file contents, or configurations discovered]
**Validation Results:** [Actual test outcomes, if any were performed]

## Consequences

### Positive
- [Benefits observed during investigation]
- [Operational improvements validated]

### Negative  
- [Limitations discovered during analysis]
- [Operational complexities identified]

### Unknown/Untested
- [Aspects that require further investigation]
- [Gaps identified but not resolved]

## Implementation Evidence

### Commands Verified
```bash
[Only include commands that were actually executed or found in repository]
```

### Configuration Discovered
```yaml/json
[Only include configurations that were examined in session files]
```

### Log Patterns Observed
```
[Only include actual log outputs or patterns found in code]
```

## Gaps Requiring Further Investigation
- [Explicitly list what wasn't tested/verified]
- [Note assumptions that need validation]
- [Identify missing operational procedures]

## References
- **Source Files Examined:** [List actual files that were read/analyzed]
- **Commands Executed:** [List commands that were run with results]
- **Tests Performed:** [List validations that were actually done]
- **Session Sections:** [Reference conversation parts where evidence was gathered]

---
**Extraction Date:** [Current date]
**Session ID/Reference:** [Identifier for source conversation]
**Evidence Quality:** [Complete/Partial/Requires Validation]
```

## Extraction Guidelines

### DO Extract:
✅ File contents that were actually read and analyzed
✅ Commands that were executed with their outputs  
✅ Configuration patterns discovered in source code
✅ Architectural decisions evident from code structure
✅ Operational procedures that were implemented or tested
✅ Error patterns observed in logs or code
✅ Dependencies discovered through file analysis

### DO NOT Extract:
❌ Best practices not validated in this specific context
❌ Standard procedures not customized for this system
❌ Assumptions about how things "should" work
❌ Generic troubleshooting advice not tested here
❌ Configurations not present in the actual files examined
❌ Log patterns not observed in actual outputs
❌ Commands not executed or validated

### Quality Indicators

**HIGH QUALITY (Include):**
- Information backed by file contents, command outputs, or code analysis
- Decisions supported by multiple evidence sources
- Operational procedures actually implemented during session
- Troubleshooting validated through testing

**MEDIUM QUALITY (Include with caveats):**
- Logical inferences from code structure with clear reasoning
- Architectural patterns evident from file organization
- Dependencies inferred from configuration analysis

**LOW QUALITY (Mark as requiring validation):**
- Assumptions based on standard practices
- Extrapolations beyond observed evidence
- Generic recommendations not specific to this system

## Final Validation Checklist

Before submitting ADR content, verify:
- [ ] Every technical detail can be traced to session evidence
- [ ] All commands/configurations were actually observed in files or executed
- [ ] Gaps and unknowns are explicitly acknowledged
- [ ] No information was invented to complete the format
- [ ] Source references are specific and verifiable
- [ ] Quality assessment is honest about evidence strength

**Remember:** An incomplete ADR with verified information is more valuable than a complete ADR with unverified assumptions.