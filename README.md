# HA-BB8 Add-on — BB-8 Integration

This repository contains the **Home Assistant add-on** for the HA-BB8 BB-8 integration.

**Governance:** Supervisor-only execution · MQTT-only telemetry/actuation · Evidence-first.  
**Canonical topics:**
- Commands: `bb8/cmd/*` (e.g., `diag_scan`, `actuate_probe`)
- Acks: `bb8/ack/*` with payload `{ "ok": true|false, "cid": "<cid>", "echo": { ... } }`
- Telemetry: `bb8/status/telemetry` with keys `connected, estop, last_cmd_ts, battery_pct, ts`

> Evidence bundles and governance docs live in the **workspace repo**.  
> See PR comments for the latest supervised receipt and SHA manifest.

