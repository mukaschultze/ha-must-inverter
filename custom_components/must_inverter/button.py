import logging
from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.const import Platform

from .const import DOMAIN, Sensor
from .__init__ import MustInverter

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    inverter_data = hass.data[DOMAIN][entry.entry_id]
    inverter = inverter_data["inverter"]
    sensors = inverter_data["sensors"]
    entities = []

    for sensor_info in sensors:
        if sensor_info.platform == Platform.BUTTON:
            sensor = MustInverterButton(inverter, sensor_info)
            entities.append(sensor)

    async_add_entities(entities)
    return True


class MustInverterButton(ButtonEntity):
    def __init__(self, inverter: MustInverter, sensor_info: Sensor):
        """Initialize the button."""
        self._inverter = inverter
        self._key = sensor_info.name
        self._address = sensor_info.address

        self._attr_has_entity_name = True
        self._attr_unique_id = f"{self._inverter.data['InverterSerialNumber']}_{self._key}"
        self._attr_translation_key = self._key.lower()
        self._attr_device_class = sensor_info.device_class
        self._attr_entity_registry_enabled_default = sensor_info.enabled

    async def async_press(self):
        await self._inverter.write_modbus_data(self._address, 1)

    @property
    def device_info(self) -> dict[str, Any] | None:
        return self._inverter._device_info()

    @property
    def available(self) -> dict[str, Any] | None:
        return True
        # return self._key in self._inverter.data
