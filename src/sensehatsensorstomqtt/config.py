"""
Config
"""
import os

import yaml


def parse_config(config_file: str = "config.yaml") -> dict:
    """
    Parse configuration file in YAML format.

    Args:
        config_file (str, optional): Path to configuration file. Defaults to "config.yaml".

    Returns:
        dict: A dictionary containing the parsed configuration values.

    Raises:
        FileNotFoundError: If the specified config file is not found.

    Examples:
        >>> parse_config("config.yaml")
        {
            'model':
                {
                    'name': 'my_model',
                    'learning_rate': 0.001
                },
            'data':
                {
                    'train_path': 'data/train.csv',
                    'test_path': 'data/test.csv'
                }
        }
    """

    config = {}

    if not os.path.isfile(config_file):
        raise FileNotFoundError(f"Configuration file '{config_file}' not found.")

    with open(config_file, "r", encoding="utf-8") as stream:
        config = yaml.safe_load(stream)

    config.setdefault("debug", False)
    config.setdefault("port", 1883)
    config.setdefault("daemon", False)
    config.setdefault(
        "log_file", "/var/log/sensehatsensorstomqtt/sensehatsensorstomqtt.log"
    )
    config.setdefault(
        "pid_file", "/run/sensehatsensorstomqtt/sensehatsensorstomqtt.pid"
    )

    return config
