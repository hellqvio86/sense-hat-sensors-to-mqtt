from unittest.mock import MagicMock, patch

import pytest

from sensehatsensorstomqtt.sensor import publish


def test_resources_created_once_and_released_on_exit():
    fake_sense = MagicMock()
    fake_client = MagicMock()
    fake_client.is_connected.return_value = True

    cycles = 0

    import threading

    stop_event = threading.Event()

    def mock_send(*args, **kwargs):
        nonlocal cycles
        cycles += 1
        if cycles >= 3:
            stop_event.set()

    with (
        patch(
            "sensehatsensorstomqtt.main.args_handler",
            return_value={
                "host": "localhost",
                "topics": ["topic/1"],
                "debug": False,
                "log_file": None,
            },
        ),
        patch("sensehatsensorstomqtt.main.setup_logger"),
        patch("sensehatsensorstomqtt.main.get_sense_hat", return_value=fake_sense) as mock_get_sense,
        patch("paho.mqtt.client.Client", return_value=fake_client) as mock_client_cls,
        patch("sensehatsensorstomqtt.main.send_sensor_data", side_effect=mock_send),
        patch.object(stop_event, "wait", side_effect=lambda timeout=None: stop_event.is_set()),
    ):
        from sensehatsensorstomqtt.main import main

        main(stop_event=stop_event)

    # SenseHat and mqtt.Client should be created once across 3 cycles, not 3 times
    assert mock_get_sense.call_count == 1
    assert mock_client_cls.call_count == 1
    # Resources must be closed on exit
    assert fake_client.disconnect.call_count == 1
    assert fake_client.loop_stop.call_count == 1
    assert fake_sense.clear.call_count == 1


def test_resources_released_on_failure_path():
    fake_sense = MagicMock()
    fake_client = MagicMock()

    with (
        patch(
            "sensehatsensorstomqtt.main.args_handler",
            return_value={
                "host": "localhost",
                "topics": ["topic/1"],
                "debug": False,
                "log_file": None,
            },
        ),
        patch("sensehatsensorstomqtt.main.setup_logger"),
        patch("sensehatsensorstomqtt.main.get_sense_hat", return_value=fake_sense),
        patch("paho.mqtt.client.Client", return_value=fake_client),
        patch("sensehatsensorstomqtt.main.send_sensor_data", side_effect=SystemExit("fatal")),
        pytest.raises(SystemExit),
    ):
        from sensehatsensorstomqtt.main import main

        main()

    assert fake_client.disconnect.call_count == 1
    assert fake_client.loop_stop.call_count == 1
    assert fake_sense.clear.call_count == 1


def test_publish_reuses_connected_client():
    config = {
        "host": "localhost",
        "username": "user",
        "password": "pw",
        "port": 1883,
        "topics": ["topic/1"],
    }
    fake_client = MagicMock()
    fake_client.is_connected.return_value = True

    publish(config, {"test": 1}, fake_client)
    # connect should not be called because client is already connected
    assert not fake_client.connect.called
    assert fake_client.publish.called
