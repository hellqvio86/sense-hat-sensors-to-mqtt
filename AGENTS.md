# AGENTS.md

Guidance for AI coding agents working in this repository. Humans: see `README.md`.
Open work items live in `todo.md` (prioritised, with acceptance criteria). Start there.

## What this project is

`sensehatsensorstomqtt` is a small Python service for a Raspberry Pi with a **Sense HAT**. Once per
cycle (~60 s) it reads temperature, humidity and pressure (median of 3 samples), publishes **one JSON
object** to one or more MQTT topics (retained), and then scrolls the values on the 8x8 LED matrix
(unless it is "night").

- Runs as a long-lived process, normally under systemd.
- Status: alpha (`0.0.x`). CLI flags, config keys and the JSON payload are consumed by other systems
  (Home Assistant etc.). Treat them as public interfaces; do not rename them casually.
- This repo shares much of its code (args, config, logging, daemonizer, Makefile, systemd unit, CI) with
  the sibling project `enviroplus-sensors-to-mqtt`. When you fix a shared module here, note in the PR
  that the sibling needs the same fix (or that the code should move to a shared package; see `todo.md`).

## Repository layout

```
src/sensehatsensorstomqtt/
  main.py        entry point `main()`; forever-loop: read -> publish -> sleep to 60 s
  args.py        argparse + config-file resolution + CLI overrides -> returns a plain dict
  config.py      YAML loading and defaults
  sensor.py      Sense HAT reads + MQTT publish + LED display (all in one function)
  utils.py       `is_night()` (hardcoded local-time window used to disable the LED display)
  consts.py      measurement units; `SLEEP_TIME_IN_SECONDS` (actually the LED pause)
  colors.py      LED text colours (mostly unused constants)
  log_setup.py   logger setup and formatting
  display.py     LED matrix display implementation and abstractions
  hardware.py    Sense HAT hardware factory
tests/          pytest test suite
systemd/         unit file installed by `make install-service`
Makefile         venv / install / test / clean / install-service
pyproject.toml   setuptools build, ruff config, console script `sensehatsensorstomqtt`
uv.lock          lockfile (installed from via uv sync)
.github/         CI matrix (3.11-3.13) and Dependabot (uv & github-actions)
```

## Commands

Run before declaring any task done:

```bash
make install     # uv venv (--system-site-packages, $(PYTHON_BIN)) + uv sync --extra dev
make test        # uv run ruff check . && uv run ruff format --check src tests && uv run pytest tests/
```

Inner loop once installed:

```bash
uv run ruff check .            # add --fix for import sorting
uv run ruff format --check src tests
uv run pytest tests/ -q
```

Run the app (Pi + Sense HAT required; fails elsewhere):

```bash
uv run sensehatsensorstomqtt --config_file ./config.yaml -D
```

Requires Python >= 3.11.

## Environment constraints you must respect

- **The sandbox has no Sense HAT, and `import sense_hat` fails there** (`ModuleNotFoundError: RTIMU`;
  the native `RTIMULib` comes from the apt package `python3-sense-hat`). Consequently
  `import sensehatsensorstomqtt.main` and `...sensor` also fail off-device. Tests for those modules must
  inject a fake `sense_hat` into `sys.modules` (see `conftest.py` pattern in `todo.md` P1-1) *before*
  importing them. Never call the real `SenseHat()` in tests.
- **No broker / network in tests.** Use a fake MQTT client object.
- **LED matrix calls block.** `SenseHat.show_message` scrolls synchronously for seconds. Any change to
  the display path must keep it optional and must not break the publish cadence.
- Target is Raspberry Pi OS (Bookworm, Python 3.11). Avoid dependencies needing compilers or large native
  libs (Pillow is already a heavy transitive dependency of `sense-hat`).
- The service currently runs as **root** under systemd. Don't write code that assumes root; don't widen privileges.

## Code conventions

- Lint/format: `ruff`, line length 120, rules `E,F,W,I`, target `py311`. Keep `ruff check .` clean;
  fix code rather than disabling rules.
- Type-hint new/changed functions; use `str | None` rather than `x: str = None`.
- Logging: use `LOGGER = logging.getLogger(__name__)` in each module. The existing code calls
  module-level `logging.info(...)`, which only works because it triggers an implicit `basicConfig()`;
  do not copy that pattern. Lazy formatting (`LOGGER.info("x %s", y)`). No `print` for operational output.
- Separate concerns when you touch `sensor.py`: *read sensors*, *build payload*, *publish*, *display*.
- Use timezone-aware datetimes (`datetime.now(datetime.UTC)`), not `utcnow()`.
- Commit messages: Conventional Commits (`fix:`, `feat:`, `chore:`, `test:`, `docs:`, `refactor:`).

## Things that will bite you

1. **Secrets.** The debug config dump prints the MQTT password (twice: `main.py` and `args.py`). Never
   log or print the config dict or credentials. Do not add real credentials to tests, fixtures or docs.
2. **Payload compatibility.** Keys `temperature`, `humidity`, `pressure`, `unit_of_temperature`,
   `unit_of_humidity`, `unit_of_pressure`, `time_utc` are consumed downstream. Renaming, removing or
   changing units/format of a key is a breaking change: flag it and update the README.
3. **Blocking cycle.** One cycle = 3 sensors x 3 samples x 1 s of sleeps, plus up to ~10 s of LED pauses
   plus scroll time, inside a 60 s cadence. Do not add slow work without checking the budget.
4. **Resource lifetime.** `SenseHat()` and `mqtt.Client()` are created every cycle and never closed. Don't
   add more per-cycle allocations; if you touch this code, release what you open.
5. **Daemon mode is legacy.** `--daemon`/`daemonizer.py` duplicates systemd and has known bugs. Don't
   extend it; remove or fix it only as described in `todo.md`.
6. **Don't edit `uv.lock` by hand.** Use `uv lock` / `uv add` / `uv remove`.
7. **CRLF.** `systemd/sensehatsensorstomqtt.service` has CRLF endings. Don't create mixed endings;
   normalise whole files when you touch them.
8. Tests live in `tests/` and are excluded from the wheel distribution.
9. The existing `test_config.py` uses a copy-pasted ML-style config (`model`, `learning_rate`) that has
   nothing to do with this project. Don't model new tests on it.

## Working agreement for agents

- Take the highest-priority unchecked item in `todo.md` unless told otherwise; one item per change set;
  tick its checkbox in the same PR.
- Every bug fix needs a regression test that fails before and passes after.
- No drive-by refactors; add a new item to `todo.md` instead.
- If verification needs real hardware, say so in the PR and list exactly what a human must check on a Pi.
  Do not claim hardware behaviour you could not observe.
- If an instruction here conflicts with an explicit user request, follow the user and flag the conflict.

## Definition of done

- [ ] `make test` passes (ruff + pytest) from a clean `make clean && make install`
- [ ] New/changed behaviour has unit tests that run without hardware or network
- [ ] No secrets in logs, tests, fixtures or docs
- [ ] README / `todo.md` updated if CLI flags, config keys, payload or install steps changed
- [ ] No new unpinned or undeclared dependencies
