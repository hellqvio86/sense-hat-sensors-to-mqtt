PROJECT_NAME := sensehatsensorstomqtt
PYTHON_BIN ?= python3

.PHONY: all venv install test clean install-service

all: install

venv:
	uv venv --allow-existing --system-site-packages --python $(PYTHON_BIN)

install: venv
	uv sync --extra dev

test:
	uv run ruff check .
	uv run ruff format --check src tests
	uv run mypy src
	uv run pytest --cov=sensehatsensorstomqtt --cov-fail-under=80 tests/

clean:
	rm -rf .venv
	rm -rf *.egg-info src/*.egg-info
	rm -rf dist build
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
