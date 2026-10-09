import datetime
import threading
from unittest.mock import MagicMock, patch

import pytest

from sensehatsensorstomqtt.config import validate_config
from sensehatsensorstomqtt.display import (
    NullDisplay,
    SenseHatDisplay,
    get_display,
)
from sensehatsensorstomqtt.sensor import send_sensor_data, show_on_display
from sensehatsensorstomqtt.utils import is_night


def test_null_display():
    disp = NullDisplay()
    # Must not raise or do anything
    disp.show({"temperature": 20.0})
    disp.clear()


def test_get_display_disabled():
    fake_sense = MagicMock()
    disp = get_display({"display": False}, sense=fake_sense)
    assert isinstance(disp, NullDisplay)

    disp_no_sense = get_display({"display": True}, sense=None)
    assert isinstance(disp_no_sense, NullDisplay)


def test_get_display_enabled():
    fake_sense = MagicMock()
    disp = get_display(
        {
            "display": True,
            "display_pause": 2.5,
            "night_start": 21,
            "night_end": 8,
        },
        sense=fake_sense,
    )
    assert isinstance(disp, SenseHatDisplay)
    assert disp.display_pause == 2.5
    assert disp.night_start == 21
    assert disp.night_end == 8


def test_sense_hat_display_day_mode():
    fake_sense = MagicMock()
    # Constant color provider for deterministic output
    fixed_color = (10, 20, 30)
    disp = SenseHatDisplay(
        sense=fake_sense,
        display_pause=0.0,
        night_start=22,
        night_end=6,
        color_provider=lambda: fixed_color,
    )

    payload = {
        "temperature": 25.0,
        "humidity": 50.0,
        "pressure": 1013.2,
        "unit_of_temperature": "C",
        "unit_of_humidity": "%",
        "unit_of_pressure": "mbar",
    }

    with patch("sensehatsensorstomqtt.display.is_night", return_value=False):
        disp.show(payload)

    # Must scroll pressure, humidity, and temperature
    assert fake_sense.show_message.call_count == 3
    calls = fake_sense.show_message.call_args_list
    assert "1013.20 mbar" in calls[0][0][0]
    assert calls[0][1]["text_colour"] == fixed_color
    assert "50.00 %" in calls[1][0][0]
    assert calls[1][1]["text_colour"] == fixed_color
    assert "25.00 C" in calls[2][0][0]


def test_sense_hat_display_night_mode():
    fake_sense = MagicMock()
    disp = SenseHatDisplay(sense=fake_sense, display_pause=0.0)

    payload = {
        "temperature": 20.0,
        "humidity": 50.0,
        "pressure": 1013.2,
        "unit_of_temperature": "C",
        "unit_of_humidity": "%",
        "unit_of_pressure": "mbar",
    }

    with patch("sensehatsensorstomqtt.display.is_night", return_value=True):
        disp.show(payload)

    # At night, messages must not be scrolled, and matrix must be cleared
    fake_sense.show_message.assert_not_called()
    fake_sense.clear.assert_called_once()


def test_sense_hat_display_respects_stop_event():
    fake_sense = MagicMock()
    disp = SenseHatDisplay(sense=fake_sense, display_pause=10.0)

    stop_event = threading.Event()
    stop_event.set()

    payload = {
        "temperature": 20.0,
        "humidity": 50.0,
        "pressure": 1000.0,
        "unit_of_pressure": "mbar",
        "unit_of_humidity": "%",
        "unit_of_temperature": "C",
    }
    with patch("sensehatsensorstomqtt.display.is_night", return_value=False):
        disp.show(payload, stop_event=stop_event)

    fake_sense.show_message.assert_not_called()


def test_sense_hat_display_resilient_to_exceptions(caplog):
    fake_sense = MagicMock()
    fake_sense.show_message.side_effect = RuntimeError("I2C error")
    disp = SenseHatDisplay(sense=fake_sense, display_pause=0.0)

    payload = {
        "temperature": 20.0,
        "humidity": 50.0,
        "pressure": 1000.0,
        "unit_of_pressure": "mbar",
        "unit_of_humidity": "%",
        "unit_of_temperature": "C",
    }
    with patch("sensehatsensorstomqtt.display.is_night", return_value=False):
        # Must not raise
        disp.show(payload)

    assert "Failed to update LED matrix display" in caplog.text


def test_send_sensor_data_with_display_disabled():
    fake_sense = MagicMock()
    fake_client = MagicMock()
    config = {
        "host": "localhost",
        "topics": ["sensors/test"],
        "display": False,
    }

    payload = send_sensor_data(
        config=config,
        measurements=1,
        mqtt_client=fake_client,
        sense=fake_sense,
    )
    assert "temperature" in payload
    # When display is False, show_message is never invoked
    fake_sense.show_message.assert_not_called()


def test_send_sensor_data_survives_display_crash():
    fake_sense = MagicMock()
    fake_client = MagicMock()
    failing_display = MagicMock()
    failing_display.show.side_effect = OSError("Hardware display crash")

    config = {
        "host": "localhost",
        "topics": ["sensors/test"],
    }

    # Even if display crashes, send_sensor_data must succeed and publish
    payload = send_sensor_data(
        config=config,
        measurements=1,
        mqtt_client=fake_client,
        sense=fake_sense,
        display=failing_display,
    )
    assert "temperature" in payload
    assert fake_client.publish.called


def test_show_on_display_backward_compatible():
    fake_sense = MagicMock()
    payload = {
        "temperature": 20.0,
        "humidity": 50.0,
        "pressure": 1000.0,
        "unit_of_pressure": "mbar",
        "unit_of_humidity": "%",
        "unit_of_temperature": "C",
    }
    with patch("sensehatsensorstomqtt.display.is_night", return_value=False):
        show_on_display(sense=fake_sense, payload=payload, display_pause=0.0)
    assert fake_sense.show_message.call_count == 3


def test_is_night_custom_hours():
    # Window spans midnight: 22:00 to 06:00
    assert is_night(current_time=datetime.datetime(2026, 1, 1, 21, 59), night_start=22, night_end=6) is False
    assert is_night(current_time=datetime.datetime(2026, 1, 1, 22, 0), night_start=22, night_end=6) is True
    assert is_night(current_time=datetime.datetime(2026, 1, 1, 3, 0), night_start=22, night_end=6) is True
    assert is_night(current_time=datetime.datetime(2026, 1, 1, 5, 59), night_start=22, night_end=6) is True
    assert is_night(current_time=datetime.datetime(2026, 1, 1, 6, 0), night_start=22, night_end=6) is False

    # Window within same day: 13:00 to 15:00
    assert is_night(current_time=datetime.datetime(2026, 1, 1, 12, 59), night_start=13, night_end=15) is False
    assert is_night(current_time=datetime.datetime(2026, 1, 1, 13, 0), night_start=13, night_end=15) is True
    assert is_night(current_time=datetime.datetime(2026, 1, 1, 14, 59), night_start=13, night_end=15) is True
    assert is_night(current_time=datetime.datetime(2026, 1, 1, 15, 0), night_start=13, night_end=15) is False


def test_config_validation_display_fields():
    cfg = validate_config(
        {
            "host": "localhost",
            "topics": ["t1"],
            "display": "false",
            "display_pause": "2.5",
            "night_start": "20",
            "night_end": "8",
        }
    )
    assert cfg.display is False
    assert cfg.display_pause == 2.5
    assert cfg.night_start == 20
    assert cfg.night_end == 8


@pytest.mark.parametrize(
    "bad_cfg, match",
    [
        ({"host": "h", "topics": ["t"], "display": "maybe"}, "Invalid display value"),
        ({"host": "h", "topics": ["t"], "display_pause": -1}, "display_pause must be non-negative"),
        ({"host": "h", "topics": ["t"], "night_start": 24}, "night_start must be between 0 and 23"),
        ({"host": "h", "topics": ["t"], "night_start": -1}, "night_start must be between 0 and 23"),
        ({"host": "h", "topics": ["t"], "night_end": 25}, "night_end must be between 0 and 23"),
        ({"host": "h", "topics": ["t"], "night_end": -1}, "night_end must be between 0 and 23"),
    ],
)
def test_config_display_validation_errors(bad_cfg, match):
    with pytest.raises(ValueError, match=match):
        validate_config(bad_cfg)
