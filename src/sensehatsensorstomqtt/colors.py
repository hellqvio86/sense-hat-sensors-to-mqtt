"""RGB colors for Sense HAT 8x8 LED matrix display."""

from random import randint

COLOR_RED = (255, 0, 0)
COLOR_YELLOW = (255, 255, 0)
COLOR_BLUE = (0, 0, 255)


def get_color_for_temperature(temperature: float) -> tuple[int, int, int]:
    """
    Function for getting color based on temperature
    """
    if temperature > 30:
        return COLOR_RED

    if temperature > 28:
        return COLOR_YELLOW

    if temperature < 18:
        return COLOR_BLUE
    else:
        return (randint(0, 255), randint(0, 255), randint(0, 255))  # noqa: S311
