# Architectural Decision Records (ADRs)

This directory contains all architectural decision records for the HA-BB8 Home Assistant add-on project.

## ADR Index

- [ADR-0001] Canonical Topology — Dual-Clone via Git Remote (Short)
- [ADR-0002] Dependency & Runtime Compatibility Policy
- [ADR-0003] Home Assistant Add-on Local Build & Slug Management
- [ADR-0004] Conditional Runtime Tools Policy (CRTP) & Workspace Drift Enforcement
- [ADR-0005] Development Setup (legacy)
- [ADR-0006] Helper Functions Migration (legacy)
- [ADR-0007] Restore add-on working tree into ./addon (Canonical) (legacy)
- [ADR-0008] End-to-End Development → Deploy Flow (Dual‑Clone & HA Supervisor)
- [ADR-0009] ADR Governance, Redaction, and Formatting Policy
- [ADR-0010] Unified Supervision & DIAG Instrumentation
- [ADR-0011] Supervisor-only Operations
- [ADR-0012] Canonical module layout & imports
- [ADR-0013] Keep all app/ scripts and diagnostics in addon/app/
- [ADR-0014] Canonical Project Setup for HA-BB8 Addon
- [ADR-0015] Snapshot & Inventory Policy
- [ADR-0016] Coverage & seam policy
- [ADR-0017] Branch & Rescue Protocol
- [ADR-0018] Mass-Deletion Guard
- [ADR-0019] Workspace folder taxonomy and assignation rules
- [ADR-0020] Motion Safety & MQTT Contract
- [ADR-0021] Patch Etiquette & Session Guidelines
- [ADR-0022] Protocol Enforcement (Topics, Imports, Shape)
- [ADR-0023] Guardrails to prevent mass-deletion and accidental backup commits
- [ADR-0024] Workspace Hygiene (BB-8 add-on) — Adoption with repo-specific overrides
- [ADR-0025] Canonical repo layout for HA BB-8 add-on (package lives under addon/)
- [ADR-0026] Backups, inventory, and retention policy for BB-8 add-on
- [ADR-0027] Hygiene gate CI and required status checks
- [ADR-0028] Remote triad, backups, and mirror cutover policy
- [ADR-0029] Restore staging protocol and receipts
- [ADR-0030] Cross-Repository ADR Alignment and Linking Standard
- [ADR-0031] Supervisor-only Operations & Testing Protocol
- [ADR-0032] MQTT/BLE Integration Architecture
- [ADR-0033] Dual-Clone Deployment Topology & Git Hygiene
- [ADR-0034] HA OS Infrastructure Knowledge & Runtime Environment
- [ADR-0035] OOM Prevention & Echo Load Management
- [ADR-0036] AI Model Selection & Governance Framework
- [ADR-0037] MQTT Discovery Device Block Compliance
- [ADR-0038] Test Coverage Measurement Framework
- [ADR-0039] Functional Coverage Framework
- [ADR-0040] Layered Deployment Model for Testing & Version Provenance
- [ADR-0041] Centralized Environment Configuration & Accessible Secrets Management

## Status Legend

- **Accepted**: Active and enforced
- **Draft**: Under development
- **Proposed**: Ready for review
- **Deprecated**: No longer recommended
- **Superseded**: Replaced by newer ADR
- **Informational**: Legacy reference

## Template

Use [ADR-template.md](ADR-template.md) for new ADRs.

[ADR-0001]: ADR-0001-workspace-topology.md
[ADR-0002]: ADR-0002-dependency-policy.md
[ADR-0003]: ADR-0003-addon-local-build-patterns.md
[ADR-0004]: ADR-0004-runtime-tools-policy.md
[ADR-0005]: ADR-0005-development-setup.md
[ADR-0006]: ADR-0006-helpers-migration.md
[ADR-0007]: ADR-0007-restore-addon.md
[ADR-0008]: ADR-0008-end-to-end-flow.md
[ADR-0009]: ADR-0009-adr-governance-formatting.md
[ADR-0010]: ADR-0010-unified-supervision-and-diag.md
[ADR-0011]: ADR-0011-supervisor-only-ops.md
[ADR-0012]: ADR-0012-repo-layout-and-imports.md
[ADR-0013]: ADR-0013-keep-addon-app.md
[ADR-0014]: ADR-0014-canonical-project-setup.md
[ADR-0015]: ADR-0015-snapshot-and-inventory-policy.md
[ADR-0016]: ADR-0016-coverage-and-seam-policy.md
[ADR-0017]: ADR-0017-branch-rescue-protocol.md
[ADR-0018]: ADR-0018-mass-deletion-guard.md
[ADR-0019]: ADR-0019-workspace-folder-taxonomy.md
[ADR-0020]: ADR-0020-motion-safety-and-mqtt-contract.md
[ADR-0021]: ADR-0021-patch-etiquette.md
[ADR-0022]: ADR-0022-protocol-enforcement.md
[ADR-0023]: ADR-0023-guardrails-mass-deletion.md
[ADR-0024]: ADR-0024-workspace-hygiene-bb8-addon.md
[ADR-0025]: ADR-0025-canonical-repo-layout-bb8-addon.md
[ADR-0026]: ADR-0026-backups-inventory-and-retention.md
[ADR-0027]: ADR-0027-hygiene-gate-and-status-checks.md
[ADR-0028]: ADR-0028-remotes-and-mirror-cutover-policy.md
[ADR-0029]: ADR-0029-restore-staging-and-receipts.md
[ADR-0030]: ADR-0030-cross-repository-adr-alignment.md
[ADR-0031]: ADR-0031-supervisor-only-operations-testing.md
[ADR-0032]: ADR-0032-mqtt-ble-integration-architecture.md
[ADR-0033]: ADR-0033-dual-clone-topology-git-hygiene.md
[ADR-0034]: ADR-0034-ha-os-infrastructure.md
[ADR-0035]: ADR-0035-oom-prevention-echo-load-management.md
[ADR-0036]: ADR-0036-ai-model-selection-governance.md
[ADR-0037]: ADR-0037-mqtt-discovery-device-block-compliance.md
[ADR-0038]: ADR-0038-test-coverage-measurement-framework.md
[ADR-0039]: ADR-0039-functional-coverage-framework.md
[ADR-0040]: ADR-0040-layered-deployment-model-for-testing.md
[ADR-0041]: ADR-0041-centralized-environment-configuration.md