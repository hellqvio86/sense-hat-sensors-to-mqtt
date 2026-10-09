from unittest.mock import MagicMock, patch

from sensehatsensorstomqtt.sensor import send_sensor_data


def test_display_failure_does_not_prevent_publishing(monkeypatch):
    config = {
        "host": "localhost",
        "username": "user",
        "password": "pw",
        "port": 1883,
        "topics": ["sensor/topic"],
    }
    fake_client = MagicMock()

    # Make show_message raise an exception
    with patch("sensehatsensorstomqtt.display.is_night", return_value=False):
        mock_sense = MagicMock()
        mock_sense.get_temperature.return_value = 21.5
        mock_sense.get_humidity.return_value = 45.0
        mock_sense.get_pressure.return_value = 1012.0
        mock_sense.show_message.side_effect = RuntimeError("LED matrix broken")

        # send_sensor_data must not raise despite display failure
        send_sensor_data(config=config, measurements=1, mqtt_client=fake_client, sense=mock_sense)

        # Publishing must still have occurred
        assert fake_client.publish.called


def test_main_survives_connect_failure(caplog):
    import threading

    cycle_calls = []
    stop_event = threading.Event()

    def mock_send(config, measurements=3, mqtt_client=None, **kwargs):
        cycle_calls.append(len(cycle_calls) + 1)
        if len(cycle_calls) == 1:
            raise ConnectionRefusedError("MQTT broker connection refused")
        if len(cycle_calls) >= 2:
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
        patch("sensehatsensorstomqtt.main.send_sensor_data", side_effect=mock_send),
        patch.object(stop_event, "wait", side_effect=lambda timeout=None: stop_event.is_set()),
    ):
        from sensehatsensorstomqtt.main import main

        main(stop_event=stop_event)

    assert len(cycle_calls) == 2
