"""
Utils
"""
import datetime
import logging


def is_night(*, current_time=None):
    """
    Function to check if its night
    """
    real_current_time = None
    if current_time:
        real_current_time = current_time
    else:
        real_current_time = datetime.datetime.now()

    logging.debug("current_time: %s", real_current_time)

    if real_current_time.hour <= 6:
        return True
    elif real_current_time.hour >= 19:
        return True
    else:
        return False
