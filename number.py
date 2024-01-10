import logging
import re
from typing import Any, Dict, Optional

from homeassistant.components.number import NumberEntity
from homeassistant.core import callback
from homeassistant.const import Platform

from .const import DOMAIN, SENSORS_ARRAY

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    entry_id = entry.entry_id

    inverter_name = "must_inverter_name"
    inverter = hass.data[DOMAIN][inverter_name]

    entities = []
    
    for sensor_info in SENSORS_ARRAY:
        if sensor_info.platform == Platform.NUMBER:
            sensor = MustInverterNumber(inverter, entry_id, sensor_info)
            entities.append(sensor)

    async_add_entities(entities)
    return True

class MustInverterNumber(NumberEntity):
    def __init__(self, inverter, entry_id, sensor_info):
        """Initialize the sensor."""
        self._inverter = inverter
        self._identifier = self._inverter.data["InverterMachineType"]
        self._key = sensor_info.name
        self._address = sensor_info.address
        self._coeff = sensor_info.coeff

        self._attr_has_entity_name = True
        self._attr_unique_id = self._key
        self._attr_name = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', self._key).capitalize()
        self._attr_device_class = sensor_info.device_class
        self._attr_entity_registry_enabled_default = sensor_info.enabled
        self._attr_icon = sensor_info.icon

        self._attr_native_min_value = sensor_info.min
        self._attr_native_max_value = sensor_info.max
        self._attr_native_step = sensor_info.step

    async def async_added_to_hass(self):
        self._inverter.async_add_must_inverter_sensor(self._inverter_data_updated)

    async def async_will_remove_from_hass(self) -> None:
        self._inverter.async_remove_must_inverter_sensor(self._inverter_data_updated)

    @callback
    def _inverter_data_updated(self):
        self.async_write_ha_state()

    @property
    def state(self):
        if self._key in self._inverter.data:
            return self._inverter.data[self._key]
    
    async def async_set_native_value(self, value: float) -> None:
        await self._inverter.write_modbus_data(self._address, int(value / self._coeff))
        if self._key in self._inverter.data:
            self._inverter.data[self._key] = value # optmiistic update

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
