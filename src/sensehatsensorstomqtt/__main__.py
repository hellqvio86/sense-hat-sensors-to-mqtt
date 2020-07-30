import argparse
import asyncio
import logging
import logging.handlers
import yaml
import pprint
import sys
import os
import json
import datetime

from random import randint
from sense_hat import SenseHat
from hbmqtt.client import MQTTClient
from async_cron.job import CronJob
from async_cron.schedule import Scheduler

sys.path.append(os.path.split(os.path.dirname(sys.argv[0]))[0])

LOGGER = logging.getLogger(__name__)
CONFIG = {}

COLOR_HIGHLIGHTED_PINK = (239, 87, 119)
COLOR_DARK_PERIWINKLE = (87, 95, 207)
COLOR_MEGAMAN = (75, 207, 250)
COLOR_FRESH_TURQUOISE = (52, 231, 228)
COLOR_MINTY_GREEN = (11, 232, 129)
COLOR_SIZZLING_RED = (245, 59, 87)
COLOR_FREE_SPEECH_BLUE = (60, 64, 198)
COLOR_SPIRO_DISCO_BALL = (15, 188, 249)
COLOR_JADE_DUST = (0, 216, 214)
COLOR_GREEN_TEAL = (5, 196, 107)
COLOR_NARENJI_ORANGE = (255, 192, 72)
COLOR_YRIEL_YELLOW = (255, 221, 89)
COLOR_SUNSET_ORANGE = (255, 94, 87)
COLOR_HINT_OF_ELUSIVE_BLUE = (210, 218, 226)
COLOR_GOOD_NIGHT = (72, 84, 96)
COLOR_CHROME_YELLOW = (255, 168, 1)
COLOR_VIBRANT_YELLOW = (255, 211, 42)
COLOR_RED_ORANGE = (255, 63, 52)
COLOR_LONDON_SQUARE = (128, 142, 155)
COLOR_BLACK_PEARL = (30, 39, 46)

def parse_config(config_file='config.yaml'):
    config = {}

    if not os.path.isfile(config_file):
        return config # empty dict

    with open(config_file, 'r') as stream:
        config = yaml.safe_load(stream)

    return config


def setup_logger(*, debug=False, log_file='/var/log/sensehatsensorstomqtt.log'):
    root = logging.getLogger()
    formatter = logging.Formatter('%(asctime)s %(process)d %(processName)-10s %(name)-8s %(funcName)-8s %(levelname)-8s %(message)s')

    if debug:
        max_bytes = 3 * 10**6
        backup_count = 10
        file_handler = logging.handlers.RotatingFileHandler(log_file, 'a', max_bytes, backup_count)
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root.addHandler(console_handler)

    if debug:
        root.setLevel(logging.DEBUG)


async def send_sensor_data():
    sense = SenseHat()
    msg = {}

    host=CONFIG['host']
    username=CONFIG['username']
    password=CONFIG['password']
    port=CONFIG['port']
    topics=CONFIG['topics']

    msg['temperature'] = sense.get_temperature()
    msg['unit_of_temperature'] = 'C'
    msg['humidity'] = sense.get_humidity()
    msg['unit_of_humidity'] = '%'
    msg['pressure'] = sense.get_pressure()
    msg['unit_of_pressure'] = 'mbar'
    msg['time_utc'] = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")

    uri = f"mqtt://{username}:{password}@{host}:{port}"

    LOGGER.info(f"Connecting to {uri}")

    C = MQTTClient()
    
    await C.connect(uri)

    LOGGER.info(f"Connected to {uri}")

    tasks = []
    
    for topic in topics:
        data = json.dumps(msg).encode('utf-8')

        LOGGER.info(f"Publishing msg: {msg} to topic: {topic}")
        tasks.append(asyncio.ensure_future(C.publish(topic, data)))
    
    await asyncio.wait(tasks)
    
    LOGGER.info("messages published")

    await C.disconnect()

    LOGGER.info('Disconnected')


    r1 = (randint(0,255), randint(0,255), randint(0,255))
    r2 = (randint(0,255), randint(0,255), randint(0,255))
    r3 = (randint(0,255), randint(0,255), randint(0,255))
    sense.show_message(f"{msg['pressure']:.2f} {msg['unit_of_pressure']}", text_colour=r1)
    await asyncio.sleep(5)
    sense.show_message(f"{msg['humidity']:.2f} {msg['unit_of_humidity']}", text_colour=r2)
    await asyncio.sleep(5)
    sense.show_message(f"{msg['temperature']:.2f} {msg['unit_of_temperature']}", text_colour=r3)



def main(*, sslcontext=False):
    """Main function."""
    LOGGER.info("Starting Sense Hat Sensors to MQTT")

    msh = Scheduler(locale='sv_SE')
    job = CronJob(name='send_sensor_data').every(30).second.go(send_sensor_data)
    msh.add_job(job)

    loop = asyncio.get_event_loop()

    try:
        loop.run_until_complete(msh.start())
    except KeyboardInterrupt:
        print('exit')

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", type=str, required=False)
    parser.add_argument("--password", type=str, required=False)
    parser.add_argument("--host", type=str, required=False)
    parser.add_argument("--port", type=str, required=False)
    parser.add_argument("--topics", type=str, required=False)
    parser.add_argument("--config_file", type=str, required=False)
    parser.add_argument("--log_file", type=str, required=False)
    parser.add_argument("-D", "--debug", action="store_true")
    args = parser.parse_args()

    if args.config_file:
        CONFIG = parse_config(config_file=args.config_file)
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
        CONFIG['log_file'] = '/var/log/sensehatsensorstomqtt.log'

    if args.topics:
        CONFIG['topics'] = [item.strip() for item in args.list.split(',')]

    if 'debug' not in CONFIG:
        CONFIG['debug'] = False

    if 'port' not in CONFIG:
        CONFIG['port'] = 1883
    

    print(f"config: {CONFIG}")

    setup_logger(debug=CONFIG['debug'], log_file=CONFIG['log_file'])

    main()