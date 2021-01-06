Custom component for IzziFast ERV 300 heat recovery ventilation unit.

Copy izzifast directory into home assistant *custom_component* directory

Support USB and network RS485 adapters

- USB configuration:
  
  izzifast:
   | type: serial
   | port: /dev/COMX
   | extract_correction: -10
   | bypass_mode: "auto"
   | bypass_temp: 24
  
- Lan configuration:

  izzifast:
   | type: tcp
   | host: "host_ip_address"
   | port: 1234
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

