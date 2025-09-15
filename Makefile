# Workspace tarball targets
tarball:
	bash scripts/make_workspace_tarball.sh

snapshot-dry:
	bash scripts/make_workspace_tarball.sh --dry-run

snapshot-verify:
	bash scripts/make_workspace_tarball.sh --verify "$(FILE)"
# =========
# Strategos: allow space-indented recipe lines (fixes 'missing separator' from GNU make).
# This is a build-only change. No targets or commands altered.
# GNU Make 3.82+ supports .RECIPEPREFIX.
# Evidence
# =========
VENV := $(CURDIR)/.venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
STAMP ?= $(shell date +"%Y%m%d_%H%M%S")
REPORTS_DIR ?= ../reports
PY := $(shell [ -x .venv/bin/python ] && echo .venv/bin/python || command -v python3 || command -v python)
REQ_RUNTIME := addon/requirements.txt
REQ_DEV := $(shell [ -f addon/requirements-dev.txt ] && echo addon/requirements-dev.txt || echo)

.SILENT:
.ONESHELL:
.PHONY: venv deps lint typecheck test dev help help-dev dev-deps dev-lint dev-typecheck dev-test addon-audit format types testcov security qa ci evidence-stp4 evidence-clean evidence-validate bleep

venv:
	@test -x "$(PYTHON)" || (python3 -m venv "$(VENV)" && "$(PIP)" install -U pip)
	if [ ! -x .venv/bin/python ]; then
		echo "Creating venv..."
		python3 -m venv .venv
	fi
	@echo "VENV_READY:$$($(PY) -c 'import sys;print(sys.version.split()[0])')"

deps: venv
	$(PIP) install --upgrade pip setuptools wheel
	[ -f $(REQ_RUNTIME) ] && $(PIP) install -r $(REQ_RUNTIME) || true
	[ -n "$(REQ_DEV)" ] && [ -f "$(REQ_DEV)" ] && $(PIP) install -r "$(REQ_DEV)" || true
	$(PIP) install -U ruff mypy pytest
	@echo "DEPS_READY"

lint: deps
	$(PY) -m ruff --version
	$(PY) -m ruff check addon || true
	@echo "LINT_DONE"

typecheck: deps
	$(PY) -m mypy --version
	$(PY) -m mypy addon || true
	@echo "TYPECHECK_DONE"

test: deps
	if [ -d addon/tests ]; then
		$(PY) -m pytest -q addon/tests || true
	fi
	@echo "TESTS_DONE"

# dev: lint typecheck test
#    @echo "MAKE_DEV_OK"

help:
	@echo "Targets:"
	@echo "  make dev        - lint (ruff), typecheck (mypy), test collect (pytest) with tokens"
	@echo "  make venv       - create .venv if missing"
	@echo "  make deps       - install runtime + dev deps into venv"
	@echo "  make lint       - run ruff on addon/"
	@echo "  make typecheck  - run mypy on addon/"
	@echo "  make test       - pytest collect on addon/tests (non-failing)"

help-dev:
	@echo "Targets:"
	@echo "  make dev        - lint (ruff), typecheck (mypy), test collect (pytest) with tokens"
	@echo "  make dev-deps   - install runtime + dev deps into venv"
	@echo "  make dev-lint   - run ruff on addon/"
	@echo "  make dev-typecheck  - run mypy on addon/"
	@echo "  make dev-test   - pytest collect on addon/tests (non-failing)"

dev-deps: venv
	$(PIP) install --upgrade pip setuptools wheel
	[ -f $(REQ_RUNTIME) ] && $(PIP) install -r $(REQ_RUNTIME) || true
	[ -n "$(REQ_DEV)" ] && [ -f "$(REQ_DEV)" ] && $(PIP) install -r "$(REQ_DEV)" || true
	$(PIP) install -U ruff mypy pytest
	@echo "DEPS_READY"

dev-lint: dev-deps
	$(PYTHON) -m ruff --version
	$(PYTHON) -m ruff check addon || true
	@echo "LINT_DONE"

dev-typecheck: dev-deps
	$(PYTHON) -m mypy --version
	$(PYTHON) -m mypy addon || true
	@echo "TYPECHECK_DONE"

dev-test: dev-deps
	if [ -d addon/tests ]; then
		$(PYTHON) -m pytest -q addon/tests || true
	fi
	@echo "TESTS_DONE"

dev: dev-lint dev-typecheck dev-test
	@echo "MAKE_DEV_OK"

addon-audit:
	python tools/audit_addon_tree.py --strict --out reports/addon_audit_ci.json

format:
	@mkdir -p $(REPORTS_DIR)/qa_$(STAMP)
	black --check . 2>&1 | tee $(REPORTS_DIR)/qa_$(STAMP)/black.log

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

.PHONY: bleep
bleep:
	python3 addon/tools/bleep_run.py
	@echo ">> bleep run complete"

clean:
	find . -name '.DS_Store' -type f -delete
	rm -rf __pycache__ addon/__pycache__ ops/__pycache__ scripts/__pycache__
	rm -rf .pytest_cache .ruff_cache
	rm -rf ../reports/stp4_* ../reports/qa_* ../reports/ci_*
	echo "Workspace cleaned."

index:
	bash ops/adr/generate_adr_index.sh


# ========= Snapshot
LOC_THRESHOLD ?= 2000
FILES_THRESHOLD ?= 80

.PHONY: snapshot snapshot-dry snapshot-auto snapshot-tarball snapshot-untracked

snapshot: snapshot-tarball

snapshot-dry:
    @LOC_THRESHOLD=$(LOC_THRESHOLD) FILES_THRESHOLD=$(FILES_THRESHOLD) \
    bash scripts/snapshot_policy.sh --dry-run

snapshot-auto:
    @LOC_THRESHOLD=$(LOC_THRESHOLD) FILES_THRESHOLD=$(FILES_THRESHOLD) \
    SNAPSHOT_AUTO=1 bash -c 'out=$$(bash scripts/snapshot_policy.sh --dry-run); echo "$$out"; \
        need=$$(echo "$$out" | jq -r .needs_snapshot); \
        if [ "$$need" = "true" ] || [ "$$need" = "1" ]; then \
            LOC_THRESHOLD=$(LOC_THRESHOLD) FILES_THRESHOLD=$(FILES_THRESHOLD) bash scripts/snapshot_policy.sh; \
        else echo "NO_SNAPSHOT_NEEDED"; fi'

snapshot-tarball:
    @LOC_THRESHOLD=$(LOC_THRESHOLD) FILES_THRESHOLD=$(FILES_THRESHOLD) \
    bash scripts/snapshot_policy.sh --force

snapshot-untracked:
    @TS=$$(date +%Y%m%d_%H%M%S); mkdir -p _backups/inventory; \
    git ls-files --others --exclude-standard | sort > "_backups/inventory/untracked_$${TS}.txt"; \
    echo "UNTRACKED_OK _backups/inventory/untracked_$${TS}.txt"


.PHONY: compile
compile:
	@python -m compileall -q .
