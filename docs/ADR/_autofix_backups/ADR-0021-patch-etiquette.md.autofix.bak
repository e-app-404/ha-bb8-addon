---
title: "ADR-0021: Patch Etiquette & Session Guidelines"
date: 2025-09-15
status: Accepted
author:
  - Evert Appels
  - Strategos GPT
related: []
supersedes: []
last_updated: 2025-09-15
---

# ADR-0021: Patch Etiquette & Session Guidelines

## Context

## Guidelines

- Keep patches small & reversible; each adds unit + FakeMQTT E2E tests.
- No prod files outside `addon/**`. Root `bb8_core/`, `services.d/`, `tools/` forbidden.
- MQTT: no wildcards in cmd/state; sanitize & test.
- Motion tests skip unless env enables motion.
- Discovery must be idempotent; guard set tracked to prevent duplicates.
- CI gates: repo-shape, protocol, coverage ≥ 70%, snapshot-policy dry-run.
- Commit format: `feat|fix|chore(scope): summary`.

## Token Blocks