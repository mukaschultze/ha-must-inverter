import asyncio
import logging
from datetime import timedelta
from typing import Optional

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_interval
from pymodbus.client import AsyncModbusSerialClient

from .const import CONF_DEVICE, DEFAULT_SCAN_INTERVAL, DOMAIN
from .mapper import *

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.NUMBER, Platform.SELECT]
_LOGGER = logging.getLogger(__name__)

async def async_setup(hass, config):
    hass.data[DOMAIN] = {}
    return True # Return boolean to indicate that initialization was successful.

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    name = "must_inverter_name"
    serial_port = entry.data[CONF_DEVICE]
    inverter = MustInverter(hass, name, serial_port)

    await inverter._async_refresh_modbus_data()

    hass.data[DOMAIN][name] = inverter

    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )

    return True

async def async_unload_entry(hass, entry):
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

    hass.data[DOMAIN]
    return True

class MustInverter:
    def __init__(
        self,
        hass,
        name,
        serial_port
    ):
        self._hass = hass
        self._serial_port = serial_port
        self._client = AsyncModbusSerialClient(serial_port,
            baudrate=19200,
            stopbits=1,
            timeout=2,
            retries=3,
            reconnect_delay=0.3,
            reconnect_delay_max=1,
        )
        self._client.rts = False
        self._client.dtr = False
        self._name = name
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

    @property
    def name(self):
        return self._name

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
            _LOGGER.debug("lock acquired")
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
            _LOGGER.debug("lock acquired")
            response = await self._client.write_register(address, value, 0x04)

        if response.isError():
            _LOGGER.error("error writing modbus data: %s", response)
        else:
            _LOGGER.debug("successfully wrote modbus data: %s %s", address, value)

        # await self._async_refresh_modbus_data()
        return response

    async def read_modbus_data(self):
        _LOGGER.debug("reading modbus data")
        
        registersAddresses = [
          # (10001, 10, convert_partArr1),
            (10101, 12, convert_partArr2),
            (15201, 21, convert_partArr3),
            (20001, 16, convert_partArr4),
            (20101, 43, convert_partArr5),
            (25201, 77, convert_partArr6),
        ]

        for register in registersAddresses:
            try:
                _LOGGER.debug("reading modbus data at address %s", register[0])
                async with self._lock:
                    _LOGGER.debug("lock acquired")
                    response = await self._client.read_holding_registers(address=register[0], count=register[1], slave=0x04)
                if response.isError():
                    _LOGGER.error("error reading modbus data at address %s: %s", register[0], response)
                else:
                    self.data.update(register[2](response.registers))
            except asyncio.exceptions.CancelledError:
                _LOGGER.warn("cancelled modbus read")
                raise
            except:
                _LOGGER.error("error reading modbus data at address %s", register[0], exc_info=True)

        _LOGGER.debug("finished reading modbus data")
        # _LOGGER.debug("Data: %s", self.data)

        return True

