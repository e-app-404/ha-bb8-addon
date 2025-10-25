---
applyTo: '**'
description: >-
  Workspace memory for HA-BB8: distilled, reusable lessons from debugging, deploys,
  and evidence runs. Keep guidance concise, generalizable, and scoped to this repo.
---

# HA‑BB8 Workspace Memory

Lean, repeatable patterns to deploy, test, and evidence the BB‑8 add‑on without regressions.

## HA Host Evidence Confinement

- Always write operational artifacts on HA Host under `/config/ha-bb8/**`.
- For governed runs, place E2E/B5 evidence under `/config/ha-bb8/checkpoints/BB8-FUNC/<UTC_TS>/`.
- After collection, copy artifacts back to the repo at `reports/checkpoints/BB8-FUNC/<origin>/<UTC_TS>/`.
- Include a `manifest.sha256` file for every checkpoint directory (names and sha256 per file).

## Add-on Container Discovery (SSH helpers)

- Prefer exact slug-based match: `addon_local_beep_boop_bb8`.
- Fallback: grep container name/image for `bb8` then pick the first match deterministically.
- If not found, stop early and print `docker ps` table for operator visibility.
- Before running helpers, ensure the add-on is rebuilt and started:
  - `ha addons reload` → `ha addons rebuild local_beep_boop_bb8` → `ha addons start local_beep_boop_bb8`.

## MQTT Inside the Container (Paho v2)

- Use `core-mosquitto` for the broker hostname inside the HA add-on container.
- Derive the base topic from configuration/env; default base is `bb8`.
- Use Paho v2 callback API: `callback_api_version=CallbackAPIVersion.VERSION2`.
- Match on_connect signatures to the protocol:
  - MQTTv5: `on_connect(client, userdata, flags, reasonCode, properties=None)`
  - MQTTv311: `on_connect(client, userdata, flags, rc)`
- Subscribe to `bb8/ack/#` and `bb8/status/#` for command acks and telemetry.
- Record event timelines with ISO-8601 ms timestamps for evidence readability.

## SSH Deploy Flow (ADR‑0008 aligned)

- Sync runtime with rsync to `/addons/local/beep_boop_bb8/` using excludes (.git, __pycache__, caches).
- Ensure `.env` defines `HA_URL` for HA API restarts (when Supervisor token not available).
- Keep the LLAT token in `secrets.yaml` (key `HA_LLAT_KEY`), never print secrets.
- Restart preference order: Supervisor API (if `SUPERVISOR_TOKEN`) → HA Core API (`/api/services/hassio/addon_restart`).
- Verify success via HTTP 200 for HA API or `{"result":"ok"}` for Supervisor API responses.

## Alpine + venv Guardrails

- Alpine 3.22: do not install `py3-venv` (not a package). Use `apk add python3 py3-pip python3-dev`.
- Create venv at `/opt/venv` and `exec` it in `run.sh` or s6 run scripts.
- Avoid mixing multiple supervision models; production model is foreground single-proc with `run.sh` exec.

## MQTT Discovery Device Block (HA compliance)

- Include both `identifiers` and `connections` in every device block; never send `{ "device": {} }`.
- Derive identifiers from config (e.g., `bb8_mac`, `bb8_name`); publish to HA discovery topics with retained payloads.

## Inline Python for One‑shot Evidence Runs

- When helper scripts aren’t baked into the image, run inline Python via `docker exec` to avoid rebuilds.
- Keep the inline runner self-contained (Paho v2 only) and write evidence to `/config/ha-bb8/...`.
- Append an echo round‑trip health line to the summary to confirm post‑sequence stability.

## ENV Governance Cross‑cutting

- Use `CONFIG_ROOT=/config` as the canonical HA root; derive all HA paths from it.
- Keep secrets out of `.env` (store in `.evidence.env` or `secrets.yaml`).
- Use singular path names (e.g., `DIR_DOMAIN`) and centralized `.env` for deploy scripts.
