6) 📄 Final Advisory (+ Patch Etiquette doc)
6.1 Token & startup guidance

# Rehydration Advisory [STRATEGOS]

## Token & startup advisory

- Token usage: moderate, safe margin; avoid pasting long full files.
- “ultra-lean mode”: unified diffs only, rationale ≤ 5 bullets
- Prefer head/tail logs (≤150 lines)
- Keep replies surgical: diffs, stubs, and minified JSON.
- Avoid full-file pastes and long logs; show ≤150 lines focused excerpts.
- Start next session with Strategos persona, oversight mode, intervention=on.

## Assumptions/risks on resume

- BLE loop thread applied everywhere
- Discovery only from scanner (no dispatcher duplicates)

## Guardrails

- One consolidated delta per cycle
- Evidence-first: run STP4 after each merge
- Never create new topic hierarchies; stick to bb8/...
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
