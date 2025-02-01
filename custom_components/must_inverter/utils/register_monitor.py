import logging
from datetime import datetime
import csv
import os
from typing import Any
import asyncio
import aiofiles
import io

_LOGGER = logging.getLogger(__name__)


class RegisterMonitor:
    def __init__(self, hass):
        self.hass = hass
        self.log_file = os.path.join(hass.config.config_dir, "must_inverter_registers.csv")
        self._lock = asyncio.Lock()  # Add lock for thread safety
        self._running = True  # Add running flag

        # Define register ranges to monitor
        self.register_ranges = [
            # Main ranges with unknown values we're investigating
            (25269, 25290, None),  # Contains status codes, RatedPowerW, and new unknown values
            # PV related ranges - keep these as they might reveal PV data
            (16200, 16210, None),  # Around existing PV2 registers
            (16100, 16110, None),  # Potential PV1 specific registers
        ]
        _LOGGER.info(f"Register monitor initialized with {len(self.register_ranges)} ranges to scan")
        _LOGGER.debug(f"Will monitor these ranges: {self.register_ranges}")

    async def stop(self):
        """Stop the monitor."""
        self._running = False
        _LOGGER.info("Register monitor stopped")

    async def scan_ranges(self, inverter):
        """Scan all defined register ranges."""
        if not self._running:
            return

        try:
            all_values = self._get_context_values(inverter)
            interesting_values: dict[int, Any] = {}

            for start, end, _ in self.register_ranges:
                try:
                    _LOGGER.debug(f"Scanning range {start}-{end}")
                    count = end - start + 1

                    if not await inverter._check_and_reopen():
                        _LOGGER.warning("Modbus connection check failed")
                        break

                    async with inverter._lock:
                        response = await inverter._client.read_holding_registers(address=start, count=count, slave=0x04)

                    if response.isError():
                        _LOGGER.warning(f"Error reading range {start}-{end}: {response}")
                        continue

                    if len(response.registers) != count:
                        _LOGGER.warning(
                            f"Wrong number of registers read at {start}, "
                            f"expected {count}, got {len(response.registers)}"
                        )
                        continue

                    # Process the response
                    for i in range(count):
                        reg = start + i
                        value = response.registers[i]
                        if value not in (None, 0):  # Skip null or zero values
                            all_values[f"REG_{reg}"] = value
                            interesting_values[reg] = value

                    # Add small delay between ranges
                    await asyncio.sleep(0.1)

                except Exception as e:
                    _LOGGER.warning(f"Error reading range {start}-{end}: {str(e)}")

            if interesting_values:
                context = self._get_value_context(inverter, interesting_values)
                _LOGGER.info(f"Found non-zero values: {interesting_values}")
                _LOGGER.info(f"Context when found: {context}")
            else:
                _LOGGER.debug("No interesting (non-zero) values found in this scan")

            await self._write_to_csv(all_values)

        except Exception as e:
            _LOGGER.error(f"Error during scan cycle: {str(e)}")

    def _get_context_values(self, inverter) -> dict[str, Any]:
        """Get context values for logging."""
        return {
            "timestamp": datetime.now().isoformat(),
            "Charger_Power": inverter.data.get("ChargerPower", 0),
            "ChargerCurrent": inverter.data.get("ChargerCurrent", 0),
            "PV_Voltage": inverter.data.get("PvVoltage", 0),
            "AccumulatedPvSellPower": inverter.data.get("AccumulatedPvSellPower", 0),
            "Battery_Power": inverter.data.get("BattPower", 0),
            "Load_Power": inverter.data.get("PLoad", 0),
            "Battery_Voltage": inverter.data.get("BatteryVoltage", 0),
            "Grid_Power": inverter.data.get("PGrid", 0),
            "ChargerWorkstate": inverter.data.get("ChargerWorkstate", ""),
            "ChargingState": inverter.data.get("ChargingState", ""),
            "MpptState": inverter.data.get("MpptState", ""),
        }

    def _get_value_context(self, inverter, values: dict[int, Any]) -> dict[str, Any]:
        """Get relevant context for the values found."""
        return {
            "PV_Active": bool(inverter.data.get("MpptState", 0)),
            "Battery_Charging": bool(inverter.data.get("BattPower", 0) > 0),
            "Grid_Connected": bool(inverter.data.get("GridVoltage", 0)),
            "Values": values,
        }

    async def _write_to_csv(self, values: dict[str, Any]):
        """Write values to CSV file asynchronously."""
        try:
            file_exists = os.path.exists(self.log_file)

            async with aiofiles.open(self.log_file, "a", newline="") as f:
                # Convert to CSV string
                fieldnames = list(values.keys())
                output = io.StringIO()
                writer = csv.DictWriter(output, fieldnames=fieldnames)

                if not file_exists:
                    writer.writeheader()
                    _LOGGER.info(f"Created new log file at {self.log_file}")

                writer.writerow(values)
                csv_string = output.getvalue()

                # Write asynchronously
                await f.write(csv_string)

            _LOGGER.debug(f"Wrote {len(values)} values to log file")
        except Exception as e:
            _LOGGER.error(f"Error writing to CSV: {str(e)}")
