"""
Utils
"""
import datetime


def is_night():
    """
    Function to check if its night
    """
    now = datetime.datetime.now()
    if now.hour >= 6 and now.hour < 19:
        # Its not night
        return False
    else:
        return True
