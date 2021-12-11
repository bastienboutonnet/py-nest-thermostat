from cleo import Application, Command
from rich.console import Console

from py_nest_thermostat.auth import Authenticator
from py_nest_thermostat.config import config
from py_nest_thermostat.nest_api import NestThermostat

console = Console()

AUTHENTICATOR = Authenticator(config)


class ListDevicesCommand(Command):
    """
    Lists the devices in the current home and allows to choose one, if more than one is availavle.

    devices
    """

    def handle(self):
        thermostat = NestThermostat(AUTHENTICATOR, config=config)
        thermostat.get_devices()


class DevicesStatsCommand(Command):
    """
    Loads the thermostat statistics such as: humidity, temperature, target temp, heating mode etc.

    stats
        {--save-to-db : When passed, the stats will be added to the backend database.}
        {--no-print : When passed, the stats not be printed.}
    """

    def handle(self):
        thermostat = NestThermostat(AUTHENTICATOR, config=config)
        thermostat.get_device_stats(
            no_print=self.option("no-print"), save_stats=self.option("save-to-db")  # type: ignore
        )


class SetTemperatureCommand(Command):
    """
    Sets the target temperature on your device

    temp
        {temperature : (float | int) Numeric value to which you want to heat or cool to.}
    """

    def handle(self):
        thermostat = NestThermostat(AUTHENTICATOR, config=config)
        thermostat.set_target_temperature(self.argument("temperature"))  # type: ignore


application = Application()
application.add(ListDevicesCommand())
application.add(DevicesStatsCommand())
application.add(SetTemperatureCommand())


if __name__ == "__main__":
    application.run()
