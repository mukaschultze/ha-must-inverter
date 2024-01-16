import logging

import voluptuous as vol
from homeassistant import config_entries

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
DEVICE_UNIQUE_ID = "must_inverter"

SERIAL_SCHEMA =vol.Schema({
    vol.Required("device"): str,
})

TCP_SCHEMA =vol.Schema({
    vol.Required("host"): str,
    vol.Required("port", default=502): int,
})

UDP_SCHEMA =vol.Schema({
    vol.Required("host"): str,
    vol.Required("port", default=502): int,
})

class MustInverterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Must Inverter config flow."""
    # The schema version of the entries that it creates
    # Home Assistant will call your migrate method if the version changes
    VERSION = 1
    MINOR_VERSION = 1
    
    async def async_step_user(self, info):
        _LOGGER.debug("async_step_user: %s", info)

        await self.async_set_unique_id(DEVICE_UNIQUE_ID)
        self._abort_if_unique_id_configured()

        return self.async_show_menu(
            step_id="user",
            menu_options=["serial", "tcp", "udp"]
        )

    async def async_step_finish(self, info):
        _LOGGER.debug("async_step_finish: %s", info)

        if info is not None:
            return self.async_create_entry(title="Must Inverter", data=info)

        return None
    
    async def async_step_serial(self, info):
        if info is not None:
            return await self.async_step_finish({**info, 'mode': "serial"})
 
        return self.async_show_form(step_id="serial", data_schema=SERIAL_SCHEMA)
        
    async def async_step_tcp(self, info):
        if info is not None:
            return await self.async_step_finish({**info, 'mode': "tcp"})
 
        return self.async_show_form(step_id="tcp", data_schema=TCP_SCHEMA)
    
    async def async_step_udp(self, info):
        if info is not None:
            return await self.async_step_finish({**info, 'mode': "udp"})
 
        return self.async_show_form(step_id="udp", data_schema=UDP_SCHEMA)