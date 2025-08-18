# 📄 Final Advisory (+ Patch Etiquette doc)

## **Token usage advisory**

- Favor YAML blocks and short enumerations; avoid verbose logs in-line.
- When sharing traces/logs, include only the first ~150 lines around key events (`ble_link_started`, handler invoke, echo publish).
- Keep deltas consolidated; one patch block per cycle.

## **Recommended next GPT startup configuration**

- Start Strategos with the **rehydration_seed** above.
- Immediately issue: “Rehydrate from seed and confirm readiness for STP4 strict graduation.”
- Strategos should output an **execution_mandate** for Pythagoras and a **delta_contract** reflecting any newly detected drift.
- Spin a parallel Pythagoras session (Copilot-facing) using the same seed (or a Pythagoras-only slice) to execute the mandate and return **patch_bundle_contract_v1** + **qa_report_contract_v1**.

## **Assumptions & risks to validate on resume**

- Shim remains hard-disabled when `REQUIRE_DEVICE_ECHO=1`.
- No retained prestate on commandable topics; retained sensors only on `bb8/sensor/*`.
- BLE loop emits `ble_link_started` and **no*- `get_event_loop` warnings.
- Discovery is published by **scanner only**.
- Strict evidence run is executed with `MQTT_BASE=bb8`, `EVIDENCE_TIMEOUT_SEC≈3.0–4.0`.

## Rehydration Seed Package Contents

[Rehydration Advisory](advisory.md)
[Session Recap Summary](session_recap.yaml)
[Artifact Reference Index](artifacts.yaml)
[Phase + Output Registry](phases.yaml)
[Memory Variables for Rehydration](memory.yaml)
[Rehydration Seed](rehydration_seed.yaml)
[Strategos Session Guidelines & Patch Etiquette](guidelines.md)
