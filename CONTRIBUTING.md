# Contributing to sense-hat-sensors-to-mqtt

Thank you for your interest in contributing!

## Development Workflow

1. Clone the repository and install the development environment:
   ```bash
   git clone https://github.com/hellqvio86/sense-hat-sensors-to-mqtt.git
   cd sense-hat-sensors-to-mqtt
   make install
   ```

2. Verify tests and linters pass:
   ```bash
   make test
   ```

## Code Standards

- **Linting & Formatting**: Follow Ruff configuration defined in `pyproject.toml`. Run `uv run ruff check .` and `uv run ruff format src tests`.
- **Typing**: Code must pass `uv run mypy src` cleanly.
- **Testing**: All changes and bugfixes must include unit tests. Tests must run without physical hardware or network connectivity. Maintain $\ge 80\%$ test coverage.
- **Line Endings**: LF line endings are enforced across all text files via `.gitattributes`.
- **Commit Messages**: Follow [Conventional Commits](https://www.conventionalcommits.org/) (e.g., `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`).
