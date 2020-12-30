Custom component for IzziFast ERV 300 heat recovery ventilation unit.

Support USB and network RS485 adapters

USB configuration:

izzifast:
  type: serial
  port: /dev/COM1
  extract_correction: -10
  bypass_mode: "auto"
  bypass_temp: 24
  
Lan configuration:

izzifast:
  type: tcp
  host: "x.x.x.x"
  port: 1234
  extract_correction: 10
  bypass_mode: "auto"
  bypass_temp: 24


To enable logs add below to configuration.yaml file

logger:
  default: info
  logs:
    custom_components.izzifast: debug
    izzicontroller: debug

