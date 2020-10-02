"""Platform to control a Zehnder ComfoAir Q350/450/600 ventilation unit."""
import logging
from typing import Optional

from homeassistant.components.fan import (
    SPEED_OFF,
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
    """Set up the ComfoConnect fan platform."""
    izzibridge = hass.data[DOMAIN]

    add_entities([IzzifastFan("iZZi Fan", izzibridge)], True)


class IzzifastFan(FanEntity):
    """Representation of the ComfoConnect fan platform."""

    def __init__(self, name, izzibridge: IzzifastBridge) -> None:
        """Initialize the ComfoConnect fan."""
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
        return self._izzibridge.unique_id

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
            if mode != None and mode != SPEED_OFF :
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

    @property
    def speed_list(self):
        """List of available fan modes."""
        return [SPEED_OFF, "20%", "30%", "40%", "50%", "60%", "70%", "80%", "90%", "100%"]

    def turn_on(self, speed_arg: Optional[str] = None, **kwargs: Any) -> None:
        """Turn on the fan."""
        if speed_arg is None:
            speed_arg = "40%"
        
        self.set_speed(speed_arg)

    def turn_off(self, **kwargs: Any) -> None:
        """Turn off the fan (to away)."""
        self.set_speed(SPEED_OFF)

    def set_speed(self, speed: str) -> None:
        """Set fan speed."""
        _LOGGER.debug("Changing fan speed to %s", speed)
        valid_val = False
        if speed == SPEED_OFF:
            self._izzibridge.set_fan_on(False)
            valid_val = True
        else:
            try:
                speedVal = int(speed.replace('%', ''))
                self._izzibridge.set_fan_on(True)
                valid_val = self._izzibridge.set_fan_speed(speedVal)  
            except ValueError:
                _LOGGER.error("Wrong speed value %s", speed)
         
        if valid_val == True:
            self._izzibridge.data[IZZY_SENSOR_FAN_MODE_ID] = speed

        # Update current mode
        self.schedule_update_ha_state()
