import logging
import re
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.const import Platform
from homeassistant.core import callback

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    inverter_data = hass.data[DOMAIN][entry.entry_id]
    inverter = inverter_data["inverter"]
    sensors = inverter_data["sensors"]
    entities = []

    for sensor_info in sensors:
        if sensor_info.platform == Platform.BINARY_SENSOR:
            sensor = MustInverterBinarySensor(inverter, sensor_info)
            entities.append(sensor)

    async_add_entities(entities)
    return True


class MustInverterBinarySensor(BinarySensorEntity):
    def __init__(self, inverter, sensor_info):
        """Initialize the binary sensor."""
        self._inverter = inverter
        self._key = sensor_info.name

        self._attr_has_entity_name = True
        self._attr_unique_id = f"{self._inverter._model}_{self._inverter.data['InverterSerialNumber']}_{self._key}"
        self._attr_translation_key = self._key
        self._attr_device_class = sensor_info.device_class
        self._attr_entity_registry_enabled_default = sensor_info.enabled

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

    @property
    def device_info(self) -> dict[str, Any] | None:
        return self._inverter._device_info()

    @property
    def available(self) -> dict[str, Any] | None:
        return self._key in self._inverter.data
