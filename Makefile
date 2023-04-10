# Define phony targets
.PHONY: venv activate deactivate clean lint install

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
	pip install -r $(REQUIREMENTS_FILE)

lint: venv activate
	flake8 src/* --count --max-complexity=13 --max-line-length=127 --statistics

# Deactivate virtual environment
deactivate:
	deactivate

# Remove virtual environment
clean:
	rm -rf $(VENV_NAME)
