# =========
# Evidence
# =========
MQTT_HOST ?= localhost
MQTT_PORT ?= 1883
MQTT_USER ?=
MQTT_PASSWORD ?=
MQTT_BASE ?= bb8
STAMP ?= $(shell date +"%Y%m%d_%H%M%S")

.PHONY: evidence-stp4 evidence-clean

evidence-stp4:
	@mkdir -p reports
	@echo ">> collecting STP4 evidence to reports/stp4_$(STAMP)"
	python3 ops/evidence/collect_stp4.py \
		--host "$(MQTT_HOST)" --port $(MQTT_PORT) \
		--user "$(MQTT_USER)" --password "$(MQTT_PASSWORD)" \
		--base "$(MQTT_BASE)" \
		--out "reports/stp4_$(STAMP)"

evidence-clean:
	@rm -rf reports/stp4_* || true
	@echo ">> cleaned prior STP4 evidence bundles"

PYTHON=python3

.PHONY: test lint

test:
	PYTHONPATH=. pytest --maxfail=1 --disable-warnings

lint:
	PYTHONPATH=. ruff .
	PYTHONPATH=. flake8 .
