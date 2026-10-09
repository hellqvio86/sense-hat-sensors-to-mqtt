# Architecture Proposal: Shared Telemetry Service Framework

## 1. Executive Summary

Both `sense-hat-sensors-to-mqtt` and `enviroplus-sensors-to-mqtt` solve the same core problem:
reading physical sensors from a Raspberry Pi HAT on a periodic cadence and publishing structured telemetry
to MQTT brokers with systemd service lifecycle management.

Currently, common infrastructure—including configuration parsing, CLI overrides, logging configuration,
MQTT connection lifecycle, Home Assistant discovery, retry/exponential backoff loops, and systemd watchdog (`sd_notify`) integration—has been developed in parallel across both repositories.

This document proposes extracting the shared core into an independent, lightweight package:
`pi-sensors-to-mqtt-core` (or merging both backends into a unified CLI under `pi-sensors-to-mqtt`).

---

## 2. Common Components & Overlap

| Component | Responsibility in Both Projects | Current Implementation Status |
| :--- | :--- | :--- |
| **`Config` Dataclass** | Schema validation, environment variable reading (`MQTT_PASSWORD`), YAML file loading, type normalization | Present in both (`config.py`) |
| **`args.py`** | Argparse CLI handling, merging flags with YAML configuration, secure credential handling | Present in both (`args.py`) |
| **`log_setup.py`** | Configures handlers, log rotation (`RotatingFileHandler`), stderr fallback, level setting | Refactored in Sense HAT, needed in Enviro+ |
| **`MQTT Publisher`** | Persistent Paho 2.x client, reconnect loop, LWT (`status_topic`), TLS (certs, CA, key, insecure), HA discovery | Complete in Sense HAT (`sensor.py`) |
| **`Service Runner`** | Monotonic cadence timer, exponential backoff on consecutive failures, signal handling (`SIGTERM`/`SIGINT`), `sd_notify` watchdog | Complete in Sense HAT (`main.py`, `sd_notify.py`) |
| **Packaging & CI** | `uv sync`, systemd unit with sandboxing (`ProtectSystem=strict`, `NoNewPrivileges`), Ruff, Mypy, GitHub Actions matrix | Complete in Sense HAT |

---

## 3. Proposed Architecture: `pi-sensors-to-mqtt-core`

### 3.1 Class & Protocol Design

```python
from typing import Protocol, Any, runtime_checkable
import threading

@runtime_checkable
class SensorBackend(Protocol):
    """Protocol implemented by hardware-specific HAT drivers."""

    @property
    def name(self) -> str:
        """Name of the hardware HAT backend (e.g., 'sensehat', 'enviroplus')."""
        ...

    def initialize(self, config: "ServiceConfig") -> None:
        """Initialize hardware interfaces (I2C, SPI, serial)."""
        ...

    def sample(self, stop_event: threading.Event | None = None) -> dict[str, Any]:
        """Perform sensor sampling and return metric dictionary."""
        ...

    def post_sample(self, payload: dict[str, Any], stop_event: threading.Event | None = None) -> None:
        """Post-publish hook (e.g., update LED matrix or LCD screen)."""
        ...

    def close(self) -> None:
        """Release hardware resources."""
        ...
```

### 3.2 Service Lifecycle Engine

The service runner in `core` manages:
1. Signal traps (`SIGTERM`, `SIGINT`) -> sets `stop_event`.
2. Connects MQTT client with configured TLS, credentials, and LWT.
3. Notifies systemd `READY=1`.
4. Executes the sampling loop:
   - Records `monotonic()` start.
   - Calls `backend.sample(stop_event)`.
   - Formats payload (`time_utc`, rounding).
   - Publishes payload, per-metric topics, and HA discovery.
   - Calls `backend.post_sample(payload, stop_event)`.
   - Pings `WATCHDOG=1`.
   - Computes cadence remaining time and sleeps on `stop_event.wait(remaining)`.
5. On exit, publishes LWT `offline`, notifies `STOPPING=1`, closes backend.

---

## 4. Migration Plan

### Phase 1: Repository Alignment (Current)
- Complete all features in `sense-hat-sensors-to-mqtt` (P0 through P3 items).
- Backport bug fixes, `log_setup.py`, and Paho 2.x lifecycle to `enviroplus-sensors-to-mqtt`.

### Phase 2: Package Extraction
- Create repo `pi-sensors-to-mqtt-core` containing:
  - `pi_sensors_core.config`
  - `pi_sensors_core.mqtt`
  - `pi_sensors_core.runner`
  - `pi_sensors_core.sd_notify`
  - `pi_sensors_core.logging`
- Publish wheel to PyPI or vendored git dependency via `uv`.

### Phase 3: Driver Integration
- `sense-hat-sensors-to-mqtt` depends on `pi-sensors-to-mqtt-core` and implements `SenseHatBackend`.
- `enviroplus-sensors-to-mqtt` depends on `pi-sensors-to-mqtt-core` and implements `EnviroPlusBackend`.
