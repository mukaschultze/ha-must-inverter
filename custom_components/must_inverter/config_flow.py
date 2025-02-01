import logging
from collections.abc import Mapping

import voluptuous as vol
from typing import Any
from homeassistant.helpers.schema_config_entry_flow import (
    SchemaConfigFlowHandler,
    SchemaFlowFormStep,
    SchemaFlowMenuStep,
    SchemaCommonFlowHandler,
)

from .const import DOMAIN, DEFAULT_SCAN_INTERVAL, MODEL_PV1800, SUPPORTED_MODELS

_LOGGER = logging.getLogger(__name__)
DEVICE_UNIQUE_ID = "must_inverter"

SERIAL_SCHEMA = vol.Schema(
    {
        vol.Required("device", default="/dev/ttyUSB0"): str,
        vol.Required("baudrate", default=19200): int,
        vol.Required("parity", default="N"): str,
        vol.Required("stopbits", default=1): int,
        vol.Required("bytesize", default=8): int,
        vol.Required("model", default=MODEL_PV1800): vol.In(SUPPORTED_MODELS),
    }
)

TCP_SCHEMA = vol.Schema(
    {
        vol.Required("host"): str,
        vol.Required("port", default=502): int,
        vol.Required("model", default=MODEL_PV1800): vol.In(SUPPORTED_MODELS),
    }
)

UDP_SCHEMA = vol.Schema(
    {
        vol.Required("host"): str,
        vol.Required("port", default=502): int,
        vol.Required("model", default=MODEL_PV1800): vol.In(SUPPORTED_MODELS),
    }
)

COMMON_SCHEMA = vol.Schema(
    {
        vol.Required("scan_interval", default=DEFAULT_SCAN_INTERVAL): vol.Coerce(float),
        vol.Required("timeout", default=2.0): vol.Coerce(float),
        vol.Required("retries", default=3): int,
        vol.Required("reconnect_delay", default=0.3): vol.Coerce(float),
        vol.Required("reconnect_delay_max", default=1.0): vol.Coerce(float),
    }
)


async def validate_serial_config(handler: SchemaCommonFlowHandler, user_input: dict[str, Any]) -> dict[str, Any]:
    user_input["mode"] = "serial"
    return user_input


async def validate_tcp_config(handler: SchemaCommonFlowHandler, user_input: dict[str, Any]) -> dict[str, Any]:
    user_input["mode"] = "tcp"
    return user_input


async def validate_udp_config(handler: SchemaCommonFlowHandler, user_input: dict[str, Any]) -> dict[str, Any]:
    user_input["mode"] = "udp"
    return user_input


CONFIG_FLOW = {
    "user": SchemaFlowMenuStep(["serial", "tcp", "udp"]),
    "serial": SchemaFlowFormStep(
        schema=SERIAL_SCHEMA,
        next_step="common",
        validate_user_input=validate_serial_config,
    ),
    "tcp": SchemaFlowFormStep(
        schema=TCP_SCHEMA,
        next_step="common",
        validate_user_input=validate_tcp_config,
    ),
    "udp": SchemaFlowFormStep(
        schema=UDP_SCHEMA,
        validate_user_input=validate_udp_config,
        next_step="common",
    ),
    "common": SchemaFlowFormStep(
        schema=COMMON_SCHEMA,
    ),
}

OPTIONS_FLOW = {
    "init": CONFIG_FLOW["user"],
    **CONFIG_FLOW,
}


class MustInverterConfigFlow(SchemaConfigFlowHandler, domain=DOMAIN):
    """Handle a config flow for Must Inverter."""

    config_flow = CONFIG_FLOW
    options_flow = OPTIONS_FLOW

    def async_config_entry_title(self, options: Mapping[str, Any]) -> str:
        """Return config entry title."""
        return f"Must Inverter ({options.get('model', MODEL_PV1800)})"
