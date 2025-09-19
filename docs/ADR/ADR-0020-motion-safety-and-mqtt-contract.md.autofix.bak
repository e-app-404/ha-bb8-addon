---
title: "ADR-0020: Workspace folder taxonomy and assignation rules"
date: 2025-09-15
status: Accepted
author:
  - Evert Appels
  - Strategos GPT
related: []
supersedes: []
last_updated: 2025-09-15
---

# ADR-0020: Motion Safety & MQTT Contract

## Context


## Safety Defaults
- ALLOW_MOTION=0 by default (no physical movement without opt-in).
- Limits: MAX_SPEED=150, MAX_DURATION_MS=1000, FAILSAFE_PAD_MS=100.

## Topics (no wildcards)
- Drive command (JSON): `bb8/<device>/cmd/drive` → payload:
  `{ "speed": int(0..255), "heading": int(0..359), "duration_ms": int(100..1000) }`
- Drive ack (non-retained): `bb8/<device>/ack/drive`
- Drive state (retained): `bb8/<device>/state/drive` (last accepted snapshot)

## Home Assistant MQTT Discovery (v1)
**Rule:** Discovery JSON MUST NOT include broker publish options (e.g., `retain`). Retention is set on the publish call only.

### Three numbers (speed / heading / duration_ms)
Publish each config to `homeassistant/number/<unique_id>/config` with `retain=True` on publish (not in JSON).

#### Example (`speed`):
```json
{
  "name": "BB-8 Speed",
  "unique_id": "bb8_<device_id>_speed",
  "device": {
    "identifiers": ["bb8_<device_id>"],
    "manufacturer": "Sphero",
    "model": "BB-8",
    "name": "BB-8 <device_id>"
  },
  "state_topic": "bb8/<device_id>/state/drive",
  "value_template": "{{ value_json.speed | default(0) }}",
  "command_topic": "bb8/<device_id>/cmd/speed",
  "min": 0,
  "max": 255,
  "step": 1
}
```

#### Example (`heading`):
```json
{
  "name": "BB-8 Heading",
  "unique_id": "bb8_<device_id>_heading",
  "device": {
    "identifiers": ["bb8_<device_id>"],
    "manufacturer": "Sphero",
    "model": "BB-8",
    "name": "BB-8 <device_id>"
  },
  "state_topic": "bb8/<device_id>/state/drive",
  "value_template": "{{ value_json.heading | default(0) }}",
  "command_topic": "bb8/<device_id>/cmd/heading",
  "min": 0,
  "max": 359,
  "step": 1
}
```

#### Example (`duration_ms`):
```json
{
  "name": "BB-8 Duration",
  "unique_id": "bb8_<device_id>_duration_ms",
  "device": {
    "identifiers": ["bb8_<device_id>"],
    "manufacturer": "Sphero",
    "model": "BB-8",
    "name": "BB-8 <device_id>"
  },
  "state_topic": "bb8/<device_id>/state/drive",
  "value_template": "{{ value_json.duration_ms | default(100) }}",
  "command_topic": "bb8/<device_id>/cmd/duration_ms",
  "min": 100,
  "max": 1000,
  "step": 1
}
```

### Drive button (static payload; no templating)

Publish to homeassistant/button/<unique_id>/config with `retain=True` on publish. 
The controller translates these simple numeric commands into a single JSON drive command on bb8/<device_id>/cmd/drive.
The MQTT Button **does not support templates** in the payload. Use a static trigger instead.

```json
{
  "name": "BB-8 Drive",
  "unique_id": "bb8_<device_id>_drive",
  "device": { "identifiers": ["bb8_<device_id>"] },
  "command_topic": "bb8/<device_id>/cmd/drive_trigger",
  "payload_press": "DRIVE"
}
```

### Controller behavior

- On `cmd/speed`|`heading`|`duration_ms`: cache latest numeric values.
- On `cmd/drive_trigger`: read cached values (or HA state), then publish JSON on `bb8/<device_id>/cmd/drive`.
- Publish `state/drive` (retained) and `ack/drive` (non-retained).

### Testing

Schema validation; clamps; disabled-motion NACK; retained states on accept; failsafe scheduled.


## Token Blocks