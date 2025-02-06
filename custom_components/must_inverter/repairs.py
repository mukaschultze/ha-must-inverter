from __future__ import annotations

import voluptuous as vol
import time

from homeassistant import data_entry_flow
from homeassistant.components.repairs import RepairsFlow
from homeassistant.core import HomeAssistant

from .__init__ import MustInverter
from .const import DOMAIN


class NoSerialNumber(RepairsFlow):
    """Handler for an issue fixing flow."""

    def __init__(self, hass: HomeAssistant, data: dict[str, str | int | float | None] | None) -> None:
        """Initialize the flow."""
        self._hass = hass
        self._data = data

    async def async_step_init(self, user_input: dict[str, str] | None = None) -> data_entry_flow.FlowResult:
        """Handle the first step of a fix flow."""
        return await self.async_step_confirm()

    async def async_step_confirm(self, user_input: dict[str, str] | None = None) -> data_entry_flow.FlowResult:
        """Handle the confirm step of a fix flow."""
        if user_input is not None:
            entry_id = self._data["entry_id"]
            device: MustInverter = self._hass.data[DOMAIN][entry_id]["inverter"]
            new_serial_number = user_input["new_serial"]

            lower = new_serial_number & 0xFFFF
            upper = (new_serial_number >> 16) & 0xFFFF

            await device.write_modbus_data(20002, upper)
            await device.write_modbus_data(20003, lower)

            self._hass.config_entries.async_schedule_reload(entry_id)

            return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema(
                {
                    vol.Required("new_serial", default=int(time.time())): int,
                }
            ),
        )


async def async_create_fix_flow(
    hass: HomeAssistant,
    issue_id: str,
    data: dict[str, str | int | float | None] | None,
) -> RepairsFlow:
    """Create flow."""
    if issue_id == "no_serial_number":
        return NoSerialNumber(hass, data)
