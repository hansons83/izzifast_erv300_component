"""Support to control a Zehnder ComfoAir Q350/450/600 ventilation unit."""
import logging

#from pycomfoconnect import Bridge, ComfoConnect
import voluptuous as vol

from homeassistant.const import (
    CONF_TYPE,
    CONF_HOST,
    CONF_NAME,
    CONF_PORT,
    EVENT_HOMEASSISTANT_STOP,
)
from homeassistant.helpers import discovery
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.dispatcher import *
from .izzi.controller import IzziEthBridge, IzziSerialBridge, IzziController

_LOGGER = logging.getLogger(__name__)

CONF_CORRECTION = "extract_correction"
CONF_BYPASS_MODE = "bypass_mode"
CONF_BYPASS_TEMP = "bypass_temp"

DOMAIN = "izzifast"

SIGNAL_IZZIFAST_UPDATE_RECEIVED = "izzifast_update_received_{}"

DEFAULT_NAME = "iZZi ERV 300"
DEFAULT_PORT = 8234
DEFAULT_CORRECTION = 0.0
DEFAULT_BYPASS_TEMP = 23
DEFAULT_BYPASS_MODE = "auto"

CONF_TYPE_SERIAL = "serial"
CONF_TYPE_TCP = "tcp"

bypass_mode_list = ["auto", "open", "closed"]
vent_mode_list = ["none", "fireplace", "open windows"]

DEVICE = None

SERIAL_SCHEMA = {
    vol.Required(CONF_TYPE): CONF_TYPE_SERIAL,
    vol.Required(CONF_PORT): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_CORRECTION, default=DEFAULT_CORRECTION): vol.All(vol.Coerce(int), vol.Range(min=-20, max=20)),
    vol.Optional(CONF_BYPASS_MODE, default=DEFAULT_BYPASS_MODE): vol.In(bypass_mode_list),
    vol.Optional(CONF_BYPASS_TEMP, default=DEFAULT_BYPASS_TEMP): vol.All(vol.Coerce(int), vol.Range(min=17, max=24)),
}

ETHERNET_SCHEMA = {
    vol.Required(CONF_TYPE): CONF_TYPE_TCP,
    vol.Required(CONF_HOST): cv.string,
    vol.Required(CONF_PORT, default=DEFAULT_PORT): cv.positive_int,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_CORRECTION, default=DEFAULT_CORRECTION): vol.All(vol.Coerce(int), vol.Range(min=-20, max=20)),
    vol.Optional(CONF_BYPASS_MODE, default=DEFAULT_BYPASS_MODE): vol.In(bypass_mode_list),
    vol.Optional(CONF_BYPASS_TEMP, default=DEFAULT_BYPASS_TEMP): vol.All(vol.Coerce(int), vol.Range(min=17, max=24)),
}


CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Any(SERIAL_SCHEMA, ETHERNET_SCHEMA)
}, extra=vol.ALLOW_EXTRA)

ATTR_MODE_NAME = "mode"
ATTR_TEMP_NAME = "temp"
BYPASS_DEFAULT_NAME = "auto"
TEMP_DEFAULT_VAL = 23
VENT_DEFAULT_NAME = "none"

def setup(hass, config):
    """Set up the izzi bridge."""

    conf = config[DOMAIN]
    type = conf[CONF_TYPE]
    name = conf[CONF_NAME]
    
    correction = conf[CONF_CORRECTION]
    bypass_temp = conf[CONF_BYPASS_TEMP]
    bypass_mode = conf[CONF_BYPASS_MODE]

    if CONF_TYPE_TCP == type:
        _LOGGER.debug("Setting up Ethernet bridge")
        host = conf[CONF_HOST]
        port = conf[CONF_PORT]
        bridge = IzziEthBridge(host, port)
    elif CONF_TYPE_SERIAL == type:
        _LOGGER.debug("Setting up Serial bridge")
        port = conf[CONF_PORT]
        bridge = IzziSerialBridge(port)
    else:
        _LOGGER.error("Wrong bridge type '%s'", type)
        return false
    
    # Setup Izzi Bridge
    izzibridge = IzzifastBridge(hass, bridge, name, correction)
    hass.data[DOMAIN] = izzibridge

    izzibridge.set_bypass_temp(bypass_temp);
    izzibridge.set_bypass_mode(bypass_mode_list.index(bypass_mode));
    
    # Start connection with bridge
    izzibridge.connect()

    # Schedule disconnect on shutdown
    def _shutdown(_event):
        izzibridge.disconnect()

    hass.bus.listen_once(EVENT_HOMEASSISTANT_STOP, _shutdown)
    
    def handle_set_bypass_mode(call):
        """Handle the service call."""
        mode = call.data.get(ATTR_MODE_NAME, BYPASS_DEFAULT_NAME)
        try:
            if izzibridge.set_bypass_mode(bypass_mode_list.index(mode)) != True:
                _LOGGER.error("Bypass mode invalid %s", mode)
        except Exception:
            _LOGGER.error("Bypass mode failed %s", mode)
            
    def handle_set_bypass_temp(call):
        """Handle the service call."""
        temp = call.data.get(ATTR_TEMP_NAME, TEMP_DEFAULT_VAL)
        try:
            if izzibridge.set_bypass_temp(temp) != True:
                _LOGGER.error("Bypass temp invalid %d", temp)
        except Exception:
            _LOGGER.error("Bypass temp failed %d", temp)
            
    def handle_set_vent_mode(call):
        """Handle the service call."""
        mode = call.data.get(ATTR_MODE_NAME, VENT_DEFAULT_NAME)
        try:
            if izzibridge.set_vent_mode(vent_mode_list.index(mode)) != True:
                _LOGGER.error("Vent mode invalid to %s", mode)
        except Exception:
            _LOGGER.error("Vent mode failed %s", mode)
            
    hass.services.register(DOMAIN, "bypass_mode", handle_set_bypass_mode)
    hass.services.register(DOMAIN, "bypass_temp", handle_set_bypass_temp)
    hass.services.register(DOMAIN, "vent_mode", handle_set_vent_mode)

    # Load platforms
    discovery.load_platform(hass, "fan", DOMAIN, {}, config)
    discovery.load_platform(hass, "sensor", DOMAIN, {}, config)
    discovery.load_platform(hass, "binary_sensor", DOMAIN, {}, config)

    return True


class IzzifastBridge:
    """Representation of a IZZI bridge."""

    def __init__(self, hass, bridge, name, correction):
        """Initialize the IZZI bridge."""
        self.data = {}
        self.name = name
        self.hass = hass
        self.unique_id = "_iZZi_300_ERV_FE"
        self.correction = correction

        self.controller = IzziController(
            bridge=bridge
        )
        self.controller.callback_sensor = self.sensor_callback

    def connect(self):
        """Connect with the bridge."""
        _LOGGER.debug("Connecting with bridge")
        self.controller.connect()

    def disconnect(self):
        """Disconnect from the bridge."""
        _LOGGER.debug("Disconnecting from bridge")
        self.controller.disconnect()
 
    def force_update(self, sensor):
        self.controller.force_update(sensor)
    
    def set_bypass_mode(self, mode) -> bool:
        return self.controller.set_bypass_mode(mode)
            
    def set_vent_mode(self, mode) -> bool:
        return self.controller.set_vent_mode(mode)
        
    def set_bypass_temp(self, temp) -> bool:
        return self.controller.set_bypass_temp(temp)
    
    def set_fan_on(self, isOn : bool) -> bool:
        self.controller.set_unit_on(isOn)
        return True
        
    def set_fan_speed(self, speed : int) -> bool:
        if speed < 20 or speed > 100:
            return False
        
        if self.correction > 0:
            self.controller.set_fan_speed(speed - int(((self.correction/100)*speed)), speed)
        else:
            self.controller.set_fan_speed(speed, speed-int(((self.correction/100)*speed)))
        
        return True
        
    def sensor_callback(self, var, value):
        """Notify listeners that we have received an update."""
        _LOGGER.debug("Received update for %s: %s", var, value)
        async_dispatcher_send(
            self.hass, SIGNAL_IZZIFAST_UPDATE_RECEIVED.format(var), value
        )
