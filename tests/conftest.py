import sys
import types


class FakeSenseHat:
    def __init__(self, *args, **kwargs):
        pass

    def get_temperature_from_humidity(self):
        return 20.0

    def get_temperature_from_pressure(self):
        return 20.0

    def get_temperature(self):
        return 20.0

    def get_humidity(self):
        return 50.0

    def get_pressure(self):
        return 1013.25

    def show_message(self, *args, **kwargs):
        pass

    def clear(self, *args, **kwargs):
        pass


fake_module = types.ModuleType("sense_hat")
fake_module.SenseHat = FakeSenseHat
sys.modules["sense_hat"] = fake_module
