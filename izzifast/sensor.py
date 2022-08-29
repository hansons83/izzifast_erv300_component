"""Platform to control a Zehnder ComfoAir Q350/450/600 ventilation unit."""

import logging
from homeassistant.helpers.dispatcher import *
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (
    DEVICE_CLASS_TEMPERATURE,
    DEVICE_CLASS_PRESSURE,
    TEMP_CELSIUS
)
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity

from . import DOMAIN, SIGNAL_IZZIFAST_UPDATE_RECEIVED, IzzifastBridge
from .izzi.const import *
from . import *
from .izzi import *

bypass_mapping = ["auto", "zawsze otwarty", "zawsze zamknięty"]
vent_mode_mapping = ["none", "fireplace", "open windows"]

_LOGGER = logging.getLogger(__name__)

def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the ComfoConnect fan platform."""
    izzibridge = hass.data[DOMAIN]

    sensors = [
        [
            "iZZi Exhaust Temperature",
            TEMP_CELSIUS,
            IZZY_SENSOR_TEMPERATURE_EXHAUST_ID,
            DEVICE_CLASS_TEMPERATURE,
            None,
            None
        ],
        [
            "iZZi Outdoor Temperature",
            TEMP_CELSIUS,
            IZZY_SENSOR_TEMPERATURE_OUTDOOR_ID,
            DEVICE_CLASS_TEMPERATURE,
            None,
            None
        ],
        [
            "iZZi Supply Temperature",
            TEMP_CELSIUS,
            IZZY_SENSOR_TEMPERATURE_SUPPLY_ID,
            DEVICE_CLASS_TEMPERATURE,
            None,
            None
        ],
        [
            "iZZi Extract Temperature",
            TEMP_CELSIUS,
            IZZY_SENSOR_TEMPERATURE_EXTRACT_ID,
            DEVICE_CLASS_TEMPERATURE,
            None,
            None
        ],
        ["iZZi Supply Fan Speed", "%", IZZY_SENSOR_FAN_SUPPLY_SPEED_ID, None, "mdi:fan", None],
        ["iZZi Extract Fan Speed", "%", IZZY_SENSOR_FAN_EXTRACT_SPEED_ID, None, "mdi:fan", None],
        ["iZZi Bypass mode", "", IZZY_SENSOR_BYPASS_MODE_ID, None, None, bypass_mapping],
        ["iZZi Bypass temp", TEMP_CELSIUS, IZZY_SENSOR_BYPASS_TEMP_ID, None, "mdi:home-temperature", None],
        ["iZZi Vent mode", "", IZZY_SENSOR_VENT_MODE_ID, None, None, vent_mode_mapping],
        ["iZZi Efficiency", "%", IZZY_SENSOR_EFFICIENCY_ID, None, None, None],
        ["iZZi Extract correction", "%", IZZY_SENSOR_EXTRACT_CORRECTION_STATE_ID, None, None, None],
        ["iZZi CF extract correction", "%", IZZY_SENSOR_CF_EXTRACT_CORRECTION_ID, None, None, None],
        ["iZZi CF supply correction", "%", IZZY_SENSOR_CF_SUPPLY_CORRECTION_ID, None, None, None]
        
    ]
    dev = []

    for sensor in sensors:
        dev.append(IzzifastSensor(sensor[0], izzibridge, sensor[1], sensor[2], sensor[3], sensor[4], sensor[5]))

    add_entities(dev, True)


class IzzifastSensor(Entity):
    """Representation of a IZZI sensor."""

    def __init__(self, name, izzibridge: IzzifastBridge, sensor_unit, sensor_type, device_class, icon, mapping_list) -> None:
        """Initialize the ComfoConnect sensor."""
        self._izzibridge = izzibridge
        self._sensor_type = sensor_type
        self._device_class = device_class
        self._units = sensor_unit
        self._name = name
        self._icon = icon
        self._mapping = mapping_list
        self._remove_signal_update = None

    async def async_added_to_hass(self):
        """Register for sensor updates."""
        _LOGGER.debug(
            "Registering for sensor %s", self._sensor_type
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
        if self._mapping != None:
            self._izzibridge.data[self._sensor_type] = self._mapping[value]
        else:
            self._izzibridge.data[self._sensor_type] = value
        
        self.schedule_update_ha_state()

    @property
    def state(self):
        """Return the state of the entity."""
        try:
            return self._izzibridge.data[self._sensor_type]
        except KeyError:
            return None

    @property
    def should_poll(self) -> bool:
        """Do not poll."""
        return False

    @property
    def unique_id(self):
        """Return a unique_id for this entity."""
        return f"{self._izzibridge.unique_id}_sensor_{self._sensor_type}"

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name
    @property
    
    def icon(self):
        """Return the icon to use in the frontend."""
        return self._icon

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity."""
        return self._units

    @property
    def device_class(self):
        """Return the device_class."""
        return self._device_class
