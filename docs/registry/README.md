# BB‑8 Ops Tooling Registry

Curated, repo‑local reference for day‑to‑day developer and operator commands. These docs keep the command surface deterministic, Supervisor‑first, and MQTT‑only. No scripts here write to HA host paths.

Contents:
- `cli.toml` — common CLI commands (Make, pytest, evidence) with purpose and safety
- `BB8-ops-toolset.toml` — repo‑local helper scripts with arguments and defaults
- `mqtt.toml` — canonical MQTT topics and scoped purge patterns

Related guides:
- `../bb8-workspace-instructions.md` — developer quickstart with governance and commands
- `../GOVERNANCE.md` — consolidated guardrails, acceptance gates, and CI checks

Quick links:
- Make coverage HTML: `make cov-html`
- Restart add‑on (Supervisor‑first): `make ha-restart`
- Env governance check: `make env-validate`
- Fast tests: `pytest -q addon/tests -k 'not slow'`
- Evidence STP4: `make evidence-stp4`
- MQTT discovery purge (dry‑run default): `bash ops/diag/mqtt_purge_discovery.sh --device-id <id> --dry-run`

Safety defaults:
- Purge helper requires both `--device-id` and `--execute` to perform destructive operations; otherwise it stays in dry‑run.
- Restart helper is Supervisor‑first and does not print secrets.

Update policy: keep these files in sync when adding new Make targets, VS Code tasks, or helper scripts.
