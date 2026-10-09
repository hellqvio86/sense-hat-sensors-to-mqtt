"""CLI arguments and configuration file resolution for Sense HAT to MQTT."""

import argparse
import os

from .config import apply_defaults, parse_config, validate_port


def _port_arg(value: str) -> int:
    try:
        return validate_port(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def args_handler(argv: list[str] | None = None, *, config_file: str | None = None) -> dict:
    """
    Function for reading arguments and config file

    Returns
    dict - config

    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", type=str, required=False)
    parser.add_argument("--password", type=str, required=False)
    parser.add_argument("--password_file", type=str, required=False)
    parser.add_argument("--host", type=str, required=False)
    parser.add_argument("--port", type=_port_arg, required=False)
    parser.add_argument("--topics", type=str, required=False)
    parser.add_argument("--qos", type=int, choices=[0, 1, 2], required=False)
    parser.add_argument("--retain", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--temperature_offset", type=float, required=False)
    parser.add_argument("--compensate_cpu_temp", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--cpu_temp_factor", type=float, required=False)
    parser.add_argument("--interval", type=float, required=False)
    parser.add_argument("--measurements", type=int, required=False)
    parser.add_argument("--sample_spacing", type=float, required=False)
    parser.add_argument("--status_topic", type=str, required=False)
    parser.add_argument("--display", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--display_pause", type=float, required=False)
    parser.add_argument("--night_start", type=int, required=False)
    parser.add_argument("--night_end", type=int, required=False)
    parser.add_argument("--client_id", type=str, required=False)
    parser.add_argument("--tls", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--tls_ca_certs", type=str, required=False)
    parser.add_argument("--tls_certfile", type=str, required=False)
    parser.add_argument("--tls_keyfile", type=str, required=False)
    parser.add_argument("--tls_insecure", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--per_metric_topics", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--ha_discovery", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--ha_discovery_prefix", type=str, required=False)
    parser.add_argument("--device_id", type=str, required=False)
    parser.add_argument("--include_imu", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--include_pressure_temp", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--config_file", type=str, required=False)
    parser.add_argument("--log_file", type=str, required=False)
    parser.add_argument("-D", "--debug", action="store_true")
    args = parser.parse_args(args=argv)

    if "config_file" in args and args.config_file:
        config = parse_config(config_file=args.config_file)
    elif config_file:
        config = parse_config(config_file=config_file)
    elif os.path.isfile("/etc/sensehatsensorstomqtt.yaml"):
        config = parse_config(config_file="/etc/sensehatsensorstomqtt.yaml")
    elif os.path.isfile("config.yaml"):
        config = parse_config(config_file="config.yaml")
    else:
        config = {}

    if "username" in args and args.username:
        config["username"] = args.username

    if "password" in args and args.password:
        config["password"] = args.password
    elif "password_file" in args and args.password_file:
        if not os.path.isfile(args.password_file):
            raise FileNotFoundError(f"Password file '{args.password_file}' not found.")
        with open(args.password_file, encoding="utf-8") as stream:
            config["password"] = stream.read().strip()
    elif os.environ.get("MQTT_PASSWORD"):
        config["password"] = os.environ["MQTT_PASSWORD"]
    elif config.get("password_file"):
        if not os.path.isfile(config["password_file"]):
            raise FileNotFoundError(f"Password file '{config['password_file']}' not found.")
        with open(config["password_file"], encoding="utf-8") as stream:
            config["password"] = stream.read().strip()

    if "host" in args and args.host:
        config["host"] = args.host

    if "port" in args and args.port is not None:
        config["port"] = args.port

    if "debug" in args and args.debug:
        config["debug"] = True

    if "log_file" in args and args.log_file:
        config["log_file"] = args.log_file

    if "topics" in args and args.topics is not None:
        topics = [item.strip() for item in args.topics.split(",") if item.strip()]
        if not topics:
            parser.error("Argument --topics must contain at least one non-empty topic.")
        config["topics"] = topics

    if "qos" in args and args.qos is not None:
        config["qos"] = args.qos

    if "retain" in args and args.retain is not None:
        config["retain"] = args.retain

    if "temperature_offset" in args and args.temperature_offset is not None:
        config["temperature_offset"] = args.temperature_offset

    if "compensate_cpu_temp" in args and args.compensate_cpu_temp is not None:
        config["compensate_cpu_temp"] = args.compensate_cpu_temp

    if "cpu_temp_factor" in args and args.cpu_temp_factor is not None:
        config["cpu_temp_factor"] = args.cpu_temp_factor

    if "interval" in args and args.interval is not None:
        config["interval"] = args.interval

    if "measurements" in args and args.measurements is not None:
        config["measurements"] = args.measurements

    if "sample_spacing" in args and args.sample_spacing is not None:
        config["sample_spacing"] = args.sample_spacing

    if "status_topic" in args and args.status_topic is not None:
        config["status_topic"] = args.status_topic

    if "display" in args and args.display is not None:
        config["display"] = args.display

    if "display_pause" in args and args.display_pause is not None:
        config["display_pause"] = args.display_pause

    if "night_start" in args and args.night_start is not None:
        config["night_start"] = args.night_start

    if "night_end" in args and args.night_end is not None:
        config["night_end"] = args.night_end

    if "client_id" in args and args.client_id is not None:
        config["client_id"] = args.client_id

    if "tls" in args and args.tls is not None:
        config["tls"] = args.tls

    if "tls_ca_certs" in args and args.tls_ca_certs is not None:
        config["tls_ca_certs"] = args.tls_ca_certs

    if "tls_certfile" in args and args.tls_certfile is not None:
        config["tls_certfile"] = args.tls_certfile

    if "tls_keyfile" in args and args.tls_keyfile is not None:
        config["tls_keyfile"] = args.tls_keyfile

    if "tls_insecure" in args and args.tls_insecure is not None:
        config["tls_insecure"] = args.tls_insecure

    if "per_metric_topics" in args and args.per_metric_topics is not None:
        config["per_metric_topics"] = args.per_metric_topics

    if "ha_discovery" in args and args.ha_discovery is not None:
        config["ha_discovery"] = args.ha_discovery

    if "ha_discovery_prefix" in args and args.ha_discovery_prefix is not None:
        config["ha_discovery_prefix"] = args.ha_discovery_prefix

    if "device_id" in args and args.device_id is not None:
        config["device_id"] = args.device_id

    if "include_imu" in args and args.include_imu is not None:
        config["include_imu"] = args.include_imu

    if "include_pressure_temp" in args and args.include_pressure_temp is not None:
        config["include_pressure_temp"] = args.include_pressure_temp

    config = apply_defaults(config)

    return config
