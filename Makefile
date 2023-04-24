# Define phony targets
.PHONY: venv activate deactivate clean lint install setup_test test coverage_test run

# Name of the virtual environment
VENV_NAME = .

# Python interpreter path
PYTHON_INTERPRETER = python3

# Path to requirements file
REQUIREMENTS_FILE = requirements.txt

# Create virtual environment
venv:
	$(PYTHON_INTERPRETER) -m venv $(VENV_NAME)

# Activate virtual environment
activate:
	. $(VENV_NAME)/bin/activate

# Install dependencies from requirements file
install: venv activate
	$(PYTHON_INTERPRETER) -m pip install -r $(REQUIREMENTS_FILE)

run: venv activate
	$(PYTHON_INTERPRETER) -m src.sensehatsensorstomqtt.__main__

lint: venv activate
	./bin/flake8 src/* --count --max-complexity=13 --max-line-length=127 --statistics

setup_test: venv activate
	$(PYTHON_INTERPRETER) -m pip install pytest pytest-cov pytest_mock flake8 sense-emu

test: venv activate setup_test
	./bin/pytest src/test/*.py

coverage_test: venv activate setup_test
	./bin/pytest --cov=src --cov-fail-under=80 --cov-report=term-missing src/tests/*.py

# Deactivate virtual environment
deactivate:
	deactivate

# Remove virtual environment
clean:
	rm -rf $(VENV_NAME)
