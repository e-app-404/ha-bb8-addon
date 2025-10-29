# BB-8 Workspace Instructions (Developer Quickstart)

This guide is a fast, governed onboarding for working in this repository. It keeps operations Supervisor-first, MQTT-only, and evidence-first, with zero secrets printed.

## Scope

- Repo: Home Assistant add-on for Sphero BB-8 (BLE + MQTT)
- You’ll run local QA/tests, build docs/evidence, and interact with the HA add-on via governed helpers.

## Layout essentials

- `addon/` — add-on runtime (Python), entrypoint `run.sh`, options `config.yaml`
- `addon/bb8_core/` — core modules (bridge, BLE, MQTT dispatcher, logging)
- `docs/` — ADRs, runbooks, registry; this file lives here
- `ops/` — repo-local helpers (diagnostics, evidence)
- `.vscode/` — tasks and extension recommendations

## Governance quickstart

- Supervisor-first operations; no host scripts outside `/config/hestia/tools`.
- Evidence confinement: add-on writes under `/data/**`; host evidence mirrors under `/config/ha-bb8/**`.
- ENV governance: use `CONFIG_ROOT=/config` for HA paths; keep secrets in `.evidence.env` (never commit).
- In-container broker hostname: `core-mosquitto` (do not hardcode external IPs in-container).

### ADR-0031 reinforcement (what this means in practice)

- Acceptance flows must operate Supervisor-only and MQTT-only. No container shell access, no non-Supervisor lifecycle.
- Evidence-first: every step creates deterministic artifacts (checkpoints, manifests) — never rely on verbal claims.
- Health is validated via MQTT echo and periodic summaries in logs; discovery uses proper device blocks.

### Broker policy (defaults and precedence)

- Resolution order: ENV (`MQTT_HOST`) → add-on options (`MQTT_HOST`/`mqtt_broker`) → default `core-mosquitto` in-container.
- Topics: default base is `bb8`; discovery prefix is `homeassistant`.
- Never print secrets; preview masked as `[MASKED]` only.

### Acceptance vs dev

- Acceptance: rebuild/restart strictly via Supervisor; evidence confined; MQTT-only probes; retained discovery.
- Dev: standalone runner acceptable for quick iteration; final acceptance still goes through Supervisor path.

## How to run (workstation)

- Create and load your local secrets (not committed):
```sh
set -a && source .evidence.env && set +a
```
- Quick QA (lint + types + tests):
```sh
make qa
```
- Fast tests only:
```sh
pytest -q addon/tests -k 'not slow'
```
- Coverage quick view (opens htmlcov best-effort):
```sh
make cov-html
```
- Evidence STP4 (MQTT-only, governed):
```sh
make evidence-stp4
```
- Restart add-on (Supervisor-first; HA API fallback):
```sh
make ha-restart
```
- MQTT discovery purge (dry-run by default):
```sh
bash ops/diag/mqtt_purge_discovery.sh --device-id <id> --dry-run
```

## MQTT topics and registry

- Default base: `bb8`; discovery prefix: `homeassistant`.
- Canonical topics and purge scope: see `docs/registry/mqtt.toml`.
- Common commands, QA, and evidence tasks: see `docs/registry/cli.toml`.

## Safety defaults

- Never print secrets. Mask previews like `MQTT_USER`, `MQTT_PASSWORD` as `[MASKED]`.
- Purge helper requires `--device-id` and `--execute` to perform destructive operations; otherwise it’s dry-run.

## Troubleshooting

- In-container DNS: `core-mosquitto` must resolve; on workstation, use your broker IP/hostname from `.evidence.env`.
- HA URL for workstation flows: set `HA_URL` in `.evidence.env` if you use HA API fallback.
- If Supervisor restart fails: retry `make ha-restart` or run the VS Code task “HA: Deploy over SSH” and then restart.

## References

- ADR-0031: Supervisor-only Operations & Testing Protocol
- ADR-0040: Layered Deployment Model for Testing & Version Provenance
- ENV governance: `.github/instructions/env-governance.instructions.md`
