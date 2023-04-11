"""
Sensor
"""
import datetime
import logging
import json

from random import randint
from time import sleep
from statistics import median

from sense_hat import SenseHat
from paho.mqtt.client import Client as MqttClient

from .consts import SLEEP_TIME_IN_SECONDS, MEASUREMENT_UNIT
from .utils import is_night


def send_sensor_data(
    *, config: dict, mqtt_client: MqttClient, measurements: int = 3
) -> None:
    """
    Takes measurements of temperature, humidity, and pressure using the Sense HAT module and publishes the results
    to an MQTT broker using the provided mqtt_client. Median values of each measurement are calculated based on
    the number of measurements specified. The data is published to each topic in the list of topics provided in the config
    dictionary as a JSON-encoded string.

    :param config: A dictionary containing the configuration parameters for the MQTT broker connection and the list of
                   topics to publish the data to.
    :param measurements: The number of measurements to take and calculate the median value of for each measurement type.
    :param mqtt_client: The MQTT client instance to use for publishing the data.
    :return: None
    """
    sense = SenseHat()
    msg = {}

    host = config["host"]
    username = config["username"]
    password = config["password"]
    port = config["port"]
    topics = config["topics"]

    # Take median of three readings
    for sensor_type in ["temperature", "humidity", "pressure"]:
        tmp = []
        for i in range(measurements):
            sensor_value = getattr(sense, f"get_{sensor_type}")()
            logging.debug(f"{sensor_type} - measurement {i} value: {sensor_value}")
            tmp.append(sensor_value)
            sleep(1)
        msg[sensor_type] = median(tmp)
        msg[f"unit_of_{sensor_type}"] = MEASUREMENT_UNIT[sensor_type]

    msg["time_utc"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")

    uri = f"mqtt://{username}:{password}@{host}:{port}"

    logging.info(f"Connecting to {uri}")

    mqtt_client.username_pw_set(username, password=password)
    mqtt_client.connect(host, port, 60)

    logging.info(f"Connected to {uri}")

    for topic in topics:
        data = json.dumps(msg).encode("utf-8")

        logging.info(f"Publishing msg: {msg} to topic: {topic}")
        mqtt_client.publish(topic=topic, payload=data, retain=True)

    logging.info("messages published")

    if is_night() is False:
        color_1 = (randint(0, 255), randint(0, 255), randint(0, 255))
        color_2 = (randint(0, 255), randint(0, 255), randint(0, 255))

        sense.show_message(
            f"{msg['pressure']:.2f} {msg['unit_of_pressure']}", text_colour=color_1
        )
        sleep(SLEEP_TIME_IN_SECONDS)

        sense.show_message(
            f"{msg['humidity']:.2f} {msg['unit_of_humidity']}", text_colour=color_2
        )
        sleep(SLEEP_TIME_IN_SECONDS)

        temperature_color = sense.get_temperature_color(msg["temperature"])

        sense.show_message(
            f"{msg['temperature']:.2f} {msg['unit_of_temperature']}",
            text_colour=temperature_color,
        )
    else:
        logging.info("Not running text on display, night mode!")
