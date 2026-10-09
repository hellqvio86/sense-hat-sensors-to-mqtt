from unittest.mock import patch

import pytest

from sensehatsensorstomqtt.args import args_handler
from sensehatsensorstomqtt.config import redact_config
from sensehatsensorstomqtt.main import main


@pytest.fixture
def dummy_config(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text("host: localhost\ntopics:\n  - sensor/topic\n", encoding="utf-8")
    return str(config_file)


def test_args_handler_debug_does_not_leak_password(dummy_config, capsys):
    secret = "my_super_secret_pw"
    args_handler(["-D", "--password", secret, "--config_file", dummy_config])
    captured = capsys.readouterr()
    assert secret not in captured.out
    assert secret not in captured.err


def test_main_debug_logs_redacted_password(dummy_config, caplog, capsys):
    import threading

    secret = "secret_password_123"
    stop_event = threading.Event()

    def mock_send(*args, **kwargs):
        stop_event.set()

    with (
        patch("sys.argv", ["sensehatsensorstomqtt", "-D", "--password", secret, "--config_file", dummy_config]),
        patch("sensehatsensorstomqtt.main.setup_logger"),
        patch("sensehatsensorstomqtt.main.send_sensor_data", side_effect=mock_send),
    ):
        main(stop_event=stop_event)

    captured = capsys.readouterr()
    assert secret not in captured.out
    assert secret not in captured.err

    # Check logger output: secret must not appear, redacted '***' should appear
    for record in caplog.records:
        assert secret not in record.getMessage()


def test_redact_config_replaces_password():
    raw = {"host": "localhost", "password": "supersecretpassword", "port": 1883}
    redacted = redact_config(raw)
    assert redacted["password"] == "***"
    assert raw["password"] == "supersecretpassword"


def test_password_from_env(tmp_path, monkeypatch):
    monkeypatch.setenv("MQTT_PASSWORD", "env_secret_pass")
    monkeypatch.chdir(tmp_path)
    config = args_handler(["--host", "localhost", "--topics", "t1"])
    assert config["password"] == "env_secret_pass"


def test_password_from_file_cli(tmp_path):
    pw_file = tmp_path / "mqtt.pw"
    pw_file.write_text("file_secret_pass\n", encoding="utf-8")
    config = args_handler(["--host", "localhost", "--topics", "t1", "--password_file", str(pw_file)])
    assert config["password"] == "file_secret_pass"


def test_password_from_file_config(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    pw_file = tmp_path / "mqtt.pw"
    pw_file.write_text("yaml_file_secret_pass\n", encoding="utf-8")
    cfg = tmp_path / "config.yaml"
    cfg.write_text(f"host: localhost\npassword_file: {pw_file}\n", encoding="utf-8")
    config = args_handler(["--topics", "t1"])
    assert config["password"] == "yaml_file_secret_pass"


def test_password_file_missing_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        args_handler(["--host", "localhost", "--topics", "t1", "--password_file", str(tmp_path / "nonexistent.pw")])
