import logging
import voluptuous as vol

from collections.abc import Mapping

from typing import Any
from homeassistant.helpers.schema_config_entry_flow import SchemaConfigFlowHandler, SchemaFlowStep, SchemaFlowFormStep

from homeassistant.helpers.selector import selector, SelectSelectorMode
from homeassistant.data_entry_flow import section
from homeassistant.const import (
    CONF_DEVICE,
    CONF_MODEL,
    CONF_SCAN_INTERVAL,
    CONF_MODE,
    CONF_HOST,
    CONF_PORT,
    CONF_TIMEOUT,
)

from .const import (
    DOMAIN,
    DEFAULT_SCAN_INTERVAL,
    SUPPORTED_MODELS,
    CONF_BAUDRATE,
    CONF_PARITY,
    CONF_STOPBITS,
    CONF_BYTESIZE,
    CONF_RETRIES,
    CONF_RECONNECT_DELAY,
    CONF_RECONNECT_DELAY_MAX,
)

_LOGGER = logging.getLogger(__name__)


SERIAL_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_DEVICE, default="/dev/ttyUSB0"): str,
        vol.Required(CONF_BAUDRATE, default=19200): int,
        vol.Required(CONF_PARITY, default="N"): str,
        vol.Required(CONF_STOPBITS, default=1): int,
        vol.Required(CONF_BYTESIZE, default=8): int,
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
        vol.Required(CONF_TIMEOUT, default=2.0): vol.Coerce(float),
        vol.Required(CONF_RETRIES, default=3): int,
        vol.Required(CONF_RECONNECT_DELAY, default=0.3): vol.Coerce(float),
        vol.Required(CONF_RECONNECT_DELAY_MAX, default=1.0): vol.Coerce(float),
    }
)


# needs to be async, probably a bug in HA
async def next_step(user_input):
    return user_input.get(CONF_MODE)


CONFIG_FLOW: Mapping[str, SchemaFlowStep] = {
    "user": SchemaFlowFormStep(next_step="common"),
    "reconfigure": SchemaFlowFormStep(next_step="common"),
    "common": SchemaFlowFormStep(schema=COMMON_SCHEMA, next_step=next_step),
    "serial": SchemaFlowFormStep(schema=SERIAL_SCHEMA, next_step="modbus"),
    "tcp": SchemaFlowFormStep(schema=TCP_SCHEMA, next_step="modbus"),
    "udp": SchemaFlowFormStep(schema=UDP_SCHEMA, next_step="modbus"),
    "modbus": SchemaFlowFormStep(schema=MODBUS_SCHEMA),
}

# OPTIONS_FLOW: Mapping[str, SchemaFlowStep] = {
#     "init": SchemaFlowFormStep(next_step="common"),
#     **CONFIG_FLOW,
# }


class MustInverterConfigFlow(SchemaConfigFlowHandler, domain=DOMAIN):
    """Handle a config flow for Must Inverter."""

    config_flow = CONFIG_FLOW
    # We'll use reconfigure feature for now
    # options_flow = OPTIONS_FLOW

    def async_config_entry_title(self, options: Mapping[str, Any]) -> str:
        """Return config entry title."""
        return f"Must Inverter"
