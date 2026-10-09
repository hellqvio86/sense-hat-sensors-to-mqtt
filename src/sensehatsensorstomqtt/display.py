"""
Display interface and Sense HAT LED matrix implementation.
"""

import logging
import threading
from abc import ABC, abstractmethod
from collections.abc import Callable
from random import randint
from time import sleep
from typing import Any

from .colors import get_color_for_temperature
from .consts import DEFAULT_DISPLAY_PAUSE
from .utils import is_night

LOGGER = logging.getLogger(__name__)


class Display(ABC):
    """Abstract interface for LED matrix display."""

    @abstractmethod
    def show(
        self,
        payload: dict[str, Any],
        stop_event: threading.Event | None = None,
    ) -> None:
        """Display payload metrics on the display."""

    @abstractmethod
    def clear(self) -> None:
        """Clear the display."""


class NullDisplay(Display):
    """No-op display implementation for headless or disabled display mode."""

    def show(
        self,
        payload: dict[str, Any],
        stop_event: threading.Event | None = None,
    ) -> None:
        pass

    def clear(self) -> None:
        pass


class SenseHatDisplay(Display):
    """Sense HAT 8x8 RGB LED matrix display implementation."""

    def __init__(
        self,
        sense: object,
        display_pause: float = DEFAULT_DISPLAY_PAUSE,
        night_start: int = 19,
        night_end: int = 7,
        color_provider: Callable[[], tuple[int, int, int]] | None = None,
    ) -> None:
        self.sense = sense
        self.display_pause = display_pause
        self.night_start = night_start
        self.night_end = night_end
        self.color_provider = color_provider

    def _get_color(self) -> tuple[int, int, int]:
        if self.color_provider is not None:
            return self.color_provider()
        return (randint(0, 255), randint(0, 255), randint(0, 255))  # noqa: S311

    def _pause(self, stop_event: threading.Event | None) -> bool:
        """Pause between scrolls. Return True if stopped."""
        if stop_event is not None:
            stop_event.wait(self.display_pause)
            return stop_event.is_set()
        if self.display_pause > 0:
            sleep(self.display_pause)
        return False

    def clear(self) -> None:
        """Clear the Sense HAT LED matrix."""
        try:
            if hasattr(self.sense, "clear"):
                self.sense.clear()
        except Exception as exc:
            LOGGER.warning("Failed to clear LED matrix display: %s", exc)

    def show(
        self,
        payload: dict[str, Any],
        stop_event: threading.Event | None = None,
    ) -> None:
        """Scroll measurements on LED matrix if not in night mode."""
        if stop_event is not None and stop_event.is_set():
            return

        night = is_night(night_start=self.night_start, night_end=self.night_end)
        LOGGER.debug("is_night: %s", night)

        if night:
            self.clear()
            LOGGER.info("Not running text on display, night mode!")
            return

        try:
            color_1 = self._get_color()
            color_2 = self._get_color()
            temp_color = get_color_for_temperature(float(payload["temperature"]))

            if hasattr(self.sense, "show_message"):
                self.sense.show_message(
                    f"{payload['pressure']:.2f} {payload['unit_of_pressure']}",
                    text_colour=color_1,
                )
            if self._pause(stop_event):
                self.clear()
                return

            if hasattr(self.sense, "show_message"):
                self.sense.show_message(
                    f"{payload['humidity']:.2f} {payload['unit_of_humidity']}",
                    text_colour=color_2,
                )
            if self._pause(stop_event):
                self.clear()
                return

            if hasattr(self.sense, "show_message"):
                self.sense.show_message(
                    f"{payload['temperature']:.2f} {payload['unit_of_temperature']}",
                    text_colour=temp_color,
                )
        except Exception as exc:
            LOGGER.warning("Failed to update LED matrix display: %s", exc)


def get_display(config: Any, sense: object | None = None) -> Display:
    """Factory function returning SenseHatDisplay or NullDisplay based on configuration."""
    if not hasattr(config, "get"):
        enabled = True
        display_pause = DEFAULT_DISPLAY_PAUSE
        night_start = 19
        night_end = 7
    else:
        enabled = bool(config.get("display", True))
        display_pause = float(config.get("display_pause", DEFAULT_DISPLAY_PAUSE))
        night_start = int(config.get("night_start", 19))
        night_end = int(config.get("night_end", 7))

    if not enabled or sense is None:
        return NullDisplay()

    return SenseHatDisplay(
        sense=sense,
        display_pause=display_pause,
        night_start=night_start,
        night_end=night_end,
    )
