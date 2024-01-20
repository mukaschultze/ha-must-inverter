import logging
import re
from typing import Any, Dict, Optional

from homeassistant.components.button import ButtonEntity
from homeassistant.const import Platform

from .const import DOMAIN, SENSORS_ARRAY

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    inverter = hass.data[DOMAIN]
    entities = []

    for sensor_info in SENSORS_ARRAY:
        if sensor_info.platform == Platform.BUTTON:
            sensor = MustInverterButton(inverter, sensor_info)
            entities.append(sensor)

    async_add_entities(entities)
    return True

class MustInverterButton(ButtonEntity):
    def __init__(self, inverter, sensor_info):
        """Initialize the sensor."""
        self._inverter = inverter
        self._key = sensor_info.name
        self._address = sensor_info.address

        self._attr_has_entity_name = True
        self._attr_unique_id = self._key
        self._attr_name = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', self._key).capitalize()
        self._attr_device_class = sensor_info.device_class
        self._attr_entity_registry_enabled_default = sensor_info.enabled
        self._attr_icon = sensor_info.icon

    async def async_press(self):
        await self._inverter.write_modbus_data(self._address, 1)

    @property
    def device_info(self) -> Optional[Dict[str, Any]]:
        return self._inverter._device_info()
