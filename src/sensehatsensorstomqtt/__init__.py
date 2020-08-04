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

from .daemonizer import Daemonizer
from .colors import get_color_for_temperature
from random import randint
from sense_hat import SenseHat
from hbmqtt.client import MQTTClient
from async_cron.job import CronJob
from async_cron.schedule import Scheduler

sys.path.append(os.path.split(os.path.dirname(sys.argv[0]))[0])

print("Path: {}".format(os.path.split(os.path.dirname(sys.argv[0]))[0]))

LOGGER = logging.getLogger(__name__)
CONFIG = {}



def parse_config(config_file='config.yaml'):
    config = {}

    if not os.path.isfile(config_file):
        return config # empty dict

    with open(config_file, 'r') as stream:
        config = yaml.safe_load(stream)

    return config


def setup_logger(*, debug=False, log_file='/var/log/sensehatsensorstomqtt/sensehatsensorstomqtt.log', daemon=False):
    root = logging.getLogger()
    file_handler = None
    max_bytes = 3 * 10**6
    backup_count = 10
    formatter = logging.Formatter('%(asctime)s %(process)d %(processName)-10s %(name)-8s %(funcName)-8s %(levelname)-8s %(message)s')

    if debug:
        file_handler = logging.handlers.RotatingFileHandler(log_file, 'a', max_bytes, backup_count)
        file_handler.setFormatter(formatter)

    if daemon:
        file_handler = logging.handlers.RotatingFileHandler(log_file, 'a', max_bytes, backup_count)
        file_handler.setFormatter(formatter)
    else:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        root.addHandler(console_handler)

    if debug:
        root.setLevel(logging.DEBUG)
    
    if file_handler:
        root.addHandler(file_handler)


async def send_sensor_data():
    sense = SenseHat()
    msg = {}

    host     = CONFIG['host']
    username = CONFIG['username']
    password = CONFIG['password']
    port     = CONFIG['port']
    topics   = CONFIG['topics']

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
    temperature_color = get_color_for_temperature(msg['temperature'])
    sense.show_message(f"{msg['temperature']:.2f} {msg['unit_of_temperature']}", text_colour=temperature_color)



def main():
    """Main function."""
    global CONFIG

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
    
    setup_logger(debug=CONFIG['debug'], log_file=CONFIG['log_file'], daemon = CONFIG['daemon'])

    if CONFIG['daemon']:
        if CONFIG['debug']:
            print('Forking!')
        Daemonizer(pid_file=CONFIG['pid_file'])


    LOGGER.info("Starting Sense Hat Sensors to MQTT")

    msh = Scheduler(locale='sv_SE')
    job = CronJob(name='send_sensor_data').every(30).second.go(send_sensor_data)
    msh.add_job(job)

    loop = asyncio.get_event_loop()

    try:
        loop.run_until_complete(msh.start())
    except KeyboardInterrupt:
        print('exit')
    
    return

if __name__ == "__main__":
    main()