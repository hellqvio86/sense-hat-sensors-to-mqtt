import json
from unittest.mock import MagicMock, patch

import pytest

from sensehatsensorstomqtt.sensor import (
    build_payload,
    publish,
    read_measurements,
    send_sensor_data,
    show_on_display,
)


@pytest.fixture
def fake_sense():
    sense = MagicMock()
    sense.get_temperature.side_effect = [20.0, 22.0, 24.0]
    sense.get_humidity.side_effect = [50.0, 52.0, 54.0]
    sense.get_pressure.side_effect = [1010.0, 1012.0, 1014.0]
    return sense


def test_read_measurements(fake_sense):
    measurements = read_measurements(fake_sense, measurements=3)
    assert measurements["temperature"] == 22.0
    assert measurements["humidity"] == 52.0
    assert measurements["pressure"] == 1012.0


def test_build_payload():
    import datetime

    measurements = {
        "temperature": 21.56789,
        "humidity": 45.12345,
        "pressure": 1013.2678,
    }
    payload = build_payload(measurements)

    # Check keys
    expected_keys = {
        "temperature",
        "humidity",
        "pressure",
        "unit_of_temperature",
        "unit_of_humidity",
        "unit_of_pressure",
        "time_utc",
    }
    assert set(payload.keys()) == expected_keys

    # Check types and rounding
    assert payload["temperature"] == 21.57
    assert isinstance(payload["temperature"], float)
    assert payload["humidity"] == 45.12
    assert isinstance(payload["humidity"], float)
    assert payload["pressure"] == 1013.3
    assert isinstance(payload["pressure"], float)

    # Check units
    assert payload["unit_of_temperature"] == "C"
    assert payload["unit_of_humidity"] == "%"
    assert payload["unit_of_pressure"] == "mbar"

    # Check ISO-8601 offset-aware UTC timestamp
    time_str = str(payload["time_utc"])
    assert "T" in time_str
    assert "+" in time_str or time_str.endswith("Z")
    parsed_dt = datetime.datetime.fromisoformat(time_str)
    assert parsed_dt.tzinfo is not None
    assert parsed_dt.utcoffset() == datetime.timedelta(0)
    # Check no microseconds in timespec="seconds"
    assert parsed_dt.microsecond == 0


def test_publish():
    config = {
        "host": "broker.local",
        "username": "user",
        "password": "pass",
        "port": 1883,
        "topics": ["topic/1", "topic/2"],
    }
    payload = {"temperature": 20.0, "time_utc": "2026-01-01T12:00:00.000"}
    mock_client = MagicMock()

    publish(config, payload, mock_client)

    mock_client.username_pw_set.assert_called_once_with("user", password="pass")
    mock_client.connect.assert_called_once_with("broker.local", 1883, 60)
    assert mock_client.publish.call_count == 2

    # Check payload sent
    encoded_payload = json.dumps(payload).encode("utf-8")
    for call in mock_client.publish.call_args_list:
        assert call.kwargs["payload"] == encoded_payload
        assert call.kwargs["retain"] is True


def test_show_on_display_day(fake_sense):
    payload = {
        "temperature": 22.0,
        "humidity": 50.0,
        "pressure": 1012.0,
        "unit_of_temperature": "C",
        "unit_of_humidity": "%",
        "unit_of_pressure": "mbar",
    }
    with patch("sensehatsensorstomqtt.display.is_night", return_value=False):
        show_on_display(fake_sense, payload)

    assert fake_sense.show_message.call_count == 3
    assert not fake_sense.clear.called


def test_show_on_display_night(fake_sense):
    payload = {
        "temperature": 22.0,
        "humidity": 50.0,
        "pressure": 1012.0,
        "unit_of_temperature": "C",
        "unit_of_humidity": "%",
        "unit_of_pressure": "mbar",
    }
    with patch("sensehatsensorstomqtt.display.is_night", return_value=True):
        show_on_display(fake_sense, payload)

    assert not fake_sense.show_message.called
    assert fake_sense.clear.called


def test_send_sensor_data_integration(fake_sense):
    config = {
        "host": "broker.local",
        "username": "user",
        "password": "pass",
        "port": 1883,
        "topics": ["topic/1"],
    }
    mock_client = MagicMock()

    with patch("sensehatsensorstomqtt.display.is_night", return_value=True):
        payload = send_sensor_data(
            config=config,
            measurements=3,
            mqtt_client=mock_client,
            sense=fake_sense,
        )

    assert payload["temperature"] == 22.0
    assert mock_client.publish.called


def test_failing_sensor_read_raises():
    broken_sense = MagicMock()
    broken_sense.get_temperature.side_effect = RuntimeError("I2C read failed")
    with pytest.raises(RuntimeError):
        read_measurements(broken_sense, measurements=1)


def test_failing_publish_raises():
    config = {
        "host": "broker.local",
        "username": "user",
        "password": "pass",
        "port": 1883,
        "topics": ["topic/1"],
    }
    mock_client = MagicMock()
    mock_client.connect.side_effect = ConnectionError("Connection failed")
    with pytest.raises(ConnectionError):
        publish(config, {"test": 1}, mock_client)


def test_hardware_get_sense_hat():
    from sensehatsensorstomqtt.hardware import get_sense_hat

    sense = get_sense_hat()
    assert sense is not None
