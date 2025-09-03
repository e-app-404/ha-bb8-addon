.PHONY: diag-health
diag-health:
	@bash ops/diag/ha_bb8_health.sh

.PHONY: diag-respawn
diag-respawn:
	@bash ops/diag/ha_bb8_respawn_drill.sh
.PHONY: diag-health
diag-health:
	@bash ops/diag/ha_bb8_health.sh

.PHONY: diag-respawn
diag-respawn:
	@bash ops/diag/ha_bb8_respawn_drill.sh
guard:
	@bash ops/workspace/validate_paths_map.sh | tee reports/paths_health_receipt.txt
	@grep -q '^TOKEN: PATHS_MAP_OK' reports/paths_health_receipt.txt

test:
	@python3 -m venv .venv
	@. .venv/bin/activate; python3 -m pip install --upgrade pip wheel --break-system-packages >/dev/null
	@. .venv/bin/activate; python3 -m pip install -e addon pytest pytest-cov --break-system-packages >/dev/null
	@test -f addon/requirements-dev.txt && . .venv/bin/activate; python3 -m pip install -r addon/requirements-dev.txt --break-system-packages >/dev/null || true
	@. .venv/bin/activate; pytest -q --maxfail=1 --cov=bb8_core --cov-report=term-missing
	@echo 'TOKEN: TEST_OK' | tee -a reports/qa_receipt.txt

runtime-deploy:
	@bash ops/automation/runtime_deploy.sh | tee reports/deploy_receipt.txt
	@grep -Eq 'CLEAN_RUNTIME_OK|DEPLOY_OK|VERIFY_OK' reports/deploy_receipt.txt

attest:
	@echo 'Use this on the HA host (SSH add-on): /config/domain/shell_commands/stp5_attest.sh' && exit 0

all: guard test publish

# --- Strategos release shortcuts ---
.PHONY: release-patch release-minor release-major release VERSION

verify-config-src:
	@grep -q 'enable_health_checks' addon/config.yaml || (echo "FATAL: enable_health_checks missing in addon/config.yaml"; exit 1)
	@echo "VERIFY_OK: source config.yaml contains enable_health_checks"

release-patch: verify-config-src
	VERSION_KIND=patch ops/release/bump_version.sh patch && \
	ops/workspace/publish_addon_archive.sh && \
	ops/release/deploy_ha_over_ssh.sh

release-minor:
	VERSION_KIND=minor ops/release/bump_version.sh minor && ops/workspace/publish_addon_archive.sh && ops/release/deploy_ha_over_ssh.sh

release-major:
	VERSION_KIND=major ops/release/bump_version.sh major && ops/workspace/publish_addon_archive.sh && ops/release/deploy_ha_over_ssh.sh

release:
	test -n "$(VERSION)" || { echo "ERROR: set VERSION=x.y.z"; exit 2; }; ops/release/bump_version.sh $(VERSION) && ops/workspace/publish_addon_archive.sh && ops/release/deploy_ha_over_ssh.sh

VENV := $(CURDIR)/.venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

.PHONY: venv
venv:
	@test -x "$(PYTHON)" || (python3 -m venv "$(VENV)" && "$(PIP)" install -U pip)

testcov: venv
	@mkdir -p reports/qa_$(STAMP)
	PYTHONPATH=$(PYTHONPATH) "$(PYTHON)" -m pytest -q --maxfail=1 --disable-warnings \
	--cov=bb8_core --cov-report=term-missing | tee reports/qa_$(STAMP)/pytest.log

STAMP ?= $(shell date +"%Y%m%d_%H%M%S")
# Consolidated reports directory (root-level); override via env if needed
REPORTS_DIR ?= ../reports

.PHONY: evidence-stp4 evidence-clean

evidence-stp4:
	@if [ -z "$$MQTT_HOST" ]; then \
	echo "ERROR: MQTT_HOST must be set in the environment (e.g., export MQTT_HOST=192.168.0.129)"; \
	exit 1; \
	fi
	@mkdir -p $(REPORTS_DIR)
	@echo ">> collecting STP4 evidence to $(REPORTS_DIR)/stp4_$(STAMP)"
	@export MQTT_HOST=$$MQTT_HOST; \
	export MQTT_BASE=$$MQTT_BASE; \
	export REQUIRE_DEVICE_ECHO=$$REQUIRE_DEVICE_ECHO; \
	export ENABLE_BRIDGE_TELEMETRY=$$ENABLE_BRIDGE_TELEMETRY; \
	export EVIDENCE_TIMEOUT_SEC=$$EVIDENCE_TIMEOUT_SEC; \
	export MQTT_USERNAME=$$MQTT_USERNAME; \
	export MQTT_PASSWORD=$$MQTT_PASSWORD; \
	export MQTT_PORT=$$MQTT_PORT; \
	bash ops/evidence/evidence_preflight.sh "$(REPORTS_DIR)/stp4_$(STAMP)"

evidence-validate:
	@echo ">> validating latest STP4 evidence bundle"
	@bash ops/evidence/stp4_evidence_validate.sh

evidence-clean:
	@rm -rf $(REPORTS_DIR)/stp4_* || true
	@echo ">> cleaned prior STP4 evidence bundles"

PYTHON=python3

# =====================
# QA & CI Targets
# =====================

.PHONY: addon-audit
addon-audit:
	python tools/audit_addon_tree.py --strict --out reports/addon_audit_ci.json

.PHONY: format lint types testcov security qa ci

format:
	@mkdir -p $(REPORTS_DIR)/qa_$(STAMP)
	black --check . 2>&1 | tee $(REPORTS_DIR)/qa_$(STAMP)/black.log

lint:
	@mkdir -p $(REPORTS_DIR)/qa_$(STAMP)
	ruff check . | tee $(REPORTS_DIR)/qa_$(STAMP)/ruff.log

types:
	@mkdir -p $(REPORTS_DIR)/qa_$(STAMP)
	mypy --install-types --non-interactive . | tee $(REPORTS_DIR)/qa_$(STAMP)/mypy.log

testcov:
	@mkdir -p $(REPORTS_DIR)/qa_$(STAMP)
	PYTHONPATH=. pytest -q --maxfail=1 --disable-warnings --cov=bb8_core --cov-report=term-missing | tee $(REPORTS_DIR)/qa_$(STAMP)/pytest.log

security:
	@mkdir -p $(REPORTS_DIR)/qa_$(STAMP)
	bandit -q -r bb8_core | tee $(REPORTS_DIR)/qa_$(STAMP)/bandit.log || true
	safety scan --full-report | tee $(REPORTS_DIR)/qa_$(STAMP)/safety.log || true

qa:
	@STAMP=$(STAMP); \
	mkdir -p $(REPORTS_DIR)/qa_$$STAMP; \
	echo ">> running QA suite to $(REPORTS_DIR)/qa_$$STAMP/"; \
	$(MAKE) format STAMP=$$STAMP; \
	$(MAKE) lint STAMP=$$STAMP; \
	$(MAKE) types STAMP=$$STAMP; \
	$(MAKE) testcov STAMP=$$STAMP; \
	$(MAKE) security STAMP=$$STAMP

ci:
	@STAMP=$(STAMP); \
	mkdir -p $(REPORTS_DIR)/ci_$$STAMP; \
	echo ">> running CI suite to $(REPORTS_DIR)/ci_$$STAMP/"; \
	$(MAKE) format STAMP=$$STAMP; \
	$(MAKE) lint STAMP=$$STAMP; \
	$(MAKE) types STAMP=$$STAMP; \
	$(MAKE) testcov STAMP=$$STAMP; \
	$(MAKE) security STAMP=$$STAMP \
	| tee $(REPORTS_DIR)/ci_$$STAMP/ci.log

.PHONY: diagnose-ssh deploy-ssh publish

diagnose-ssh:
	REMOTE_HOST_ALIAS=home-assistant ops/release/deploy_ha_over_ssh.sh diagnose

deploy-ssh:
	REMOTE_HOST_ALIAS=home-assistant ops/release/deploy_ha_over_ssh.sh

publish:
	REMOTE_HOST_ALIAS=home-assistant ops/release/publish_and_deploy.sh