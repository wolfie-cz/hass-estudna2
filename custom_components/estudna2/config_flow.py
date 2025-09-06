import voluptuous as vol
import logging

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from .const import DOMAIN
from .estudna import ThingsBoard

_LOGGER = logging.getLogger(__name__)

class EStudnaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow pro eSTUDNA."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def async_step_user(self, user_input=None) -> FlowResult:
        """User enters the credentials."""
        errors = {}

        if user_input is not None:
            username = user_input.get("username")
            password = user_input.get("password")

            thingsboard = ThingsBoard()
            try:
                # Login to ThingsBoard API
                await self.hass.async_add_executor_job(thingsboard.login, username, password)
                # If login is OK, we store the data
                return self.async_create_entry(
                    title=username,
                    data={
                        "username": username,
                        "password": password
                    }
                )
            except Exception as e:
                _LOGGER.error("We could not login to eSTUDNA2: %s", e)
                errors["base"] = "cannot_connect"

        # Shows the form for entering the creds
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("username"): str,
                    vol.Required("password"): str
                }
            ),
            errors=errors
        )
