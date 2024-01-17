import logging

import voluptuous as vol
from typing import Any
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
DEVICE_UNIQUE_ID = "must_inverter"

SERIAL_SCHEMA =vol.Schema({
    vol.Required("device"): str,
    vol.Required("baudrate", default=19200): int,
    vol.Required("parity", default="N"): str,
    vol.Required("stopbits", default=1): int,
    vol.Required("bytesize", default=8): int,
})

TCP_SCHEMA =vol.Schema({
    vol.Required("host"): str,
    vol.Required("port", default=502): int,
})

UDP_SCHEMA =vol.Schema({
    vol.Required("host"): str,
    vol.Required("port", default=502): int,
})

COMMON_SCHEMA = vol.Schema({
    vol.Required("timeout", default=2.0): vol.Coerce(float),
    vol.Required("retries", default=3): int,
    vol.Required("reconnect_delay", default=0.3): vol.Coerce(float),
    vol.Required("reconnect_delay_max", default=1.0): vol.Coerce(float),
})

class MustInverterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Must Inverter config flow."""
    # The schema version of the entries that it creates
    # Home Assistant will call your migrate method if the version changes
    VERSION = 1
    MINOR_VERSION = 1

    data = {}

    async def async_step_user(self, info: dict[str, Any] | None = None) -> FlowResult:
        _LOGGER.debug("async_step_user: %s", info)

        await self.async_set_unique_id(DEVICE_UNIQUE_ID)
        self._abort_if_unique_id_configured()

        return self.async_show_menu(
            step_id="user",
            menu_options=["serial", "tcp", "udp"]
        )

    async def async_step_common(self, info: dict[str, Any] | None = None) -> FlowResult:
        _LOGGER.debug("async_step_common: %s", info)

        if info is not None:
            self.data.update(info)
            return await self.async_step_finish()

        return self.async_show_form(step_id="common", data_schema=COMMON_SCHEMA, last_step=True)

    async def async_step_finish(self, info: dict[str, Any] | None = None) -> FlowResult:
        _LOGGER.debug("async_step_finish: %s", info)
        return self.async_create_entry(title="Must Inverter", data=self.data)

    async def async_step_serial(self, info: dict[str, Any] | None = None) -> FlowResult:
        if info is not None:
            self.data.update(info)
            self.data["mode"] = "serial"
            return await self.async_step_common()

        return self.async_show_form(step_id="serial", data_schema=SERIAL_SCHEMA)

    async def async_step_tcp(self, info: dict[str, Any] | None = None) -> FlowResult:
        if info is not None:
            self.data.update(info)
            self.data["mode"] = "tcp"
            return await self.async_step_common()

        return self.async_show_form(step_id="tcp", data_schema=TCP_SCHEMA)

    async def async_step_udp(self, info: dict[str, Any] | None = None) -> FlowResult:
        if info is not None:
            self.data.update(info)
            self.data["mode"] = "udp"
            return await self.async_step_common()

        return self.async_show_form(step_id="udp", data_schema=UDP_SCHEMA)