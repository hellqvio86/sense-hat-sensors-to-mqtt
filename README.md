# Sense Hat Sensors to MQTT

A python utility to publish data from Sense Hat sensors to an MQTT broker.

## Requirements

- Python 3.6+
- Raspberry Pi with a Sense Hat
- `make` (optional, for simplified build commands)
- `uv` (modern Python package manager, install with: `curl -LsSf https://astral.sh/uv/install.sh | sh`)

## Installation & Setup

We recommend using the included `Makefile` to handle creating a virtual environment and installing dependencies safely using `uv`.

### 1. Local Development / Virtual Environment

To set up a local virtual environment (`.venv`) and install dependencies:

```bash
make install
```

You can then run the tool directly from the virtual environment:
```bash
uv run sensehatsensorstomqtt
```
Alternatively, activate the venv directly and run it:
```bash
source .venv/bin/activate
sensehatsensorstomqtt
```

### 2. Running Tests & Linting

To run the test suite and `ruff` linting using `uv`:

```bash
make test
```

## Configuration

The application can be configured via command-line arguments or a YAML configuration file. It will look for a config file in the following order:
1. File specified by `--config_file`
2. `/etc/sensehatsensorstomqtt.yaml`
3. `config.yaml` in the current directory

### YAML Configuration Example

```yaml
host: "192.168.1.100"
port: 1883
username: "mqtt_user"
password: "mqtt_password"
topics:
  - "home/sensors/sensehat"
debug: false
daemon: false
```

### Command Line Arguments

You can override any YAML configuration via CLI flags:
- `--host`: MQTT broker host
- `--port`: MQTT broker port (default 1883)
- `--username`: MQTT username
- `--password`: MQTT password
- `--topics`: Comma-separated list of topics
- `--config_file`: Path to a custom YAML config file
- `--pid_file`: Path to store the PID file (useful when daemonized)
- `--log_file`: Path to the log file
- `-D, --debug`: Enable debug logging
- `--daemon`: Run as a background daemon process

## Systemd Service

To install this application as a background service managed by `systemd`, run:

```bash
make install-service
```

This command will:
1. Create a wrapper script in `/usr/local/bin/sensehatsensorstomqtt` that natively targets the `.venv` isolated environment in this folder.
2. Copy the systemd unit file from `systemd/sensehatsensorstomqtt.service` to `/etc/systemd/system/`.
3. Reload the systemd daemon.

After installation, you can enable and start the service:

```bash
sudo systemctl enable sensehatsensorstomqtt
sudo systemctl start sensehatsensorstomqtt
```

To view logs:
```bash
journalctl -u sensehatsensorstomqtt -f
```
