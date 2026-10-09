"""
Hardware adapter for Sense HAT.
"""

import contextlib


def get_sense_hat():
    """Lazily import, instantiate, and prime SenseHat."""
    from sense_hat import SenseHat

    sense = SenseHat()
    with contextlib.suppress(Exception):
        sense.get_temperature()
        sense.get_humidity()
        sense.get_pressure()
    return sense
