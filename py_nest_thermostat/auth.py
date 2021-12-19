import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import httpx
import questionary
from pydantic import BaseModel
from rich.console import Console

from py_nest_thermostat.config import PyNestConfig
from py_nest_thermostat.logger import log

console = Console()


class AccessToken(BaseModel):
    access_token: str
    refresh_token: str
    access_token_obtained_at: datetime = datetime.strptime(
        "1901-01-01 00:00:00.00", "%Y-%m-%d %H:%M:%S.%f"
    )
    expires_in: int


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str]
    expires_in: int


class AuthRequestError(Exception):
    """Thrown when there was something wrong with a HTTP request."""


class Authenticator:
    TOKEN_URL = "https://www.googleapis.com/oauth2/v4/token"
    ACCESS_TOKEN_FILENAME = Path("~/.py-nest-thermostat/access_token.json").expanduser()

    def __init__(self, config: PyNestConfig):
        self.config = config
        self.access_token_json: Optional[AccessToken] = None

        self.access_token_obtained_at: datetime = datetime.strptime(
            "1901-01-01 00:00:00.00", "%Y-%m-%d %H:%M:%S.%f"
        )
        self.token_response_json: Optional[dict[str, Any]] = None

    def get_token(self):
        # open the cached creds
        if os.path.isfile(self.ACCESS_TOKEN_FILENAME):
            with open(self.ACCESS_TOKEN_FILENAME) as f:
                try:
                    token_file_dict = json.load(f)
                    self.access_token_json = AccessToken(**token_file_dict)
                except json.JSONDecodeError as e:
                    raise AuthRequestError(
                        f"There was an issue reading access_token.json so we'll have to re-authenticate. Error: {e}"
                    )

        if self.access_token_json:
            last_accessed_at = self.access_token_json.access_token_obtained_at
            assert last_accessed_at, "last_accessed_at cannot be None"
            # last_accessed_at = datetime.strptime(last_accessed_at, "%Y-%m-%d %H:%M:%S.%f")
            expires_delta = self.access_token_json.expires_in
            last_access_to_now_delta = datetime.utcnow() - last_accessed_at

            if last_access_to_now_delta.seconds > int(expires_delta) - 10:
                log.debug("We need to refresh the token as it has expired.")
                self.authenticate()
            else:
                # TODO: Check how we can control the logger level via cleo
                log.debug("No need to authenticate, auth code is still valid")
                # self.access_token = self.access_token_json.get("access_token", "")
        else:
            log.info("Authenticating")
            self.authenticate()

    def verify_and_parse_token_response(self, token_response: httpx.Response):
        if token_response.status_code == 200:
            self.token_response_json = token_response.json()
            if self.token_response_json:
                self.token_response_model = TokenResponse(**self.token_response_json)
                if self.token_response_model.refresh_token:
                    self.refresh_token = self.token_response_model.refresh_token
                self.access_token_json = AccessToken(
                    access_token=self.token_response_model.access_token,
                    refresh_token=self.refresh_token,
                    access_token_obtained_at=datetime.utcnow(),
                    expires_in=self.token_response_model.expires_in,
                )
            else:
                raise AuthRequestError(f"{token_response.status_code=}, {token_response.json()=}")

    def authenticate(self):
        # if we already have a refresh token we don't need to go through auth again.
        if self.access_token_json:
            log.debug("We have found an access token file")
            if self.access_token_json.refresh_token:
                self.refresh_token = self.access_token_json.refresh_token
                log.debug("A refresh token was found so we'll auth by requesting a new token")
            # compose the request params
            refresh_token_params: dict[str, str] = {
                "client_id": self.config.nest_auth.client_id,
                "client_secret": self.config.nest_auth.client_secret,
                "refresh_token": self.refresh_token,
                "grant_type": "refresh_token",
            }
            try:
                token_response = httpx.post(self.TOKEN_URL, params=refresh_token_params)
                log.debug("Token refresh request issued")
                self.verify_and_parse_token_response(token_response)
            except httpx.RequestError as e:
                # TODO: shouldn't we be raising here?
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
                    "from the URL of the page that was loaded after you authorised the app.\n"
                )
            ).ask()
            if auth_code:
                # we then use that code to make an auth and this will give us a token + a refresh one
                log.debug("we're going to try first time auth flow")
                token_request_params: dict[str, str] = {
                    "client_id": self.config.nest_auth.client_id,
                    "client_secret": self.config.nest_auth.client_secret,
                    "code": f"{auth_code}",
                    "grant_type": "authorization_code",
                    "redirect_uri": self.config.nest_auth.redirect_uri,
                }
                try:
                    token_response = httpx.post(self.TOKEN_URL, params=token_request_params)
                    self.verify_and_parse_token_response(token_response)
                except httpx.RequestError as e:
                    # TODO: shouldn't we be raising here?
                    log.error(f"There was an issue while requesting tokens. {e}")
            else:
                raise AuthRequestError("You do not seem to have provided any authorization_code")

        if self.token_response_json and self.refresh_token:
            with open(self.ACCESS_TOKEN_FILENAME, "w") as f:
                if self.access_token_json:
                    json.dump(self.access_token_json.dict(), f, default=str)
        else:
            raise AttributeError(
                "The token request does not seem to have returned a refresh token. "
                "A refresh token is necessary to persist your credentials"
                "Try to authenticate again and see if the problem persists."
            )
