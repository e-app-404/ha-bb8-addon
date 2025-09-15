# Strategos Session Guidelines & Patch Etiquette

**Goal:** keep conversations fast, accurate, and reproducible.

## Patch Etiquette

- Prefer **unified diffs** over full file drops.
- For JSON/YAML: **minify** unless readability is essential; include one representative object.
- For logs: include ≤150 lines, focused around the event; redact secrets; use timestamps.
- Avoid speculative code; provide **compilable** stubs with clear TODO markers.
- Use **feature flags** (env/options) when introducing optional behavior.

## Evidence & Acceptance

- Every phase requires evidence artifacts with paths and hashes where possible.
- STP4 roundtrip: include per-entity command payload, state echo payload, timestamps (command vs echo), and a PASS/FAIL line.

## Security & Privacy

- Never log raw credentials or tokens. Only emit booleans for presence.
- Use `BB8_LOG_PATH` and fallback to `/tmp` if needed; warn once.

## Architecture Ground Rules

- MQTT/HA concerns live in the **Facade**.
- `BLEBridge` is device-oriented; provide thin delegates only.
- Discovery is published **once** (Facade); dispatcher avoids discovery.

## Operational Controls

- LWT/birth: retain online/offline via `bb8/status`.
- Reconnect/backoff handled in dispatcher; no tight loops.
- Use try/except around BLE actions; log structured errors.

## Performance & Tokens

- Keep responses ≤ ~1.5k tokens; split work if needed.
- Reference existing artifacts by name/path instead of repeating content.

## Contact Points

- Next decision checkpoint: **STP4 evidence capture**.
- Owners:
  - Code (facade/bridge): Eng
  - MQTT/HA schema & evidence: QA/Integrations
  - Packaging/AppArmor/host_dbus: DevOps
