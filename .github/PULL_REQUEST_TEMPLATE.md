# STP4 Device Echo PR Acceptance Checklist

- [ ] **Roundtrip evidence:** All BB-8 entities pass roundtrip (STP4/roundtrip: PASS)
- [ ] **Schema compliance:** All entities pass schema validation (schema: PASS)
- [ ] **Device echo:** All scalar state echoes include `"source":"device"` (not just facade)
- [ ] **LED RGB:** LED state is published as compact JSON (no spaces, e.g. `{"r":255,"g":102,"b":0}`)
- [ ] **No get_event_loop warnings:** No `DeprecationWarning: There is no current event loop` in logs
- [ ] **No retained commandable echoes:** All commandable state topics publish with `retain=False`
- [ ] **No legacy/duplicate entities:** Only flat namespace entities are present in discovery

---

## Description

<!-- Describe the purpose and scope of this PR -->

## Testing

<!-- List evidence runs, manual tests, and validation steps -->

## Additional Notes

<!-- Any extra context, links, or migration notes -->
