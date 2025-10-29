---
goal: Improve dev UX via Makefile tasks, VS Code tasks, minimal extension pack, quick coverage, MQTT discovery purge helper, and Supervisor restart helper
version: 1.0
date_created: 2025-10-27
owner: HA-BB8 Maintainers
status: In progress
tags: [process, editor, qa, ops, developer-experience]
---

# Introduction

![Status: Planned](https://img.shields.io/badge/status-Planned-blue)

Deterministic, low-risk quality-of-life improvements to speed up local development, validation, and operational tasks: consolidate Makefile targets, surface CI/evidence tasks in VS Code, recommend a minimal extension pack, add a quick coverage view, provide an MQTT discovery purge helper, and a Supervisor-only restart helper surfaced via Make.

## 1. Requirements & Constraints

- REQ-001: Provide Makefile targets for quick coverage (cov-html) and HA restart (ha-restart).
- REQ-002: Add VS Code tasks for QA, fast tests, evidence STP4, and env validation; include problem matchers where feasible.
- REQ-003: Recommend minimal extension pack (Python, YAML, Docker, Markdownlint, EditorConfig) in `.vscode/extensions.json`.
- REQ-004: Create `ops/diag/mqtt_purge_discovery.sh` to purge retained discovery topics for the active device.
- REQ-005: Add `ops/evidence/restart_helpers.sh` and wire `make ha-restart`.
- CON-001: Do not modify ADR content or ADR workflows in this plan.
- CON-002: Keep all scripts repo-local; no writes outside the workspace.
- GUD-001: Align with governance docs (Supervisor-first, env governance) and macOS default shell (zsh).
- SEC-001: Do not print secrets; load credentials from `.evidence.env`.

## 2. Implementation Steps

### Implementation Phase 1

- GOAL-001: Editor/Makefile foundation and helper scripts

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-001 | Add minimal extension recommendations to `.vscode/extensions.json`: Python, YAML, Docker, Markdownlint, EditorConfig |  |  |
| TASK-002 | Add Makefile target `cov-html` to generate HTML coverage and open it (macOS `open`, Linux `xdg-open`) | ✅ | 2025-10-27 |
| TASK-003 | Add Makefile target `ha-restart` invoking `ops/evidence/restart_helpers.sh` with fallback to HA API | ✅ | 2025-10-27 |
| TASK-004 | Create script `ops/diag/mqtt_purge_discovery.sh` to purge retained `homeassistant/#` topics for this device/base | ✅ | 2025-10-27 |
| TASK-005 | Add `ops/evidence/restart_helpers.sh` (Supervisor-first; HA API fallback) and mark executable | ✅ | 2025-10-27 |
| TASK-006 | Add VS Code tasks in `.vscode/tasks.json`: QA, Tests: fast, Evidence: STP4, Env: validate, HA: Restart add-on | ✅ | 2025-10-27 |

### Implementation Phase 2

- GOAL-002: Wire problem matchers and validation, ensure consistency

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-007 | Attach problem matchers to QA and Tests tasks (pytest output) | ✅ | 2025-10-27 |
| TASK-008 | Ensure `make env-validate` exists; if absent, add target to run `ops/env/env_governance_check.sh` and write to `reports/checkpoints/ENV-GOV/` | ✅ | 2025-10-27 |
| TASK-009 | Smoke test scripts and tasks on macOS (local) and ensure non-blocking behavior |  |  |

## 3. Alternatives

- ALT-001: Use devcontainer tasks instead of local VS Code tasks. Not chosen to avoid coupling to containerized dev.
- ALT-002: Integrate purge/HA restart into a single monolithic script. Not chosen to keep concern boundaries clear and composable.

## 4. Dependencies

- DEP-001: `pytest`, `pytest-cov` installed in the active environment for `cov-html`.
- DEP-002: macOS `open` or Linux `xdg-open` available to launch HTML coverage report.
- DEP-003: `mosquitto-clients` for `mosquitto_pub` and `mosquitto_sub` (for purge helper). Install via Homebrew: `brew install mosquitto`.
- DEP-004: `.evidence.env` with MQTT and HA credentials (no secrets in `.env`).

## 5. Files

- FILE-001: `.vscode/extensions.json` (recommend minimal extension pack)
- FILE-002: `.vscode/tasks.json` (add consolidated tasks)
- FILE-003: `Makefile` (add `cov-html`, `ha-restart`, verify `env-validate`)
- FILE-004: `ops/diag/mqtt_purge_discovery.sh` (new helper script)
- FILE-005: `ops/evidence/restart_helpers.sh` (new helper script)

## 6. Testing

- TEST-001: Coverage quick view
  - Run: `make cov-html`
  - Verify: `htmlcov/index.html` opens; coverage files generated; command returns 0.

- TEST-002: HA restart helper
  - Pre: Ensure `.evidence.env` has either `SUPERVISOR_TOKEN` (inside HA) or `HA_URL` + `HA_TOKEN` (outside).
  - Run: `make ha-restart`
  - Verify: Command prints success path (Supervisor or HA API); non-zero exit on failure.

- TEST-003: MQTT discovery purge
  - Pre: `.evidence.env` contains `MQTT_HOST`, `MQTT_PORT`, `MQTT_USER`, `MQTT_PASSWORD`, `MQTT_BASE`, `DEVICE_ID` (or pass flags).
  - Dry-run: `bash ops/diag/mqtt_purge_discovery.sh --dry-run`
  - Verify: Lists candidate topics; with `--execute`, publishes retained nulls and confirms.

- TEST-004: VS Code tasks
  - Open Command Palette → “Run Task”
  - Verify tasks exist: QA: make qa, Tests: fast, Evidence: STP4, Env: validate, HA: Restart add-on.
  - Verify problem panel populates for test failures.

## 7. Risks & Assumptions

- RISK-001: Missing `mosquitto-clients` will break purge helper; mitigation: detect and print actionable install hint.
- RISK-002: Opening coverage report may fail on headless CI; mitigation: make `open` best-effort and non-blocking.
- ASSUMPTION-001: `.evidence.env` is present locally and not committed to git; secrets remain out of `.env`.
- ASSUMPTION-002: Makefile exists and is the canonical command surface for local dev.

## 8. Related Specifications / Further Reading

- `.github/instructions/testing-deployment.instructions.md` — Supervisor-first operations
- `.github/instructions/env-governance.instructions.md` — Environment variable governance
- `docs/Project_Folders_Structure_Blueprint.md` — Structure context for editors and ops

---

## Implementation Details (Appendix)

This appendix provides exact edits for deterministic execution.

### A) Minimal extension pack (`.vscode/extensions.json`)

Add (or ensure) the following recommendations:

```
{
  "recommendations": [
    "ms-python.python",
    "redhat.vscode-yaml",
    "ms-azuretools.vscode-docker",
    "DavidAnson.vscode-markdownlint",
    "EditorConfig.EditorConfig"
  ]
}
```

### B) Makefile targets

Append the following targets if missing:

```
cov-html:
	pytest -q --maxfail=1 --disable-warnings --cov=addon/bb8_core --cov-report=html || true
	@if [ -d htmlcov ]; then \
	  (command -v open >/dev/null 2>&1 && open htmlcov/index.html) \
	  || (command -v xdg-open >/devnull 2>&1 && xdg-open htmlcov/index.html) \
	  || echo "Coverage HTML generated at htmlcov/index.html"; \
	fi

ha-restart:
	bash ops/evidence/restart_helpers.sh supervisor local_beep_boop_bb8 \
	 || bash ops/evidence/restart_helpers.sh ha local_beep_boop_bb8

env-validate:
	@bash ops/env/env_governance_check.sh | tee reports/checkpoints/ENV-GOV/env_validate.out
```

### C) VS Code tasks (`.vscode/tasks.json`)

Merge/add tasks (labels must match exactly):

```
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "QA: make qa",
      "type": "shell",
      "command": "make qa",
      "group": "build",
      "problemMatcher": ["$gcc"]
    },
    {
      "label": "Tests: fast",
      "type": "shell",
      "command": "pytest -q addon/tests -k 'not slow'",
      "group": "test",
      "problemMatcher": []
    },
    {
      "label": "Evidence: STP4",
      "type": "shell",
      "command": "make evidence-stp4",
      "group": "test",
      "problemMatcher": []
    },
    {
      "label": "Env: validate",
      "type": "shell",
      "command": "make env-validate",
      "group": "build",
      "problemMatcher": []
    },
    {
      "label": "HA: Restart add-on",
      "type": "shell",
      "command": "make ha-restart",
      "group": "build",
      "problemMatcher": []
    }
  ]
}
```

### D) MQTT discovery purge helper (`ops/diag/mqtt_purge_discovery.sh`)

Create script with executable bit:

```
#!/usr/bin/env bash
set -euo pipefail

usage() { echo "Usage: $0 [--base <mqtt_base>] [--device-id <id>] [--dry-run|--execute]"; exit 2; }

BASE="${MQTT_BASE:-bb8}"
DEVICE_ID="${DEVICE_ID:-}"  # optional; if set, will narrow topics
MODE="dry"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --base) BASE="$2"; shift 2;;
    --device-id) DEVICE_ID="$2"; shift 2;;
    --dry-run) MODE="dry"; shift;;
    --execute) MODE="exec"; shift;;
    *) usage;;
  esac
done

require() { command -v "$1" >/dev/null 2>&1 || { echo "Missing $1; install mosquitto-clients"; exit 3; }; }
require mosquitto_pub

set -a; [ -f .evidence.env ] && source .evidence.env; set +a

HOST="${MQTT_HOST:?set in .evidence.env}"
PORT="${MQTT_PORT:-1883}"
USER="${MQTT_USER:-}"
PASS="${MQTT_PASSWORD:-${MQTT_PASS:-}}"

AUTH=( )
[[ -n "$USER" ]] && AUTH+=( -u "$USER" )
[[ -n "$PASS" ]] && AUTH+=( -P "$PASS" )

prefix="homeassistant"
filter="$prefix/#"
[[ -n "$DEVICE_ID" ]] && filter="$prefix/#/$DEVICE_ID/#"

echo "Scanning retained discovery under: $filter (base=$BASE)"

# If mosquitto_sub is available, list candidates; else proceed blind
if command -v mosquitto_sub >/dev/null 2>&1; then
  mapfile -t topics < <(mosquitto_sub -h "$HOST" -p "$PORT" "${AUTH[@]}" -t "$filter" -v -C 1 -W 1 | awk '{print $1}' | sort -u)
else
  topics=( )
fi

if [[ ${#topics[@]} -eq 0 ]]; then
  echo "No topics detected via mosquitto_sub; continuing with wildcard path (may be no-op)."
fi

purge_one() {
  local t="$1"
  echo "Purge retain: $t"
  mosquitto_pub -h "$HOST" -p "$PORT" "${AUTH[@]}" -t "$t" -n -r
}

if [[ "$MODE" == "dry" ]]; then
  printf "DRY-RUN: would purge %d topics\n" "${#topics[@]}"
  printf "%s\n" "${topics[@]}"
  exit 0
fi

for t in "${topics[@]}"; do
  purge_one "$t"
done

echo "Done."
```

### E) Supervisor restart helper (`ops/evidence/restart_helpers.sh`)

Create script with executable bit:

```
#!/usr/bin/env bash
set -euo pipefail

mode="${1:-auto}"
addon="${2:-local_beep_boop_bb8}"

if [[ "$mode" == "supervisor" || ( "$mode" == "auto" && -n "${SUPERVISOR_TOKEN:-}" ) ]]; then
  curl -fsS -H "Authorization: Bearer $SUPERVISOR_TOKEN" http://supervisor/ping >/dev/null
  curl -fsS -X POST -H "Authorization: Bearer $SUPERVISOR_TOKEN" "http://supervisor/addons/$addon/restart"
  echo "OK: supervisor add-on restart"
  exit 0
fi

if [[ -n "${HA_URL:-}" && -n "${HA_TOKEN:-}" ]]; then
  curl -fsS -H "Authorization: Bearer $HA_TOKEN" "$HA_URL/api/" >/dev/null
  curl -fsS -X POST -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" \
       -d "{\"addon\":\"$addon\"}" "$HA_URL/api/services/hassio/addon_restart"
  echo "OK: HA API add-on restart"
  exit 0
fi

echo "ERR: No valid context (need SUPERVISOR_TOKEN or HA_URL+HA_TOKEN)"; exit 2
```
