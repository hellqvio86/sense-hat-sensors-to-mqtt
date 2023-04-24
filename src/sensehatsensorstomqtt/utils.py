"""
Utils
"""
import datetime


def is_night(*, current_time=datetime.datetime.now()):
    """
    Function to check if its night
    """
    if current_time.hour >= 6 and current_time.hour < 19:
        # Its not night
        return False
    else:
        return True
