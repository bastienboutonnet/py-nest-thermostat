from cleo import Application, Command

from py_nest_thermostat.auth import Authenticator
from py_nest_thermostat.nest_api import NestThermostat

AUTHENTICATOR = Authenticator()


class DevicesCommand(Command):
    """
    Lists the devices in the current home and allows to choose one, if more than one is availavle.

    devices
    """

    def handle(self):
        thermostat = NestThermostat(AUTHENTICATOR)
        thermostat.get_devices()


application = Application()
application.add(DevicesCommand())


if __name__ == "__main__":
    application.run()
