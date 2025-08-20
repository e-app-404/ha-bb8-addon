## 1) Receipt verification (no code changes)

=== BASELINE_SHA ===
b5661c9c7c90418498790113d4d45915bd3eb5f8

=== RECEIPT_CONTENTS ===
<<<FILE:reports/qa_20250819_185143Z/pythagoras_receipt_20250819_185143Z.status>>>
VERDICT=PASS
RUFF=PASS
MYPY=PASS
PYTEST=PASS
DISCOVERY_NOLED=PASS
DISCOVERY_LED=PASS
ADDON_AUDIT=SKIP
STATUS_JSON=reports/qa_20250819_185143Z/project_status.log
STATUS_MD=reports/qa_20250819_185143Z/summary_20250819_185143Z.md
VDISC_NOLED=reports/qa_20250819_185143Z/verify_no_led.log
VDISC_LED=reports/qa_20250819_185143Z/verify_led.log
<<<END:reports/qa_20250819_185143Z/pythagoras_receipt_20250819_185143Z.status>>>
<<<FILE:./reports/qa_20250819_185143Z/summary_20250819_185143Z.md>>>
# QA Receipt (20250819_185143Z)
- Verdict: PASS
- Ruff: PASS
- Mypy: PASS
- Pytest: PASS
- Discovery (LED off): PASS
- Discovery (LED on): PASS
- Addon audit: SKIP
<<<END:./reports/qa_20250819_185143Z/summary_20250819_185143Z.md>>>
<<<FILE:./reports/qa_20250819_182755Z/project_status.log>>>
PROJECT_STATUS: PASS
JSON: /Users/evertappels/Projects/HA-BB8/reports/project_status_audit_20250819_182813Z.json
MD: /Users/evertappels/Projects/HA-BB8/reports/project_status_audit_20250819_182813Z.md
<<<END:./reports/qa_20250819_182755Z/project_status.log>>>
<<<FILE:./reports/qa_20250819_182755Z/verify_no_led.log>>>
/Users/evertappels/Projects/HA-BB8/tools/verify_discovery.py:96: DeprecationWarning: Callback API version 1 is deprecated, update to latest version
  c = mqtt.Client()
Discovery Verification Results:
Topic                      | Retained | stat_t              | avty_t      | sw_version      | identifiers
---------------------------|----------|---------------------|-------------|----------------|-------------------
homeassistant/binary_sensor/bb8_presence/config | True    | bb8/presence/state  | bb8/status  | 2025.08.20     | ['bb8', 'mac:ED:ED:87:D7:27:50']
homeassistant/sensor/bb8_rssi/config | True    | bb8/rssi/state      | bb8/status  | 2025.08.20     | ['bb8', 'mac:ED:ED:87:D7:27:50']

PASS
<<<END:./reports/qa_20250819_182755Z/verify_no_led.log>>>
<<<FILE:./reports/qa_20250819_182755Z/verify_led.log>>>
/Users/evertappels/Projects/HA-BB8/tools/verify_discovery.py:96: DeprecationWarning: Callback API version 1 is deprecated, update to latest version
  c = mqtt.Client()
Discovery Verification Results:
Topic                      | Retained | stat_t              | avty_t      | sw_version      | identifiers
---------------------------|----------|---------------------|-------------|----------------|-------------------
homeassistant/binary_sensor/bb8_presence/config | True    | bb8/presence/state  | bb8/status  | 2025.08.20     | ['bb8', 'mac:ED:ED:87:D7:27:50']
homeassistant/sensor/bb8_rssi/config | True    | bb8/rssi/state      | bb8/status  | 2025.08.20     | ['bb8', 'mac:ED:ED:87:D7:27:50']
homeassistant/light/bb8_led/config | True    | bb8/led/state       | bb8/status  | 2025.08.20     | ['bb8', 'mac:ED:ED:87:D7:27:50']

PASS
<<<END:./reports/qa_20250819_182755Z/verify_led.log>>>

## 2) Baseline artifacts request

=== RUNTIME_TOUCHPOINTS ===

=== BOM ===
b5661c9c7c90418498790113d4d45915bd3eb5f8

A       reports/qa_20250819_185143Z/pythagoras_receipt_20250819_185143Z.status

=== PATCH ===
diff --git a/reports/qa_20250819_185143Z/pythagoras_receipt_20250819_185143Z.status b/reports/qa_20250819_185143Z/pythagoras_receipt_20250819_185143Z.status
new file mode 100644
index 0000000..7a3b06a
--- /dev/null
+++ b/reports/qa_20250819_185143Z/pythagoras_receipt_20250819_185143Z.status
@@ -0,0 +1,11 @@
+VERDICT=PASS
+RUFF=PASS
+MYPY=PASS
+PYTEST=PASS
+DISCOVERY_NOLED=PASS
+DISCOVERY_LED=PASS
+ADDON_AUDIT=SKIP
+STATUS_JSON=reports/qa_20250819_185143Z/project_status.log
+STATUS_MD=reports/qa_20250819_185143Z/summary_20250819_185143Z.md
+VDISC_NOLED=reports/qa_20250819_185143Z/verify_no_led.log
+VDISC_LED=reports/qa_20250819_185143Z/verify_led.log

## 3) VCS actions on that validated commit

Tag and branch creation:

Tag pushed: RE-BASELINE_20250819_185143Z
Branch pushed: rebaseline/stp5-various-pass

PR URL: https://github.com/e-app-404/ha-bb8-addon/pull/3

Git output:
Enumerating objects: 8, done.
Counting objects: 100% (8/8), done.
Delta compression using up to 8 threads
Compressing objects: 100% (6/6), done.
Writing objects: 100% (6/6), 821 bytes | 821.00 KiB/s, done.
Total 6 (delta 2), reused 0 (delta 0), pack-reused 0
remote: Resolving deltas: 100% (2/2), completed with 2 local objects.
To https://github.com/e-app-404/ha-bb8-addon.git
 * [new tag]         RE-BASELINE_20250819_185143Z -> RE-BASELINE_20250819_185143Z
Total 0 (delta 0), reused 0 (delta 0), pack-reused 0
To https://github.com/e-app-404/ha-bb8-addon.git
  3f032a9..b5661c9  rebaseline/stp5-various-pass -> rebaseline/stp5-various-pass
branch 'rebaseline/stp5-various-pass' set up to track 'origin/rebaseline/stp5-various-pass'.
a pull request for branch "rebaseline/stp5-various-pass" into branch "main" already exists:
https://github.com/e-app-404/ha-bb8-addon/pull/3