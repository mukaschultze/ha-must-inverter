import asyncio
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.event import async_track_time_interval
from pymodbus.client import AsyncModbusSerialClient, AsyncModbusTcpClient, AsyncModbusUdpClient

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN
from .mapper import *

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.NUMBER, Platform.SELECT, Platform.SWITCH, Platform.BUTTON]
_LOGGER = logging.getLogger(__name__)

async def async_setup(hass, config):
    hass.data[DOMAIN] = {}
    return True # Return boolean to indicate that initialization was successful.

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up the must inverter component."""
    try:
        entry.async_on_unload(entry.add_update_listener(async_reload_entry))

        inverter = MustInverter(hass, entry)

        successConnecting = await inverter.connect()

        if not successConnecting:
            raise ConfigEntryNotReady(f"Unable to connect to modbus device")

        successReading = await inverter._async_refresh_modbus_data()

        if not successReading:
            raise ConfigEntryNotReady(f"Unable to read from modbus device")

        hass.data[DOMAIN][entry.entry_id] = inverter

        for component in PLATFORMS:
            hass.async_create_task(
                hass.config_entries.async_forward_entry_setup(entry, component)
            )

        return True
    except ConfigEntryNotReady as ex:
        raise ex
    except Exception as ex:
        _LOGGER.exception("Error setting up modbus device", exc_info=True)
        raise ConfigEntryNotReady(f"Unknown error connecting to modbus device") from ex

async def async_unload_entry(hass, entry):
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in PLATFORMS
            ]
        )
    )

    if not unload_ok:
        return False

    hass.data[DOMAIN][entry.entry_id] = None
    return True

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update listener, called when the config entry options are changed."""
    await hass.config_entries.async_reload(entry.entry_id)

class MustInverter:

    def __init__(
        self,
        hass,
        entry: ConfigEntry
    ):
        self._hass = hass

        common = {
            'timeout': entry.options["timeout"],
            'retries': entry.options["retries"],
            'reconnect_delay': entry.options["reconnect_delay"],
            'reconnect_delay_max': entry.options["reconnect_delay_max"],
        }

        match entry.options["mode"]:
            case "serial":
                self._client = AsyncModbusSerialClient(
                    entry.options["device"],
                    baudrate = entry.options["baudrate"],
                    stopbits = entry.options["stopbits"],
                    bytesize = entry.options["bytesize"],
                    parity = entry.options["parity"],
                    **common
                )
            case "tcp":
                self._client = AsyncModbusTcpClient(
                    entry.options["host"],
                    port = entry.options["port"],
                    **common
                )
            case "udp":
                self._client = AsyncModbusUdpClient(
                    entry.options["host"],
                    port = entry.options["port"],
                    **common
                )
            case _:
                raise Exception("Invalid mode")

        self._client.rts = False
        self._client.dtr = False
        self._lock = asyncio.Lock()
        self._scan_interval = timedelta(seconds=DEFAULT_SCAN_INTERVAL)
        self._sensors = []
        self.data = {}

    @callback
    def async_add_must_inverter_sensor(self, update_callback):
        # This is the first sensor, set up interval.
        if not self._sensors:
            self._unsub_interval_method = async_track_time_interval(
                self._hass, self._async_refresh_modbus_data, self._scan_interval
            )

        self._sensors.append(update_callback)

    @callback
    def async_remove_must_inverter_sensor(self, update_callback):
        self._sensors.remove(update_callback)

        if not self._sensors:
            """stop the interval timer upon removal of last sensor"""
            self._unsub_interval_method()
            self._unsub_interval_method = None
            self.close()


    async def _async_refresh_modbus_data(self, now=None):
        if not await self._check_and_reopen():
            #if not connected, skip
            _LOGGER.warning("not connected, skipping refresh")
            return False

        try:
            update_result = await self.read_modbus_data()

            if update_result:
                for update_callback in self._sensors:
                    update_callback()
        except Exception as e:
            _LOGGER.exception("error reading inverter data", exc_info=True)
            update_result = False

        return update_result

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
            _LOGGER.info("successfully connected to %s:%s", self._client.comm_params.host, self._client.comm_params.port)
        else:
            _LOGGER.warning("not able to connect to %s:%s", self._client.comm_params.host, self._client.comm_params.port)
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

        # Reading all the control messages at once (ranges 20016-20100 and/or
        # 10009-10100 are problematic) causes the inverter to shut down
        # immediately and the charger stops working afterwards (all registers
        # return zeroes). Requires the grid/batteries/PV to be disconnected and
        # the inverter restarted for it to come back online.
        registersAddresses = [
          # (10000, 10008, convert_partArr1), # Charger Control Messages
            (10101, 10124, convert_partArr2), # Charger Control Messages
            (15201, 15221, convert_partArr3), # Charger Display Messages
            (20000, 20016, convert_partArr4), # Inverter Control Messages
            (20101, 20214, convert_partArr5), # Inverter Control Messages
            (25201, 25279, convert_partArr6), # Inverter Display Messages
        ]

        read = dict()

        for register in registersAddresses:
            start = register[0]
            end = register[1]
            count = end - start + 1

            try:
                _LOGGER.debug("reading modbus data from %s to %s (%s)", start, end, count)
                async with self._lock:
                    if not await self._check_and_reopen():
                        break

                    response = await self._client.read_holding_registers(address=start, count=count, slave=0x04)
                if response.isError():
                    _LOGGER.error("error reading modbus data at address %s: %s", register[0], response)
                elif len(response.registers) != count:
                    _LOGGER.warn("wrong number of registers read at address %s, expected %s, got %s", register[0], register[1], len(response.registers))
                else:
                    for i in range(count):
                        read[start + i] = response.registers[i]
                    self.data.update(register[2](read))
            except asyncio.exceptions.CancelledError:
                _LOGGER.warn("cancelled modbus read")
                raise
            except:
                _LOGGER.error("error reading modbus data at address %s", register[0], exc_info=True)

        _LOGGER.debug("finished reading modbus data, %s", read)
        # _LOGGER.debug("Data: %s", self.data)

        return True

    def _device_info(self):
        return  {
            "identifiers": {(DOMAIN, self.data["InverterMachineType"])},
            "name": self.data["InverterMachineType"],
            "model": self.data["InverterMachineType"],
            "manufacturer": "Must Solar",
            "hw_version": self.data["InverterHardwareVersion"],
            "sw_version": self.data["InverterSoftwareVersion"],
            "serial_number": self.data["InverterSerialNumber"],
        }