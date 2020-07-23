import argparse
import asyncio
import logging
import logging.handlers
import yaml
import pprint
import sys
import os
import sense_hat

from sense_hat import SenseHat
from hbmqtt.client import MQTTClient
from async_cron.job import CronJob
from async_cron.schedule import Scheduler

sys.path.append(os.path.split(os.path.dirname(sys.argv[0]))[0])

try:
    import aiocasambi
except ModuleNotFoundError as err:
    pprint.pprint(sys.path)
    raise err

LOGGER = logging.getLogger(__name__)

def parse_config(config_file='config.yaml'):
    config = {}

    if not os.path.isfile(config_file):
        return config # empty dict

    with open(config_file, 'r') as stream:
        config = yaml.safe_load(stream)

    return config


def setup_logger(*, debug=False):
    root = logging.getLogger()
    formatter = logging.Formatter('%(asctime)s %(process)d %(processName)-10s %(name)-8s %(funcName)-8s %(levelname)-8s %(message)s')

    if debug:
        max_bytes = 3 * 10**6
        backup_count = 10
        file_handler = logging.handlers.RotatingFileHandler('sensehat.log', 'a', max_bytes, backup_count)
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root.addHandler(console_handler)

    if debug:
        root.setLevel(logging.DEBUG)


@asyncio.coroutine
def send_sensor_data(host, user, password, port, topics):
    sense = SenseHat()
    msg = {}

    msg['temperature'] = sense.get_temperature()
    msg['humidity'] = sense.get_humidity()
    msg['pressure'] = sense.get_pressure()

    uri = f"mqtt://{user}:{password}@{host}:{port}"


    C = MQTTClient()
    yield from C.connect(uri)

    logger.info(f"Connected to {uri}")

    tasks = []
    
    for topic in topics:
        data = json.dumps(msg)
        tasks.append(asyncio.ensure_future(C.publish(topic, data)))
    yield from asyncio.wait(tasks)
    logger.info("messages published")
    yield from C.disconnect()

    logger.info('Disconnected')


async def main(*, user, password, host, topics, port=1883, sslcontext=False):
    """Main function."""
    LOGGER.info("Starting Sense Hat Sensors to MQTT")

    msh = Scheduler()
    job = CronJob(name='minute').every(1).minute.go(send_sensor_data, host, user, password, port, topics)

    msh.add_job(job)

    loop = asyncio.get_event_loop()

    try:
        loop.run_until_complete(msh.start())
    except KeyboardInterrupt:
        print('exit')

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--user", type=str, required=False)
    parser.add_argument("--password", type=str, required=False)
    parser.add_argument("--host", type=str, required=False)
    parser.add_argument("--port", type=str, required=False)
    parser.add_argument("--topics", type=str, required=False)
    parser.add_argument("-D", "--debug", action="store_true")
    args = parser.parse_args()

    config = parse_config()

    if args.user:
        config['user'] = args.user
    
    if args.password:
        config['password'] = args.password
    
    if args.host:
        config['host'] = args.host
    
    if args.port:
        config['port'] = args.port

    if args.debug:
        config['debug'] = True

    if args.topics:
        config['topics'] = [item.strip() for item in args.list.split(',')]

    if 'debug' not in config:
        config['debug'] = False

    if 'port' not in config:
        config['port'] = 1883
    
    setup_logger(debug=config['debug'])

    LOGGER.info(
        f"{args.email}, {args.api_key}, {args.user_password}, {args.network_password}"
    )

    try:
        asyncio.run(
            main(
                user=config['user'],
                password=config['password'],
                host=config['host'],
                topics=config['topics'],
                port=config['port']
            )
        )
    except KeyboardInterrupt:
        pass