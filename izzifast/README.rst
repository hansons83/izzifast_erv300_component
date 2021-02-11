Custom component for IzziFast ERV 300 heat recovery ventilation unit.

Copy izzifast directory into home assistant *custom_component* directory

Support USB and network RS485 adapters
Support slave and master mode.
 - In slave mode only sensors and binary_sensors are available and touch panel must be connected to RS485 lines.
 - In master mode, fan entity and services are also available, touch panel must not be connected.

- USB configuration:
  
  izzifast:
   | type: serial
   | port: /dev/COMX
   | mode: "slave"
   | extract_correction: -10
   | bypass_mode: "auto"
   | bypass_temp: 24
  
- Lan configuration:

  izzifast:
   | type: tcp
   | host: "host_ip_address"
   | port: 1234
   | mode: "master"
   | extract_correction: 10
   | bypass_mode: "auto"
   | bypass_temp: 24
  
Make sure RS485 of LAN converter is configured as follow:

    | Baud Rate： 9600 bps
    | Data Size： 8 bit
    | Parity： None
    | Stop Bits： 1 bit

To enable logs add below to configuration.yaml file

logger:
  default: info

  logs:
   | custom_components.izzifast: debug
   | izzicontroller: debug

