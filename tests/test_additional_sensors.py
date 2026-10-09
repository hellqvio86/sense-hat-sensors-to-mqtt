"""Tests for additional Sense HAT data (IMU and pressure sensor temperature)."""

from unittest.mock import MagicMock

from sensehatsensorstomqtt.sensor import build_payload, read_measurements


def test_read_measurements_imu_and_pressure_temp():
    fake_sense = MagicMock()
    fake_sense.get_temperature.side_effect = [20.0, 20.0, 20.0]
    fake_sense.get_humidity.side_effect = [50.0, 50.0, 50.0]
    fake_sense.get_pressure.side_effect = [1012.0, 1012.0, 1012.0]
    fake_sense.get_temperature_from_pressure.return_value = 21.4
    fake_sense.get_orientation.return_value = {"pitch": 1.234, "roll": 2.345, "yaw": 3.456}
    fake_sense.get_accelerometer_raw.return_value = {"x": 0.0123, "y": 0.0456, "z": 0.9876}
    fake_sense.get_gyroscope_raw.return_value = {"x": 0.0012, "y": 0.0023, "z": 0.0034}
    fake_sense.get_compass_raw.return_value = {"x": 10.123, "y": 20.234, "z": 30.345}

    readings = read_measurements(
        fake_sense,
        measurements=3,
        include_imu=True,
        include_pressure_temp=True,
    )

    assert readings["temperature"] == 20.0
    assert readings["pressure_temperature"] == 21.4
    assert readings["orientation"] == {"pitch": 1.23, "roll": 2.35, "yaw": 3.46}
    assert readings["accelerometer"] == {"x": 0.012, "y": 0.046, "z": 0.988}
    assert readings["gyroscope"] == {"x": 0.001, "y": 0.002, "z": 0.003}
    assert readings["compass"] == {"x": 10.123, "y": 20.234, "z": 30.345}

    payload = build_payload(readings)
    assert payload["pressure_temperature"] == 21.4
    assert payload["orientation"] == {"pitch": 1.23, "roll": 2.35, "yaw": 3.46}
    assert payload["accelerometer"] == {"x": 0.012, "y": 0.046, "z": 0.988}
    assert payload["gyroscope"] == {"x": 0.001, "y": 0.002, "z": 0.003}
    assert payload["compass"] == {"x": 10.123, "y": 20.234, "z": 30.345}


def test_read_measurements_imu_disabled_by_default():
    fake_sense = MagicMock()
    fake_sense.get_temperature.side_effect = [20.0]
    fake_sense.get_humidity.side_effect = [50.0]
    fake_sense.get_pressure.side_effect = [1012.0]

    readings = read_measurements(fake_sense, measurements=1)
    assert "orientation" not in readings
    assert "accelerometer" not in readings
    assert "gyroscope" not in readings
    assert "compass" not in readings
    assert "pressure_temperature" not in readings

    payload = build_payload(readings)
    assert "orientation" not in payload
    assert "pressure_temperature" not in payload


def test_read_measurements_imu_error_tolerance():
    fake_sense = MagicMock()
    fake_sense.get_temperature.side_effect = [20.0]
    fake_sense.get_humidity.side_effect = [50.0]
    fake_sense.get_pressure.side_effect = [1012.0]
    fake_sense.get_orientation.side_effect = OSError("IMU I2C communication error")
    fake_sense.get_temperature_from_pressure.side_effect = RuntimeError("Hardware fault")

    readings = read_measurements(
        fake_sense,
        measurements=1,
        include_imu=True,
        include_pressure_temp=True,
    )
    assert readings["temperature"] == 20.0
    assert "orientation" not in readings
    assert "pressure_temperature" not in readings
