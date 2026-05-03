import os
import tempfile

import pytest

from sensehatsensorstomqtt.config import parse_config


def test_parse_config():
    # Create a temporary config file with test data
    config_data = """
    model:
        name: my_model
        learning_rate: 0.001
    data:
        train_path: data/train.csv
        test_path: data/test.csv
    """
    with tempfile.NamedTemporaryFile(mode="w+", delete=False) as f:
        f.write(config_data)
        config_file = f.name

    # Test with the temporary config file
    expected = {
        "model": {
            "name": "my_model",
            "learning_rate": 0.001,
        },
        "data": {
            "train_path": "data/train.csv",
            "test_path": "data/test.csv",
        },
        "debug": False,
        "port": 1883,
        "daemon": False,
        "log_file": "/var/log/sensehatsensorstomqtt/sensehatsensorstomqtt.log",
        "pid_file": "/run/sensehatsensorstomqtt/sensehatsensorstomqtt.pid",
    }
    actual = parse_config(config_file)
    assert actual == expected

    # Remove the temporary config file
    os.unlink(config_file)

    # Test with a missing config file
    with pytest.raises(FileNotFoundError):
        parse_config("missing_config.yaml")
