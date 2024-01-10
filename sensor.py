import logging
import re
from typing import Any, Dict, Optional

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.const import Platform, UnitOfEnergy
from homeassistant.core import callback

from .const import DOMAIN, SENSORS_ARRAY

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    entry_id = entry.entry_id

    inverter_name = "must_inverter_name"
    inverter = hass.data[DOMAIN][inverter_name]

    entities = []
    
    for sensor_info in SENSORS_ARRAY:
        if sensor_info.platform == Platform.SENSOR:
            sensor = MustInverterSensor(inverter, entry_id, sensor_info)
            entities.append(sensor)

    async_add_entities(entities)
    return True

class MustInverterSensor(SensorEntity):
    def __init__(self, inverter, entry_id, sensor_info):
        """Initialize the sensor."""
        self._inverter = inverter
        self._key = sensor_info.name

        self._attr_has_entity_name = True
        self._attr_unique_id = self._key
        self._attr_name = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', self._key).capitalize()
        self._attr_native_unit_of_measurement = sensor_info.unit
        self._attr_device_class = sensor_info.device_class
        self._attr_entity_registry_enabled_default = sensor_info.enabled
        self._attr_icon = sensor_info.icon
        self._attr_options = sensor_info.options

        if self._attr_native_unit_of_measurement == UnitOfEnergy.KILO_WATT_HOUR:
            self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        elif self._attr_options is None:
            self._attr_state_class = SensorStateClass.MEASUREMENT

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
            if self._attr_options is not None:
                return self._attr_options[self._inverter.data[self._key]]
            else:
                return self._inverter.data[self._key]

    @property
    def device_info(self) -> Optional[Dict[str, Any]]:
        return self._inverter._device_info()