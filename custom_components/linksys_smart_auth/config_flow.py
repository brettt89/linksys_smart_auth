"""UI for configuring the integration."""

import base64
import aiohttp
import asyncio
import voluptuous as vol

from homeassistant import config_entries
from http import HTTPStatus
from .const import DOMAIN

class LinksysWifiConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Store connection configuration"""
    def __init__(self):
        self.errors = {}

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            # Validate user input
            valid = await asyncio.run(self.is_valid(user_input))
            if valid:
                # Store the data
                return self.async_create_entry(
                    title="Linksys Smart Wifi",
                    data={
                        "host": user_input["host"]
                    },
                )

            self.errors["base"] = "auth_error"
            
        # Specify items in the order they are to be displayed in the UI
        data_schema = {
            vol.Required("host"): str,
            vol.Required("username", default="admin"): str,
            vol.Required("password"): str,
        }

        return self.async_show_form(
            step_id="user", data_schema=vol.Schema(data_schema), errors=self.errors
        )
    
    async def is_valid(self, user_input):
        # create the login hash
        username = user_input["username"]
        password = user_input["password"]
        host = user_input["host"]
        credentials = f"{username}:{password}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        auth_string = f"Basic {encoded_credentials}"
        
        # check connection
        data = [
            {
                "request": {},
                "action": "http://linksys.com/jnap/core/GetDeviceInfo",
            }
        ]
        headers = {
            "X-JNAP-Action": "http://linksys.com/jnap/core/Transaction",
            "X-JNAP-Authorization": auth_string
        }
        try:
            async with aiohttp.ClientSession() as session:
                response = await session.post(
                    f"http://{host}/JNAP/",
                    timeout=10,
                    headers=headers,
                    data=data,
                )
        except aiohttp.ServerTimeoutError:
            self.errors["base"] = "timeout"
            return False
        except aiohttp.ClientConnectionError:
            self.errors["base"] = "connection_error"
            return False
        except aiohttp.ClientResponseError:
            self.errors["base"] = "http_error"
            return False
        except aiohttp.ClientError:
            self.errors["base"] = "unexpected"
            return False

        try:
            data = response.json()
            result = data["result"]
            responses = data["responses"]

            if result != "OK":
                self.errors["base"] = "api_error"
                error_type = responses[0]['result']
                if error_type == "_ErrorUnauthorized":
                    self.errors["base"] = "unauthorized"
                return False
            
            return True

        except (KeyError, IndexError):
            self.errors["base"] = "invalid_response"
            return False

        return True