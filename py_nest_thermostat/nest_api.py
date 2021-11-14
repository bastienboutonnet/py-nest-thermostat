import json
import re
from typing import Any, Optional, Sequence

import httpx
from pydantic import BaseModel
from rich.align import Align
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel

from py_nest_thermostat.auth import Authenticator
from py_nest_thermostat.logger import log

console = Console()


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


class NestThermostat:
    # TODO: remove BASE_NEST_API_URL and update downstream query urls
    BASE_NEST_API_URL: str = "https://smartdevicemanagement.googleapis.com/v1/enterprises/"
    SUPPORTED_DEVICE_TYPES: set[str] = {"sdm.devices.types.THERMOSTAT"}
    SDM_API: str = "https://smartdevicemanagement.googleapis.com/v1"

    def __init__(self, authenticator: Authenticator):
        self.authenticator = authenticator

        # made available by methods
        self.device_list: Optional[DeviceList]
        self.device_type: Optional[str]
        self.thermostat_id: Optional[str]
        self.thermostat_display_name: Optional[str]

        self.authenticator.get_token()
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.authenticator.access_token}",
        }

    def get_devices(self):
        device_url = f"{self.BASE_NEST_API_URL}{self.authenticator.project_id}/devices"

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
                console.print(
                    f"You're currently controlling the '{self.thermostat_display_name}' thermostat."
                )
            else:
                log.error(
                    f"Unsupported Device Type: {self.device_type}. Supported types: {self.SUPPORTED_DEVICE_TYPES}"
                )
        else:
            raise httpx.RequestError(
                f"Request failed: {devices_response.status_code=}, {devices_response.text=}"
            )

    def get_device_stats(self, print: bool = True):
        # TODO: think about replacing the key access by gets when there is a chance that the attribute it not present.
        self.get_devices()
        assert self.device_list, "device_list cannot be None"
        self.active_device: Optional[Device] = self.device_list.devices[0]

        # we need to get the unit because it will help us use approproate scale specific keys
        temperature_unit = self.active_device.traits["sdm.devices.traits.Settings"][
            "temperatureScale"
        ]
        temperature_unit = temperature_unit.title()
        self.device_stats = ThermostatStats(
            device_id=self.active_device.name,
            device_name=self.active_device.parentRelations[0].displayName,
            status=self.active_device.traits["sdm.devices.traits.Connectivity"]["status"],
            humidity=round(
                float(
                    self.active_device.traits["sdm.devices.traits.Humidity"][
                        "ambientHumidityPercent"
                    ],
                ),
            ),
            temperature=round(
                self.active_device.traits["sdm.devices.traits.Temperature"][
                    f"ambientTemperature{temperature_unit}"
                ],
                1,
            ),
            temperature_unit=temperature_unit,
            mode=self.active_device.traits["sdm.devices.traits.ThermostatMode"]["mode"],
            target_temperature=round(
                self.active_device.traits["sdm.devices.traits.ThermostatTemperatureSetpoint"][
                    f"heat{temperature_unit}"
                ],
                1,
            ),
        )
        if print:
            teal = "#A8F9FF"
            red = "#FF6978"
            temp_colour = (
                teal
                if float(self.device_stats.temperature)
                < float(self.device_stats.target_temperature)
                else teal
            )
            target_temp_colour = (
                red
                if float(self.device_stats.target_temperature)
                > float(self.device_stats.temperature)
                else teal
            )
            mode_colour = red if self.device_stats.mode == "HEAT" else teal
            temp_symbol = "°C" if self.device_stats.temperature_unit.lower() == "celsius" else "°F"
            panels = [
                Panel(
                    Align.center(
                        f"[bold][{temp_colour}]{self.device_stats.temperature}[/{temp_colour}][/bold] {temp_symbol}"
                    ),
                    title="Temperature",
                ),
                Panel(
                    Align.center(f"[bold][{teal}]{self.device_stats.humidity}[/{teal}][/bold] %"),
                    title="Humidity",
                ),
                Panel(
                    Align.center(
                        f"[bold][{mode_colour}]{self.device_stats.mode}[/{mode_colour}][/bold]"
                    ),
                    title="Mode",
                ),
                Panel(
                    Align.center(
                        f"[bold][{target_temp_colour}]{float(self.device_stats.target_temperature)}[/{target_temp_colour}][/bold] {temp_symbol}"  # noqa: E501
                    ),
                    title="Target Temperature",
                ),
            ]
            console.print(Columns(panels))

    def set_target_temperature(self, temperature: float):
        self.get_device_stats(print=False)

        command_url = f"{self.SDM_API}/enterprises/{self.authenticator.project_id}/devices/{self.thermostat_id}:executeCommand"  # noqa: E501

        temperature = float(temperature)
        request_body = {
            "command": "sdm.devices.commands.ThermostatTemperatureSetpoint.SetHeat",
            "params": {"heatCelsius": temperature},
        }
        response = httpx.post(
            command_url,
            headers=self.headers,
            data=json.dumps(request_body),  # type: ignore
        )

        if response.status_code == 200:
            console.print(f"{self.thermostat_display_name} successfully set to '{temperature}'")
        else:
            httpx.RequestError(f"Request failed: {response.status_code=}, {response.text=}")
