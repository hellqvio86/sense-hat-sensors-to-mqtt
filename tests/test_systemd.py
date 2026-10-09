import configparser
import shutil
import subprocess
import tempfile
from pathlib import Path

SERVICE_PATH = Path(__file__).resolve().parent.parent / "systemd" / "sensehatsensorstomqtt.service"


def test_systemd_service_file_line_endings_are_lf():
    raw_bytes = SERVICE_PATH.read_bytes()
    assert b"\r" not in raw_bytes, "systemd unit file contains CRLF line endings"


def test_systemd_service_no_duplicate_keys_per_section():
    lines = SERVICE_PATH.read_text(encoding="utf-8").splitlines()
    seen_keys: dict[str, set[str]] = {}
    current_section = None

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            current_section = line[1:-1]
            seen_keys[current_section] = set()
            continue
        if "=" in line and current_section:
            key = line.split("=", 1)[0].strip()
            # In systemd, only specific keys like Environment can appear multiple times
            assert key not in seen_keys[current_section], f"Duplicate key '{key}' found in section [{current_section}]"
            seen_keys[current_section].add(key)


def test_systemd_service_content_and_hardening():
    content = SERVICE_PATH.read_text(encoding="utf-8")
    assert "Python Demo Service" not in content
    assert "enviroplus" not in content
    assert "RemainAfterExit" not in content
    assert "Restart=always" not in content

    config = configparser.ConfigParser(interpolation=None)
    config.read_string(content)

    assert config.get("Unit", "After") == "network-online.target"
    assert config.get("Unit", "Wants") == "network-online.target"
    assert config.get("Service", "Type") == "simple"
    assert config.get("Service", "Restart") == "on-failure"
    assert config.get("Service", "User") == "sensehat"
    assert config.get("Service", "Group") == "sensehat"
    assert "i2c" in config.get("Service", "SupplementaryGroups")
    assert "video" in config.get("Service", "SupplementaryGroups")
    assert "input" in config.get("Service", "SupplementaryGroups")
    assert config.get("Service", "NoNewPrivileges") == "true"
    assert config.get("Service", "ProtectSystem") == "strict"
    assert config.get("Service", "ProtectHome") == "true"
    assert config.get("Service", "PrivateTmp") == "true"


def test_systemd_analyze_verify_passes():
    if not shutil.which("systemd-analyze"):
        return

    content = SERVICE_PATH.read_text(encoding="utf-8")
    # Replace ExecStart with a known local executable for systemd-analyze verification
    test_content = content.replace("/usr/local/bin/sensehatsensorstomqtt", "/bin/sh -c true")

    with tempfile.NamedTemporaryFile("w", suffix=".service", delete=True) as tmp:
        tmp.write(test_content)
        tmp.flush()

        res = subprocess.run(
            ["systemd-analyze", "verify", tmp.name],
            capture_output=True,
            text=True,
        )
        assert res.returncode == 0, f"systemd-analyze verify failed: {res.stderr}"
