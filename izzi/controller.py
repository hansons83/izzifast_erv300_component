#!/usr/bin/env python

import binascii
import socket 
import struct
import time
import sys
import select
import logging
import threading
from array import array
from .const import *
from . import *

_LOGGER = logging.getLogger('izzicontroller')

#values = array('B', [0x64, 0x19, 0x00, 0x14, 0x00, 0x16, 0x05, 0x00, 0x17, 0x02, 0x28, 0x28, 0x00, 0x00, 0x00])


#socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#socket.connect((TCP_IP, TCP_PORT))
#socket.setblocking(0)

#class IzziEthbrindge
#    connect()
#    disconnect()    
#    read_message()
#    write_message()
class IzziBridge(object):
    def connect(self) -> bool:
        """Open connection to the bridge."""
        pass
    def disconnect(self) -> bool:
        """Close connection to the bridge."""
        pass
    def is_connected(self):
        """Returns weather there is an open socket."""
        pass

    def read_message(self, timeout=3) -> b'':
        """Read a message from the connection."""
        pass
        
    def write_message(self, message: b'') -> bool:
        """Write a message to the connection."""
        pass

class IzziEthBridge(IzziBridge):
    """Implements an interface to send and receive messages from the Bridge."""

    STATUS_MESSAGE_LENGTH = 15

    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port

        self._socket = None
        self.debug = False

    def connect(self) -> bool:
        """Open connection to the bridge."""

        if self._socket is None:
            tcpsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            tcpsocket.connect((self.host, self.port))
            tcpsocket.setblocking(0)
            self._socket = tcpsocket
            # Clear buffered data
            while True:
                ready = select.select([self._socket], [], [], 0.1)
                if not ready[0]:
                    break
                self._socket.recv(1024)

        return True

    def disconnect(self) -> bool:
        """Close connection to the bridge."""

        self._socket.close()
        self._socket = None

        return True

    def is_connected(self):
        """Returns weather there is an open socket."""
        
        return self._socket is not None

    def read_message(self, timeout=3) -> b'':
        """Read a message from the connection."""

        if self._socket is None:
            raise Exception('Broken pipe')

        message = b''
        remaining = self.STATUS_MESSAGE_LENGTH
        message_valid = False
        while remaining > 0:
            ready = select.select([self._socket], [], [], timeout)
            if not ready[0]:
                message = None
                break
            if not message_valid:
                data = self._socket.recv(1)
                if struct.unpack_from('>B', data, 0)[0] != IZZI_STATUS_MESSAGE_ID:
                    continue
                message_valid = True
            else:
                data = self._socket.recv(remaining)
            remaining -= len(data)
            message += (data)
        
        # Debug message
        
        if message != None:
            _LOGGER.debug("RX %s", binascii.hexlify(message))
        return message

    def write_message(self, message: b'') -> bool:
        """Send a message."""

        if self._socket is None:
            raise Exception('Not connected!')

        # Debug message
        #_LOGGER.debug("TX %s", "".join( str(x) for x in message))
        _LOGGER.debug("TX %s", str(binascii.hexlify(message)))
        # Send packet
        try:
            self._socket.sendall(message)
        except Exception:
            return False
        return True

class IzziController(object):
    """Implements the commands to communicate with the IZZI 300 ERV ventilation unit."""
                    # Id of sensor,                      Value,    Index in status message array
    _sensors_data = {IZZY_SENSOR_TEMPERATURE_SUPPLY_ID: [None, IZZI_STATUS_MSG_SUPPLY_AIR_TEMP_INDEX], 
                     IZZY_SENSOR_TEMPERATURE_EXTRACT_ID: [None, IZZI_STATUS_MSG_EXTRACT_AIR_TEMP_INDEX], 
                     IZZY_SENSOR_TEMPERATURE_EXHAUST_ID: [None, IZZI_STATUS_MSG_EXHAUST_AIR_TEMP_INDEX],
                     IZZY_SENSOR_TEMPERATURE_OUTDOOR_ID: [None, IZZI_STATUS_MSG_OUTDOR_AIR_TEMP_INDEX], 
                     IZZY_SENSOR_BYPASS_STATE_ID: [None, IZZI_STATUS_MSG_BYPASS_STATE_INDEX], 
                     IZZY_SENSOR_COVER_STATE_ID: [None, IZZI_STATUS_MSG_COVER_STATE_INDEX]}

                    # Id of sensor,               Target value,    Index in command array, multiplier
    _cmd_data = {IZZY_SENSOR_FAN_SUPPLY_SPEED_ID: [0, IZZI_CMD_MSG_SUPPLY_FAN_SPEED_INDEX, None], 
                 IZZY_SENSOR_FAN_EXTRACT_SPEED_ID: [0, IZZI_CMD_MSG_EXTRACT_FAN_SPEED_INDEX, None], 
                 IZZY_SENSOR_UNIT_STATE_ID: [IZZY_CMD_UNIT_STATE_OFF, IZZI_CMD_MSG_UNIT_STATE_INDEX, None], 
                 IZZY_SENSOR_BYPASS_TEMP_ID: [22, IZZI_CMD_MSG_BYPASS_TEMP_INDEX, None],
                 IZZY_SENSOR_BYPASS_MODE_ID: [IZZY_CMD_BYPASS_MODE_AUTO, IZZI_CMD_MSG_BYPASS_MODE_INDEX, None]}

                    # Id of sensor,           Target Value, Current value    
    _virtual_data = {IZZY_SENSOR_VENT_MODE_ID: [IZZY_SENSOR_VENT_MODE_NONE, None],
                     IZZY_SENSOR_EFFICIENCY_ID: [0, None]} 

    _command_present = False
    """Callback function to invoke when sensor updates are received."""
    callback_sensor = None
    
    _command_message = array('B', [0x64, 0x19, 0x00, 0x14, 0x00, 0x16, 0x05, 0x00, 0x17, 0x02, 0x28, 0x28, 0x01, 0x00, 0x00])

    def __init__(self, bridge: IzziBridge):

        self._bridge = bridge
        self._stopping = False
        self._connection_thread = None

    def connect(self):
        """Connect to the bridge. Disconnect existing clients if needed by default."""

        try:
            # Start connection thread
            self._connection_thread = threading.Thread(target=self._connection_thread_loop)
            self._connection_thread.start()
        except Exception as exc:
            _LOGGER.error(exc)
            raise Exception('Could start task.')

    def disconnect(self):
        """Disconnect from the bridge."""
    
        # Set the stopping flag
        self._stopping = True

        # Wait for the background thread to finish
        self._connection_thread.join()
        self._connection_thread = None

    def is_connected(self):
        """Returns whether there is a connection with the bridge."""

        return self._bridge.is_connected()

    def force_update(self, sensor_id):
        """Make sure state of sensor will be published."""
        sensor_obj = self._sensors_data.get(sensor_id)
        if sensor_obj != None:
            sensor_obj[0] = None
        sensor_obj = self._cmd_data.get(sensor_id)
        if sensor_obj != None:
            sensor_obj[0] = None
        sensor_obj = self._virtual_data.get(sensor_id)
        if sensor_obj != None:
            sensor_obj[1] = None
    
    def set_bypass_mode(self, mode : int) -> bool:
        if mode < 0 or mode > 2:
            return False
        self._cmd_data[IZZY_SENSOR_BYPASS_MODE_ID][0] = mode
        return True
        
    def get_bypass_mode(self) -> int:
        return self._cmd_data[IZZY_SENSOR_BYPASS_MODE_ID][0];
        
    def set_bypass_temp(self, temp : int) -> bool:
        if temp < 18 or temp > 26:
            return False
        self._cmd_data[IZZY_SENSOR_BYPASS_TEMP_ID][0] = temp
        return True
        
    def set_fan_speed(self, supply : int, extract : int) :
        if supply < 20 or extract < 20 or supply > 100 or supply > 100:
            return False
        
        self._cmd_data[IZZY_SENSOR_FAN_SUPPLY_SPEED_ID][0] = supply
        self._cmd_data[IZZY_SENSOR_FAN_EXTRACT_SPEED_ID][0] = extract
        return True

    def get_supply_speed():
        return self._cmd_data[IZZY_SENSOR_FAN_SUPPLY_SPEED_ID][0]
        
    def get_extract_speed():
        return self._cmd_data[IZZY_SENSOR_FAN_EXTRACT_SPEED_ID][0]
    
    
    def set_vent_mode(self, mode : int) -> bool:
        if mode < IZZY_SENSOR_VENT_MODE_NONE or mode > IZZY_SENSOR_VENT_MODE_OPEN_WINDOW:
            return False
        if mode == IZZY_SENSOR_VENT_MODE_NONE:
            self._cmd_data[IZZY_SENSOR_FAN_SUPPLY_SPEED_ID][2] = None
            self._cmd_data[IZZY_SENSOR_FAN_EXTRACT_SPEED_ID][2] = None
        elif mode == IZZY_SENSOR_VENT_MODE_FIREPLACE:
            self._cmd_data[IZZY_SENSOR_FAN_SUPPLY_SPEED_ID][2] = None
            self._cmd_data[IZZY_SENSOR_FAN_EXTRACT_SPEED_ID][2] = 0.8
        elif mode == IZZY_SENSOR_VENT_MODE_OPEN_WINDOW:
            self._cmd_data[IZZY_SENSOR_FAN_SUPPLY_SPEED_ID][2] = 0
            self._cmd_data[IZZY_SENSOR_FAN_EXTRACT_SPEED_ID][2] = None
        
        self._virtual_data[IZZY_SENSOR_VENT_MODE_ID][0] = mode
        return True
    
    def set_unit_on(self, on : bool) :
        if on:
            self._cmd_data[IZZY_SENSOR_UNIT_STATE_ID][0] = IZZY_CMD_UNIT_STATE_ON
        else:
            self._cmd_data[IZZY_SENSOR_UNIT_STATE_ID][0] = IZZY_CMD_UNIT_STATE_OFF
        return True
        
    def _connection_thread_loop(self):
        self._stopping = False
        stat_msg_counter = 0
            
        while not self._stopping:
        
            # Start connection
            if not self.is_connected():

                try:
                    _LOGGER.info("Trying connect to bridge")
                    # Connect or re-connect
                    if not self._bridge.connect():
                        time.sleep(5)
                        continue
                        
                    _LOGGER.info("Connection established")
                except Exception as exc:
                    _LOGGER.error(exc)
                    time.sleep(5)
                    continue;
            
            try:
                
                status_message = self._bridge.read_message()
                if status_message == None:
                    self._bridge.disconnect()
                    _LOGGER.error("Can't read message, disconnecting")
                    continue

                #print(binascii.hexlify(status_message))
                command_id = struct.unpack_from('>B', status_message, IZZI_STATUS_MSG_ID_INDEX)[0]
                if (command_id == IZZI_STATUS_MESSAGE_ID):
                    stat_msg_counter += 1
                    #_LOGGER.debug(status_message)
                    
                    for sensor_id in self._sensors_data:
                        sensor_data = self._sensors_data[sensor_id];
                        #print(sensor_id, " ;", self._sensors_data[sensor_id])
                        sensor_current = struct.unpack_from('>B', status_message, sensor_data[1])[0] 
                       
                        if sensor_data[0] != sensor_current:
                            sensor_data[0] = sensor_current
                            if self.callback_sensor:
                                self.callback_sensor(sensor_id, sensor_data[0])
                    
                    #Calculate efficiency
                    try:
                        t1 = float(self._sensors_data[IZZY_SENSOR_TEMPERATURE_OUTDOOR_ID][0])
                        t2 = float(self._sensors_data[IZZY_SENSOR_TEMPERATURE_SUPPLY_ID][0])
                        t3 = float(self._sensors_data[IZZY_SENSOR_TEMPERATURE_EXTRACT_ID][0])
                        
                        if t3 != t1:
                            efficiency = ((t2 - t1) / (t3 - t1)) * 100.0
                            self._virtual_data[IZZY_SENSOR_EFFICIENCY_ID][0] = int(efficiency)
                        else:
                            self._virtual_data[IZZY_SENSOR_EFFICIENCY_ID][0] = 0
                                
                    except Exception as exc:
                        self._virtual_data[IZZY_SENSOR_EFFICIENCY_ID][0] = None
                        _LOGGER.error(exc)
                
                elif command_id == IZZI_COMMAND_MESSAGE_ID:
                    self._command_present = True
                    
                for sensor_id in self._cmd_data:
                    sensor_data = self._cmd_data[sensor_id]
                    #print(sensor_id, " ;", self._sensors_data[sensor_id])
                    sensor_current = self._command_message[sensor_data[1]]
                    if sensor_data[0] is None:
                        sensor_data[0] = sensor_current
                        if self.callback_sensor:
                            self.callback_sensor(sensor_id, sensor_data[0])
                    
                        # Make sure we use up to date data
                    if sensor_data[2] is not None:
                        exp_sensor_val = int(float(sensor_data[0]) * sensor_data[2])
                    else:
                        exp_sensor_val = sensor_data[0]
                        
                    if exp_sensor_val != sensor_current:
                        self._command_message[sensor_data[1]] = exp_sensor_val
                        if self.callback_sensor:
                            self.callback_sensor(sensor_id, self._command_message[sensor_data[1]])
                    
                for sensor_id in self._virtual_data:
                    sensor_data = self._virtual_data[sensor_id]
                    #print(sensor_id, " ;", self._sensors_data[sensor_id])
                    if sensor_data[1] is None or sensor_data[0] != sensor_data[1]:
                        sensor_data[1] = sensor_data[0]
                        if self.callback_sensor:
                            self.callback_sensor(sensor_id, sensor_data[0])
                 
                #if self._command_present == False and stat_msg_counter >= 2:
                if stat_msg_counter >= 2:
                    stat_msg_counter = 0
                    #print(self._command_message)
                    time.sleep(0.1)
                    #_LOGGER.debug(self._command_message)
                    self._bridge.write_message(self._command_message)

            except Exception as exc:
                _LOGGER.error(exc)
                continue
            
        self._bridge.disconnect()
