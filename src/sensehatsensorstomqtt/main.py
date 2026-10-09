"""Main entry point for Sense HAT sensors to MQTT service."""

import contextlib
import logging
import logging.handlers
import signal
import sys
import threading
import time

import paho.mqtt.client as mqtt

from .args import args_handler
from .config import redact_config, validate_config
from .display import get_display
from .hardware import get_sense_hat
from .log_setup import setup_logger
from .sensor import publish_status, send_sensor_data

LOGGER = logging.getLogger(__name__)


def main(stop_event: threading.Event | None = None) -> None:
    """Main function."""
    try:
        raw_config = args_handler()
        config = validate_config(raw_config)
    except Exception as exc:
        logging.basicConfig(level=logging.ERROR)
        LOGGER.error("Configuration error: %s", exc)
        sys.exit(1)
        return

    setup_logger(debug=config["debug"], log_file=config["log_file"])

    if config["debug"]:
        LOGGER.debug("config: %s", redact_config(config))

    LOGGER.info("Starting Sense Hat Sensors to MQTT")

    if stop_event is None:
        stop_event = threading.Event()

    def _signal_handler(signum: int, _frame: object) -> None:
        if stop_event.is_set():
            LOGGER.warning("Received signal %s again, forcing exit...", signum)
            sys.exit(1)
        LOGGER.info("Received signal %s, initiating graceful shutdown...", signum)
        stop_event.set()

    with contextlib.suppress(ValueError, AttributeError):
        signal.signal(signal.SIGTERM, _signal_handler)
        signal.signal(signal.SIGINT, _signal_handler)

    sense = get_sense_hat()
    display = get_display(config=config, sense=sense)
    client_id = config.get("client_id")
    try:
        if client_id:
            mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=str(client_id))
        else:
            mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    except (AttributeError, TypeError):
        mqtt_client = mqtt.Client(client_id=str(client_id)) if client_id else mqtt.Client()

    interval = float(config.get("interval", 60.0))
    measurements = int(config.get("measurements", 3))

    from .sd_notify import notify_ready, notify_stopping, notify_watchdog

    notify_ready()

    try:
        consecutive_failures = 0
        while not stop_event.is_set():
            before_work = time.monotonic()
            try:
                send_sensor_data(
                    config=config,
                    measurements=measurements,
                    mqtt_client=mqtt_client,
                    sense=sense,
                    stop_event=stop_event,
                    display=display,
                )
                consecutive_failures = 0
                notify_watchdog()
            except Exception:
                consecutive_failures += 1
                LOGGER.exception(
                    "Error during sensor/publish cycle (consecutive failures: %d)",
                    consecutive_failures,
                )

            if stop_event.is_set():
                break

            after_work = time.monotonic()

            elapsed = after_work - before_work
            remaining = interval - elapsed
            min_pause = 1.0
            base_sleep = max(min_pause, remaining)
            if consecutive_failures > 0:
                sleep_time = min(300.0, base_sleep * min(consecutive_failures, 5))
            else:
                sleep_time = base_sleep

            LOGGER.debug("Sleeping %s seconds", sleep_time)

            if sleep_time > 0:
                stop_event.wait(timeout=sleep_time)
    except KeyboardInterrupt:
        LOGGER.info("Interrupted by keyboard, stopping...")
        stop_event.set()
    finally:
        LOGGER.info("Cleaning up resources before exit")
        notify_stopping()
        if mqtt_client is not None:
            publish_status(mqtt_client=mqtt_client, config=config, status="offline", wait=True)
            with contextlib.suppress(Exception):
                mqtt_client.disconnect()
            with contextlib.suppress(Exception):
                mqtt_client.loop_stop()
        if display is not None:
            with contextlib.suppress(Exception):
                display.clear()
        elif sense is not None:
            with contextlib.suppress(Exception):
                sense.clear()


if __name__ == "__main__":
    main()
