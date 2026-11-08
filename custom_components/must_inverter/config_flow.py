import logging
import probatio as vol

from collections.abc import Mapping

from typing import Any
from urllib.parse import parse_qs, urlparse
from homeassistant.components.modbus import async_get_temporary_unit
from homeassistant.components.modbus.connection import async_get_connection_info
from homeassistant.config_entries import ConfigEntryState
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers.schema_config_entry_flow import (
    SchemaCommonFlowHandler,
    SchemaConfigFlowHandler,
    SchemaFlowError,
    SchemaFlowFormStep,
    SchemaFlowStep,
    SchemaOptionsFlowHandler,
)

from homeassistant.helpers.selector import selector, SelectSelectorMode, SerialPortSelector
from homeassistant.const import (
    CONF_NAME,
    CONF_DEVICE,
    CONF_MODEL,
    CONF_SCAN_INTERVAL,
    CONF_MODE,
    CONF_HOST,
    CONF_PORT,
    CONF_TIMEOUT,
)
from modbus_connection import ModbusError

from .connection import create_modbus_params
from .const import (
    DOMAIN,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_DEVICE_ID,
    DEFAULT_TIMEOUT,
    DEFAULT_BAUDRATE,
    DEFAULT_PARITY,
    DEFAULT_STOPBITS,
    DEFAULT_BYTESIZE,
    SUPPORTED_MODELS,
    CONF_BAUDRATE,
    CONF_PARITY,
    CONF_STOPBITS,
    CONF_BYTESIZE,
    CONF_DEVICE_ID,
)

_LOGGER = logging.getLogger(__name__)

# Registers read to check the inverter is answering, valid for every supported model
PROBE_ADDRESS = 20001
PROBE_COUNT = 3


SERIAL_SCHEMA = vol.Schema(
    {
        # Lists local ports and ESPHome serial proxies, and accepts socket:// and
        # rfc2217:// device server URLs when entered manually
        vol.Required(CONF_DEVICE): SerialPortSelector(),
        vol.Required(CONF_BAUDRATE, default=DEFAULT_BAUDRATE): vol.Coerce(int),
        vol.Required(CONF_PARITY, default=DEFAULT_PARITY): selector(
            {
                "select": {
                    "mode": SelectSelectorMode.LIST,
                    "translation_key": CONF_PARITY,
                    # Lowercase as hassfest requires for translated options
                    "options": ["n", "e", "o"],
                }
            }
        ),
        vol.Required(CONF_STOPBITS, default=DEFAULT_STOPBITS): selector(
            {
                "select": {
                    "mode": SelectSelectorMode.LIST,
                    "options": ["1", "2"],
                }
            }
        ),
        vol.Required(CONF_BYTESIZE, default=DEFAULT_BYTESIZE): selector(
            {
                "select": {
                    "mode": SelectSelectorMode.LIST,
                    "options": ["7", "8"],
                }
            }
        ),
    }
)

TCP_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=502): int,
    }
)

UDP_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=502): int,
    }
)

COMMON_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_NAME): str,
        vol.Required(CONF_MODEL, default="autodetect"): selector(
            {
                "select": {
                    "mode": SelectSelectorMode.DROPDOWN,
                    "translation_key": CONF_MODEL,
                    "options": ["autodetect"] + SUPPORTED_MODELS,
                }
            }
        ),
        vol.Required(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.Coerce(float),
        vol.Required(CONF_MODE): selector(
            {
                "select": {
                    "mode": SelectSelectorMode.LIST,
                    "translation_key": CONF_MODE,
                    "options": ["serial", "tcp", "udp"],
                }
            }
        ),
    }
)

MODBUS_SCHEMA = vol.Schema(
    {
        # The shared connection rejects negative timeouts
        vol.Required(CONF_TIMEOUT, default=DEFAULT_TIMEOUT): vol.All(vol.Coerce(float), vol.Range(min=0.1)),
        vol.Required(CONF_DEVICE_ID, default=DEFAULT_DEVICE_ID): int,
    }
)


async def validate_connection(handler: SchemaCommonFlowHandler, user_input: dict[str, Any]) -> dict[str, Any]:
    """Check the inverter answers over the connection settings entered in the previous steps."""
    flow = handler.parent_handler
    hass = flow.hass
    options = {**handler.options, **user_input}

    try:
        params = create_modbus_params(options)
    except ValueError as ex:
        _LOGGER.warning("invalid connection settings: %s", ex)
        raise SchemaFlowError("cannot_connect") from ex

    # A loaded entry holds the port with its current settings, and one port can't be
    # shared over different settings. Unload it while probing the new ones.
    entry = flow.config_entry if isinstance(flow, SchemaOptionsFlowHandler) else None
    relinking = False
    if entry is not None and entry.state in (ConfigEntryState.LOADED, ConfigEntryState.SETUP_RETRY):
        current = create_modbus_params(entry.options)
        if current.endpoint == params.endpoint and current != params:
            relinking = await hass.config_entries.async_unload(entry.entry_id)

    # The connection's timeout is the largest one its units ask for, recorded per unit
    # id and kept after the probe releases the unit. Probe with the submitted timeout,
    # then put back what the unit had before: the loaded entry's own timeout, or nothing.
    # Leave it alone when another entry holds the same unit id, as it is that entry's.
    holders = {
        entry_id
        for info in async_get_connection_info(hass)
        if info.endpoint == params.endpoint
        for entry_id, unit_ids in info.units.items()
        if options[CONF_DEVICE_ID] in unit_ids
    }
    own_entry_id = entry.entry_id if entry is not None else None
    held_elsewhere = bool(holders - {own_entry_id})

    succeeded = False
    try:
        async with async_get_temporary_unit(hass, params, options[CONF_DEVICE_ID]) as unit:
            if not held_elsewhere:
                unit.require_timeout(options[CONF_TIMEOUT])
                if unit.connected:
                    # A live link keeps the timeout it was opened with, and a raised one only
                    # schedules its teardown. Drop it now so the probe reconnects with it.
                    await unit.disconnect()
            try:
                await unit.read_holding_registers(PROBE_ADDRESS, PROBE_COUNT)
            finally:
                if not held_elsewhere:
                    held_by_entry = own_entry_id in holders
                    unit.require_timeout(entry.options.get(CONF_TIMEOUT, DEFAULT_TIMEOUT) if held_by_entry else None)
        succeeded = True
    except ConfigEntryNotReady as ex:
        # The ESPHome integration providing the serial proxy has not loaded yet
        _LOGGER.warning("serial port not ready: %s", ex)
        raise SchemaFlowError("cannot_connect") from ex
    except HomeAssistantError as ex:
        _LOGGER.warning("serial port in use: %s", ex)
        raise SchemaFlowError("port_in_use") from ex
    except (ModbusError, OSError) as ex:
        _LOGGER.warning("unable to talk to the inverter: %s", ex)
        raise SchemaFlowError("cannot_connect") from ex
    finally:
        if relinking and not succeeded:
            # The new settings won't be saved, set the entry back up with the stored ones.
            # On success, saving the changed options reloads it (options_flow_reloads).
            await hass.config_entries.async_setup(entry.entry_id)

    return user_input


# needs to be async, probably a bug in HA
async def next_step(user_input):
    return user_input.get(CONF_MODE)


CONFIG_FLOW: Mapping[str, SchemaFlowStep] = {
    "user": SchemaFlowFormStep(next_step="common"),
    # Reconfigure is not yet supported by SchemaConfigFlowHandler as it creates a new entry instead of updating the existing one
    # "reconfigure": SchemaFlowFormStep(next_step="common"),
    "common": SchemaFlowFormStep(schema=COMMON_SCHEMA, next_step=next_step),
    "serial": SchemaFlowFormStep(schema=SERIAL_SCHEMA, next_step="modbus"),
    "tcp": SchemaFlowFormStep(schema=TCP_SCHEMA, next_step="modbus"),
    "udp": SchemaFlowFormStep(schema=UDP_SCHEMA, next_step="modbus"),
    "modbus": SchemaFlowFormStep(schema=MODBUS_SCHEMA, validate_user_input=validate_connection),
}

OPTIONS_FLOW: Mapping[str, SchemaFlowStep] = {
    "init": SchemaFlowFormStep(next_step="common"),
    **CONFIG_FLOW,
}


class MustInverterConfigFlow(SchemaConfigFlowHandler, domain=DOMAIN):
    """Handle a config flow for Must Inverter."""

    VERSION = 1
    MINOR_VERSION = 2

    config_flow = CONFIG_FLOW
    options_flow = OPTIONS_FLOW
    # Reload whenever saved options change, even if the entry isn't loaded at that point
    options_flow_reloads = True

    def async_config_entry_title(self, options: Mapping[str, Any]) -> str:
        """Return config entry title."""
        # return f"Must Inverter"
        mode = options.get(CONF_MODE)

        if mode == "serial":
            device = options.get(CONF_DEVICE, "")
            if device.startswith("esphome-hass://"):
                # esphome-hass://esphome/<entry_id>?port_name=<name>
                port_name = parse_qs(urlparse(device).query).get("port_name")
                device = port_name[0] if port_name else "ESPHome serial proxy"
            return options.get(CONF_NAME) or device
        else:
            return options.get(CONF_NAME) or options.get(CONF_HOST)
