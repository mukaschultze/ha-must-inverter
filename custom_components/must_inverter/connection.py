from collections.abc import Mapping
from typing import Any

from homeassistant.const import CONF_DEVICE, CONF_HOST, CONF_MODE, CONF_PORT
from modbus_connection import ModbusSerialParams, ModbusTcpParams, ModbusUdpParams

from .const import CONF_BAUDRATE, CONF_BYTESIZE, CONF_PARITY, CONF_STOPBITS

type ModbusParams = ModbusSerialParams | ModbusTcpParams | ModbusUdpParams


def create_modbus_params(options: Mapping[str, Any]) -> ModbusParams:
    """Build the Modbus link parameters from the config entry options.

    The serial device can be a local port, a `socket://` or `rfc2217://` device
    server, or an ESPHome serial proxy (`esphome-hass://`), all opened by serialx.
    """
    match options[CONF_MODE]:
        case "serial":
            return ModbusSerialParams(
                device=options[CONF_DEVICE],
                baudrate=int(options[CONF_BAUDRATE]),
                bytesize=int(options[CONF_BYTESIZE]),
                parity=str(options[CONF_PARITY]).upper(),
                stopbits=int(options[CONF_STOPBITS]),
            )
        case "tcp":
            return ModbusTcpParams(host=options[CONF_HOST], port=int(options[CONF_PORT]))
        case "udp":
            return ModbusUdpParams(host=options[CONF_HOST], port=int(options[CONF_PORT]))
        case mode:
            raise ValueError(f"Invalid mode {mode!r}")
