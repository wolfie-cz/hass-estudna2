import logging
import requests
from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.const import UnitOfLength
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .const import DOMAIN
from .estudna import ThingsBoard
import json
from datetime import datetime

_LOGGER = logging.getLogger(__name__)

class EStudnaSensor(SensorEntity):
    """eSTUDNA2 Water level"""

    def __init__(self, hass: HomeAssistant, thingsboard: ThingsBoard, device: dict):
        self._hass = hass
        self._thingsboard = thingsboard
        self._device = device
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._state = None
        self._attributes = {}

    @property
    def unique_id(self) -> str:
        return self._device["id"]

    @property
    def name(self) -> str:
        return self._device.get("name", f"Device {self.unique_id}")

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._device["id"])},
            model=self._device.get("type"),
            manufacturer="SEA Praha",
            name=self._device.get("name"),
        )

    @property
    def state(self):
        return self._state

    @property
    def extra_state_attributes(self):
        """Returns attributes of the sensor for HA."""
        return self._attributes

    @property
    def available(self):
        return self._state is not None

    @property
    def unit_of_measurement(self) -> str:
        return UnitOfLength.METERS

    async def async_update(self) -> None:
        """Update of status of sensors and attributes."""
        try:
            values = await self._hass.async_add_executor_job(
                self._thingsboard.get_device_values, self.unique_id
            )

            self._state = None
            self._attributes = {}

            if "ain1" in values and isinstance(values["ain1"], list) and values["ain1"]:
                entry = values["ain1"][0]
                raw_val = entry.get("value")
                ts = entry.get("ts")

                try:
                    val_json = json.loads(raw_val)
                    self._state = float(val_json.get("str"))
                    self._attributes = {
                        "zone": val_json.get("zone"),
                        "units": val_json.get("units"),
                        "last_updated": datetime.fromtimestamp(ts / 1000).isoformat()
                    }
                except (ValueError, TypeError, json.JSONDecodeError) as e:
                    _LOGGER.error(
                        "Error while parsing value for device %s: %s", self.unique_id, e
                    )
                    self._state = None
                    self._attributes = {}

        except requests.exceptions.RequestException as e:
            _LOGGER.error(
                "Error retrieving water level for device %s: %s", self.unique_id, e
            )
            self._state = None
            self._attributes = {}

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    """Set up EStudna sensors from config entry."""
    username = entry.data.get("username")
    password = entry.data.get("password")

    thingsboard = ThingsBoard()
    try:
        # Logging in and getting list of devices
        await hass.async_add_executor_job(thingsboard.login, username, password)
        devices = await hass.async_add_executor_job(thingsboard.get_devices)
    except (requests.exceptions.RequestException, ValueError) as e:
        _LOGGER.error("Cannot connect to eSTUDNA2: %s", e)
        devices = []

    # Creating sensors for all devices
    sensors = [EStudnaSensor(hass, thingsboard, device) for device in devices]
    async_add_entities(sensors)
