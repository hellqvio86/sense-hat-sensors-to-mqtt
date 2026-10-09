"""Configuration loading, validation, and defaults for Sense HAT to MQTT."""

import os
from dataclasses import asdict, dataclass, field, fields
from typing import Any

import yaml


@dataclass
class Config:
    """Typed and validated service configuration."""

    host: str = ""
    topics: list[str] = field(default_factory=list)
    port: int = 1883
    username: str | None = None
    password: str | None = None
    password_file: str | None = None
    debug: bool = False
    log_file: str | None = None
    qos: int = 1
    retain: bool = True
    publish_timeout: float = 5.0
    temperature_offset: float = 0.0
    compensate_cpu_temp: bool = False
    cpu_temp_factor: float = 5.466
    interval: float = 60.0
    measurements: int = 3
    sample_spacing: float = 1.0
    status_topic: str | None = None
    display: bool = True
    display_pause: float = 5.0
    night_start: int = 19
    night_end: int = 7
    client_id: str | None = None
    tls: bool = False
    tls_ca_certs: str | None = None
    tls_certfile: str | None = None
    tls_keyfile: str | None = None
    tls_insecure: bool = False
    per_metric_topics: bool = False
    ha_discovery: bool = False
    ha_discovery_prefix: str = "homeassistant"
    device_id: str = "sensehat"
    include_imu: bool = False
    include_pressure_temp: bool = False
    extra_fields: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        """Validate configuration values and normalize types."""
        if not self.host or not isinstance(self.host, str) or not self.host.strip():
            raise ValueError("Configuration 'host' is required and must not be empty.")
        self.host = self.host.strip()

        if self.topics is None:
            raise ValueError("Configuration 'topics' is required and must not be empty.")

        if isinstance(self.topics, str):
            self.topics = [t.strip() for t in self.topics.split(",") if t.strip()]
        elif isinstance(self.topics, list):
            self.topics = [str(t).strip() for t in self.topics if str(t).strip()]
        else:
            raise ValueError("Configuration 'topics' must be a list of strings or comma-separated string.")

        if not self.topics:
            raise ValueError("Configuration 'topics' must contain at least one non-empty topic.")

        self.port = validate_port(self.port)

        if not isinstance(self.debug, bool):
            if str(self.debug).lower() in ("true", "1", "yes"):
                self.debug = True
            elif str(self.debug).lower() in ("false", "0", "no"):
                self.debug = False
            else:
                raise ValueError(f"Invalid debug value: {self.debug!r}. Must be boolean.")

        try:
            self.qos = int(self.qos)
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Invalid MQTT QoS: {self.qos!r}. Must be an integer.") from exc
        if self.qos not in (0, 1, 2):
            raise ValueError(f"Invalid MQTT QoS: {self.qos}. Must be 0, 1, or 2.")

        if not isinstance(self.retain, bool):
            if str(self.retain).lower() in ("true", "1", "yes"):
                self.retain = True
            elif str(self.retain).lower() in ("false", "0", "no"):
                self.retain = False
            else:
                raise ValueError(f"Invalid retain value: {self.retain!r}. Must be boolean.")

        try:
            self.temperature_offset = float(self.temperature_offset)
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Invalid temperature_offset: {self.temperature_offset!r}. Must be a float.") from exc

        if not isinstance(self.compensate_cpu_temp, bool):
            if str(self.compensate_cpu_temp).lower() in ("true", "1", "yes"):
                self.compensate_cpu_temp = True
            elif str(self.compensate_cpu_temp).lower() in ("false", "0", "no"):
                self.compensate_cpu_temp = False
            else:
                raise ValueError(f"Invalid compensate_cpu_temp value: {self.compensate_cpu_temp!r}. Must be boolean.")

        try:
            self.cpu_temp_factor = float(self.cpu_temp_factor)
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Invalid cpu_temp_factor: {self.cpu_temp_factor!r}. Must be a float.") from exc

        try:
            self.interval = float(self.interval)
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Invalid interval: {self.interval!r}. Must be a float.") from exc
        if self.interval <= 0:
            raise ValueError(f"Interval must be greater than 0, got: {self.interval}")

        try:
            self.measurements = int(self.measurements)
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Invalid measurements: {self.measurements!r}. Must be an integer.") from exc
        if self.measurements < 1:
            raise ValueError(f"Measurements must be at least 1, got: {self.measurements}")

        try:
            self.sample_spacing = float(self.sample_spacing)
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Invalid sample_spacing: {self.sample_spacing!r}. Must be a float.") from exc
        if self.sample_spacing < 0:
            raise ValueError(f"sample_spacing must be non-negative, got: {self.sample_spacing}")

        if self.status_topic is not None:
            self.status_topic = str(self.status_topic).strip()
            if not self.status_topic:
                self.status_topic = None

        if not isinstance(self.display, bool):
            if str(self.display).lower() in ("true", "1", "yes"):
                self.display = True
            elif str(self.display).lower() in ("false", "0", "no"):
                self.display = False
            else:
                raise ValueError(f"Invalid display value: {self.display!r}. Must be boolean.")

        try:
            self.display_pause = float(self.display_pause)
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Invalid display_pause: {self.display_pause!r}. Must be a float.") from exc
        if self.display_pause < 0:
            raise ValueError(f"display_pause must be non-negative, got: {self.display_pause}")

        try:
            self.night_start = int(self.night_start)
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Invalid night_start: {self.night_start!r}. Must be an integer.") from exc
        if not (0 <= self.night_start <= 23):
            raise ValueError(f"night_start must be between 0 and 23, got: {self.night_start}")

        try:
            self.night_end = int(self.night_end)
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Invalid night_end: {self.night_end!r}. Must be an integer.") from exc
        if not (0 <= self.night_end <= 23):
            raise ValueError(f"night_end must be between 0 and 23, got: {self.night_end}")

        if self.client_id is not None:
            self.client_id = str(self.client_id).strip() or None

        if not isinstance(self.tls, bool):
            self.tls = str(self.tls).lower() in ("true", "1", "yes")

        if self.tls_ca_certs is not None:
            self.tls_ca_certs = str(self.tls_ca_certs).strip() or None

        if self.tls_certfile is not None:
            self.tls_certfile = str(self.tls_certfile).strip() or None

        if self.tls_keyfile is not None:
            self.tls_keyfile = str(self.tls_keyfile).strip() or None

        if not isinstance(self.tls_insecure, bool):
            self.tls_insecure = str(self.tls_insecure).lower() in ("true", "1", "yes")

        if not isinstance(self.per_metric_topics, bool):
            self.per_metric_topics = str(self.per_metric_topics).lower() in ("true", "1", "yes")

        if not isinstance(self.ha_discovery, bool):
            self.ha_discovery = str(self.ha_discovery).lower() in ("true", "1", "yes")

        if not isinstance(self.include_imu, bool):
            self.include_imu = str(self.include_imu).lower() in ("true", "1", "yes")

        if not isinstance(self.include_pressure_temp, bool):
            self.include_pressure_temp = str(self.include_pressure_temp).lower() in ("true", "1", "yes")

        if self.ha_discovery_prefix:
            self.ha_discovery_prefix = str(self.ha_discovery_prefix).strip()
        else:
            self.ha_discovery_prefix = "homeassistant"
        self.device_id = str(self.device_id).strip() if self.device_id else "sensehat"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Config":
        """Create a Config instance from a dictionary."""
        known_field_names = {f.name for f in fields(cls) if f.name != "extra_fields"}
        known = {}
        extra = {}
        for k, v in data.items():
            if k in known_field_names:
                known[k] = v
            else:
                extra[k] = v
        return cls(**known, extra_fields=extra)

    def __getitem__(self, item: str) -> Any:
        if hasattr(self, item) and item != "extra_fields":
            return getattr(self, item)
        if item in self.extra_fields:
            return self.extra_fields[item]
        raise KeyError(item)

    def __setitem__(self, key: str, value: Any) -> None:
        if hasattr(self, key) and key != "extra_fields":
            setattr(self, key, value)
        else:
            self.extra_fields[key] = value

    def __contains__(self, item: str) -> bool:
        return (hasattr(self, item) and item != "extra_fields") or item in self.extra_fields

    def get(self, item: str, default: Any = None) -> Any:
        if hasattr(self, item) and item != "extra_fields":
            val = getattr(self, item)
            return default if val is None else val
        return self.extra_fields.get(item, default)

    def keys(self):
        return [f.name for f in fields(self) if f.name != "extra_fields"] + list(self.extra_fields.keys())

    def __iter__(self):
        return iter(self.keys())

    def items(self):
        return [(k, self[k]) for k in self.keys()]

    def to_dict(self) -> dict[str, Any]:
        """Convert Config to a plain dictionary including extra_fields."""
        res = asdict(self)
        extra = res.pop("extra_fields", {})
        res.update(extra)
        return res


def validate_config(config: dict | Config) -> Config:
    """Validate and normalize configuration dictionary or Config instance."""
    cfg = config if isinstance(config, Config) else Config.from_dict(config)
    cfg.validate()
    return cfg


def validate_port(port: int | str) -> int:
    """Validate and convert port number."""
    try:
        port_int = int(port)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Port must be an integer, got: {port!r}") from exc
    if not (1 <= port_int <= 65535):
        raise ValueError(f"Port must be between 1 and 65535, got: {port_int}")
    return port_int


def apply_defaults(config: dict) -> dict:
    """Apply default configuration values and validate."""
    config.setdefault("debug", False)
    config.setdefault("port", 1883)
    config["port"] = validate_port(config["port"])
    config.setdefault("log_file", None)
    config.setdefault("qos", 1)
    try:
        config["qos"] = int(config["qos"])
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Invalid MQTT QoS: {config['qos']!r}. Must be an integer.") from exc
    if config["qos"] not in (0, 1, 2):
        raise ValueError(f"Invalid MQTT QoS: {config['qos']}. Must be 0, 1, or 2.")

    config.setdefault("retain", True)
    if not isinstance(config["retain"], bool):
        if str(config["retain"]).lower() in ("true", "1", "yes"):
            config["retain"] = True
        elif str(config["retain"]).lower() in ("false", "0", "no"):
            config["retain"] = False
        else:
            raise ValueError(f"Invalid retain value: {config['retain']!r}. Must be boolean.")

    config.setdefault("interval", 60.0)
    try:
        config["interval"] = float(config["interval"])
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Invalid interval: {config['interval']!r}. Must be a float.") from exc
    if config["interval"] <= 0:
        raise ValueError(f"Interval must be greater than 0, got: {config['interval']}")

    config.setdefault("measurements", 3)
    try:
        config["measurements"] = int(config["measurements"])
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Invalid measurements: {config['measurements']!r}. Must be an integer.") from exc
    if config["measurements"] < 1:
        raise ValueError(f"Measurements must be at least 1, got: {config['measurements']}")

    config.setdefault("sample_spacing", 1.0)
    try:
        config["sample_spacing"] = float(config["sample_spacing"])
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Invalid sample_spacing: {config['sample_spacing']!r}. Must be a float.") from exc
    if config["sample_spacing"] < 0:
        raise ValueError(f"sample_spacing must be non-negative, got: {config['sample_spacing']}")

    config.setdefault("status_topic", None)
    if config["status_topic"] is not None:
        config["status_topic"] = str(config["status_topic"]).strip()
        if not config["status_topic"]:
            config["status_topic"] = None

    config.setdefault("display", True)
    if not isinstance(config["display"], bool):
        if str(config["display"]).lower() in ("true", "1", "yes"):
            config["display"] = True
        elif str(config["display"]).lower() in ("false", "0", "no"):
            config["display"] = False
        else:
            raise ValueError(f"Invalid display value: {config['display']!r}. Must be boolean.")

    config.setdefault("display_pause", 5.0)
    try:
        config["display_pause"] = float(config["display_pause"])
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Invalid display_pause: {config['display_pause']!r}. Must be a float.") from exc
    if config["display_pause"] < 0:
        raise ValueError(f"display_pause must be non-negative, got: {config['display_pause']}")

    config.setdefault("night_start", 19)
    try:
        config["night_start"] = int(config["night_start"])
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Invalid night_start: {config['night_start']!r}. Must be an integer.") from exc
    if not (0 <= config["night_start"] <= 23):
        raise ValueError(f"night_start must be between 0 and 23, got: {config['night_start']}")

    config.setdefault("night_end", 7)
    try:
        config["night_end"] = int(config["night_end"])
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Invalid night_end: {config['night_end']!r}. Must be an integer.") from exc
    if not (0 <= config["night_end"] <= 23):
        raise ValueError(f"night_end must be between 0 and 23, got: {config['night_end']}")

    config.setdefault("client_id", None)
    config.setdefault("tls", False)
    config.setdefault("tls_ca_certs", None)
    config.setdefault("tls_certfile", None)
    config.setdefault("tls_keyfile", None)
    config.setdefault("tls_insecure", False)
    config.setdefault("per_metric_topics", False)
    config.setdefault("ha_discovery", False)
    config.setdefault("ha_discovery_prefix", "homeassistant")
    config.setdefault("device_id", "sensehat")

    return config


def redact_config(config: dict[str, Any] | Config) -> dict[str, Any]:
    """Return a shallow copy of config with sensitive fields redacted."""
    redacted = dict(config.to_dict()) if isinstance(config, Config) else dict(config)
    if redacted.get("password"):
        redacted["password"] = "***"  # noqa: S105
    return redacted


def parse_config(config_file: str = "config.yaml") -> dict:
    """
    Parse configuration file in YAML format.

    Args:
        config_file (str, optional): Path to configuration file. Defaults to "config.yaml".

    Returns:
        dict: A dictionary containing the parsed configuration values.

    Raises:
        FileNotFoundError: If the specified config file is not found.

    Examples:
        >>> parse_config("config.yaml")
        {
            'host': '192.168.1.100',
            'port': 1883,
            'topics': ['home/sensors/sensehat'],
            'qos': 1,
            'retain': True
        }
    """

    config = {}

    if not os.path.isfile(config_file):
        raise FileNotFoundError(f"Configuration file '{config_file}' not found.")

    with open(config_file, encoding="utf-8") as stream:
        config = yaml.safe_load(stream)

        if config is None:
            config = {}

    return apply_defaults(config)
