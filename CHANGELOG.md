# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-10-09

### Added
- Configurable cadence (`interval`, `measurements`, `sample_spacing`) using `time.monotonic()` to maintain consistent sampling timing without drift.
- MQTT availability status topic (`status_topic`) with retained `online`/`offline` state and Last Will and Testament (LWT) registered with the broker.
- Configurable MQTT Quality of Service (`qos`) and `retain` settings.
- Raspberry Pi CPU temperature compensation (`compensate_cpu_temp`, `cpu_temp_factor`) and manual temperature calibration offset (`temperature_offset`).
- Decoupled LED matrix display subsystem (`display.py`) supporting real hardware (`SenseHatDisplay`) and headless environments (`NullDisplay`).
- Configurable display toggle (`display`), scroll pause (`display_pause`), and night mode window (`night_start`, `night_end`).
- Typed configuration schema (`Config` dataclass) with fail-fast validation.
- Hardware factory (`hardware.py`) allowing off-device testing without hardware imports and priming initial sensor reads.
- CI matrix workflow for Python 3.11, 3.12, and 3.13 with coverage gate, twine check, and wheel contents verification.
- Static type checking with Mypy and expanded Ruff linting rule sets.
- Automated drift verification test ensuring all CLI options are documented in README.
- Pre-commit configuration and `.gitattributes` enforcing LF line endings.

### Fixed
- Migrated to Paho MQTT 2.x `CallbackAPIVersion.VERSION2` and bounded dependency (`paho-mqtt>=2.0.0,<3.0.0`).
- Prevented credential leakage by automatically redacting passwords in debug logging and error output.
- Replaced buggy custom daemonizer with standard systemd service management and graceful signal handling (`SIGTERM` / `SIGINT`).
- Fixed systemd service unit: run as dedicated non-root `sensehat` user with supplementary groups `i2c`, `video`, `input`, and applied security hardening directives.
- Excluded test files from built binary wheels.
- Replaced deprecated naive UTC datetime with timezone-aware ISO-8601 UTC timestamp.
- Applied numeric rounding to measurements in MQTT payload (temperature/humidity: 0.01, pressure: 0.1).
- Fixed typos and incorrect docstrings across codebase.
