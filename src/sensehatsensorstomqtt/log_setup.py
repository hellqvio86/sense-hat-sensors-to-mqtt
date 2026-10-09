"""Logging setup and handlers for Sense HAT to MQTT."""

import logging
import os
from logging.handlers import RotatingFileHandler


def setup_logger(
    *,
    debug: bool = False,
    log_file: str | None = None,
) -> logging.Logger:
    """
    Function for setting up logging
    """
    root = logging.getLogger()
    formatter = logging.Formatter(
        "%(asctime)s %(process)d %(processName)-10s %(name)-8s %(funcName)-8s %(levelname)-8s %(message)s"
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root.addHandler(console_handler)

    if log_file:
        try:
            log_dir = os.path.dirname(log_file)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)
            file_handler = RotatingFileHandler(log_file, "a", maxBytes=3 * 10**6, backupCount=10)
            file_handler.setFormatter(formatter)
            root.addHandler(file_handler)
        except OSError as exc:
            root.warning("Could not set up log file %s: %s", log_file, exc)

    if debug:
        root.setLevel(logging.DEBUG)
    else:
        root.setLevel(logging.INFO)

    return root
