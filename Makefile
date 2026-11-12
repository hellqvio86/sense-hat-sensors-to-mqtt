PROJECT_NAME := sensehatsensorstomqtt
PYTHON_BIN ?= python3

.PHONY: all venv install test clean install-service hooks renovate renovate-summary

all: install

venv:
	uv venv --allow-existing --system-site-packages --python $(PYTHON_BIN)

hooks:
	@if [ -d .git ]; then \
		git config core.hooksPath .githooks; \
		echo "Configured git hooks path to .githooks"; \
	fi

install: venv hooks
	uv sync --extra dev

test:
	uv run ruff check .
	uv run ruff format --check src tests .github/scripts
	uv run mypy src
	uv run pytest --cov=sensehatsensorstomqtt --cov-fail-under=80 --cov-report=json tests/
	uv run python .github/scripts/generate_coverage_badge.py

clean:
	rm -rf .venv
	rm -rf *.egg-info src/*.egg-info
	rm -rf dist build coverage.json .coverage
	find . -type f -name '*.pyc' -delete
	find . -type d -name '__pycache__' -delete

install-service:
	@echo "Ensuring sensehat system user exists..."
	@id -u sensehat >/dev/null 2>&1 || sudo useradd -r -s /usr/sbin/nologin -G i2c,video,input sensehat || true
	@echo "Installing executable wrapper to /usr/local/bin/"
	@printf '#!/bin/bash\nexec $(CURDIR)/.venv/bin/$(PROJECT_NAME) "$$@"\n' | sudo tee /usr/local/bin/$(PROJECT_NAME) > /dev/null
	sudo chmod 755 /usr/local/bin/$(PROJECT_NAME)
	@echo "Installing systemd service..."
	sudo cp systemd/$(PROJECT_NAME).service /etc/systemd/system/
	sudo systemctl daemon-reload
	@echo "Service installed successfully."
	@echo "Enable it with: sudo systemctl enable $(PROJECT_NAME)"
	@echo "Start it with: sudo systemctl start $(PROJECT_NAME)"

renovate:
	@./bin/renovate/run.sh

renovate-summary:
	@./bin/renovate/run.sh --summary

secrets: ## Run TruffleHog secret scanning
	@echo "Running TruffleHog secret scan..."
	@if command -v trufflehog >/dev/null 2>&1; then \
		trufflehog --no-update git file://$$(pwd) --only-verified --fail; \
	elif command -v docker >/dev/null 2>&1; then \
		docker run --rm -v $$(pwd):/src -w /src trufflesecurity/trufflehog:latest git file:///src --only-verified --fail; \
	else \
		echo "ERROR: trufflehog or docker is required!" >&2 && exit 1; \
	fi

trivy: ## Run Trivy vulnerability scanning
	@echo "Running Trivy vulnerability scan..."
	@if command -v trivy >/dev/null 2>&1; then \
		trivy fs --severity HIGH,CRITICAL --exit-code 1 .; \
	elif command -v docker >/dev/null 2>&1; then \
		docker run --rm -v $$(pwd):/src -v trivy-cache:/root/.cache -w /src aquasec/trivy:latest fs --severity HIGH,CRITICAL --exit-code 1 .; \
	else \
		echo "ERROR: trivy or docker is required!" >&2 && exit 1; \
	fi

