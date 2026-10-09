import signal
import threading
from unittest.mock import MagicMock, patch

import pytest

from sensehatsensorstomqtt.config import validate_config
from sensehatsensorstomqtt.main import main
from sensehatsensorstomqtt.sensor import (
    publish,
    publish_status,
    read_measurements,
    show_on_display,
)


def test_config_cadence_and_status_defaults():
    cfg = validate_config({"host": "localhost", "topics": ["sensors/test"]})
    assert cfg.interval == 60.0
    assert cfg.measurements == 3
    assert cfg.sample_spacing == 1.0
    assert cfg.status_topic is None


def test_config_cadence_and_status_custom():
    cfg = validate_config(
        {
            "host": "localhost",
            "topics": ["sensors/test"],
            "interval": "30.5",
            "measurements": "5",
            "sample_spacing": "0.5",
            "status_topic": "sensors/test/status",
        }
    )
    assert cfg.interval == 30.5
    assert cfg.measurements == 5
    assert cfg.sample_spacing == 0.5
    assert cfg.status_topic == "sensors/test/status"


@pytest.mark.parametrize(
    "invalid_cfg, match",
    [
        ({"host": "h", "topics": ["t"], "interval": 0}, "Interval must be greater than 0"),
        ({"host": "h", "topics": ["t"], "interval": -5}, "Interval must be greater than 0"),
        ({"host": "h", "topics": ["t"], "interval": "abc"}, "Invalid interval"),
        ({"host": "h", "topics": ["t"], "measurements": 0}, "Measurements must be at least 1"),
        ({"host": "h", "topics": ["t"], "measurements": -1}, "Measurements must be at least 1"),
        ({"host": "h", "topics": ["t"], "measurements": "xyz"}, "Invalid measurements"),
        ({"host": "h", "topics": ["t"], "sample_spacing": -0.1}, "sample_spacing must be non-negative"),
        ({"host": "h", "topics": ["t"], "sample_spacing": "bad"}, "Invalid sample_spacing"),
    ],
)
def test_config_cadence_validation_errors(invalid_cfg, match):
    with pytest.raises(ValueError, match=match):
        validate_config(invalid_cfg)


def test_publish_sets_lwt_and_online_status():
    fake_client = MagicMock()
    fake_client.is_connected.return_value = False
    config = {
        "host": "mqtt.local",
        "port": 1883,
        "topics": ["sensors/data"],
        "status_topic": "sensors/availability",
        "qos": 1,
        "retain": True,
    }
    payload = {"temperature": 21.0}

    publish(config=config, payload=payload, mqtt_client=fake_client)

    # LWT must be set before connecting
    fake_client.will_set.assert_called_once_with(
        topic="sensors/availability",
        payload=b"offline",
        qos=1,
        retain=True,
    )
    fake_client.connect.assert_called_once_with("mqtt.local", 1883, 60)

    # Online status must be published after connection
    calls = fake_client.publish.call_args_list
    assert any(c.kwargs.get("topic") == "sensors/availability" and c.kwargs.get("payload") == b"online" for c in calls)


def test_publish_without_status_topic_skips_lwt():
    fake_client = MagicMock()
    fake_client.is_connected.return_value = False
    config = {
        "host": "mqtt.local",
        "port": 1883,
        "topics": ["sensors/data"],
        "status_topic": None,
    }
    publish(config=config, payload={"val": 1}, mqtt_client=fake_client)

    fake_client.will_set.assert_not_called()
    for c in fake_client.publish.call_args_list:
        assert c.kwargs.get("topic") != "sensors/availability"


def test_publish_status_helper():
    fake_client = MagicMock()
    config = {"status_topic": "status/sensor", "qos": 2, "retain": True}

    publish_status(fake_client, config, status="online")
    fake_client.publish.assert_called_with(topic="status/sensor", payload=b"online", qos=2, retain=True)

    publish_status(fake_client, config, status="offline", wait=True)
    fake_client.publish.assert_called_with(topic="status/sensor", payload=b"offline", qos=2, retain=True)


def test_publish_status_safe_on_errors():
    fake_client = MagicMock()
    fake_client.publish.side_effect = RuntimeError("publish failed")
    # Must not raise
    publish_status(fake_client, {"status_topic": "topic"}, status="offline", wait=True)
    publish_status(fake_client, None, status="online")
    publish_status(fake_client, {}, status="online")


def test_main_publishes_offline_on_shutdown():
    fake_sense = MagicMock()
    fake_client = MagicMock()
    fake_client.is_connected.return_value = True

    stop_event = threading.Event()

    def mock_send(*args, **kwargs):
        stop_event.set()

    with (
        patch(
            "sensehatsensorstomqtt.main.args_handler",
            return_value={
                "host": "localhost",
                "topics": ["topic/1"],
                "status_topic": "topic/status",
                "qos": 1,
                "retain": True,
            },
        ),
        patch("sensehatsensorstomqtt.main.setup_logger"),
        patch("sensehatsensorstomqtt.main.get_sense_hat", return_value=fake_sense),
        patch("paho.mqtt.client.Client", return_value=fake_client),
        patch("sensehatsensorstomqtt.main.send_sensor_data", side_effect=mock_send),
    ):
        main(stop_event=stop_event)

    # offline status must be published during shutdown cleanup
    fake_client.publish.assert_called_with(
        topic="topic/status",
        payload=b"offline",
        qos=1,
        retain=True,
    )
    assert fake_client.disconnect.called
    assert fake_sense.clear.called


def test_main_signal_handler_sets_stop_event():
    handlers = {}

    def mock_signal(sig, handler):
        handlers[sig] = handler

    stop_event = threading.Event()

    def mock_send(*args, **kwargs):
        # Call the registered SIGTERM handler during the loop
        assert not stop_event.is_set()
        handlers[signal.SIGTERM](signal.SIGTERM, None)
        assert stop_event.is_set()

    with (
        patch("signal.signal", side_effect=mock_signal),
        patch("sensehatsensorstomqtt.main.args_handler", return_value={"host": "h", "topics": ["t"]}),
        patch("sensehatsensorstomqtt.main.setup_logger"),
        patch("sensehatsensorstomqtt.main.get_sense_hat"),
        patch("paho.mqtt.client.Client"),
        patch("sensehatsensorstomqtt.main.send_sensor_data", side_effect=mock_send),
    ):
        main(stop_event=stop_event)

    # Verify SIGTERM and SIGINT were registered
    assert signal.SIGTERM in handlers
    assert signal.SIGINT in handlers

    # A second invocation when stop_event is already set calls sys.exit(1)
    with pytest.raises(SystemExit) as exc_info:
        handlers[signal.SIGTERM](signal.SIGTERM, None)
    assert exc_info.value.code == 1


def test_main_enforces_minimum_pause_on_overrun():
    fake_sense = MagicMock()
    fake_client = MagicMock()
    stop_event = threading.Event()
    wait_calls = []

    # Simulate elapsed work of 70s on an interval of 60s (overrun by 10s)
    mock_monotonic = [0.0, 70.0, 71.0, 72.0]

    def mock_send(*args, **kwargs):
        pass

    def mock_wait(timeout=None):
        wait_calls.append(timeout)
        stop_event.set()
        return True

    with (
        patch(
            "sensehatsensorstomqtt.main.args_handler",
            return_value={
                "host": "localhost",
                "topics": ["t"],
                "interval": 60.0,
            },
        ),
        patch("sensehatsensorstomqtt.main.setup_logger"),
        patch("sensehatsensorstomqtt.main.get_sense_hat", return_value=fake_sense),
        patch("paho.mqtt.client.Client", return_value=fake_client),
        patch("sensehatsensorstomqtt.main.send_sensor_data", side_effect=mock_send),
        patch("time.monotonic", side_effect=mock_monotonic),
        patch.object(stop_event, "wait", side_effect=mock_wait),
    ):
        main(stop_event=stop_event)

    # Minimum pause of 1.0 second must be enforced
    assert wait_calls == [1.0]


def test_read_measurements_respects_stop_event():
    fake_sense = MagicMock()
    fake_sense.get_temperature.return_value = 20.0
    fake_sense.get_humidity.return_value = 40.0
    fake_sense.get_pressure.return_value = 1000.0

    stop_event = threading.Event()
    stop_event.set()

    # When stop_event is already set, it should not hang and return immediately
    readings = read_measurements(
        sense=fake_sense,
        measurements=5,
        sample_spacing=10.0,
        stop_event=stop_event,
    )
    assert "temperature" in readings
    assert "humidity" in readings
    assert "pressure" in readings


def test_show_on_display_respects_stop_event():
    fake_sense = MagicMock()
    stop_event = threading.Event()
    stop_event.set()

    payload = {
        "temperature": 20.0,
        "humidity": 40.0,
        "pressure": 1000.0,
        "unit_of_temperature": "C",
        "unit_of_humidity": "%",
        "unit_of_pressure": "hPa",
    }
    show_on_display(sense=fake_sense, payload=payload, stop_event=stop_event)
    # When stop_event is already set, show_message should not be called
    fake_sense.show_message.assert_not_called()
