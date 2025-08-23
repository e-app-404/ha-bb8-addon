# BB-8 Patch Etiquette & Session Guidelines


## Contract

- **Repo Structure:** `addon/` is never a git repo in the workspace. Do **not** run `git init` inside `addon/`; all git operations are workspace-root only. Separation is handled by subtree publish and runtime clone, not by nested repos.
- **Namespace:** Flat MQTT `bb8/<behavior>/<action>` only.
- **Discovery:** Published by the *scanner* exclusively; dispatcher discovery OFF by default.
- **Evidence-first:** Changes must make STP4 *easier* to pass (never harder).

## Deltas

- **One consolidated delta per cycle.** No piecemeal merges.
- Include: scope, files touched, acceptance tests, and rollback note.
- **Binary acceptance:** Roundtrip PASS + Schema PASS (strict mode when device echoes land).

## Topics & Entities

- Commandables must emit state echoes.
- Façade echoes tag `{"source":"facade"}`; device echoes tag `{"source":"device"}`.
- HA Light uses JSON schema: `{"state":"ON","color":{"r","g","b"},"color_mode":"rgb"}`.

## Telemetry & Looping

- Scanner owns `bb8/sensor/*` by default. Bridge telemetry gated by `enable_bridge_telemetry`.
- BLE loops run on a dedicated event loop thread (no `get_event_loop` in main).

## Logging

- Add `role` to telemetry logs (`bridge` vs `scanner`).
- No duplicate handlers; one clean log line per event.

## Evidence Runbook

1. If device echoes missing: `REQUIRE_DEVICE_ECHO=0`, verify façade roundtrip.
2. After device echoes integrated: `REQUIRE_DEVICE_ECHO=1`, rerun STP4.
3. Submit: `evidence_manifest.json` + first 20 lines of `ha_mqtt_trace_snapshot.jsonl`.

## Redaction & Retention

- Avoid creds in logs; redact tokens/paths as needed.
- Clear stale HA discovery (`-r -n` to old config topics) after renames.

## Decision Checkpoints

- Namespace changes require PO sign-off.
- Discovery ownership changes require Strategos sign-off.

*Last updated:* 2025-08-13 • Anchor STRAT-f8202ca110cc

## Release Quickstart (Workspace → GitHub → HA runtime)

1. Dev & test locally (`make dev`).
2. Publish add-on subtree to GitHub:
	```sh
	make publish
	```

	(No-op safe if addon/ unchanged.)
3. Deploy to HA runtime and restart add-on:

	REMOTE_HOST_ALIAS=home-assistant ops/release/deploy_ha_over_ssh.sh

Acceptance tokens you should see: SUBTREE_PUBLISH_OK, DEPLOY_OK, VERIFY_OK, RUNTIME_TOPOLOGY_OK.

This doesn’t change policy; it consolidates the release path already defined in ADR-0001 addenda. :contentReference[oaicite:9]{index=9}
