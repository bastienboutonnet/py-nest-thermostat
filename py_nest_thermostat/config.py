from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

CONFIG_FILE = Path("~/.py-nest-thermostat/config.yaml").expanduser()


def open_yaml(path: Path) -> dict[str, Any]:
    if path.is_file():
        with open(path) as stream:
            congif_yaml = yaml.safe_load(stream)
            return congif_yaml
    else:
        raise FileNotFoundError(f"No config.yaml found at: {path}")


class NestAuth(BaseModel):
    client_id: str
    client_secret: str
    redirect_uri: str
    project_id: str


class DatabaseAuth(BaseModel):
    type: str
    credentials: dict[str, str]


class PyNestConfig(BaseModel):
    nest_auth: NestAuth
    database: DatabaseAuth


config = PyNestConfig(**open_yaml(CONFIG_FILE))
