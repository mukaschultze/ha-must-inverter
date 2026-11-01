"""The Must Inverter integration."""

import asyncio
import logging
import contextlib

from datetime import timedelta

from homeassistant.components.modbus import async_get_unit
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryError, ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.event import async_track_time_interval
from modbus_connection import ModbusConnectionError, ModbusError, ModbusTimeoutError

from homeassistant.const import (
    CONF_NAME,
    CONF_MODEL,
    CONF_SCAN_INTERVAL,
    CONF_TIMEOUT,
)

from .connection import create_modbus_params
from .const import (
    DOMAIN,
    CONF_BYTESIZE,
    CONF_PARITY,
    CONF_STOPBITS,
    CONF_DEVICE_ID,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_DEVICE_ID,
    DEFAULT_STOPBITS,
    DEFAULT_TIMEOUT,
    LEGACY_OPTIONS,
    get_sensors_for_model,
    MODEL_PV1900,
    MODEL_PH1100,
)

from .mapper import (
    convert_ph1100_partArr1,
    convert_ph1100_partArr2,
    convert_ph1100_partArr3,
    convert_ph1100_partArr4,
    convert_partArr2,
    convert_partArr3,
    convert_partArr4,
    convert_partArr5,
    convert_partArr6,
    convert_battery_status,
    convert_pv_data,
)
# from .utils.register_monitor import RegisterMonitor

PLATFORMS = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SWITCH,
    Platform.BUTTON,
    Platform.TIME,
]
_LOGGER = logging.getLogger(__name__)


async def async_setup(hass, config):
    hass.data[DOMAIN] = {}
    return True  # Return boolean to indicate that initialization was successful.


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the must inverter component."""
    try:
        entry.async_on_unload(entry.add_update_listener(async_reload_entry))

        # Initialize inverter with model-specific sensors
        try:
            inverter = MustInverter(hass, entry)
        except HomeAssistantError as ex:
            # Another integration holds the same port with different link settings
            raise ConfigEntryError(str(ex)) from ex

        # The shared connection is opened on demand by the first read
        successReading = await inverter._async_refresh_modbus_data()

        if not successReading:
            raise ConfigEntryNotReady("Unable to read from modbus device")

        model = inverter.model
        sensors = get_sensors_for_model(model)
        _LOGGER.debug("Setting up Must Inverter with model: %s", model)

        # Store sensors to be used by platforms
        hass.data[DOMAIN][entry.entry_id] = {"inverter": inverter, "sensors": sensors}

        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

        # Removing register monitor as we've found all needed registers
        # If you need to add it back, uncomment the following lines and set the ranges to scan in register_monitor.py
        # monitor = RegisterMonitor(hass)

        # Add monitoring to the update cycle, but at a slower rate
        # async def delayed_monitor():
        #     """Run monitor at a slower rate to avoid overwhelming the device."""
        #     try:
        #         while True:
        #             await monitor.scan_ranges(inverter)
        #             await asyncio.sleep(300)  # Run every 5 minutes
        #     except asyncio.CancelledError:
        #         _LOGGER.debug("Register monitor task cancelled")
        #         raise

        # monitor_task = asyncio.create_task(delayed_monitor())

        # Store the task so we can cancel it later
        # hass.data[DOMAIN][entry.entry_id]["monitor_task"] = monitor_task

        return True
    except (ConfigEntryNotReady, ConfigEntryError) as ex:
        raise ex
    except Exception as ex:
        _LOGGER.exception("Error setting up modbus device", exc_info=True)
        raise ConfigEntryNotReady("Unknown error connecting to modbus device") from ex


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        # Cancel the monitor task
        if monitor_task := hass.data[DOMAIN][entry.entry_id].get("monitor_task"):
            monitor_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await monitor_task

        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update listener, called when the config entry options are changed."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate old config entries."""
    if entry.version > 1:
        return False

    if entry.minor_version < 2:
        # 1.2 moved from pymodbus to Home Assistant's shared modbus connections:
        # retries and reconnect delays are no longer configurable, and the serial
        # framing settings are stored as the string values of their select fields
        options = {k: v for k, v in entry.options.items() if k not in LEGACY_OPTIONS}

        if CONF_PARITY in options:
            options[CONF_PARITY] = str(options[CONF_PARITY]).lower()
        if CONF_BYTESIZE in options:
            options[CONF_BYTESIZE] = str(int(options[CONF_BYTESIZE]))
        if CONF_STOPBITS in options:
            stopbits = options[CONF_STOPBITS]
            if stopbits not in (1, 2, "1", "2"):
                _LOGGER.warning("unsupported stop bits %s, falling back to %s", stopbits, DEFAULT_STOPBITS)
                stopbits = DEFAULT_STOPBITS
            options[CONF_STOPBITS] = str(stopbits)

        hass.config_entries.async_update_entry(entry, options=options, minor_version=2)
        _LOGGER.debug("migrated config entry %s to version 1.2", entry.entry_id)

    return True


class MustInverter:
    def __init__(self, hass, entry: ConfigEntry):
        self._hass = hass
        self._callbacks = []  # Store callbacks separately
        self._entry = entry

        # The connection is owned by the modbus integration and shared with any
        # other integration talking to the same port. It connects on demand,
        # reconnects by itself and is closed once the last entry using it unloads.
        self._device_id = entry.options.get(CONF_DEVICE_ID, DEFAULT_DEVICE_ID)
        self._unit = async_get_unit(hass, entry, create_modbus_params(entry.options), self._device_id)
        self._unit.require_timeout(entry.options.get(CONF_TIMEOUT, DEFAULT_TIMEOUT))
        self._scan_interval = timedelta(seconds=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))
        self._reading = False
        self.registers = {}
        self.data = {}

    @callback
    def async_add_must_inverter_sensor(self, update_callback):
        # This is the first sensor, set up interval.
        if not self._callbacks:
            self._unsub_interval_method = async_track_time_interval(
                self._hass, self._async_refresh_modbus_data, self._scan_interval
            )

        self._callbacks.append(update_callback)

    @callback
    def async_remove_must_inverter_sensor(self, update_callback):
        self._callbacks.remove(update_callback)

        if not self._callbacks:
            """stop the interval timer upon removal of last sensor"""
            self._unsub_interval_method()
            self._unsub_interval_method = None

    async def _async_refresh_modbus_data(self, now=None):
        try:
            update_result = await self.read_modbus_data()

            if update_result:
                for update_callback in self._callbacks:
                    update_callback()
        except ConfigEntryNotReady as ex:
            _LOGGER.warning("modbus connection not ready: %s", ex)
            update_result = False
        except Exception:
            _LOGGER.exception("error reading inverter data", exc_info=True)
            update_result = False

        return update_result

    @property
    def name(self):
        return self._entry.options.get(CONF_NAME, self.data.get("InverterMachineType", self.model))

    @property
    def model(self):
        from_config = self._entry.options.get(CONF_MODEL)
        detected = self.data.get("InverterMachineType")

        if from_config == "autodetect":
            return detected

        return from_config or detected

    @property
    def has_extra_registers(self):
        return self.model == MODEL_PV1900

    async def write_modbus_data(self, address, value):
        _LOGGER.debug("writing modbus data: %s %s", address, value)

        try:
            await self._unit.write_register(address, value)
        except ModbusError as ex:
            _LOGGER.error("error writing modbus data at address %s: %s", address, ex)
            raise HomeAssistantError(f"Error writing {value} to register {address}: {ex}") from ex

        _LOGGER.debug("successfully wrote modbus data: %s %s", address, value)

    async def read_modbus_data(self):
        _LOGGER.debug("reading modbus data")

        if self._reading:
            _LOGGER.warning(
                "skipping reading modbus data, previous read still in progress, make sure your scan interval is not too low"
            )
            return False
        self._reading = True

        # Reading all the control messages at once (ranges 20016-20100 and/or
        # 10009-10100 are problematic) causes the inverter to shut down
        # immediately and the charger stops working afterwards (all registers
        # return zeroes). Requires the grid/batteries/PV to be disconnected and
        # the inverter restarted for it to come back online.
        if self.model == MODEL_PH1100:
            registersAddresses = [
                (10102, 10119, convert_ph1100_partArr1),  # Charger Control Messages
                (15104, 15119, convert_ph1100_partArr2),  # Charger Display Messages
                (20001, 20003, convert_ph1100_partArr3),  # Inverter Control Messages
                (25225, 25339, convert_ph1100_partArr4),  # Inverter Display Messages
            ]
        else:
            # Base register ranges for all models
            registersAddresses = [
                # (10000, 10008, convert_partArr1), # Charger Control Messages
                (10101, 10124, convert_partArr2),  # Charger Control Messages
                (15201, 15221, convert_partArr3),  # Charger Display Messages
                (20000, 20016, convert_partArr4),  # Inverter Control Messages
                (20101, 20214, convert_partArr5),  # Inverter Control Messages
                (25201, 25279, convert_partArr6),  # Inverter Display Messages
            ]

            # Add PV19-specific register ranges if needed
            # Keep register ranges for pv separate to not overload the inverter
            if self.has_extra_registers:
                registersAddresses.extend(
                    [
                        (113, 114, convert_battery_status),  # Battery Status (SoC, SoH)
                        (15207, 15208, convert_pv_data),  # PV1 Data (Current, Power)
                        (16205, 16208, convert_pv_data),  # PV2 Data (Voltage, Current, Power)
                    ]
                )

        read = {}

        try:
            for register in registersAddresses:
                if self.has_extra_registers:
                    # Add a small delay between reading standard and PV19-specific registers
                    # to prevent any potential issues
                    await asyncio.sleep(0.1)

                start = register[0]
                end = register[1]
                count = end - start + 1

                try:
                    _LOGGER.debug("reading modbus data from %s to %s (%s)", start, end, count)

                    registers = await self._unit.read_holding_registers(start, count)

                    if len(registers) != count:
                        _LOGGER.warning(
                            "wrong number of registers read at address %s, expected %s, got %s - this usually is caused by concurrent access to modbus (usb/wifi/rs485), please remove other devices",
                            start,
                            count,
                            len(registers),
                        )
                        # Log the actual values received
                        _LOGGER.debug("Received registers (wrong): %s", registers)

                        ir.async_create_issue(
                            self._hass,
                            DOMAIN,
                            "mismatched_registers",
                            is_fixable=False,
                            severity=ir.IssueSeverity.ERROR,
                            translation_key="mismatched_registers",
                            is_persistent=False,
                            learn_more_url="https://github.com/mukaschultze/ha-must-inverter/issues/47",
                        )
                    else:
                        _LOGGER.debug("Correctly read %s registers from start %s", count, start)
                        for i in range(count):
                            read[start + i] = registers[i]
                        self.data.update(register[2](read))
                except asyncio.exceptions.CancelledError:
                    _LOGGER.warning("cancelled modbus read")
                    raise
                except (ModbusConnectionError, ModbusTimeoutError) as ex:
                    # The link is down or the inverter is not answering, the
                    # remaining ranges would fail the same way. The connection
                    # is re-established by the next poll.
                    _LOGGER.warning("unable to read modbus data at address %s: %s", start, ex)
                    return False
                except ModbusError as ex:
                    _LOGGER.error("error reading modbus data at address %s: %s", start, ex)
                except ConfigEntryNotReady:
                    # Raised while the ESPHome integration providing a serial proxy has not loaded yet
                    raise
                except Exception:
                    _LOGGER.error("error reading modbus data at address %s", start, exc_info=True)
        finally:
            self._reading = False

        _LOGGER.debug("finished reading modbus data, %s", read)
        self.registers = read
        # _LOGGER.debug("Data: %s", self.data)

        if self.data["InverterSerialNumber"] == 0xFFFFFFFF or self.data["InverterSerialNumber"] == 0:
            ir.async_create_issue(
                self._hass,
                DOMAIN,
                "no_serial_number",
                is_fixable=True,
                severity=ir.IssueSeverity.WARNING,
                translation_key="no_serial_number",
                data={"entry_id": self._entry.entry_id},
            )

        return True

    def _device_info(self):
        return {
            "identifiers": {(DOMAIN, self.data["InverterSerialNumber"])},
            "name": self.name,
            "manufacturer": "Must Solar",
            "model": self.data.get("InverterMachineType", self.model),
            "hw_version": self.data.get("InverterHardwareVersion"),
            "sw_version": self.data.get("InverterSoftwareVersion"),
            "serial_number": self.data["InverterSerialNumber"],
        }
