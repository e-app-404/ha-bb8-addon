# HA‑BB8 Governance (Operational and Developer Guardrails)

This document consolidates operational boundaries, acceptance criteria, and developer guardrails derived from ADR‑0031, ADR‑0040, and ENV governance.

## Operational boundaries (binding)

- Supervisor‑only lifecycle for acceptance flows (no container shell for acceptance).
- MQTT‑only testing surface (`bb8/cmd/*`, `bb8/ack/*`, `bb8/status/*`).
- Evidence‑first: deterministic artifacts under governed paths with manifests.
- Write confinement: container → `/data/**`; HA host evidence → `/config/ha-bb8/**`.

## Environment governance

- Canonical HA root: `CONFIG_ROOT=/config`; derive all HA paths from it.
- Secrets live in `.evidence.env` (never commit). `.env` holds non‑secret config only.
- In‑container broker hostname: `core-mosquitto`.
- MQTT resolution precedence: ENV (`MQTT_HOST`) → options (`MQTT_HOST`/`mqtt_broker`) → default `core-mosquitto`.

## Acceptance gates (INT‑HA‑CONTROL)

- P0 stability: 120 min, 0 TypeError/coroutine errors.
- MQTT persistence: presence+rssi recover ≤10s after broker and HA Core restarts.
- Single‑owner discovery: no duplicates; valid device blocks with identifiers and connections.
- LED alignment: schema‑valid light entity, toggle‑gated.
- Config defaults proven: `MQTT_BASE=bb8`, `REQUIRE_DEVICE_ECHO=1`, `PUBLISH_LED_DISCOVERY=0`.

## QA and CI guardrails

- Lint/format/types: black, ruff, mypy.
- Tests: pytest with coverage (term‑missing). Target coverage: ≥80% on protected branches.
- Security (informative): bandit, safety — non‑blocking but recommended.
- Shape guard: enforce canonical `addon/` structure and key entrypoints.

## Prohibited and discouraged patterns

- Using `systemctl` for Mosquitto on HA OS in acceptance docs (prefer `ha addons restart core_mosquitto`).
- Host utility scripts outside `/config/hestia/tools`.
- Printing secrets in logs or evidence.

## Deterministic receipts (operator checklist)

- Supervisor status and logs include: `run.sh entry`, health summaries, MQTT connect/subscribed lines.
- MQTT echo health returns within SLA; discovery retained and well‑formed.
- Artifacts contain a SHA‑manifest and minimal, greppable JSON fields.

## References

- ADR‑0031: Supervisor‑only Operations & Testing Protocol
- ADR‑0040: Layered Deployment Model for Testing & Version Provenance
- ENV governance: `.github/instructions/env-governance.instructions.md`
