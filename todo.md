# todo.md: critical review of sense-hat-sensors-to-mqtt

Audience: AI coding agents (and humans). Read `AGENTS.md` first.
Reviewed at commit `dc0a589` (version 0.0.4).

How to use this file:
- Work top-down by priority. One item per change set. Tick the box when merged.
- Each item has **Where**, **Problem**, **Fix**, **Done when** (testable acceptance criteria).
- Evidence tags: `[verified]` = reproduced by running the code in a sandbox; `[code]` = established by
  reading the code (not run on hardware); `[hw]` = needs a Raspberry Pi + Sense HAT to confirm.
- Tests must not touch hardware or a real broker (fake `sense_hat`, fake MQTT client).

## Summary

The happy path (read 3 sensors, publish JSON, scroll it on the LED matrix) works. Around it:
`--topics` on the command line crashes, `--port` is passed to paho as a string, CLI-only configuration is
impossible, the debug mode prints the MQTT password twice, any transient error kills the process, the
logging module only works because of import order, and the test suite is a single copy-pasted test that
cannot even import the application modules without the Sense HAT libraries. Much of this code is
duplicated in the sibling `enviroplus-sensors-to-mqtt` project, so fixes should be mirrored there.

---

## P0: Bugs that break documented or default behaviour

### [x] P0-1 `--topics` on the command line crashes `[verified]`
- **Where:** `args.py:64-65`
- **Problem:** `args.list.split(",")` references a non-existent attribute (should be `args.topics`).
  `sensehatsensorstomqtt --topics a,b` raises `AttributeError: 'Namespace' object has no attribute 'list'`.
  README advertises `--topics`.
- **Fix:** Use `args.topics`. Strip empty items; reject an empty list.
- **Done when:** a test calls `args_handler` with `--topics a,b` and gets `["a", "b"]`; whitespace and
  trailing commas are handled.

### [x] P0-2 `--port` is kept as a string and breaks the MQTT connection `[verified]`
- **Where:** `args.py:22,49-50`, `sensor.py:64`
- **Problem:** The argument is declared `type=str` and stored without conversion, so `config["port"]` is
  `"8883"`. `paho.connect(host, "1883", 60)` raises `TypeError: '<=' not supported between instances of
  'str' and 'int'`. (The sibling project does `int(...)`; this one does not.)
- **Fix:** `type=int` with range validation (1-65535); also coerce/validate a `port:` read from YAML.
- **Done when:** test asserts `config["port"]` is an `int` for both CLI and YAML sources; non-numeric input
  yields a clear argparse error.

### [x] P0-3 CLI-only configuration crashes when no config file exists `[verified]`
- **Where:** `args.py:31-38`, `config.py:40-41`
- **Problem:** `args_handler()` always ends in `parse_config()`, which raises `FileNotFoundError` for a
  missing `config.yaml`. Running with only `--host/--username/--password/--topics` and no file fails with a
  traceback, contradicting the README ("configured via command-line arguments or a YAML file").
- **Fix:** Make the config file optional. Order: `--config_file` (error if given but missing),
  `/etc/sensehatsensorstomqtt.yaml`, `./config.yaml`, otherwise defaults. Apply defaults after merging.
- **Done when:** test with CLI flags only and no file yields a valid config; `--config_file /nonexistent`
  still errors clearly.

### [x] P0-4 Debug mode prints the MQTT password (twice) `[verified]`
- **Where:** `main.py:27-28`, `args.py:67-68`
- **Problem:** With `-D`, the entire config dict is `print`ed, including `'password': 'secret123'`, once in
  `args_handler` and again in `main()`. Output goes to the terminal/journal. Passing `--password` on the
  command line also exposes it in `ps` / `/proc/*/cmdline`.
- **Fix:** Remove both prints; log a redacted copy via the logger (`password: "***"`). Add env-var
  (`MQTT_PASSWORD`) and/or `password_file` support; recommend `chmod 600` for the config file.
- **Done when:** test asserts no log/stdout output of `args_handler`/`main` contains the password.

### [x] P0-5 `logging.py` raises `AttributeError` unless another module imported `logging.handlers` first `[verified]`
- **Where:** `logging.py:4,22`
- **Problem:** It does `import logging` but uses `logging.handlers.RotatingFileHandler`. Using the module in
  isolation fails with `AttributeError: module 'logging' has no attribute 'handlers'`. The app only works
  because `main.py` happens to `import logging.handlers` first.
- **Fix:** `import logging.handlers` (or `from logging.handlers import RotatingFileHandler`) in `logging.py`.
  Also rename the module (see P3-2).
- **Done when:** a test imports `setup_logger` in a fresh interpreter (subprocess) and calls it with
  `debug=True` and a temp `log_file`.

### [x] P0-6 `-D`/`--daemon` require a writable `/var/log/sensehatsensorstomqtt/` `[code]`
- **Where:** `logging.py:21-26`, `config.py:52-54`
- **Problem:** Whenever `debug or daemon` is set, a `RotatingFileHandler` is opened immediately at the default
  `/var/log/...` path. If the directory doesn't exist or isn't writable (dev machine, non-root) startup
  fails. (Same code reproduced as a failure in the sibling project.)
- **Fix:** Create a file handler only when `log_file` is explicitly set; default to console logging; on file
  errors log a warning and continue.
- **Done when:** `setup_logger(debug=True)` works with no `log_file`; an unwritable path warns, not raises.

### [x] P0-7 Any exception terminates the service; no per-cycle error handling `[code]`
- **Where:** `main.py:41-54`, `sensor.py:35-101`
- **Problem:** I2C/Sense HAT errors, `connect()` failures (DNS, broker down, network not up at boot),
  or LED errors propagate out of `main()` and kill the process; recovery depends solely on systemd (whose
  unit has conflicting `Restart=` lines, P1-7). A failed LED call also loses the already-read sensor data
  if it occurs before publishing is retried.
- **Fix:** Wrap each cycle in `try/except Exception` with `LOGGER.exception`, continue to the next cycle,
  and back off after repeated failures. Make the display failure non-fatal and independent of publishing.
- **Done when:** tests inject a failing `connect` and a failing `show_message`; the loop survives and the
  failure is logged; publishing still happens when only the display fails.

### [x] P0-8 Pidfile bug writes the stale PID `[code]`
- **Where:** `daemonizer.py:44-64`
- **Problem:** `pid` is overwritten by the pidfile contents. For a stale pidfile (dead process) the code then
  writes that **old** PID instead of `os.getpid()`. Non-numeric contents leave `pid` a `str` and
  `psutil.pid_exists(pid)` raises `TypeError`. File handle in the read branch is never closed.
- **Fix:** Superseded by P1-1 (remove the daemonizer). If kept: separate variables, `int()` in try/except,
  `with open(...)`.
- **Done when:** P1-1 is done, or tests cover stale, live and garbage pidfiles.

---

## P1: Reliability, correctness, security, testability

### [x] P1-1 Make the code importable and testable without hardware, then add a real test suite `[verified]`
- **Where:** `sensor.py:13`, `main.py`, `src/tests/test_config.py`, new `src/tests/conftest.py`
- **Problem:** `from sense_hat import SenseHat` runs at import time. Off-device (CI, laptops)
  `import sensehatsensorstomqtt.main` fails with `ModuleNotFoundError: No module named 'RTIMU'`, so `main`,
  `sensor`, `colors`'s caller etc. are unimportable and untested. The only test (`test_config.py`) uses a
  copy-pasted ML config (`model.learning_rate`, `data.train_path`) unrelated to this project, asserts on
  those irrelevant keys, and leaks the temp file if the assertion fails (`os.unlink` is not in `finally`).
  Effective behavioural coverage of the app is ~0 %.
- **Fix:**
  1. Move hardware access behind an adapter (`hardware.py`) that imports `sense_hat` lazily; keep the rest
     importable. In tests use a `conftest.py` that injects a fake into `sys.modules`:
     ```python
     import sys, types
     fake = types.ModuleType("sense_hat"); fake.SenseHat = FakeSenseHat
     sys.modules.setdefault("sense_hat", fake)
     ```
  2. Split `send_sensor_data` into `read_measurements()`, `build_payload()`, `publish()`, `show_on_display()`.
  3. Give `args_handler(argv=None)` an `argv` parameter instead of reading `sys.argv` implicitly.
  4. Replace `test_config.py` with realistic tests (use `tmp_path`): defaults, YAML merge, CLI precedence,
     validation, payload keys/units/rounding, `is_night` boundaries (06:59 night, 07:00 day, 18:59 day,
     19:00 night), failing-sensor/failing-publish paths, loop control with a fake clock.
- **Done when:** `pytest --cov=sensehatsensorstomqtt` >= 80 % with no Sense HAT libs importable; CI enforces it.

### [x] P1-2 Hardware handles and MQTT client are created every cycle and never released `[code]` `[hw]`
- **Where:** `sensor.py:35`, `main.py:43`
- **Problem:** A new `SenseHat()` (opens the IMU/humidity sensors and the framebuffer) and a new
  `mqtt.Client()` are created each minute; neither is closed or disconnected. Over days this leaks file
  descriptors/sockets and re-initialising the Sense HAT every cycle is slow and unnecessary.
- **Fix:** Create the `SenseHat` once at startup and reuse it; use one long-lived MQTT client with
  `loop_start()`, auto-reconnect, and `disconnect()`/`loop_stop()` on shutdown; or use `try/finally`.
- **Done when:** fakes assert every opened resource is closed exactly once on success and failure paths; a
  human long-run on a Pi shows a stable FD count (`ls /proc/<pid>/fd | wc -l`).

### [x] P1-3 MQTT publishing is fire-and-forget with no checks `[code]`
- **Where:** `sensor.py:63-75`
- **Problem:** `connect()` + `publish()` with no network loop, no check of the returned `MQTTMessageInfo`, no
  `wait_for_publish()`, and no disconnect. "messages published" is logged even if delivery failed. The same
  JSON is re-encoded for every topic. Retain is hardcoded; QoS is the default 0.
- **Fix:** Check `rc`, `wait_for_publish(timeout=...)`, log failures; add `on_connect`/`on_disconnect`
  callbacks; encode the payload once; make `qos`/`retain` configurable (default QoS 1).
- **Done when:** a fake client returning a failure results in an error log, not "published".

### [x] P1-4 Deprecated paho callback API and unbounded dependency `[verified]`
- **Where:** `main.py:43`, `pyproject.toml` (`paho-mqtt`)
- **Problem:** `mqtt.Client()` with paho-mqtt 2.1.0 (the locked version) emits
  `DeprecationWarning: Callback API version 1 is deprecated`. The dependency has no bounds, so a future
  release may remove the old signature and the service will crash at start-up.
- **Fix:** `mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)`; declare `paho-mqtt>=2.0,<3`.
- **Done when:** no `DeprecationWarning` when constructing the client (`-W error::DeprecationWarning` test).

### [x] P1-5 Validate configuration; fail fast `[code]`
- **Where:** `sensor.py:38-42`, `args.py`, `config.py`
- **Problem:** `host`, `username`, `password`, `topics` are read with `config[...]` deep inside the sensor
  function, so a missing key surfaces as a bare `KeyError` on the first cycle. Anonymous brokers can't be
  used (`username`/`password` mandatory). `topics` may be a string or list and may be empty (silently
  publishes nothing). No type checks for `port`/`debug`/`daemon`.
- **Fix:** A typed config (`dataclass` with a `validate()` step) built once at startup; required: `host`,
  non-empty `topics: list[str]`; optional credentials; exit with a readable message.
- **Done when:** parametrised tests cover missing host, empty topics, bad port, anonymous broker, YAML
  string vs list topics.

### [x] P1-6 Sensor accuracy: self-heating and start-up readings `[code]` `[hw]`
- **Where:** `sensor.py:44-55`
- **Problem:** The Sense HAT's temperature (and the humidity derived from it) reads several °C high because of
  Raspberry Pi CPU heat; there is no compensation or offset, so published values are systematically wrong
  for anyone who trusts them (e.g. Home Assistant). The first readings after creating `SenseHat()` are
  commonly stale/zero, and the code creates a new instance every cycle (P1-2) so it hits this each time; the
  median of 3 one-second samples only partly masks it.
- **Fix:** Add config `temperature_offset` and/or CPU-temperature-based compensation as a pure, unit-tested
  function; discard the first read after init; document accuracy limits in the README.
- **Done when:** compensation unit tests; README documents the option; on-Pi check that values are plausible.

### [x] P1-7 Fix the systemd unit `[verified for CRLF; code for the rest]`
- **Where:** `systemd/sensehatsensorstomqtt.service`, `Makefile` (`install-service`)
- **Problem:** Header says "Python Demo Service"; a commented `ExecStop`/`PIDFile` line refers to
  `enviroplussensorstomqtt` (copy-paste from the sibling project). `Restart=always` is declared and then
  overridden by a later `Restart=on-failure`. `RemainAfterExit=yes` is meaningless for `Type=simple`.
  `After=network.target` should be `network-online.target`. Runs as **root** with no hardening;
  `TimeoutStartSec=600` unexplained. CRLF line endings (only this file is CRLF in the repo). Unit does not
  pass `--config_file`. The installed wrapper hardcodes `$(CURDIR)/.venv/bin/...`, so moving/deleting the
  checkout silently breaks the service.
- **Fix:** Clean up comments and duplicate keys; `network-online.target`; run as a dedicated user in the
  groups the Sense HAT needs (`i2c`, `video`/framebuffer, `input` for the joystick; confirm on a Pi);
  add hardening (`NoNewPrivileges`, `ProtectSystem=strict`, `ProtectHome`, `PrivateTmp`, validated with
  `systemd-analyze security`); convert to LF; consider installing into a fixed venv path.
- **Done when:** `systemd-analyze verify` passes; no duplicate keys; `git ls-files --eol` shows LF.

### [x] P1-8 Remove the hand-rolled daemonizer `[code]`
- **Where:** `daemonizer.py`, `main.py:34-37`, `args.py` (`--daemon`, `--pid_file`), `config.py`, `logging.py`, `pyproject.toml` (`psutil`)
- **Problem:** Self-daemonising conflicts with systemd `Type=simple`, and the module has defects beyond P0-8:
  forks in a constructor; `start()` daemonises twice; `setpgrp()` instead of `setsid()`; `umask(0)`;
  redirects stdio after logging is set up; never removes the pidfile; assumes `/run/<name>/` exists;
  `___setup_pidfile` triple-underscore name; mixed quote styles.
- **Fix:** Delete it and the `--daemon`/`--pid_file` options (optionally deprecate for one release); drop
  `psutil`; document systemd as the supported background mode.
- **Done when:** no references remain; `psutil` removed from dependencies and `uv.lock`; README updated.

### [x] P1-9 Graceful shutdown, availability, configurable cadence `[code]`
- **Where:** `main.py:41-54`, `sensor.py:45-53`
- **Problem:** `while True` with no SIGTERM/SIGINT handling; `systemctl stop` can interrupt a read or an LED
  scroll mid-way and never disconnects from the broker. Retained messages stay forever with no
  availability/LWT signal, so a dead service looks like fresh data. The 60 s interval, number of samples (3)
  and the 1 s sample spacing are hardcoded. If a cycle overruns 60 s the loop does not sleep at all.
- **Fix:** `threading.Event`-driven loop and sleep; SIGTERM/SIGINT handlers; `will_set` + online/offline
  status topic; `interval`, `measurements` in config; `time.monotonic()`; enforce a minimum pause.
- **Done when:** tests with a fake clock/event verify cadence, overrun warning, clean shutdown and the
  offline publish.

### [x] P1-10 Payload hygiene `[code]`
- **Where:** `sensor.py:54-57`
- **Problem:** `datetime.utcnow()` is deprecated and returns a naive timestamp with microseconds and no
  offset. Values are unrounded floats (e.g. `24.38765`). `unit_of_*` keys repeat in every message. Pressure
  unit is "mbar" (numerically equal to hPa; fine, but undocumented).
- **Fix:** `datetime.now(datetime.UTC).isoformat(timespec="seconds")`; round (temp/humidity 0.01,
  pressure 0.1); document the payload schema (and keep existing keys, or add `schema_version`).
- **Done when:** README documents the schema; test asserts keys, types, rounding and an offset-aware timestamp.

---

## P2: Display, packaging, CI and docs

### [x] P2-1 LED display logic is tangled into publishing and is not configurable `[code]` `[hw]`
- **Where:** `sensor.py:77-101`, `utils.py`, `consts.py`, `colors.py`
- **Problem:** Display code lives inside `send_sensor_data`, runs after publishing and stretches each cycle
  (two 5 s pauses plus three blocking scrolls). It can't be disabled for headless/always-dark setups.
  `is_night()` hardcodes "hour <= 6 or >= 19", uses naive local time (DST/timezone dependent) and isn't
  configurable. `SLEEP_TIME_IN_SECONDS` actually controls the LED pause. Colours are random
  (`randint`), so output is non-deterministic and untestable. `is_night` has no type hints.
- **Fix:** Move to a `display.py` with `Display` interface (real + null); config keys `display: true/false`,
  `night_start`/`night_end` (or sunrise/sunset), `display_pause`; rename the constant; inject colour choice
  or seed it in tests.
- **Done when:** display can be disabled in config; unit tests cover the night window and the display being
  skipped; a failing display never affects publishing (see P0-7).

### [x] P2-2 Tests are shipped inside the wheel `[verified]`
- **Where:** `pyproject.toml` (`[tool.setuptools.packages.find]`), `src/tests/__init__.py`
- **Problem:** The built wheel contains top-level `tests/__init__.py` and `tests/test_config.py`.
- **Fix:** Move tests to repo-root `tests/` or set `include = ["sensehatsensorstomqtt*"]`; update Makefile/CI.
- **Done when:** the wheel contains only `sensehatsensorstomqtt/` and dist-info.

### [x] P2-3 Dependencies and metadata `[code]`
- **Where:** `pyproject.toml`
- **Problem:** `numpy<3.0.0` is declared but never imported by this code (transitive via `sense-hat`);
  `sense-hat` and `paho-mqtt` are unbounded; `pyyaml` is duplicated in the `tests` extra; `ruff` is
  installed ad hoc by the Makefile; `psutil` is only for the daemonizer and `setproctitle` is cosmetic
  (native build). Classifier `Topic :: Software Development :: Build Tools` is wrong; the `Download` URL
  (`v_01.tar.gz`) doesn't match version 0.0.4.
- **Fix:** Remove unused deps, add bounds, add a `dev` extra (`pytest`, `pytest-cov`, `ruff`, type checker),
  fix classifiers and URLs.
- **Done when:** `uv lock --check` passes; a clean install from metadata runs tests; `twine check` is clean.

### [x] P2-4 Makefile and CI `[code]`
- **Where:** `Makefile`, `.github/workflows/ci.yml`
- **Problem:** The Makefile hardcodes `/usr/bin/python3`, ignores `uv.lock` (`uv pip install -e`), and makes
  `test` depend on `install` (reinstalls on every run); `install-service` writes via `/tmp` with `echo`.
  CI runs one Python version (3.11), `setup-uv` is `version: "latest"`, actions are pinned by tag not SHA,
  and there is no coverage, type-check, wheel-contents or `systemd-analyze verify` step. CI is green only
  because no test imports the hardware-dependent modules (P1-1).
- **Fix:** `uv sync` from the lockfile; `PYTHON_BIN ?=`; split install and test; matrix 3.11-3.13; pin
  tool/action versions; add coverage gate, `ruff format --check`, `python -m build` + `twine check`.
- **Done when:** CI green on the matrix and fails on a deliberately broken test/wheel.

### [x] P2-5 Linting, typing and style `[code]`
- **Where:** `pyproject.toml`, all modules
- **Problem:** Ruff rules are only `E,F,W,I`; `B`, `UP` (flags `utcnow`, `= None` annotations), `S`, `SIM`,
  `N`, `RUF`, `ARG` are missing. No type checker. Mixed single/double-quote styles and mixed docstring
  styles (reST, Google, none). `args_handler(*, config_file: str = None)` is mis-annotated.
- **Fix:** Enable those rule sets and fix findings; add `mypy`/`pyright`; add `ruff format` and `pre-commit`
  (including `mixed-line-ending`).
- **Done when:** `ruff check`, `ruff format --check` and the type checker are clean in CI.

### [x] P2-6 README gaps `[code]`
- **Where:** `README.md`
- **Problem:** Omits enabling I2C (`raspi-config`), the need for `--system-site-packages` / apt
  `python3-sense-hat` when using the venv, the MQTT payload and units, retain/QoS behaviour, LED behaviour and
  the night window, the `log_file`/`pid_file` config keys, and troubleshooting. The CLI-only claim is false
  (P0-3) and `--topics` is broken (P0-1). Package docstrings contain typos ("messurements", "Sensehat") and
  `config.py`'s docstring example is the unrelated ML config. `colors.py` is documented as "Colors for terminal"
  although it drives the LED matrix.
- **Fix:** Rewrite with prerequisites, a config reference table, an example payload, security notes and
  troubleshooting; fix docstrings.
- **Done when:** a test diffs argparse options against the README so they can't drift.

### [x] P2-7 Housekeeping `[verified for CRLF]`
- **Where:** repo root
- **Problem:** No `.gitattributes` (CRLF already present in the unit file), no `CHANGELOG`, no tag/release
  process, no `SECURITY`/`CONTRIBUTING`. `colors.py` has ~20 unused colour constants.
- **Fix:** Add `.gitattributes` (`* text=auto eol=lf`), `CHANGELOG.md`, tag-driven versioning; trim
  `colors.py` to what is used.
- **Done when:** `git ls-files --eol` shows no CRLF in tracked text files.

---

## P3: Cleanup and features

### [x] P3-1 Extract the code shared with `enviroplus-sensors-to-mqtt`
- **Problem:** `args.py`, `config.py`, `logging.py`, `daemonizer.py`, `Makefile`, the systemd unit and CI are
  near-identical copies in both repos, and the copies have already diverged (this repo is missing the `int()`
  port conversion and has the `args.list` bug; the sibling has the correct versions). Every bug here exists
  or will exist there.
- **Fix:** Create a small shared package/template (config + CLI + logging + MQTT publisher + service
  scaffolding) or merge both into one project with pluggable sensor backends (`--board sensehat|enviroplus`).
- **Done when:** one implementation of config/args/logging/MQTT is used by both projects.

### [x] P3-2 Rename `logging.py`
- **Problem:** A module named `logging` inside the package invites shadowing of the stdlib module and
  contributed to P0-5. Also replace module-level `logging.info(...)` calls (which implicitly call
  `basicConfig()`) with per-module `LOGGER = logging.getLogger(__name__)`.
- **Fix:** Rename to `log_setup.py`; use named loggers everywhere.
- **Done when:** no module is named like a stdlib module; no bare `logging.info(` calls remain.

### [x] P3-3 MQTT and Home Assistant features
- **Problem:** The package docstring says the data goes "to Home Assistant", but there is no MQTT discovery,
  no per-metric topics, no TLS, no client id, no availability topic.
- **Fix (each optional, config-driven):** `tls` (CA/cert/key; `tls_insecure` off by default), `client_id`,
  `qos`, `retain`, per-metric subtopics, availability + LWT (P1-9), Home Assistant discovery payloads.
- **Done when:** each option has unit tests against a fake client and a README section.

### [x] P3-4 Additional Sense HAT data
- **Problem:** The IMU (accelerometer, gyroscope, magnetometer, orientation) and joystick are available but
  unused; a second humidity/temperature source (pressure sensor temperature) is ignored.
- **Fix:** Optional, feature-flagged fields with tolerant handling of unavailable sensors.
- **Done when:** unit tests with the fake `SenseHat`; README documents fields.

### [x] P3-5 Observability and release
- **Problem:** No health signal except tailing logs; not published to PyPI; no versioned releases.
- **Fix:** Status message (uptime, last-success time, error counter); optional `sd_notify` watchdog
  (`WatchdogSec=`); tag-triggered release workflow with trusted publishing, or document source-only install.
- **Done when:** watchdog heartbeat tested with a fake notifier; tagged release produces a verified artifact.

---

## Suggested order of attack

1. P0-1, P0-2, P0-3, P0-4, P0-5 (small, isolated, easy to test, high impact)
2. P1-1 (testability refactor + real tests): unlocks safe changes for everything else
3. P0-6, P0-7, P1-2, P1-3, P1-4, P1-9 (reliability and MQTT)
4. P1-8 (remove daemonizer; supersedes P0-8), P1-5, P1-7
5. P1-6, P1-10 (measurement and payload quality)
6. P2-* (display, packaging, CI, docs), then P3-*
7. Mirror every fix in `enviroplus-sensors-to-mqtt`, or do P3-1 early to avoid doing everything twice

## Verification notes (how these findings were established)

- Cloned `main` at `dc0a589`; `ruff check .` passes; `pytest` passes (1 test) after
  `pip install -e .[tests]` (sense-hat 2.6.0, paho-mqtt 2.1.0, numpy 2.5.3, pillow 12.3.0).
- Reproduced by execution: P0-1 (`AttributeError: 'Namespace' object has no attribute 'list'`),
  P0-2 (`port` is `str`; paho `connect` raises `TypeError` with a string port), P0-3 (`FileNotFoundError` with
  CLI-only flags), P0-4 (debug output contained `'password': 'secret123'`), P0-5 (`AttributeError: module
  'logging' has no attribute 'handlers'`), P1-1 (`ModuleNotFoundError: No module named 'RTIMU'` importing
  `main`), P1-4 (`DeprecationWarning: Callback API version 1 is deprecated`), P2-2 (wheel contains `tests/`),
  P2-7 (CRLF only in the systemd unit), and the `is_night` boundaries (06:30 night, 07:30 day, 18:30 day,
  19:30 night).
- Items tagged `[code]` come from reading the source and were not run on hardware; `[hw]` items need a
  Raspberry Pi with a Sense HAT to confirm.
