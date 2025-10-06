# INT-HA-CONTROL Gate A Resume Prompt

**CONTEXT**: I'm resuming work on INT-HA-CONTROL Gate A acceptance for the BB8 Home Assistant add-on. We have a critical infrastructure blocker where the Docker container lacks Python dependencies (paho-mqtt, bleak, spherov2), causing both bb8_core.main and echo_responder to crash on import with "ModuleNotFoundError: No module named 'paho'".

**CURRENT STATE**: All technical patches have been implemented and deployed, but are blocked by the infrastructure issue. The container is in a restart loop (attempt #35+) with both services failing immediately.

**TECHNICAL PATCHES DEPLOYED**:
1. ✅ Echo startup module (`addon/bb8_core/echo_startup.py`) - forces echo responder when REQUIRE_DEVICE_ECHO=1
2. ✅ Bridge controller integration (line 477) - calls echo startup during initialization  
3. ✅ Entity persistence audit script with HA API integration and 10-second SLA validation
4. ✅ Runtime package installation in run.sh (lines 141-158) - attempts to install missing deps at startup
5. ✅ Requirements.txt copied to addon/requirements.txt for proper Docker build context

**ROOT CAUSE**: Original Docker build was missing requirements.txt file (was in project root, not addon/ directory), so the Dockerfile's conditional pip install never executed. File has been copied to correct location but container needs rebuild.

**IMMEDIATE NEXT STEPS**:
1. Restart Home Assistant Core to clear container cache
2. Check if runtime installation in run.sh resolved the dependency issue
3. If still failing, manually rebuild add-on via HA UI (Settings > Add-ons > BB8 > Rebuild)
4. Once deps are installed, execute Gate A validation sequence expecting 5/5 criteria to PASS

**VALIDATION SEQUENCE POST-FIX**:
```bash
# MQTT Echo Test (expect 5/5 pings successful)
HOST=192.168.0.129 PORT=1883 USER=mqtt_bb8 PASS=mqtt_bb8 BASE=bb8 REQUIRE_DEVICE_ECHO=1 python3 reports/checkpoints/INT-HA-CONTROL/mqtt_health_echo_test.py

# Entity Persistence Audit (≤10s recovery SLA)  
python3 reports/checkpoints/INT-HA-CONTROL/entity_persistence_audit.py

# Discovery Ownership, LED Schema, Config validation
python3 reports/checkpoints/INT-HA-CONTROL/discovery_ownership_audit.py
python3 reports/checkpoints/INT-HA-CONTROL/led_entity_alignment_test.py

# Final evidence collection
./ops/evidence/execute_int_ha_control.sh
```

**ENVIRONMENT**: 
- HA_URL=http://192.168.0.129:8123
- MQTT broker at 192.168.0.129:1883 (mqtt_bb8/mqtt_bb8)
- REQUIRE_DEVICE_ECHO=1, PUBLISH_LED_DISCOVERY=0
- All credentials in .evidence.env

**CONFIDENCE**: HIGH (90%) - Root cause identified, solution clear, all patches ready for activation once container rebuild completes.

**FULL CONTEXT**: See `docs/meta/int-ha-control-context-seed-2025-10-05.md` for complete technical details.

---

**INSTRUCTION**: Please immediately resume INT-HA-CONTROL Gate A unblock work by first checking the current container status, then proceeding with the container rebuild resolution to activate all deployed technical patches and complete the 5/5 acceptance criteria validation.