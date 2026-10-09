# Sense Hat Sensors to MQTT

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

A robust Python service for Raspberry Pi with a **Sense HAT**. Once per configurable cycle (default 60s), it samples temperature, humidity, and pressure using median filtering, publishes a structured JSON payload to one or more MQTT topics with retain and QoS, and optionally scrolls the measurements on the 8x8 LED matrix (unless in night mode).

---

## Prerequisites & Hardware Setup

### 1. Enable I2C Interface
The Sense HAT sensors communicate over the Raspberry Pi I2C bus. You must ensure I2C is enabled:

```bash
sudo raspi-config nonint do_i2c 0
```
*(Alternatively, run `sudo raspi-config` and navigate to **Interface Options** -> **I2C** -> **Yes**).*

Verify `/dev/i2c-1` exists:
```bash
ls -l /dev/i2c*
```

### 2. System Packages & Python Environment
The Sense HAT software stack depends on `RTIMULib` C bindings provided by the Raspberry Pi OS package `python3-sense-hat`.

Install the required apt packages:
```bash
sudo apt-get update
sudo apt-get install -y python3-dev gcc cmake python3-sense-hat libjpeg-dev zlib1g-dev libfreetype6-dev
```

> [!IMPORTANT]
> Because `sense-hat` relies on native `RTIMULib` in system site-packages, any Python virtual environment **must** be created with `--system-site-packages`. The included `Makefile` handles this automatically.

### 3. Install `uv`
This project uses [`uv`](https://docs.astral.sh/uv/) for fast, deterministic dependency management:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

## Installation & Setup

Clone the repository and install into a local virtual environment:

```bash
git clone https://github.com/hellqvio86/sense-hat-sensors-to-mqtt.git
cd sense-hat-sensors-to-mqtt
make install
```

This creates `.venv` with `--system-site-packages` and syncs all dependencies from `uv.lock`.

### Running Locally
Run the application with a YAML configuration file:
```bash
uv run sensehatsensorstomqtt --config_file ./config.yaml
```
Or run directly with CLI arguments:
```bash
uv run sensehatsensorstomqtt --host 192.168.1.100 --topics home/sensors/sensehat -D
```

### Running Tests & Linting
Run the test suite, Ruff linter, formatting checks, and Mypy type-checker:
```bash
make test
```

---

## Configuration

Configuration values are resolved with the following precedence (highest to lowest):
1. Command-line arguments (`--host`, `--port`, etc.)
2. Environment variables (`MQTT_PASSWORD`)
3. Configuration file in the following search order:
   - File specified via `--config_file <path>`
   - `/etc/sensehatsensorstomqtt.yaml`
   - `./config.yaml` (in current working directory)
4. Built-in defaults

### Example `config.yaml`

```yaml
host: "192.168.1.100"
port: 1883
username: "mqtt_user"
password: "mqtt_password"
# Or read password securely from file:
# password_file: "/etc/sensehat_mqtt.password"
topics:
  - "home/sensors/sensehat"
qos: 1
retain: true
publish_timeout: 5.0

# MQTT Client & Security
client_id: "sensehat-pi"
tls: false
tls_ca_certs: "/etc/ssl/certs/ca-certificates.crt"
tls_certfile: null
tls_keyfile: null
tls_insecure: false

# Topics & Home Assistant Discovery
per_metric_topics: false
ha_discovery: false
ha_discovery_prefix: "homeassistant"
device_id: "sensehat"

# Availability / Last Will and Testament (LWT)
status_topic: "home/sensors/sensehat/status"

# Cadence & Sampling
interval: 60.0
measurements: 3
sample_spacing: 1.0

# Sensor Calibration & CPU Compensation
temperature_offset: 0.0
compensate_cpu_temp: true
cpu_temp_factor: 5.466

# LED Matrix Display
display: true
display_pause: 5.0
night_start: 19
night_end: 7

# Logging
log_file: "/var/log/sensehatsensorstomqtt.log"
debug: false
```

### Configuration Reference Table

| Key | CLI Argument | Env Var | Type | Default | Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `host` | `--host` | | `string` | *(Required)* | MQTT broker hostname or IP address. |
| `port` | `--port` | | `integer` | `1883` | MQTT broker port (1–65535). |
| `username` | `--username` | | `string` | `None` | Username for authenticated MQTT brokers. |
| `password` | `--password` | `MQTT_PASSWORD` | `string` | `None` | Password for authenticated MQTT brokers. |
| `password_file` | `--password_file` | | `string` | `None` | Path to a file containing the MQTT password. |
| `topics` | `--topics` | | `list` / `csv` | *(Required)* | MQTT topics to publish sensor telemetry to. |
| `qos` | `--qos` | | `integer` | `1` | MQTT Quality of Service level (`0`, `1`, or `2`). |
| `retain` | `--retain` / `--no-retain` | | `boolean` | `true` | Whether MQTT messages are published with the retain flag. |
| `publish_timeout`| | | `float` | `5.0` | Timeout in seconds waiting for MQTT broker publish acknowledgment. |
| `client_id` | `--client_id` | | `string` | `None` | Explicit MQTT client ID. |
| `tls` | `--tls` / `--no-tls` | | `boolean` | `false` | Enable TLS encryption for MQTT connection. |
| `tls_ca_certs` | `--tls_ca_certs` | | `string` | `None` | Path to CA certificates file for TLS verification. |
| `tls_certfile` | `--tls_certfile` | | `string` | `None` | Path to client certificate file for mutual TLS. |
| `tls_keyfile` | `--tls_keyfile` | | `string` | `None` | Path to client private key file for mutual TLS. |
| `tls_insecure` | `--tls_insecure` / `--no-tls_insecure` | | `boolean` | `false` | Disable server certificate hostname verification. |
| `per_metric_topics` | `--per_metric_topics` / `--no-per_metric_topics` | | `boolean` | `false` | Also publish individual values to `{topic}/{metric}` subtopics. |
| `ha_discovery` | `--ha_discovery` / `--no-ha_discovery` | | `boolean` | `false` | Enable Home Assistant MQTT Discovery entity registration. |
| `ha_discovery_prefix` | `--ha_discovery_prefix` | | `string` | `homeassistant` | MQTT topic prefix for Home Assistant discovery. |
| `device_id` | `--device_id` | | `string` | `sensehat` | Unique device identifier used in Home Assistant discovery. |
| `include_imu` | `--include_imu` / `--no-include_imu` | | `boolean` | `false` | Include IMU sensors (orientation, accelerometer, gyroscope, compass) in payload. |
| `include_pressure_temp` | `--include_pressure_temp` / `--no-include_pressure_temp` | | `boolean` | `false` | Include temperature read from the pressure sensor in payload. |
| `status_topic` | `--status_topic` | | `string` | `None` | LWT and availability topic (`online` / `offline`). |
| `interval` | `--interval` | | `float` | `60.0` | Cadence interval in seconds between publication cycles. |
| `measurements` | `--measurements` | | `integer` | `3` | Number of samples taken per cycle for median filtering ($\ge 1$). |
| `sample_spacing` | `--sample_spacing`| | `float` | `1.0` | Delay in seconds between individual sensor sample reads. |
| `temperature_offset` | `--temperature_offset` | | `float` | `0.0` | Manual temperature offset in °C subtracted from readings. |
| `compensate_cpu_temp` | `--compensate_cpu_temp` / `--no-compensate_cpu_temp` | | `boolean` | `false` | Compensate for Raspberry Pi CPU heat radiation. |
| `cpu_temp_factor` | `--cpu_temp_factor` | | `float` | `5.466` | Scaling factor for CPU temperature compensation. |
| `display` | `--display` / `--no-display` | | `boolean` | `true` | Enable or disable the 8x8 LED matrix display. |
| `display_pause` | `--display_pause` | | `float` | `5.0` | Pause in seconds between messages scrolling on the LED matrix. |
| `night_start` | `--night_start` | | `integer` | `19` | Local hour (0–23) when night mode starts (turns LED matrix off). |
| `night_end` | `--night_end` | | `integer` | `7` | Local hour (0–23) when night mode ends (turns LED matrix on). |
| `log_file` | `--log_file` | | `string` | `None` | Path to rotating log file. Defaults to stderr. |
| `debug` | `-D`, `--debug` | | `boolean` | `false` | Enable verbose debug logging (passwords are redacted). |

---

## MQTT Payload Schema

Each cycle publishes a single JSON object to the configured topic(s):

```json
{
  "temperature": 21.45,
  "humidity": 45.20,
  "pressure": 1013.2,
  "unit_of_temperature": "C",
  "unit_of_humidity": "%",
  "unit_of_pressure": "mbar",
  "time_utc": "2026-10-09T10:15:30+00:00"
}
```

### Fields & Units
- `temperature` (`float`): Ambient temperature in degrees Celsius (°C), rounded to 2 decimal places (`0.01`). Calibrated by `temperature_offset` and/or `compensate_cpu_temp`.
- `humidity` (`float`): Relative humidity in percent (`%`), rounded to 2 decimal places (`0.01`).
- `pressure` (`float`): Atmospheric pressure in millibars (hPa), rounded to 1 decimal place (`0.1`). Note: $1\text{ mbar} = 1\text{ hPa} = 100\text{ Pa}$.
- `unit_of_temperature` (`string`): Temperature unit (`"C"`).
- `unit_of_humidity` (`string`): Humidity unit (`"%"`).
- `unit_of_pressure` (`string`): Pressure unit (`"mbar"`).
- `time_utc` (`string`): Timezone-aware ISO-8601 UTC timestamp with second precision (`YYYY-MM-DDTHH:MM:SS+00:00`).
- `pressure_temperature` (`float`, optional): Temperature in °C from the pressure sensor when `include_pressure_temp` is enabled.
- `orientation` (`object`, optional): IMU pitch, roll, and yaw angles in degrees when `include_imu` is enabled.
- `accelerometer` (`object`, optional): Raw acceleration vector (`x`, `y`, `z`) in Gs when `include_imu` is enabled.
- `gyroscope` (`object`, optional): Raw rotational velocity vector (`x`, `y`, `z`) in rad/s when `include_imu` is enabled.
- `compass` (`object`, optional): Raw magnetic field vector (`x`, `y`, `z`) in microteslas ($\mu\text{T}$) when `include_imu` is enabled.

---

## Sensor Calibration & Accuracy

The Raspberry Pi Sense HAT sits directly above the Pi CPU and SoC. As a result, heat generated by the board causes raw Sense HAT temperature readings to run significantly higher than ambient room temperature, which also distorts relative humidity calculations.

To improve temperature accuracy, two calibration mechanisms are supported:

1. **Manual Offset (`temperature_offset`)**: Subtracts a fixed degree Celsius offset (e.g. `3.5`) from the measured temperature:
   ```yaml
   temperature_offset: 3.5
   ```
2. **CPU Temperature Compensation (`compensate_cpu_temp`)**: Reads Pi CPU temperature from `/sys/class/thermal/thermal_zone0/temp` each cycle and calculates ambient temperature using:
   $$\text{temp} = \text{temp}_{\text{raw}} - \frac{\text{temp}_{\text{cpu}} - \text{temp}_{\text{raw}}}{\text{factor}} - \text{offset}$$
   The scaling factor can be tuned via `cpu_temp_factor` (default `5.466`, typical range `1.2`–`5.5` depending on enclosure and airflow).

On startup, initial sensor readings are primed and discarded to prevent publishing uncalibrated or stale initial values.

---

## LED Matrix Display & Night Mode

When `display: true` (the default), the service scrolls current readings on the Sense HAT 8x8 LED matrix after each publish cycle.

- **Night Window**: Between `night_start` (default `19` / 7 PM) and `night_end` (default `7` / 7 AM), the LED matrix is kept completely dark to avoid disturbance.
- **Headless Mode**: For server closets or always-dark installations, set `display: false` or pass `--no-display` to completely disable the LED matrix and save power.
- **Non-blocking Loop**: If the LED display encounters an error or hardware disconnect, display failures are logged safely without interrupting sensor publishing.

---

## Security Best Practices

1. **Do not put plaintext passwords in command-line arguments**: Flags like `--password` are visible in `ps` and `/proc/*/cmdline`. Use `MQTT_PASSWORD` environment variable or `password_file` instead.
2. **Secure file permissions**: Ensure your config and password files are restricted:
   ```bash
   chmod 600 config.yaml /etc/sensehat_mqtt.password
   ```
3. **Automatic Log Redaction**: Passwords are automatically redacted (`***`) in debug output and logs.

---

## Systemd Service Installation

To install this application as a hardened system service managed by `systemd`:

```bash
make install-service
```

This command will:
1. Ensure the system user `sensehat` exists with memberships in `i2c`, `video`, and `input` groups.
2. Install the wrapper executable directly to `/usr/local/bin/sensehatsensorstomqtt`.
3. Install the hardened systemd unit file from `systemd/sensehatsensorstomqtt.service` into `/etc/systemd/system/`.
4. Reload `systemd`.

Enable and start the service:
```bash
sudo systemctl enable sensehatsensorstomqtt
sudo systemctl start sensehatsensorstomqtt
```

Check status and follow live logs:
```bash
sudo systemctl status sensehatsensorstomqtt
journalctl -u sensehatsensorstomqtt -f
```

---

## Troubleshooting

### `ModuleNotFoundError: No module named 'RTIMU'`
- **Cause**: The native `RTIMULib` C library from Raspberry Pi OS is missing, or the virtual environment was created without access to system site-packages.
- **Fix**: Install the apt package and recreate the virtual environment:
  ```bash
  sudo apt-get install -y python3-sense-hat
  make clean && make install
  ```

### `PermissionError: [Errno 13] Permission denied: '/dev/i2c-1'`
- **Cause**: The current user or service account lacks permissions to access the I2C device bus.
- **Fix**: Add your user to the necessary hardware groups:
  ```bash
  sudo usermod -aG i2c,video,input $USER
  ```
  *(Log out and back in for group changes to take effect).*

### `ConnectionRefusedError` or MQTT Publish Timeout
- **Cause**: The broker is unreachable, offline, or rejecting credentials.
- **Fix**: Verify your broker address and port with `ping` or `mosquitto_sub`:
  ```bash
  mosquitto_sub -h <broker-ip> -p 1883 -u <user> -P <pass> -t "test"
  ```

### LED Matrix is Dark During the Day
- **Cause**: Check if `night_start` and `night_end` match your system timezone. Ensure system time is correct:
  ```bash
  timedatectl
  ```
  Or check if `--no-display` or `display: false` was set in your configuration.
