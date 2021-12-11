import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import httpx
import questionary
from rich.console import Console

from py_nest_thermostat.config import PyNestConfig
from py_nest_thermostat.logger import log

console = Console()


class AuthRequestError(Exception):
    """Thrown when there was something wrong with a HTTP request."""


class Authenticator:
    TOKEN_URL = "https://www.googleapis.com/oauth2/v4/token"
    ACCESS_TOKEN_FILENAME = Path("~/.py-nest-thermostat/access_token.json").expanduser()

    def __init__(self, config: PyNestConfig):
        self.config = config
        # this will be populated when we do get token
        self.access_token_json: Optional[dict[str, Any]] = None
        self.access_token: str
        self.access_token_obtained_at: datetime
        self.token_response_json: Optional[dict[str, Any]] = None

    def get_token(self):
        # open the cached creds
        if os.path.isfile(self.ACCESS_TOKEN_FILENAME):
            with open(self.ACCESS_TOKEN_FILENAME) as f:
                try:
                    self.access_token_json = json.load(f)
                except json.JSONDecodeError as e:
                    log.error(
                        f"There was an issue reading access_token.json so we'll have to re-authenticate. Error: {e}"
                    )
                    self.access_token_json = None

        if self.access_token_json is not None:
            last_accessed_at = self.access_token_json.get(
                "access_token_obtained_at", "1901-01-01 00:00:00"
            )
            last_accessed_at = datetime.strptime(last_accessed_at, "%Y-%m-%d %H:%M:%S.%f")
            expires_delta = self.access_token_json.get("expires_in", 0)
            last_access_to_now_delta = datetime.now() - last_accessed_at

            if last_access_to_now_delta.seconds > int(expires_delta) - 10:
                log.debug("We need to refresh the token as it has expired.")
                self.authenticate()
            else:
                log.debug("No need to authenticate, auth code is still valid")
                self.access_token = self.access_token_json.get("access_token", "")
        else:
            log.info("Authenticating")
            self.authenticate()

    def authenticate(self):
        # if we already have a refresh token we don't need to go through auth again.
        if self.access_token_json:
            self.refresh_token = self.access_token_json.get("refresh_token", "")
            console.print("We have a access_token_json and we're gonna use it")
            if self.access_token_json.get("refresh_token", ""):
                console.print("We also have a refresh token in that json")
            refresh_token_params: dict[str, str] = {
                "client_id": self.config.nest_auth.client_id,
                "client_secret": self.config.nest_auth.client_secret,
                "refresh_token": self.refresh_token,
                "grant_type": "refresh_token",
            }
            try:
                token_response = httpx.post(self.TOKEN_URL, params=refresh_token_params)
                log.debug("Made refresh for token")
                if token_response.status_code == 200:
                    self.token_response_json = token_response.json()
                    if self.token_response_json:
                        self.access_token = self.token_response_json.get("access_token", "")
                else:
                    raise AuthRequestError(
                        f"{token_response.status_code=}, {token_response.json()=}"
                    )
            except httpx.RequestError as e:
                log.error(f"There was an issue while requesting tokens. {e}")
        else:
            # we first need to obtain an authorization_code via an interactive process
            authorization_code_url = (
                f"https://nestservices.google.com/partnerconnections/"
                f"{self.config.nest_auth.project_id}/auth?redirect_uri={self.config.nest_auth.redirect_uri}&"
                "access_type=offline&prompt=consent&client_id="
                f"{self.config.nest_auth.client_id}&response_type=code&scope="
                "https://www.googleapis.com/auth/sdm.service"
            )
            console.print(
                f"Open the following URL in your browser: {authorization_code_url} \n"
                "Once you have authorised, you will be redirected to your redirect_uri: "
                f"{self.config.nest_auth.redirect_uri}"
            )
            # TODO: Revisit this as it looks like passing the 4/ via the input changes the / and messes up the request.
            auth_code = questionary.password(
                message=(
                    "Paste the code contained between '?code=' and '&scope=' "
                    "from the URL of the page that was loaded after you authorised the app."
                )
            ).ask()
            if auth_code is not None:
                # we then use that code to make an auth and this will give us a token + a refresh one
                log.debug("we're going to try first time auth flow")
                token_request_params: dict[str, str] = {
                    "client_id": self.config.nest_auth.client_id,
                    "client_secret": self.config.nest_auth.client_secret,
                    "code": f"{auth_code}",
                    "grant_type": "authorization_code",
                    "redirect_uri": self.config.nest_auth.redirect_uri,
                }
                token_response = httpx.post(self.TOKEN_URL, params=token_request_params)
                if token_response.status_code == 200:
                    self.token_response_json = token_response.json()
                    self.access_token = self.token_response_json.get("access_token", "")

                    if self.access_token:
                        self.access_token_obtained_at = datetime.now()
                    self.refresh_token = self.token_response_json.get("refresh_token", "")

                else:
                    raise AuthRequestError(
                        f"Token request unsuccessful {token_response.status_code=}, {token_response.text=}"
                    )
            else:
                raise AuthRequestError("You do not seem to have provided any authorization_code")

        if self.token_response_json and self.refresh_token:
            with open(self.ACCESS_TOKEN_FILENAME, "w") as f:
                self.token_response_json.update(
                    {
                        "refresh_token": self.refresh_token,
                        "access_token_obtained_at": self.access_token_obtained_at,
                    }
                )
                json.dump(self.token_response_json, f, default=str)
        else:
            raise AttributeError(
                "I must have a refresh token otherwise I'm not going to save the token"
            )
