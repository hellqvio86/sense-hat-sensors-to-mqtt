import pytest

from sensehatsensorstomqtt.config import apply_defaults, parse_config, validate_port


def test_parse_config_valid_file(tmp_path):
    config_data = """
host: "mqtt.example.com"
port: 8883
username: "iot_user"
password: "secret_password"
topics:
  - "sensors/livingroom"
"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(config_data, encoding="utf-8")

    actual = parse_config(str(config_file))

    assert actual["host"] == "mqtt.example.com"
    assert actual["port"] == 8883
    assert actual["username"] == "iot_user"
    assert actual["password"] == "secret_password"
    assert actual["topics"] == ["sensors/livingroom"]
    assert actual["debug"] is False
    assert actual["log_file"] is None


def test_parse_config_defaults(tmp_path):
    config_file = tmp_path / "empty.yaml"
    config_file.write_text("", encoding="utf-8")

    actual = parse_config(str(config_file))

    assert actual["debug"] is False
    assert actual["port"] == 1883
    assert actual["log_file"] is None


def test_parse_config_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        parse_config("nonexistent_config.yaml")


def test_parse_config_port_coercion_and_validation(tmp_path):
    cfg_file = tmp_path / "config_str_port.yaml"
    cfg_file.write_text("port: '8883'\n", encoding="utf-8")
    parsed = parse_config(str(cfg_file))
    assert parsed["port"] == 8883
    assert isinstance(parsed["port"], int)

    bad_cfg = tmp_path / "config_bad_port.yaml"
    bad_cfg.write_text("port: 70000\n", encoding="utf-8")
    with pytest.raises(ValueError):
        parse_config(str(bad_cfg))

    bad_str_cfg = tmp_path / "config_nan_port.yaml"
    bad_str_cfg.write_text("port: 'invalid'\n", encoding="utf-8")
    with pytest.raises(ValueError):
        parse_config(str(bad_str_cfg))


def test_validate_port_range():
    assert validate_port(1) == 1
    assert validate_port(65535) == 65535
    assert validate_port("1883") == 1883

    with pytest.raises(ValueError):
        validate_port(0)
    with pytest.raises(ValueError):
        validate_port(65536)
    with pytest.raises(ValueError):
        validate_port("invalid")


def test_apply_defaults_preserves_existing():
    cfg = {"debug": True, "port": 9999, "log_file": "/tmp/test.log"}
    result = apply_defaults(cfg)
    assert result["debug"] is True
    assert result["port"] == 9999
    assert result["log_file"] == "/tmp/test.log"
