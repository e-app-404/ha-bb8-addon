Operate under Strategos governance. Be quiet, Supervisor-first, MQTT-only.

CONTEXT:
- Broker=core-mosquitto, Base=bb8, MAC=ED:ED:87:D7:27:50, Adapter=hci0
- Evidence host root=/config/ha-bb8/checkpoints/BB8-FUNC/<TS>; local mirror=reports/checkpoints/BB8-FUNC/
- Entry: python -m bb8_core.bridge_controller (foreground)

DO EXACTLY:
1) Confirm dispatcher: LWT bb8/status offline; on connect → online (retained); subs bb8/cmd/#, bb8/echo/cmd; echo replies with {"source":"device"}; telemetry heartbeat present.
2) Ensure handlers exist: power, drive, stop, led, led_preset, estop, clear_estop, diag_scan, diag_gatt, actuate_probe (ACKs with cid).
3) Rebuild & restart via Supervisor (no rsync).
4) Evidence (host→mirror):
   - c1_scan_ack.json from bb8/ack/diag_scan (ok:true for target MAC)
   - c2_actuation_ack.json from bb8/ack/actuate_probe (ok:true)
   - supervisor_restart.log
5) Return ≤10 lines:
   [Gate]: ACCEPT|REWORK
   - 3 highlights
   - Host evidence path
   - Local mirror path
   - 2 next steps
