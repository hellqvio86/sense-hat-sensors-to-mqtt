import pytest

from sensehatsensorstomqtt.args import args_handler


@pytest.fixture
def dummy_config(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text("host: localhost\n", encoding="utf-8")
    return str(config_file)


def test_args_topics_basic(dummy_config):
    config = args_handler(["--topics", "a,b", "--config_file", dummy_config])
    assert config["topics"] == ["a", "b"]


def test_args_topics_whitespace_and_trailing_comma(dummy_config):
    config = args_handler(["--topics", " a , b , ", "--config_file", dummy_config])
    assert config["topics"] == ["a", "b"]


def test_args_topics_empty_items(dummy_config):
    config = args_handler(["--topics", "a,,b", "--config_file", dummy_config])
    assert config["topics"] == ["a", "b"]


def test_args_topics_empty_string_rejected(dummy_config):
    with pytest.raises(SystemExit):
        args_handler(["--topics", "", "--config_file", dummy_config])


def test_args_topics_only_commas_rejected(dummy_config):
    with pytest.raises(SystemExit):
        args_handler(["--topics", " , , ", "--config_file", dummy_config])


def test_args_port_int(dummy_config):
    config = args_handler(["--port", "8883", "--config_file", dummy_config])
    assert config["port"] == 8883
    assert isinstance(config["port"], int)


def test_args_port_non_numeric_rejected(dummy_config):
    with pytest.raises(SystemExit):
        args_handler(["--port", "not-a-port", "--config_file", dummy_config])


def test_args_port_out_of_range_rejected(dummy_config):
    with pytest.raises(SystemExit):
        args_handler(["--port", "70000", "--config_file", dummy_config])


def test_args_cli_only_no_config_file(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    config = args_handler(["--host", "mqtt.local", "--topics", "a,b"])
    assert config["host"] == "mqtt.local"
    assert config["topics"] == ["a", "b"]
    assert config["port"] == 1883
    assert config["debug"] is False


def test_args_nonexistent_config_file_errors():
    with pytest.raises(FileNotFoundError):
        args_handler(["--config_file", "/nonexistent/config.yaml"])


def test_args_default_config_yaml_detected(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    local_cfg = tmp_path / "config.yaml"
    local_cfg.write_text("host: from-file.local\nport: 8883\n", encoding="utf-8")
    config = args_handler(["--topics", "a,b"])
    assert config["host"] == "from-file.local"
    assert config["port"] == 8883
    assert config["topics"] == ["a", "b"]


def test_args_cli_overrides_file(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    local_cfg = tmp_path / "config.yaml"
    local_cfg.write_text("host: from-file.local\nport: 8883\n", encoding="utf-8")
    config = args_handler(["--host", "from-cli.local", "--port", "1883", "--topics", "a,b"])
    assert config["host"] == "from-cli.local"
    assert config["port"] == 1883


def test_args_cadence_and_status(dummy_config):
    config = args_handler(
        [
            "--config_file",
            dummy_config,
            "--interval",
            "45.0",
            "--measurements",
            "5",
            "--sample_spacing",
            "2.0",
            "--status_topic",
            "sensors/status",
        ]
    )
    assert config["interval"] == 45.0
    assert config["measurements"] == 5
    assert config["sample_spacing"] == 2.0
    assert config["status_topic"] == "sensors/status"


def test_args_display_options(dummy_config):
    config = args_handler(
        [
            "--config_file",
            dummy_config,
            "--no-display",
            "--display_pause",
            "3.0",
            "--night_start",
            "22",
            "--night_end",
            "6",
        ]
    )
    assert config["display"] is False
    assert config["display_pause"] == 3.0
    assert config["night_start"] == 22
    assert config["night_end"] == 6

    config2 = args_handler(
        [
            "--config_file",
            dummy_config,
            "--display",
        ]
    )
    assert config2["display"] is True
