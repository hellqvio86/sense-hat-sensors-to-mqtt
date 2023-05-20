"""
Utils
"""
import datetime


def is_night(*, current_time=datetime.datetime.now()):
    """
    Function to check if its night
    """
    if current_time.hour <= 6:
        return True
    elif current_time.hour >= 19:
        return True
    else:
        return False
