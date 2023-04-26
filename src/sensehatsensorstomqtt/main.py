"""
Simple program to send Sensehat messurements through MQTT
to Home Assistant
"""
import logging
import logging.handlers
import time

from time import sleep

import paho.mqtt.client as mqtt

from setproctitle import setproctitle

from .daemonizer import Daemonizer
from .logging import setup_logger
from .args import args_handler
from .sensor import send_sensor_data


def main():
    """Main function."""
    config = {}

    setproctitle("sensehatsensorstomqtt")

    config = args_handler()

    if config["debug"]:
        print(f"config: {config}")

    setup_logger(
        debug=config["debug"], log_file=config["log_file"], daemon=config["daemon"]
    )

    if config["daemon"]:
        if config["debug"]:
            print("Forking!")
        Daemonizer(pid_file=config["pid_file"])

    logging.info("Starting Sense Hat Sensors to MQTT")

    while True:
        before_work = time.time()
        mqtt_client = mqtt.Client()

        send_sensor_data(config=config, mqtt_client=mqtt_client)

        after_work = time.time()

        sleep_time = round(60 - (after_work - before_work))

        logging.debug(f"Sleeping {sleep_time} seconds")

        if sleep_time > 0:
            sleep(sleep_time)


if __name__ == "__main__":
    main()
