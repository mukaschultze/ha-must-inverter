from __future__ import annotations

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er

from .const import DOMAIN
from .__init__ import MustInverter

# Add more fields that might contain sensitive information
TO_REDACT = {
    "host",
    "port",
    "serial_number",
    "InverterSerialNumber",
    "mac_address",
    "unique_id",
    "identifiers",
}

TO_REDACT_DEV = {
    "serial_number",
    "identifiers",
}

async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict:
    """Return diagnostics for a config entry."""
    diag_data = {
        "entry": async_redact_data(entry.as_dict(), TO_REDACT),
        "entry_id": entry.entry_id,
        "version": entry.version,
        "minor_version": entry.minor_version,
    }

    # Get device data
    devs_data = _async_devices_as_dict(hass, entry)
    diag_data["devices"] = devs_data

    return diag_data

@callback
def _async_devices_as_dict(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict:
    """Gather device information."""
    devs_data = {}
    device: MustInverter = hass.data[DOMAIN].get(entry.entry_id, {})
    
    if not device:
        return {"error": "No device data found"}

    device_info = device._device_info()
    
    devs_data[entry.entry_id] = {
        "model": device._model,
        "device_info": async_redact_data(device_info, TO_REDACT_DEV),
        "data": async_redact_data(device.data, TO_REDACT),
        "registers": device.registers,
        "home_assistant": _async_device_ha_info(hass, device_info["identifiers"]),
    }

    return devs_data

@callback
def _async_device_ha_info(hass: HomeAssistant, identifiers: set[tuple[str, str]]) -> dict | None:
    """Gather information how this device is represented in Home Assistant."""

    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)
    hass_device = device_registry.async_get_device(identifiers)
    if not hass_device:
        return None

    data = {
        "name": hass_device.name,
        "name_by_user": hass_device.name_by_user,
        "model": hass_device.model,
        "manufacturer": hass_device.manufacturer,
        "sw_version": hass_device.sw_version,
        "hw_version": hass_device.hw_version,
        "disabled": hass_device.disabled,
        "disabled_by": hass_device.disabled_by,
        "entities": {},
    }

    hass_entities = er.async_entries_for_device(
        entity_registry,
        device_id=hass_device.id,
        include_disabled_entities=True,
    )

    for entity_entry in hass_entities:
        if entity_entry.platform != DOMAIN:
            continue
        
        state = hass.states.get(entity_entry.entity_id)
        state_dict = None
        if state:
            state_dict = dict(state.as_dict())
            # Remove redundant or sensitive information
            state_dict.pop("entity_id", None)
            state_dict.pop("context", None)

        data["entities"][entity_entry.entity_id] = {
            "name": entity_entry.name,
            "original_name": entity_entry.original_name,
            "disabled": entity_entry.disabled,
            "disabled_by": entity_entry.disabled_by,
            "entity_category": entity_entry.entity_category,
            "device_class": entity_entry.device_class,
            "original_device_class": entity_entry.original_device_class,
            "icon": entity_entry.icon,
            "original_icon": entity_entry.original_icon,
            "unit_of_measurement": entity_entry.unit_of_measurement,
            "state": state_dict,
        }

    return data
