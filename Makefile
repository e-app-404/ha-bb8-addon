# Makefile — operator one-liners
.PHONY: guard test publish runtime-deploy attest all


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

publish:
	@bash ops/automation/ship_addon.sh publish | tee reports/publish_receipt.txt
	@grep -q 'SUBTREE_PUBLISH_OK' reports/publish_receipt.txt

runtime-deploy:
	@bash ops/automation/runtime_deploy.sh | tee reports/deploy_receipt.txt
	@grep -Eq 'CLEAN_RUNTIME_OK|DEPLOY_OK|VERIFY_OK' reports/deploy_receipt.txt

attest:
	@echo 'Use this on the HA host (SSH add-on): /config/domain/shell_commands/stp5_attest.sh' && exit 0

all: guard test publish
