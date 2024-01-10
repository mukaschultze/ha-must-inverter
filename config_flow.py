from homeassistant import config_entries
import voluptuous as vol
from .const import DOMAIN
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)
from .const import (
    CONF_DEVICE,
)

class MustInverterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Must Inverter config flow."""
    # The schema version of the entries that it creates
    # Home Assistant will call your migrate method if the version changes
    VERSION = 1
    MINOR_VERSION = 1
    
    async def async_step_user(self, info):
        if info is not None:
            return self.async_create_entry(title="Must Inverter", data=info)

        return self.async_show_form(
            step_id="user", data_schema=vol.Schema({vol.Required(CONF_DEVICE): str})
        )