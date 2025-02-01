import asyncio
import logging
import re
from collections import namedtuple
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import Platform
from homeassistant.core import callback

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# This lock is used to prevent concurrent writes to the system settings.
_system_settings_lock = asyncio.Lock()


async def async_setup_entry(hass, entry, async_add_entities):
    Setting = namedtuple("Setting", ["bit", "name", "flip", "enabled", "icon"])

    # fmt: off
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
    # fmt: on

    inverter_data = hass.data[DOMAIN][entry.entry_id]
    inverter = inverter_data["inverter"]
    sensors = inverter_data["sensors"]
    entities = []

    for setting in settings:
        entities.append(MustInverterSettingsSwitch(inverter, setting))

    for sensor_info in sensors:
        if sensor_info.platform == Platform.SWITCH:
            sensor = MustInverterSwitch(inverter, sensor_info)
            entities.append(sensor)

    async_add_entities(entities)
    return True


class MustInverterSwitch(SwitchEntity):
    def __init__(self, inverter, sensor_info):
        """Initialize the sensor."""
        self._inverter = inverter
        self._key = sensor_info.name
        self._address = sensor_info.address

        self._attr_has_entity_name = True
        self._attr_unique_id = f"{self._inverter._model}_{self._inverter.data['InverterSerialNumber']}_{self._key}"
        self._attr_name = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", self._key)
        self._attr_device_class = sensor_info.device_class
        self._attr_entity_registry_enabled_default = sensor_info.enabled
        self._attr_icon = sensor_info.icon

    async def async_added_to_hass(self):
        self._inverter.async_add_must_inverter_sensor(self._inverter_data_updated)

    async def async_will_remove_from_hass(self) -> None:
        self._inverter.async_remove_must_inverter_sensor(self._inverter_data_updated)

    @callback
    def _inverter_data_updated(self):
        self.async_write_ha_state()

    @property
    def is_on(self):
        if self._key in self._inverter.data:
            return self._inverter.data[self._key] == 1

    async def _async_set_value(self, set):
        value = set and 1 or 0
        await self._inverter.write_modbus_data(self._address, value)
        if self._key in self._inverter.data:
            self._inverter.data[self._key] = value  # optmiistic update

    async def async_turn_on(self, **kwargs):
        return await self._async_set_value(True)

    async def async_turn_off(self, **kwargs):
        return await self._async_set_value(False)

    @property
    def device_info(self) -> dict[str, Any] | None:
        return self._inverter._device_info()

    @property
    def available(self) -> dict[str, Any] | None:
        return self._key in self._inverter.data


class MustInverterSettingsSwitch(SwitchEntity):
    def __init__(self, inverter, setting_config):
        """Initialize the sensor."""
        self._inverter = inverter
        self._name = setting_config.name
        self._bit = setting_config.bit
        self._flip = setting_config.flip

        self._attr_has_entity_name = True
        self._attr_unique_id = f"{self._inverter._model}_{self._inverter.data['InverterSerialNumber']}_{self._name}"
        self._attr_name = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", self._name)
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
        set = current_settings & (1 << self._bit) != 0
        return set != self._flip

    async def _async_set_value(self, set):
        KEY = "SystemSetting"
        ADDRESS = 20142

        if KEY not in self._inverter.data:
            return None

        async with _system_settings_lock:
            current_settings = self._inverter.data[KEY]

            if self._flip:
                set = not set

            if set:
                new_value = current_settings | (1 << self._bit)
            else:
                new_value = current_settings & ~(1 << self._bit)

            await self._inverter.write_modbus_data(ADDRESS, int(new_value))
            self._inverter.data[KEY] = new_value  # optmiistic update

    async def async_turn_on(self, **kwargs):
        return await self._async_set_value(True)

    async def async_turn_off(self, **kwargs):
        return await self._async_set_value(False)

    @property
    def device_info(self) -> dict[str, Any] | None:
        return self._inverter._device_info()

    @property
    def available(self) -> dict[str, Any] | None:
        return "SystemSetting" in self._inverter.data
