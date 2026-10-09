import logging
import subprocess
import sys

from sensehatsensorstomqtt.log_setup import setup_logger


def test_setup_logger_in_isolation(tmp_path):
    log_file = tmp_path / "test.log"
    code = f"""
from sensehatsensorstomqtt.log_setup import setup_logger
logger = setup_logger(debug=True, log_file={str(log_file)!r})
logger.info("testing")
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"Subprocess failed with stderr:\n{result.stderr}"
    assert log_file.exists()


def test_setup_logger_no_log_file():
    logger = setup_logger(debug=True)
    assert logger.level == logging.DEBUG


def test_setup_logger_unwritable_path(caplog):
    # An unwritable/impossible path should warn, not raise
    with caplog.at_level(logging.WARNING):
        logger = setup_logger(debug=True, log_file="/proc/forbidden/test.log")
    assert logger.level == logging.DEBUG
    assert any("Could not set up log file" in record.getMessage() for record in caplog.records)
