import json
import re
import uuid
from datetime import datetime
from typing import Any, Optional, Sequence

import httpx
from pydantic import BaseModel
from rich.align import Align
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel

from py_nest_thermostat.auth import Authenticator
from py_nest_thermostat.config import PyNestConfig
from py_nest_thermostat.connectors.base import BaseDbConnector
from py_nest_thermostat.connectors.cockroach_db import cockroach_connector
from py_nest_thermostat.connectors.postgres import postgres_connector
from py_nest_thermostat.logger import log
from py_nest_thermostat.models import DeviceStats

console = Console()

TEAL = "#6CA6DE"
RED = "#FF6978"
GREEN = "#80EBA6"
YELLOW = "#D4B57C"
PURPLE = "#B179CC"


class DatabaseFactory:
    def __init__(self, config: PyNestConfig):
        self.db_type = config.database.type

    def get_connector(self) -> BaseDbConnector:
        if self.db_type == "postgres":
            return postgres_connector
        elif self.db_type == "cockroach":
            return cockroach_connector
        else:
            raise NotImplementedError(f"{self.db_type} is not a supported database type")


class ParentRelation(BaseModel):
    parent: str
    displayName: str


# TODO: Is there a way I could do a model also for the thermostat traits?
# I should but the traits name have dots so we'll have to find a way to set up aliases or something like that.
# this doc page contains a JSON (https://developers.google.com/nest/device-access/api/thermostat#json)
# which I could probably make pydantic parse and build a model for.
class Device(BaseModel):
    name: str
    type: str
    assignee: str
    traits: dict[str, Any]
    parentRelations: list[ParentRelation]


class DeviceList(BaseModel):
    devices: Sequence[Device]


class ThermostatStats(BaseModel):
    device_name: str
    status: str
    humidity: float
    temperature: float
    temperature_unit: str
    mode: str
    target_temperature: str
    eco_mode: str


class NestThermostat:
    # TODO: remove BASE_NEST_API_URL and update downstream query urls
    BASE_NEST_API_URL: str = "https://smartdevicemanagement.googleapis.com/v1/enterprises/"
    SUPPORTED_DEVICE_TYPES: set[str] = {"sdm.devices.types.THERMOSTAT"}
    SDM_API: str = "https://smartdevicemanagement.googleapis.com/v1"

    def __init__(self, authenticator: Authenticator, config: PyNestConfig):
        self.authenticator = authenticator
        self.config = config

        # made available by methods
        self.device_list: Optional[DeviceList]
        self.device_type: Optional[str]
        self.thermostat_id: Optional[str]
        self.thermostat_display_name: Optional[str]

        self.authenticator.get_token()
        assert (
            self.authenticator.access_token_json
        ), "The access token json was not correctly accessed"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.authenticator.access_token_json.access_token}",
        }

    def get_devices(self, print_controlled_device_name: bool = True):
        device_url = f"{self.BASE_NEST_API_URL}{self.config.nest_auth.project_id}/devices"

        devices_response = httpx.get(device_url, headers=self.headers)

        if devices_response.status_code == 200:
            self.device_list = DeviceList(**devices_response.json())

            # TODO: we need to allow users to choose their device as there may be more than one
            self.device_type = self.device_list.devices[0].type
            if {self.device_type}.issubset(self.SUPPORTED_DEVICE_TYPES):
                device_id_match = re.search(r"(?<=\/devices\/).*", self.device_list.devices[0].name)
                if device_id_match:
                    self.thermostat_id = device_id_match[0]
                self.thermostat_display_name = (
                    self.device_list.devices[0].parentRelations[0].displayName
                )
                if print_controlled_device_name:
                    console.print(
                        f"You're currently controlling the [{YELLOW}]{self.thermostat_display_name}[/{YELLOW}] "
                        "thermostat."
                    )
            else:
                log.error(
                    f"Unsupported Device Type: {self.device_type}. Supported types: {self.SUPPORTED_DEVICE_TYPES}"
                )
        else:
            raise httpx.RequestError(
                f"Request failed: {devices_response.status_code=}, {devices_response.text=}"
            )

    def get_device_stats(
        self,
        no_print: bool = False,
        save_stats: bool = False,
        print_controlled_device_name: bool = True,
    ):
        # TODO: think about replacing the key access by gets when there is a chance that the attribute it not present.
        self.get_devices(print_controlled_device_name)
        assert self.device_list, "device_list cannot be None"
        self.active_device: Optional[Device] = self.device_list.devices[0]
        assert self.active_device, "Could not find any devices"

        # we need to get the unit because it will help us use approproate scale specific keys
        temperature_unit = self.active_device.traits.get("sdm.devices.traits.Settings", {}).get(
            "temperatureScale", "no scale retrieved"
        )
        temperature_unit = temperature_unit.title()
        is_in_eco_mode = self.active_device.traits.get("sdm.devices.traits.ThermostatEco", {}).get(
            "mode", False
        )

        # perform some eco mode related remappings
        if is_in_eco_mode == "MANUAL_ECO":
            target_temperature = self.active_device.traits.get(
                "sdm.devices.traits.ThermostatEco", {}
            ).get(f"heat{temperature_unit}", 0)
        else:
            target_temperature = self.active_device.traits.get(
                "sdm.devices.traits.ThermostatTemperatureSetpoint", {}
            ).get(f"heat{temperature_unit}", 0)

        # build device stats object
        self.device_stats = ThermostatStats(
            device_id=self.active_device.name,
            device_name=self.active_device.parentRelations[0].displayName,
            status=self.active_device.traits.get("sdm.devices.traits.Connectivity", {}).get(
                "status"
            ),
            humidity=round(
                float(
                    self.active_device.traits.get("sdm.devices.traits.Humidity", {}).get(
                        "ambientHumidityPercent", 0
                    ),
                ),
            ),
            temperature=round(
                self.active_device.traits.get("sdm.devices.traits.Temperature", {}).get(
                    f"ambientTemperature{temperature_unit}", 0
                ),
                1,
            ),
            temperature_unit=temperature_unit,
            mode=self.active_device.traits.get("sdm.devices.traits.ThermostatMode", {}).get(
                "mode", "NA"
            ),
            target_temperature=round(target_temperature, 1),
            eco_mode=self.active_device.traits.get("sdm.devices.traits.ThermostatEco", {}).get(
                "mode", "no eco mode info found"
            ),
        )
        if not no_print:
            self.print_device_stats()
        if save_stats:
            self.save_record_to_db()

    def save_record_to_db(self):
        id = uuid.uuid1()
        if isinstance(self.device_stats, ThermostatStats):
            device_stats = DeviceStats(
                id=id,
                name=self.thermostat_display_name,
                recorded_at=datetime.utcnow(),
                humidity=self.device_stats.humidity,
                temperature=self.device_stats.temperature,
                mode=self.device_stats.mode,
                target_temperature=self.device_stats.target_temperature,
            )
            database_connector = DatabaseFactory(self.config).get_connector()
            database_connector.connect()
            database_connector.create_models()
            with database_connector.session_manager() as session:  # type: ignore
                log.info(f"Saving thremostat stats to database: {self.config.database.type}.")
                session.add(device_stats)
                session.commit()
        else:
            raise AttributeError(
                "device_stats is None or not a valid object of type ThermostatStats. Skipping database update"
            )

    def print_device_stats(self):
        temp_colour = (
            TEAL
            if float(self.device_stats.temperature) < float(self.device_stats.target_temperature)
            else TEAL
        )
        target_temp_colour = (
            RED
            if float(self.device_stats.target_temperature) > float(self.device_stats.temperature)
            else TEAL
        )
        mode_colour = RED if self.device_stats.mode == "HEAT" else TEAL
        eco_mode_colour = GREEN if self.device_stats.eco_mode != "OFF" else YELLOW
        temp_symbol = "°C" if self.device_stats.temperature_unit.lower() == "celsius" else "°F"
        panels = [
            Panel(
                Align.center(
                    f"[bold][{temp_colour}]{self.device_stats.temperature}[/{temp_colour}][/bold] {temp_symbol}"
                ),
                title=f"[{PURPLE}]Temperature",
            ),
            Panel(
                Align.center(f"[bold][{TEAL}]{self.device_stats.humidity}[/{TEAL}][/bold] %"),
                title=f"[{PURPLE}]Humidity",
            ),
            Panel(
                Align.center(
                    f"[bold][{mode_colour}]{self.device_stats.mode}[/{mode_colour}][/bold]"
                ),
                title=f"[{PURPLE}]Mode",
            ),
            Panel(
                Align.center(
                    f"[bold][{eco_mode_colour}]{self.device_stats.eco_mode}[/{eco_mode_colour}][/bold]"
                ),
                title=f"[{PURPLE}]Eco Mode",
            ),
            Panel(
                Align.center(
                    f"[bold][{target_temp_colour}]{float(self.device_stats.target_temperature)}[/{target_temp_colour}][/bold] {temp_symbol}"  # noqa: E501
                ),
                title=f"[{PURPLE}]Target Temperature",
            ),
        ]
        console.print(Columns(panels))

    def set_target_temperature(self, temperature: float):
        self.get_devices()

        command_url = f"{self.SDM_API}/enterprises/{self.config.nest_auth.project_id}/devices/{self.thermostat_id}:executeCommand"  # noqa: E501

        temperature = float(temperature)
        request_body = {
            "command": "sdm.devices.commands.ThermostatTemperatureSetpoint.SetHeat",
            # TODO/FIXME: would `heatCelsius` field work if the devise is in F?
            "params": {"heatCelsius": temperature},
        }
        response = httpx.post(
            command_url,
            headers=self.headers,
            data=json.dumps(request_body),  # type: ignore
        )

        if response.status_code == 200:
            console.print(
                f"{self.thermostat_display_name} successfully set to [bold][{GREEN}]{temperature}[/{GREEN}][/bold]"
            )
        else:
            httpx.RequestError(f"Request failed: {response.status_code=}, {response.text=}")

        # display info pannel after success
        self.get_device_stats(no_print=False, print_controlled_device_name=False)
