from unittest.mock import MagicMock, patch

import pytest

from sensehatsensorstomqtt.config import validate_config
from sensehatsensorstomqtt.sensor import publish


@pytest.mark.parametrize(
    "invalid_host",
    [None, "", "   "],
)
def test_validation_missing_or_empty_host(invalid_host):
    data = {"host": invalid_host, "topics": ["topic/1"]}
    with pytest.raises(ValueError, match="host"):
        validate_config(data)


@pytest.mark.parametrize(
    "invalid_topics",
    [None, [], "", "   ", " , , "],
)
def test_validation_missing_or_empty_topics(invalid_topics):
    data = {"host": "localhost", "topics": invalid_topics}
    with pytest.raises(ValueError, match="topics"):
        validate_config(data)


@pytest.mark.parametrize(
    "bad_port",
    [0, 65536, "not-a-port", -1],
)
def test_validation_bad_port(bad_port):
    data = {"host": "localhost", "topics": ["topic/1"], "port": bad_port}
    with pytest.raises(ValueError, match=r"[Pp]ort"):
        validate_config(data)


@pytest.mark.parametrize(
    "input_topics,expected",
    [
        ("sensors/livingroom", ["sensors/livingroom"]),
        ("sensors/a, sensors/b", ["sensors/a", "sensors/b"]),
        (["sensors/a", " sensors/b "], ["sensors/a", "sensors/b"]),
        ("  sensors/a , , sensors/b  ", ["sensors/a", "sensors/b"]),
    ],
)
def test_validation_topics_normalization(input_topics, expected):
    cfg = validate_config({"host": "localhost", "topics": input_topics})
    assert cfg.topics == expected
    assert cfg["topics"] == expected


def test_anonymous_broker_validation_and_publish(caplog):
    cfg = validate_config({"host": "broker.local", "topics": ["sensors/test"]})
    assert cfg.username is None
    assert cfg.password is None

    fake_client = MagicMock()
    fake_client.is_connected.return_value = False
    fake_msg_info = MagicMock()
    fake_msg_info.rc = 0
    fake_msg_info.is_published.return_value = True
    fake_client.publish.return_value = fake_msg_info

    with caplog.at_level("INFO"):
        publish(cfg, {"temperature": 21.0}, fake_client)

    # Anonymous broker: username_pw_set must not be called
    assert not fake_client.username_pw_set.called
    fake_client.connect.assert_called_once_with("broker.local", 1883, 60)
    # Redacted URI should be mqtt://broker.local:1883 without 'None'
    assert "mqtt://broker.local:1883" in caplog.text
    assert "None" not in caplog.text


def test_main_exits_on_invalid_config(caplog):
    with (
        patch("sensehatsensorstomqtt.main.args_handler", return_value={"host": "", "topics": []}),
        patch("sys.exit", side_effect=SystemExit(1)) as mock_exit,
        pytest.raises(SystemExit),
    ):
        from sensehatsensorstomqtt.main import main

        main()
    mock_exit.assert_called_once_with(1)
    assert any("Configuration error" in record.message for record in caplog.records)


def test_config_dataclass_mapping_interface():
    from sensehatsensorstomqtt.config import Config

    cfg = Config.from_dict(
        {
            "host": "localhost",
            "topics": ["t1"],
            "custom_key": "custom_val",
        }
    )

    assert cfg["host"] == "localhost"
    assert cfg["custom_key"] == "custom_val"
    assert "host" in cfg
    assert "custom_key" in cfg
    assert "nonexistent" not in cfg
    assert cfg.get("host") == "localhost"
    assert cfg.get("custom_key") == "custom_val"
    assert cfg.get("missing", "default") == "default"

    cfg["host"] = "otherhost"
    assert cfg.host == "otherhost"
    cfg["new_key"] = 123
    assert cfg["new_key"] == 123

    with pytest.raises(KeyError):
        _ = cfg["completely_unknown"]

    keys = list(cfg.keys())
    assert "host" in keys
    assert "custom_key" in keys
    assert "new_key" in keys

    items = dict(cfg.items())
    assert items["host"] == "otherhost"
    assert items["custom_key"] == "custom_val"

    d = dict(cfg)
    assert d["host"] == "otherhost"


def test_config_validation_coercions():
    cfg = validate_config(
        {
            "host": "localhost",
            "topics": ["t1"],
            "debug": "yes",
            "qos": "2",
            "retain": "false",
        }
    )
    assert cfg.debug is True
    assert cfg.qos == 2
    assert cfg.retain is False

    cfg2 = validate_config(
        {
            "host": "localhost",
            "topics": ["t1"],
            "debug": "0",
            "retain": "true",
        }
    )
    assert cfg2.debug is False
    assert cfg2.retain is True


def test_config_validation_invalid_types():
    with pytest.raises(ValueError, match="debug"):
        validate_config({"host": "localhost", "topics": ["t1"], "debug": "maybe"})

    with pytest.raises(ValueError, match="retain"):
        validate_config({"host": "localhost", "topics": ["t1"], "retain": "invalid"})

    with pytest.raises(ValueError, match="QoS"):
        validate_config({"host": "localhost", "topics": ["t1"], "qos": "not-a-number"})

    with pytest.raises(ValueError, match="QoS"):
        validate_config({"host": "localhost", "topics": ["t1"], "qos": 99})

    with pytest.raises(ValueError, match="topics"):
        validate_config({"host": "localhost", "topics": 12345})


def test_validate_config_with_config_instance():
    from sensehatsensorstomqtt.config import Config

    instance = Config(host="myhost", topics=["topic1"])
    validated = validate_config(instance)
    assert validated is instance
    assert validated.host == "myhost"
