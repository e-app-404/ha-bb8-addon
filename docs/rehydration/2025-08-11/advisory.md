# Rehydration Advisory [STRATEGOS]

## Token & startup advisory

- Keep replies surgical: diffs, stubs, and minified JSON.
- Avoid full-file pastes and long logs; show ≤150 lines focused excerpts.
- Start next session with Strategos persona, oversight mode, intervention=on.

## Assumptions/risks on resume

- BLE actions may require BlueZ/DBus permissions on host; verify host_dbus: true, udev: true, AppArmor profile paths.
- Local vs container bleak versions differ; align or schedule an upgrade test.
- PR delta may conflict with recent facade-first changes; rebase carefully.

## Guardrails

- Enforce no secrets in logs (booleans for credential presence only).
- One discovery publisher (facade) only; dispatcher stays neutral.
- Keep dispatcher signature stable; deprecate but accept legacy params with warnings.

## Rehydration Seed Package Contents

[Rehydration Advisory](advisory.md)
[Session Recap Summary](session_recap.yaml)
[Artifact Reference Index](artifacts.yaml)
[Phase + Output Registry](phases.yaml)
[Memory Variables for Rehydration](memory.yaml)
[Rehydration Seed](rehydration_seed.yaml)
[Strategos Session Guidelines & Patch Etiquette](guidelines.md)
