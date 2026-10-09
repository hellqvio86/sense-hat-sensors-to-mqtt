from unittest.mock import MagicMock

import pytest

from sensehatsensorstomqtt.sensor import publish


def test_publish_failure_rc_logs_error_and_does_not_log_success(caplog):
    config = {
        "host": "localhost",
        "username": "user",
        "password": "pw",
        "port": 1883,
        "topics": ["topic/1"],
        "qos": 1,
        "retain": True,
    }
    fake_client = MagicMock()
    fake_client.is_connected.return_value = True

    fake_msg_info = MagicMock()
    fake_msg_info.rc = 4  # MQTT_ERR_NO_CONN
    fake_client.publish.return_value = fake_msg_info

    with caplog.at_level("DEBUG"), pytest.raises(RuntimeError):
        publish(config, {"temp": 20.0}, fake_client)

    assert "messages published" not in caplog.text
    assert any(record.levelname == "ERROR" and "Failed to publish" in record.message for record in caplog.records)


def test_publish_timeout_logs_error_and_does_not_log_success(caplog):
    config = {
        "host": "localhost",
        "username": "user",
        "password": "pw",
        "port": 1883,
        "topics": ["topic/1"],
        "qos": 1,
        "retain": True,
    }
    fake_client = MagicMock()
    fake_client.is_connected.return_value = True

    fake_msg_info = MagicMock()
    fake_msg_info.rc = 0
    fake_msg_info.is_published.return_value = False
    fake_client.publish.return_value = fake_msg_info

    with caplog.at_level("DEBUG"), pytest.raises(RuntimeError):
        publish(config, {"temp": 20.0}, fake_client)

    assert "messages published" not in caplog.text
    assert any(record.levelname == "ERROR" and "timed out" in record.message for record in caplog.records)


def test_publish_configurable_qos_and_retain():
    config = {
        "host": "localhost",
        "username": "user",
        "password": "pw",
        "port": 1883,
        "topics": ["topic/1"],
        "qos": 2,
        "retain": False,
    }
    fake_client = MagicMock()
    fake_client.is_connected.return_value = True

    fake_msg_info = MagicMock()
    fake_msg_info.rc = 0
    fake_msg_info.is_published.return_value = True
    fake_client.publish.return_value = fake_msg_info

    publish(config, {"temp": 20.0}, fake_client)

    fake_client.publish.assert_called_once_with(
        topic="topic/1",
        payload=b'{"temp": 20.0}',
        qos=2,
        retain=False,
    )


def test_publish_wait_exception_logs_error(caplog):
    config = {
        "host": "localhost",
        "username": "user",
        "password": "pw",
        "port": 1883,
        "topics": ["topic/1"],
    }
    fake_client = MagicMock()
    fake_client.is_connected.return_value = True

    fake_msg_info = MagicMock()
    fake_msg_info.rc = 0
    fake_msg_info.wait_for_publish.side_effect = RuntimeError("network drop")
    fake_client.publish.return_value = fake_msg_info

    with caplog.at_level("DEBUG"), pytest.raises(RuntimeError):
        publish(config, {"temp": 20.0}, fake_client)

    assert "messages published" not in caplog.text
    assert any(
        record.levelname == "ERROR" and "Failed waiting for publish" in record.message for record in caplog.records
    )


def test_mqtt_callbacks_log_appropriately(caplog):
    from sensehatsensorstomqtt.sensor import on_mqtt_connect, on_mqtt_disconnect

    fake_client = MagicMock()
    with caplog.at_level("DEBUG"):
        on_mqtt_connect(fake_client, None, {}, 0)
        assert "MQTT connection established" in caplog.text

    caplog.clear()
    with caplog.at_level("DEBUG"):
        on_mqtt_connect(fake_client, None, {}, 5)
        assert any(
            record.levelname == "ERROR" and "failed with return code 5" in record.message for record in caplog.records
        )

    caplog.clear()
    with caplog.at_level("DEBUG"):
        on_mqtt_disconnect(fake_client, None, 1)
        assert any(record.levelname == "WARNING" and "MQTT disconnected" in record.message for record in caplog.records)


def test_qos_and_retain_args():
    from sensehatsensorstomqtt.args import args_handler

    config = args_handler(["--qos", "2", "--no-retain", "--topics", "t1"])
    assert config["qos"] == 2
    assert config["retain"] is False

    config = args_handler(["--retain", "--topics", "t1"])
    assert config["retain"] is True


def test_invalid_qos_and_retain_config():
    from sensehatsensorstomqtt.config import apply_defaults

    with pytest.raises(ValueError, match="Invalid MQTT QoS"):
        apply_defaults({"qos": 5})

    with pytest.raises(ValueError, match="Invalid retain value"):
        apply_defaults({"retain": "invalid"})
