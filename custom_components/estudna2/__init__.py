"""eSTUDNA2 component for Home Assistant (API v2)."""

from functools import partial
import logging
import requests

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .estudna import ThingsBoard
from .sensor import EStudnaSensor

__all__ = ["EStudnaSensor"]  # pro export a odstranění F401

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up eSTUDNA2 from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    tb = ThingsBoard()

    try:
        # Login via API v2
        await hass.loop.run_in_executor(
            None,
            partial(tb.login, entry.data.get("username"), entry.data.get("password"))
        )
    except (requests.exceptions.RequestException, ValueError) as e:
        _LOGGER.error("Could not login to eSTUDNA2: %s", e)
        return False

    # Storing ThingsBoard instance for this entry_id
    hass.data[DOMAIN][entry.entry_id] = tb

    # Handing over to platforms (sensors)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
