from typing import Any, Optional

import httpx
import questionary
from pydantic import BaseModel

from py_nest_thermostat.auth import Authenticator


class ParentRelation(BaseModel):
    parent: str
    displayName: str


# TODO: Is there a way I could do a model also for the thermostat traits?
# I should but the traits name have dots so we'll have to find a way to set up aliases or something like that.
class Device(BaseModel):
    name: str
    type: str
    assignee: str
    traits: dict[str, Any]
    parentRelations: list[ParentRelation]


class DeviceList(BaseModel):
    devices: list[Device]


class NestThermostat:
    BASE_NEST_API_URL: str = "https://smartdevicemanagement.googleapis.com/v1/enterprises/"
    SUPPORTED_DEVICE_TYPES: set[str] = {"sdm.devices.types.THERMOSTAT"}

    def __init__(self, authenticator: Authenticator):
        self.authenticator = authenticator

        # made available by methods
        self.devices: dict[str, Any]
        self.device_type: str
        self.thermostat_id: str
        self.thermostat_display_name: str

    def get_devices(self):
        self.authenticator.get_token()
        device_url = f"{self.BASE_NEST_API_URL}{self.authenticator.project_id}/devices"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.authenticator.access_token}",
        }

        devices_response = httpx.get(device_url, headers=headers)

        if devices_response.status_code == 200:
            devices = devices_response.json()
            print(devices)

            # if there are several devices in the home we need to ask users to choose
            if len(devices.get("devices")) > 1:
                available_devices = devices.get("devices")
                chosen_device = questionary.select(
                    "You seem to have seveal devices in your home. Which is the Nest thermostat you want to control?",
                    choices=available_devices,
                ).ask()
                print(chosen_device)
            else:
                self.device_type = devices.get("devices")[0]["type"]
                if {self.device_type}.issubset(self.SUPPORTED_DEVICE_TYPES):
                    self.thermostat_id = devices.get("devices")[0].get("name")
                    self.thermostat_display_name = devices.get("devices")[0]["parentRelations"][0][
                        "displayName"
                    ]
                    # .get("name")
                    print(f"{self.thermostat_display_name=}")
                else:
                    print(
                        f"Unsupported Device Type: {self.device_type}. Supported types: {self.SUPPORTED_DEVICE_TYPES}"
                    )
        else:
            raise httpx.RequestError(
                f"Request failed: {devices_response.status_code=}, {devices_response.text=}"
            )

    def get_device_stats(self, device_name: Optional[str] = None):
        self.get_devices()
