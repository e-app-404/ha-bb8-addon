# --- Strategos release shortcuts ---
.PHONY: release-patch release-minor release-major release VERSION
release-patch: ; VERSION_KIND=patch ops/release/bump_version.sh patch && ops/release/publish_addon_archive.sh && ops/release/deploy_ha_over_ssh.sh
release-minor: ; VERSION_KIND=minor ops/release/bump_version.sh minor && ops/release/publish_addon_archive.sh && ops/release/deploy_ha_over_ssh.sh
release-major: ; VERSION_KIND=major ops/release/bump_version.sh major && ops/release/publish_addon_archive.sh && ops/release/deploy_ha_over_ssh.sh
release: ; test -n "$(VERSION)" || { echo "ERROR: set VERSION=x.y.z"; exit 2; }; ops/release/bump_version.sh $(VERSION) && ops/release/publish_addon_archive.sh && ops/release/deploy_ha_over_ssh.sh

# --- ADR-0028: Remote triad management ---
.PHONY: backups triad-status triad-sync triad-sync-mirror triad-verify
backups:
	git fetch --all --prune
	STAMP=$$(date -u +%Y%m%dT%H%M%SZ); \
	git push github refs/heads/main:refs/heads/backup/main-github-$$STAMP; \
	git push github refs/heads/main:refs/tags/backup/main-github-$$STAMP; \
	git push origin refs/heads/main:refs/heads/backup/main-nas-$$STAMP; \
	git push origin refs/heads/main:refs/tags/backup/main-nas-$$STAMP; \
	echo BACKUPS_OK:$$STAMP

triad-status:
	@echo "== Triad Status =="
	@echo -n "LOCAL : "; git rev-parse HEAD
	@echo -n "GITHUB: "; git ls-remote --heads github main | awk '{print $$1" "$$2}'
	@echo -n "NAS   : "; git ls-remote --heads origin main  | awk '{print $$1" "$$2}'

triad-sync:
	git fetch github main --prune
	GITHUB_REF=refs/remotes/github/main; \
	GITHUB_SHA=$$(git rev-parse $$GITHUB_REF); \
	echo "Syncing NAS main to GitHub SHA: $$GITHUB_SHA"; \
	if git push origin --force-with-lease=main $${GITHUB_SHA}:refs/heads/main; then \
		echo MIRROR_SYNC_OK; \
	else \
		echo "Force-with-lease failed; trying mirror branch fallback (ADR-0028)"; \
		$(MAKE) triad-sync-mirror || (echo MIRROR_SYNC_DENIED; exit 2); \
	fi

triad-sync-mirror:
	@git fetch github main --prune
	@GITHUB_REF=refs/remotes/github/main; \
	echo "Updating NAS mirror/main from $$GITHUB_REF"; \
	git push origin $$GITHUB_REF:refs/heads/mirror/main && echo MIRROR_BRANCH_SYNC_OK || (echo MIRROR_BRANCH_SYNC_FAILED; exit 3)

triad-verify:
	@LOCAL=$$(git rev-parse HEAD); \
	GH=$$(git ls-remote --heads github main | awk '{print $$1}'); \
	NAS=$$(git ls-remote --heads origin main | awk '{print $$1}'); \
	NAS_M=$$(git ls-remote --heads origin mirror/main 2>/dev/null | awk '{print $$1}'); \
	echo LOCAL=$$LOCAL; echo GITHUB=$$GH; echo NAS=$$NAS; [ -n "$$NAS_M" ] && echo NAS_MIRROR=$$NAS_M || true; \
	if [ "$$GH" = "$$NAS" ]; then echo REMOTE_TRIAD_OK; exit 0; fi; \
	if [ -n "$$NAS_M" ] && [ "$$GH" = "$$NAS_M" ]; then echo "REMOTE_TRIAD_OK (via mirror/main)"; exit 0; fi; \
	echo "DRIFT: remote_triad_mismatch"; exit 2

# =========
#.RECIPEPREFIX =  # <- INTENTIONAL SINGLE SPACE AFTER '='
# Strategos: allow space-indented recipe lines (fixes 'missing separator' from GNU make).
# This is a build-only change. No targets or commands altered.
# GNU Make 3.82+ supports .RECIPEPREFIX.
# Evidence
# =========
VENV := $(CURDIR)/.venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

.PHONY: venv
venv:
	@test -x "$(PYTHON)" || (python3 -m venv "$(VENV)" && "$(PIP)" install -U pip)

testcov: venv
	@mkdir -p $(REPORTS_DIR)/qa_$(STAMP)
	PYTHONPATH=. "$(PYTHON)" -m pytest -q --maxfail=1 --disable-warnings \
		--cov=bb8_core --cov-report=term-missing | tee $(REPORTS_DIR)/qa_$(STAMP)/pytest.log

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

quiet:
	sh ops/check_workspace_quiet.sh .