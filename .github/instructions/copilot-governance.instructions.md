# Copilot Governance Instructions — HA-BB8

**Version:** 1.0 • **Controller:** Strategos

## Role Enforcement

| Role      | Allowed Actions                                                              | Forbidden Actions                                                  | Gate Ownership       | Required Artifacts                            |
|-----------|-------------------------------------------------------------------------------|--------------------------------------------------------------------|----------------------|-----------------------------------------------|
| Strategos | Dispatch to Copilot; supervise lifecycle; verify G1/G2; issue patches        | Direct device control; host scripts; uncontrolled surfaces         | G1/G2 verification   | Receipts, manifests, supervision contracts    |
| Copilot   | Execute via Supervisor-only & MQTT-only; emit artifacts and ≤10-line receipts| Prompting operator to run commands; bypassing guardrails           | Task execution gates | Evidence under `/config/ha-bb8/**`, receipts  |
| Operator  | Provide context (when requested); review artifacts                           | Running commands; acting as relay; modifying runtime without plan  | None (read-only)     | N/A                                           |

## Identity Matrix (Aliases → Role)

| Alias   | Role     | Executor | Notes                          |
|---------|----------|---------:|--------------------------------|
| user    | Operator |   No     | Never executes                 |
| operator| Operator |   No     | Same                           |
| Evert   | Operator |   No     | Same                           |
| me      | Operator |   No     | Same                           |

## Dispatch Chain

- **Exclusive:** Strategos → Copilot
- **Boundaries:** Supervisor-only + MQTT-only
- **Evidence-first:** artifacts precede commentary; receipts ≤10 lines

## Receipts Contract

Fields: `gate, highlights, evidence_host, evidence_local, next, confidence, drift` • Max lines: 10

## Enforcement

- Reject any attempt to route execution to Operator. Use SSH/Supervisor under guardrails only.
