from unittest.mock import MagicMock, mock_open, patch

from sensehatsensorstomqtt.sensor import (
    compensate_temperature,
    get_cpu_temperature,
    send_sensor_data,
)


def test_compensate_temperature_maths():
    # raw=28.0, cpu=50.0, factor=5.466, offset=0.0
    # diff = 50.0 - 28.0 = 22.0
    # heating = 22.0 / 5.466 = 4.02488...
    # expected = 28.0 - 4.02488 = 23.975... -> 23.98
    result = compensate_temperature(raw_temp=28.0, cpu_temp=50.0, factor=5.466, offset=0.0)
    assert result == 23.98

    # with offset=1.5
    result_with_offset = compensate_temperature(raw_temp=28.0, cpu_temp=50.0, factor=5.466, offset=1.5)
    assert result_with_offset == 22.48

    # offset only, cpu_temp=None
    result_offset_only = compensate_temperature(raw_temp=25.0, cpu_temp=None, offset=3.2)
    assert result_offset_only == 21.80


def test_get_cpu_temperature_success():
    m = mock_open(read_data="45123\n")
    with patch("builtins.open", m):
        temp = get_cpu_temperature()
        assert temp == 45.123


def test_get_cpu_temperature_failure():
    with patch("builtins.open", side_effect=OSError("Not found")):
        temp = get_cpu_temperature()
        assert temp is None


def test_temperature_offset_end_to_end():
    fake_sense = MagicMock()
    fake_sense.get_temperature.return_value = 25.0
    fake_sense.get_humidity.return_value = 50.0
    fake_sense.get_pressure.return_value = 1013.0

    fake_client = MagicMock()
    config = {
        "host": "localhost",
        "topics": ["sensor/topic"],
        "temperature_offset": 3.0,
    }

    with (
        patch("sensehatsensorstomqtt.sensor.publish"),
        patch("sensehatsensorstomqtt.sensor.show_on_display"),
    ):
        payload = send_sensor_data(config=config, measurements=1, mqtt_client=fake_client, sense=fake_sense)

    assert payload["temperature"] == 22.0


def test_cpu_temp_compensation_end_to_end():
    fake_sense = MagicMock()
    fake_sense.get_temperature.return_value = 28.0
    fake_sense.get_humidity.return_value = 50.0
    fake_sense.get_pressure.return_value = 1013.0

    fake_client = MagicMock()
    config = {
        "host": "localhost",
        "topics": ["sensor/topic"],
        "compensate_cpu_temp": True,
        "cpu_temp_factor": 5.466,
    }

    with (
        patch("sensehatsensorstomqtt.sensor.get_cpu_temperature", return_value=50.0),
        patch("sensehatsensorstomqtt.sensor.publish"),
        patch("sensehatsensorstomqtt.sensor.show_on_display"),
    ):
        payload = send_sensor_data(config=config, measurements=1, mqtt_client=fake_client, sense=fake_sense)

    assert payload["temperature"] == 23.98


def test_temperature_compensation_args():
    from sensehatsensorstomqtt.args import args_handler

    config = args_handler(
        [
            "--topics",
            "t1",
            "--temperature_offset",
            "2.5",
            "--compensate_cpu_temp",
            "--cpu_temp_factor",
            "4.0",
        ]
    )
    assert config["temperature_offset"] == 2.5
    assert config["compensate_cpu_temp"] is True
    assert config["cpu_temp_factor"] == 4.0

    config2 = args_handler(
        [
            "--topics",
            "t1",
            "--no-compensate_cpu_temp",
        ]
    )
    assert config2["compensate_cpu_temp"] is False


def test_temperature_compensation_config_validation():
    import pytest

    from sensehatsensorstomqtt.config import validate_config

    with pytest.raises(ValueError, match="temperature_offset"):
        validate_config({"host": "localhost", "topics": ["t1"], "temperature_offset": "invalid"})

    with pytest.raises(ValueError, match="compensate_cpu_temp"):
        validate_config({"host": "localhost", "topics": ["t1"], "compensate_cpu_temp": "invalid"})

    with pytest.raises(ValueError, match="cpu_temp_factor"):
        validate_config({"host": "localhost", "topics": ["t1"], "cpu_temp_factor": "invalid"})


def test_get_sense_hat_primes_sensors():
    from sensehatsensorstomqtt.hardware import get_sense_hat

    fake_sense_instance = MagicMock()
    with patch("sense_hat.SenseHat", return_value=fake_sense_instance):
        sense = get_sense_hat()
        assert sense is fake_sense_instance
        assert fake_sense_instance.get_temperature.called
        assert fake_sense_instance.get_humidity.called
        assert fake_sense_instance.get_pressure.called
