import logging
from datetime import datetime
from pathlib import Path

from cleo import Application, Command
from rich.console import Console

from py_nest_thermostat import __version__
from py_nest_thermostat.auth import Authenticator
from py_nest_thermostat.config import config
from py_nest_thermostat.logger import log
from py_nest_thermostat.nest_api import NestThermostat

console = Console()

AUTHENTICATOR = Authenticator(config)


def parse_start_end_datetime(start_date_str: str, end_date_str: str) -> tuple[datetime, datetime]:
    datetime_pattern: str = "%Y-%m-%d %H:%M:%S.%f"
    start_datetime = datetime.strptime("1901-01-01 00:00:00.00", datetime_pattern)
    end_datetime = datetime.utcnow()

    if start_date_str:
        start_datetime = datetime.strptime(start_date_str, datetime_pattern)
    if end_date_str:
        end_datetime = datetime.strptime(end_date_str, datetime_pattern)

    return start_datetime, end_datetime


class ListDevicesCommand(Command):
    """
    Lists the devices in the current home and allows to choose one, if more than one is availavle.

    devices
    """

    def handle(self):
        if self.io.output.is_debug():
            log.setLevel(logging.DEBUG)
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
        if self.io.output.is_debug():
            log.setLevel(logging.DEBUG)
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
        if self.io.output.is_debug():
            log.setLevel(logging.DEBUG)
        thermostat = NestThermostat(AUTHENTICATOR, config=config)
        thermostat.set_target_temperature(self.argument("temperature"))  # type: ignore


class DownloadStats(Command):
    """
    Downloads your device historical measurements. Requires a database backend and collection to be set up.

    dl
        {--start-date : (str): YYYY-MM-DD data from which you want to get data.}
        {--end-date : (str): YYYY-MM-DD data up to which you want to get data.}
        {--save-path : (str): Full path to which you would like to get your csv. File is named nest_stats_start_date_end_date}
    """  # noqa

    def handle(self):
        if self.io.output.is_debug():
            log.setLevel(logging.DEBUG)
        start_date_str = self.option("start-date")
        end_date_str = self.option("end-date")
        save_path_str = self.option("save-path")
        if save_path_str:
            assert isinstance(save_path_str, str)
            save_path = Path(save_path_str)
        else:
            save_path = Path()
        start_datetime, end_datetime = parse_start_end_datetime(start_date_str, end_date_str)  # type: ignore
        thermostat = NestThermostat(AUTHENTICATOR, config=config)
        thermostat.download_historicals(start_datetime, end_datetime, save_path)


class PlotHistoricals(Command):
    """
    Retrieves and generates plots of your device statistics (temperature, humidity, target temperature).

    plot
        {--start-date : (str): YYYY-MM-DD data from which you want to get data.}
        {--end-date : (str): YYYY-MM-DD data up to which you want to get data.}
    """

    def handle(self):
        if self.io.output.is_debug():
            log.setLevel(logging.DEBUG)
        start_date_str = self.option("start-date")
        end_date_str = self.option("end-date")
        start_datetime, end_datetime = parse_start_end_datetime(start_date_str, end_date_str)  # type: ignore
        thermostat = NestThermostat(AUTHENTICATOR, config=config)
        thermostat.plot_historicals(start_datetime, end_datetime)


application = Application(name="py-nest-thermostat", version=__version__)
application.add(ListDevicesCommand())
application.add(DevicesStatsCommand())
application.add(SetTemperatureCommand())
application.add(PlotHistoricals())
application.add(DownloadStats())


if __name__ == "__main__":
    application.run()
