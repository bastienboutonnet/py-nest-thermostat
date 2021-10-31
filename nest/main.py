import json
import os
from datetime import datetime
from typing import Any, Dict, Optional

import httpx
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "credentials.env"))


class AuthRequestError(Exception):
    """Thrown when there was something wrong with a HTTP request."""


class Authenticator:
    TOKEN_URL = "https://www.googleapis.com/oauth2/v4/token"
    ACCESS_TOKEN_FILENAME = "access_token.json"

    def __init__(self):
        self.client_id: str = os.getenv("client_id", "")
        self.client_secret: str = os.getenv("client_secret", "")
        self.redirect_uri: str = os.getenv("redirect_uri", "")
        self.authorization_code: str = os.getenv("authorization_code", "")
        self.refresh_token: Optional[str] = os.getenv("refresh_token")

        # this will be populated when we do get token
        self.access_token_json: Optional[Dict[str, Any]] = None
        self.access_token: str
        self.access_token_obtained_at: datetime
        self.token_response_json: Optional[Dict[str, Any]] = None

    def get_token(self):
        # open the cached creds
        if os.path.isfile(self.ACCESS_TOKEN_FILENAME):
            with open(self.ACCESS_TOKEN_FILENAME, "r") as f:
                self.access_token_json = json.load(f)

        if self.access_token_json is not None:
            print("we have an access token")
            last_accessed_at = self.access_token_json.get(
                "access_token_obtained_at", "1901-01-01 00:00:00"
            )
            last_accessed_at = datetime.strptime(last_accessed_at, "%y-%m-%d %H:%M:%S")
            expires_delta = self.access_token_json.get("expires_in", 0)
            last_access_to_now_delta = datetime.now() - last_accessed_at

            if last_access_to_now_delta.seconds > int(expires_delta) - 10:
                self.authenticate()
                # return self.access_token
            else:
                self.access_token = self.access_token_json.get("access_token", "")
                # return self.access_token
        else:
            self.authenticate()

    def authenticate(self):
        # if we already have a refresh token we don't need to go through auth again.
        if self.refresh_token:
            refresh_token_params: Dict[str, str] = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": self.refresh_token,
            }
            try:
                token_response = httpx.post(self.TOKEN_URL, params=refresh_token_params)
                if token_response.status_code == 200:
                    self.token_response_json = token_response.json()
                    self.access_token = self.token_response_json.get("access_token", "")
                else:
                    raise AuthRequestError(
                        f"{token_response.status_code=}, {token_response.json()=}"
                    )
            except httpx.RequestError as e:
                print(f"There was an issue while requesting {e.request.url!r}.")
        else:
            # when we do not have a refresh token
            print("we're going to try first time auth flow")
            token_request_params: Dict[str, str] = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "authorization_code": self.authorization_code,
                "grant_type": "authorization_code",
                "redirect_uri": self.redirect_uri,
            }
            token_response = httpx.post(self.TOKEN_URL, params=token_request_params)
            if token_response.status_code == 200:
                self.token_response_json = token_response.json()
                self.access_token = self.token_response_json.get("access_token", "")

                if self.access_token:
                    self.access_token_obtained_at = datetime.now()
                self.refresh_token = self.token_response_json.get("refresh_token", "")

                if self.refresh_token is not None:
                    with open("credentials.env", "a") as f:
                        # TODO: this is a bit dirty may we should rewrite so that
                        # we check wether there is already an entry for "refresh_token" in the file
                        # and in that case we probably want to nuke it first.
                        f.write(f"refresh_token={self.refresh_token}")
            else:
                raise AuthRequestError("meh")

                # cache the access code along with a timestamp of when we got it
        if self.token_response_json:
            with open("access_token.json", "w") as f:
                self.token_response_json.update(
                    {"access_token_obtained_at": self.access_token_obtained_at}
                )
                json.dump(self.token_response_json, f, default=str)
