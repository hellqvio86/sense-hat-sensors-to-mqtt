'''
Simple program to send Sensehat messurements through MQTT
to Home Assistant
'''
import argparse
import asyncio
import logging
import logging.handlers
import yaml
import sys
import os
import json
import datetime
import time

from .daemonizer import Daemonizer
from .colors import get_color_for_temperature
from random import randint
from time import sleep

from setproctitle import setproctitle
from sense_hat import SenseHat
import paho.mqtt.client as mqtt
from statistics import median

sys.path.append(os.path.split(os.path.dirname(sys.argv[0]))[0])

LOGGER = logging.getLogger(__name__)
CONFIG = {}

MQTT_CLIENT = None


def parse_config(config_file='config.yaml'):
    '''
    Parse configuration
    '''
    config = {}

    if not os.path.isfile(config_file):
        # Return empty dict
        return config

    with open(config_file, 'r') as stream:
        config = yaml.safe_load(stream)

    return config


def setup_logger(
        *,
        debug=False,
        log_file='/var/log/sensehatsensorstomqtt/sensehatsensorstomqtt.log',
        daemon=False):
    '''
    Function for setting up logging
    '''
    root = logging.getLogger()
    file_handler = None
    max_bytes = 3 * 10**6
    backup_count = 10
    formatter = logging.Formatter(
        '%(asctime)s %(process)d %(processName)-10s %(name)-8s %(funcName)-8s %(levelname)-8s %(message)s')

    if debug:
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            'a',
            max_bytes,
            backup_count
        )
        file_handler.setFormatter(formatter)

    if daemon:
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            'a',
            max_bytes,
            backup_count
        )
        file_handler.setFormatter(formatter)
    else:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        root.addHandler(console_handler)

    if debug:
        root.setLevel(logging.DEBUG)

    if file_handler:
        root.addHandler(file_handler)


def send_sensor_data(measurements=3):
    '''
    Semd semse hat measurement
    '''
    global MQTT_CLIENT
    sense = SenseHat()
    msg = {}

    host = CONFIG['host']
    username = CONFIG['username']
    password = CONFIG['password']
    port = CONFIG['port']
    topics = CONFIG['topics']

    # Take median of three readings
    tmp = []
    for i in range(0, measurements):
        temperature = sense.get_temperature()
        LOGGER.debug(f"temperature - measurement {i} value: {temperature}")
        tmp.append(temperature)
        sleep(1)
    msg['temperature'] = median(tmp)
    msg['unit_of_temperature'] = 'C'

    tmp = []
    for i in range(0, measurements):
        humidity = sense.get_humidity()
        LOGGER.debug(f"humidity - measurement {i} value: {humidity}")
        tmp.append(humidity)
        sleep(1)
    msg['humidity'] = median(tmp)
    msg['unit_of_humidity'] = '%'

    tmp = []
    for i in range(0, measurements):
        pressure = sense.get_pressure()
        LOGGER.debug(f"pressure - measurement {i} value: {pressure}")
        tmp.append(pressure)
        sleep(1)
    msg['pressure'] = median(tmp)
    msg['unit_of_pressure'] = 'mbar'
    msg['time_utc'] = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")

    uri = f"mqtt://{username}:{password}@{host}:{port}"

    LOGGER.info(f"Connecting to {uri}")

    MQTT_CLIENT = mqtt.Client()
    MQTT_CLIENT.username_pw_set(username, password=password)
    MQTT_CLIENT.connect(host, port, 60)

    LOGGER.info(f"Connected to {uri}")

    for topic in topics:
        data = json.dumps(msg).encode('utf-8')

        # WILL_SET()
        # will_set(topic, payload=None, qos=0, retain=False)
        # Set a Will to be sent to the broker. If the client disconnects without calling disconnect(), 
        # the broker will publish the message on its behalf.
        #
        # topic
        # the topic that the will message should be published on.
        # payload
        # the message to send as a will. If not given, or set to None a zero length message will be 
        # used as the will. Passing an int or float will result in the payload being converted to a 
        # string representing that number. If you wish to send a true int/float, use struct.pack() 
        # to create the payload you require.
        #
        # qos
        # the quality of service level to use for the will.
        #
        # retain
        # if set to True, the will message will be set as the “last known good”/retained message for the topic.
        # Raises a ValueError if qos is not 0, 1 or 2, or if topic is None or has zero string length.
        #
        MQTT_CLIENT.will_set(topic, payload=None, qos=0, retain=True)

        LOGGER.info(f"Publishing msg: {msg} to topic: {topic}")
        MQTT_CLIENT.publish(topic=topic, payload=data)

    LOGGER.info("messages published")

    color_1 = (randint(0, 255), randint(0, 255), randint(0, 255))
    color_2 = (randint(0, 255), randint(0, 255), randint(0, 255))

    sense.show_message(
        f"{msg['pressure']:.2f} {msg['unit_of_pressure']}",
        text_colour=color_1)
    sleep(5)

    sense.show_message(
        f"{msg['humidity']:.2f} {msg['unit_of_humidity']}",
        text_colour=color_2)
    sleep(5)

    temperature_color = get_color_for_temperature(msg['temperature'])

    sense.show_message(
        f"{msg['temperature']:.2f} {msg['unit_of_temperature']}",
        text_colour=temperature_color)


def main():
    """Main function."""
    global CONFIG

    setproctitle('sensehatsensorstomqtt')

    parser = argparse.ArgumentParser()
    parser.add_argument("--username", type=str, required=False)
    parser.add_argument("--password", type=str, required=False)
    parser.add_argument("--host", type=str, required=False)
    parser.add_argument("--port", type=str, required=False)
    parser.add_argument("--topics", type=str, required=False)
    parser.add_argument("--config_file", type=str, required=False)
    parser.add_argument("--log_file", type=str, required=False)
    parser.add_argument("--pid_file", type=str, required=False)
    parser.add_argument("-D", "--debug", action="store_true")
    parser.add_argument("--daemon", action="store_true")
    args = parser.parse_args()

    if args.config_file:
        CONFIG = parse_config(config_file=args.config_file)
    elif os.path.exists('/etc/sensehatsensorstomqtt.yaml'):
        CONFIG = parse_config(config_file='/etc/sensehatsensorstomqtt.yaml')
    else:
        CONFIG = parse_config()

    if args.username:
        CONFIG['username'] = args.username

    if args.password:
        CONFIG['password'] = args.password

    if args.host:
        CONFIG['host'] = args.host

    if args.port:
        CONFIG['port'] = args.port

    if args.debug:
        CONFIG['debug'] = True

    if args.log_file:
        CONFIG['log_file'] = args.log_file
    else:
        CONFIG['log_file'] = '/var/log/sensehatsensorstomqtt/sensehatsensorstomqtt.log'

    if args.pid_file:
        CONFIG['pid_file'] = args.pid_file
    else:
        CONFIG['pid_file'] = '/run/sensehatsensorstomqtt/sensehatsensorstomqtt.pid'

    if args.daemon:
        CONFIG['daemon'] = args.daemon
    elif 'daemon' not in CONFIG:
        CONFIG['daemon'] = False

    if args.topics:
        CONFIG['topics'] = [item.strip() for item in args.list.split(',')]

    if 'debug' not in CONFIG:
        CONFIG['debug'] = False

    if 'port' not in CONFIG:
        CONFIG['port'] = 1883

    if CONFIG['debug']:
        print(f"config: {CONFIG}")

    setup_logger(
        debug=CONFIG['debug'],
        log_file=CONFIG['log_file'],
        daemon=CONFIG['daemon']
    )

    if CONFIG['daemon']:
        if CONFIG['debug']:
            print('Forking!')
        Daemonizer(pid_file=CONFIG['pid_file'])

    LOGGER.info("Starting Sense Hat Sensors to MQTT")

    while(True):
        before_work = time.time()
        send_sensor_data()

        after_work = time.time()

        sleep_time = round(60 - (after_work - before_work))

        LOGGER.debug(f"Sleeping {sleep_time} seconds")

        if sleep_time > 0:
            sleep(sleep_time)

    return


if __name__ == "__main__":
    main()
