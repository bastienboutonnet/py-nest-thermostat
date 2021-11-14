from cleo import Application, Command
from rich.console import Console

from py_nest_thermostat.auth import Authenticator
from py_nest_thermostat.nest_api import NestThermostat

console = Console()

AUTHENTICATOR = Authenticator()


class ListDevicesCommand(Command):
    """
    Lists the devices in the current home and allows to choose one, if more than one is availavle.

    devices
    """

    def handle(self):
        thermostat = NestThermostat(AUTHENTICATOR)
        thermostat.get_devices()


class DevicesStatsCommand(Command):
    """
    Loads the thermostat statistics such as: humidity, temperature, target temp, heating mode etc.

    stats
    """

    def handle(self):
        thermostat = NestThermostat(AUTHENTICATOR)
        thermostat.get_device_stats()


class SetTemperatureCommand(Command):
    """
    Sets the target temperature on your device

    temp
        {temperature : (float | int) What temperature do you want your heating at?}
    """

    def handle(self):
        thermostat = NestThermostat(AUTHENTICATOR)
        thermostat.set_target_temperature(self.argument("temperature"))  # type: ignore


application = Application()
application.add(ListDevicesCommand())
application.add(DevicesStatsCommand())
application.add(SetTemperatureCommand())


if __name__ == "__main__":
    application.run()
