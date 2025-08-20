## 2025-08-20 (TS: 20250820_200721Z) — Attempt 1 [REJECT]

**Verdict:** REJECT (binary)

**Reasons**
- Broker env drift across artifacts (`127.0.0.1` in run log vs `192.168.0.129` in manifest).
- Probe result: `roundtrip=FAIL`, `schema=UNKNOWN` (device echo not observed).
- Trace shows `source: "facade"` on scalars; policy requires `{"source":"device"}` when `REQUIRE_DEVICE_ECHO=1`.
- No `ble_link_started` lines found in the run log.

**Evidence (inline excerpts)**

**Manifest**
```json
{
  "STP4/roundtrip": "PASS",
  "base_topic": "bb8",
  "broker": {
    "host": "192.168.0.129",
    "port": 1883,
    "user_present": true
  },
  "files": [
    "ha_discovery_dump.json",
    "ha_mqtt_trace_snapshot.json"
  ],
  "generated_at": "2025-08-14T03:20:46.788194+00:00",
  "roundtrip": "PASS",
  "schema": "PASS",
  "schema_details": {
    "count": 0,
    "details": [],
    "valid": true
  },
  "timeouts_sec": 3.0
}
```

run.log (first 38 lines)

```log
[evidence
] ts=20250820_190721Z base=bb8 require_echo=1
[evidence
] broker=127.0.0.1: 1883 user=
[evidence
] step=probe
probe: connected=True roundtrip=FAIL schema=UNKNOWN
[evidence
] step=capture
[trace
] wrote ../reports/stp4_20250820_200721/ha_mqtt_trace_snapshot.jsonl
[evidence
] step=collector
{
  "event": "version_probe",
  "bleak": "0.22.3",
  "spherov2": "0.12.1"
}
[LOGGING DEBUG
] Resolved LOG_PATH candidate: /Volumes/addons/docs/reports/ha_bb8_addon.log
[LOGGING DEBUG
] Writable: True
2025-08-20 20: 07: 42,
137 INFO:bb8_addon: {'event': 'version_probe', 'bleak': '0.22.3', 'spherov2': '0.12.1'
}
[DEBUG
] Loaded config for MQTT: {'MQTT_USERNAME': None, 'MQTT_PASSWORD': None, 'MQTT_HOST': '127.0.0.1', 'MQTT_PORT': 1883, 'MQTT_BASE': 'bb8'
}
{
  "generated_at": "2025-08-20T19:08:09.255679+00:00",
  "broker": {
    "host": "127.0.0.1",
    "port": 1883,
    "user_present": false
  },
  "base_topic": "bb8",
  "schema": "PASS",
  "schema_details": {
    "valid": true,
    "count": 0,
    "details": []
  },
  "roundtrip": "FAIL",
  "STP4/roundtrip": "FAIL (explain if FAIL)",
  "timeouts_sec": 2.0,
  "files": [
    "ha_discovery_dump.json",
    "ha_mqtt_trace_snapshot.json"
  ]
}
[evidence
] collector exited nonzero (continuing; manifest will record verdicts)
[evidence
] step=manifest
[evidence
] complete: roundtrip=FAIL schema=UNKNOWN
```

ha_mqtt_trace_snapshot (first 13 entries)

```json
[
  {
    "command_payload": "ON",
    "command_topic": "bb8/power/set",
    "command_ts": "2025-08-14T03:20:46.145475+00:00",
    "entity": "power_on",
    "expect": "ON",
    "note": "",
    "pass": true,
    "source": "facade",
    "state_payload": "{\"value\": \"ON\", \"source\": \"facade\"}",
    "state_topic": "bb8/power/state",
    "state_ts": "2025-08-14T03:20:46.225260+00:00"
  },
  {
    "command_payload": "",
    "command_topic": "bb8/stop/press",
    "command_ts": "2025-08-14T03:20:46.226109+00:00",
    "entity": "stop_pressed",
    "expect": "pressed",
    "note": "",
    "pass": true,
    "source": "facade",
    "state_payload": "pressed",
    "state_topic": "bb8/stop/state",
    "state_ts": "2025-08-14T03:20:46.314418+00:00"
  },
  {
    "command_payload": "",
    "command_topic": "bb8/stop/press",
    "command_ts": "2025-08-14T03:20:46.226109+00:00",
    "entity": "stop_idle",
    "expect": "idle",
    "note": "",
    "pass": true,
    "source": "facade",
    "state_payload": "idle",
    "state_topic": "bb8/stop/state",
    "state_ts": "2025-08-14T03:20:46.314831+00:00"
  },
  {
    "command_payload": "{\"hex\": \"#FF6600\"}",
    "command_topic": "bb8/led/set",
    "command_ts": "2025-08-14T03:20:46.315090+00:00",
    "entity": "led_rgb",
    "expect": "{\"r\":255,\"g\":102,\"b\":0}",
    "note": "shape_json",
    "pass": true,
    "source": "facade",
    "state_payload": "{\"r\": 255, \"g\": 102, \"b\": 0}",
    "state_topic": "bb8/led/state",
    "state_ts": "2025-08-14T03:20:46.402412+00:00"
  },
  {
    "entity": "presence_state",
    "pass": true,
    "state_payload": null,
    "state_topic": "bb8/presence/state"
  },
  {
    "entity": "rssi_state",
    "pass": true,
    "state_payload": null,
    "state_topic": "bb8/rssi/state"
  },
  {
    "command_payload": "",
    "command_topic": "bb8/sleep/press",
    "command_ts": "2025-08-14T03:20:46.403069+00:00",
    "entity": "sleep_pressed",
    "expect": "pressed",
    "note": "",
    "pass": true,
    "source": "facade",
    "state_payload": "pressed",
    "state_topic": "bb8/sleep/state",
    "state_ts": "2025-08-14T03:20:46.490451+00:00"
  },
  {
    "command_payload": "",
    "command_topic": "bb8/sleep/press",
    "command_ts": "2025-08-14T03:20:46.403069+00:00",
    "entity": "sleep_idle",
    "expect": "idle",
    "note": "",
    "pass": true,
    "source": "facade",
    "state_payload": "idle",
    "state_topic": "bb8/sleep/state",
    "state_ts": "2025-08-14T03:20:46.490716+00:00"
  },
  {
    "command_payload": "270",
    "command_topic": "bb8/heading/set",
    "command_ts": "2025-08-14T03:20:46.491213+00:00",
    "entity": "heading_set_270",
    "expect": "270",
    "note": "",
    "pass": true,
    "source": "facade",
    "state_payload": "270",
    "state_topic": "bb8/heading/state",
    "state_ts": "2025-08-14T03:20:46.578761+00:00"
  },
  {
    "command_payload": "128",
    "command_topic": "bb8/speed/set",
    "command_ts": "2025-08-14T03:20:46.578991+00:00",
    "entity": "speed_set_128",
    "expect": "128",
    "note": "",
    "pass": true,
    "source": "facade",
    "state_payload": "128",
    "state_topic": "bb8/speed/state",
    "state_ts": "2025-08-14T03:20:46.666828+00:00"
  },
  {
    "command_payload": "",
    "command_topic": "bb8/drive/press",
    "command_ts": "2025-08-14T03:20:46.667074+00:00",
    "entity": "drive_pressed",
    "expect": "pressed",
    "note": "",
    "pass": true,
    "source": "facade",
    "state_payload": "pressed",
    "state_topic": "bb8/drive/state",
    "state_ts": "2025-08-14T03:20:46.754388+00:00"
  },
  {
    "command_payload": "",
    "command_topic": "bb8/drive/press",
    "command_ts": "2025-08-14T03:20:46.667074+00:00",
    "entity": "drive_idle",
    "expect": "idle",
    "note": "",
    "pass": true,
    "source": "facade",
    "state_payload": "idle",
    "state_topic": "bb8/drive/state",
    "state_ts": "2025-08-14T03:20:46.754951+00:00"
  }
]
```

Next run (strict, device echo required)

Align broker env: MQTT_HOST=192.168.0.129, MQTT_PORT=1883.

Ensure device online; scalars must include {"source":"device"}.

Re-run: REPORTS_DIR="reports/evidence" make evidence-stp4
