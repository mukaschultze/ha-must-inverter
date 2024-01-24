import logging

_LOGGER = logging.getLogger(__name__)

def twos_complement(val, bits = 16):
    if (val & (1 << (bits - 1))) != 0: # if sign bit is set e.g., 8bit: 128-255
        val = val - (1 << bits)        # compute negative value
    return val                         # return positive value as is

#not implemented/needed
def convert_partArr1(partArr1):
    if partArr1 is None:
        return None

    return None

def convert_partArr2(partArr2):
    if partArr2 is None:
        return None

    result = {}
    result["ChargerWorkEnable"] =              twos_complement(partArr2[0])
    result["AbsorbVoltage"] =                  twos_complement(partArr2[1]) * 0.1
    result["FloatVoltage"] =                   twos_complement(partArr2[2]) * 0.1
    result["AbsorptionVoltage"] =              twos_complement(partArr2[3]) * 0.1
    result["BatteryLowVoltage"] =              twos_complement(partArr2[4]) * 0.1
    result["BatteryHighVoltage"] =             twos_complement(partArr2[6]) * 0.1
    result["MaxChargerCurrent"] =              twos_complement(partArr2[7]) * 0.1
    result["AbsorbChargerCurrent"] =           twos_complement(partArr2[8]) * 0.1
    result["BatteryType"] =                    twos_complement(partArr2[9])
    result["BatteryAh"] =                      twos_complement(partArr2[10])
    result["RemoveTheAccumulatedData"] =       twos_complement(partArr2[11])
    result["BatteryEqualizationEnable"] =      twos_complement(partArr2[17])
    result["BatteryEqualizationVoltage"] =     twos_complement(partArr2[18]) * 0.1
    result["BatteryEqualizationTime"] =        twos_complement(partArr2[20])
    result["BatteryEqualizationTimeout"] =     twos_complement(partArr2[21])
    result["BatteryEqualizationInterval"] =    twos_complement(partArr2[22])
    result["BatteryEqualizationImmediately"] = twos_complement(partArr2[23])

    return result

def convert_partArr3(partArr3):
    if partArr3 is None:
        return None

    result = {}
    result["ChargerWorkstate"] =     twos_complement(partArr3[0])
    result["MpptState"] =            twos_complement(partArr3[1])
    result["ChargingState"] =        twos_complement(partArr3[2])
    result["PvVoltage"] =            twos_complement(partArr3[4]) * 0.1
    result["BatteryVoltage"] =       twos_complement(partArr3[5]) * 0.1
    result["ChargerCurrent"] =       twos_complement(partArr3[6]) * 0.1
    result["ChargerPower"] =         twos_complement(partArr3[7])
    result["RadiatorTemperature"] =  twos_complement(partArr3[8])
    result["ExternalTemperature"] =  twos_complement(partArr3[9])
    result["BatteryRelay"] =         twos_complement(partArr3[10])
    result["PvRelay"] =              twos_complement(partArr3[11])
    result["ErrorMessage"] =         twos_complement(partArr3[12])
    result["WarningMessage"] =       twos_complement(partArr3[13])
    result["BattVolGrade"] =         twos_complement(partArr3[14])
    result["RatedCurrent"] =         twos_complement(partArr3[15]) * 0.1
    result["AccumulatedPower"] =     twos_complement(partArr3[16]) * 1000 + twos_complement(partArr3[17]) * 0.1
    result["AccumulatedTime"] =      int(partArr3[18]) * 60 * 60 + int(partArr3[19]) * 60 + int(partArr3[20])
    return result

def convert_partArr4(partArr4):
    if partArr4 is None:
        return None

    int16_4 = twos_complement(partArr4[4])
    int16_5 = twos_complement(partArr4[0])
    str1 = ""

    # Map int16_5 to InverterMachineType
    if int16_5 == 1600:
        str1 = "PC1600"
    elif int16_5 == 1800:
        str1 = "PV1800" if int16_4 > 20000 else "PH1800"
    elif int16_5 == 3000:
        str1 = "PH3000"
    elif int16_5 == 3500:
        str1 = "PV3500"

    int16_6 = twos_complement(partArr4[3])

    # Map int16_6 to InverterHardwareVersion
    if partArr4[3] != 0 and int16_6 != 0:
        str2 = f"{int16_6 // 10000}.{(int16_6 // 100) % 100}.{int16_6 % 100}"
    else:
        str2 = "1.00.00"

    int16_7 = twos_complement(partArr4[4])

    # Map int16_7 to InverterSoftwareVersion
    if partArr4[4] != 0 and int16_7 != 0:
        str3 = f"{int16_7 // 10000}.{(int16_7 // 100) % 100}.{int16_7 % 100}"
    else:
        str3 = "1.00.00"

    result = {}
    result["InverterMachineType"] =       str1
    result["InverterSerialNumber"] =      hex(partArr4[1] << 16 | partArr4[2])
    result["InverterHardwareVersion"] =   str2
    result["InverterSoftwareVersion"] =   str3
    result["InverterBatteryVoltageC"] =   partArr4[8]
    result["InverterVoltageC"] =          partArr4[9]
    result["GridVoltageC"] =              partArr4[10]
    result["BusVoltageC"] =               partArr4[11]
    result["ControlCurrentC"] =           partArr4[12]
    result["InverterCurrentC"] =          partArr4[13]
    result["GridCurrentC"] =              partArr4[14]
    result["LoadCurrentC"] =              partArr4[15]

    return result

def convert_partArr6(partArr6):
    if partArr6 is None:
        return None

    result = {}
    result["WorkState"] =                       twos_complement(partArr6[0])
    result["AcVoltageGrade"] =                  twos_complement(partArr6[1])
    result["RatedPower"] =                      twos_complement(partArr6[2])
    result["InverterBatteryVoltage"] =          twos_complement(partArr6[4]) * 0.1
    result["InverterVoltage"] =                 twos_complement(partArr6[5]) * 0.1
    result["GridVoltage"] =                     twos_complement(partArr6[6]) * 0.1
    result["BusVoltage"] =                      twos_complement(partArr6[7]) * 0.1
    result["ControlCurrent"] =                  twos_complement(partArr6[8]) * 0.1
    result["InverterCurrent"] =                 twos_complement(partArr6[9]) * 0.1
    result["GridCurrent"] =                     twos_complement(partArr6[10]) * 0.1
    result["LoadCurrent"] =                     twos_complement(partArr6[11]) * 0.1
    result["PInverter"] =                       twos_complement(partArr6[12])
    result["PGrid"] =                           twos_complement(partArr6[13])
    result["PLoad"] =                           twos_complement(partArr6[14])
    result["LoadPercent"] =                     twos_complement(partArr6[15])
    result["SInverter"] =                       twos_complement(partArr6[16])
    result["SGrid"] =                           twos_complement(partArr6[17])
    result["Sload"] =                           twos_complement(partArr6[18])
    result["Qinverter"] =                       twos_complement(partArr6[20])
    result["Qgrid"] =                           twos_complement(partArr6[21])
    result["Qload"] =                           twos_complement(partArr6[22])
    result["InverterFrequency"] =               twos_complement(partArr6[24]) * 0.01
    result["GridFrequency"] =                   twos_complement(partArr6[25]) * 0.01
    result["InverterMaxNumber"] =               partArr6[28]
    result["CombineType"] =                     partArr6[29]
    result["InverterNumber"] =                  partArr6[30]
    result["AcRadiatorTemperature"] =           twos_complement(partArr6[32])
    result["TransformerTemperature"] =          twos_complement(partArr6[33])
    result["DcRadiatorTemperature"] =           twos_complement(partArr6[34])
    result["InverterRelayState"] =              twos_complement(partArr6[36])
    result["GridRelayState"] =                  twos_complement(partArr6[37])
    result["LoadRelayState"] =                  twos_complement(partArr6[38])
    result["N_LineRelayState"] =                twos_complement(partArr6[39])
    result["DCRelayState"] =                    twos_complement(partArr6[40])
    result["EarthRelayState"] =                 twos_complement(partArr6[41])
    result["AccumulatedChargerPower"] =         twos_complement(partArr6[44]) * 1000 + twos_complement(partArr6[45]) * 0.1
    result["AccumulatedDischargerPower"] =      twos_complement(partArr6[46]) * 1000 + twos_complement(partArr6[47]) * 0.1
    result["AccumulatedBuyPower"] =             twos_complement(partArr6[48]) * 1000 + twos_complement(partArr6[49]) * 0.1
    result["AccumulatedSellPower"] =            twos_complement(partArr6[50]) * 1000 + twos_complement(partArr6[51]) * 0.1
    result["AccumulatedLoadPower"] =            twos_complement(partArr6[52]) * 1000 + twos_complement(partArr6[53]) * 0.1
    result["AccumulatedSelfUsePower"] =         twos_complement(partArr6[54]) * 1000 + twos_complement(partArr6[55]) * 0.1
    result["AccumulatedPvSellPower"] =          twos_complement(partArr6[56]) * 1000 + twos_complement(partArr6[57]) * 0.1
    result["AccumulatedGridChargerPower"] =     twos_complement(partArr6[58]) * 1000 + twos_complement(partArr6[59]) * 0.1
    #"InverterErrorMessage": Rs485ComServer.Operator.AnalyBitMessage(partArr6[60], Rs485Parse.InverterError1) + Rs485ComServer.Operator.AnalyBitMessage(partArr6[61], Rs485Parse.InverterError2),
    #"InverterWarningMessage": Rs485ComServer.Operator.AnalyBitMessage(partArr6[64], Rs485Parse.InverterWarning)
    result["BattPower"] =                       twos_complement(partArr6[72])
    result["BattCurrent"] =                     twos_complement(partArr6[73])
    result["RatedPowerW"] =                     twos_complement(partArr6[76])

    return result

def convert_partArr5(partArr5):
    if partArr5 is None:
        return None

    result = {}
    result["InverterOffgridWorkEnable"] =        twos_complement(partArr5[0])
    result["InverterOutputVoltageSet"] =         twos_complement(partArr5[1]) * 0.1
    result["InverterOutputFrequencySet"] =       twos_complement(partArr5[2]) * 0.01
    result["InverterSearchModeEnable"] =         twos_complement(partArr5[3])
    result["InverterOngridWorkEnable"] =         twos_complement(partArr5[4])
    result["InverterChargerFromGridEnable"] =    twos_complement(partArr5[5])
    result["InverterDischargerEnable"] =         twos_complement(partArr5[6])
    result["InverterDischargerToGridEnable"] =   twos_complement(partArr5[7])
    result["EnergyUseMode"] =                    twos_complement(partArr5[8])
    result["GridProtectStandard"] =              twos_complement(partArr5[10])
    result["SolarUseAim"] =                      twos_complement(partArr5[11])
    result["InverterMaxDischargerCurrent"] =     twos_complement(partArr5[12]) * 0.1
    result["BatteryStopDischargingVoltage"] =    twos_complement(partArr5[17]) * 0.1
    result["BatteryStopChargingVoltage"] =       twos_complement(partArr5[18]) * 0.1
    result["GridMaxChargerCurrentSet"] =         twos_complement(partArr5[24]) * 0.1
    result["InverterBatteryLowVoltage"] =        twos_complement(partArr5[26]) * 0.1
    result["InverterBatteryHighVoltage"] =       twos_complement(partArr5[27]) * 0.1
    result["MaxCombineChargerCurrent"] =         twos_complement(partArr5[31]) * 0.1
    result["SystemSetting"] =                    partArr5[41]
    result["ChargerSourcePriority"] =            twos_complement(partArr5[42])
    return result
