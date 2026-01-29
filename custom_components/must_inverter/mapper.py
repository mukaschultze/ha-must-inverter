import datetime
import logging

from .const import INVERTER_ERROR, INVERTER_WARNING, CHARGER_ERROR, CHARGER_WARNING

_LOGGER = logging.getLogger(__name__)


def int16(address, registers):
    val = registers[address]
    bits = 16
    if (val & (1 << (bits - 1))) != 0:  # if sign bit is set e.g., 8bit: 128-255
        val = val - (1 << bits)  # compute negative value
    return val  # return positive value as is


def uint16(address, registers):
    return registers[address]


def version(address, registers):
    return f"{registers[address] // 10000}.{(registers[address] // 100) % 100}.{registers[address] % 100}"


def accumulated_kwh(address, registers):
    return registers[address] * 1000 + registers[address + 1] * 0.1


def duration(address, registers):
    return int(registers[address]) * 60 * 60 + int(registers[address + 1]) * 60 + int(registers[address + 2])


def time(address, registers):
    return datetime.time(registers[address] // 100, registers[address] % 100)


def serial(address, registers):
    return registers[address] << 16 | registers[address + 1]


def serial_string(address, registers):
    return f"{registers[address]:05d}{registers[address + 1]:05d}{registers[address + 2]:05d}"


def model(address, registers):
    a = chr(registers[address] >> 8 & 0xFF)
    b = chr(registers[address] & 0xFF)
    return f"{a}{b}{registers[address + 1]}"


def error_bits(address, registers, error_codes):
    number_of_registers = len(error_codes) // 16
    errors_found = []

    for i in range(number_of_registers):
        for j in range(16):
            if registers[address + i] & (1 << j):
                _LOGGER.debug("Error code %s found", i * 16 + j)
                errors_found.append(error_codes[i * 16 + j] or f"Unknown error bit {i * 16 + j}")

    if len(errors_found) == 0:
        return "No errors"

    _LOGGER.debug("Errors found: %s", errors_found)
    return ", ".join(errors_found)


def convert_partArr2(partArr2):
    if partArr2 is None:
        return None

    # fmt: off
    result = {}
    result["ChargerWorkEnable"] =              int16(10101, partArr2)
    result["AbsorbVoltage"] =                  int16(10102, partArr2)
    result["FloatVoltage"] =                   int16(10103, partArr2)
    result["AbsorptionVoltage"] =              int16(10104, partArr2)
    result["BatteryLowVoltage"] =              int16(10105, partArr2)
    result["BatteryHighVoltage"] =             int16(10107, partArr2)
    result["MaxChargerCurrent"] =              int16(10108, partArr2)
    result["AbsorbChargerCurrent"] =           int16(10109, partArr2)
    result["BatteryType"] =                    int16(10110, partArr2)
    result["BatteryAh"] =                      int16(10111, partArr2)
    result["RemoveTheAccumulatedData"] =       int16(10112, partArr2)
    result["BatteryEqualizationEnable"] =      int16(10118, partArr2)
    result["BatteryEqualizationVoltage"] =     int16(10119, partArr2)
    result["BatteryEqualizationTime"] =        int16(10121, partArr2)
    result["BatteryEqualizationTimeout"] =     int16(10122, partArr2)
    result["BatteryEqualizationInterval"] =    int16(10123, partArr2)
    result["BatteryEqualizationImmediately"] = int16(10124, partArr2)
    # fmt: on

    return result


def convert_partArr3(partArr3):
    if partArr3 is None:
        return None

    # fmt: off
    result = {}
    result["ChargerWorkstate"] =     int16(15201, partArr3)
    result["MpptState"] =            int16(15202, partArr3)
    result["ChargingState"] =        int16(15203, partArr3)
    result["PvVoltage"] =            int16(15205, partArr3)
    result["BatteryVoltage"] =       int16(15206, partArr3)
    result["ChargerCurrent"] =       int16(15207, partArr3)
    result["ChargerPower"] =         int16(15208, partArr3)
    result["RadiatorTemperature"] =  int16(15209, partArr3)
    result["ExternalTemperature"] =  int16(15210, partArr3)
    result["BatteryRelay"] =         int16(15211, partArr3)
    result["PvRelay"] =              int16(15212, partArr3)
    result["ChargerErrorMessage"] =  error_bits(15213, partArr3, CHARGER_ERROR)
    result["ChargerWarningMessage"] =error_bits(15214, partArr3, CHARGER_WARNING)
    result["BattVolGrade"] =         int16(15215, partArr3)
    result["RatedCurrent"] =         int16(15216, partArr3)
    result["AccumulatedPower"] =     accumulated_kwh(15217, partArr3)
    result["AccumulatedTime"] =      duration(15219, partArr3)
    # fmt: on

    return result


def convert_partArr4(partArr4):
    if partArr4 is None:
        return None

    # fmt: off
    result = {}
    result["InverterMachineType"] =       model(20000, partArr4)
    result["InverterSerialNumber"] =      serial(20002, partArr4)
    result["InverterHardwareVersion"] =   version(20004, partArr4)
    result["InverterSoftwareVersion"] =   version(20005, partArr4)

    # Calibration registers
    result["InverterBatteryVoltageC"] =   int16(20009, partArr4)
    result["InverterVoltageC"] =          int16(20010, partArr4)
    result["GridVoltageC"] =              int16(20011, partArr4)
    result["BusVoltageC"] =               int16(20012, partArr4)
    result["ControlCurrentC"] =           int16(20013, partArr4)
    result["InverterCurrentC"] =          int16(20014, partArr4)
    result["GridCurrentC"] =              int16(20015, partArr4)
    result["LoadCurrentC"] =              int16(20016, partArr4)
    # fmt: on

    return result


def convert_partArr6(partArr6):
    if partArr6 is None:
        return None

    # fmt: off
    result = {}
    result["WorkState"] =                       int16(25201, partArr6)
    result["AcVoltageGrade"] =                  int16(25202, partArr6)
    result["RatedPower"] =                      int16(25203, partArr6)
    result["InverterBatteryVoltage"] =          int16(25205, partArr6)
    result["InverterVoltage"] =                 int16(25206, partArr6)
    result["GridVoltage"] =                     int16(25207, partArr6)
    result["BusVoltage"] =                      int16(25208, partArr6)
    result["ControlCurrent"] =                  int16(25209, partArr6)
    result["InverterCurrent"] =                 int16(25210, partArr6)
    result["GridCurrent"] =                     int16(25211, partArr6)
    result["LoadCurrent"] =                     int16(25212, partArr6)
    result["PInverter"] =                       int16(25213, partArr6)
    result["PGrid"] =                           int16(25214, partArr6)
    result["PLoad"] =                           int16(25215, partArr6)
    result["LoadPercent"] =                     int16(25216, partArr6)
    result["SInverter"] =                       int16(25217, partArr6)
    result["SGrid"] =                           int16(25218, partArr6)
    result["Sload"] =                           int16(25219, partArr6)
    result["Qinverter"] =                       int16(25221, partArr6)
    result["Qgrid"] =                           int16(25222, partArr6)
    result["Qload"] =                           int16(25223, partArr6)
    result["InverterFrequency"] =               int16(25225, partArr6)
    result["GridFrequency"] =                   int16(25226, partArr6)
    result["InverterMaxNumber"] =               uint16(25229, partArr6)
    result["CombineType"] =                     uint16(25230, partArr6)
    result["InverterNumber"] =                  uint16(25231, partArr6)
    result["AcRadiatorTemperature"] =           int16(25233, partArr6)
    result["TransformerTemperature"] =          int16(25234, partArr6)
    result["DcRadiatorTemperature"] =           int16(25235, partArr6)
    result["InverterRelayState"] =              int16(25237, partArr6)
    result["GridRelayState"] =                  int16(25238, partArr6)
    result["LoadRelayState"] =                  int16(25239, partArr6)
    result["N_LineRelayState"] =                int16(25240, partArr6)
    result["DCRelayState"] =                    int16(25241, partArr6)
    result["EarthRelayState"] =                 int16(25242, partArr6)
    result["AccumulatedChargerPower"] =         accumulated_kwh(25245, partArr6)
    result["AccumulatedDischargerPower"] =      accumulated_kwh(25247, partArr6)
    result["AccumulatedBuyPower"] =             accumulated_kwh(25249, partArr6)
    result["AccumulatedSellPower"] =            accumulated_kwh(25251, partArr6)
    result["AccumulatedLoadPower"] =            accumulated_kwh(25253, partArr6)
    result["AccumulatedSelfUsePower"] =         accumulated_kwh(25255, partArr6)
    result["AccumulatedPvSellPower"] =          accumulated_kwh(25257, partArr6)
    result["AccumulatedGridChargerPower"] =     accumulated_kwh(25259, partArr6)
    result["InverterErrorMessage"] =            error_bits(25261, partArr6, INVERTER_ERROR)
    result["InverterWarningMessage"] =          error_bits(25265, partArr6, INVERTER_WARNING)
    result["BattPower"] =                       int16(25273, partArr6)
    result["BattCurrent"] =                     int16(25274, partArr6)
    result["RatedPowerW"] =                     int16(25277, partArr6)
    # fmt: on

    return result


def convert_partArr5(partArr5):
    if partArr5 is None:
        return None

    # fmt: off
    result = {}
    result["InverterOffgridWorkEnable"] =        int16(20101, partArr5)
    result["InverterOutputVoltageSet"] =         int16(20102, partArr5)
    result["InverterOutputFrequencySet"] =       int16(20103, partArr5)
    result["InverterSearchModeEnable"] =         int16(20104, partArr5)
    result["InverterOngridWorkEnable"] =         int16(20105, partArr5)
    result["InverterChargerFromGridEnable"] =    int16(20106, partArr5)
    result["InverterDischargerEnable"] =         int16(20107, partArr5)
    result["InverterDischargerToGridEnable"] =   int16(20108, partArr5)
    result["EnergyUseMode"] =                    int16(20109, partArr5)
    result["GridProtectStandard"] =              int16(20111, partArr5)
    result["SolarUseAim"] =                      int16(20112, partArr5)
    result["InverterMaxDischargerCurrent"] =     int16(20113, partArr5)
    result["BatteryStopDischargingVoltage"] =    int16(20118, partArr5)
    result["BatteryStopChargingVoltage"] =       int16(20119, partArr5)
    result["GridMaxChargerCurrentSet"] =         int16(20125, partArr5)
    result["InverterBatteryLowVoltage"] =        int16(20127, partArr5)
    result["InverterBatteryHighVoltage"] =       int16(20128, partArr5)
    result["MaxCombineChargerCurrent"] =         int16(20132, partArr5)
    result["SystemSetting"] =                    uint16(20142, partArr5)
    result["ChargerSourcePriority"] =            int16(20143, partArr5)
    result["SolarPowerBalance"] =                int16(20144, partArr5)
    # fmt: on

    return result


# used for PV1900
def convert_battery_status(registers):
    """Convert battery status registers."""
    result = {}
    try:
        if 113 in registers:
            result["StateOfCharge"] = registers[113]
        if 114 in registers:
            result["BatteryStateOfHealth"] = registers[114]
    except Exception as e:
        _LOGGER.debug("Battery status not available: %s", e)
    return result


# used for PV1900
def convert_pv_data(registers):
    """Convert PV-specific registers."""
    result = {}
    try:
        # PV1 data
        if 15207 in registers:
            result["PV1ChargerCurrent"] = registers[15207]
        if 15208 in registers:
            result["PV1ChargerPower"] = registers[15208]

        # PV2 data
        if 16205 in registers:
            result["PV2Voltage"] = registers[16205]
        if 16207 in registers:
            result["PV2ChargerCurrent"] = registers[16207]
        if 16208 in registers:
            result["PV2ChargerPower"] = registers[16208]
    except Exception as e:
        _LOGGER.debug("PV data not available: %s", e)
    return result


def convert_ph1100_partArr1(partArr1):
    if partArr1 is None:
        return None

    # fmt: off
    result = {}
    result["BatteryEqualizationInterval"] =  int16(10117, partArr1)
    result["BatteryEqualizationStartTime"] = time(10118, partArr1)
    result["BatteryEqualizationEndTime"] =   time(10119, partArr1)
    # fmt: on

    return result


def convert_ph1100_partArr2(partArr2):
    if partArr2 is None:
        return None

    # fmt: off
    result = {}
    result["BatteryVoltage"] =         int16(15104, partArr2)
    result["BattCurrent"] =            int16(15105, partArr2)
    result["BattPower"] =              int16(15106, partArr2)
    result["InverterTemperature"] =    int16(15107, partArr2)
    result["DcRadiatorTemperature"] =  int16(15108, partArr2)
    result["TransformerTemperature"] = int16(15109, partArr2)
    result["AmbientTemperature"] =     int16(15110, partArr2)
    result["BatteryTemperature"] =     int16(15111, partArr2)
    result["BMSVoltage"] =             int16(15112, partArr2)
    result["BMSCurrent"] =             int16(15113, partArr2)
    result["BMSTemperature"] =         int16(15114, partArr2)
    result["BMSStateOfCharge"] =       int16(15115, partArr2)
    result["BMSMaxCVSet"] =            int16(15116, partArr2)
    result["BMSMaxCCSet"] =            int16(15117, partArr2)
    result["BMSDisCVSet"] =            int16(15118, partArr2)
    result["BMSDisCCSet"] =            int16(15119, partArr2)
    # fmt: on

    return result


def convert_ph1100_partArr3(partArr3):
    if partArr3 is None:
        return None

    # fmt: off
    result = {}
    result["InverterSerialNumber"] = serial_string(20001, partArr3)
    # fmt: on

    return result


def convert_ph1100_partArr4(partArr4):
    if partArr4 is None:
        return None

    # fmt: off
    result = {}
    result["PV1Voltage"] =                   int16(25225, partArr4)
    result["PV1Current"] =                   int16(25226, partArr4)
    result["PV1Power"] =                     int16(25227, partArr4)
    result["PV2Voltage"] =                   int16(25228, partArr4)
    result["PV2Current"] =                   int16(25229, partArr4)
    result["PV2Power"] =                     int16(25230, partArr4)
    result["PV3Voltage"] =                   int16(25231, partArr4)
    result["PV3Current"] =                   int16(25232, partArr4)
    result["PV3Power"] =                     int16(25233, partArr4)
    result["PV4Voltage"] =                   int16(25234, partArr4)
    result["PV4Current"] =                   int16(25235, partArr4)
    result["PV4Power"] =                     int16(25236, partArr4)
    result["GridVoltageR"] =                 int16(25237, partArr4)
    result["GridVoltageS"] =                 int16(25238, partArr4)
    result["GridVoltageT"] =                 int16(25239, partArr4)
    result["GridCurrentR"] =                 int16(25240, partArr4)
    result["GridCurrentS"] =                 int16(25241, partArr4)
    result["GridCurrentT"] =                 int16(25242, partArr4)
    result["GridFrequency"] =                int16(25243, partArr4)
    result["PGrid"] =                        int16(25244, partArr4)
    result["QGrid"] =                        int16(25245, partArr4)
    result["SGrid"] =                        int16(25246, partArr4)
    result["InverterVoltageR"] =             int16(25247, partArr4)
    result["InverterVoltageS"] =             int16(25248, partArr4)
    result["InverterVoltageT"] =             int16(25249, partArr4)
    result["InverterCurrentR"] =             int16(25250, partArr4)
    result["InverterCurrentS"] =             int16(25251, partArr4)
    result["InverterCurrentT"] =             int16(25252, partArr4)
    result["InverterFrequency"] =            int16(25253, partArr4)
    result["PInverter"] =                    int16(25254, partArr4)
    result["QInverter"] =                    int16(25255, partArr4)
    result["SInverter"] =                    int16(25256, partArr4)
    result["LoadVoltageR"] =                 int16(25257, partArr4)
    result["LoadVoltageS"] =                 int16(25258, partArr4)
    result["LoadVoltageT"] =                 int16(25259, partArr4)
    result["LoadCurrentR"] =                 int16(25260, partArr4)
    result["LoadCurrentS"] =                 int16(25261, partArr4)
    result["LoadCurrentT"] =                 int16(25262, partArr4)
    result["PLoad"] =                        int16(25263, partArr4)
    result["QLoad"] =                        int16(25264, partArr4)
    result["SLoad"] =                        int16(25265, partArr4)
    result["MainsCTRPhaseCurrent"] =         int16(25284, partArr4)
    result["MainsCTSPhaseCurrent"] =         int16(25285, partArr4)
    result["MainsCTTPhaseCurrent"] =         int16(25286, partArr4)
    result["MainsPowerCT"] =                 int16(25287, partArr4)
    result["TotalPvEnergy"] =                accumulated_kwh(25310, partArr4)
    result["TotalLoadEnergy"] =              accumulated_kwh(25312, partArr4)
    result["TotalBatteryChargeEnergy"] =     accumulated_kwh(25314, partArr4)
    result["TotalBatteryDischargeEnergy"] =  accumulated_kwh(25316, partArr4)
    result["TotalInverterChargeEnergy"] =    accumulated_kwh(25318, partArr4)
    result["TotalInverterDischargeEnergy"] = accumulated_kwh(25320, partArr4)
    result["TotalGridChargeEnergy"] =        accumulated_kwh(25322, partArr4)
    result["TotalGridDischargeEnergy"] =     accumulated_kwh(25324, partArr4)
    result["TotalMainsChargeEnergyCT"] =     accumulated_kwh(25336, partArr4)
    result["TotalMainsDischargeEnergyCT"] =  accumulated_kwh(25338, partArr4)
    # fmt: on

    return result
