from sensehatsensorstomqtt.colors import (
    COLOR_BLUE,
    COLOR_RED,
    COLOR_YELLOW,
    get_color_for_temperature,
)


def test_get_color_for_temperature_hot():
    assert get_color_for_temperature(35.0) == COLOR_RED
    assert get_color_for_temperature(30.1) == COLOR_RED


def test_get_color_for_temperature_warm():
    assert get_color_for_temperature(29.0) == COLOR_YELLOW
    assert get_color_for_temperature(28.1) == COLOR_YELLOW


def test_get_color_for_temperature_cold():
    assert get_color_for_temperature(17.9) == COLOR_BLUE
    assert get_color_for_temperature(10.0) == COLOR_BLUE


def test_get_color_for_temperature_moderate():
    color = get_color_for_temperature(22.0)
    assert isinstance(color, tuple)
    assert len(color) == 3
    for channel in color:
        assert 0 <= channel <= 255
