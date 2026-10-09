import datetime

from sensehatsensorstomqtt.utils import is_night


def test_is_night_boundary_morning():
    # 06:59:59 is night
    t1 = datetime.datetime(2026, 1, 1, 6, 59, 59)
    assert is_night(current_time=t1) is True

    # 07:00:00 is day
    t2 = datetime.datetime(2026, 1, 1, 7, 0, 0)
    assert is_night(current_time=t2) is False


def test_is_night_boundary_evening():
    # 18:59:59 is day
    t1 = datetime.datetime(2026, 1, 1, 18, 59, 59)
    assert is_night(current_time=t1) is False

    # 19:00:00 is night
    t2 = datetime.datetime(2026, 1, 1, 19, 0, 0)
    assert is_night(current_time=t2) is True


def test_is_night_midday_and_midnight():
    # 12:00:00 is day
    assert is_night(current_time=datetime.datetime(2026, 1, 1, 12, 0, 0)) is False

    # 00:00:00 is night
    assert is_night(current_time=datetime.datetime(2026, 1, 1, 0, 0, 0)) is True


def test_is_night_default_time():
    # Without parameter, uses current time and returns boolean
    assert isinstance(is_night(), bool)
