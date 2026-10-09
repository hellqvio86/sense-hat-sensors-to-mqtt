"""Sense HAT sensor reading, calibration, and MQTT publishing."""

from __future__ import annotations

import contextlib
import datetime
import json
import logging
import threading
from statistics import median
from time import sleep
from typing import TYPE_CHECKING, Any

from paho.mqtt.client import CallbackAPIVersion
from paho.mqtt.client import Client as MqttClient

from .consts import DEFAULT_DISPLAY_PAUSE, MEASUREMENT_UNIT
from .display import Display, SenseHatDisplay, get_display
from .hardware import get_sense_hat

if TYPE_CHECKING:
    from .config import Config

LOGGER = logging.getLogger(__name__)


def compensate_temperature(
    raw_temp: float,
    cpu_temp: float | None = None,
    factor: float = 5.466,
    offset: float = 0.0,
) -> float:
    """Compensate Sense HAT raw temperature for CPU self-heating and manual offset."""
    temp = raw_temp
    if cpu_temp is not None:
        temp = temp - ((cpu_temp - temp) / factor)
    temp = temp - offset
    return round(temp, 2)


def get_cpu_temperature(path: str = "/sys/class/thermal/thermal_zone0/temp") -> float | None:
    """Read CPU temperature in Celsius from sysfs thermal zone if available."""
    try:
        with open(path, encoding="utf-8") as f:
            content = f.read().strip()
            return float(content) / 1000.0
    except (OSError, ValueError):
        return None


def read_measurements(
    sense: object,
    measurements: int = 3,
    temperature_offset: float = 0.0,
    cpu_temp: float | None = None,
    cpu_factor: float = 5.466,
    sample_spacing: float = 1.0,
    stop_event: threading.Event | None = None,
    include_imu: bool = False,
    include_pressure_temp: bool = False,
) -> dict[str, Any]:
    """Read temperature, humidity, and pressure measurements (plus optional IMU) from Sense HAT."""
    readings: dict[str, Any] = {}
    for sensor_type in ["temperature", "humidity", "pressure"]:
        tmp = []
        for i in range(measurements):
            if stop_event is not None and stop_event.is_set():
                break
            sensor_value = getattr(sense, f"get_{sensor_type}")()
            LOGGER.debug("%s - measurement %s value: %s", sensor_type, i, sensor_value)
            tmp.append(sensor_value)
            if measurements > 1 and i < measurements - 1:
                if stop_event is not None:
                    stop_event.wait(sample_spacing)
                    if stop_event.is_set():
                        break
                else:
                    sleep(sample_spacing)
        if not tmp:
            tmp.append(float(getattr(sense, f"get_{sensor_type}")()))
        median_val = float(median(tmp))
        if sensor_type == "temperature":
            readings[sensor_type] = compensate_temperature(
                raw_temp=median_val,
                cpu_temp=cpu_temp,
                factor=cpu_factor,
                offset=temperature_offset,
            )
        elif sensor_type == "humidity":
            readings[sensor_type] = round(median_val, 2)
        elif sensor_type == "pressure":
            readings[sensor_type] = round(median_val, 1)
        else:
            readings[sensor_type] = median_val

    if include_pressure_temp and hasattr(sense, "get_temperature_from_pressure"):
        try:
            pt = float(sense.get_temperature_from_pressure())
            readings["pressure_temperature"] = compensate_temperature(
                raw_temp=pt,
                cpu_temp=cpu_temp,
                factor=cpu_factor,
                offset=temperature_offset,
            )
        except Exception as exc:
            LOGGER.debug("Could not read pressure sensor temperature: %s", exc)

    if include_imu:
        if hasattr(sense, "get_orientation"):
            try:
                orient = sense.get_orientation()
                if isinstance(orient, dict):
                    readings["orientation"] = {
                        k: round(float(v), 2) for k, v in orient.items() if isinstance(v, (int, float))
                    }
            except Exception as exc:
                LOGGER.debug("Could not read orientation: %s", exc)
        if hasattr(sense, "get_accelerometer_raw"):
            try:
                accel = sense.get_accelerometer_raw()
                if isinstance(accel, dict):
                    readings["accelerometer"] = {
                        k: round(float(v), 3) for k, v in accel.items() if isinstance(v, (int, float))
                    }
            except Exception as exc:
                LOGGER.debug("Could not read accelerometer: %s", exc)
        if hasattr(sense, "get_gyroscope_raw"):
            try:
                gyro = sense.get_gyroscope_raw()
                if isinstance(gyro, dict):
                    readings["gyroscope"] = {
                        k: round(float(v), 3) for k, v in gyro.items() if isinstance(v, (int, float))
                    }
            except Exception as exc:
                LOGGER.debug("Could not read gyroscope: %s", exc)
        if hasattr(sense, "get_compass_raw"):
            try:
                compass = sense.get_compass_raw()
                if isinstance(compass, dict):
                    readings["compass"] = {
                        k: round(float(v), 3) for k, v in compass.items() if isinstance(v, (int, float))
                    }
            except Exception as exc:
                LOGGER.debug("Could not read compass: %s", exc)

    return readings


def build_payload(measurements: dict[str, Any]) -> dict[str, object]:
    """Construct JSON payload dictionary with measurements and metadata."""
    msg: dict[str, object] = {
        "temperature": round(float(measurements["temperature"]), 2),
        "humidity": round(float(measurements["humidity"]), 2),
        "pressure": round(float(measurements["pressure"]), 1),
        "unit_of_temperature": MEASUREMENT_UNIT["temperature"],
        "unit_of_humidity": MEASUREMENT_UNIT["humidity"],
        "unit_of_pressure": MEASUREMENT_UNIT["pressure"],
        "time_utc": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"),
    }
    if "pressure_temperature" in measurements:
        msg["pressure_temperature"] = measurements["pressure_temperature"]
    if "orientation" in measurements:
        msg["orientation"] = measurements["orientation"]
    if "accelerometer" in measurements:
        msg["accelerometer"] = measurements["accelerometer"]
    if "gyroscope" in measurements:
        msg["gyroscope"] = measurements["gyroscope"]
    if "compass" in measurements:
        msg["compass"] = measurements["compass"]
    return msg


def publish_status(
    mqtt_client: MqttClient,
    config: dict[str, Any] | Config | Any,
    status: str | dict[str, Any],
    wait: bool = False,
    timeout: float = 2.0,
) -> None:
    """Publish availability status (online/offline or telemetry heartbeat) to status_topic if configured."""
    if not hasattr(config, "get"):
        return
    status_topic = config.get("status_topic")
    if not status_topic:
        return
    qos = int(config.get("qos", 1))
    retain = bool(config.get("retain", True))
    payload = json.dumps(status).encode("utf-8") if isinstance(status, dict) else str(status).encode("utf-8")
    try:
        info = mqtt_client.publish(topic=status_topic, payload=payload, qos=qos, retain=retain)
        if wait and info is not None and hasattr(info, "wait_for_publish"):
            try:
                info.wait_for_publish(timeout=timeout)
            except Exception as exc:
                LOGGER.warning("Failed waiting for status publish to %s: %s", status_topic, exc)
    except Exception as exc:
        LOGGER.warning("Failed to publish status %s to %s: %s", status, status_topic, exc)


def on_mqtt_connect(client: MqttClient, userdata: object, _flags: object, rc: object, *_args: object) -> None:
    """Callback for MQTT connection."""
    rc_code = getattr(rc, "value", rc)
    if rc_code == 0:
        LOGGER.info("MQTT connection established")
        if isinstance(userdata, dict) and "config" in userdata:
            publish_status(mqtt_client=client, config=userdata["config"], status="online")
    else:
        LOGGER.error("MQTT connection failed with return code %s", rc)


def on_mqtt_disconnect(_client: MqttClient, _userdata: object, *args: object) -> None:
    """Callback for MQTT disconnect."""
    LOGGER.warning("MQTT disconnected: %s", args)


HA_DISCOVERY_SENSORS = [
    {
        "metric": "temperature",
        "name": "Temperature",
        "device_class": "temperature",
        "unit": "°C",
        "state_class": "measurement",
        "value_template": "{{ value_json.temperature }}",
    },
    {
        "metric": "humidity",
        "name": "Humidity",
        "device_class": "humidity",
        "unit": "%",
        "state_class": "measurement",
        "value_template": "{{ value_json.humidity }}",
    },
    {
        "metric": "pressure",
        "name": "Pressure",
        "device_class": "pressure",
        "unit": "hPa",
        "state_class": "measurement",
        "value_template": "{{ value_json.pressure }}",
    },
]


def publish_ha_discovery(
    mqtt_client: MqttClient,
    config: dict[str, Any] | Config | Any,
    topics: list[str],
) -> None:
    """Publish Home Assistant MQTT discovery sensor configurations."""
    if not bool(config.get("ha_discovery", False)):
        return
    prefix = str(config.get("ha_discovery_prefix", "homeassistant"))
    device_id = str(config.get("device_id", "sensehat"))
    status_topic = config.get("status_topic")
    state_topic = topics[0] if topics else f"{device_id}/sensors"
    qos = int(config.get("qos", 1))

    device_info = {
        "identifiers": [device_id],
        "name": f"Sense HAT ({device_id})",
        "model": "Raspberry Pi Sense HAT",
        "manufacturer": "Raspberry Pi",
    }

    for sensor in HA_DISCOVERY_SENSORS:
        metric = sensor["metric"]
        disc_topic = f"{prefix}/sensor/{device_id}/{metric}/config"
        disc_payload: dict[str, Any] = {
            "name": f"{device_id} {sensor['name']}",
            "unique_id": f"{device_id}_{metric}",
            "state_topic": state_topic,
            "value_template": sensor["value_template"],
            "device_class": sensor["device_class"],
            "unit_of_measurement": sensor["unit"],
            "state_class": sensor["state_class"],
            "device": device_info,
        }
        if status_topic:
            disc_payload["availability_topic"] = status_topic
            disc_payload["payload_available"] = "online"
            disc_payload["payload_not_available"] = "offline"

        data = json.dumps(disc_payload).encode("utf-8")
        LOGGER.info("Publishing HA discovery for %s to %s", metric, disc_topic)
        with contextlib.suppress(Exception):
            mqtt_client.publish(topic=disc_topic, payload=data, qos=qos, retain=True)


def publish(config: dict[str, Any] | Config | Any, payload: dict[str, Any], mqtt_client: MqttClient) -> None:
    """Connect and publish payload to configured MQTT broker and topics."""
    host = config["host"]
    username = config.get("username")
    password = config.get("password")
    port = int(config.get("port", 1883))
    topics = config["topics"]
    if isinstance(topics, str):
        topics = [t.strip() for t in topics.split(",") if t.strip()]
    qos = int(config.get("qos", 1))
    retain = bool(config.get("retain", True))
    publish_timeout = float(config.get("publish_timeout", 5.0))
    tls_enabled = bool(config.get("tls", False)) or bool(config.get("tls_ca_certs"))
    per_metric_topics = bool(config.get("per_metric_topics", False))

    if not hasattr(mqtt_client, "on_connect") or mqtt_client.on_connect is None:
        with contextlib.suppress(Exception):
            mqtt_client.on_connect = on_mqtt_connect
    if not hasattr(mqtt_client, "on_disconnect") or mqtt_client.on_disconnect is None:
        with contextlib.suppress(Exception):
            mqtt_client.on_disconnect = on_mqtt_disconnect

    is_connected = False
    if hasattr(mqtt_client, "is_connected"):
        try:
            is_connected = mqtt_client.is_connected() is True
        except Exception:
            is_connected = False

    if not is_connected:
        protocol = "mqtts" if tls_enabled else "mqtt"
        redacted_uri = f"{protocol}://{username}:***@{host}:{port}" if username else f"{protocol}://{host}:{port}"
        LOGGER.info("Connecting to %s", redacted_uri)

        if tls_enabled and hasattr(mqtt_client, "tls_set"):
            ca_certs = config.get("tls_ca_certs")
            certfile = config.get("tls_certfile")
            keyfile = config.get("tls_keyfile")
            insecure = bool(config.get("tls_insecure", False))
            mqtt_client.tls_set(ca_certs=ca_certs, certfile=certfile, keyfile=keyfile)
            if hasattr(mqtt_client, "tls_insecure_set"):
                mqtt_client.tls_insecure_set(insecure)

        status_topic = config.get("status_topic")
        if status_topic and hasattr(mqtt_client, "will_set"):
            mqtt_client.will_set(topic=status_topic, payload=b"offline", qos=qos, retain=retain)

        if hasattr(mqtt_client, "user_data_set"):
            with contextlib.suppress(Exception):
                mqtt_client.user_data_set({"config": config})

        if username is not None:
            mqtt_client.username_pw_set(username, password=password)
        mqtt_client.connect(host, port, 60)
        if hasattr(mqtt_client, "loop_start"):
            mqtt_client.loop_start()
        LOGGER.info("Connected to %s", redacted_uri)

        if status_topic:
            publish_status(mqtt_client=mqtt_client, config=config, status="online")

        # Publish HA discovery if configured
        publish_ha_discovery(mqtt_client=mqtt_client, config=config, topics=topics)

    data = json.dumps(payload).encode("utf-8")
    published_count = 0
    for topic in topics:
        LOGGER.info("Publishing msg: %s to topic: %s", data.decode("utf-8"), topic)
        msg_info = mqtt_client.publish(topic=topic, payload=data, qos=qos, retain=retain)
        if msg_info is not None:
            rc = getattr(msg_info, "rc", 0)
            if isinstance(rc, int) and rc != 0:
                LOGGER.error("Failed to publish to topic %s: return code %s", topic, rc)
                continue
            if hasattr(msg_info, "wait_for_publish"):
                try:
                    msg_info.wait_for_publish(timeout=publish_timeout)
                except Exception as exc:
                    LOGGER.error("Failed waiting for publish to topic %s: %s", topic, exc)
                    continue
            if hasattr(msg_info, "is_published"):
                try:
                    if msg_info.is_published() is False:
                        LOGGER.error("Publishing to topic %s timed out after %s seconds", topic, publish_timeout)
                        continue
                except Exception as exc:
                    LOGGER.error("Error checking is_published for topic %s: %s", topic, exc)
                    continue
        published_count += 1

        if per_metric_topics:
            for metric in ("temperature", "humidity", "pressure"):
                if metric in payload:
                    metric_topic = f"{topic.rstrip('/')}/{metric}"
                    metric_val = str(payload[metric]).encode("utf-8")
                    LOGGER.debug("Publishing per-metric %s: %s to %s", metric, metric_val, metric_topic)
                    with contextlib.suppress(Exception):
                        mqtt_client.publish(topic=metric_topic, payload=metric_val, qos=qos, retain=retain)

    if published_count == len(topics):
        LOGGER.info("messages published")
    else:
        LOGGER.error(
            "Failed to publish messages to all topics (succeeded %d of %d)",
            published_count,
            len(topics),
        )
        raise RuntimeError(f"Failed to publish to all topics ({published_count}/{len(topics)} succeeded)")


def show_on_display(
    sense: object,
    payload: dict,
    stop_event: threading.Event | None = None,
    display_pause: float = DEFAULT_DISPLAY_PAUSE,
    night_start: int = 19,
    night_end: int = 7,
    display: Display | None = None,
) -> None:
    """Scroll measurements on LED matrix if not in night mode."""
    if display is not None:
        display.show(payload=payload, stop_event=stop_event)
        return
    disp = SenseHatDisplay(
        sense=sense,
        display_pause=display_pause,
        night_start=night_start,
        night_end=night_end,
    )
    disp.show(payload=payload, stop_event=stop_event)


def send_sensor_data(
    config: dict[str, Any] | Config | Any,
    measurements: int | None = None,
    mqtt_client: MqttClient | None = None,
    sense: object | None = None,
    stop_event: threading.Event | None = None,
    display: Display | None = None,
) -> dict[str, object]:
    """Orchestrate sensor reading, payload building, MQTT publishing, and LED display."""
    if sense is None:
        sense = get_sense_hat()
    if mqtt_client is None:
        try:
            mqtt_client = MqttClient(CallbackAPIVersion.VERSION2)
        except (AttributeError, TypeError):
            mqtt_client = MqttClient()
    if display is None:
        display = get_display(config=config, sense=sense)

    if measurements is None:
        measurements = int(config.get("measurements", 3))

    temp_offset = float(config.get("temperature_offset", 0.0))
    compensate_cpu = bool(config.get("compensate_cpu_temp", False))
    cpu_factor = float(config.get("cpu_temp_factor", 5.466))
    sample_spacing = float(config.get("sample_spacing", 1.0))
    cpu_temp = get_cpu_temperature() if compensate_cpu else None

    include_imu = bool(config.get("include_imu", False))
    include_pressure_temp = bool(config.get("include_pressure_temp", False))

    readings = read_measurements(
        sense,
        measurements=measurements,
        temperature_offset=temp_offset,
        cpu_temp=cpu_temp,
        cpu_factor=cpu_factor,
        sample_spacing=sample_spacing,
        stop_event=stop_event,
        include_imu=include_imu,
        include_pressure_temp=include_pressure_temp,
    )
    payload = build_payload(readings)
    try:
        publish(config=config, payload=payload, mqtt_client=mqtt_client)
    finally:
        try:
            display.show(payload=payload, stop_event=stop_event)
        except Exception as exc:
            LOGGER.warning("Failed to update LED matrix display: %s", exc)
    return payload
