import asyncio
import logging
import contextlib

from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.event import async_track_time_interval
from pymodbus.client import AsyncModbusSerialClient, AsyncModbusTcpClient, AsyncModbusUdpClient

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, get_sensors_for_model, MODEL_PV1900
from .mapper import (
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
        inverter = MustInverter(hass, entry)

        successConnecting = await inverter.connect()

        if not successConnecting:
            raise ConfigEntryNotReady("Unable to connect to modbus device")

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
    except ConfigEntryNotReady as ex:
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


class MustInverter:
    def __init__(self, hass, entry: ConfigEntry):
        self._hass = hass
        self._callbacks = []  # Store callbacks separately
        self._entry = entry
        # Check both data and options

        common = {
            "timeout": entry.options["timeout"],
            "retries": entry.options["retries"],
            "reconnect_delay": entry.options["reconnect_delay"],
            "reconnect_delay_max": entry.options["reconnect_delay_max"],
        }

        match entry.options["mode"]:
            case "serial":
                self._client = AsyncModbusSerialClient(
                    entry.options["device"],
                    baudrate=entry.options["baudrate"],
                    stopbits=entry.options["stopbits"],
                    bytesize=entry.options["bytesize"],
                    parity=entry.options["parity"],
                    **common,
                )
            case "tcp":
                self._client = AsyncModbusTcpClient(entry.options["host"], port=entry.options["port"], **common)
            case "udp":
                self._client = AsyncModbusUdpClient(entry.options["host"], port=entry.options["port"], **common)
            case _:
                raise Exception("Invalid mode")

        self._client.rts = False
        self._client.dtr = False
        self._lock = asyncio.Lock()
        self._scan_interval = timedelta(seconds=entry.options.get("scan_interval", DEFAULT_SCAN_INTERVAL))
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
            self.close()

    async def _async_refresh_modbus_data(self, now=None):
        if not await self._check_and_reopen():
            # if not connected, skip
            _LOGGER.warning("not connected, skipping refresh")
            return False

        try:
            update_result = await self.read_modbus_data()

            if update_result:
                for update_callback in self._callbacks:
                    update_callback()
        except Exception:
            _LOGGER.exception("error reading inverter data", exc_info=True)
            update_result = False

        return update_result

    @property
    def model(self):
        from_config = self._entry.data.get("model") or self._entry.options.get("model")
        detected = self.data.get("InverterMachineType")

        return from_config or detected

    @property
    def has_extra_registers(self):
        return self.model == MODEL_PV1900

    def close(self):
        _LOGGER.info("closing modbus client")
        self._client.close()

    async def _check_and_reopen(self):
        if not self._client.connected:
            _LOGGER.info("modbus client is not connected, trying to reconnect")
            return await self.connect()

        return self._client.connected

    async def connect(self):
        result = False

        _LOGGER.debug("connecting to %s:%s", self._client.comm_params.host, self._client.comm_params.port)

        async with self._lock:
            result = await self._client.connect()

        if result:
            _LOGGER.info(
                "successfully connected to %s:%s", self._client.comm_params.host, self._client.comm_params.port
            )
        else:
            _LOGGER.warning(
                "not able to connect to %s:%s", self._client.comm_params.host, self._client.comm_params.port
            )
        return result

    async def write_modbus_data(self, address, value):
        await self._check_and_reopen()

        _LOGGER.debug("writing modbus data: %s %s", address, value)
        async with self._lock:
            response = await self._client.write_register(address, value, 0x04)

        if response.isError():
            _LOGGER.error("error writing modbus data: %s", response)
        else:
            _LOGGER.debug("successfully wrote modbus data: %s %s", address, value)

        # await self._async_refresh_modbus_data()
        return response

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

                if not await self._check_and_reopen():
                    break

                async with self._lock:
                    response = await self._client.read_holding_registers(address=start, count=count, slave=0x04)
                if response.isError():
                    _LOGGER.error("error reading modbus data at address %s: %s", start, response)
                elif len(response.registers) != count:
                    _LOGGER.warning(
                        "wrong number of registers read at address %s, expected %s, got %s",
                        start,
                        count,
                        len(response.registers),
                    )
                else:
                    for i in range(count):
                        read[start + i] = response.registers[i]
                    self.data.update(register[2](read))
            except asyncio.exceptions.CancelledError:
                _LOGGER.warning("cancelled modbus read")
                raise
            except:
                _LOGGER.error("error reading modbus data at address %s", start, exc_info=True)

        _LOGGER.debug("finished reading modbus data, %s", read)
        self.registers = read
        self._reading = False
        # _LOGGER.debug("Data: %s", self.data)

        return True

    def _device_info(self):
        # TODO: Find a way of making sure two inverters of the same model don't have the same identifiers. Issue #54
        return {
            "identifiers": {(DOMAIN, self.model)},
            "name": self.model,
            "model": self.model,
            "manufacturer": "Must Solar",
            "hw_version": self.data["InverterHardwareVersion"],
            "sw_version": self.data["InverterSoftwareVersion"],
            "serial_number": self.data["InverterSerialNumber"],
        }
