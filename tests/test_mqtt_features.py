"""Tests for MQTT features: TLS, client_id, per-metric topics, and Home Assistant discovery."""

import json
from unittest.mock import MagicMock

from sensehatsensorstomqtt.config import Config
from sensehatsensorstomqtt.sensor import publish, publish_ha_discovery


def test_publish_tls_configuration():
    config = Config(
        host="tls.broker.local",
        topics=["sensors/sensehat"],
        port=8883,
        tls=True,
        tls_ca_certs="/etc/ssl/certs/ca.pem",
        tls_certfile="/etc/ssl/certs/client.crt",
        tls_keyfile="/etc/ssl/certs/client.key",
        tls_insecure=True,
    )
    payload = {"temperature": 21.0}
    mock_client = MagicMock()
    mock_client.is_connected.return_value = False

    publish(config, payload, mock_client)

    mock_client.tls_set.assert_called_once_with(
        ca_certs="/etc/ssl/certs/ca.pem",
        certfile="/etc/ssl/certs/client.crt",
        keyfile="/etc/ssl/certs/client.key",
    )
    mock_client.tls_insecure_set.assert_called_once_with(True)
    mock_client.connect.assert_called_once_with("tls.broker.local", 8883, 60)


def test_publish_per_metric_topics():
    config = Config(
        host="broker.local",
        topics=["sensors/sensehat"],
        per_metric_topics=True,
    )
    payload = {
        "temperature": 21.5,
        "humidity": 45.2,
        "pressure": 1013.2,
    }
    mock_client = MagicMock()
    mock_client.is_connected.return_value = False

    publish(config, payload, mock_client)

    # 1 base topic + 3 per-metric topics
    published_topics = [call.kwargs["topic"] for call in mock_client.publish.call_args_list]
    assert "sensors/sensehat" in published_topics
    assert "sensors/sensehat/temperature" in published_topics
    assert "sensors/sensehat/humidity" in published_topics
    assert "sensors/sensehat/pressure" in published_topics

    temp_call = next(
        c for c in mock_client.publish.call_args_list if c.kwargs["topic"] == "sensors/sensehat/temperature"
    )
    assert temp_call.kwargs["payload"] == b"21.5"


def test_publish_ha_discovery():
    config = Config(
        host="broker.local",
        topics=["home/sensehat/state"],
        ha_discovery=True,
        ha_discovery_prefix="homeassistant",
        device_id="living_room_sensehat",
        status_topic="home/sensehat/status",
    )
    mock_client = MagicMock()

    publish_ha_discovery(mqtt_client=mock_client, config=config, topics=config.topics)

    assert mock_client.publish.call_count == 3
    discovery_topics = [call.kwargs["topic"] for call in mock_client.publish.call_args_list]
    assert "homeassistant/sensor/living_room_sensehat/temperature/config" in discovery_topics
    assert "homeassistant/sensor/living_room_sensehat/humidity/config" in discovery_topics
    assert "homeassistant/sensor/living_room_sensehat/pressure/config" in discovery_topics

    temp_call = next(c for c in mock_client.publish.call_args_list if "temperature" in c.kwargs["topic"])
    temp_payload = json.loads(temp_call.kwargs["payload"].decode("utf-8"))
    assert temp_payload["name"] == "living_room_sensehat Temperature"
    assert temp_payload["unique_id"] == "living_room_sensehat_temperature"
    assert temp_payload["state_topic"] == "home/sensehat/state"
    assert temp_payload["device_class"] == "temperature"
    assert temp_payload["unit_of_measurement"] == "°C"
    assert temp_payload["availability_topic"] == "home/sensehat/status"
    assert temp_payload["device"]["identifiers"] == ["living_room_sensehat"]
    assert temp_call.kwargs["retain"] is True


def test_publish_ha_discovery_disabled():
    config = Config(
        host="broker.local",
        topics=["home/sensehat/state"],
        ha_discovery=False,
    )
    mock_client = MagicMock()
    publish_ha_discovery(mqtt_client=mock_client, config=config, topics=config.topics)
    assert mock_client.publish.call_count == 0
