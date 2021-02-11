"""Support for the for Danfoss Air HRV binary sensors."""
import logging
from homeassistant.helpers.dispatcher import *
from homeassistant.components.binary_sensor import BinarySensorEntity 
from homeassistant.const import (
    STATE_ON,
    STATE_OFF,
)

from . import DOMAIN, SIGNAL_IZZIFAST_UPDATE_RECEIVED, IzzifastBridge
from .izzi.const import *

from . import *
from .izzi import *

_LOGGER = logging.getLogger(__name__)

def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the available Danfoss Air sensors etc."""
    izzibridge = hass.data[DOMAIN]

    sensors = [
        ["iZZi Bypass", IZZY_SENSOR_BYPASS_STATE_ID, "opening", IZZI_STATUS_MSG_BYPASS_STATE_OPEN],
        ["iZZi Cover", IZZY_SENSOR_COVER_STATE_ID, "opening", IZZY_STATUS_MSG_COVER_STATE_OPEN],
        ["iZZi Defrost", IZZY_SENSOR_DEFROST_STATE_ID, "problem", IZZY_STATUS_MSG_DEFROST_STATE_ACTIVE],
    ]

    dev = []

    for sensor in sensors:
        dev.append(IzzifastBinarySensor(izzibridge, sensor[0], sensor[1], sensor[2], sensor[3]))

    add_entities(dev, True)


class IzzifastBinarySensor(BinarySensorEntity):
    """Representation of a Danfoss Air binary sensor."""

    def __init__(self, izzibridge, name, sensor_type, device_class, active_state):
        """Initialize the Danfoss Air binary sensor."""
        self._izzibridge = izzibridge
        self._name = name
        self._state = None
        self._sensor_type = sensor_type
        self._device_class = device_class
        self._active_state = active_state

    async def async_added_to_hass(self):
        """Register for sensor updates."""
        _LOGGER.debug(
            "Registering for binary sensor %s", self._sensor_type
        )
        self._remove_signal_update = async_dispatcher_connect(
            self.hass,
            SIGNAL_IZZIFAST_UPDATE_RECEIVED.format(self._sensor_type),
            self._handle_update,
        )
        self._izzibridge.force_update(self._sensor_type)
        
    async def async_will_remove_from_hass(self) -> None:
        """Call when entity will be removed from hass."""
        self._remove_signal_update()
    
    def _handle_update(self, value):
        """Handle update callbacks."""
        _LOGGER.debug(
            "Handle update for sensor %s : %s",
            self._name,
            value,
        )
        self._izzibridge.data[self._sensor_type] = value
        self.schedule_update_ha_state()

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def is_on(self):
        """Return the state of the sensor."""
        try:
            return self._izzibridge.data[self._sensor_type] == self._active_state
        except KeyError:
            return False

    @property
    def device_class(self):
        """Type of device class."""
        return self._device_class

    @property
    def should_poll(self) -> bool:
        """Do not poll."""
        return False

    @property
    def unique_id(self):
        """Return a unique_id for this entity."""
        return f"{self._izzibridge.unique_id}_binary_sensor_{self._sensor_type}"
