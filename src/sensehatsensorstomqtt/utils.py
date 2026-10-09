"""Utility functions for time and night-window calculations."""

import datetime
import logging

LOGGER = logging.getLogger(__name__)


def is_night(
    *,
    current_time: datetime.datetime | None = None,
    night_start: int = 19,
    night_end: int = 7,
) -> bool:
    """
    Check if the current (or specified) time falls within the night window.

    By default, night starts at 19:00 (inclusive) and ends at 07:00 (exclusive).
    """
    real_current_time = current_time if current_time is not None else datetime.datetime.now().astimezone()

    LOGGER.debug(
        "Checking is_night: current_time=%s, night_start=%d, night_end=%d",
        real_current_time,
        night_start,
        night_end,
    )

    hour = real_current_time.hour
    if night_start > night_end:
        # Window spans across midnight, e.g. 19:00 to 07:00
        return hour >= night_start or hour < night_end
    elif night_start < night_end:
        # Window within same calendar day, e.g. 01:00 to 05:00
        return night_start <= hour < night_end
    return False
