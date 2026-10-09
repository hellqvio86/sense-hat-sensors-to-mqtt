import warnings
from unittest.mock import MagicMock, patch

import pytest


def test_main_no_deprecation_warning_on_client_creation():
    with (
        warnings.catch_warnings(),
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
        patch("sensehatsensorstomqtt.main.get_sense_hat"),
        patch("sensehatsensorstomqtt.main.send_sensor_data", side_effect=SystemExit(0)),
    ):
        warnings.simplefilter("error", DeprecationWarning)
        from sensehatsensorstomqtt.main import main

        with pytest.raises(SystemExit):
            main()


def test_sensor_data_default_client_no_deprecation_warning():
    fake_sense = MagicMock()
    with (
        warnings.catch_warnings(),
        patch("sensehatsensorstomqtt.sensor.publish"),
        patch("sensehatsensorstomqtt.sensor.show_on_display"),
    ):
        warnings.simplefilter("error", DeprecationWarning)
        from sensehatsensorstomqtt.sensor import send_sensor_data

        config = {
            "host": "localhost",
            "username": "user",
            "password": "pw",
            "port": 1883,
            "topics": ["topic/1"],
        }
        send_sensor_data(config=config, measurements=1, sense=fake_sense)
