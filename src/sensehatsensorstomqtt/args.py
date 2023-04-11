"""
args handler
"""
import os
import argparse

from .config import parse_config


def args_handler() -> dict:
    """
    Function for reading arguments and config file

    Returns
    dict - config

    """
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
        config = parse_config(config_file=args.config_file)
    elif os.path.exists("/etc/sensehatsensorstomqtt.yaml"):
        config = parse_config(config_file="/etc/sensehatsensorstomqtt.yaml")
    else:
        config = parse_config()

    if args.username:
        config["username"] = args.username

    if args.password:
        config["password"] = args.password

    if args.host:
        config["host"] = args.host

    if args.port:
        config["port"] = args.port

    if args.debug:
        config["debug"] = True

    if args.log_file:
        config["log_file"] = args.log_file

    if args.pid_file:
        config["pid_file"] = args.pid_file

    if args.daemon:
        config["daemon"] = args.daemon

    if args.topics:
        config["topics"] = [item.strip() for item in args.list.split(",")]

    if config["debug"]:
        print(f"config: {config}")

    return config
