"""Platform to control a IZZI ERV 300 ventilation unit."""
import logging
from typing import Optional

from homeassistant.components.fan import (
    SUPPORT_SET_SPEED,
    FanEntity,
)

from homeassistant.helpers.dispatcher import *

from . import DOMAIN, SIGNAL_IZZIFAST_UPDATE_RECEIVED, IzzifastBridge
from .izzi.const import *
from . import *
from .izzi import *

_LOGGER = logging.getLogger(__name__)

def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Izzi fan platform."""
    izzibridge = hass.data[DOMAIN]

    add_entities([IzzifastFan("iZZi Fan", izzibridge)], True)


class IzzifastFan(FanEntity):
    """Representation of the Izzi fan platform."""

    def __init__(self, name, izzibridge: IzzifastBridge) -> None:
        """Initialize the Izzi fan."""
        self._izzibridge = izzibridge
        self._name = name

    async def async_added_to_hass(self):
        """Register for sensor updates."""
        _LOGGER.debug("Registering for fan speed")
        self._remove_signal_update = async_dispatcher_connect(
            self.hass,
            SIGNAL_IZZIFAST_UPDATE_RECEIVED.format(IZZY_SENSOR_FAN_MODE_ID),
            self._handle_update,
        )
        self._izzibridge.force_update(IZZY_SENSOR_FAN_MODE_ID)
        
    async def async_will_remove_from_hass(self) -> None:
        """Call when entity will be removed from hass."""
        self._remove_signal_update()

    def _handle_update(self, value):
        """Handle update callbacks."""
        _LOGGER.debug(
            "Handle update for fan speed (%d): %s", IZZY_SENSOR_FAN_MODE_ID, value
        )
        self._izzibridge.data[IZZY_SENSOR_FAN_MODE_ID] = value
        self.schedule_update_ha_state()

    @property
    def should_poll(self) -> bool:
        """Do not poll."""
        return False

    @property
    def unique_id(self):
        """Return a unique_id for this entity."""
        return f"{self._izzibridge.unique_id}_fan"

    @property
    def name(self):
        """Return the name of the fan."""
        return self._name

    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        return "mdi:air-conditioner"

    @property
    def supported_features(self) -> int:
        """Flag supported features."""
        return SUPPORT_SET_SPEED

    @property
    def is_on(self) -> bool:
        """Flag is on."""
        try:
            mode = self._izzibridge.data[IZZY_SENSOR_FAN_MODE_ID]
            if mode != None :
                _LOGGER.debug("Is on True")
                return True
            return False
            _LOGGER.debug("Is on False")
        except KeyError:
            _LOGGER.debug("Is on False")
            return False
    @property
    def speed(self):
        """Return the current fan mode."""
        try:
            return self._izzibridge.data[IZZY_SENSOR_FAN_MODE_ID]
        except KeyError:
            return None

    def turn_on(self, speed_arg: Optional[int] = None, **kwargs: Any) -> None:
        """Turn on the fan."""
        if speed_arg is None:
            speed_arg = 40
        
        self._izzibridge.set_fan_on(True)
        self.set_percentage(speed_arg)

    def turn_off(self, **kwargs: Any) -> None:
        """Turn off the fan (to away)."""
        self._izzibridge.set_fan_on(False)
        
    def set_percentage(self, percentage: int) -> None:
        """Set fan speed."""
        _LOGGER.debug("Changing fan percentage to %d %%", percentage)
        valid_val = False
        if percentage == 0:
            self._izzibridge.set_fan_on(False)
            valid_val = True
        else:
            try:
                self._izzibridge.set_fan_on(True)
                valid_val = self._izzibridge.set_fan_speed(percentage)  
            except ValueError:
                _LOGGER.error("Wrong percentage value %s", percentage)
         
        if valid_val == True:
            self._izzibridge.data[IZZY_SENSOR_FAN_MODE_ID] = percentage
        else:
            _LOGGER.error("Fan percentage not accepted %s", percentage)

        # Update current mode
        self.schedule_update_ha_state()
 
