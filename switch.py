import asyncio
import logging
import re
from collections import namedtuple
from typing import Any, Dict, Optional

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import callback

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# This lock is used to prevent concurrent writes to the system settings.
_system_settings_lock = asyncio.Lock()

async def async_setup_entry(hass, entry, async_add_entities):
    entry_id = entry.entry_id

    inverter_name = "must_inverter_name"
    inverter = hass.data[DOMAIN][inverter_name]

    Setting = namedtuple('Setting', ['bit', 'name', 'flip', 'enabled', 'icon'])

    settings = [
        Setting(0, "OverLoadRestart",  True,  True,  'mdi:restart-alert'),
        Setting(1, "OverTempRestart",  True,  True,  'mdi:thermometer-alert'),
        Setting(2, "OverLoadBypass",   True,  True,  'mdi:transmission-tower-off'),
        Setting(3, "AutoTurnPage",     True,  True,  'mdi:book-open-page-variant'),
        Setting(4, "GridBuzz",         False, True,  'mdi:bell-alert'),
        Setting(5, "Buzz",             True,  True,  'mdi:bell'),
        Setting(6, "LcdLight",         False, True,  'mdi:lightbulb'),
        Setting(7, "RecordFault",      True,  True,  'mdi:alert'),
    ]

    entities = []

    for setting in settings:
        entities.append(MustInverterSettingsSwitch(inverter, entry_id, setting))

    async_add_entities(entities)
    return True

class MustInverterSettingsSwitch(SwitchEntity):
    def __init__(self, inverter, entry_id, setting_config):
        """Initialize the sensor."""
        self._inverter = inverter
        self._identifier = self._inverter.data["InverterMachineType"]
        self._name = setting_config.name
        self._bit = setting_config.bit
        self._flip = setting_config.flip

        self._attr_has_entity_name = True
        self._attr_unique_id = self._name
        self._attr_name = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', self._name).capitalize()
        # self._attr_device_class = sensor_info.device_class
        self._attr_entity_registry_enabled_default = setting_config.enabled
        self._attr_icon = setting_config.icon

    async def async_added_to_hass(self):
        self._inverter.async_add_must_inverter_sensor(self._inverter_data_updated)

    async def async_will_remove_from_hass(self) -> None:
        self._inverter.async_remove_must_inverter_sensor(self._inverter_data_updated)

    @callback
    def _inverter_data_updated(self):
        self.async_write_ha_state()

    @property
    def is_on(self):
        if "SystemSetting" not in self._inverter.data:
            return None
        
        current_settings = self._inverter.data["SystemSetting"]
        set = (current_settings & (1 << self._bit) != 0)
        return set != self._flip

    @property
    def device_info(self) -> Optional[Dict[str, Any]]:
        device_info = {
            "identifiers": {(DOMAIN, self._identifier)},
            "name": self._inverter.data["InverterMachineType"],
            "model": self._inverter.data["InverterMachineType"],
            "manufacturer": "Must Solar",
            "hw_version": self._inverter.data["InverterHardwareVersion"],
            "sw_version": self._inverter.data["InverterSoftwareVersion"],
            "serial_number": self._inverter.data["InverterSerialNumber"],
        }
        return device_info
    
    async def _async_set_value(self, set):
        KEY = "SystemSetting"
        ADDRESS = 20142

        if KEY not in self._inverter.data:
            return None

        async with _system_settings_lock:
            current_settings = self._inverter.data[KEY]

            if(self._flip):
                set = not set

            if set:
               new_value = current_settings | (1 << self._bit)
            else:
               new_value = current_settings & ~(1 << self._bit)

            await self._inverter.write_modbus_data(ADDRESS, int(new_value))
            self._inverter.data[KEY] = new_value # optmiistic update
    
    async def async_turn_on(self, **kwargs):
        return await self._async_set_value(True)

    async def async_turn_off(self, **kwargs):
        return await self._async_set_value(False)
