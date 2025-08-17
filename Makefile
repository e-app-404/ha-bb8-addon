# =========
# Evidence
# =========

STAMP ?= $(shell date +"%Y%m%d_%H%M%S")

.PHONY: evidence-stp4 evidence-clean

evidence-stp4:
	@if [ -z "$$MQTT_HOST" ]; then \
		echo "ERROR: MQTT_HOST must be set in the environment (e.g., export MQTT_HOST=192.168.x.x)"; \
		exit 1; \
	fi
	@mkdir -p reports
	@echo ">> collecting STP4 evidence to reports/stp4_$(STAMP)"
	@export MQTT_HOST=$$MQTT_HOST; \
	export MQTT_BASE=$$MQTT_BASE; \
	export REQUIRE_DEVICE_ECHO=$$REQUIRE_DEVICE_ECHO; \
	export ENABLE_BRIDGE_TELEMETRY=$$ENABLE_BRIDGE_TELEMETRY; \
	export EVIDENCE_TIMEOUT_SEC=$$EVIDENCE_TIMEOUT_SEC; \
	export MQTT_USERNAME=$$MQTT_USERNAME; \
	export MQTT_PASSWORD=$$MQTT_PASSWORD; \
	export MQTT_PORT=$$MQTT_PORT; \
	bash ops/evidence/run_evidence_stp4.sh "reports/stp4_$(STAMP)"

evidence-validate:
	@echo ">> validating latest STP4 evidence bundle"
	@bash ops/evidence/stp4_evidence_validate.sh

evidence-clean:
	@rm -rf reports/stp4_* || true
	@echo ">> cleaned prior STP4 evidence bundles"

PYTHON=python3

# =====================
# QA & CI Targets
# =====================

.PHONY: format lint types testcov security qa ci

format:
	@mkdir -p reports/qa_$(STAMP)
	black --check . 2>&1 | tee reports/qa_$(STAMP)/black.log

lint:
	@mkdir -p reports/qa_$(STAMP)
	ruff check . | tee reports/qa_$(STAMP)/ruff.log

types:
	@mkdir -p reports/qa_$(STAMP)
	mypy --install-types --non-interactive . | tee reports/qa_$(STAMP)/mypy.log

testcov:
	@mkdir -p reports/qa_$(STAMP)
	PYTHONPATH=. pytest -q --maxfail=1 --disable-warnings --cov=bb8_core --cov-report=term-missing | tee reports/qa_$(STAMP)/pytest.log

security:
	@mkdir -p reports/qa_$(STAMP)
	bandit -q -r bb8_core | tee reports/qa_$(STAMP)/bandit.log || true
	safety scan --full-report | tee reports/qa_$(STAMP)/safety.log || true

qa:
	@STAMP=$(STAMP); \
	mkdir -p reports/qa_$$STAMP; \
	echo ">> running QA suite to reports/qa_$$STAMP/"; \
	$(MAKE) format STAMP=$$STAMP; \
	$(MAKE) lint STAMP=$$STAMP; \
	$(MAKE) types STAMP=$$STAMP; \
	$(MAKE) testcov STAMP=$$STAMP; \
	$(MAKE) security STAMP=$$STAMP

ci:
	@STAMP=$(STAMP); \
	mkdir -p reports/ci_$$STAMP; \
	echo ">> running CI suite to reports/ci_$$STAMP/"; \
	$(MAKE) format STAMP=$$STAMP; \
	$(MAKE) lint STAMP=$$STAMP; \
	$(MAKE) types STAMP=$$STAMP; \
	$(MAKE) testcov STAMP=$$STAMP; \
	$(MAKE) security STAMP=$$STAMP \
	| tee reports/ci_$$STAMP/ci.log
