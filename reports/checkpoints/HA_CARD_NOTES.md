## BB‑8 HA Card Notes (STP5)

**Defaults:** LED discovery remains disabled. You will see Presence + RSSI grouped under the same device. To test LED command UX without enabling discovery, use an [MQTT Button/Light helper] or call `bb8/led/cmd` directly.

### Example (Manual Card)

```yaml
type: vertical-stack
cards:
  - type: entities
    title: BB‑8
    entities:
      - entity: binary_sensor.bb8_presence
      - entity: sensor.bb8_rssi
  # Optional: if you expose a manual light via MQTT helper
  - type: light
    entity: light.bb8_led_optional
```

### Notes
- Command path: `bb8/led/cmd` with JSON `{r,g,b}`
- State echo: `bb8/led/state` (strict keys `{r,g,b}`, no `source`)
- Discovery owner: scanner only (bridge telemetry stays suppressed)
