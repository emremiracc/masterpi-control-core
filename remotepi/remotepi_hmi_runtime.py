# -*- coding: utf-8 -*-
"""
remotepi_hmi_runtime.py
=======================
RemotePi HMI — Unified Runtime Module
Birleştirilmiş tek modül: MODULE-R001 → MODULE-R060

RemotePi, sondaj kulesi kontrol sisteminin operatör tarafıdır.
Kivy tabanlı dokunmatik HMI + çift joystick + MQTT/UDP transport.

Modül yapısı:
  BÖLÜM 1 — Hardware Layer    (R001-R007)
  BÖLÜM 2 — Runtime Core      (R008-R029)
  BÖLÜM 3 — Final Revisions   (R030-R045)
  BÖLÜM 4 — Extended Runtime  (R047-R060)
  BÖLÜM 5 — HMI App           (final runtime-connected HMI + FAZ patches)
"""
from __future__ import annotations



# ============================================================
# MODULE-R001
# ============================================================

# hardware/remotepi_gpio_binding_map.py
"""
MODULE-R001
RemotePi GPIO / ADC / HMI Binding Map
-------------------------------------
Purpose:
    Single Source of Truth (SSOT) for RemotePi hardware bindings.
Design principles:
    - RemotePi has a hybrid control architecture:
        1) Touchscreen HMI panel (software/UI event source)
        2) Two physical joysticks (hardware input source)
    - HMI widgets are NOT GPIO pins.
    - Joystick axes are analog sources read via ADS1115.
    - Joystick push-buttons are direct GPIO digital inputs.
    - Cooling, buzzer, and telemetry channels are part of the local hardware layer.
Notes:
    - ADS1115 #1 address: 0x48  (ADDR -> GND)
    - ADS1115 #2 address: 0x49  (ADDR -> 3V3)
    - Shared I2C bus on GPIO2 (SDA) / GPIO3 (SCL)
    - Remote fan is controlled locally from GPIO18
    - Remote buzzer is controlled locally from GPIO25
"""
from dataclasses import dataclass
from enum import Enum
from typing import Final, Optional
# ============================================================
# ENUMS
# ============================================================
class Direction(str, Enum):
    IN = "IN"
    OUT = "OUT"
    I2C = "I2C"
    UI = "UI"
    ANALOG = "ANALOG"
    VIRTUAL = "VIRTUAL"
class PullMode(str, Enum):
    NONE = "NONE"
    UP = "PULL_UP"
    DOWN = "PULL_DOWN"
class SignalType(str, Enum):
    DIGITAL = "DIGITAL"
    PWM = "PWM"
    I2C = "I2C"
    ANALOG = "ANALOG"
    UI_EVENT = "UI_EVENT"
    TELEMETRY = "TELEMETRY"
    POWER = "POWER"
    THERMAL = "THERMAL"
class HardwareLayer(str, Enum):
    UI = "UI"
    GPIO = "GPIO"
    I2C = "I2C"
    ADC = "ADC"
    POWER = "POWER"
    THERMAL = "THERMAL"
    SAFETY = "SAFETY"
# ============================================================
# DATA MODELS
# ============================================================
@dataclass(frozen=True)
class GPIOBinding:
    name: str
    bcm: int
    physical_pin: int
    direction: Direction
    signal_type: SignalType
    pull: PullMode = PullMode.NONE
    active_high: bool = True
    subsystem: str = ""
    description: str = ""
@dataclass(frozen=True)
class I2CBusBinding:
    name: str
    bus_id: int
    sda_bcm: int
    scl_bcm: int
    sda_pin: int
    scl_pin: int
    description: str = ""
@dataclass(frozen=True)
class ADS1115Binding:
    name: str
    i2c_address: int
    bus_name: str
    description: str = ""
@dataclass(frozen=True)
class ADCChannelBinding:
    name: str
    adc_name: str
    channel: int
    signal_type: SignalType
    subsystem: str
    unit: Optional[str] = None
    expected_range: Optional[str] = None
    description: str = ""
@dataclass(frozen=True)
class UIBinding:
    name: str
    signal_type: SignalType
    subsystem: str
    description: str = ""
# ============================================================
# I2C BUS
# ============================================================
I2C_BUSES: Final[dict[str, I2CBusBinding]] = {
    "I2C1_MAIN": I2CBusBinding(
        name="I2C1_MAIN",
        bus_id=1,
        sda_bcm=2,
        scl_bcm=3,
        sda_pin=3,
        scl_pin=5,
        description="Shared I2C backbone for ADS1115 #1 and ADS1115 #2."
    )
}
# ============================================================
# GPIO BINDINGS
# ============================================================
GPIO_BINDINGS: Final[dict[str, GPIOBinding]] = {
    # Digital joystick buttons
    "LEFT_JOYSTICK_BTN": GPIOBinding(
        name="LEFT_JOYSTICK_BTN",
        bcm=17,
        physical_pin=11,
        direction=Direction.IN,
        signal_type=SignalType.DIGITAL,
        pull=PullMode.UP,
        subsystem="INPUT",
        description="Left joystick push-button. Supports short/long press logic in software."
    ),
    "RIGHT_JOYSTICK_BTN": GPIOBinding(
        name="RIGHT_JOYSTICK_BTN",
        bcm=16,
        physical_pin=36,
        direction=Direction.IN,
        signal_type=SignalType.DIGITAL,
        pull=PullMode.UP,
        subsystem="INPUT",
        description="Right joystick push-button. Supports short/long press logic in software."
    ),
    # Local outputs
    "REMOTE_FAN_CTRL": GPIOBinding(
        name="REMOTE_FAN_CTRL",
        bcm=18,
        physical_pin=12,
        direction=Direction.OUT,
        signal_type=SignalType.PWM,
        subsystem="COOLING",
        description="RemotePi local 12V fan control output via MOSFET."
    ),
    "BUZZER_REMOTE": GPIOBinding(
        name="BUZZER_REMOTE",
        bcm=25,
        physical_pin=22,
        direction=Direction.OUT,
        signal_type=SignalType.PWM,
        subsystem="ALARM",
        description="RemotePi local buzzer output. Used for FAULT_MASTER or FAULT_REMOTE patterns."
    ),
}
# ============================================================
# ADS1115 DEVICES
# ============================================================
ADS1115_DEVICES: Final[dict[str, ADS1115Binding]] = {
    "ADS1115_1": ADS1115Binding(
        name="ADS1115_1",
        i2c_address=0x48,
        bus_name="I2C1_MAIN",
        description="Primary analog input ADC for joystick axes."
    ),
    "ADS1115_2": ADS1115Binding(
        name="ADS1115_2",
        i2c_address=0x49,
        bus_name="I2C1_MAIN",
        description="Secondary analog input ADC for battery and temperature telemetry."
    ),
}
# ============================================================
# ADC CHANNEL BINDINGS
# ============================================================
ADC_CHANNEL_BINDINGS: Final[dict[str, ADCChannelBinding]] = {
    # ADS1115 #1 → joystick axes
    "LEFT_JOYSTICK_X": ADCChannelBinding(
        name="LEFT_JOYSTICK_X",
        adc_name="ADS1115_1",
        channel=0,
        signal_type=SignalType.ANALOG,
        subsystem="JOYSTICK",
        unit="raw",
        expected_range="0.0V-3.3V",
        description="Left joystick X axis."
    ),
    "LEFT_JOYSTICK_Y": ADCChannelBinding(
        name="LEFT_JOYSTICK_Y",
        adc_name="ADS1115_1",
        channel=1,
        signal_type=SignalType.ANALOG,
        subsystem="JOYSTICK",
        unit="raw",
        expected_range="0.0V-3.3V",
        description="Left joystick Y axis."
    ),
    "RIGHT_JOYSTICK_X": ADCChannelBinding(
        name="RIGHT_JOYSTICK_X",
        adc_name="ADS1115_1",
        channel=2,
        signal_type=SignalType.ANALOG,
        subsystem="JOYSTICK",
        unit="raw",
        expected_range="0.0V-3.3V",
        description="Right joystick X axis."
    ),
    "RIGHT_JOYSTICK_Y": ADCChannelBinding(
        name="RIGHT_JOYSTICK_Y",
        adc_name="ADS1115_1",
        channel=3,
        signal_type=SignalType.ANALOG,
        subsystem="JOYSTICK",
        unit="raw",
        expected_range="0.0V-3.3V",
        description="Right joystick Y axis."
    ),
    # ADS1115 #2 → system telemetry
    "BATTERY_VOLTAGE_SENSE": ADCChannelBinding(
        name="BATTERY_VOLTAGE_SENSE",
        adc_name="ADS1115_2",
        channel=0,
        signal_type=SignalType.TELEMETRY,
        subsystem="POWER",
        unit="volts_scaled",
        expected_range="scaled",
        description="Battery voltage sense through resistor divider. Requires calibration."
    ),
    "LM35_TEMP": ADCChannelBinding(
        name="LM35_TEMP",
        adc_name="ADS1115_2",
        channel=1,
        signal_type=SignalType.THERMAL,
        subsystem="THERMAL",
        unit="degC",
        expected_range="0.0V-1.5V",
        description="LM35 temperature sensor input."
    ),
    "NTC_BATTERY_TEMP": ADCChannelBinding(
        name="NTC_BATTERY_TEMP",
        adc_name="ADS1115_2",
        channel=2,
        signal_type=SignalType.THERMAL,
        subsystem="THERMAL",
        unit="degC_est",
        expected_range="divider",
        description="Battery pack NTC temperature sensing input."
    ),
    "ADC2_SPARE": ADCChannelBinding(
        name="ADC2_SPARE",
        adc_name="ADS1115_2",
        channel=3,
        signal_type=SignalType.ANALOG,
        subsystem="RESERVED",
        unit=None,
        expected_range=None,
        description="Reserved analog input for future expansion."
    ),
}
# ============================================================
# HMI / UI BINDINGS
# ============================================================
# IMPORTANT:
# These are NOT GPIO pins.
# These are software-side event sources produced by the touchscreen UI.
UI_BINDINGS: Final[dict[str, UIBinding]] = {
    # Left block
    "UI_WHEEL": UIBinding(
        name="UI_WHEEL",
        signal_type=SignalType.UI_EVENT,
        subsystem="HMI_LEFT_BLOCK",
        description="Wheel control mode selection."
    ),
    "UI_DRIVER": UIBinding(
        name="UI_DRIVER",
        signal_type=SignalType.UI_EVENT,
        subsystem="HMI_LEFT_BLOCK",
        description="Driver control mode selection."
    ),
    "UI_DRAWWORKS": UIBinding(
        name="UI_DRAWWORKS",
        signal_type=SignalType.UI_EVENT,
        subsystem="HMI_LEFT_BLOCK",
        description="Drawworks control mode selection."
    ),
    "UI_SANDLINE": UIBinding(
        name="UI_SANDLINE",
        signal_type=SignalType.UI_EVENT,
        subsystem="HMI_LEFT_BLOCK",
        description="Sandline control mode selection."
    ),
    "UI_WINCH": UIBinding(
        name="UI_WINCH",
        signal_type=SignalType.UI_EVENT,
        subsystem="HMI_LEFT_BLOCK",
        description="Winch control mode selection."
    ),
    "UI_ROTARY_TABLE": UIBinding(
        name="UI_ROTARY_TABLE",
        signal_type=SignalType.UI_EVENT,
        subsystem="HMI_LEFT_BLOCK",
        description="Rotary table control mode selection."
    ),
    "UI_AUTONOM": UIBinding(
        name="UI_AUTONOM",
        signal_type=SignalType.UI_EVENT,
        subsystem="HMI_LEFT_BLOCK",
        description="Autonomous mode selection."
    ),
    "UI_MENU": UIBinding(
        name="UI_MENU",
        signal_type=SignalType.UI_EVENT,
        subsystem="HMI_LEFT_BLOCK",
        description="Menu navigation."
    ),
    # Right block
    "UI_START_STOP": UIBinding(
        name="UI_START_STOP",
        signal_type=SignalType.UI_EVENT,
        subsystem="HMI_RIGHT_BLOCK",
        description="System start/stop toggle."
    ),
    "UI_PARKING_LIGHT": UIBinding(
        name="UI_PARKING_LIGHT",
        signal_type=SignalType.UI_EVENT,
        subsystem="HMI_RIGHT_BLOCK",
        description="Parking light toggle."
    ),
    "UI_LOW_BEAM_LIGHT": UIBinding(
        name="UI_LOW_BEAM_LIGHT",
        signal_type=SignalType.UI_EVENT,
        subsystem="HMI_RIGHT_BLOCK",
        description="Low beam light toggle."
    ),
    "UI_HIGH_BEAM_LIGHT": UIBinding(
        name="UI_HIGH_BEAM_LIGHT",
        signal_type=SignalType.UI_EVENT,
        subsystem="HMI_RIGHT_BLOCK",
        description="High beam light toggle."
    ),
    "UI_SIGNAL_LHR_LIGHT": UIBinding(
        name="UI_SIGNAL_LHR_LIGHT",
        signal_type=SignalType.UI_EVENT,
        subsystem="HMI_RIGHT_BLOCK",
        description="Signal light toggle."
    ),
    "UI_RIG_FLOOR_LIGHT": UIBinding(
        name="UI_RIG_FLOOR_LIGHT",
        signal_type=SignalType.UI_EVENT,
        subsystem="HMI_RIGHT_BLOCK",
        description="Rig floor light toggle."
    ),
    "UI_ROTATION_LIGHT": UIBinding(
        name="UI_ROTATION_LIGHT",
        signal_type=SignalType.UI_EVENT,
        subsystem="HMI_RIGHT_BLOCK",
        description="Rotation light toggle."
    ),
    "UI_FAULT": UIBinding(
        name="UI_FAULT",
        signal_type=SignalType.UI_EVENT,
        subsystem="HMI_RIGHT_BLOCK",
        description="Fault status / fault acknowledge / fault view trigger."
    ),
    # Top/status area
    "UI_WIFI_STATUS": UIBinding(
        name="UI_WIFI_STATUS",
        signal_type=SignalType.UI_EVENT,
        subsystem="HMI_STATUS_BAR",
        description="Wi-Fi status indicator."
    ),
    "UI_BLUETOOTH_STATUS": UIBinding(
        name="UI_BLUETOOTH_STATUS",
        signal_type=SignalType.UI_EVENT,
        subsystem="HMI_STATUS_BAR",
        description="Bluetooth status indicator."
    ),
    "UI_BATTERY_STATUS": UIBinding(
        name="UI_BATTERY_STATUS",
        signal_type=SignalType.UI_EVENT,
        subsystem="HMI_STATUS_BAR",
        description="Battery status indicator."
    ),
    "UI_MASTER_COOLING_STATUS": UIBinding(
        name="UI_MASTER_COOLING_STATUS",
        signal_type=SignalType.UI_EVENT,
        subsystem="HMI_STATUS_BAR",
        description="MasterPi cooling state indicator."
    ),
    "UI_REMOTE_COOLING_STATUS": UIBinding(
        name="UI_REMOTE_COOLING_STATUS",
        signal_type=SignalType.UI_EVENT,
        subsystem="HMI_STATUS_BAR",
        description="RemotePi cooling state indicator."
    ),
}
# ============================================================
# LOGICAL GROUPS
# ============================================================
JOYSTICK_GROUPS: Final[dict[str, dict[str, str]]] = {
    "LEFT_JOYSTICK": {
        "x_axis": "LEFT_JOYSTICK_X",
        "y_axis": "LEFT_JOYSTICK_Y",
        "button": "LEFT_JOYSTICK_BTN",
    },
    "RIGHT_JOYSTICK": {
        "x_axis": "RIGHT_JOYSTICK_X",
        "y_axis": "RIGHT_JOYSTICK_Y",
        "button": "RIGHT_JOYSTICK_BTN",
    },
}
THERMAL_GROUP: Final[dict[str, str]] = {
    "fan_output": "REMOTE_FAN_CTRL",
    "battery_temp_sensor": "NTC_BATTERY_TEMP",
    "ambient_or_local_temp_sensor": "LM35_TEMP",
}
ALARM_GROUP: Final[dict[str, str]] = {
    "buzzer_output": "BUZZER_REMOTE",
    "fault_ui": "UI_FAULT",
}
POWER_GROUP: Final[dict[str, str]] = {
    "battery_voltage": "BATTERY_VOLTAGE_SENSE",
    "battery_temp": "NTC_BATTERY_TEMP",
}
I2C_GROUP: Final[dict[str, str]] = {
    "main_bus": "I2C1_MAIN",
    "adc_1": "ADS1115_1",
    "adc_2": "ADS1115_2",
}
# ============================================================
# HMI → CONTROL MODE HINTS
# ============================================================
# These are software hints for upper layers (FSM / event router).
# They do NOT directly manipulate GPIO in this module.
HMI_TO_PRIMARY_CONTROL_HINT: Final[dict[str, str]] = {
    "UI_WHEEL": "LEFT_JOYSTICK_X",
    "UI_DRIVER": "RIGHT_JOYSTICK_Y",
    "UI_DRAWWORKS": "RIGHT_JOYSTICK_Y",
    "UI_SANDLINE": "LEFT_JOYSTICK_Y",
    "UI_WINCH": "LEFT_JOYSTICK_X",
    "UI_ROTARY_TABLE": "LEFT_JOYSTICK_Y",
    "UI_AUTONOM": "VIRTUAL_AUTONOM_CONTROL",
    "UI_MENU": "VIRTUAL_MENU_CONTROL",
}
# ============================================================
# VALIDATION HELPERS
# ============================================================
def get_gpio_binding(name: str) -> GPIOBinding:
    return GPIO_BINDINGS[name]
def get_adc_binding(name: str) -> ADCChannelBinding:
    return ADC_CHANNEL_BINDINGS[name]
def get_ui_binding(name: str) -> UIBinding:
    return UI_BINDINGS[name]
def get_ads_device(name: str) -> ADS1115Binding:
    return ADS1115_DEVICES[name]
def validate_unique_gpio_usage() -> None:
    seen: dict[tuple[int, int], str] = {}
    for binding in GPIO_BINDINGS.values():
        key = (binding.bcm, binding.physical_pin)
        if key in seen:
            raise ValueError(
                f"GPIO conflict: {binding.name} conflicts with {seen[key]} "
                f"on BCM={binding.bcm}, Pin={binding.physical_pin}"
            )
        seen[key] = binding.name
def validate_unique_adc_channels() -> None:
    seen: dict[tuple[str, int], str] = {}
    for binding in ADC_CHANNEL_BINDINGS.values():
        key = (binding.adc_name, binding.channel)
        if key in seen:
            raise ValueError(
                f"ADC channel conflict: {binding.name} conflicts with {seen[key]} "
                f"on {binding.adc_name} channel A{binding.channel}"
            )
        seen[key] = binding.name
def validate_bindings() -> None:
    validate_unique_gpio_usage()
    validate_unique_adc_channels()
# Run validation at import time to keep SSOT strict.
validate_bindings()


# ============================================================
# MODULE-R002
# ============================================================

# hardware/remotepi_hw_profile.py
"""
MODULE-R002
RemotePi Hardware Profile
-------------------------
Purpose:
    Hardware behavior profile and operating thresholds for RemotePi.
Depends on:
    - hardware/remotepi_gpio_binding_map.py
Scope:
    - Joystick analog processing rules
    - ADC calibration placeholders
    - Thermal thresholds
    - Battery thresholds
    - Buzzer patterns
    - UI timing constants
Notes:
    This module contains operational constants and profile definitions.
    It does NOT perform GPIO/ADC I/O directly.
"""
from dataclasses import dataclass
from typing import Final
# ============================================================
# GLOBAL PROFILE INFO
# ============================================================
PROFILE_NAME: Final[str] = "RemotePi Hardware Profile"
PROFILE_VERSION: Final[str] = "1.0.0"
PROFILE_TARGET: Final[str] = "RemotePi"
PROFILE_MODE: Final[str] = "FIELD_CONTROL_NODE"
# ============================================================
# ADC / JOYSTICK PROFILE
# ============================================================
@dataclass(frozen=True)
class ADCProfile:
    sample_rate_sps: int
    gain: str
    reference_voltage: float
    raw_min: int
    raw_center: int
    raw_max: int
@dataclass(frozen=True)
class JoystickAxisProfile:
    deadzone_ratio: float
    soft_zone_ratio: float
    invert: bool
    expo: float
    clamp_min: float
    clamp_max: float
@dataclass(frozen=True)
class JoystickButtonProfile:
    debounce_ms: int
    short_press_ms: int
    long_press_ms: int
    repeat_interval_ms: int
ADC_PROFILE: Final[ADCProfile] = ADCProfile(
    sample_rate_sps=128,
    gain="GAIN_1",
    reference_voltage=4.096,
    raw_min=0,
    raw_center=16384,
    raw_max=32767,
)
LEFT_JOYSTICK_X_PROFILE: Final[JoystickAxisProfile] = JoystickAxisProfile(
    deadzone_ratio=0.08,
    soft_zone_ratio=0.15,
    invert=False,
    expo=1.20,
    clamp_min=-1.0,
    clamp_max=1.0,
)
LEFT_JOYSTICK_Y_PROFILE: Final[JoystickAxisProfile] = JoystickAxisProfile(
    deadzone_ratio=0.08,
    soft_zone_ratio=0.15,
    invert=True,
    expo=1.20,
    clamp_min=-1.0,
    clamp_max=1.0,
)
RIGHT_JOYSTICK_X_PROFILE: Final[JoystickAxisProfile] = JoystickAxisProfile(
    deadzone_ratio=0.08,
    soft_zone_ratio=0.15,
    invert=False,
    expo=1.20,
    clamp_min=-1.0,
    clamp_max=1.0,
)
RIGHT_JOYSTICK_Y_PROFILE: Final[JoystickAxisProfile] = JoystickAxisProfile(
    deadzone_ratio=0.08,
    soft_zone_ratio=0.15,
    invert=True,
    expo=1.20,
    clamp_min=-1.0,
    clamp_max=1.0,
)
JOYSTICK_BUTTON_PROFILE: Final[JoystickButtonProfile] = JoystickButtonProfile(
    debounce_ms=35,
    short_press_ms=120,
    long_press_ms=900,
    repeat_interval_ms=250,
)
# ============================================================
# BATTERY PROFILE
# ============================================================
@dataclass(frozen=True)
class BatteryProfile:
    chemistry: str
    series_count: int
    parallel_count: int
    nominal_voltage: float
    full_voltage: float
    warning_voltage: float
    critical_voltage: float
    shutdown_voltage: float
BATTERY_PROFILE: Final[BatteryProfile] = BatteryProfile(
    chemistry="Li-ion 18650",
    series_count=3,
    parallel_count=3,
    nominal_voltage=11.1,
    full_voltage=12.6,
    warning_voltage=10.8,
    critical_voltage=10.2,
    shutdown_voltage=9.6,
)
# ============================================================
# THERMAL PROFILE
# ============================================================
@dataclass(frozen=True)
class ThermalProfile:
    fan_on_temp_c: float
    fan_off_temp_c: float
    warning_temp_c: float
    critical_temp_c: float
    shutdown_temp_c: float
LM35_THERMAL_PROFILE: Final[ThermalProfile] = ThermalProfile(
    fan_on_temp_c=42.0,
    fan_off_temp_c=37.0,
    warning_temp_c=55.0,
    critical_temp_c=65.0,
    shutdown_temp_c=72.0,
)
NTC_BATTERY_THERMAL_PROFILE: Final[ThermalProfile] = ThermalProfile(
    fan_on_temp_c=40.0,
    fan_off_temp_c=35.0,
    warning_temp_c=50.0,
    critical_temp_c=58.0,
    shutdown_temp_c=65.0,
)
# ============================================================
# SENSOR CALIBRATION PLACEHOLDERS
# ============================================================
@dataclass(frozen=True)
class DividerCalibration:
    r_top_ohm: float
    r_bottom_ohm: float
    adc_reference_voltage: float
    scale_factor: float
@dataclass(frozen=True)
class LM35Calibration:
    mv_per_c: float
    voltage_offset_mv: float
@dataclass(frozen=True)
class NTCCalibration:
    nominal_resistance_ohm: float
    nominal_temp_c: float
    beta_value: float
    series_resistor_ohm: float
BATTERY_DIVIDER_CALIBRATION: Final[DividerCalibration] = DividerCalibration(
    r_top_ohm=30000.0,
    r_bottom_ohm=7500.0,
    adc_reference_voltage=4.096,
    scale_factor=(30000.0 + 7500.0) / 7500.0,
)
LM35_CALIBRATION: Final[LM35Calibration] = LM35Calibration(
    mv_per_c=10.0,
    voltage_offset_mv=0.0,
)
NTC_CALIBRATION: Final[NTCCalibration] = NTCCalibration(
    nominal_resistance_ohm=10000.0,
    nominal_temp_c=25.0,
    beta_value=3950.0,
    series_resistor_ohm=10000.0,
)
# ============================================================
# BUZZER PROFILE
# ============================================================
@dataclass(frozen=True)
class BuzzerPattern:
    on_ms: int
    off_ms: int
    repeat_count: int
BUZZER_PATTERNS: Final[dict[str, BuzzerPattern]] = {
    "BOOT_OK": BuzzerPattern(on_ms=80, off_ms=60, repeat_count=2),
    "BUTTON_ACK": BuzzerPattern(on_ms=40, off_ms=0, repeat_count=1),
    "WARNING": BuzzerPattern(on_ms=120, off_ms=120, repeat_count=3),
    "FAULT": BuzzerPattern(on_ms=300, off_ms=200, repeat_count=4),
    "CRITICAL": BuzzerPattern(on_ms=600, off_ms=150, repeat_count=6),
}
# ============================================================
# UI / EVENT TIMING PROFILE
# ============================================================
@dataclass(frozen=True)
class UITimingProfile:
    tap_debounce_ms: int
    screen_refresh_ms: int
    telemetry_refresh_ms: int
    network_status_refresh_ms: int
    fault_flash_ms: int
UI_TIMING_PROFILE: Final[UITimingProfile] = UITimingProfile(
    tap_debounce_ms=80,
    screen_refresh_ms=100,
    telemetry_refresh_ms=250,
    network_status_refresh_ms=1000,
    fault_flash_ms=400,
)
# ============================================================
# CONTROL MODE LIMITS
# ============================================================
@dataclass(frozen=True)
class ControlLimits:
    max_command_step: float
    soft_start_step: float
    emergency_zero_timeout_ms: int
CONTROL_LIMITS: Final[ControlLimits] = ControlLimits(
    max_command_step=0.10,
    soft_start_step=0.04,
    emergency_zero_timeout_ms=150,
)
# ============================================================
# HELPERS
# ============================================================
def battery_state_from_voltage(voltage: float) -> str:
    if voltage <= BATTERY_PROFILE.shutdown_voltage:
        return "SHUTDOWN"
    if voltage <= BATTERY_PROFILE.critical_voltage:
        return "CRITICAL"
    if voltage <= BATTERY_PROFILE.warning_voltage:
        return "WARNING"
    if voltage > BATTERY_PROFILE.full_voltage:
        return "OVER_RANGE"
    return "NORMAL"
def thermal_state_from_temp(temp_c: float, profile: ThermalProfile) -> str:
    if temp_c >= profile.shutdown_temp_c:
        return "SHUTDOWN"
    if temp_c >= profile.critical_temp_c:
        return "CRITICAL"
    if temp_c >= profile.warning_temp_c:
        return "WARNING"
    return "NORMAL"
def fan_should_run(temp_c: float, profile: ThermalProfile, currently_running: bool) -> bool:
    if currently_running:
        return temp_c >= profile.fan_off_temp_c
    return temp_c >= profile.fan_on_temp_c
def apply_deadzone(value: float, deadzone_ratio: float) -> float:
    if abs(value) < deadzone_ratio:
        return 0.0
    return value
def clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(value, max_value))
def normalize_adc_to_unit(raw_value: int, adc_profile: ADCProfile = ADC_PROFILE) -> float:
    """
    Normalize 16-bit ADC reading to approximately -1.0 ... +1.0
    around raw_center.
    """
    span_low = adc_profile.raw_center - adc_profile.raw_min
    span_high = adc_profile.raw_max - adc_profile.raw_center
    if raw_value >= adc_profile.raw_center:
        normalized = (raw_value - adc_profile.raw_center) / max(span_high, 1)
    else:
        normalized = (raw_value - adc_profile.raw_center) / max(span_low, 1)
    return clamp(normalized, -1.0, 1.0)
def shape_joystick_value(value: float, axis_profile: JoystickAxisProfile) -> float:
    value = clamp(value, axis_profile.clamp_min, axis_profile.clamp_max)
    value = apply_deadzone(value, axis_profile.deadzone_ratio)
    if value == 0.0:
        return 0.0
    sign = 1.0 if value >= 0 else -1.0
    magnitude = abs(value) ** axis_profile.expo
    shaped = sign * magnitude
    if axis_profile.invert:
        shaped *= -1.0
    return clamp(shaped, axis_profile.clamp_min, axis_profile.clamp_max)


# ============================================================
# MODULE-R003
# ============================================================

# hardware/remotepi_signal_names.py
"""
MODULE-R003
RemotePi Signal Names
---------------------
Purpose:
    Centralized signal/event/state/fault name constants for RemotePi.
Why this module exists:
    - Prevent string duplication across the project
    - Keep FSM / logger / HMI / telemetry / safety layers aligned
    - Provide stable SSOT names for events and states
"""
from typing import Final
# ============================================================
# MODULE INFO
# ============================================================
MODULE_NAME: Final[str] = "RemotePi Signal Names"
MODULE_VERSION: Final[str] = "1.0.0"
TARGET_NODE: Final[str] = "REMOTE_PI"
# ============================================================
# SYSTEM / NODE IDENTITY
# ============================================================
NODE_REMOTE: Final[str] = "REMOTE_PI"
NODE_MASTER: Final[str] = "MASTER_PI"
NODE_HMI: Final[str] = "HMI"
NODE_UI: Final[str] = "UI"
NODE_ADC: Final[str] = "ADC"
NODE_GPIO: Final[str] = "GPIO"
NODE_SAFETY: Final[str] = "SAFETY"
# ============================================================
# UI EVENTS
# ============================================================
EVENT_UI_WHEEL: Final[str] = "EVENT_UI_WHEEL"
EVENT_UI_DRIVER: Final[str] = "EVENT_UI_DRIVER"
EVENT_UI_DRAWWORKS: Final[str] = "EVENT_UI_DRAWWORKS"
EVENT_UI_SANDLINE: Final[str] = "EVENT_UI_SANDLINE"
EVENT_UI_WINCH: Final[str] = "EVENT_UI_WINCH"
EVENT_UI_ROTARY_TABLE: Final[str] = "EVENT_UI_ROTARY_TABLE"
EVENT_UI_AUTONOM: Final[str] = "EVENT_UI_AUTONOM"
EVENT_UI_MENU: Final[str] = "EVENT_UI_MENU"
EVENT_UI_START_STOP: Final[str] = "EVENT_UI_START_STOP"
EVENT_UI_PARKING_LIGHT: Final[str] = "EVENT_UI_PARKING_LIGHT"
EVENT_UI_LOW_BEAM_LIGHT: Final[str] = "EVENT_UI_LOW_BEAM_LIGHT"
EVENT_UI_HIGH_BEAM_LIGHT: Final[str] = "EVENT_UI_HIGH_BEAM_LIGHT"
EVENT_UI_SIGNAL_LHR_LIGHT: Final[str] = "EVENT_UI_SIGNAL_LHR_LIGHT"
EVENT_UI_RIG_FLOOR_LIGHT: Final[str] = "EVENT_UI_RIG_FLOOR_LIGHT"
EVENT_UI_ROTATION_LIGHT: Final[str] = "EVENT_UI_ROTATION_LIGHT"
EVENT_UI_FAULT: Final[str] = "EVENT_UI_FAULT"
EVENT_UI_SCREEN_READY: Final[str] = "EVENT_UI_SCREEN_READY"
EVENT_UI_HEARTBEAT: Final[str] = "EVENT_UI_HEARTBEAT"
# ============================================================
# JOYSTICK EVENTS
# ============================================================
EVENT_LEFT_JOYSTICK_MOVE: Final[str] = "EVENT_LEFT_JOYSTICK_MOVE"
EVENT_RIGHT_JOYSTICK_MOVE: Final[str] = "EVENT_RIGHT_JOYSTICK_MOVE"
EVENT_LEFT_JOYSTICK_X_CHANGED: Final[str] = "EVENT_LEFT_JOYSTICK_X_CHANGED"
EVENT_LEFT_JOYSTICK_Y_CHANGED: Final[str] = "EVENT_LEFT_JOYSTICK_Y_CHANGED"
EVENT_RIGHT_JOYSTICK_X_CHANGED: Final[str] = "EVENT_RIGHT_JOYSTICK_X_CHANGED"
EVENT_RIGHT_JOYSTICK_Y_CHANGED: Final[str] = "EVENT_RIGHT_JOYSTICK_Y_CHANGED"
EVENT_LEFT_JOYSTICK_BUTTON_DOWN: Final[str] = "EVENT_LEFT_JOYSTICK_BUTTON_DOWN"
EVENT_LEFT_JOYSTICK_BUTTON_UP: Final[str] = "EVENT_LEFT_JOYSTICK_BUTTON_UP"
EVENT_LEFT_JOYSTICK_BUTTON_SHORT: Final[str] = "EVENT_LEFT_JOYSTICK_BUTTON_SHORT"
EVENT_LEFT_JOYSTICK_BUTTON_LONG: Final[str] = "EVENT_LEFT_JOYSTICK_BUTTON_LONG"
EVENT_RIGHT_JOYSTICK_BUTTON_DOWN: Final[str] = "EVENT_RIGHT_JOYSTICK_BUTTON_DOWN"
EVENT_RIGHT_JOYSTICK_BUTTON_UP: Final[str] = "EVENT_RIGHT_JOYSTICK_BUTTON_UP"
EVENT_RIGHT_JOYSTICK_BUTTON_SHORT: Final[str] = "EVENT_RIGHT_JOYSTICK_BUTTON_SHORT"
EVENT_RIGHT_JOYSTICK_BUTTON_LONG: Final[str] = "EVENT_RIGHT_JOYSTICK_BUTTON_LONG"
EVENT_JOYSTICK_NEUTRAL: Final[str] = "EVENT_JOYSTICK_NEUTRAL"
EVENT_JOYSTICK_ACTIVITY: Final[str] = "EVENT_JOYSTICK_ACTIVITY"
# ============================================================
# ADC / SENSOR / TELEMETRY SIGNALS
# ============================================================
SIG_LEFT_JOYSTICK_X_RAW: Final[str] = "SIG_LEFT_JOYSTICK_X_RAW"
SIG_LEFT_JOYSTICK_Y_RAW: Final[str] = "SIG_LEFT_JOYSTICK_Y_RAW"
SIG_RIGHT_JOYSTICK_X_RAW: Final[str] = "SIG_RIGHT_JOYSTICK_X_RAW"
SIG_RIGHT_JOYSTICK_Y_RAW: Final[str] = "SIG_RIGHT_JOYSTICK_Y_RAW"
SIG_LEFT_JOYSTICK_X_NORM: Final[str] = "SIG_LEFT_JOYSTICK_X_NORM"
SIG_LEFT_JOYSTICK_Y_NORM: Final[str] = "SIG_LEFT_JOYSTICK_Y_NORM"
SIG_RIGHT_JOYSTICK_X_NORM: Final[str] = "SIG_RIGHT_JOYSTICK_X_NORM"
SIG_RIGHT_JOYSTICK_Y_NORM: Final[str] = "SIG_RIGHT_JOYSTICK_Y_NORM"
SIG_BATTERY_VOLTAGE: Final[str] = "SIG_BATTERY_VOLTAGE"
SIG_BATTERY_PERCENT_EST: Final[str] = "SIG_BATTERY_PERCENT_EST"
SIG_BATTERY_TEMP_C: Final[str] = "SIG_BATTERY_TEMP_C"
SIG_LM35_TEMP_C: Final[str] = "SIG_LM35_TEMP_C"
SIG_WIFI_CONNECTED: Final[str] = "SIG_WIFI_CONNECTED"
SIG_WIFI_RSSI: Final[str] = "SIG_WIFI_RSSI"
SIG_BLUETOOTH_CONNECTED: Final[str] = "SIG_BLUETOOTH_CONNECTED"
SIG_ETHERNET_LINK: Final[str] = "SIG_ETHERNET_LINK"
SIG_REMOTE_FAN_ACTIVE: Final[str] = "SIG_REMOTE_FAN_ACTIVE"
SIG_REMOTE_BUZZER_ACTIVE: Final[str] = "SIG_REMOTE_BUZZER_ACTIVE"
SIG_SYSTEM_HEARTBEAT: Final[str] = "SIG_SYSTEM_HEARTBEAT"
SIG_SYSTEM_UPTIME_SEC: Final[str] = "SIG_SYSTEM_UPTIME_SEC"
# ============================================================
# COMMAND SIGNALS
# ============================================================
CMD_SYSTEM_START: Final[str] = "CMD_SYSTEM_START"
CMD_SYSTEM_STOP: Final[str] = "CMD_SYSTEM_STOP"
CMD_REMOTE_FAN_ON: Final[str] = "CMD_REMOTE_FAN_ON"
CMD_REMOTE_FAN_OFF: Final[str] = "CMD_REMOTE_FAN_OFF"
CMD_BUZZER_BOOT_OK: Final[str] = "CMD_BUZZER_BOOT_OK"
CMD_BUZZER_BUTTON_ACK: Final[str] = "CMD_BUZZER_BUTTON_ACK"
CMD_BUZZER_WARNING: Final[str] = "CMD_BUZZER_WARNING"
CMD_BUZZER_FAULT: Final[str] = "CMD_BUZZER_FAULT"
CMD_BUZZER_CRITICAL: Final[str] = "CMD_BUZZER_CRITICAL"
CMD_MODE_WHEEL: Final[str] = "CMD_MODE_WHEEL"
CMD_MODE_DRIVER: Final[str] = "CMD_MODE_DRIVER"
CMD_MODE_DRAWWORKS: Final[str] = "CMD_MODE_DRAWWORKS"
CMD_MODE_SANDLINE: Final[str] = "CMD_MODE_SANDLINE"
CMD_MODE_WINCH: Final[str] = "CMD_MODE_WINCH"
CMD_MODE_ROTARY_TABLE: Final[str] = "CMD_MODE_ROTARY_TABLE"
CMD_MODE_AUTONOM: Final[str] = "CMD_MODE_AUTONOM"
CMD_MODE_MENU: Final[str] = "CMD_MODE_MENU"
CMD_LIGHT_PARKING_TOGGLE: Final[str] = "CMD_LIGHT_PARKING_TOGGLE"
CMD_LIGHT_LOW_BEAM_TOGGLE: Final[str] = "CMD_LIGHT_LOW_BEAM_TOGGLE"
CMD_LIGHT_HIGH_BEAM_TOGGLE: Final[str] = "CMD_LIGHT_HIGH_BEAM_TOGGLE"
CMD_LIGHT_SIGNAL_LHR_TOGGLE: Final[str] = "CMD_LIGHT_SIGNAL_LHR_TOGGLE"
CMD_LIGHT_RIG_FLOOR_TOGGLE: Final[str] = "CMD_LIGHT_RIG_FLOOR_TOGGLE"
CMD_LIGHT_ROTATION_TOGGLE: Final[str] = "CMD_LIGHT_ROTATION_TOGGLE"
CMD_FAULT_VIEW_OPEN: Final[str] = "CMD_FAULT_VIEW_OPEN"
CMD_FAULT_ACK: Final[str] = "CMD_FAULT_ACK"
CMD_JOYSTICK_LEFT_UPDATE: Final[str] = "CMD_JOYSTICK_LEFT_UPDATE"
CMD_JOYSTICK_RIGHT_UPDATE: Final[str] = "CMD_JOYSTICK_RIGHT_UPDATE"
# ============================================================
# STATES
# ============================================================
STATE_BOOTING: Final[str] = "STATE_BOOTING"
STATE_IDLE: Final[str] = "STATE_IDLE"
STATE_READY: Final[str] = "STATE_READY"
STATE_ACTIVE: Final[str] = "STATE_ACTIVE"
STATE_WARNING: Final[str] = "STATE_WARNING"
STATE_FAULT: Final[str] = "STATE_FAULT"
STATE_CRITICAL: Final[str] = "STATE_CRITICAL"
STATE_SHUTDOWN: Final[str] = "STATE_SHUTDOWN"
STATE_UI_READY: Final[str] = "STATE_UI_READY"
STATE_UI_NOT_READY: Final[str] = "STATE_UI_NOT_READY"
STATE_REMOTE_COOLING_ACTIVE: Final[str] = "STATE_REMOTE_COOLING_ACTIVE"
STATE_REMOTE_COOLING_IDLE: Final[str] = "STATE_REMOTE_COOLING_IDLE"
STATE_NETWORK_ONLINE: Final[str] = "STATE_NETWORK_ONLINE"
STATE_NETWORK_OFFLINE: Final[str] = "STATE_NETWORK_OFFLINE"
STATE_BATTERY_NORMAL: Final[str] = "STATE_BATTERY_NORMAL"
STATE_BATTERY_WARNING: Final[str] = "STATE_BATTERY_WARNING"
STATE_BATTERY_CRITICAL: Final[str] = "STATE_BATTERY_CRITICAL"
STATE_BATTERY_SHUTDOWN: Final[str] = "STATE_BATTERY_SHUTDOWN"
STATE_TEMP_NORMAL: Final[str] = "STATE_TEMP_NORMAL"
STATE_TEMP_WARNING: Final[str] = "STATE_TEMP_WARNING"
STATE_TEMP_CRITICAL: Final[str] = "STATE_TEMP_CRITICAL"
STATE_TEMP_SHUTDOWN: Final[str] = "STATE_TEMP_SHUTDOWN"
STATE_CONTROL_MODE_WHEEL: Final[str] = "STATE_CONTROL_MODE_WHEEL"
STATE_CONTROL_MODE_DRIVER: Final[str] = "STATE_CONTROL_MODE_DRIVER"
STATE_CONTROL_MODE_DRAWWORKS: Final[str] = "STATE_CONTROL_MODE_DRAWWORKS"
STATE_CONTROL_MODE_SANDLINE: Final[str] = "STATE_CONTROL_MODE_SANDLINE"
STATE_CONTROL_MODE_WINCH: Final[str] = "STATE_CONTROL_MODE_WINCH"
STATE_CONTROL_MODE_ROTARY_TABLE: Final[str] = "STATE_CONTROL_MODE_ROTARY_TABLE"
STATE_CONTROL_MODE_AUTONOM: Final[str] = "STATE_CONTROL_MODE_AUTONOM"
STATE_CONTROL_MODE_MENU: Final[str] = "STATE_CONTROL_MODE_MENU"
# ============================================================
# FAULT CODES
# ============================================================
FAULT_NONE: Final[str] = "FAULT_NONE"
FAULT_REMOTE_OVERHEAT: Final[str] = "FAULT_REMOTE_OVERHEAT"
FAULT_BATTERY_OVERHEAT: Final[str] = "FAULT_BATTERY_OVERHEAT"
FAULT_BATTERY_LOW: Final[str] = "FAULT_BATTERY_LOW"
FAULT_BATTERY_CRITICAL: Final[str] = "FAULT_BATTERY_CRITICAL"
FAULT_BATTERY_SENSOR_INVALID: Final[str] = "FAULT_BATTERY_SENSOR_INVALID"
FAULT_LM35_SENSOR_INVALID: Final[str] = "FAULT_LM35_SENSOR_INVALID"
FAULT_NTC_SENSOR_INVALID: Final[str] = "FAULT_NTC_SENSOR_INVALID"
FAULT_ADC1_OFFLINE: Final[str] = "FAULT_ADC1_OFFLINE"
FAULT_ADC2_OFFLINE: Final[str] = "FAULT_ADC2_OFFLINE"
FAULT_I2C_BUS_ERROR: Final[str] = "FAULT_I2C_BUS_ERROR"
FAULT_LEFT_JOYSTICK_STUCK: Final[str] = "FAULT_LEFT_JOYSTICK_STUCK"
FAULT_RIGHT_JOYSTICK_STUCK: Final[str] = "FAULT_RIGHT_JOYSTICK_STUCK"
FAULT_LEFT_JOYSTICK_BUTTON_STUCK: Final[str] = "FAULT_LEFT_JOYSTICK_BUTTON_STUCK"
FAULT_RIGHT_JOYSTICK_BUTTON_STUCK: Final[str] = "FAULT_RIGHT_JOYSTICK_BUTTON_STUCK"
FAULT_UI_UNRESPONSIVE: Final[str] = "FAULT_UI_UNRESPONSIVE"
FAULT_NETWORK_LINK_LOST: Final[str] = "FAULT_NETWORK_LINK_LOST"
FAULT_REMOTE_FAN_FAILURE: Final[str] = "FAULT_REMOTE_FAN_FAILURE"
FAULT_MASTER_LINK_TIMEOUT: Final[str] = "FAULT_MASTER_LINK_TIMEOUT"
FAULT_UNKNOWN: Final[str] = "FAULT_UNKNOWN"
# ============================================================
# WARNING CODES
# ============================================================
WARN_BATTERY_LOW: Final[str] = "WARN_BATTERY_LOW"
WARN_TEMP_HIGH: Final[str] = "WARN_TEMP_HIGH"
WARN_NETWORK_WEAK: Final[str] = "WARN_NETWORK_WEAK"
WARN_JOYSTICK_DRIFT: Final[str] = "WARN_JOYSTICK_DRIFT"
WARN_UI_SLOW: Final[str] = "WARN_UI_SLOW"
# ============================================================
# TOPIC / CHANNEL NAMES
# ============================================================
TOPIC_EVENTS: Final[str] = "remotepi/events"
TOPIC_TELEMETRY: Final[str] = "remotepi/telemetry"
TOPIC_FAULTS: Final[str] = "remotepi/faults"
TOPIC_STATES: Final[str] = "remotepi/states"
TOPIC_COMMANDS: Final[str] = "remotepi/commands"
TOPIC_HEALTH: Final[str] = "remotepi/health"
# ============================================================
# LOG CATEGORIES
# ============================================================
LOG_UI: Final[str] = "LOG_UI"
LOG_ADC: Final[str] = "LOG_ADC"
LOG_GPIO: Final[str] = "LOG_GPIO"
LOG_POWER: Final[str] = "LOG_POWER"
LOG_THERMAL: Final[str] = "LOG_THERMAL"
LOG_FAULT: Final[str] = "LOG_FAULT"
LOG_NETWORK: Final[str] = "LOG_NETWORK"
LOG_SYSTEM: Final[str] = "LOG_SYSTEM"
# ============================================================
# COLLECTIONS
# ============================================================
ALL_UI_EVENTS: Final[tuple[str, ...]] = (
    EVENT_UI_WHEEL,
    EVENT_UI_DRIVER,
    EVENT_UI_DRAWWORKS,
    EVENT_UI_SANDLINE,
    EVENT_UI_WINCH,
    EVENT_UI_ROTARY_TABLE,
    EVENT_UI_AUTONOM,
    EVENT_UI_MENU,
    EVENT_UI_START_STOP,
    EVENT_UI_PARKING_LIGHT,
    EVENT_UI_LOW_BEAM_LIGHT,
    EVENT_UI_HIGH_BEAM_LIGHT,
    EVENT_UI_SIGNAL_LHR_LIGHT,
    EVENT_UI_RIG_FLOOR_LIGHT,
    EVENT_UI_ROTATION_LIGHT,
    EVENT_UI_FAULT,
)
ALL_PRIMARY_STATES: Final[tuple[str, ...]] = (
    STATE_BOOTING,
    STATE_IDLE,
    STATE_READY,
    STATE_ACTIVE,
    STATE_WARNING,
    STATE_FAULT,
    STATE_CRITICAL,
    STATE_SHUTDOWN,
)
ALL_FAULT_CODES: Final[tuple[str, ...]] = (
    FAULT_NONE,
    FAULT_REMOTE_OVERHEAT,
    FAULT_BATTERY_OVERHEAT,
    FAULT_BATTERY_LOW,
    FAULT_BATTERY_CRITICAL,
    FAULT_BATTERY_SENSOR_INVALID,
    FAULT_LM35_SENSOR_INVALID,
    FAULT_NTC_SENSOR_INVALID,
    FAULT_ADC1_OFFLINE,
    FAULT_ADC2_OFFLINE,
    FAULT_I2C_BUS_ERROR,
    FAULT_LEFT_JOYSTICK_STUCK,
    FAULT_RIGHT_JOYSTICK_STUCK,
    FAULT_LEFT_JOYSTICK_BUTTON_STUCK,
    FAULT_RIGHT_JOYSTICK_BUTTON_STUCK,
    FAULT_UI_UNRESPONSIVE,
    FAULT_NETWORK_LINK_LOST,
    FAULT_REMOTE_FAN_FAILURE,
    FAULT_MASTER_LINK_TIMEOUT,
    FAULT_UNKNOWN,
)
ALL_WARNING_CODES: Final[tuple[str, ...]] = (
    WARN_BATTERY_LOW,
    WARN_TEMP_HIGH,
    WARN_NETWORK_WEAK,
    WARN_JOYSTICK_DRIFT,
    WARN_UI_SLOW,
)


# ============================================================
# MODULE-R004
# ============================================================

# hardware/remotepi_fault_policy.py
"""
MODULE-R004
RemotePi Fault Policy
---------------------
Purpose:
    Central safety / warning / fault decision policy for RemotePi.
Depends on:
    - hardware/remotepi_hw_profile.py
    - hardware/remotepi_signal_names.py
Scope:
    - Evaluate battery and thermal conditions
    - Convert raw health conditions into warnings / faults / states
    - Decide fan forcing policy
    - Decide buzzer alert class
    - Decide shutdown necessity
Notes:
    This module does NOT access GPIO directly.
    It only produces policy decisions for upper layers.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Final, Optional
from hardware.remotepi_hw_profile import (
    BATTERY_PROFILE,
    LM35_THERMAL_PROFILE,
    NTC_BATTERY_THERMAL_PROFILE,
    battery_state_from_voltage,
    thermal_state_from_temp,
)
from hardware.remotepi_signal_names import (
    FAULT_ADC1_OFFLINE,
    FAULT_ADC2_OFFLINE,
    FAULT_BATTERY_CRITICAL,
    FAULT_BATTERY_LOW,
    FAULT_BATTERY_OVERHEAT,
    FAULT_BATTERY_SENSOR_INVALID,
    FAULT_I2C_BUS_ERROR,
    FAULT_LM35_SENSOR_INVALID,
    FAULT_MASTER_LINK_TIMEOUT,
    FAULT_NETWORK_LINK_LOST,
    FAULT_NONE,
    FAULT_NTC_SENSOR_INVALID,
    FAULT_REMOTE_FAN_FAILURE,
    FAULT_REMOTE_OVERHEAT,
    STATE_ACTIVE,
    STATE_BOOTING,
    STATE_CRITICAL,
    STATE_FAULT,
    STATE_IDLE,
    STATE_READY,
    STATE_SHUTDOWN,
    STATE_TEMP_CRITICAL,
    STATE_TEMP_NORMAL,
    STATE_TEMP_SHUTDOWN,
    STATE_TEMP_WARNING,
    STATE_WARNING,
    WARN_BATTERY_LOW,
    WARN_NETWORK_WEAK,
    WARN_TEMP_HIGH,
)
# ============================================================
# ENUMS
# ============================================================
class Severity(str, Enum):
    NORMAL = "NORMAL"
    WARNING = "WARNING"
    FAULT = "FAULT"
    CRITICAL = "CRITICAL"
    SHUTDOWN = "SHUTDOWN"
class BuzzerClass(str, Enum):
    NONE = "NONE"
    BUTTON_ACK = "BUTTON_ACK"
    WARNING = "WARNING"
    FAULT = "FAULT"
    CRITICAL = "CRITICAL"
# ============================================================
# DATA MODELS
# ============================================================
@dataclass(frozen=True)
class HealthSnapshot:
    """
    Upper layers should construct this snapshot from actual readings.
    """
    battery_voltage: Optional[float] = None
    battery_temp_c: Optional[float] = None
    local_temp_c: Optional[float] = None
    adc1_online: bool = True
    adc2_online: bool = True
    i2c_ok: bool = True
    network_online: bool = True
    network_weak: bool = False
    master_link_ok: bool = True
    remote_fan_feedback_ok: bool = True
    ui_ready: bool = True
    system_active: bool = False
@dataclass
class FaultPolicyDecision:
    severity: Severity
    primary_state: str
    thermal_state: str
    warnings: list[str] = field(default_factory=list)
    faults: list[str] = field(default_factory=list)
    force_fan_on: bool = False
    request_shutdown: bool = False
    buzzer_class: BuzzerClass = BuzzerClass.NONE
    ui_fault_latched: bool = False
    accept_user_control: bool = True
    allow_new_motion_commands: bool = True
    summary: str = ""
# ============================================================
# VALIDATION HELPERS
# ============================================================
def _is_invalid_temperature(value: Optional[float]) -> bool:
    if value is None:
        return True
    return value < -40.0 or value > 150.0
def _is_invalid_voltage(value: Optional[float]) -> bool:
    if value is None:
        return True
    return value < 0.0 or value > 20.0
def _highest_severity(current: Severity, incoming: Severity) -> Severity:
    order = {
        Severity.NORMAL: 0,
        Severity.WARNING: 1,
        Severity.FAULT: 2,
        Severity.CRITICAL: 3,
        Severity.SHUTDOWN: 4,
    }
    return incoming if order[incoming] > order[current] else current
def _map_severity_to_primary_state(severity: Severity, system_active: bool) -> str:
    if severity == Severity.SHUTDOWN:
        return STATE_SHUTDOWN
    if severity == Severity.CRITICAL:
        return STATE_CRITICAL
    if severity == Severity.FAULT:
        return STATE_FAULT
    if severity == Severity.WARNING:
        return STATE_WARNING
    return STATE_ACTIVE if system_active else STATE_READY
def _map_thermal_bucket(local_temp_c: Optional[float]) -> str:
    if _is_invalid_temperature(local_temp_c):
        return STATE_TEMP_WARNING
    temp_state = thermal_state_from_temp(local_temp_c, LM35_THERMAL_PROFILE)
    if temp_state == "SHUTDOWN":
        return STATE_TEMP_SHUTDOWN
    if temp_state == "CRITICAL":
        return STATE_TEMP_CRITICAL
    if temp_state == "WARNING":
        return STATE_TEMP_WARNING
    return STATE_TEMP_NORMAL
# ============================================================
# EVALUATION
# ============================================================
def evaluate_fault_policy(snapshot: HealthSnapshot) -> FaultPolicyDecision:
    decision = FaultPolicyDecision(
        severity=Severity.NORMAL,
        primary_state=_map_severity_to_primary_state(Severity.NORMAL, snapshot.system_active),
        thermal_state=_map_thermal_bucket(snapshot.local_temp_c),
        summary="System healthy.",
    )
    # --------------------------------------------------------
    # HARD FAULTS: infrastructure / bus / ADC
    # --------------------------------------------------------
    if not snapshot.i2c_ok:
        decision.faults.append(FAULT_I2C_BUS_ERROR)
        decision.severity = _highest_severity(decision.severity, Severity.FAULT)
    if not snapshot.adc1_online:
        decision.faults.append(FAULT_ADC1_OFFLINE)
        decision.severity = _highest_severity(decision.severity, Severity.FAULT)
    if not snapshot.adc2_online:
        decision.faults.append(FAULT_ADC2_OFFLINE)
        decision.severity = _highest_severity(decision.severity, Severity.FAULT)
    # --------------------------------------------------------
    # SENSOR VALIDITY
    # --------------------------------------------------------
    if _is_invalid_voltage(snapshot.battery_voltage):
        decision.faults.append(FAULT_BATTERY_SENSOR_INVALID)
        decision.severity = _highest_severity(decision.severity, Severity.FAULT)
    if _is_invalid_temperature(snapshot.local_temp_c):
        decision.faults.append(FAULT_LM35_SENSOR_INVALID)
        decision.severity = _highest_severity(decision.severity, Severity.FAULT)
    if _is_invalid_temperature(snapshot.battery_temp_c):
        decision.faults.append(FAULT_NTC_SENSOR_INVALID)
        decision.severity = _highest_severity(decision.severity, Severity.FAULT)
    # --------------------------------------------------------
    # BATTERY POLICY
    # --------------------------------------------------------
    battery_valid = not _is_invalid_voltage(snapshot.battery_voltage)
    if battery_valid and snapshot.battery_voltage is not None:
        battery_bucket = battery_state_from_voltage(snapshot.battery_voltage)
        if battery_bucket == "WARNING":
            decision.warnings.append(WARN_BATTERY_LOW)
            decision.faults.append(FAULT_BATTERY_LOW)
            decision.severity = _highest_severity(decision.severity, Severity.WARNING)
        elif battery_bucket == "CRITICAL":
            decision.faults.append(FAULT_BATTERY_CRITICAL)
            decision.severity = _highest_severity(decision.severity, Severity.CRITICAL)
        elif battery_bucket == "SHUTDOWN":
            decision.faults.append(FAULT_BATTERY_CRITICAL)
            decision.severity = _highest_severity(decision.severity, Severity.SHUTDOWN)
            decision.request_shutdown = True
    # --------------------------------------------------------
    # THERMAL POLICY - LOCAL LM35
    # --------------------------------------------------------
    local_temp_valid = not _is_invalid_temperature(snapshot.local_temp_c)
    if local_temp_valid and snapshot.local_temp_c is not None:
        local_temp_bucket = thermal_state_from_temp(snapshot.local_temp_c, LM35_THERMAL_PROFILE)
        if local_temp_bucket == "WARNING":
            decision.warnings.append(WARN_TEMP_HIGH)
            decision.force_fan_on = True
            decision.severity = _highest_severity(decision.severity, Severity.WARNING)
        elif local_temp_bucket == "CRITICAL":
            decision.faults.append(FAULT_REMOTE_OVERHEAT)
            decision.force_fan_on = True
            decision.severity = _highest_severity(decision.severity, Severity.CRITICAL)
        elif local_temp_bucket == "SHUTDOWN":
            decision.faults.append(FAULT_REMOTE_OVERHEAT)
            decision.force_fan_on = True
            decision.request_shutdown = True
            decision.severity = _highest_severity(decision.severity, Severity.SHUTDOWN)
    # --------------------------------------------------------
    # THERMAL POLICY - BATTERY NTC
    # --------------------------------------------------------
    battery_temp_valid = not _is_invalid_temperature(snapshot.battery_temp_c)
    if battery_temp_valid and snapshot.battery_temp_c is not None:
        battery_temp_bucket = thermal_state_from_temp(snapshot.battery_temp_c, NTC_BATTERY_THERMAL_PROFILE)
        if battery_temp_bucket == "WARNING":
            decision.warnings.append(WARN_TEMP_HIGH)
            decision.force_fan_on = True
            decision.severity = _highest_severity(decision.severity, Severity.WARNING)
        elif battery_temp_bucket == "CRITICAL":
            decision.faults.append(FAULT_BATTERY_OVERHEAT)
            decision.force_fan_on = True
            decision.severity = _highest_severity(decision.severity, Severity.CRITICAL)
        elif battery_temp_bucket == "SHUTDOWN":
            decision.faults.append(FAULT_BATTERY_OVERHEAT)
            decision.force_fan_on = True
            decision.request_shutdown = True
            decision.severity = _highest_severity(decision.severity, Severity.SHUTDOWN)
    # --------------------------------------------------------
    # FAN FAILURE POLICY
    # --------------------------------------------------------
    if decision.force_fan_on and not snapshot.remote_fan_feedback_ok:
        decision.faults.append(FAULT_REMOTE_FAN_FAILURE)
        decision.severity = _highest_severity(decision.severity, Severity.FAULT)
    # --------------------------------------------------------
    # NETWORK / LINK POLICY
    # --------------------------------------------------------
    if not snapshot.network_online:
        decision.faults.append(FAULT_NETWORK_LINK_LOST)
        decision.severity = _highest_severity(decision.severity, Severity.FAULT)
    if snapshot.network_weak:
        decision.warnings.append(WARN_NETWORK_WEAK)
        decision.severity = _highest_severity(decision.severity, Severity.WARNING)
    if not snapshot.master_link_ok:
        decision.faults.append(FAULT_MASTER_LINK_TIMEOUT)
        decision.severity = _highest_severity(decision.severity, Severity.FAULT)
    # --------------------------------------------------------
    # UI POLICY
    # --------------------------------------------------------
    # UI not ready is not immediately a shutdown condition, but it should latch a fault view.
    if not snapshot.ui_ready:
        decision.ui_fault_latched = True
        decision.severity = _highest_severity(decision.severity, Severity.WARNING)
    # --------------------------------------------------------
    # FINAL SAFETY GATES
    # --------------------------------------------------------
    if decision.severity in (Severity.CRITICAL, Severity.SHUTDOWN):
        decision.accept_user_control = False
        decision.allow_new_motion_commands = False
        decision.ui_fault_latched = True
    elif decision.severity == Severity.FAULT:
        decision.accept_user_control = True
        decision.allow_new_motion_commands = False
        decision.ui_fault_latched = True
    elif decision.severity == Severity.WARNING:
        decision.accept_user_control = True
        decision.allow_new_motion_commands = True
    # --------------------------------------------------------
    # BUZZER CLASS
    # --------------------------------------------------------
    if decision.severity == Severity.WARNING:
        decision.buzzer_class = BuzzerClass.WARNING
    elif decision.severity == Severity.FAULT:
        decision.buzzer_class = BuzzerClass.FAULT
    elif decision.severity in (Severity.CRITICAL, Severity.SHUTDOWN):
        decision.buzzer_class = BuzzerClass.CRITICAL
    else:
        decision.buzzer_class = BuzzerClass.NONE
    # --------------------------------------------------------
    # PRIMARY STATE / THERMAL STATE / SUMMARY
    # --------------------------------------------------------
    decision.primary_state = _map_severity_to_primary_state(decision.severity, snapshot.system_active)
    decision.thermal_state = _map_thermal_bucket(snapshot.local_temp_c)
    decision.summary = _build_summary(decision)
    return decision
# ============================================================
# SUMMARY BUILDER
# ============================================================
def _build_summary(decision: FaultPolicyDecision) -> str:
    if decision.severity == Severity.NORMAL:
        return "System healthy and ready."
    parts: list[str] = [f"Severity={decision.severity.value}"]
    if decision.warnings:
        parts.append("Warnings=" + ",".join(decision.warnings))
    if decision.faults:
        parts.append("Faults=" + ",".join(decision.faults))
    if decision.force_fan_on:
        parts.append("ForceFan=YES")
    if decision.request_shutdown:
        parts.append("Shutdown=REQUESTED")
    if not decision.allow_new_motion_commands:
        parts.append("Motion=LOCKED")
    return " | ".join(parts)
# ============================================================
# DEFAULT SNAPSHOT HELPERS
# ============================================================
def build_boot_snapshot() -> HealthSnapshot:
    return HealthSnapshot(
        battery_voltage=BATTERY_PROFILE.nominal_voltage,
        battery_temp_c=25.0,
        local_temp_c=25.0,
        adc1_online=True,
        adc2_online=True,
        i2c_ok=True,
        network_online=True,
        network_weak=False,
        master_link_ok=True,
        remote_fan_feedback_ok=True,
        ui_ready=True,
        system_active=False,
    )
def build_safe_idle_snapshot() -> HealthSnapshot:
    return HealthSnapshot(
        battery_voltage=11.6,
        battery_temp_c=28.0,
        local_temp_c=31.0,
        adc1_online=True,
        adc2_online=True,
        i2c_ok=True,
        network_online=True,
        network_weak=False,
        master_link_ok=True,
        remote_fan_feedback_ok=True,
        ui_ready=True,
        system_active=False,
    )


# ============================================================
# MODULE-R005
# ============================================================

# hardware/remotepi_calibration_profile.py
"""
MODULE-R005
RemotePi Calibration Profile
----------------------------
Purpose:
    Field calibration constants for RemotePi hardware.
Scope:
    - Joystick real center offsets
    - ADC raw min/max learned values
    - Battery divider real scale factor
    - LM35 offset correction
    - NTC curve fine tuning
    - Fan PWM calibration
Important:
    These values are updated after real device commissioning.
"""
from dataclasses import dataclass
from typing import Final
# ============================================================
# JOYSTICK CALIBRATION
# ============================================================
@dataclass(frozen=True)
class JoystickCalibration:
    center_raw: int
    min_raw: int
    max_raw: int
    invert: bool
LEFT_JOYSTICK_X_CAL: Final[JoystickCalibration] = JoystickCalibration(
    center_raw=16210,
    min_raw=420,
    max_raw=32400,
    invert=False,
)
LEFT_JOYSTICK_Y_CAL: Final[JoystickCalibration] = JoystickCalibration(
    center_raw=16380,
    min_raw=390,
    max_raw=32350,
    invert=True,
)
RIGHT_JOYSTICK_X_CAL: Final[JoystickCalibration] = JoystickCalibration(
    center_raw=16190,
    min_raw=450,
    max_raw=32320,
    invert=False,
)
RIGHT_JOYSTICK_Y_CAL: Final[JoystickCalibration] = JoystickCalibration(
    center_raw=16420,
    min_raw=410,
    max_raw=32450,
    invert=True,
)
# ============================================================
# BATTERY DIVIDER CALIBRATION
# ============================================================
@dataclass(frozen=True)
class BatteryDividerCalibration:
    scale_factor: float
    voltage_offset: float
BATTERY_DIVIDER_CAL: Final[BatteryDividerCalibration] = BatteryDividerCalibration(
    scale_factor=5.18,      # measured real multiplier
    voltage_offset=0.07,    # measured offset correction
)
# ============================================================
# LM35 CALIBRATION
# ============================================================
@dataclass(frozen=True)
class LM35Calibration:
    mv_per_c: float
    offset_c: float
LM35_CAL: Final[LM35Calibration] = LM35Calibration(
    mv_per_c=10.0,
    offset_c=-1.2,
)
# ============================================================
# NTC CALIBRATION
# ============================================================
@dataclass(frozen=True)
class NTCCalibration:
    beta: float
    nominal_res: float
    nominal_temp_c: float
    offset_c: float
NTC_CAL: Final[NTCCalibration] = NTCCalibration(
    beta=3950.0,
    nominal_res=10000.0,
    nominal_temp_c=25.0,
    offset_c=1.8,
)
# ============================================================
# FAN PWM CALIBRATION
# ============================================================
@dataclass(frozen=True)
class FanCalibration:
    pwm_start: float
    pwm_nominal: float
    pwm_max: float
REMOTE_FAN_CAL: Final[FanCalibration] = FanCalibration(
    pwm_start=0.28,
    pwm_nominal=0.55,
    pwm_max=1.0,
)
# ============================================================
# HELPER FUNCTIONS
# ============================================================
def correct_battery_voltage(raw_voltage: float) -> float:
    return raw_voltage * BATTERY_DIVIDER_CAL.scale_factor + BATTERY_DIVIDER_CAL.voltage_offset
def correct_lm35_temp(raw_temp_c: float) -> float:
    return raw_temp_c + LM35_CAL.offset_c
def correct_ntc_temp(raw_temp_c: float) -> float:
    return raw_temp_c + NTC_CAL.offset_c
def normalize_joystick(raw: int, cal: JoystickCalibration) -> float:
    span_low = cal.center_raw - cal.min_raw
    span_high = cal.max_raw - cal.center_raw
    if raw >= cal.center_raw:
        value = (raw - cal.center_raw) / span_high
    else:
        value = (raw - cal.center_raw) / span_low
    value = max(-1.0, min(1.0, value))
    if cal.invert:
        value *= -1.0
    return value


# ============================================================
# MODULE-R006
# ============================================================

# runtime/remotepi_input_manager.py
"""
MODULE-R006
RemotePi Input Manager
----------------------
Purpose:
    Real-time operator input processing layer.
Responsibilities:
    - Read joystick analog channels via ADS1115
    - Apply calibration + normalization
    - Apply shaping / deadzone
    - Detect movement events
    - Read joystick digital buttons
    - Merge with UI event queue
"""
import time
from dataclasses import dataclass
from typing import Callable, Optional
from hardware.remotepi_gpio_binding_map import (
    ADC_CHANNEL_BINDINGS,
    JOYSTICK_GROUPS,
    GPIO_BINDINGS,
)
from hardware.remotepi_hw_profile import (
    normalize_adc_to_unit,
    shape_joystick_value,
    LEFT_JOYSTICK_X_PROFILE,
    LEFT_JOYSTICK_Y_PROFILE,
    RIGHT_JOYSTICK_X_PROFILE,
    RIGHT_JOYSTICK_Y_PROFILE,
)
from hardware.remotepi_calibration_profile import (
    LEFT_JOYSTICK_X_CAL,
    LEFT_JOYSTICK_Y_CAL,
    RIGHT_JOYSTICK_X_CAL,
    RIGHT_JOYSTICK_Y_CAL,
    normalize_joystick,
)
from hardware.remotepi_signal_names import (
    EVENT_LEFT_JOYSTICK_MOVE,
    EVENT_RIGHT_JOYSTICK_MOVE,
    EVENT_LEFT_JOYSTICK_BUTTON_SHORT,
    EVENT_RIGHT_JOYSTICK_BUTTON_SHORT,
)
# ============================================================
# DATA MODELS
# ============================================================
@dataclass
class JoystickState:
    x: float = 0.0
    y: float = 0.0
    last_button: bool = False
    last_event_ts: float = 0.0
# ============================================================
# MAIN CLASS
# ============================================================
class RemotePiInputManager:
    def __init__(
        self,
        adc_reader: Callable[[str], int],
        gpio_reader: Callable[[str], bool],
        ui_event_source: Callable[[], Optional[str]],
        event_sink: Callable[[str, dict], None],
        loop_dt: float = 0.05,
    ):
        """
        adc_reader(channel_name) -> raw int
        gpio_reader(gpio_name) -> bool
        ui_event_source() -> event or None
        event_sink(event_name, payload_dict)
        """
        self.adc_reader = adc_reader
        self.gpio_reader = gpio_reader
        self.ui_event_source = ui_event_source
        self.event_sink = event_sink
        self.loop_dt = loop_dt
        self.left = JoystickState()
        self.right = JoystickState()
        self.deadzone = 0.05
    # --------------------------------------------------------
    def _process_axis(self, raw: int, cal, profile) -> float:
        v = normalize_joystick(raw, cal)
        v = shape_joystick_value(v, profile)
        return v
    # --------------------------------------------------------
    def _read_left(self):
        raw_x = self.adc_reader("LEFT_JOYSTICK_X")
        raw_y = self.adc_reader("LEFT_JOYSTICK_Y")
        x = self._process_axis(raw_x, LEFT_JOYSTICK_X_CAL, LEFT_JOYSTICK_X_PROFILE)
        y = self._process_axis(raw_y, LEFT_JOYSTICK_Y_CAL, LEFT_JOYSTICK_Y_PROFILE)
        if abs(x - self.left.x) > self.deadzone or abs(y - self.left.y) > self.deadzone:
            self.left.x = x
            self.left.y = y
            self.event_sink(EVENT_LEFT_JOYSTICK_MOVE, {
                "x": x,
                "y": y,
                "ts": time.time()
            })
        btn = self.gpio_reader("LEFT_JOYSTICK_BTN")
        if btn and not self.left.last_button:
            self.event_sink(EVENT_LEFT_JOYSTICK_BUTTON_SHORT, {})
        self.left.last_button = btn
    # --------------------------------------------------------
    def _read_right(self):
        raw_x = self.adc_reader("RIGHT_JOYSTICK_X")
        raw_y = self.adc_reader("RIGHT_JOYSTICK_Y")
        x = self._process_axis(raw_x, RIGHT_JOYSTICK_X_CAL, RIGHT_JOYSTICK_X_PROFILE)
        y = self._process_axis(raw_y, RIGHT_JOYSTICK_Y_CAL, RIGHT_JOYSTICK_Y_PROFILE)
        if abs(x - self.right.x) > self.deadzone or abs(y - self.right.y) > self.deadzone:
            self.right.x = x
            self.right.y = y
            self.event_sink(EVENT_RIGHT_JOYSTICK_MOVE, {
                "x": x,
                "y": y,
                "ts": time.time()
            })
        btn = self.gpio_reader("RIGHT_JOYSTICK_BTN")
        if btn and not self.right.last_button:
            self.event_sink(EVENT_RIGHT_JOYSTICK_BUTTON_SHORT, {})
        self.right.last_button = btn
    # --------------------------------------------------------
    def _merge_ui(self):
        evt = self.ui_event_source()
        if evt:
            self.event_sink(evt, {"ts": time.time()})
    # --------------------------------------------------------
    def run_forever(self):
        while True:
            self._read_left()
            self._read_right()
            self._merge_ui()
            time.sleep(self.loop_dt)


# ============================================================
# MODULE-R007
# ============================================================

# runtime/remotepi_telemetry_manager.py
"""
MODULE-R007
RemotePi Telemetry Manager
--------------------------
Purpose:
    Real-time health and telemetry processing layer for RemotePi.
Responsibilities:
    - Read battery voltage via ADS1115
    - Read LM35 and NTC thermal channels
    - Apply calibration corrections
    - Decide local fan demand
    - Build HealthSnapshot for fault policy
    - Publish telemetry and heartbeat events
"""
import time
from dataclasses import asdict, dataclass
from typing import Callable, Optional
from hardware.remotepi_hw_profile import (
    LM35_THERMAL_PROFILE,
    NTC_BATTERY_THERMAL_PROFILE,
    fan_should_run,
)
from hardware.remotepi_calibration_profile import (
    correct_battery_voltage,
    correct_lm35_temp,
    correct_ntc_temp,
)
from hardware.remotepi_fault_policy import (
    HealthSnapshot,
    FaultPolicyDecision,
    evaluate_fault_policy,
)
from hardware.remotepi_signal_names import (
    SIG_BATTERY_VOLTAGE,
    SIG_BATTERY_TEMP_C,
    SIG_LM35_TEMP_C,
    SIG_REMOTE_FAN_ACTIVE,
    SIG_SYSTEM_HEARTBEAT,
    SIG_SYSTEM_UPTIME_SEC,
    TOPIC_TELEMETRY,
    TOPIC_HEALTH,
)
# ============================================================
# DATA MODELS
# ============================================================
@dataclass
class TelemetryFrame:
    ts: float
    uptime_sec: float
    battery_voltage: float
    battery_temp_c: float
    local_temp_c: float
    remote_fan_active: bool
    network_online: bool
    network_weak: bool
    master_link_ok: bool
    adc1_online: bool
    adc2_online: bool
    i2c_ok: bool
    ui_ready: bool
    system_active: bool
# ============================================================
# MAIN CLASS
# ============================================================
class RemotePiTelemetryManager:
    def __init__(
        self,
        adc_reader: Callable[[str], float],
        output_writer: Callable[[str, bool], None],
        event_sink: Callable[[str, dict], None],
        network_status_reader: Callable[[], dict],
        ui_health_reader: Callable[[], bool],
        system_active_reader: Callable[[], bool],
        loop_dt: float = 0.25,
    ):
        """
        adc_reader(channel_name) -> raw/engineering float
            Expected channel names:
                - BATTERY_VOLTAGE_SENSE
                - LM35_TEMP
                - NTC_BATTERY_TEMP
        output_writer(output_name, state)
            Example:
                output_writer("REMOTE_FAN_CTRL", True)
        event_sink(topic_or_event_name, payload_dict)
        network_status_reader() -> {
            "network_online": bool,
            "network_weak": bool,
            "master_link_ok": bool,
            "adc1_online": bool,
            "adc2_online": bool,
            "i2c_ok": bool,
        }
        ui_health_reader() -> bool
        system_active_reader() -> bool
        """
        self.adc_reader = adc_reader
        self.output_writer = output_writer
        self.event_sink = event_sink
        self.network_status_reader = network_status_reader
        self.ui_health_reader = ui_health_reader
        self.system_active_reader = system_active_reader
        self.loop_dt = loop_dt
        self._boot_ts = time.time()
        self._fan_running = False
        self._last_policy: Optional[FaultPolicyDecision] = None
    # --------------------------------------------------------
    def _uptime(self) -> float:
        return time.time() - self._boot_ts
    # --------------------------------------------------------
    def _read_battery_voltage(self) -> float:
        raw = self.adc_reader("BATTERY_VOLTAGE_SENSE")
        return correct_battery_voltage(float(raw))
    def _read_lm35_temp(self) -> float:
        raw = self.adc_reader("LM35_TEMP")
        return correct_lm35_temp(float(raw))
    def _read_ntc_temp(self) -> float:
        raw = self.adc_reader("NTC_BATTERY_TEMP")
        return correct_ntc_temp(float(raw))
    # --------------------------------------------------------
    def _build_snapshot(self) -> HealthSnapshot:
        net = self.network_status_reader()
        battery_voltage = self._read_battery_voltage()
        local_temp_c = self._read_lm35_temp()
        battery_temp_c = self._read_ntc_temp()
        return HealthSnapshot(
            battery_voltage=battery_voltage,
            battery_temp_c=battery_temp_c,
            local_temp_c=local_temp_c,
            adc1_online=bool(net.get("adc1_online", True)),
            adc2_online=bool(net.get("adc2_online", True)),
            i2c_ok=bool(net.get("i2c_ok", True)),
            network_online=bool(net.get("network_online", True)),
            network_weak=bool(net.get("network_weak", False)),
            master_link_ok=bool(net.get("master_link_ok", True)),
            remote_fan_feedback_ok=True,
            ui_ready=self.ui_health_reader(),
            system_active=self.system_active_reader(),
        )
    # --------------------------------------------------------
    def _apply_fan_policy(self, snapshot: HealthSnapshot, decision: FaultPolicyDecision) -> bool:
        demand_local = False
        if snapshot.local_temp_c is not None:
            demand_local = fan_should_run(
                snapshot.local_temp_c,
                LM35_THERMAL_PROFILE,
                currently_running=self._fan_running,
            )
        if snapshot.battery_temp_c is not None:
            demand_battery = fan_should_run(
                snapshot.battery_temp_c,
                NTC_BATTERY_THERMAL_PROFILE,
                currently_running=self._fan_running,
            )
            demand_local = demand_local or demand_battery
        final_fan_state = demand_local or decision.force_fan_on
        if final_fan_state != self._fan_running:
            self.output_writer("REMOTE_FAN_CTRL", final_fan_state)
            self._fan_running = final_fan_state
        return self._fan_running
    # --------------------------------------------------------
    def _build_frame(
        self,
        snapshot: HealthSnapshot,
        fan_active: bool,
    ) -> TelemetryFrame:
        net = self.network_status_reader()
        return TelemetryFrame(
            ts=time.time(),
            uptime_sec=self._uptime(),
            battery_voltage=float(snapshot.battery_voltage or 0.0),
            battery_temp_c=float(snapshot.battery_temp_c or 0.0),
            local_temp_c=float(snapshot.local_temp_c or 0.0),
            remote_fan_active=fan_active,
            network_online=bool(net.get("network_online", True)),
            network_weak=bool(net.get("network_weak", False)),
            master_link_ok=bool(net.get("master_link_ok", True)),
            adc1_online=bool(net.get("adc1_online", True)),
            adc2_online=bool(net.get("adc2_online", True)),
            i2c_ok=bool(net.get("i2c_ok", True)),
            ui_ready=self.ui_health_reader(),
            system_active=self.system_active_reader(),
        )
    # --------------------------------------------------------
    def _publish_frame(self, frame: TelemetryFrame) -> None:
        payload = asdict(frame)
        self.event_sink(TOPIC_TELEMETRY, payload)
        self.event_sink(SIG_BATTERY_VOLTAGE, {
            "value": frame.battery_voltage,
            "ts": frame.ts,
        })
        self.event_sink(SIG_BATTERY_TEMP_C, {
            "value": frame.battery_temp_c,
            "ts": frame.ts,
        })
        self.event_sink(SIG_LM35_TEMP_C, {
            "value": frame.local_temp_c,
            "ts": frame.ts,
        })
        self.event_sink(SIG_REMOTE_FAN_ACTIVE, {
            "value": frame.remote_fan_active,
            "ts": frame.ts,
        })
        self.event_sink(SIG_SYSTEM_UPTIME_SEC, {
            "value": frame.uptime_sec,
            "ts": frame.ts,
        })
    # --------------------------------------------------------
    def _publish_health(self, decision: FaultPolicyDecision, frame: TelemetryFrame) -> None:
        self.event_sink(TOPIC_HEALTH, {
            "ts": frame.ts,
            "severity": decision.severity.value,
            "primary_state": decision.primary_state,
            "thermal_state": decision.thermal_state,
            "warnings": list(decision.warnings),
            "faults": list(decision.faults),
            "force_fan_on": decision.force_fan_on,
            "request_shutdown": decision.request_shutdown,
            "accept_user_control": decision.accept_user_control,
            "allow_new_motion_commands": decision.allow_new_motion_commands,
            "ui_fault_latched": decision.ui_fault_latched,
            "summary": decision.summary,
        })
    # --------------------------------------------------------
    def _publish_heartbeat(self, frame: TelemetryFrame) -> None:
        self.event_sink(SIG_SYSTEM_HEARTBEAT, {
            "ts": frame.ts,
            "uptime_sec": frame.uptime_sec,
            "network_online": frame.network_online,
            "master_link_ok": frame.master_link_ok,
            "ui_ready": frame.ui_ready,
        })
    # --------------------------------------------------------
    def tick(self) -> FaultPolicyDecision:
        snapshot = self._build_snapshot()
        decision = evaluate_fault_policy(snapshot)
        fan_active = self._apply_fan_policy(snapshot, decision)
        frame = self._build_frame(snapshot, fan_active)
        self._publish_frame(frame)
        self._publish_health(decision, frame)
        self._publish_heartbeat(frame)
        self._last_policy = decision
        return decision
    # --------------------------------------------------------
    def run_forever(self) -> None:
        while True:
            self.tick()
            time.sleep(self.loop_dt)
    # --------------------------------------------------------
    @property
    def last_policy(self) -> Optional[FaultPolicyDecision]:
        return self._last_policy


# ============================================================
# MODULE-R008
# ============================================================

# runtime/remotepi_event_router.py
"""
MODULE-R008
RemotePi Event Router
---------------------
Purpose:
    Central event routing layer for RemotePi runtime.
Responsibilities:
    - Accept UI events and joystick events
    - Convert them into normalized command events
    - Respect current safety policy
    - Respect current active control mode
    - Gate motion commands when faults/critical states are active
"""
import time
from dataclasses import dataclass, field
from typing import Callable, Final, Optional
from hardware.remotepi_fault_policy import FaultPolicyDecision, Severity
from hardware.remotepi_signal_names import (
    CMD_BUZZER_BUTTON_ACK,
    CMD_FAULT_ACK,
    CMD_FAULT_VIEW_OPEN,
    CMD_JOYSTICK_LEFT_UPDATE,
    CMD_JOYSTICK_RIGHT_UPDATE,
    CMD_LIGHT_HIGH_BEAM_TOGGLE,
    CMD_LIGHT_LOW_BEAM_TOGGLE,
    CMD_LIGHT_PARKING_TOGGLE,
    CMD_LIGHT_RIG_FLOOR_TOGGLE,
    CMD_LIGHT_ROTATION_TOGGLE,
    CMD_LIGHT_SIGNAL_LHR_TOGGLE,
    CMD_MODE_AUTONOM,
    CMD_MODE_DRIVER,
    CMD_MODE_DRAWWORKS,
    CMD_MODE_MENU,
    CMD_MODE_ROTARY_TABLE,
    CMD_MODE_SANDLINE,
    CMD_MODE_WHEEL,
    CMD_MODE_WINCH,
    CMD_SYSTEM_START,
    CMD_SYSTEM_STOP,
    EVENT_LEFT_JOYSTICK_BUTTON_LONG,
    EVENT_LEFT_JOYSTICK_BUTTON_SHORT,
    EVENT_LEFT_JOYSTICK_MOVE,
    EVENT_RIGHT_JOYSTICK_BUTTON_LONG,
    EVENT_RIGHT_JOYSTICK_BUTTON_SHORT,
    EVENT_RIGHT_JOYSTICK_MOVE,
    EVENT_UI_AUTONOM,
    EVENT_UI_DRIVER,
    EVENT_UI_DRAWWORKS,
    EVENT_UI_FAULT,
    EVENT_UI_HIGH_BEAM_LIGHT,
    EVENT_UI_LOW_BEAM_LIGHT,
    EVENT_UI_MENU,
    EVENT_UI_PARKING_LIGHT,
    EVENT_UI_RIG_FLOOR_LIGHT,
    EVENT_UI_ROTARY_TABLE,
    EVENT_UI_SANDLINE,
    EVENT_UI_SIGNAL_LHR_LIGHT,
    EVENT_UI_START_STOP,
    EVENT_UI_WHEEL,
    EVENT_UI_WINCH,
    STATE_CONTROL_MODE_AUTONOM,
    STATE_CONTROL_MODE_DRIVER,
    STATE_CONTROL_MODE_DRAWWORKS,
    STATE_CONTROL_MODE_MENU,
    STATE_CONTROL_MODE_ROTARY_TABLE,
    STATE_CONTROL_MODE_SANDLINE,
    STATE_CONTROL_MODE_WHEEL,
    STATE_CONTROL_MODE_WINCH,
    TOPIC_COMMANDS,
    TOPIC_EVENTS,
)
# ============================================================
# CONSTANT TABLES
# ============================================================
UI_MODE_EVENT_TO_STATE: Final[dict[str, str]] = {
    EVENT_UI_WHEEL: STATE_CONTROL_MODE_WHEEL,
    EVENT_UI_DRIVER: STATE_CONTROL_MODE_DRIVER,
    EVENT_UI_DRAWWORKS: STATE_CONTROL_MODE_DRAWWORKS,
    EVENT_UI_SANDLINE: STATE_CONTROL_MODE_SANDLINE,
    EVENT_UI_WINCH: STATE_CONTROL_MODE_WINCH,
    EVENT_UI_ROTARY_TABLE: STATE_CONTROL_MODE_ROTARY_TABLE,
    EVENT_UI_AUTONOM: STATE_CONTROL_MODE_AUTONOM,
    EVENT_UI_MENU: STATE_CONTROL_MODE_MENU,
}
UI_MODE_EVENT_TO_COMMAND: Final[dict[str, str]] = {
    EVENT_UI_WHEEL: CMD_MODE_WHEEL,
    EVENT_UI_DRIVER: CMD_MODE_DRIVER,
    EVENT_UI_DRAWWORKS: CMD_MODE_DRAWWORKS,
    EVENT_UI_SANDLINE: CMD_MODE_SANDLINE,
    EVENT_UI_WINCH: CMD_MODE_WINCH,
    EVENT_UI_ROTARY_TABLE: CMD_MODE_ROTARY_TABLE,
    EVENT_UI_AUTONOM: CMD_MODE_AUTONOM,
    EVENT_UI_MENU: CMD_MODE_MENU,
}
UI_ACTION_EVENT_TO_COMMAND: Final[dict[str, str]] = {
    EVENT_UI_PARKING_LIGHT: CMD_LIGHT_PARKING_TOGGLE,
    EVENT_UI_LOW_BEAM_LIGHT: CMD_LIGHT_LOW_BEAM_TOGGLE,
    EVENT_UI_HIGH_BEAM_LIGHT: CMD_LIGHT_HIGH_BEAM_TOGGLE,
    EVENT_UI_SIGNAL_LHR_LIGHT: CMD_LIGHT_SIGNAL_LHR_TOGGLE,
    EVENT_UI_RIG_FLOOR_LIGHT: CMD_LIGHT_RIG_FLOOR_TOGGLE,
    EVENT_UI_ROTATION_LIGHT: CMD_LIGHT_ROTATION_TOGGLE,
}
MOTION_ENABLED_MODES: Final[set[str]] = {
    STATE_CONTROL_MODE_WHEEL,
    STATE_CONTROL_MODE_DRIVER,
    STATE_CONTROL_MODE_DRAWWORKS,
    STATE_CONTROL_MODE_SANDLINE,
    STATE_CONTROL_MODE_WINCH,
    STATE_CONTROL_MODE_ROTARY_TABLE,
}
NON_MOTION_MODES: Final[set[str]] = {
    STATE_CONTROL_MODE_AUTONOM,
    STATE_CONTROL_MODE_MENU,
}
# ============================================================
# DATA MODELS
# ============================================================
@dataclass
class RouterState:
    active_mode: str = STATE_CONTROL_MODE_MENU
    system_running: bool = False
    last_fault_policy: Optional[FaultPolicyDecision] = None
    last_event_ts: float = field(default_factory=time.time)
# ============================================================
# MAIN CLASS
# ============================================================
class RemotePiEventRouter:
    def __init__(
        self,
        command_sink: Callable[[str, dict], None],
        event_sink: Callable[[str, dict], None],
    ):
        """
        command_sink(command_name, payload)
            Used for normalized command output toward upper layers / transport.
        event_sink(topic_or_event_name, payload)
            Used for internal observability/logging.
        """
        self.command_sink = command_sink
        self.event_sink = event_sink
        self.state = RouterState()
    # --------------------------------------------------------
    def update_fault_policy(self, decision: FaultPolicyDecision) -> None:
        self.state.last_fault_policy = decision
        self.event_sink(TOPIC_EVENTS, {
            "ts": time.time(),
            "type": "FAULT_POLICY_UPDATE",
            "severity": decision.severity.value,
            "primary_state": decision.primary_state,
            "allow_new_motion_commands": decision.allow_new_motion_commands,
            "accept_user_control": decision.accept_user_control,
        })
    # --------------------------------------------------------
    def _policy(self) -> FaultPolicyDecision:
        if self.state.last_fault_policy is None:
            # Safe default when no telemetry decision has arrived yet
            return FaultPolicyDecision(
                severity=Severity.WARNING,
                primary_state="STATE_WARNING",
                thermal_state="STATE_TEMP_WARNING",
                warnings=["BOOTSTRAP_POLICY_MISSING"],
                faults=[],
                force_fan_on=False,
                request_shutdown=False,
                buzzer_class="WARNING",  # type: ignore[arg-type]
                ui_fault_latched=False,
                accept_user_control=True,
                allow_new_motion_commands=False,
                summary="No fault policy available yet; motion locked by default.",
            )
        return self.state.last_fault_policy
    # --------------------------------------------------------
    def _emit_command(self, command: str, payload: Optional[dict] = None) -> None:
        payload = payload or {}
        payload.setdefault("ts", time.time())
        payload.setdefault("mode", self.state.active_mode)
        self.command_sink(command, payload)
        self.event_sink(TOPIC_COMMANDS, {
            "command": command,
            **payload,
        })
    # --------------------------------------------------------
    def _ack_button(self) -> None:
        self._emit_command(CMD_BUZZER_BUTTON_ACK, {})
    # --------------------------------------------------------
    def _set_mode_from_ui_event(self, event_name: str) -> None:
        next_state = UI_MODE_EVENT_TO_STATE[event_name]
        next_command = UI_MODE_EVENT_TO_COMMAND[event_name]
        self.state.active_mode = next_state
        self._emit_command(next_command, {"selected_mode": next_state})
    # --------------------------------------------------------
    def _handle_start_stop(self) -> None:
        policy = self._policy()
        if self.state.system_running:
            self.state.system_running = False
            self._emit_command(CMD_SYSTEM_STOP, {"reason": "UI_START_STOP"})
            return
        # Start request
        if policy.accept_user_control and not policy.request_shutdown:
            self.state.system_running = True
            self._emit_command(CMD_SYSTEM_START, {"reason": "UI_START_STOP"})
        else:
            self.event_sink(TOPIC_EVENTS, {
                "ts": time.time(),
                "type": "START_BLOCKED_BY_POLICY",
                "severity": policy.severity.value,
                "summary": policy.summary,
            })
    # --------------------------------------------------------
    def _handle_fault_button(self) -> None:
        policy = self._policy()
        if policy.ui_fault_latched or policy.faults:
            self._emit_command(CMD_FAULT_VIEW_OPEN, {
                "faults": list(policy.faults),
                "warnings": list(policy.warnings),
            })
        else:
            self._emit_command(CMD_FAULT_ACK, {"reason": "UI_FAULT_TAP_NO_ACTIVE_FAULT"})
    # --------------------------------------------------------
    def _handle_ui_event(self, event_name: str, payload: dict) -> None:
        self.state.last_event_ts = time.time()
        if event_name in UI_MODE_EVENT_TO_STATE:
            self._set_mode_from_ui_event(event_name)
            self._ack_button()
            return
        if event_name == EVENT_UI_START_STOP:
            self._handle_start_stop()
            self._ack_button()
            return
        if event_name == EVENT_UI_FAULT:
            self._handle_fault_button()
            self._ack_button()
            return
        if event_name in UI_ACTION_EVENT_TO_COMMAND:
            self._emit_command(UI_ACTION_EVENT_TO_COMMAND[event_name], payload)
            self._ack_button()
            return
        self.event_sink(TOPIC_EVENTS, {
            "ts": time.time(),
            "type": "UNHANDLED_UI_EVENT",
            "event": event_name,
            "payload": payload,
        })
    # --------------------------------------------------------
    def _motion_allowed(self) -> bool:
        return self._policy().allow_new_motion_commands and self.state.system_running
    # --------------------------------------------------------
    def _build_motion_payload(self, side: str, payload: dict) -> dict:
        x = float(payload.get("x", 0.0))
        y = float(payload.get("y", 0.0))
        return {
            "side": side,
            "mode": self.state.active_mode,
            "x": x,
            "y": y,
            "magnitude": (x * x + y * y) ** 0.5,
            "ts": payload.get("ts", time.time()),
        }
    # --------------------------------------------------------
    def _handle_left_joystick_move(self, payload: dict) -> None:
        if self.state.active_mode not in MOTION_ENABLED_MODES:
            self.event_sink(TOPIC_EVENTS, {
                "ts": time.time(),
                "type": "LEFT_JOYSTICK_IGNORED_MODE",
                "mode": self.state.active_mode,
                "payload": payload,
            })
            return
        if not self._motion_allowed():
            self.event_sink(TOPIC_EVENTS, {
                "ts": time.time(),
                "type": "LEFT_JOYSTICK_BLOCKED_POLICY",
                "mode": self.state.active_mode,
                "payload": payload,
            })
            return
        self._emit_command(CMD_JOYSTICK_LEFT_UPDATE, self._build_motion_payload("LEFT", payload))
    # --------------------------------------------------------
    def _handle_right_joystick_move(self, payload: dict) -> None:
        if self.state.active_mode not in MOTION_ENABLED_MODES:
            self.event_sink(TOPIC_EVENTS, {
                "ts": time.time(),
                "type": "RIGHT_JOYSTICK_IGNORED_MODE",
                "mode": self.state.active_mode,
                "payload": payload,
            })
            return
        if not self._motion_allowed():
            self.event_sink(TOPIC_EVENTS, {
                "ts": time.time(),
                "type": "RIGHT_JOYSTICK_BLOCKED_POLICY",
                "mode": self.state.active_mode,
                "payload": payload,
            })
            return
        self._emit_command(CMD_JOYSTICK_RIGHT_UPDATE, self._build_motion_payload("RIGHT", payload))
    # --------------------------------------------------------
    def _handle_joystick_button(self, side: str, event_name: str, payload: dict) -> None:
        self.event_sink(TOPIC_EVENTS, {
            "ts": time.time(),
            "type": "JOYSTICK_BUTTON",
            "side": side,
            "event": event_name,
            "mode": self.state.active_mode,
            "payload": payload,
        })
        # Basit başlangıç mantığı:
        # kısa basış = ack
        # uzun basış = fault view / future shortcut
        if event_name in (EVENT_LEFT_JOYSTICK_BUTTON_SHORT, EVENT_RIGHT_JOYSTICK_BUTTON_SHORT):
            self._ack_button()
            return
        if event_name in (EVENT_LEFT_JOYSTICK_BUTTON_LONG, EVENT_RIGHT_JOYSTICK_BUTTON_LONG):
            self._emit_command(CMD_FAULT_VIEW_OPEN, {
                "reason": "JOYSTICK_LONG_PRESS",
                "side": side,
            })
            return
    # --------------------------------------------------------
    def route_event(self, event_name: str, payload: Optional[dict] = None) -> None:
        payload = payload or {}
        self.state.last_event_ts = time.time()
        if event_name.startswith("EVENT_UI_"):
            self._handle_ui_event(event_name, payload)
            return
        if event_name == EVENT_LEFT_JOYSTICK_MOVE:
            self._handle_left_joystick_move(payload)
            return
        if event_name == EVENT_RIGHT_JOYSTICK_MOVE:
            self._handle_right_joystick_move(payload)
            return
        if event_name in (EVENT_LEFT_JOYSTICK_BUTTON_SHORT, EVENT_LEFT_JOYSTICK_BUTTON_LONG):
            self._handle_joystick_button("LEFT", event_name, payload)
            return
        if event_name in (EVENT_RIGHT_JOYSTICK_BUTTON_SHORT, EVENT_RIGHT_JOYSTICK_BUTTON_LONG):
            self._handle_joystick_button("RIGHT", event_name, payload)
            return
        self.event_sink(TOPIC_EVENTS, {
            "ts": time.time(),
            "type": "UNROUTED_EVENT",
            "event": event_name,
            "payload": payload,
            "mode": self.state.active_mode,
        })


# ============================================================
# MODULE-R009
# ============================================================

# runtime/remotepi_state_store.py
"""
MODULE-R009
RemotePi State Store
--------------------
Purpose:
    Central runtime state container for RemotePi.
Responsibilities:
    - Hold live runtime state in one place
    - Track modes, warnings, faults, telemetry, health and outputs
    - Provide safe update methods
    - Provide snapshot export for HMI / logger / transport
"""
import time
from dataclasses import asdict, dataclass, field
from threading import RLock
from typing import Any, Optional
# ============================================================
# DATA MODELS
# ============================================================
@dataclass
class ModeState:
    active_mode: str = "STATE_CONTROL_MODE_MENU"
    system_running: bool = False
    autonom_enabled: bool = False
@dataclass
class ThermalState:
    local_temp_c: float = 0.0
    battery_temp_c: float = 0.0
    thermal_state: str = "STATE_TEMP_NORMAL"
    fan_active: bool = False
@dataclass
class BatteryState:
    voltage: float = 0.0
    percent_est: float = 0.0
    bucket: str = "STATE_BATTERY_NORMAL"
@dataclass
class NetworkState:
    wifi_connected: bool = False
    bluetooth_connected: bool = False
    ethernet_link: bool = False
    master_link_ok: bool = False
    network_online: bool = False
    network_weak: bool = False
@dataclass
class InputState:
    left_x: float = 0.0
    left_y: float = 0.0
    right_x: float = 0.0
    right_y: float = 0.0
    left_button_pressed: bool = False
    right_button_pressed: bool = False
    last_input_ts: float = 0.0
@dataclass
class SafetyState:
    severity: str = "NORMAL"
    primary_state: str = "STATE_BOOTING"
    accept_user_control: bool = False
    allow_new_motion_commands: bool = False
    request_shutdown: bool = False
    ui_fault_latched: bool = False
    summary: str = ""
@dataclass
class OutputState:
    remote_fan_active: bool = False
    buzzer_active: bool = False
@dataclass
class RuntimeState:
    ts: float = field(default_factory=time.time)
    boot_ts: float = field(default_factory=time.time)
    mode: ModeState = field(default_factory=ModeState)
    thermal: ThermalState = field(default_factory=ThermalState)
    battery: BatteryState = field(default_factory=BatteryState)
    network: NetworkState = field(default_factory=NetworkState)
    inputs: InputState = field(default_factory=InputState)
    safety: SafetyState = field(default_factory=SafetyState)
    outputs: OutputState = field(default_factory=OutputState)
    warnings: list[str] = field(default_factory=list)
    faults: list[str] = field(default_factory=list)
    last_event: Optional[str] = None
    last_command: Optional[str] = None
    uptime_sec: float = 0.0
# ============================================================
# MAIN STORE
# ============================================================
class RemotePiStateStore:
    def __init__(self) -> None:
        self._lock = RLock()
        self._state = RuntimeState()
    # --------------------------------------------------------
    # INTERNAL
    # --------------------------------------------------------
    def _touch(self) -> None:
        self._state.ts = time.time()
        self._state.uptime_sec = self._state.ts - self._state.boot_ts
    # --------------------------------------------------------
    # MODE / SYSTEM
    # --------------------------------------------------------
    def set_active_mode(self, mode_name: str) -> None:
        with self._lock:
            self._state.mode.active_mode = mode_name
            self._touch()
    def set_system_running(self, running: bool) -> None:
        with self._lock:
            self._state.mode.system_running = running
            self._touch()
    def set_autonom_enabled(self, enabled: bool) -> None:
        with self._lock:
            self._state.mode.autonom_enabled = enabled
            self._touch()
    # --------------------------------------------------------
    # INPUTS
    # --------------------------------------------------------
    def update_left_joystick(self, x: float, y: float) -> None:
        with self._lock:
            self._state.inputs.left_x = float(x)
            self._state.inputs.left_y = float(y)
            self._state.inputs.last_input_ts = time.time()
            self._touch()
    def update_right_joystick(self, x: float, y: float) -> None:
        with self._lock:
            self._state.inputs.right_x = float(x)
            self._state.inputs.right_y = float(y)
            self._state.inputs.last_input_ts = time.time()
            self._touch()
    def set_left_button(self, pressed: bool) -> None:
        with self._lock:
            self._state.inputs.left_button_pressed = bool(pressed)
            self._state.inputs.last_input_ts = time.time()
            self._touch()
    def set_right_button(self, pressed: bool) -> None:
        with self._lock:
            self._state.inputs.right_button_pressed = bool(pressed)
            self._state.inputs.last_input_ts = time.time()
            self._touch()
    # --------------------------------------------------------
    # BATTERY / THERMAL
    # --------------------------------------------------------
    def update_battery(self, voltage: float, percent_est: float, bucket: str) -> None:
        with self._lock:
            self._state.battery.voltage = float(voltage)
            self._state.battery.percent_est = float(percent_est)
            self._state.battery.bucket = bucket
            self._touch()
    def update_thermal(self, local_temp_c: float, battery_temp_c: float, thermal_state: str) -> None:
        with self._lock:
            self._state.thermal.local_temp_c = float(local_temp_c)
            self._state.thermal.battery_temp_c = float(battery_temp_c)
            self._state.thermal.thermal_state = thermal_state
            self._touch()
    # --------------------------------------------------------
    # NETWORK
    # --------------------------------------------------------
    def update_network(
        self,
        *,
        wifi_connected: bool,
        bluetooth_connected: bool,
        ethernet_link: bool,
        master_link_ok: bool,
        network_online: bool,
        network_weak: bool,
    ) -> None:
        with self._lock:
            self._state.network.wifi_connected = bool(wifi_connected)
            self._state.network.bluetooth_connected = bool(bluetooth_connected)
            self._state.network.ethernet_link = bool(ethernet_link)
            self._state.network.master_link_ok = bool(master_link_ok)
            self._state.network.network_online = bool(network_online)
            self._state.network.network_weak = bool(network_weak)
            self._touch()
    # --------------------------------------------------------
    # OUTPUTS
    # --------------------------------------------------------
    def set_fan_active(self, active: bool) -> None:
        with self._lock:
            self._state.outputs.remote_fan_active = bool(active)
            self._state.thermal.fan_active = bool(active)
            self._touch()
    def set_buzzer_active(self, active: bool) -> None:
        with self._lock:
            self._state.outputs.buzzer_active = bool(active)
            self._touch()
    # --------------------------------------------------------
    # SAFETY
    # --------------------------------------------------------
    def update_safety(
        self,
        *,
        severity: str,
        primary_state: str,
        accept_user_control: bool,
        allow_new_motion_commands: bool,
        request_shutdown: bool,
        ui_fault_latched: bool,
        summary: str,
        warnings: list[str],
        faults: list[str],
        thermal_state: Optional[str] = None,
    ) -> None:
        with self._lock:
            self._state.safety.severity = severity
            self._state.safety.primary_state = primary_state
            self._state.safety.accept_user_control = bool(accept_user_control)
            self._state.safety.allow_new_motion_commands = bool(allow_new_motion_commands)
            self._state.safety.request_shutdown = bool(request_shutdown)
            self._state.safety.ui_fault_latched = bool(ui_fault_latched)
            self._state.safety.summary = summary
            self._state.warnings = list(warnings)
            self._state.faults = list(faults)
            if thermal_state is not None:
                self._state.thermal.thermal_state = thermal_state
            self._touch()
    # --------------------------------------------------------
    # TRACE
    # --------------------------------------------------------
    def set_last_event(self, event_name: str) -> None:
        with self._lock:
            self._state.last_event = event_name
            self._touch()
    def set_last_command(self, command_name: str) -> None:
        with self._lock:
            self._state.last_command = command_name
            self._touch()
    # --------------------------------------------------------
    # ACCESSORS
    # --------------------------------------------------------
    def snapshot(self) -> RuntimeState:
        with self._lock:
            state_dict = asdict(self._state)
            return RuntimeState(
                ts=state_dict["ts"],
                boot_ts=state_dict["boot_ts"],
                mode=ModeState(**state_dict["mode"]),
                thermal=ThermalState(**state_dict["thermal"]),
                battery=BatteryState(**state_dict["battery"]),
                network=NetworkState(**state_dict["network"]),
                inputs=InputState(**state_dict["inputs"]),
                safety=SafetyState(**state_dict["safety"]),
                outputs=OutputState(**state_dict["outputs"]),
                warnings=list(state_dict["warnings"]),
                faults=list(state_dict["faults"]),
                last_event=state_dict["last_event"],
                last_command=state_dict["last_command"],
                uptime_sec=state_dict["uptime_sec"],
            )
    def to_dict(self) -> dict[str, Any]:
        with self._lock:
            self._touch()
            return asdict(self._state)
    # --------------------------------------------------------
    # QUICK READS
    # --------------------------------------------------------
    def get_active_mode(self) -> str:
        with self._lock:
            return self._state.mode.active_mode
    def is_system_running(self) -> bool:
        with self._lock:
            return self._state.mode.system_running
    def is_motion_allowed(self) -> bool:
        with self._lock:
            return self._state.safety.allow_new_motion_commands
    def has_faults(self) -> bool:
        with self._lock:
            return len(self._state.faults) > 0
    def get_faults(self) -> list[str]:
        with self._lock:
            return list(self._state.faults)
    def get_warnings(self) -> list[str]:
        with self._lock:
            return list(self._state.warnings)
    # --------------------------------------------------------
    # RESET
    # --------------------------------------------------------
    def clear_fault_latch(self) -> None:
        with self._lock:
            self._state.safety.ui_fault_latched = False
            self._touch()
    def clear_warnings(self) -> None:
        with self._lock:
            self._state.warnings.clear()
            self._touch()
    def reset_runtime_inputs(self) -> None:
        with self._lock:
            self._state.inputs = InputState()
            self._touch()


# ============================================================
# MODULE-R010
# ============================================================

# runtime/remotepi_runtime_controller.py
"""
MODULE-R010
RemotePi Runtime Controller
---------------------------
Purpose:
    Main runtime orchestrator for RemotePi node.
Responsibilities:
    - Wire input manager, telemetry manager, event router and state store
    - Provide unified event bus
    - Maintain runtime loop timing
    - Update state store from telemetry + router decisions
"""
import time
from typing import Callable, Optional
from runtime.remotepi_input_manager import RemotePiInputManager
from runtime.remotepi_telemetry_manager import RemotePiTelemetryManager
from runtime.remotepi_event_router import RemotePiEventRouter
from runtime.remotepi_state_store import RemotePiStateStore
from hardware.remotepi_fault_policy import FaultPolicyDecision
# ============================================================
# MAIN CONTROLLER
# ============================================================
class RemotePiRuntimeController:
    def __init__(
        self,
        adc_reader: Callable[[str], float],
        gpio_reader: Callable[[str], bool],
        gpio_writer: Callable[[str, bool], None],
        ui_event_source: Callable[[], Optional[str]],
        network_status_reader: Callable[[], dict],
        ui_health_reader: Callable[[], bool],
        system_active_reader: Callable[[], bool],
        loop_dt: float = 0.02,
    ):
        self.state_store = RemotePiStateStore()
        # ---- event sink wiring ----
        def event_sink(name: str, payload: dict):
            self._on_event(name, payload)
        def command_sink(cmd: str, payload: dict):
            self._on_command(cmd, payload)
        # ---- runtime modules ----
        self.input_mgr = RemotePiInputManager(
            adc_reader=adc_reader,
            gpio_reader=gpio_reader,
            ui_event_source=ui_event_source,
            event_sink=event_sink,
        )
        self.telemetry_mgr = RemotePiTelemetryManager(
            adc_reader=adc_reader,
            output_writer=gpio_writer,
            event_sink=event_sink,
            network_status_reader=network_status_reader,
            ui_health_reader=ui_health_reader,
            system_active_reader=system_active_reader,
        )
        self.router = RemotePiEventRouter(
            command_sink=command_sink,
            event_sink=event_sink,
        )
        self.loop_dt = loop_dt
        self._last_telemetry = 0.0
        self._telemetry_period = 0.25
    # ============================================================
    # EVENT HANDLING
    # ============================================================
    def _on_event(self, name: str, payload: dict):
        self.state_store.set_last_event(name)
        # joystick updates
        if name == "EVENT_LEFT_JOYSTICK_MOVE":
            self.state_store.update_left_joystick(payload["x"], payload["y"])
        elif name == "EVENT_RIGHT_JOYSTICK_MOVE":
            self.state_store.update_right_joystick(payload["x"], payload["y"])
        # route event into router
        self.router.route_event(name, payload)
    # ============================================================
    # COMMAND HANDLING
    # ============================================================
    def _on_command(self, name: str, payload: dict):
        self.state_store.set_last_command(name)
        # running state sync
        if name == "CMD_SYSTEM_START":
            self.state_store.set_system_running(True)
        elif name == "CMD_SYSTEM_STOP":
            self.state_store.set_system_running(False)
    # ============================================================
    # TELEMETRY STEP
    # ============================================================
    def _telemetry_step(self):
        decision: FaultPolicyDecision = self.telemetry_mgr.tick()
        self.router.update_fault_policy(decision)
        # update state store safety mirror
        self.state_store.update_safety(
            severity=decision.severity.value,
            primary_state=decision.primary_state,
            accept_user_control=decision.accept_user_control,
            allow_new_motion_commands=decision.allow_new_motion_commands,
            request_shutdown=decision.request_shutdown,
            ui_fault_latched=decision.ui_fault_latched,
            summary=decision.summary,
            warnings=decision.warnings,
            faults=decision.faults,
            thermal_state=decision.thermal_state,
        )
        self.state_store.set_fan_active(decision.force_fan_on)
    # ============================================================
    # MAIN LOOP
    # ============================================================
    def run_forever(self):
        while True:
            # ---- input step (fast loop)
            self.input_mgr._read_left()
            self.input_mgr._read_right()
            self.input_mgr._merge_ui()
            # ---- telemetry step (slower loop)
            now = time.time()
            if now - self._last_telemetry >= self._telemetry_period:
                self._telemetry_step()
                self._last_telemetry = now
            time.sleep(self.loop_dt)


# ============================================================
# MODULE-R011
# ============================================================

# runtime/remotepi_boot_sequence.py
"""
MODULE-R011
RemotePi Boot Sequence
----------------------

Purpose:
    Controlled startup and self-test procedure for RemotePi.

Responsibilities:
    - Run boot steps in deterministic order
    - Validate UI, ADC, joystick center, thermal sanity, fan, buzzer
    - Check network and MasterPi link presence
    - Produce boot report
    - Decide whether runtime may proceed

Notes:
    This module does not start the main runtime loop by itself.
    It only evaluates boot readiness.
"""
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional
from hardware.remotepi_fault_policy import HealthSnapshot, evaluate_fault_policy
from hardware.remotepi_signal_names import (
    CMD_BUZZER_BOOT_OK,
    CMD_BUZZER_FAULT,
    FAULT_ADC1_OFFLINE,
    FAULT_ADC2_OFFLINE,
    FAULT_I2C_BUS_ERROR,
    FAULT_LEFT_JOYSTICK_STUCK,
    FAULT_RIGHT_JOYSTICK_STUCK,
    FAULT_UI_UNRESPONSIVE,
    FAULT_MASTER_LINK_TIMEOUT,
    STATE_BOOTING,
    STATE_READY,
    STATE_WARNING,
    STATE_FAULT,
)
from hardware.remotepi_calibration_profile import (
    LEFT_JOYSTICK_X_CAL,
    LEFT_JOYSTICK_Y_CAL,
    RIGHT_JOYSTICK_X_CAL,
    RIGHT_JOYSTICK_Y_CAL,
)
# ============================================================
# ENUMS
# ============================================================
class BootSeverity(str, Enum):
    OK = "OK"
    WARNING = "WARNING"
    FAULT = "FAULT"
    BLOCKED = "BLOCKED"
class BootStepStatus(str, Enum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"
    SKIP = "SKIP"
# ============================================================
# DATA MODELS
# ============================================================
@dataclass
class BootStepResult:
    name: str
    status: BootStepStatus
    message: str
    details: dict = field(default_factory=dict)
@dataclass
class BootReport:
    started_ts: float
    finished_ts: float
    total_duration_sec: float
    overall_state: str
    severity: BootSeverity
    can_start_runtime: bool
    steps: list[BootStepResult] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    faults: list[str] = field(default_factory=list)
    summary: str = ""
# ============================================================
# MAIN CLASS
# ============================================================
class RemotePiBootSequence:
    def __init__(
        self,
        adc_reader: Callable[[str], float],
        gpio_reader: Callable[[str], bool],
        gpio_writer: Callable[[str, bool], None],
        command_sink: Callable[[str, dict], None],
        network_status_reader: Callable[[], dict],
        ui_health_reader: Callable[[], bool],
        sleep_fn: Callable[[float], None] = time.sleep,
    ):
        self.adc_reader = adc_reader
        self.gpio_reader = gpio_reader
        self.gpio_writer = gpio_writer
        self.command_sink = command_sink
        self.network_status_reader = network_status_reader
        self.ui_health_reader = ui_health_reader
        self.sleep_fn = sleep_fn
        self._steps: list[BootStepResult] = []
        self._warnings: list[str] = []
        self._faults: list[str] = []
    # --------------------------------------------------------
    def _add_step(self, name: str, status: BootStepStatus, message: str, **details) -> None:
        self._steps.append(
            BootStepResult(
                name=name,
                status=status,
                message=message,
                details=details,
            )
        )
    # --------------------------------------------------------
    def _safe_adc_read(self, channel_name: str) -> tuple[bool, Optional[float]]:
        try:
            value = float(self.adc_reader(channel_name))
            return True, value
        except Exception as exc:
            return False, None
    # --------------------------------------------------------
    def _within_center_band(self, raw_value: float, center: int, tolerance: int = 2500) -> bool:
        return abs(raw_value - center) <= tolerance
    # --------------------------------------------------------
    # BOOT STEPS
    # --------------------------------------------------------
    def _step_ui_ready(self) -> None:
        ok = bool(self.ui_health_reader())
        if ok:
            self._add_step("ui_ready", BootStepStatus.PASS, "HMI/UI responded.")
        else:
            self._faults.append(FAULT_UI_UNRESPONSIVE)
            self._add_step("ui_ready", BootStepStatus.FAIL, "HMI/UI did not respond.")
    def _step_i2c_adc_check(self) -> None:
        net = self.network_status_reader()
        i2c_ok = bool(net.get("i2c_ok", True))
        adc1_ok = bool(net.get("adc1_online", True))
        adc2_ok = bool(net.get("adc2_online", True))
        if not i2c_ok:
            self._faults.append(FAULT_I2C_BUS_ERROR)
        if not adc1_ok:
            self._faults.append(FAULT_ADC1_OFFLINE)
        if not adc2_ok:
            self._faults.append(FAULT_ADC2_OFFLINE)
        if i2c_ok and adc1_ok and adc2_ok:
            self._add_step(
                "i2c_adc_check",
                BootStepStatus.PASS,
                "I2C bus and both ADS1115 devices are online.",
            )
        else:
            self._add_step(
                "i2c_adc_check",
                BootStepStatus.FAIL,
                "One or more I2C/ADC checks failed.",
                i2c_ok=i2c_ok,
                adc1_ok=adc1_ok,
                adc2_ok=adc2_ok,
            )
    def _step_joystick_center_check(self) -> None:
        checks = [
            ("LEFT_JOYSTICK_X", LEFT_JOYSTICK_X_CAL.center_raw, "LEFT_X"),
            ("LEFT_JOYSTICK_Y", LEFT_JOYSTICK_Y_CAL.center_raw, "LEFT_Y"),
            ("RIGHT_JOYSTICK_X", RIGHT_JOYSTICK_X_CAL.center_raw, "RIGHT_X"),
            ("RIGHT_JOYSTICK_Y", RIGHT_JOYSTICK_Y_CAL.center_raw, "RIGHT_Y"),
        ]
        all_ok = True
        detail_map: dict[str, float] = {}
        for channel_name, center, label in checks:
            ok, value = self._safe_adc_read(channel_name)
            if not ok or value is None:
                all_ok = False
                detail_map[label] = -1.0
                continue
            detail_map[label] = value
            if not self._within_center_band(value, center):
                all_ok = False
        if all_ok:
            self._add_step(
                "joystick_center_check",
                BootStepStatus.PASS,
                "Both joystick assemblies are inside boot neutral band.",
                **detail_map,
            )
            return
        self._warnings.append(FAULT_LEFT_JOYSTICK_STUCK)
        self._warnings.append(FAULT_RIGHT_JOYSTICK_STUCK)
        self._add_step(
            "joystick_center_check",
            BootStepStatus.WARN,
            "One or more joystick axes are outside neutral boot band.",
            **detail_map,
        )
    def _step_thermal_sanity(self) -> None:
        ok_lm35, lm35 = self._safe_adc_read("LM35_TEMP")
        ok_ntc, ntc = self._safe_adc_read("NTC_BATTERY_TEMP")
        lm35_valid = ok_lm35 and lm35 is not None and (-20.0 <= lm35 <= 100.0)
        ntc_valid = ok_ntc and ntc is not None and (-20.0 <= ntc <= 100.0)
        if lm35_valid and ntc_valid:
            self._add_step(
                "thermal_sanity",
                BootStepStatus.PASS,
                "Temperature channels are inside sane boot range.",
                lm35_temp=lm35,
                ntc_temp=ntc,
            )
        else:
            self._add_step(
                "thermal_sanity",
                BootStepStatus.WARN,
                "One or more temperature channels are outside sane boot range.",
                lm35_temp=lm35,
                ntc_temp=ntc,
            )
            self._warnings.append("WARN_THERMAL_SANITY_CHECK")
    def _step_fan_test(self) -> None:
        try:
            self.gpio_writer("REMOTE_FAN_CTRL", True)
            self.sleep_fn(0.15)
            self.gpio_writer("REMOTE_FAN_CTRL", False)
            self._add_step(
                "fan_test",
                BootStepStatus.PASS,
                "Remote cooling fan output toggled successfully."
            )
        except Exception as exc:
            self._add_step(
                "fan_test",
                BootStepStatus.FAIL,
                "Remote cooling fan test failed.",
                error=str(exc),
            )
            self._faults.append("FAULT_REMOTE_FAN_BOOT_TEST")
    def _step_buzzer_test(self) -> None:
        try:
            self.command_sink(CMD_BUZZER_BOOT_OK, {"reason": "BOOT_SEQUENCE_TEST"})
            self._add_step(
                "buzzer_test",
                BootStepStatus.PASS,
                "Buzzer boot acknowledgement command dispatched."
            )
        except Exception as exc:
            self._add_step(
                "buzzer_test",
                BootStepStatus.WARN,
                "Buzzer boot command could not be dispatched.",
                error=str(exc),
            )
            self._warnings.append("WARN_BUZZER_BOOT_TEST")
    def _step_network_check(self) -> None:
        net = self.network_status_reader()
        network_online = bool(net.get("network_online", True))
        master_link_ok = bool(net.get("master_link_ok", True))
        if network_online and master_link_ok:
            self._add_step(
                "network_check",
                BootStepStatus.PASS,
                "Network and MasterPi link are available.",
                network_online=network_online,
                master_link_ok=master_link_ok,
            )
            return
        if not master_link_ok:
            self._faults.append(FAULT_MASTER_LINK_TIMEOUT)
        self._add_step(
            "network_check",
            BootStepStatus.WARN if network_online else BootStepStatus.FAIL,
            "Network and/or MasterPi link is not fully ready.",
            network_online=network_online,
            master_link_ok=master_link_ok,
        )
    def _step_health_policy_preview(self) -> None:
        net = self.network_status_reader()
        ok_bat, battery_voltage = self._safe_adc_read("BATTERY_VOLTAGE_SENSE")
        ok_lm35, local_temp = self._safe_adc_read("LM35_TEMP")
        ok_ntc, battery_temp = self._safe_adc_read("NTC_BATTERY_TEMP")
        snapshot = HealthSnapshot(
            battery_voltage=battery_voltage if ok_bat else None,
            local_temp_c=local_temp if ok_lm35 else None,
            battery_temp_c=battery_temp if ok_ntc else None,
            adc1_online=bool(net.get("adc1_online", True)),
            adc2_online=bool(net.get("adc2_online", True)),
            i2c_ok=bool(net.get("i2c_ok", True)),
            network_online=bool(net.get("network_online", True)),
            network_weak=bool(net.get("network_weak", False)),
            master_link_ok=bool(net.get("master_link_ok", True)),
            remote_fan_feedback_ok=True,
            ui_ready=bool(self.ui_health_reader()),
            system_active=False,
        )
        decision = evaluate_fault_policy(snapshot)
        if decision.request_shutdown:
            self._add_step(
                "health_policy_preview",
                BootStepStatus.FAIL,
                "Boot health preview requests shutdown.",
                severity=decision.severity.value,
                summary=decision.summary,
            )
            self._faults.extend(decision.faults)
            return
        if decision.faults:
            self._add_step(
                "health_policy_preview",
                BootStepStatus.WARN,
                "Boot health preview produced faults/warnings.",
                severity=decision.severity.value,
                faults=list(decision.faults),
                warnings=list(decision.warnings),
                summary=decision.summary,
            )
            self._warnings.extend(decision.warnings)
            self._warnings.extend(decision.faults)
            return
        self._add_step(
            "health_policy_preview",
            BootStepStatus.PASS,
            "Boot health preview is acceptable.",
            severity=decision.severity.value,
            summary=decision.summary,
        )
    # --------------------------------------------------------
    # FINALIZATION
    # --------------------------------------------------------
    def _build_report(self, started_ts: float) -> BootReport:
        finished_ts = time.time()
        faults = list(dict.fromkeys(self._faults))
        warnings = list(dict.fromkeys(self._warnings))
        if faults:
            severity = BootSeverity.FAULT
            overall_state = STATE_FAULT
            can_start_runtime = False
            summary = f"Boot blocked by {len(faults)} fault(s)."
        elif warnings:
            severity = BootSeverity.WARNING
            overall_state = STATE_WARNING
            can_start_runtime = True
            summary = f"Boot completed with {len(warnings)} warning(s)."
        else:
            severity = BootSeverity.OK
            overall_state = STATE_READY
            can_start_runtime = True
            summary = "Boot completed successfully."
        return BootReport(
            started_ts=started_ts,
            finished_ts=finished_ts,
            total_duration_sec=finished_ts - started_ts,
            overall_state=overall_state,
            severity=severity,
            can_start_runtime=can_start_runtime,
            steps=list(self._steps),
            warnings=warnings,
            faults=faults,
            summary=summary,
        )
    # --------------------------------------------------------
    # PUBLIC API
    # --------------------------------------------------------
    def run(self) -> BootReport:
        self._steps.clear()
        self._warnings.clear()
        self._faults.clear()
        started_ts = time.time()
        self._add_step("boot_enter", BootStepStatus.PASS, "Boot sequence entered.", state=STATE_BOOTING)
        self._step_ui_ready()
        self._step_i2c_adc_check()
        self._step_joystick_center_check()
        self._step_thermal_sanity()
        self._step_fan_test()
        self._step_buzzer_test()
        self._step_network_check()
        self._step_health_policy_preview()
        report = self._build_report(started_ts)
        if report.can_start_runtime:
            self.command_sink(CMD_BUZZER_BOOT_OK, {"reason": "BOOT_OK"})
        else:
            self.command_sink(CMD_BUZZER_FAULT, {"reason": "BOOT_BLOCKED"})
        return report


# ============================================================
# MODULE-R012
# ============================================================

# runtime/remotepi_command_transport.py
"""
MODULE-R012
RemotePi Command Transport
--------------------------

Purpose:
    Reliable command transport layer between RemotePi and MasterPi.

Responsibilities:
    - Normalize outgoing commands into transport packets
    - Separate local-only commands from remote-bound commands
    - Manage ACK / retry / timeout logic
    - Provide delivery status to upper layers

Notes:
    This module does not implement the physical socket by itself.
    It wraps an injected transport_adapter.
"""
import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Callable, Optional
# ============================================================
# ENUMS
# ============================================================
class TransportTarget(str, Enum):
    LOCAL = "LOCAL"
    MASTER = "MASTER"
    BROADCAST = "BROADCAST"
class DeliveryState(str, Enum):
    QUEUED = "QUEUED"
    SENT = "SENT"
    ACKED = "ACKED"
    TIMEOUT = "TIMEOUT"
    FAILED = "FAILED"
    DROPPED = "DROPPED"
# ============================================================
# DATA MODELS
# ============================================================
@dataclass
class CommandPacket:
    packet_id: str
    seq: int
    command: str
    target: TransportTarget
    created_ts: float
    payload: dict = field(default_factory=dict)
    requires_ack: bool = True
    retry_count: int = 0
    max_retries: int = 3
    timeout_sec: float = 0.75
@dataclass
class DeliveryRecord:
    packet: CommandPacket
    state: DeliveryState
    last_attempt_ts: float = 0.0
    ack_ts: Optional[float] = None
    error: Optional[str] = None
# ============================================================
# COMMAND CLASSIFICATION
# ============================================================
LOCAL_ONLY_COMMANDS = {
    "CMD_BUZZER_BOOT_OK",
    "CMD_BUZZER_BUTTON_ACK",
    "CMD_BUZZER_WARNING",
    "CMD_BUZZER_FAULT",
    "CMD_BUZZER_CRITICAL",
    "CMD_REMOTE_FAN_ON",
    "CMD_REMOTE_FAN_OFF",
    "CMD_FAULT_VIEW_OPEN",
    "CMD_FAULT_ACK",
}
MASTER_BOUND_COMMAND_PREFIXES = (
    "CMD_MODE_",
    "CMD_LIGHT_",
    "CMD_JOYSTICK_",
    "CMD_SYSTEM_",
)
NO_ACK_COMMANDS = {
    "CMD_BUZZER_BUTTON_ACK",
}
# ============================================================
# MAIN CLASS
# ============================================================
class RemotePiCommandTransport:
    def __init__(
        self,
        transport_adapter: Callable[[dict], bool],
        local_command_sink: Callable[[str, dict], None],
        status_sink: Callable[[str, dict], None],
    ):
        """
        transport_adapter(packet_dict) -> bool
            Sends packet to MasterPi transport layer.
            Returns True if handed off to link layer successfully.
        local_command_sink(command_name, payload)
            Executes local-only commands.
        status_sink(topic_or_event_name, payload)
            Observability / logger / state hooks.
        """
        self.transport_adapter = transport_adapter
        self.local_command_sink = local_command_sink
        self.status_sink = status_sink
        self._seq = 0
        self._pending: dict[str, DeliveryRecord] = {}
        self._history: list[DeliveryRecord] = []
    # --------------------------------------------------------
    def _next_seq(self) -> int:
        self._seq += 1
        return self._seq
    def _make_packet(self, command: str, payload: Optional[dict] = None) -> CommandPacket:
        payload = payload or {}
        target = self._resolve_target(command)
        requires_ack = command not in NO_ACK_COMMANDS and target != TransportTarget.LOCAL
        return CommandPacket(
            packet_id=str(uuid.uuid4()),
            seq=self._next_seq(),
            command=command,
            target=target,
            created_ts=time.time(),
            payload=dict(payload),
            requires_ack=requires_ack,
        )
    def _resolve_target(self, command: str) -> TransportTarget:
        if command in LOCAL_ONLY_COMMANDS:
            return TransportTarget.LOCAL
        if command.startswith(MASTER_BOUND_COMMAND_PREFIXES):
            return TransportTarget.MASTER
        return TransportTarget.BROADCAST
    # --------------------------------------------------------
    def submit(self, command: str, payload: Optional[dict] = None) -> str:
        packet = self._make_packet(command, payload)
        record = DeliveryRecord(packet=packet, state=DeliveryState.QUEUED)
        if packet.target == TransportTarget.LOCAL:
            self.local_command_sink(packet.command, packet.payload)
            record.state = DeliveryState.ACKED
            record.ack_ts = time.time()
            self._history.append(record)
            self.status_sink("transport/local_executed", {
                "packet_id": packet.packet_id,
                "seq": packet.seq,
                "command": packet.command,
                "payload": packet.payload,
            })
            return packet.packet_id
        ok = self._send_packet(record)
        if packet.requires_ack and ok:
            self._pending[packet.packet_id] = record
        else:
            self._history.append(record)
        return packet.packet_id
    # --------------------------------------------------------
    def _send_packet(self, record: DeliveryRecord) -> bool:
        packet = record.packet
        try:
            handed_off = self.transport_adapter(asdict(packet))
        except Exception as exc:
            handed_off = False
            record.error = str(exc)
        record.last_attempt_ts = time.time()
        if handed_off:
            record.state = DeliveryState.SENT if packet.requires_ack else DeliveryState.ACKED
            if not packet.requires_ack:
                record.ack_ts = time.time()
            self.status_sink("transport/sent", {
                "packet_id": packet.packet_id,
                "seq": packet.seq,
                "command": packet.command,
                "target": packet.target.value,
                "retry_count": packet.retry_count,
                "requires_ack": packet.requires_ack,
            })
            return True
        record.state = DeliveryState.FAILED
        self.status_sink("transport/send_failed", {
            "packet_id": packet.packet_id,
            "seq": packet.seq,
            "command": packet.command,
            "target": packet.target.value,
            "retry_count": packet.retry_count,
            "error": record.error,
        })
        return False
    # --------------------------------------------------------
    def receive_ack(self, packet_id: str) -> bool:
        record = self._pending.pop(packet_id, None)
        if record is None:
            self.status_sink("transport/ack_unknown", {
                "packet_id": packet_id,
            })
            return False
        record.state = DeliveryState.ACKED
        record.ack_ts = time.time()
        self._history.append(record)
        self.status_sink("transport/acked", {
            "packet_id": record.packet.packet_id,
            "seq": record.packet.seq,
            "command": record.packet.command,
            "latency_sec": record.ack_ts - record.packet.created_ts,
        })
        return True
    # --------------------------------------------------------
    def tick(self) -> None:
        now = time.time()
        expired: list[str] = []
        for packet_id, record in list(self._pending.items()):
            packet = record.packet
            deadline = record.last_attempt_ts + packet.timeout_sec
            if now < deadline:
                continue
            if packet.retry_count < packet.max_retries:
                packet.retry_count += 1
                ok = self._send_packet(record)
                if not ok and packet.retry_count >= packet.max_retries:
                    record.state = DeliveryState.FAILED
                    expired.append(packet_id)
            else:
                record.state = DeliveryState.TIMEOUT
                expired.append(packet_id)
        for packet_id in expired:
            record = self._pending.pop(packet_id, None)
            if record is None:
                continue
            self._history.append(record)
            self.status_sink("transport/finalized", {
                "packet_id": record.packet.packet_id,
                "seq": record.packet.seq,
                "command": record.packet.command,
                "state": record.state.value,
                "retry_count": record.packet.retry_count,
            })
    # --------------------------------------------------------
    def pending_count(self) -> int:
        return len(self._pending)
    def get_pending_packets(self) -> list[dict]:
        return [
            {
                "packet_id": rec.packet.packet_id,
                "seq": rec.packet.seq,
                "command": rec.packet.command,
                "state": rec.state.value,
                "retry_count": rec.packet.retry_count,
                "created_ts": rec.packet.created_ts,
                "last_attempt_ts": rec.last_attempt_ts,
            }
            for rec in self._pending.values()
        ]
    def get_history(self, limit: int = 50) -> list[dict]:
        items = self._history[-limit:]
        return [
            {
                "packet_id": rec.packet.packet_id,
                "seq": rec.packet.seq,
                "command": rec.packet.command,
                "target": rec.packet.target.value,
                "state": rec.state.value,
                "retry_count": rec.packet.retry_count,
                "created_ts": rec.packet.created_ts,
                "ack_ts": rec.ack_ts,
                "error": rec.error,
            }
            for rec in items
        ]


# ============================================================
# MODULE-R013
# ============================================================

# runtime/remotepi_packet_codec.py
"""
MODULE-R013
RemotePi Packet Codec
---------------------

Purpose:
    Protocol packet encoder/decoder for RemotePi communications.

Responsibilities:
    - Build command packets
    - Build ACK packets
    - Build telemetry packets
    - Build health packets
    - Decode and validate inbound packets
    - Enforce minimal protocol schema

Notes:
    This module is transport-agnostic.
    It only works with Python dict / JSON-safe payloads.
"""
import json
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional
# ============================================================
# PROTOCOL CONSTANTS
# ============================================================
PROTOCOL_NAME = "CAKIRO_MRKP"
PROTOCOL_VERSION = "1.0"
REMOTE_NODE_ID = "REMOTE_PI"
MASTER_NODE_ID = "MASTER_PI"
# ============================================================
# ENUMS
# ============================================================
class PacketType(str, Enum):
    COMMAND = "COMMAND"
    ACK = "ACK"
    TELEMETRY = "TELEMETRY"
    HEALTH = "HEALTH"
    EVENT = "EVENT"
    HELLO = "HELLO"
    HEARTBEAT = "HEARTBEAT"
    ERROR = "ERROR"
# ============================================================
# DATA MODELS
# ============================================================
@dataclass
class DecodedPacket:
    packet_type: PacketType
    src: str
    dst: str
    ts: float
    body: dict[str, Any]
    raw: dict[str, Any]
# ============================================================
# BUILDERS
# ============================================================
def _base_packet(packet_type: PacketType, src: str, dst: str) -> dict[str, Any]:
    return {
        "protocol": PROTOCOL_NAME,
        "version": PROTOCOL_VERSION,
        "type": packet_type.value,
        "src": src,
        "dst": dst,
        "ts": time.time(),
    }
def build_command_packet(
    *,
    packet_id: str,
    seq: int,
    command: str,
    payload: dict[str, Any],
    requires_ack: bool,
    src: str = REMOTE_NODE_ID,
    dst: str = MASTER_NODE_ID,
) -> dict[str, Any]:
    pkt = _base_packet(PacketType.COMMAND, src, dst)
    pkt["body"] = {
        "packet_id": packet_id,
        "seq": seq,
        "command": command,
        "payload": payload,
        "requires_ack": requires_ack,
    }
    return pkt
def build_ack_packet(
    *,
    packet_id: str,
    ack_for_seq: int,
    ok: bool = True,
    reason: str = "OK",
    src: str = MASTER_NODE_ID,
    dst: str = REMOTE_NODE_ID,
) -> dict[str, Any]:
    pkt = _base_packet(PacketType.ACK, src, dst)
    pkt["body"] = {
        "packet_id": packet_id,
        "ack_for_seq": ack_for_seq,
        "ok": ok,
        "reason": reason,
    }
    return pkt
def build_telemetry_packet(
    *,
    telemetry: dict[str, Any],
    src: str = REMOTE_NODE_ID,
    dst: str = MASTER_NODE_ID,
) -> dict[str, Any]:
    pkt = _base_packet(PacketType.TELEMETRY, src, dst)
    pkt["body"] = telemetry
    return pkt
def build_health_packet(
    *,
    severity: str,
    primary_state: str,
    thermal_state: str,
    warnings: list[str],
    faults: list[str],
    summary: str,
    src: str = REMOTE_NODE_ID,
    dst: str = MASTER_NODE_ID,
) -> dict[str, Any]:
    pkt = _base_packet(PacketType.HEALTH, src, dst)
    pkt["body"] = {
        "severity": severity,
        "primary_state": primary_state,
        "thermal_state": thermal_state,
        "warnings": list(warnings),
        "faults": list(faults),
        "summary": summary,
    }
    return pkt
def build_event_packet(
    *,
    event_name: str,
    payload: dict[str, Any],
    src: str = REMOTE_NODE_ID,
    dst: str = MASTER_NODE_ID,
) -> dict[str, Any]:
    pkt = _base_packet(PacketType.EVENT, src, dst)
    pkt["body"] = {
        "event": event_name,
        "payload": payload,
    }
    return pkt
def build_hello_packet(
    *,
    node_role: str,
    capabilities: list[str],
    src: str = REMOTE_NODE_ID,
    dst: str = MASTER_NODE_ID,
) -> dict[str, Any]:
    pkt = _base_packet(PacketType.HELLO, src, dst)
    pkt["body"] = {
        "node_role": node_role,
        "capabilities": list(capabilities),
    }
    return pkt
def build_heartbeat_packet(
    *,
    uptime_sec: float,
    system_running: bool,
    active_mode: str,
    src: str = REMOTE_NODE_ID,
    dst: str = MASTER_NODE_ID,
) -> dict[str, Any]:
    pkt = _base_packet(PacketType.HEARTBEAT, src, dst)
    pkt["body"] = {
        "uptime_sec": uptime_sec,
        "system_running": system_running,
        "active_mode": active_mode,
    }
    return pkt
def build_error_packet(
    *,
    error_code: str,
    message: str,
    detail: Optional[dict[str, Any]] = None,
    src: str = REMOTE_NODE_ID,
    dst: str = MASTER_NODE_ID,
) -> dict[str, Any]:
    pkt = _base_packet(PacketType.ERROR, src, dst)
    pkt["body"] = {
        "error_code": error_code,
        "message": message,
        "detail": detail or {},
    }
    return pkt
# ============================================================
# SERIALIZATION
# ============================================================
def to_json(packet: dict[str, Any]) -> str:
    return json.dumps(packet, ensure_ascii=False, separators=(",", ":"))
def from_json(data: str) -> dict[str, Any]:
    return json.loads(data)
# ============================================================
# VALIDATION
# ============================================================
def validate_packet_shape(packet: dict[str, Any]) -> None:
    required_top = ("protocol", "version", "type", "src", "dst", "ts", "body")
    for key in required_top:
        if key not in packet:
            raise ValueError(f"Missing packet field: {key}")
    if packet["protocol"] != PROTOCOL_NAME:
        raise ValueError(f"Invalid protocol: {packet['protocol']}")
    if packet["version"] != PROTOCOL_VERSION:
        raise ValueError(f"Unsupported version: {packet['version']}")
    if not isinstance(packet["body"], dict):
        raise ValueError("Packet body must be a dict")
def _require_body_keys(packet: dict[str, Any], keys: tuple[str, ...]) -> None:
    body = packet["body"]
    for key in keys:
        if key not in body:
            raise ValueError(f"Missing body field for {packet['type']}: {key}")
def validate_packet_semantics(packet: dict[str, Any]) -> None:
    validate_packet_shape(packet)
    ptype = packet["type"]
    if ptype == PacketType.COMMAND.value:
        _require_body_keys(packet, ("packet_id", "seq", "command", "payload", "requires_ack"))
    elif ptype == PacketType.ACK.value:
        _require_body_keys(packet, ("packet_id", "ack_for_seq", "ok", "reason"))
    elif ptype == PacketType.TELEMETRY.value:
        # flexible body, no extra hard check
        pass
    elif ptype == PacketType.HEALTH.value:
        _require_body_keys(packet, ("severity", "primary_state", "thermal_state", "warnings", "faults", "summary"))
    elif ptype == PacketType.EVENT.value:
        _require_body_keys(packet, ("event", "payload"))
    elif ptype == PacketType.HELLO.value:
        _require_body_keys(packet, ("node_role", "capabilities"))
    elif ptype == PacketType.HEARTBEAT.value:
        _require_body_keys(packet, ("uptime_sec", "system_running", "active_mode"))
    elif ptype == PacketType.ERROR.value:
        _require_body_keys(packet, ("error_code", "message", "detail"))
    else:
        raise ValueError(f"Unknown packet type: {ptype}")
def decode_packet(packet: dict[str, Any]) -> DecodedPacket:
    validate_packet_semantics(packet)
    return DecodedPacket(
        packet_type=PacketType(packet["type"]),
        src=str(packet["src"]),
        dst=str(packet["dst"]),
        ts=float(packet["ts"]),
        body=dict(packet["body"]),
        raw=dict(packet),
    )
# ============================================================
# ACK HELPERS
# ============================================================
def extract_ack_packet_id(packet: dict[str, Any]) -> str:
    decoded = decode_packet(packet)
    if decoded.packet_type != PacketType.ACK:
        raise ValueError("Packet is not ACK type")
    return str(decoded.body["packet_id"])
def extract_command_identity(packet: dict[str, Any]) -> tuple[str, int, str]:
    decoded = decode_packet(packet)
    if decoded.packet_type != PacketType.COMMAND:
        raise ValueError("Packet is not COMMAND type")
    return (
        str(decoded.body["packet_id"]),
        int(decoded.body["seq"]),
        str(decoded.body["command"]),
    )


# ============================================================
# MODULE-R014
# ============================================================

# runtime/remotepi_link_manager.py
"""
MODULE-R014
RemotePi Link Manager
---------------------

Purpose:
    Live session manager between RemotePi and MasterPi.

Responsibilities:
    - Establish session
    - Send HELLO / HEARTBEAT packets
    - Decode inbound packets
    - Forward ACKs to command transport
    - Detect link timeout / reconnect need
    - Expose link health to upper runtime layers

Notes:
    This module depends on an injected adapter that actually performs
    send/receive operations. The adapter may use TCP, UDP, websocket,
    serial bridge, or another transport.
"""
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional
from runtime.remotepi_packet_codec import (
    PacketType,
    REMOTE_NODE_ID,
    MASTER_NODE_ID,
    build_heartbeat_packet,
    build_hello_packet,
    decode_packet,
    extract_ack_packet_id,
)
from runtime.remotepi_command_transport import RemotePiCommandTransport
# ============================================================
# ENUMS
# ============================================================
class LinkState(str, Enum):
    DOWN = "DOWN"
    CONNECTING = "CONNECTING"
    HELLO_SENT = "HELLO_SENT"
    UP = "UP"
    DEGRADED = "DEGRADED"
    RECONNECTING = "RECONNECTING"
# ============================================================
# DATA MODELS
# ============================================================
@dataclass
class LinkStatus:
    state: LinkState = LinkState.DOWN
    connected: bool = False
    master_link_ok: bool = False
    last_rx_ts: float = 0.0
    last_tx_ts: float = 0.0
    last_hello_ts: float = 0.0
    last_heartbeat_ts: float = 0.0
    reconnect_count: int = 0
    last_error: Optional[str] = None
    negotiated: bool = False
    peer_id: str = MASTER_NODE_ID
@dataclass
class LinkManagerConfig:
    hello_interval_sec: float = 2.0
    heartbeat_interval_sec: float = 1.0
    rx_timeout_sec: float = 3.0
    reconnect_backoff_sec: float = 1.5
# ============================================================
# MAIN CLASS
# ============================================================
class RemotePiLinkManager:
    def __init__(
        self,
        adapter_connect: Callable[[], bool],
        adapter_send: Callable[[dict], bool],
        adapter_receive: Callable[[], Optional[dict]],
        adapter_close: Callable[[], None],
        command_transport: RemotePiCommandTransport,
        status_sink: Callable[[str, dict], None],
        runtime_state_reader: Callable[[], dict],
        config: Optional[LinkManagerConfig] = None,
    ):
        """
        adapter_connect() -> bool
        adapter_send(packet_dict) -> bool
        adapter_receive() -> packet_dict | None
        adapter_close() -> None
        command_transport:
            Used to forward ACK packets into transport layer.
        status_sink(topic_or_event_name, payload):
            Logger / observability hook.
        runtime_state_reader() -> dict:
            Should return at least:
                {
                    "uptime_sec": float,
                    "system_running": bool,
                    "active_mode": str,
                }
        """
        self.adapter_connect = adapter_connect
        self.adapter_send = adapter_send
        self.adapter_receive = adapter_receive
        self.adapter_close = adapter_close
        self.command_transport = command_transport
        self.status_sink = status_sink
        self.runtime_state_reader = runtime_state_reader
        self.config = config or LinkManagerConfig()
        self.status = LinkStatus()
        self._last_connect_attempt_ts = 0.0
    # --------------------------------------------------------
    def _emit(self, event: str, **payload) -> None:
        self.status_sink(event, {
            "ts": time.time(),
            "link_state": self.status.state.value,
            **payload,
        })
    # --------------------------------------------------------
    def _set_state(self, state: LinkState, *, error: Optional[str] = None) -> None:
        self.status.state = state
        self.status.last_error = error
        self.status.connected = state in {LinkState.HELLO_SENT, LinkState.UP, LinkState.DEGRADED}
        self.status.master_link_ok = state == LinkState.UP
        self._emit("link/state_changed", state=state.value, error=error)
    # --------------------------------------------------------
    def connect(self) -> bool:
        now = time.time()
        if now - self._last_connect_attempt_ts < self.config.reconnect_backoff_sec:
            return False
        self._last_connect_attempt_ts = now
        self._set_state(LinkState.CONNECTING)
        try:
            ok = bool(self.adapter_connect())
        except Exception as exc:
            ok = False
            self._set_state(LinkState.DOWN, error=str(exc))
            return False
        if not ok:
            self._set_state(LinkState.DOWN, error="CONNECT_FAILED")
            return False
        self.status.connected = True
        self.status.reconnect_count += 1
        self._emit("link/connected")
        return self.send_hello()
    # --------------------------------------------------------
    def disconnect(self) -> None:
        try:
            self.adapter_close()
        finally:
            self.status.connected = False
            self.status.master_link_ok = False
            self.status.negotiated = False
            self._set_state(LinkState.DOWN)
    # --------------------------------------------------------
    def send_hello(self) -> bool:
        pkt = build_hello_packet(
            node_role="FIELD_REMOTE_CONTROLLER",
            capabilities=[
                "HMI_TOUCH",
                "DUAL_JOYSTICK",
                "DUAL_ADS1115",
                "BATTERY_MONITOR",
                "THERMAL_MONITOR",
                "LOCAL_FAN_CONTROL",
                "LOCAL_BUZZER",
            ],
            src=REMOTE_NODE_ID,
            dst=MASTER_NODE_ID,
        )
        ok = self._safe_send(pkt)
        if ok:
            self.status.last_hello_ts = time.time()
            self._set_state(LinkState.HELLO_SENT)
        return ok
    # --------------------------------------------------------
    def send_heartbeat(self) -> bool:
        runtime = self.runtime_state_reader()
        pkt = build_heartbeat_packet(
            uptime_sec=float(runtime.get("uptime_sec", 0.0)),
            system_running=bool(runtime.get("system_running", False)),
            active_mode=str(runtime.get("active_mode", "STATE_CONTROL_MODE_MENU")),
            src=REMOTE_NODE_ID,
            dst=MASTER_NODE_ID,
        )
        ok = self._safe_send(pkt)
        if ok:
            self.status.last_heartbeat_ts = time.time()
        return ok
    # --------------------------------------------------------
    def _safe_send(self, packet: dict) -> bool:
        try:
            ok = bool(self.adapter_send(packet))
        except Exception as exc:
            self._set_state(LinkState.DEGRADED, error=str(exc))
            self._emit("link/send_error", error=str(exc))
            return False
        if ok:
            self.status.last_tx_ts = time.time()
            self._emit("link/tx", packet_type=packet.get("type"))
            return True
        self._set_state(LinkState.DEGRADED, error="SEND_FAILED")
        self._emit("link/send_failed", packet_type=packet.get("type"))
        return False
    # --------------------------------------------------------
    def _handle_ack(self, packet: dict) -> None:
        packet_id = extract_ack_packet_id(packet)
        self.command_transport.receive_ack(packet_id)
        self._emit("link/ack_received", packet_id=packet_id)
    def _handle_hello(self, decoded) -> None:
        self.status.negotiated = True
        self.status.peer_id = decoded.src
        self._set_state(LinkState.UP)
        self._emit("link/hello_received", src=decoded.src)
    def _handle_heartbeat(self, decoded) -> None:
        if self.status.state != LinkState.UP:
            self._set_state(LinkState.UP)
        self._emit("link/heartbeat_received", src=decoded.src)
    def _handle_command(self, decoded) -> None:
        self._emit("link/command_received", command=decoded.body.get("command"), src=decoded.src)
    def _handle_event(self, decoded) -> None:
        self._emit("link/event_received", event=decoded.body.get("event"), src=decoded.src)
    def _handle_health(self, decoded) -> None:
        self._emit("link/health_received", severity=decoded.body.get("severity"), src=decoded.src)
    def _handle_telemetry(self, decoded) -> None:
        self._emit("link/telemetry_received", src=decoded.src)
    # --------------------------------------------------------
    def poll_incoming(self) -> None:
        try:
            packet = self.adapter_receive()
        except Exception as exc:
            self._set_state(LinkState.DEGRADED, error=str(exc))
            self._emit("link/rx_error", error=str(exc))
            return
        if not packet:
            return
        self.status.last_rx_ts = time.time()
        try:
            decoded = decode_packet(packet)
        except Exception as exc:
            self._emit("link/packet_decode_error", error=str(exc))
            return
        if decoded.packet_type == PacketType.ACK:
            self._handle_ack(packet)
        elif decoded.packet_type == PacketType.HELLO:
            self._handle_hello(decoded)
        elif decoded.packet_type == PacketType.HEARTBEAT:
            self._handle_heartbeat(decoded)
        elif decoded.packet_type == PacketType.COMMAND:
            self._handle_command(decoded)
        elif decoded.packet_type == PacketType.EVENT:
            self._handle_event(decoded)
        elif decoded.packet_type == PacketType.HEALTH:
            self._handle_health(decoded)
        elif decoded.packet_type == PacketType.TELEMETRY:
            self._handle_telemetry(decoded)
        else:
            self._emit("link/unhandled_packet_type", packet_type=decoded.packet_type.value)
    # --------------------------------------------------------
    def tick(self) -> None:
        now = time.time()
        if self.status.state == LinkState.DOWN:
            self.connect()
            return
        if self.status.state in {LinkState.CONNECTING, LinkState.RECONNECTING}:
            self.connect()
            return
        self.poll_incoming()
        if self.status.connected and (now - self.status.last_heartbeat_ts) >= self.config.heartbeat_interval_sec:
            self.send_heartbeat()
        if self.status.last_rx_ts > 0 and (now - self.status.last_rx_ts) > self.config.rx_timeout_sec:
            self._set_state(LinkState.DEGRADED, error="RX_TIMEOUT")
            self._emit("link/rx_timeout", timeout_sec=self.config.rx_timeout_sec)
        if self.status.state == LinkState.DEGRADED:
            self.adapter_close()
            self.status.connected = False
            self.status.master_link_ok = False
            self.status.negotiated = False
            self._set_state(LinkState.RECONNECTING)
    # --------------------------------------------------------
    def get_status_dict(self) -> dict:
        return {
            "state": self.status.state.value,
            "connected": self.status.connected,
            "master_link_ok": self.status.master_link_ok,
            "last_rx_ts": self.status.last_rx_ts,
            "last_tx_ts": self.status.last_tx_ts,
            "last_hello_ts": self.status.last_hello_ts,
            "last_heartbeat_ts": self.status.last_heartbeat_ts,
            "reconnect_count": self.status.reconnect_count,
            "last_error": self.status.last_error,
            "negotiated": self.status.negotiated,
            "peer_id": self.status.peer_id,
        }


# ============================================================
# MODULE-R015
# ============================================================

# runtime/remotepi_local_command_executor.py
"""
MODULE-R015
RemotePi Local Command Executor
-------------------------------

Purpose:
    Execute device-local commands on RemotePi hardware.

Responsibilities:
    - Drive buzzer patterns
    - Force fan ON/OFF
    - Trigger local UI fault view hooks
    - Update runtime state store outputs
    - Provide simple actuator safety timing

Notes:
    This layer does NOT generate commands.
    It only executes commands already classified as LOCAL.
"""
import time
from enum import Enum
from typing import Callable, Optional
# ============================================================
# ENUMS
# ============================================================
class BuzzerPattern(str, Enum):
    ACK = "ACK"
    WARNING = "WARNING"
    FAULT = "FAULT"
    CRITICAL = "CRITICAL"
    BOOT_OK = "BOOT_OK"
# ============================================================
# MAIN CLASS
# ============================================================
class RemotePiLocalCommandExecutor:
    def __init__(
        self,
        gpio_writer: Callable[[str, bool], None],
        ui_fault_hook: Callable[[dict], None],
        state_store_hook: Callable[[str, bool], None],
        sleep_fn: Callable[[float], None] = time.sleep,
    ):
        """
        gpio_writer(name, state)
            Example:
                gpio_writer("REMOTE_BUZZER_CTRL", True)
        ui_fault_hook(payload)
            Allows HMI layer to open fault screen.
        state_store_hook(output_name, state)
            Allows runtime state store sync.
        """
        self.gpio_writer = gpio_writer
        self.ui_fault_hook = ui_fault_hook
        self.state_store_hook = state_store_hook
        self.sleep_fn = sleep_fn
    # --------------------------------------------------------
    # BUZZER CONTROL
    # --------------------------------------------------------
    def _pulse(self, duration: float):
        self.gpio_writer("REMOTE_BUZZER_CTRL", True)
        self.state_store_hook("BUZZER", True)
        self.sleep_fn(duration)
        self.gpio_writer("REMOTE_BUZZER_CTRL", False)
        self.state_store_hook("BUZZER", False)
    def _pattern_ack(self):
        self._pulse(0.05)
    def _pattern_warning(self):
        for _ in range(2):
            self._pulse(0.08)
            self.sleep_fn(0.08)
    def _pattern_fault(self):
        for _ in range(3):
            self._pulse(0.12)
            self.sleep_fn(0.12)
    def _pattern_critical(self):
        for _ in range(5):
            self._pulse(0.18)
            self.sleep_fn(0.08)
    def _pattern_boot_ok(self):
        self._pulse(0.15)
        self.sleep_fn(0.05)
        self._pulse(0.15)
    def execute_buzzer(self, pattern: BuzzerPattern):
        if pattern == BuzzerPattern.ACK:
            self._pattern_ack()
        elif pattern == BuzzerPattern.WARNING:
            self._pattern_warning()
        elif pattern == BuzzerPattern.FAULT:
            self._pattern_fault()
        elif pattern == BuzzerPattern.CRITICAL:
            self._pattern_critical()
        elif pattern == BuzzerPattern.BOOT_OK:
            self._pattern_boot_ok()
    # --------------------------------------------------------
    # FAN CONTROL
    # --------------------------------------------------------
    def set_fan(self, state: bool):
        self.gpio_writer("REMOTE_FAN_CTRL", bool(state))
        self.state_store_hook("FAN", bool(state))
    # --------------------------------------------------------
    # FAULT VIEW
    # --------------------------------------------------------
    def open_fault_view(self, payload: Optional[dict] = None):
        payload = payload or {}
        self.ui_fault_hook(payload)
    # --------------------------------------------------------
    # COMMAND DISPATCH
    # --------------------------------------------------------
    def execute(self, command: str, payload: Optional[dict] = None):
        payload = payload or {}
        # ---- buzzer commands ----
        if command == "CMD_BUZZER_BUTTON_ACK":
            self.execute_buzzer(BuzzerPattern.ACK)
            return
        if command == "CMD_BUZZER_WARNING":
            self.execute_buzzer(BuzzerPattern.WARNING)
            return
        if command == "CMD_BUZZER_FAULT":
            self.execute_buzzer(BuzzerPattern.FAULT)
            return
        if command == "CMD_BUZZER_CRITICAL":
            self.execute_buzzer(BuzzerPattern.CRITICAL)
            return
        if command == "CMD_BUZZER_BOOT_OK":
            self.execute_buzzer(BuzzerPattern.BOOT_OK)
            return
        # ---- fan commands ----
        if command == "CMD_REMOTE_FAN_ON":
            self.set_fan(True)
            return
        if command == "CMD_REMOTE_FAN_OFF":
            self.set_fan(False)
            return
        # ---- fault ui ----
        if command == "CMD_FAULT_VIEW_OPEN":
            self.open_fault_view(payload)
            return
        if command == "CMD_FAULT_ACK":
            # placeholder future logic
            return
        # ---- unknown ----
        # intentionally silent for safety


# ============================================================
# MODULE-R016
# ============================================================

# runtime/remotepi_watchdog_supervisor.py
"""
MODULE-R016
RemotePi Watchdog Supervisor
----------------------------

Purpose:
    High-level liveness and safety supervision for RemotePi runtime.

Responsibilities:
    - Monitor input activity freshness
    - Monitor telemetry freshness
    - Monitor link freshness
    - Detect joystick stuck behavior
    - Detect thermal runaway tendency
    - Escalate warnings/faults/critical shutdown requests

Notes:
    This module does NOT own the main runtime loop.
    It supervises other modules and emits watchdog decisions.
"""
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional
# ============================================================
# ENUMS
# ============================================================
class WatchdogSeverity(str, Enum):
    NORMAL = "NORMAL"
    WARNING = "WARNING"
    FAULT = "FAULT"
    CRITICAL = "CRITICAL"
    SHUTDOWN = "SHUTDOWN"
# ============================================================
# DATA MODELS
# ============================================================
@dataclass
class WatchdogThresholds:
    input_stale_sec: float = 1.0
    telemetry_stale_sec: float = 1.2
    link_stale_sec: float = 3.5
    joystick_stuck_sec: float = 8.0
    thermal_runaway_delta_c: float = 8.0
    thermal_runaway_window_sec: float = 20.0
@dataclass
class ThermalSample:
    ts: float
    local_temp_c: float
    battery_temp_c: float
@dataclass
class WatchdogDecision:
    severity: WatchdogSeverity
    warnings: list[str] = field(default_factory=list)
    faults: list[str] = field(default_factory=list)
    request_shutdown: bool = False
    force_fault_view: bool = False
    force_buzzer: Optional[str] = None
    summary: str = "Watchdog healthy."
# ============================================================
# MAIN CLASS
# ============================================================
class RemotePiWatchdogSupervisor:
    def __init__(
        self,
        state_reader: Callable[[], dict],
        link_status_reader: Callable[[], dict],
        event_sink: Callable[[str, dict], None],
        thresholds: Optional[WatchdogThresholds] = None,
    ):
        """
        state_reader() -> runtime state dict
        link_status_reader() -> link status dict
        event_sink(topic_or_event_name, payload)
        """
        self.state_reader = state_reader
        self.link_status_reader = link_status_reader
        self.event_sink = event_sink
        self.thresholds = thresholds or WatchdogThresholds()
        self._last_input_nonzero_ts: float = 0.0
        self._thermal_history: list[ThermalSample] = []
    # --------------------------------------------------------
    def _emit(self, event: str, **payload) -> None:
        self.event_sink(event, {
            "ts": time.time(),
            **payload,
        })
    # --------------------------------------------------------
    def _max_abs_axis(self, state: dict) -> float:
        inputs = state.get("inputs", {})
        values = [
            abs(float(inputs.get("left_x", 0.0))),
            abs(float(inputs.get("left_y", 0.0))),
            abs(float(inputs.get("right_x", 0.0))),
            abs(float(inputs.get("right_y", 0.0))),
        ]
        return max(values) if values else 0.0
    # --------------------------------------------------------
    def _update_input_activity(self, state: dict) -> None:
        max_axis = self._max_abs_axis(state)
        if max_axis > 0.15:
            self._last_input_nonzero_ts = time.time()
    # --------------------------------------------------------
    def _update_thermal_history(self, state: dict) -> None:
        thermal = state.get("thermal", {})
        sample = ThermalSample(
            ts=time.time(),
            local_temp_c=float(thermal.get("local_temp_c", 0.0)),
            battery_temp_c=float(thermal.get("battery_temp_c", 0.0)),
        )
        self._thermal_history.append(sample)
        cutoff = time.time() - self.thresholds.thermal_runaway_window_sec
        self._thermal_history = [x for x in self._thermal_history if x.ts >= cutoff]
    # --------------------------------------------------------
    def _check_stale_streams(self, state: dict, link: dict, decision: WatchdogDecision) -> None:
        now = time.time()
        inputs = state.get("inputs", {})
        last_input_ts = float(inputs.get("last_input_ts", 0.0))
        if last_input_ts > 0 and (now - last_input_ts) > self.thresholds.input_stale_sec:
            decision.warnings.append("WATCHDOG_INPUT_STALE")
            if decision.severity == WatchdogSeverity.NORMAL:
                decision.severity = WatchdogSeverity.WARNING
        last_state_ts = float(state.get("ts", 0.0))
        if last_state_ts > 0 and (now - last_state_ts) > self.thresholds.telemetry_stale_sec:
            decision.faults.append("WATCHDOG_TELEMETRY_STALE")
            if decision.severity in (WatchdogSeverity.NORMAL, WatchdogSeverity.WARNING):
                decision.severity = WatchdogSeverity.FAULT
        last_rx_ts = float(link.get("last_rx_ts", 0.0))
        if last_rx_ts > 0 and (now - last_rx_ts) > self.thresholds.link_stale_sec:
            decision.faults.append("WATCHDOG_LINK_STALE")
            if decision.severity in (WatchdogSeverity.NORMAL, WatchdogSeverity.WARNING):
                decision.severity = WatchdogSeverity.FAULT
    # --------------------------------------------------------
    def _check_joystick_stuck(self, state: dict, decision: WatchdogDecision) -> None:
        if self._last_input_nonzero_ts <= 0:
            return
        if (time.time() - self._last_input_nonzero_ts) < self.thresholds.joystick_stuck_sec:
            return
        if self._max_abs_axis(state) > 0.15:
            decision.faults.append("WATCHDOG_JOYSTICK_STUCK_ACTIVE")
            if decision.severity in (WatchdogSeverity.NORMAL, WatchdogSeverity.WARNING):
                decision.severity = WatchdogSeverity.FAULT
            decision.force_fault_view = True
    # --------------------------------------------------------
    def _check_thermal_runaway(self, decision: WatchdogDecision) -> None:
        if len(self._thermal_history) < 2:
            return
        first = self._thermal_history[0]
        last = self._thermal_history[-1]
        local_delta = last.local_temp_c - first.local_temp_c
        battery_delta = last.battery_temp_c - first.battery_temp_c
        runaway_delta = max(local_delta, battery_delta)
        if runaway_delta >= self.thresholds.thermal_runaway_delta_c:
            decision.faults.append("WATCHDOG_THERMAL_RUNAWAY")
            decision.force_fault_view = True
            decision.force_buzzer = "CRITICAL"
            if runaway_delta >= (self.thresholds.thermal_runaway_delta_c + 4.0):
                decision.severity = WatchdogSeverity.SHUTDOWN
                decision.request_shutdown = True
            elif decision.severity in (
                WatchdogSeverity.NORMAL,
                WatchdogSeverity.WARNING,
                WatchdogSeverity.FAULT,
            ):
                decision.severity = WatchdogSeverity.CRITICAL
    # --------------------------------------------------------
    def _merge_existing_safety(self, state: dict, decision: WatchdogDecision) -> None:
        safety = state.get("safety", {})
        current_severity = str(safety.get("severity", "NORMAL"))
        rank = {
            "NORMAL": 0,
            "WARNING": 1,
            "FAULT": 2,
            "CRITICAL": 3,
            "SHUTDOWN": 4,
        }
        if rank.get(current_severity, 0) > rank.get(decision.severity.value, 0):
            decision.severity = WatchdogSeverity(current_severity)
        if bool(safety.get("request_shutdown", False)):
            decision.request_shutdown = True
            if decision.severity != WatchdogSeverity.SHUTDOWN:
                decision.severity = WatchdogSeverity.SHUTDOWN
    # --------------------------------------------------------
    def _finalize(self, decision: WatchdogDecision) -> WatchdogDecision:
        if decision.severity == WatchdogSeverity.WARNING and not decision.force_buzzer:
            decision.force_buzzer = "WARNING"
        elif decision.severity == WatchdogSeverity.FAULT and not decision.force_buzzer:
            decision.force_buzzer = "FAULT"
        elif decision.severity in (WatchdogSeverity.CRITICAL, WatchdogSeverity.SHUTDOWN) and not decision.force_buzzer:
            decision.force_buzzer = "CRITICAL"
        if decision.severity == WatchdogSeverity.NORMAL:
            decision.summary = "Watchdog healthy."
        else:
            parts = [f"Severity={decision.severity.value}"]
            if decision.warnings:
                parts.append("Warnings=" + ",".join(decision.warnings))
            if decision.faults:
                parts.append("Faults=" + ",".join(decision.faults))
            if decision.request_shutdown:
                parts.append("Shutdown=REQUESTED")
            decision.summary = " | ".join(parts)
        return decision
    # --------------------------------------------------------
    def tick(self) -> WatchdogDecision:
        state = self.state_reader()
        link = self.link_status_reader()
        self._update_input_activity(state)
        self._update_thermal_history(state)
        decision = WatchdogDecision(severity=WatchdogSeverity.NORMAL)
        self._check_stale_streams(state, link, decision)
        self._check_joystick_stuck(state, decision)
        self._check_thermal_runaway(decision)
        self._merge_existing_safety(state, decision)
        self._finalize(decision)
        self._emit(
            "watchdog/tick",
            severity=decision.severity.value,
            warnings=list(decision.warnings),
            faults=list(decision.faults),
            request_shutdown=decision.request_shutdown,
            summary=decision.summary,
        )
        return decision


# ============================================================
# MODULE-R017
# ============================================================

# runtime/remotepi_runtime_app.py
"""
MODULE-R017
RemotePi Runtime App
--------------------

Purpose:
    Top-level executable runtime application for RemotePi.

Responsibilities:
    - Run boot sequence
    - Construct runtime components
    - Bind local command execution
    - Bind link manager and command transport
    - Run watchdog supervision
    - Orchestrate the full runtime lifecycle

Notes:
    This module is intentionally adapter-driven.
    Real GPIO / ADC / UI / network implementations are injected.
"""
import time
from dataclasses import dataclass
from typing import Callable, Optional, Any
from runtime.remotepi_runtime_controller import RemotePiRuntimeController
from runtime.remotepi_boot_sequence import RemotePiBootSequence, BootReport
from runtime.remotepi_command_transport import RemotePiCommandTransport
from runtime.remotepi_link_manager import RemotePiLinkManager, LinkManagerConfig
from runtime.remotepi_local_command_executor import RemotePiLocalCommandExecutor
from runtime.remotepi_watchdog_supervisor import (
    RemotePiWatchdogSupervisor,
    WatchdogDecision,
)
from runtime.remotepi_packet_codec import build_command_packet
# ============================================================
# APP CONFIG
# ============================================================
@dataclass
class RemotePiRuntimeAppConfig:
    main_loop_dt: float = 0.02
    watchdog_period_sec: float = 0.50
    link_period_sec: float = 0.05
    transport_period_sec: float = 0.05
# ============================================================
# MAIN APP
# ============================================================
class RemotePiRuntimeApp:
    def __init__(
        self,
        *,
        adc_reader: Callable[[str], float],
        gpio_reader: Callable[[str], bool],
        gpio_writer: Callable[[str, bool], None],
        ui_event_source: Callable[[], Optional[str]],
        ui_health_reader: Callable[[], bool],
        ui_fault_hook: Callable[[dict], None],
        network_status_reader: Callable[[], dict],
        adapter_connect: Callable[[], bool],
        adapter_send: Callable[[dict], bool],
        adapter_receive: Callable[[], Optional[dict]],
        adapter_close: Callable[[], None],
        sleep_fn: Callable[[float], None] = time.sleep,
        config: Optional[RemotePiRuntimeAppConfig] = None,
        link_config: Optional[LinkManagerConfig] = None,
    ):
        self.adc_reader = adc_reader
        self.gpio_reader = gpio_reader
        self.gpio_writer = gpio_writer
        self.ui_event_source = ui_event_source
        self.ui_health_reader = ui_health_reader
        self.ui_fault_hook = ui_fault_hook
        self.network_status_reader = network_status_reader
        self.adapter_connect = adapter_connect
        self.adapter_send = adapter_send
        self.adapter_receive = adapter_receive
        self.adapter_close = adapter_close
        self.sleep_fn = sleep_fn
        self.config = config or RemotePiRuntimeAppConfig()
        self.link_config = link_config or LinkManagerConfig()
        self.boot_report: Optional[BootReport] = None
        self._local_executor: Optional[RemotePiLocalCommandExecutor] = None
        self._command_transport: Optional[RemotePiCommandTransport] = None
        self._link_manager: Optional[RemotePiLinkManager] = None
        self._runtime_controller: Optional[RemotePiRuntimeController] = None
        self._watchdog: Optional[RemotePiWatchdogSupervisor] = None
        self._should_run = False
        self._last_watchdog_ts = 0.0
        self._last_link_ts = 0.0
        self._last_transport_ts = 0.0
    # --------------------------------------------------------
    # OBSERVABILITY
    # --------------------------------------------------------
    def _status_sink(self, topic: str, payload: dict) -> None:
        # Placeholder central status/log sink.
        # Can later be routed into logger / telemetry / JSONL / console.
        _ = (topic, payload)
    # --------------------------------------------------------
    # STATE READERS
    # --------------------------------------------------------
    def _runtime_state_reader(self) -> dict:
        if not self._runtime_controller:
            return {
                "uptime_sec": 0.0,
                "system_running": False,
                "active_mode": "STATE_CONTROL_MODE_MENU",
            }
        state = self._runtime_controller.state_store.to_dict()
        return {
            "uptime_sec": float(state.get("uptime_sec", 0.0)),
            "system_running": bool(state.get("mode", {}).get("system_running", False)),
            "active_mode": str(state.get("mode", {}).get("active_mode", "STATE_CONTROL_MODE_MENU")),
        }
    def _full_state_reader(self) -> dict:
        if not self._runtime_controller:
            return {}
        return self._runtime_controller.state_store.to_dict()
    def _link_status_reader(self) -> dict:
        if not self._link_manager:
            return {
                "state": "DOWN",
                "connected": False,
                "master_link_ok": False,
                "last_rx_ts": 0.0,
            }
        return self._link_manager.get_status_dict()
    # --------------------------------------------------------
    # LOCAL EXECUTION
    # --------------------------------------------------------
    def _state_store_output_hook(self, output_name: str, state: bool) -> None:
        if not self._runtime_controller:
            return
        if output_name == "FAN":
            self._runtime_controller.state_store.set_fan_active(state)
        elif output_name == "BUZZER":
            self._runtime_controller.state_store.set_buzzer_active(state)
    def _local_command_sink(self, command: str, payload: dict) -> None:
        if self._local_executor is None:
            return
        self._local_executor.execute(command, payload)
    # --------------------------------------------------------
    # TRANSPORT ADAPTER WRAP
    # --------------------------------------------------------
    def _transport_adapter(self, packet_dict: dict) -> bool:
        encoded = build_command_packet(
            packet_id=packet_dict["packet_id"],
            seq=int(packet_dict["seq"]),
            command=str(packet_dict["command"]),
            payload=dict(packet_dict.get("payload", {})),
            requires_ack=bool(packet_dict.get("requires_ack", True)),
        )
        return bool(self.adapter_send(encoded))
    # --------------------------------------------------------
    # COMMAND BRIDGE
    # --------------------------------------------------------
    def _command_bridge(self, command: str, payload: dict) -> None:
        if self._command_transport is None:
            return
        self._command_transport.submit(command, payload)
    # --------------------------------------------------------
    # BOOT
    # --------------------------------------------------------
    def run_boot_sequence(self) -> BootReport:
        boot = RemotePiBootSequence(
            adc_reader=self.adc_reader,
            gpio_reader=self.gpio_reader,
            gpio_writer=self.gpio_writer,
            command_sink=self._local_command_sink,
            network_status_reader=self.network_status_reader,
            ui_health_reader=self.ui_health_reader,
            sleep_fn=self.sleep_fn,
        )
        self.boot_report = boot.run()
        return self.boot_report
    # --------------------------------------------------------
    # BUILD
    # --------------------------------------------------------
    def build(self) -> None:
        self._local_executor = RemotePiLocalCommandExecutor(
            gpio_writer=self.gpio_writer,
            ui_fault_hook=self.ui_fault_hook,
            state_store_hook=self._state_store_output_hook,
            sleep_fn=self.sleep_fn,
        )
        self._command_transport = RemotePiCommandTransport(
            transport_adapter=self._transport_adapter,
            local_command_sink=self._local_command_sink,
            status_sink=self._status_sink,
        )
        self._runtime_controller = RemotePiRuntimeController(
            adc_reader=self.adc_reader,
            gpio_reader=self.gpio_reader,
            gpio_writer=self.gpio_writer,
            ui_event_source=self.ui_event_source,
            network_status_reader=self.network_status_reader,
            ui_health_reader=self.ui_health_reader,
            system_active_reader=lambda: bool(
                self._runtime_controller.state_store.is_system_running()  # type: ignore[union-attr]
            ) if self._runtime_controller else False,
            loop_dt=self.config.main_loop_dt,
        )
        # Router command sink override
        self._runtime_controller.router.command_sink = self._command_bridge
        self._link_manager = RemotePiLinkManager(
            adapter_connect=self.adapter_connect,
            adapter_send=self.adapter_send,
            adapter_receive=self.adapter_receive,
            adapter_close=self.adapter_close,
            command_transport=self._command_transport,
            status_sink=self._status_sink,
            runtime_state_reader=self._runtime_state_reader,
            config=self.link_config,
        )
        self._watchdog = RemotePiWatchdogSupervisor(
            state_reader=self._full_state_reader,
            link_status_reader=self._link_status_reader,
            event_sink=self._status_sink,
        )
    # --------------------------------------------------------
    # WATCHDOG ACTIONS
    # --------------------------------------------------------
    def _apply_watchdog_decision(self, decision: WatchdogDecision) -> None:
        if self._runtime_controller is None or self._local_executor is None:
            return
        store = self._runtime_controller.state_store
        if decision.force_fault_view:
            self._local_executor.open_fault_view({
                "source": "WATCHDOG",
                "summary": decision.summary,
                "faults": list(decision.faults),
                "warnings": list(decision.warnings),
            })
        if decision.force_buzzer == "WARNING":
            self._local_executor.execute("CMD_BUZZER_WARNING", {})
        elif decision.force_buzzer == "FAULT":
            self._local_executor.execute("CMD_BUZZER_FAULT", {})
        elif decision.force_buzzer == "CRITICAL":
            self._local_executor.execute("CMD_BUZZER_CRITICAL", {})
        if decision.request_shutdown:
            store.set_system_running(False)
            store.update_safety(
                severity=decision.severity.value,
                primary_state="STATE_SHUTDOWN",
                accept_user_control=False,
                allow_new_motion_commands=False,
                request_shutdown=True,
                ui_fault_latched=True,
                summary=decision.summary,
                warnings=list(decision.warnings),
                faults=list(decision.faults),
            )
    # --------------------------------------------------------
    # TICK
    # --------------------------------------------------------
    def tick(self) -> None:
        now = time.time()
        if self._runtime_controller is not None:
            # Input step
            self._runtime_controller.input_mgr._read_left()
            self._runtime_controller.input_mgr._read_right()
            self._runtime_controller.input_mgr._merge_ui()
            # Telemetry step
            if now - self._runtime_controller._last_telemetry >= self._runtime_controller._telemetry_period:
                self._runtime_controller._telemetry_step()
                self._runtime_controller._last_telemetry = now
        if self._command_transport is not None and (now - self._last_transport_ts) >= self.config.transport_period_sec:
            self._command_transport.tick()
            self._last_transport_ts = now
        if self._link_manager is not None and (now - self._last_link_ts) >= self.config.link_period_sec:
            self._link_manager.tick()
            self._last_link_ts = now
        if self._watchdog is not None and (now - self._last_watchdog_ts) >= self.config.watchdog_period_sec:
            decision = self._watchdog.tick()
            self._apply_watchdog_decision(decision)
            self._last_watchdog_ts = now
    # --------------------------------------------------------
    # RUN CONTROL
    # --------------------------------------------------------
    def start(self) -> BootReport:
        self.build()
        report = self.run_boot_sequence()
        if not report.can_start_runtime:
            self._should_run = False
            return report
        self._should_run = True
        return report
    def run_forever(self) -> BootReport:
        report = self.start()
        if not report.can_start_runtime:
            return report
        while self._should_run:
            self.tick()
            self.sleep_fn(self.config.main_loop_dt)
        return report
    def stop(self) -> None:
        self._should_run = False
        if self._link_manager is not None:
            self._link_manager.disconnect()


# ============================================================
# MODULE-R018
# ============================================================

# runtime/remotepi_diagnostics_reporter.py
"""
MODULE-R018
RemotePi Diagnostics Reporter
-----------------------------

Purpose:
    Consolidated diagnostics report builder for RemotePi runtime.

Responsibilities:
    - Gather boot report, runtime state, link status and watchdog decision
    - Produce compact and full diagnostic snapshots
    - Provide service-friendly summary structures
    - Help field maintenance and post-fault analysis

Notes:
    This module is read-only.
    It does not control runtime behavior directly.
"""
import time
from dataclasses import asdict, dataclass, field, is_dataclass
from typing import Any, Callable, Optional
# ============================================================
# DATA MODELS
# ============================================================
@dataclass
class DiagnosticSection:
    name: str
    ok: bool
    summary: str
    data: dict[str, Any] = field(default_factory=dict)
@dataclass
class RemotePiDiagnosticReport:
    created_ts: float
    overall_ok: bool
    overall_summary: str
    sections: list[DiagnosticSection] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    faults: list[str] = field(default_factory=list)
    runtime_state: dict[str, Any] = field(default_factory=dict)
    link_status: dict[str, Any] = field(default_factory=dict)
    watchdog: dict[str, Any] = field(default_factory=dict)
    boot: dict[str, Any] = field(default_factory=dict)
# ============================================================
# HELPERS
# ============================================================
def _to_plain_dict(obj: Any) -> dict[str, Any]:
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return dict(obj)
    if is_dataclass(obj):
        return asdict(obj)
    if hasattr(obj, "__dict__"):
        return dict(vars(obj))
    return {"value": obj}
def _safe_call(reader: Callable[[], Any]) -> tuple[bool, Any]:
    try:
        return True, reader()
    except Exception as exc:
        return False, {"error": str(exc)}
# ============================================================
# MAIN CLASS
# ============================================================
class RemotePiDiagnosticsReporter:
    def __init__(
        self,
        runtime_state_reader: Callable[[], Any],
        link_status_reader: Callable[[], Any],
        watchdog_reader: Callable[[], Any],
        boot_report_reader: Callable[[], Any],
    ):
        self.runtime_state_reader = runtime_state_reader
        self.link_status_reader = link_status_reader
        self.watchdog_reader = watchdog_reader
        self.boot_report_reader = boot_report_reader
    # --------------------------------------------------------
    def _build_runtime_section(self, runtime_state: dict[str, Any]) -> DiagnosticSection:
        safety = runtime_state.get("safety", {})
        faults = list(runtime_state.get("faults", []))
        warnings = list(runtime_state.get("warnings", []))
        ok = not bool(faults) and str(safety.get("severity", "NORMAL")) not in ("FAULT", "CRITICAL", "SHUTDOWN")
        summary = (
            f"mode={runtime_state.get('mode', {}).get('active_mode', 'UNKNOWN')} | "
            f"running={runtime_state.get('mode', {}).get('system_running', False)} | "
            f"severity={safety.get('severity', 'UNKNOWN')} | "
            f"faults={len(faults)} | warnings={len(warnings)}"
        )
        return DiagnosticSection(
            name="runtime_state",
            ok=ok,
            summary=summary,
            data=runtime_state,
        )
    def _build_link_section(self, link_status: dict[str, Any]) -> DiagnosticSection:
        state = str(link_status.get("state", "UNKNOWN"))
        ok = bool(link_status.get("master_link_ok", False))
        summary = (
            f"state={state} | connected={link_status.get('connected', False)} | "
            f"master_link_ok={link_status.get('master_link_ok', False)} | "
            f"reconnect_count={link_status.get('reconnect_count', 0)}"
        )
        return DiagnosticSection(
            name="link_status",
            ok=ok,
            summary=summary,
            data=link_status,
        )
    def _build_watchdog_section(self, watchdog: dict[str, Any]) -> DiagnosticSection:
        severity = str(watchdog.get("severity", "NORMAL"))
        ok = severity == "NORMAL"
        summary = (
            f"severity={severity} | "
            f"shutdown={watchdog.get('request_shutdown', False)} | "
            f"faults={len(watchdog.get('faults', []))} | "
            f"warnings={len(watchdog.get('warnings', []))}"
        )
        return DiagnosticSection(
            name="watchdog",
            ok=ok,
            summary=summary,
            data=watchdog,
        )
    def _build_boot_section(self, boot: dict[str, Any]) -> DiagnosticSection:
        if not boot:
            return DiagnosticSection(
                name="boot_report",
                ok=False,
                summary="boot report unavailable",
                data={},
            )
        ok = bool(boot.get("can_start_runtime", False))
        summary = (
            f"state={boot.get('overall_state', 'UNKNOWN')} | "
            f"severity={boot.get('severity', 'UNKNOWN')} | "
            f"can_start_runtime={boot.get('can_start_runtime', False)}"
        )
        return DiagnosticSection(
            name="boot_report",
            ok=ok,
            summary=summary,
            data=boot,
        )
    # --------------------------------------------------------
    def build_report(self) -> RemotePiDiagnosticReport:
        ok_runtime, runtime_obj = _safe_call(self.runtime_state_reader)
        ok_link, link_obj = _safe_call(self.link_status_reader)
        ok_watchdog, watchdog_obj = _safe_call(self.watchdog_reader)
        ok_boot, boot_obj = _safe_call(self.boot_report_reader)
        runtime_state = _to_plain_dict(runtime_obj)
        link_status = _to_plain_dict(link_obj)
        watchdog = _to_plain_dict(watchdog_obj)
        boot = _to_plain_dict(boot_obj)
        sections = [
            self._build_runtime_section(runtime_state),
            self._build_link_section(link_status),
            self._build_watchdog_section(watchdog),
            self._build_boot_section(boot),
        ]
        warnings: list[str] = []
        faults: list[str] = []
        warnings.extend(runtime_state.get("warnings", []))
        warnings.extend(watchdog.get("warnings", []))
        faults.extend(runtime_state.get("faults", []))
        faults.extend(watchdog.get("faults", []))
        # unique-preserving order
        warnings = list(dict.fromkeys(str(x) for x in warnings))
        faults = list(dict.fromkeys(str(x) for x in faults))
        overall_ok = all(section.ok for section in sections) and not faults
        summary_parts = [
            f"overall_ok={overall_ok}",
            f"faults={len(faults)}",
            f"warnings={len(warnings)}",
            f"runtime={sections[0].summary}",
            f"link={sections[1].summary}",
            f"watchdog={sections[2].summary}",
            f"boot={sections[3].summary}",
        ]
        return RemotePiDiagnosticReport(
            created_ts=time.time(),
            overall_ok=overall_ok,
            overall_summary=" | ".join(summary_parts),
            sections=sections,
            warnings=warnings,
            faults=faults,
            runtime_state=runtime_state,
            link_status=link_status,
            watchdog=watchdog,
            boot=boot,
        )
    # --------------------------------------------------------
    def build_compact_report(self) -> dict[str, Any]:
        report = self.build_report()
        return {
            "created_ts": report.created_ts,
            "overall_ok": report.overall_ok,
            "overall_summary": report.overall_summary,
            "warnings": list(report.warnings),
            "faults": list(report.faults),
        }
    def build_service_report(self) -> dict[str, Any]:
        report = self.build_report()
        return {
            "created_ts": report.created_ts,
            "overall_ok": report.overall_ok,
            "overall_summary": report.overall_summary,
            "boot": report.boot,
            "runtime_state": report.runtime_state,
            "link_status": report.link_status,
            "watchdog": report.watchdog,
            "warnings": list(report.warnings),
            "faults": list(report.faults),
            "sections": [asdict(section) for section in report.sections],
        }


# ============================================================
# MODULE-R019
# ============================================================

# runtime/remotepi_jsonl_logger.py
"""
MODULE-R019
RemotePi JSONL Logger
---------------------

Purpose:
    Persistent event / telemetry / diagnostic logger for RemotePi.

Responsibilities:
    - Write structured JSONL lines
    - Provide safe buffered disk writing
    - Support log rotation by size
    - Provide service export helpers

Notes:
    JSONL chosen for:
        - append-only reliability
        - easy parsing
        - crash-safe minimal corruption
"""
import json
import os
import time
from dataclasses import dataclass
from typing import Optional, Any
# ============================================================
# CONFIG
# ============================================================
@dataclass
class JsonlLoggerConfig:
    log_dir: str = "logs"
    base_filename: str = "remotepi_runtime"
    max_file_size_bytes: int = 4 * 1024 * 1024   # 4 MB
    flush_interval_sec: float = 0.5
# ============================================================
# MAIN CLASS
# ============================================================
class RemotePiJsonlLogger:
    def __init__(
        self,
        config: Optional[JsonlLoggerConfig] = None,
        time_fn=time.time,
    ):
        self.config = config or JsonlLoggerConfig()
        self.time_fn = time_fn
        os.makedirs(self.config.log_dir, exist_ok=True)
        self._current_path = self._build_new_path()
        self._buffer: list[str] = []
        self._last_flush = 0.0
    # --------------------------------------------------------
    def _build_new_path(self) -> str:
        ts = int(self.time_fn())
        name = f"{self.config.base_filename}_{ts}.jsonl"
        return os.path.join(self.config.log_dir, name)
    # --------------------------------------------------------
    def _rotate_if_needed(self):
        try:
            size = os.path.getsize(self._current_path)
        except FileNotFoundError:
            return
        if size >= self.config.max_file_size_bytes:
            self._current_path = self._build_new_path()
    # --------------------------------------------------------
    def _flush(self):
        if not self._buffer:
            return
        self._rotate_if_needed()
        with open(self._current_path, "a", encoding="utf-8") as f:
            for line in self._buffer:
                f.write(line)
        self._buffer.clear()
        self._last_flush = self.time_fn()
    # --------------------------------------------------------
    def log(self, topic: str, payload: dict[str, Any]):
        record = {
            "ts": self.time_fn(),
            "topic": topic,
            "payload": payload,
        }
        try:
            line = json.dumps(record, ensure_ascii=False) + "\n"
        except Exception:
            # fallback safe encoding
            line = json.dumps({
                "ts": self.time_fn(),
                "topic": "LOGGER_ENCODING_ERROR",
                "payload": {"original_topic": topic},
            }) + "\n"
        self._buffer.append(line)
        now = self.time_fn()
        if (now - self._last_flush) >= self.config.flush_interval_sec:
            self._flush()
    # --------------------------------------------------------
    def force_flush(self):
        self._flush()
    # --------------------------------------------------------
    def export_latest_log(self) -> Optional[str]:
        """
        Returns path of latest active log file.
        """
        if os.path.exists(self._current_path):
            return self._current_path
        return None
    # --------------------------------------------------------
    def export_all_logs(self) -> list[str]:
        files = []
        for name in os.listdir(self.config.log_dir):
            if name.endswith(".jsonl"):
                files.append(os.path.join(self.config.log_dir, name))
        return sorted(files)


# ============================================================
# MODULE-R020
# ============================================================

# runtime/remotepi_safe_shutdown_manager.py
"""
MODULE-R020
RemotePi Safe Shutdown Manager
------------------------------

Purpose:
    Controlled shutdown coordinator for RemotePi.

Responsibilities:
    - Evaluate shutdown requests from safety / watchdog / user
    - Stop motion acceptance
    - Force local outputs into safe state
    - Notify peer/master when possible
    - Flush logs
    - Close transport/link cleanly
    - Trigger final OS/platform shutdown hook

Notes:
    This module does not call operating-system shutdown directly unless
    a platform_shutdown_hook is injected.
"""
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional
# ============================================================
# ENUMS
# ============================================================
class ShutdownReason(str, Enum):
    USER_REQUEST = "USER_REQUEST"
    WATCHDOG_REQUEST = "WATCHDOG_REQUEST"
    BATTERY_CRITICAL = "BATTERY_CRITICAL"
    THERMAL_CRITICAL = "THERMAL_CRITICAL"
    FAULT_POLICY_REQUEST = "FAULT_POLICY_REQUEST"
    LINK_LOSS_FAILSAFE = "LINK_LOSS_FAILSAFE"
    UNKNOWN = "UNKNOWN"
class ShutdownStage(str, Enum):
    IDLE = "IDLE"
    INITIATED = "INITIATED"
    NOTIFYING = "NOTIFYING"
    MOTION_LOCK = "MOTION_LOCK"
    OUTPUTS_SAFE = "OUTPUTS_SAFE"
    LOG_FLUSH = "LOG_FLUSH"
    LINK_CLOSE = "LINK_CLOSE"
    PLATFORM_SHUTDOWN = "PLATFORM_SHUTDOWN"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"
# ============================================================
# DATA MODELS
# ============================================================
@dataclass
class ShutdownRequest:
    reason: ShutdownReason
    requested_ts: float
    source: str
    detail: dict = field(default_factory=dict)
@dataclass
class ShutdownResult:
    ok: bool
    stage: ShutdownStage
    started_ts: float
    finished_ts: float
    reason: ShutdownReason
    summary: str
    steps: list[dict] = field(default_factory=list)
# ============================================================
# MAIN CLASS
# ============================================================
class RemotePiSafeShutdownManager:
    def __init__(
        self,
        *,
        state_store,
        local_command_executor,
        link_manager,
        command_transport,
        logger=None,
        notify_master_sink: Optional[Callable[[str, dict], None]] = None,
        platform_shutdown_hook: Optional[Callable[[dict], None]] = None,
        sleep_fn: Callable[[float], None] = time.sleep,
    ):
        """
        state_store:
            RemotePiStateStore-like object
        local_command_executor:
            RemotePiLocalCommandExecutor-like object
        link_manager:
            RemotePiLinkManager-like object
        command_transport:
            RemotePiCommandTransport-like object
        logger:
            Optional logger with force_flush()
        notify_master_sink(command_name, payload):
            Optional higher-level notify command path.
        platform_shutdown_hook(payload):
            Optional OS-level/system-level shutdown trigger.
        """
        self.state_store = state_store
        self.local_command_executor = local_command_executor
        self.link_manager = link_manager
        self.command_transport = command_transport
        self.logger = logger
        self.notify_master_sink = notify_master_sink
        self.platform_shutdown_hook = platform_shutdown_hook
        self.sleep_fn = sleep_fn
        self._active_request: Optional[ShutdownRequest] = None
        self._stage: ShutdownStage = ShutdownStage.IDLE
    # --------------------------------------------------------
    @property
    def stage(self) -> ShutdownStage:
        return self._stage
    @property
    def active_request(self) -> Optional[ShutdownRequest]:
        return self._active_request
    # --------------------------------------------------------
    def _step(self, steps: list[dict], stage: ShutdownStage, ok: bool, message: str, **detail) -> None:
        self._stage = stage
        steps.append({
            "ts": time.time(),
            "stage": stage.value,
            "ok": ok,
            "message": message,
            "detail": detail,
        })
    # --------------------------------------------------------
    def request_shutdown(
        self,
        reason: ShutdownReason,
        source: str,
        detail: Optional[dict] = None,
    ) -> ShutdownRequest:
        req = ShutdownRequest(
            reason=reason,
            requested_ts=time.time(),
            source=source,
            detail=detail or {},
        )
        self._active_request = req
        return req
    # --------------------------------------------------------
    def execute(self, request: Optional[ShutdownRequest] = None) -> ShutdownResult:
        started_ts = time.time()
        steps: list[dict] = []
        req = request or self._active_request
        if req is None:
            req = self.request_shutdown(
                reason=ShutdownReason.UNKNOWN,
                source="AUTO_FALLBACK",
                detail={},
            )
        try:
            self._step(
                steps,
                ShutdownStage.INITIATED,
                True,
                "Shutdown sequence initiated.",
                reason=req.reason.value,
                source=req.source,
            )
            # ------------------------------------------------
            # 1) Notify peer/master if possible
            # ------------------------------------------------
            self._step(steps, ShutdownStage.NOTIFYING, True, "Notifying upper layers and peer.")
            try:
                if self.notify_master_sink is not None:
                    self.notify_master_sink("CMD_REMOTE_SHUTDOWN_NOTIFY", {
                        "reason": req.reason.value,
                        "source": req.source,
                        "detail": dict(req.detail),
                        "ts": time.time(),
                    })
                else:
                    self.command_transport.submit("CMD_REMOTE_SHUTDOWN_NOTIFY", {
                        "reason": req.reason.value,
                        "source": req.source,
                        "detail": dict(req.detail),
                        "ts": time.time(),
                    })
                self._step(steps, ShutdownStage.NOTIFYING, True, "Shutdown notify dispatched.")
            except Exception as exc:
                self._step(
                    steps,
                    ShutdownStage.NOTIFYING,
                    False,
                    "Shutdown notify failed.",
                    error=str(exc),
                )
            # ------------------------------------------------
            # 2) Lock motion / user control at state level
            # ------------------------------------------------
            self._step(steps, ShutdownStage.MOTION_LOCK, True, "Locking runtime control.")
            self.state_store.set_system_running(False)
            self.state_store.update_safety(
                severity="SHUTDOWN",
                primary_state="STATE_SHUTDOWN",
                accept_user_control=False,
                allow_new_motion_commands=False,
                request_shutdown=True,
                ui_fault_latched=True,
                summary=f"Safe shutdown active: {req.reason.value}",
                warnings=[],
                faults=[f"SHUTDOWN_{req.reason.value}"],
            )
            self._step(steps, ShutdownStage.MOTION_LOCK, True, "Runtime control locked.")
            # ------------------------------------------------
            # 3) Force local outputs to safe state
            # ------------------------------------------------
            self._step(steps, ShutdownStage.OUTPUTS_SAFE, True, "Driving local outputs to safe state.")
            try:
                self.local_command_executor.execute("CMD_REMOTE_FAN_OFF", {})
            except Exception as exc:
                self._step(
                    steps,
                    ShutdownStage.OUTPUTS_SAFE,
                    False,
                    "Fan safe-state command failed.",
                    error=str(exc),
                )
            try:
                self.local_command_executor.execute("CMD_BUZZER_CRITICAL", {})
            except Exception as exc:
                self._step(
                    steps,
                    ShutdownStage.OUTPUTS_SAFE,
                    False,
                    "Buzzer critical pattern failed.",
                    error=str(exc),
                )
            try:
                self.local_command_executor.execute("CMD_FAULT_VIEW_OPEN", {
                    "source": "SAFE_SHUTDOWN",
                    "reason": req.reason.value,
                    "detail": dict(req.detail),
                })
            except Exception as exc:
                self._step(
                    steps,
                    ShutdownStage.OUTPUTS_SAFE,
                    False,
                    "Fault view open failed.",
                    error=str(exc),
                )
            self._step(steps, ShutdownStage.OUTPUTS_SAFE, True, "Outputs forced to safe state.")
            # ------------------------------------------------
            # 4) Flush logger / persistent records
            # ------------------------------------------------
            self._step(steps, ShutdownStage.LOG_FLUSH, True, "Flushing persistent logs.")
            try:
                if self.logger is not None and hasattr(self.logger, "force_flush"):
                    self.logger.force_flush()
                self._step(steps, ShutdownStage.LOG_FLUSH, True, "Persistent logs flushed.")
            except Exception as exc:
                self._step(
                    steps,
                    ShutdownStage.LOG_FLUSH,
                    False,
                    "Persistent log flush failed.",
                    error=str(exc),
                )
            # ------------------------------------------------
            # 5) Close link cleanly
            # ------------------------------------------------
            self._step(steps, ShutdownStage.LINK_CLOSE, True, "Closing link/session.")
            try:
                if self.link_manager is not None:
                    self.link_manager.disconnect()
                self._step(steps, ShutdownStage.LINK_CLOSE, True, "Link/session closed.")
            except Exception as exc:
                self._step(
                    steps,
                    ShutdownStage.LINK_CLOSE,
                    False,
                    "Link close failed.",
                    error=str(exc),
                )
            # Small drain delay
            self.sleep_fn(0.10)
            # ------------------------------------------------
            # 6) Platform shutdown hook
            # ------------------------------------------------
            self._step(steps, ShutdownStage.PLATFORM_SHUTDOWN, True, "Calling platform shutdown hook.")
            try:
                if self.platform_shutdown_hook is not None:
                    self.platform_shutdown_hook({
                        "reason": req.reason.value,
                        "source": req.source,
                        "detail": dict(req.detail),
                        "ts": time.time(),
                    })
                self._step(
                    steps,
                    ShutdownStage.PLATFORM_SHUTDOWN,
                    True,
                    "Platform shutdown hook completed or skipped."
                )
            except Exception as exc:
                self._stage = ShutdownStage.FAILED
                return ShutdownResult(
                    ok=False,
                    stage=ShutdownStage.FAILED,
                    started_ts=started_ts,
                    finished_ts=time.time(),
                    reason=req.reason,
                    summary=f"Safe shutdown failed during platform hook: {exc}",
                    steps=steps,
                )
            self._stage = ShutdownStage.COMPLETE
            return ShutdownResult(
                ok=True,
                stage=ShutdownStage.COMPLETE,
                started_ts=started_ts,
                finished_ts=time.time(),
                reason=req.reason,
                summary=f"Safe shutdown completed: {req.reason.value}",
                steps=steps,
            )
        except Exception as exc:
            self._stage = ShutdownStage.FAILED
            return ShutdownResult(
                ok=False,
                stage=ShutdownStage.FAILED,
                started_ts=started_ts,
                finished_ts=time.time(),
                reason=req.reason,
                summary=f"Safe shutdown failed: {exc}",
                steps=steps,
            )


# ============================================================
# MODULE-R021
# ============================================================

# runtime/remotepi_service_mode.py
"""
MODULE-R021
RemotePi Service Mode Manager
-----------------------------

Purpose:
    Field service / maintenance / calibration operational mode.

Responsibilities:
    - Block normal runtime motion control
    - Provide actuator test utilities
    - Provide live analog monitoring
    - Support joystick calibration workflow
    - Allow diagnostics interaction without starting system motion

Notes:
    Service mode is considered a controlled safe mode.
"""
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional
# ============================================================
# ENUMS
# ============================================================
class ServiceState(str, Enum):
    IDLE = "IDLE"
    ACTIVE = "ACTIVE"
    CALIBRATION = "CALIBRATION"
    TESTING = "TESTING"
# ============================================================
# DATA MODELS
# ============================================================
@dataclass
class ServiceSnapshot:
    ts: float
    state: ServiceState
    joystick: dict = field(default_factory=dict)
    adc: dict = field(default_factory=dict)
    outputs: dict = field(default_factory=dict)
# ============================================================
# MAIN CLASS
# ============================================================
class RemotePiServiceMode:
    def __init__(
        self,
        adc_reader: Callable[[str], float],
        gpio_writer: Callable[[str, bool], None],
        state_store,
        sleep_fn=time.sleep,
    ):
        self.adc_reader = adc_reader
        self.gpio_writer = gpio_writer
        self.state_store = state_store
        self.sleep_fn = sleep_fn
        self._state = ServiceState.IDLE
        self._last_snapshot: Optional[ServiceSnapshot] = None
    # --------------------------------------------------------
    @property
    def state(self) -> ServiceState:
        return self._state
    def enter(self):
        self._state = ServiceState.ACTIVE
        # runtime motion lock
        self.state_store.set_system_running(False)
        self.state_store.update_safety(
            severity="SERVICE",
            primary_state="STATE_SERVICE_MODE",
            accept_user_control=False,
            allow_new_motion_commands=False,
            request_shutdown=False,
            ui_fault_latched=False,
            summary="Service mode active",
            warnings=[],
            faults=[],
        )
    def exit(self):
        self._state = ServiceState.IDLE
    # --------------------------------------------------------
    # FAN TEST
    # --------------------------------------------------------
    def test_fan(self, duration_sec: float = 2.0):
        self._state = ServiceState.TESTING
        self.gpio_writer("REMOTE_FAN_CTRL", True)
        self.sleep_fn(duration_sec)
        self.gpio_writer("REMOTE_FAN_CTRL", False)
        self._state = ServiceState.ACTIVE
    # --------------------------------------------------------
    # BUZZER TEST
    # --------------------------------------------------------
    def test_buzzer(self):
        self._state = ServiceState.TESTING
        for _ in range(3):
            self.gpio_writer("REMOTE_BUZZER_CTRL", True)
            self.sleep_fn(0.15)
            self.gpio_writer("REMOTE_BUZZER_CTRL", False)
            self.sleep_fn(0.15)
        self._state = ServiceState.ACTIVE
    # --------------------------------------------------------
    # LIVE ADC READ
    # --------------------------------------------------------
    def read_all_adc(self) -> dict:
        names = [
            "LEFT_JOYSTICK_X",
            "LEFT_JOYSTICK_Y",
            "RIGHT_JOYSTICK_X",
            "RIGHT_JOYSTICK_Y",
            "BATTERY_VOLTAGE_SENSE",
            "LM35_TEMP",
            "NTC_BATTERY_TEMP",
        ]
        values = {}
        for n in names:
            try:
                values[n] = float(self.adc_reader(n))
            except Exception:
                values[n] = None
        return values
    # --------------------------------------------------------
    # JOYSTICK SNAPSHOT
    # --------------------------------------------------------
    def read_joystick(self) -> dict:
        try:
            return {
                "lx": self.adc_reader("LEFT_JOYSTICK_X"),
                "ly": self.adc_reader("LEFT_JOYSTICK_Y"),
                "rx": self.adc_reader("RIGHT_JOYSTICK_X"),
                "ry": self.adc_reader("RIGHT_JOYSTICK_Y"),
            }
        except Exception:
            return {}
    # --------------------------------------------------------
    # CALIBRATION WORKFLOW
    # --------------------------------------------------------
    def start_calibration(self):
        self._state = ServiceState.CALIBRATION
    def capture_center(self) -> dict:
        data = self.read_joystick()
        return data
    def finish_calibration(self):
        self._state = ServiceState.ACTIVE
    # --------------------------------------------------------
    # SNAPSHOT
    # --------------------------------------------------------
    def build_snapshot(self) -> ServiceSnapshot:
        snap = ServiceSnapshot(
            ts=time.time(),
            state=self._state,
            joystick=self.read_joystick(),
            adc=self.read_all_adc(),
            outputs={
                "fan": self.state_store.is_fan_active(),
                "buzzer": self.state_store.is_buzzer_active(),
            },
        )
        self._last_snapshot = snap
        return snap
    def last_snapshot(self) -> Optional[ServiceSnapshot]:
        return self._last_snapshot


# ============================================================
# MODULE-R022
# ============================================================

# runtime/remotepi_mode_fsm.py
"""
MODULE-R022
RemotePi Mode FSM
-----------------

Purpose:
    High-level operational mode state machine for RemotePi.

Responsibilities:
    - Manage active control mode
    - Enforce motion permission rules
    - Integrate safety/watchdog/shutdown transitions
    - Provide deterministic mode transitions
"""
import time
from enum import Enum
from dataclasses import dataclass
# ============================================================
# ENUMS
# ============================================================
class RemoteMode(str, Enum):
    BOOT = "BOOT"
    CONTROL_MENU = "CONTROL_MENU"
    MANUAL_CONTROL = "MANUAL_CONTROL"
    SERVICE_MODE = "SERVICE_MODE"
    FAULT_LOCK = "FAULT_LOCK"
    SAFE_SHUTDOWN = "SAFE_SHUTDOWN"
# ============================================================
# DATA MODEL
# ============================================================
@dataclass
class ModeSnapshot:
    ts: float
    mode: RemoteMode
    system_running: bool
    motion_allowed: bool
    user_control_allowed: bool
# ============================================================
# MAIN FSM
# ============================================================
class RemotePiModeFSM:
    def __init__(self, state_store):
        self.state_store = state_store
        self._mode = RemoteMode.BOOT
    # --------------------------------------------------------
    @property
    def mode(self) -> RemoteMode:
        return self._mode
    # --------------------------------------------------------
    def _apply_permissions(self):
        """
        Sync permissions into state store
        """
        if self._mode == RemoteMode.BOOT:
            self.state_store.set_system_running(False)
            self.state_store.set_motion_allowed(False)
        elif self._mode == RemoteMode.CONTROL_MENU:
            self.state_store.set_system_running(False)
            self.state_store.set_motion_allowed(False)
        elif self._mode == RemoteMode.MANUAL_CONTROL:
            self.state_store.set_system_running(True)
            self.state_store.set_motion_allowed(True)
        elif self._mode == RemoteMode.SERVICE_MODE:
            self.state_store.set_system_running(False)
            self.state_store.set_motion_allowed(False)
        elif self._mode == RemoteMode.FAULT_LOCK:
            self.state_store.set_system_running(False)
            self.state_store.set_motion_allowed(False)
        elif self._mode == RemoteMode.SAFE_SHUTDOWN:
            self.state_store.set_system_running(False)
            self.state_store.set_motion_allowed(False)
    # --------------------------------------------------------
    # TRANSITIONS
    # --------------------------------------------------------
    def to_control_menu(self):
        self._mode = RemoteMode.CONTROL_MENU
        self._apply_permissions()
    def to_manual(self):
        if not self.state_store.is_safe_to_run():
            return
        self._mode = RemoteMode.MANUAL_CONTROL
        self._apply_permissions()
    def to_service(self):
        self._mode = RemoteMode.SERVICE_MODE
        self._apply_permissions()
    def to_fault_lock(self):
        self._mode = RemoteMode.FAULT_LOCK
        self._apply_permissions()
    def to_shutdown(self):
        self._mode = RemoteMode.SAFE_SHUTDOWN
        self._apply_permissions()
    # --------------------------------------------------------
    # SAFETY HOOK
    # --------------------------------------------------------
    def safety_override(self):
        safety = self.state_store.get_safety()
        sev = safety.get("severity", "NORMAL")
        if sev in ("FAULT", "CRITICAL"):
            self.to_fault_lock()
        if sev == "SHUTDOWN":
            self.to_shutdown()
    # --------------------------------------------------------
    # SNAPSHOT
    # --------------------------------------------------------
    def snapshot(self) -> ModeSnapshot:
        return ModeSnapshot(
            ts=time.time(),
            mode=self._mode,
            system_running=self.state_store.is_system_running(),
            motion_allowed=self.state_store.is_motion_allowed(),
            user_control_allowed=self.state_store.accept_user_control(),
        )


# ============================================================
# MODULE-R023
# ============================================================

# runtime/remotepi_hmi_event_mapper.py
"""
MODULE-R023
RemotePi HMI Event Mapper
-------------------------

Purpose:
    Non-invasive adapter layer between existing Kivy HMI actions and the
    standardized RemotePi runtime event model.

Design goals:
    - Preserve current HMI code structure
    - Do not break existing button logic
    - Convert UI names/actions into normalized runtime events
    - Prepare clean integration path for FSM / router / state store

Important note:
    This module does NOT directly modify Kivy widgets.
    It only maps names, emits normalized events, and can optionally mirror
    current HMI app state into runtime-friendly structures.
"""
import time
from dataclasses import dataclass, field
from typing import Callable, Optional, Any
from hardware.remotepi_signal_names import (
    EVENT_UI_AUTONOM,
    EVENT_UI_DRIVER,
    EVENT_UI_DRAWWORKS,
    EVENT_UI_FAULT,
    EVENT_UI_HEARTBEAT,
    EVENT_UI_HIGH_BEAM_LIGHT,
    EVENT_UI_LOW_BEAM_LIGHT,
    EVENT_UI_MENU,
    EVENT_UI_PARKING_LIGHT,
    EVENT_UI_RIG_FLOOR_LIGHT,
    EVENT_UI_ROTARY_TABLE,
    EVENT_UI_SANDLINE,
    EVENT_UI_SIGNAL_LHR_LIGHT,
    EVENT_UI_START_STOP,
    EVENT_UI_WHEEL,
    EVENT_UI_WINCH,
)
# ============================================================
# DATA MODELS
# ============================================================
@dataclass
class HMIMapResult:
    event_name: str
    payload: dict[str, Any] = field(default_factory=dict)
@dataclass
class HMISnapshot:
    ts: float
    screen_name: str
    system_started: bool
    autonom_active: bool
    active_mode: Optional[str]
    engine_sound_enabled: bool
    parking_light_on: bool
    low_beam_on: bool
    high_beam_on: bool
    signal_lhr_on: bool
    rig_floor_light_on: bool
    rotation_light_on: bool
    batt_master_level: float
    batt_remote_level: float
    mc_fan_state: str
    rc_fan_state: str
    fault_level: int
    fault_text: str
    system_status: str
# ============================================================
# MAIN CLASS
# ============================================================
class RemotePiHMIEventMapper:
    """
    Safe adapter for the existing RemotePiHMIApp.
    Integration philosophy:
        Existing Kivy app keeps its current behavior.
        This mapper only standardizes outgoing events.
    """
    #: Existing Kivy on_btn(name) values -> standardized runtime event names
    BUTTON_EVENT_MAP = {
        "WHEEL": EVENT_UI_WHEEL,
        "DRIVER": EVENT_UI_DRIVER,
        "DRAWWORKS": EVENT_UI_DRAWWORKS,
        "SANDLINE": EVENT_UI_SANDLINE,
        "WINCH": EVENT_UI_WINCH,
        "ROTARY TABLE": EVENT_UI_ROTARY_TABLE,
        "AUTONOM": EVENT_UI_AUTONOM,
        "MENU": EVENT_UI_MENU,
        "START_STOP": EVENT_UI_START_STOP,
        "PARKING LIGHT": EVENT_UI_PARKING_LIGHT,
        "LOW BEAM LIGHT": EVENT_UI_LOW_BEAM_LIGHT,
        "HIGH BEAM LIGHT": EVENT_UI_HIGH_BEAM_LIGHT,
        "SIGNAL(LHR)LIGHT": EVENT_UI_SIGNAL_LHR_LIGHT,
        "RIG FLOOR LIGHT": EVENT_UI_RIG_FLOOR_LIGHT,
        "ROTATION LIGHT": EVENT_UI_ROTATION_LIGHT,
    }
    #: Top icon names -> semantic UI action/event names
    TOP_ICON_EVENT_MAP = {
        "battery": "EVENT_UI_TOP_BATTERY",
        "wifi": "EVENT_UI_TOP_WIFI",
        "bluetooth": "EVENT_UI_TOP_BLUETOOTH",
        "camera": "EVENT_UI_TOP_CAMERA",
    }
    def __init__(
        self,
        event_sink: Optional[Callable[[str, dict], None]] = None,
        status_sink: Optional[Callable[[str, dict], None]] = None,
    ):
        """
        event_sink(event_name, payload):
            Optional normalized event output.
        status_sink(topic, payload):
            Optional observability/log output.
        """
        self.event_sink = event_sink
        self.status_sink = status_sink
    # --------------------------------------------------------
    # INTERNAL HELPERS
    # --------------------------------------------------------
    def _emit(self, event_name: str, payload: Optional[dict] = None) -> HMIMapResult:
        payload = payload or {}
        payload.setdefault("ts", time.time())
        if self.event_sink is not None:
            self.event_sink(event_name, payload)
        if self.status_sink is not None:
            self.status_sink("hmi_mapper/event", {
                "event_name": event_name,
                "payload": dict(payload),
            })
        return HMIMapResult(event_name=event_name, payload=payload)
    def _status(self, topic: str, **payload) -> None:
        if self.status_sink is not None:
            self.status_sink(topic, {
                "ts": time.time(),
                **payload,
            })
    # --------------------------------------------------------
    # BUTTON MAPPING
    # --------------------------------------------------------
    def map_button(
        self,
        *,
        name: str,
        button_state: Optional[str] = None,
        active_mode: Optional[str] = None,
        is_system_started: Optional[bool] = None,
        is_autonom_active: Optional[bool] = None,
    ) -> Optional[HMIMapResult]:
        """
        Map current HMI on_btn(name) semantics to normalized runtime events.
        Parameters mirror the current Kivy app's naming and state style.
        """
        event_name = self.BUTTON_EVENT_MAP.get(name)
        if event_name is None:
            self._status("hmi_mapper/unmapped_button", name=name)
            return None
        payload = {
            "ui_name": name,
            "button_state": button_state,
            "active_mode": active_mode,
            "is_system_started": is_system_started,
            "is_autonom_active": is_autonom_active,
        }
        return self._emit(event_name, payload)
    # --------------------------------------------------------
    # TOP ICON MAPPING
    # --------------------------------------------------------
    def map_top_icon(self, icon_name: str) -> Optional[HMIMapResult]:
        event_name = self.TOP_ICON_EVENT_MAP.get(icon_name)
        if event_name is None:
            self._status("hmi_mapper/unmapped_top_icon", icon_name=icon_name)
            return None
        return self._emit(event_name, {
            "icon_name": icon_name,
        })
    # --------------------------------------------------------
    # FAULT BUTTON MAPPING
    # --------------------------------------------------------
    def map_fault_short_press(self, fault_level: int) -> HMIMapResult:
        """
        Existing HMI short press currently behaves like status peek/log action.
        We preserve that meaning by emitting EVENT_UI_FAULT with press_type=short.
        """
        return self._emit(EVENT_UI_FAULT, {
            "press_type": "short",
            "fault_level": int(fault_level),
        })
    def map_fault_long_press(self, fault_level: int, fault_count: int = 0) -> HMIMapResult:
        """
        Existing HMI long press opens fault screen after ~2 seconds.
        We preserve that behavior semantically here.
        """
        return self._emit(EVENT_UI_FAULT, {
            "press_type": "long",
            "fault_level": int(fault_level),
            "fault_count": int(fault_count),
            "open_fault_screen": True,
        })
    # --------------------------------------------------------
    # JOYSTICK BUTTON MAPPING
    # --------------------------------------------------------
    def map_left_joystick_button(self, press_type: str) -> HMIMapResult:
        """
        Existing HMI behavior:
            - left joystick long press -> open faults
        """
        press_type = str(press_type).lower().strip()
        if press_type == "long":
            return self._emit("EVENT_LEFT_JOYSTICK_BUTTON_LONG", {
                "source": "HMI_APP",
                "mapped_behavior": "OPEN_FAULTS",
            })
        return self._emit("EVENT_LEFT_JOYSTICK_BUTTON_SHORT", {
            "source": "HMI_APP",
        })
    def map_right_joystick_button(self, press_type: str, engine_sound_enabled: bool) -> HMIMapResult:
        """
        Existing HMI behavior:
            - right joystick short press toggles engine sound enable flag
        This is preserved only as event meaning. No local buzzer assumption is made.
        """
        press_type = str(press_type).lower().strip()
        if press_type == "long":
            return self._emit("EVENT_RIGHT_JOYSTICK_BUTTON_LONG", {
                "source": "HMI_APP",
                "engine_sound_enabled": bool(engine_sound_enabled),
            })
        return self._emit("EVENT_RIGHT_JOYSTICK_BUTTON_SHORT", {
            "source": "HMI_APP",
            "engine_sound_enabled": bool(engine_sound_enabled),
        })
    # --------------------------------------------------------
    # SCREEN / NAVIGATION MAPPING
    # --------------------------------------------------------
    def map_screen_open(self, screen_name: str) -> HMIMapResult:
        return self._emit("EVENT_UI_SCREEN_OPEN", {
            "screen_name": str(screen_name),
        })
    def map_screen_close(self, screen_name: str) -> HMIMapResult:
        return self._emit("EVENT_UI_SCREEN_CLOSE", {
            "screen_name": str(screen_name),
        })
    def map_camera_open(self) -> HMIMapResult:
        return self._emit("EVENT_UI_TOP_CAMERA", {
            "action": "open_camera",
        })
    def map_camera_close(self) -> HMIMapResult:
        return self._emit("EVENT_UI_CAMERA_CLOSE", {
            "action": "close_camera",
        })
    # --------------------------------------------------------
    # STATE MIRRORING
    # --------------------------------------------------------
    def snapshot_from_app(self, app: Any) -> HMISnapshot:
        """
        Build a runtime-friendly HMI snapshot from the existing Kivy app
        without changing the app structure.
        """
        current_screen = ""
        try:
            current_screen = str(app.sm.current)
        except Exception:
            current_screen = "unknown"
        return HMISnapshot(
            ts=time.time(),
            screen_name=current_screen,
            system_started=bool(getattr(app, "is_system_started", False)),
            autonom_active=bool(getattr(app, "is_autonom_active", False)),
            active_mode=getattr(app, "active_mode", None),
            engine_sound_enabled=bool(getattr(app, "engine_sound_enabled", False)),
            parking_light_on=bool(getattr(app, "parking_light_on", False)),
            low_beam_on=bool(getattr(app, "low_beam_on", False)),
            high_beam_on=bool(getattr(app, "high_beam_on", False)),
            signal_lhr_on=bool(getattr(app, "signal_lhr_on", False)),
            rig_floor_light_on=bool(getattr(app, "rig_floor_light_on", False)),
            rotation_light_on=bool(getattr(app, "rotation_light_on", False)),
            batt_master_level=float(getattr(app, "batt_m_level", 0.0)),
            batt_remote_level=float(getattr(app, "batt_r_level", 0.0)),
            mc_fan_state=str(getattr(app, "mc_fan_state", "COMM_LOST")),
            rc_fan_state=str(getattr(app, "rc_fan_state", "COMM_LOST")),
            fault_level=int(getattr(app, "fault_level", 0)),
            fault_text=str(getattr(app, "fault_text", "")),
            system_status=str(getattr(app, "system_status", "")),
        )
    def emit_snapshot_heartbeat(self, app: Any) -> HMIMapResult:
        snap = self.snapshot_from_app(app)
        return self._emit(EVENT_UI_HEARTBEAT, {
            "screen_name": snap.screen_name,
            "system_started": snap.system_started,
            "autonom_active": snap.autonom_active,
            "active_mode": snap.active_mode,
            "engine_sound_enabled": snap.engine_sound_enabled,
            "parking_light_on": snap.parking_light_on,
            "low_beam_on": snap.low_beam_on,
            "high_beam_on": snap.high_beam_on,
            "signal_lhr_on": snap.signal_lhr_on,
            "rig_floor_light_on": snap.rig_floor_light_on,
            "rotation_light_on": snap.rotation_light_on,
            "batt_master_level": snap.batt_master_level,
            "batt_remote_level": snap.batt_remote_level,
            "mc_fan_state": snap.mc_fan_state,
            "rc_fan_state": snap.rc_fan_state,
            "fault_level": snap.fault_level,
            "system_status": snap.system_status,
        })
    # --------------------------------------------------------
    # SAFE INTEGRATION HELPERS
    # --------------------------------------------------------
    def bind_existing_app(self, app: Any) -> None:
        """
        Optional lightweight helper.
        This does NOT monkey-patch behavior.
        It only attaches mapper reference for future use.
        Example:
            mapper.bind_existing_app(app)
            app.hmi_mapper = mapper
        """
        setattr(app, "hmi_mapper", self)
        self._status("hmi_mapper/bound", app_class=app.__class__.__name__)
    def build_button_payload_from_app(
        self,
        app: Any,
        name: str,
        button_state: Optional[str] = None,
    ) -> dict[str, Any]:
        return {
            "ui_name": name,
            "button_state": button_state,
            "active_mode": getattr(app, "active_mode", None),
            "is_system_started": bool(getattr(app, "is_system_started", False)),
            "is_autonom_active": bool(getattr(app, "is_autonom_active", False)),
            "screen_name": getattr(getattr(app, "sm", None), "current", "unknown"),
        }


# ============================================================
# MODULE-R024
# ============================================================

# runtime/remotepi_hmi_runtime_bridge.py
"""
MODULE-R024
RemotePi HMI Runtime Bridge
---------------------------

Purpose:
    Safe bridge between the existing Kivy HMI and the newer RemotePi runtime stack.

Responsibilities:
    - Accept normalized HMI events from R023 mapper
    - Forward mode-related events into R022 FSM
    - Forward command/UI events into R008 event router
    - Mirror selected HMI state into runtime state store
    - Preserve compatibility with existing HMI behavior

Design mode:
    - passive: observe and mirror only
    - hybrid: route standardized events while allowing legacy HMI logic
    - active: runtime stack becomes primary authority
"""
import time
from dataclasses import dataclass
from typing import Any, Optional, Callable
# ============================================================
# CONFIG
# ============================================================
@dataclass
class HMIRuntimeBridgeConfig:
    mode: str = "hybrid"   # "passive" | "hybrid" | "active"
    mirror_hmi_state: bool = True
    forward_events_to_router: bool = True
    drive_fsm_from_hmi: bool = True
    emit_status_logs: bool = True
# ============================================================
# MAIN CLASS
# ============================================================
class RemotePiHMIRuntimeBridge:
    def __init__(
        self,
        *,
        mode_fsm=None,
        event_router=None,
        state_store=None,
        status_sink: Optional[Callable[[str, dict], None]] = None,
        config: Optional[HMIRuntimeBridgeConfig] = None,
    ):
        """
        mode_fsm:
            Expected compatible with RemotePiModeFSM-like API
        event_router:
            Expected compatible with RemotePiEventRouter.route_event(...)
        state_store:
            Expected compatible with RemotePiStateStore-like API
        status_sink(topic, payload):
            Optional observability sink
        """
        self.mode_fsm = mode_fsm
        self.event_router = event_router
        self.state_store = state_store
        self.status_sink = status_sink
        self.config = config or HMIRuntimeBridgeConfig()
        self._last_snapshot_ts = 0.0
        self._last_event_name: Optional[str] = None
    # --------------------------------------------------------
    # INTERNAL
    # --------------------------------------------------------
    def _emit_status(self, topic: str, **payload) -> None:
        if not self.config.emit_status_logs:
            return
        if self.status_sink is not None:
            self.status_sink(topic, {
                "ts": time.time(),
                **payload,
            })
    # --------------------------------------------------------
    # HMI SNAPSHOT MIRROR
    # --------------------------------------------------------
    def mirror_hmi_snapshot(self, snapshot: Any) -> None:
        """
        Mirror selected HMI-visible state into runtime state store.
        The snapshot may be:
            - HMISnapshot dataclass from R023
            - dict-like object
        """
        if not self.config.mirror_hmi_state or self.state_store is None:
            return
        if hasattr(snapshot, "__dict__"):
            data = vars(snapshot)
        elif isinstance(snapshot, dict):
            data = snapshot
        else:
            self._emit_status("hmi_bridge/mirror_skipped", reason="unsupported_snapshot_type")
            return
        try:
            # Mode/system mirror
            active_mode = data.get("active_mode")
            system_started = bool(data.get("system_started", False))
            if active_mode is not None and hasattr(self.state_store, "set_active_mode"):
                self.state_store.set_active_mode(str(active_mode))
            if hasattr(self.state_store, "set_system_running"):
                self.state_store.set_system_running(system_started)
            # Battery mirror
            batt_m = float(data.get("batt_master_level", 0.0))
            batt_r = float(data.get("batt_remote_level", 0.0))
            if hasattr(self.state_store, "update_battery"):
                # RemotePi state store tek bucket bekliyor; şimdilik remote battery baz alınır
                bucket = "STATE_BATTERY_NORMAL"
                if batt_r <= 10:
                    bucket = "STATE_BATTERY_SHUTDOWN"
                elif batt_r <= 20:
                    bucket = "STATE_BATTERY_CRITICAL"
                elif batt_r <= 40:
                    bucket = "STATE_BATTERY_WARNING"
                self.state_store.update_battery(
                    voltage=batt_r,
                    percent_est=batt_r,
                    bucket=bucket,
                )
            # Cooling / thermal-visible mirror
            if hasattr(self.state_store, "set_fan_active"):
                rc_state = str(data.get("rc_fan_state", "COMM_LOST"))
                self.state_store.set_fan_active(rc_state == "ON")
            # Safety/fault visible mirror
            fault_level = int(data.get("fault_level", 0))
            summary = str(data.get("system_status", ""))
            severity = "NORMAL"
            if fault_level == 1:
                severity = "WARNING"
            elif fault_level >= 2:
                severity = "FAULT"
            warnings = []
            faults = []
            if fault_level == 1:
                warnings.append("HMI_FAULT_LEVEL_1")
            elif fault_level >= 2:
                faults.append("HMI_FAULT_LEVEL_2")
            if hasattr(self.state_store, "update_safety"):
                self.state_store.update_safety(
                    severity=severity,
                    primary_state="STATE_ACTIVE" if system_started else "STATE_READY",
                    accept_user_control=(fault_level < 2),
                    allow_new_motion_commands=(system_started and fault_level < 2),
                    request_shutdown=False,
                    ui_fault_latched=(fault_level > 0),
                    summary=summary or "HMI mirror update",
                    warnings=warnings,
                    faults=faults,
                )
            self._last_snapshot_ts = time.time()
            self._emit_status(
                "hmi_bridge/snapshot_mirrored",
                active_mode=active_mode,
                system_started=system_started,
                fault_level=fault_level,
            )
        except Exception as exc:
            self._emit_status("hmi_bridge/mirror_error", error=str(exc))
    # --------------------------------------------------------
    # FSM FORWARDING
    # --------------------------------------------------------
    def _drive_fsm_from_event(self, event_name: str, payload: dict) -> None:
        if not self.config.drive_fsm_from_hmi or self.mode_fsm is None:
            return
        try:
            if event_name == "EVENT_UI_MENU":
                if hasattr(self.mode_fsm, "to_control_menu"):
                    self.mode_fsm.to_control_menu()
            elif event_name == "EVENT_UI_AUTONOM":
                # mevcut FSM'de AUTONOM ayrı top-level mode değilse menu/manual ayrımına göre genişletilebilir
                if hasattr(self.mode_fsm, "to_control_menu"):
                    self.mode_fsm.to_control_menu()
            elif event_name in (
                "EVENT_UI_WHEEL",
                "EVENT_UI_DRIVER",
                "EVENT_UI_DRAWWORKS",
                "EVENT_UI_SANDLINE",
                "EVENT_UI_WINCH",
                "EVENT_UI_ROTARY_TABLE",
            ):
                if hasattr(self.mode_fsm, "to_manual"):
                    self.mode_fsm.to_manual()
            elif event_name == "EVENT_UI_FAULT":
                press_type = str(payload.get("press_type", "")).lower()
                if press_type == "long" and hasattr(self.mode_fsm, "to_fault_lock"):
                    self.mode_fsm.to_fault_lock()
            self._emit_status("hmi_bridge/fsm_driven", event_name=event_name)
        except Exception as exc:
            self._emit_status("hmi_bridge/fsm_drive_error", event_name=event_name, error=str(exc))
    # --------------------------------------------------------
    # ROUTER FORWARDING
    # --------------------------------------------------------
    def _forward_to_router(self, event_name: str, payload: dict) -> None:
        if not self.config.forward_events_to_router or self.event_router is None:
            return
        try:
            self.event_router.route_event(event_name, payload)
            self._emit_status("hmi_bridge/router_forwarded", event_name=event_name)
        except Exception as exc:
            self._emit_status("hmi_bridge/router_error", event_name=event_name, error=str(exc))
    # --------------------------------------------------------
    # PUBLIC EVENT ENTRY
    # --------------------------------------------------------
    def handle_hmi_event(self, event_name: str, payload: Optional[dict] = None) -> None:
        payload = payload or {}
        self._last_event_name = event_name
        self._emit_status(
            "hmi_bridge/event_received",
            event_name=event_name,
            payload=payload,
            bridge_mode=self.config.mode,
        )
        if self.config.mode == "passive":
            return
        if self.config.mode in ("hybrid", "active"):
            self._drive_fsm_from_event(event_name, payload)
            self._forward_to_router(event_name, payload)
    # --------------------------------------------------------
    # APP SNAPSHOT ENTRY
    # --------------------------------------------------------
    def sync_from_app(self, app: Any) -> None:
        """
        Lightweight mirroring from existing Kivy app object.
        """
        if self.state_store is None:
            return
        try:
            snapshot = {
                "screen_name": getattr(getattr(app, "sm", None), "current", "unknown"),
                "system_started": bool(getattr(app, "is_system_started", False)),
                "autonom_active": bool(getattr(app, "is_autonom_active", False)),
                "active_mode": getattr(app, "active_mode", None),
                "engine_sound_enabled": bool(getattr(app, "engine_sound_enabled", False)),
                "parking_light_on": bool(getattr(app, "parking_light_on", False)),
                "low_beam_on": bool(getattr(app, "low_beam_on", False)),
                "high_beam_on": bool(getattr(app, "high_beam_on", False)),
                "signal_lhr_on": bool(getattr(app, "signal_lhr_on", False)),
                "rig_floor_light_on": bool(getattr(app, "rig_floor_light_on", False)),
                "rotation_light_on": bool(getattr(app, "rotation_light_on", False)),
                "batt_master_level": float(getattr(app, "batt_m_level", 0.0)),
                "batt_remote_level": float(getattr(app, "batt_r_level", 0.0)),
                "mc_fan_state": str(getattr(app, "mc_fan_state", "COMM_LOST")),
                "rc_fan_state": str(getattr(app, "rc_fan_state", "COMM_LOST")),
                "fault_level": int(getattr(app, "fault_level", 0)),
                "fault_text": str(getattr(app, "fault_text", "")),
                "system_status": str(getattr(app, "system_status", "")),
            }
            self.mirror_hmi_snapshot(snapshot)
        except Exception as exc:
            self._emit_status("hmi_bridge/app_sync_error", error=str(exc))
    # --------------------------------------------------------
    # QUICK INSPECTION
    # --------------------------------------------------------
    def get_bridge_status(self) -> dict:
        return {
            "mode": self.config.mode,
            "mirror_hmi_state": self.config.mirror_hmi_state,
            "forward_events_to_router": self.config.forward_events_to_router,
            "drive_fsm_from_hmi": self.config.drive_fsm_from_hmi,
            "last_snapshot_ts": self._last_snapshot_ts,
            "last_event_name": self._last_event_name,
        }


# ============================================================
# MODULE-R025
# ============================================================

# runtime/remotepi_integration_profile.py
"""
MODULE-R025
RemotePi Integration Profile
----------------------------

Purpose:
    Transition profile between legacy HMI behavior and the new runtime stack.

Responsibilities:
    - Define authority model
    - Select passive / hybrid / active integration mode
    - Gate which events are handled by legacy HMI
    - Gate which events are forwarded into runtime
    - Support staged migration without breaking the existing UI

Design note:
    This module is policy-only.
    It does not perform routing by itself.
"""
from dataclasses import dataclass, field
from typing import Final
# ============================================================
# DATA MODELS
# ============================================================
@dataclass
class AuthorityProfile:
    hmi_is_visual_source: bool
    hmi_is_control_source: bool
    runtime_is_primary_authority: bool
    legacy_hmi_logic_enabled: bool
@dataclass
class EventPolicy:
    forward_to_runtime: bool
    keep_legacy_behavior: bool
    mirror_to_state_store: bool
    drive_fsm: bool
@dataclass
class IntegrationProfile:
    name: str
    bridge_mode: str  # passive | hybrid | active
    authority: AuthorityProfile
    event_policies: dict[str, EventPolicy] = field(default_factory=dict)
    description: str = ""
# ============================================================
# COMMON EVENT GROUPS
# ============================================================
MODE_EVENTS: Final[tuple[str, ...]] = (
    "EVENT_UI_WHEEL",
    "EVENT_UI_DRIVER",
    "EVENT_UI_DRAWWORKS",
    "EVENT_UI_SANDLINE",
    "EVENT_UI_WINCH",
    "EVENT_UI_ROTARY_TABLE",
    "EVENT_UI_AUTONOM",
    "EVENT_UI_MENU",
)
ACTION_EVENTS: Final[tuple[str, ...]] = (
    "EVENT_UI_START_STOP",
    "EVENT_UI_PARKING_LIGHT",
    "EVENT_UI_LOW_BEAM_LIGHT",
    "EVENT_UI_HIGH_BEAM_LIGHT",
    "EVENT_UI_SIGNAL_LHR_LIGHT",
    "EVENT_UI_RIG_FLOOR_LIGHT",
    "EVENT_UI_ROTATION_LIGHT",
)
TOP_ICON_EVENTS: Final[tuple[str, ...]] = (
    "EVENT_UI_TOP_BATTERY",
    "EVENT_UI_TOP_WIFI",
    "EVENT_UI_TOP_BLUETOOTH",
    "EVENT_UI_TOP_CAMERA",
)
FAULT_EVENTS: Final[tuple[str, ...]] = (
    "EVENT_UI_FAULT",
    "EVENT_LEFT_JOYSTICK_BUTTON_LONG",
    "EVENT_LEFT_JOYSTICK_BUTTON_SHORT",
    "EVENT_RIGHT_JOYSTICK_BUTTON_SHORT",
    "EVENT_RIGHT_JOYSTICK_BUTTON_LONG",
)
SCREEN_EVENTS: Final[tuple[str, ...]] = (
    "EVENT_UI_SCREEN_OPEN",
    "EVENT_UI_SCREEN_CLOSE",
    "EVENT_UI_CAMERA_CLOSE",
    "EVENT_UI_HEARTBEAT",
)
# ============================================================
# POLICY BUILDERS
# ============================================================
def _make_policy(
    *,
    forward_to_runtime: bool,
    keep_legacy_behavior: bool,
    mirror_to_state_store: bool,
    drive_fsm: bool,
) -> EventPolicy:
    return EventPolicy(
        forward_to_runtime=forward_to_runtime,
        keep_legacy_behavior=keep_legacy_behavior,
        mirror_to_state_store=mirror_to_state_store,
        drive_fsm=drive_fsm,
    )
def build_passive_profile() -> IntegrationProfile:
    """
    Existing HMI remains fully authoritative.
    Runtime only observes.
    """
    event_policies: dict[str, EventPolicy] = {}
    for evt in MODE_EVENTS + ACTION_EVENTS + TOP_ICON_EVENTS + FAULT_EVENTS + SCREEN_EVENTS:
        event_policies[evt] = _make_policy(
            forward_to_runtime=False,
            keep_legacy_behavior=True,
            mirror_to_state_store=True,
            drive_fsm=False,
        )
    return IntegrationProfile(
        name="PASSIVE_OBSERVE_ONLY",
        bridge_mode="passive",
        authority=AuthorityProfile(
            hmi_is_visual_source=True,
            hmi_is_control_source=True,
            runtime_is_primary_authority=False,
            legacy_hmi_logic_enabled=True,
        ),
        event_policies=event_policies,
        description="Legacy HMI remains authoritative; runtime only mirrors.",
    )
def build_hybrid_profile() -> IntegrationProfile:
    """
    Safest staged migration profile.
    Legacy HMI behavior remains active, but standardized events are also
    forwarded into runtime for FSM/router/state synchronization.
    """
    event_policies: dict[str, EventPolicy] = {}
    for evt in MODE_EVENTS:
        event_policies[evt] = _make_policy(
            forward_to_runtime=True,
            keep_legacy_behavior=True,
            mirror_to_state_store=True,
            drive_fsm=True,
        )
    for evt in ACTION_EVENTS:
        event_policies[evt] = _make_policy(
            forward_to_runtime=True,
            keep_legacy_behavior=True,
            mirror_to_state_store=True,
            drive_fsm=False,
        )
    for evt in TOP_ICON_EVENTS:
        event_policies[evt] = _make_policy(
            forward_to_runtime=True,
            keep_legacy_behavior=True,
            mirror_to_state_store=True,
            drive_fsm=False,
        )
    for evt in FAULT_EVENTS:
        event_policies[evt] = _make_policy(
            forward_to_runtime=True,
            keep_legacy_behavior=True,
            mirror_to_state_store=True,
            drive_fsm=True,
        )
    for evt in SCREEN_EVENTS:
        event_policies[evt] = _make_policy(
            forward_to_runtime=True,
            keep_legacy_behavior=True,
            mirror_to_state_store=True,
            drive_fsm=False,
        )
    return IntegrationProfile(
        name="HYBRID_MIRROR_AND_FORWARD",
        bridge_mode="hybrid",
        authority=AuthorityProfile(
            hmi_is_visual_source=True,
            hmi_is_control_source=True,
            runtime_is_primary_authority=False,
            legacy_hmi_logic_enabled=True,
        ),
        event_policies=event_policies,
        description="Legacy HMI keeps behavior; runtime receives mirrored standardized events.",
    )
def build_active_profile() -> IntegrationProfile:
    """
    Runtime becomes primary decision authority.
    HMI becomes mostly visual/input frontend.
    """
    event_policies: dict[str, EventPolicy] = {}
    for evt in MODE_EVENTS + ACTION_EVENTS + FAULT_EVENTS:
        event_policies[evt] = _make_policy(
            forward_to_runtime=True,
            keep_legacy_behavior=False,
            mirror_to_state_store=True,
            drive_fsm=True,
        )
    for evt in TOP_ICON_EVENTS + SCREEN_EVENTS:
        event_policies[evt] = _make_policy(
            forward_to_runtime=True,
            keep_legacy_behavior=True,
            mirror_to_state_store=True,
            drive_fsm=False,
        )
    return IntegrationProfile(
        name="ACTIVE_RUNTIME_AUTHORITY",
        bridge_mode="active",
        authority=AuthorityProfile(
            hmi_is_visual_source=True,
            hmi_is_control_source=False,
            runtime_is_primary_authority=True,
            legacy_hmi_logic_enabled=False,
        ),
        event_policies=event_policies,
        description="Runtime becomes primary authority; HMI becomes frontend and event source.",
    )
# ============================================================
# DEFAULT PROFILE
# ============================================================
DEFAULT_INTEGRATION_PROFILE: Final[IntegrationProfile] = build_hybrid_profile()
# ============================================================
# HELPERS
# ============================================================
def get_event_policy(
    event_name: str,
    profile: IntegrationProfile = DEFAULT_INTEGRATION_PROFILE,
) -> EventPolicy:
    return profile.event_policies.get(
        event_name,
        _make_policy(
            forward_to_runtime=True,
            keep_legacy_behavior=True,
            mirror_to_state_store=True,
            drive_fsm=False,
        ),
    )
def should_forward_to_runtime(
    event_name: str,
    profile: IntegrationProfile = DEFAULT_INTEGRATION_PROFILE,
) -> bool:
    return get_event_policy(event_name, profile).forward_to_runtime
def should_keep_legacy_behavior(
    event_name: str,
    profile: IntegrationProfile = DEFAULT_INTEGRATION_PROFILE,
) -> bool:
    return get_event_policy(event_name, profile).keep_legacy_behavior
def should_mirror_to_state_store(
    event_name: str,
    profile: IntegrationProfile = DEFAULT_INTEGRATION_PROFILE,
) -> bool:
    return get_event_policy(event_name, profile).mirror_to_state_store
def should_drive_fsm(
    event_name: str,
    profile: IntegrationProfile = DEFAULT_INTEGRATION_PROFILE,
) -> bool:
    return get_event_policy(event_name, profile).drive_fsm


# ============================================================
# MODULE-R026
# ============================================================

# runtime/remotepi_hybrid_integration_manager.py
"""
MODULE-R026
RemotePi Hybrid Integration Manager
-----------------------------------

Purpose:
    Runtime coordination layer for staged coexistence between the existing
    legacy Kivy HMI and the newer RemotePi runtime stack.

Responsibilities:
    - Own the integration profile (R025)
    - Wire mapper (R023) and bridge (R024)
    - Apply per-event integration policy
    - Preserve legacy HMI behavior while forwarding standardized events
    - Support passive / hybrid / active staged migration

Notes:
    This module is intentionally non-invasive.
    It does not replace the legacy HMI logic by itself.
"""
import time
from dataclasses import dataclass
from typing import Any, Optional, Callable
from runtime.remotepi_hmi_event_mapper import RemotePiHMIEventMapper
from runtime.remotepi_hmi_runtime_bridge import (
    RemotePiHMIRuntimeBridge,
    HMIRuntimeBridgeConfig,
)
from runtime.remotepi_integration_profile import (
    IntegrationProfile,
    DEFAULT_INTEGRATION_PROFILE,
    get_event_policy,
)
# ============================================================
# DATA MODELS
# ============================================================
@dataclass
class HybridIntegrationStatus:
    ts: float
    profile_name: str
    bridge_mode: str
    mapper_bound: bool
    bridge_ready: bool
    last_event_name: Optional[str]
    last_snapshot_ts: float
# ============================================================
# MAIN CLASS
# ============================================================
class RemotePiHybridIntegrationManager:
    def __init__(
        self,
        *,
        profile: IntegrationProfile = DEFAULT_INTEGRATION_PROFILE,
        mode_fsm=None,
        event_router=None,
        state_store=None,
        status_sink: Optional[Callable[[str, dict], None]] = None,
    ):
        self.profile = profile
        self.mode_fsm = mode_fsm
        self.event_router = event_router
        self.state_store = state_store
        self.status_sink = status_sink
        self.mapper: Optional[RemotePiHMIEventMapper] = None
        self.bridge: Optional[RemotePiHMIRuntimeBridge] = None
        self._last_event_name: Optional[str] = None
        self._last_snapshot_ts: float = 0.0
    # --------------------------------------------------------
    # INTERNAL
    # --------------------------------------------------------
    def _emit_status(self, topic: str, **payload) -> None:
        if self.status_sink is not None:
            self.status_sink(topic, {
                "ts": time.time(),
                **payload,
            })
    # --------------------------------------------------------
    # BUILD / WIRING
    # --------------------------------------------------------
    def build(self) -> None:
        bridge_cfg = HMIRuntimeBridgeConfig(
            mode=self.profile.bridge_mode,
            mirror_hmi_state=True,
            forward_events_to_router=True,
            drive_fsm_from_hmi=True,
            emit_status_logs=True,
        )
        self.bridge = RemotePiHMIRuntimeBridge(
            mode_fsm=self.mode_fsm,
            event_router=self.event_router,
            state_store=self.state_store,
            status_sink=self.status_sink,
            config=bridge_cfg,
        )
        self.mapper = RemotePiHMIEventMapper(
            event_sink=self.handle_hmi_event,
            status_sink=self.status_sink,
        )
        self._emit_status(
            "integration_manager/built",
            profile_name=self.profile.name,
            bridge_mode=self.profile.bridge_mode,
        )
    # --------------------------------------------------------
    # APP BINDING
    # --------------------------------------------------------
    def bind_app(self, app: Any) -> None:
        if self.mapper is None or self.bridge is None:
            self.build()
        assert self.mapper is not None
        self.mapper.bind_existing_app(app)
        # Convenience refs on app for low-risk usage
        setattr(app, "hmi_mapper", self.mapper)
        setattr(app, "hmi_runtime_bridge", self.bridge)
        setattr(app, "hmi_integration_manager", self)
        self._emit_status(
            "integration_manager/app_bound",
            app_class=app.__class__.__name__,
            profile_name=self.profile.name,
        )
    # --------------------------------------------------------
    # POLICY-DRIVEN EVENT HANDLING
    # --------------------------------------------------------
    def handle_hmi_event(self, event_name: str, payload: Optional[dict] = None) -> None:
        payload = payload or {}
        self._last_event_name = event_name
        policy = get_event_policy(event_name, self.profile)
        self._emit_status(
            "integration_manager/event_received",
            event_name=event_name,
            payload=payload,
            forward_to_runtime=policy.forward_to_runtime,
            keep_legacy_behavior=policy.keep_legacy_behavior,
            mirror_to_state_store=policy.mirror_to_state_store,
            drive_fsm=policy.drive_fsm,
        )
        # Bridge yoksa en azından event kayıtlı kalsın
        if self.bridge is None:
            return
        # Bu katman legacy davranışı doğrudan iptal etmez.
        # Legacy davranışın korunup korunmayacağı bilgisi profile'da taşınır.
        # Şu anda legacy path'e müdahale etmiyoruz; sadece runtime forwarding policy uyguluyoruz.
        if policy.forward_to_runtime:
            self.bridge.handle_hmi_event(event_name, payload)
    # --------------------------------------------------------
    # SNAPSHOT SYNC
    # --------------------------------------------------------
    def sync_from_app(self, app: Any) -> None:
        if self.bridge is None:
            return
        self.bridge.sync_from_app(app)
        self._last_snapshot_ts = time.time()
        self._emit_status(
            "integration_manager/app_synced",
            screen_name=getattr(getattr(app, "sm", None), "current", "unknown"),
        )
    # --------------------------------------------------------
    # MAPPER ACCESS HELPERS
    # --------------------------------------------------------
    def map_button_from_app(self, app: Any, btn_instance: Any, name: str):
        if self.mapper is None:
            return None
        return self.mapper.map_button(
            name=name,
            button_state=getattr(btn_instance, "state", None),
            active_mode=getattr(app, "active_mode", None),
            is_system_started=bool(getattr(app, "is_system_started", False)),
            is_autonom_active=bool(getattr(app, "is_autonom_active", False)),
        )
    def map_top_icon_from_app(self, icon_name: str):
        if self.mapper is None:
            return None
        return self.mapper.map_top_icon(icon_name)
    def map_fault_short_from_app(self, app: Any):
        if self.mapper is None:
            return None
        return self.mapper.map_fault_short_press(
            int(getattr(app, "fault_level", 0))
        )
    def map_fault_long_from_app(self, app: Any):
        if self.mapper is None:
            return None
        return self.mapper.map_fault_long_press(
            int(getattr(app, "fault_level", 0)),
            fault_count=len(getattr(app, "fault_messages", [])),
        )
    def map_left_joystick_long(self):
        if self.mapper is None:
            return None
        return self.mapper.map_left_joystick_button("long")
    def map_right_joystick_short(self, engine_sound_enabled: bool):
        if self.mapper is None:
            return None
        return self.mapper.map_right_joystick_button(
            "short",
            bool(engine_sound_enabled),
        )
    # --------------------------------------------------------
    # HEARTBEAT
    # --------------------------------------------------------
    def emit_hmi_heartbeat(self, app: Any):
        if self.mapper is None:
            return None
        result = self.mapper.emit_snapshot_heartbeat(app)
        self.sync_from_app(app)
        return result
    # --------------------------------------------------------
    # PROFILE CONTROL
    # --------------------------------------------------------
    def set_profile(self, profile: IntegrationProfile) -> None:
        self.profile = profile
        if self.bridge is not None:
            # bridge mode profile ile hizalanır
            self.bridge.config = HMIRuntimeBridgeConfig(
                mode=profile.bridge_mode,
                mirror_hmi_state=True,
                forward_events_to_router=True,
                drive_fsm_from_hmi=True,
                emit_status_logs=True,
            )
        self._emit_status(
            "integration_manager/profile_changed",
            profile_name=profile.name,
            bridge_mode=profile.bridge_mode,
        )
    # --------------------------------------------------------
    # INSPECTION
    # --------------------------------------------------------
    def get_status(self) -> HybridIntegrationStatus:
        bridge_mode = self.profile.bridge_mode
        if self.bridge is not None:
            bridge_mode = self.bridge.config.mode
        return HybridIntegrationStatus(
            ts=time.time(),
            profile_name=self.profile.name,
            bridge_mode=bridge_mode,
            mapper_bound=self.mapper is not None,
            bridge_ready=self.bridge is not None,
            last_event_name=self._last_event_name,
            last_snapshot_ts=self._last_snapshot_ts,
        )
    def get_status_dict(self) -> dict:
        status = self.get_status()
        return {
            "ts": status.ts,
            "profile_name": status.profile_name,
            "bridge_mode": status.bridge_mode,
            "mapper_bound": status.mapper_bound,
            "bridge_ready": status.bridge_ready,
            "last_event_name": status.last_event_name,
            "last_snapshot_ts": status.last_snapshot_ts,
        }


# ============================================================
# MODULE-R027
# ============================================================

# runtime/remotepi_hmi_patch_adapter.py
"""
MODULE-R027
RemotePi HMI Patch Adapter
--------------------------

Purpose:
    Centralize minimal patch hooks for the existing RemotePiHMIApp.

Responsibilities:
    - Provide safe helper methods for patched HMI integration points
    - Keep legacy HMI file cleaner
    - Work with hmi_integration_manager if available
    - Fail safe / no-op when integration manager is absent

Design rule:
    Never break legacy HMI behavior.
"""
from typing import Any, Optional
class RemotePiHMIPatchAdapter:
    @staticmethod
    def _manager(app: Any):
        return getattr(app, "hmi_integration_manager", None)
    @staticmethod
    def bind_app(app: Any) -> None:
        mgr = RemotePiHMIPatchAdapter._manager(app)
        if mgr is not None:
            mgr.bind_app(app)
    @staticmethod
    def on_button(app: Any, btn_instance: Any, name: str) -> None:
        mgr = RemotePiHMIPatchAdapter._manager(app)
        if mgr is not None:
            mgr.map_button_from_app(app, btn_instance, name)
    @staticmethod
    def on_top_icon(app: Any, icon_name: str) -> None:
        mgr = RemotePiHMIPatchAdapter._manager(app)
        if mgr is not None:
            mgr.map_top_icon_from_app(icon_name)
    @staticmethod
    def on_fault_short(app: Any) -> None:
        mgr = RemotePiHMIPatchAdapter._manager(app)
        if mgr is not None:
            mgr.map_fault_short_from_app(app)
    @staticmethod
    def on_fault_long(app: Any) -> None:
        mgr = RemotePiHMIPatchAdapter._manager(app)
        if mgr is not None:
            mgr.map_fault_long_from_app(app)
    @staticmethod
    def on_left_joystick_long(app: Any) -> None:
        mgr = RemotePiHMIPatchAdapter._manager(app)
        if mgr is not None:
            mgr.map_left_joystick_long()
    @staticmethod
    def on_right_joystick_short(app: Any, engine_sound_enabled: bool) -> None:
        mgr = RemotePiHMIPatchAdapter._manager(app)
        if mgr is not None:
            mgr.map_right_joystick_short(engine_sound_enabled)
    @staticmethod
    def on_screen_open(app: Any) -> None:
        mgr = RemotePiHMIPatchAdapter._manager(app)
        if mgr is not None:
            mgr.sync_from_app(app)
    @staticmethod
    def on_screen_close(app: Any) -> None:
        mgr = RemotePiHMIPatchAdapter._manager(app)
        if mgr is not None:
            mgr.sync_from_app(app)
    @staticmethod
    def emit_heartbeat(app: Any) -> None:
        mgr = RemotePiHMIPatchAdapter._manager(app)
        if mgr is not None:
            mgr.emit_hmi_heartbeat(app)
    @staticmethod
    def sync_now(app: Any) -> None:
        mgr = RemotePiHMIPatchAdapter._manager(app)
        if mgr is not None:
            mgr.sync_from_app(app)


# ============================================================
# MODULE-R028
# ============================================================

# runtime/remotepi_hmi_patch_plan_final.py
"""
MODULE-R028
RemotePi HMI Patch Plan Final
-----------------------------

Purpose:
    Final integration patch plan for the existing RemotePiHMIApp.

This module is documentation-oriented and defines:
    - what must be added
    - what must NOT be changed
    - where patch points exist
    - what the staged migration path is

Primary design rule:
    Preserve the current working HMI behavior.
"""
from dataclasses import dataclass, field
from typing import Final
# ============================================================
# DATA MODELS
# ============================================================
@dataclass
class PatchPoint:
    method_name: str
    action: str
    risk_level: str
    note: str
@dataclass
class ProtectedArea:
    name: str
    reason: str
@dataclass
class PatchPlan:
    title: str
    strategy: str
    required_imports: tuple[str, ...]
    build_stage_actions: tuple[str, ...]
    patch_points: tuple[PatchPoint, ...]
    protected_areas: tuple[ProtectedArea, ...]
    recommended_profile: str
    summary: str
# ============================================================
# REQUIRED IMPORTS
# ============================================================
REQUIRED_IMPORTS: Final[tuple[str, ...]] = (
    "from runtime.remotepi_integration_profile import build_hybrid_profile",
    "from runtime.remotepi_hybrid_integration_manager import RemotePiHybridIntegrationManager",
    "from runtime.remotepi_hmi_patch_adapter import RemotePiHMIPatchAdapter",
)
# ============================================================
# BUILD STAGE ACTIONS
# ============================================================
BUILD_STAGE_ACTIONS: Final[tuple[str, ...]] = (
    "Create RemotePiHybridIntegrationManager with build_hybrid_profile().",
    "Bind the app with RemotePiHMIPatchAdapter.bind_app(self).",
    "Keep existing ScreenManager, UI widgets, and scheduling logic intact.",
    "Add a lightweight periodic heartbeat callback for integration sync.",
)
# ============================================================
# PATCH POINTS
# ============================================================
PATCH_POINTS: Final[tuple[PatchPoint, ...]] = (
    PatchPoint(
        method_name="build",
        action=(
            "Initialize hmi_integration_manager using build_hybrid_profile() "
            "and call RemotePiHMIPatchAdapter.bind_app(self). "
            "Also add periodic RemotePiHMIPatchAdapter.emit_heartbeat(self)."
        ),
        risk_level="LOW",
        note="Safe because it only attaches integration helpers."
    ),
    PatchPoint(
        method_name="on_btn",
        action=(
            "At method entry, call RemotePiHMIPatchAdapter.on_button(self, btn_instance, name)."
        ),
        risk_level="LOW",
        note="Does not alter existing button logic."
    ),
    PatchPoint(
        method_name="on_top_icon",
        action=(
            "At method entry, call RemotePiHMIPatchAdapter.on_top_icon(self, widget.icon_name)."
        ),
        risk_level="LOW",
        note="Existing screen open behavior remains unchanged."
    ),
    PatchPoint(
        method_name="on_fault",
        action=(
            "At method entry, call RemotePiHMIPatchAdapter.on_fault_short(self)."
        ),
        risk_level="LOW",
        note="Preserves current short press behavior."
    ),
    PatchPoint(
        method_name="_poll_joystick_buttons",
        action=(
            "On right joystick short press, call "
            "RemotePiHMIPatchAdapter.on_right_joystick_short(self, self.engine_sound_enabled). "
            "On left joystick long press, call "
            "RemotePiHMIPatchAdapter.on_left_joystick_long(self) and "
            "RemotePiHMIPatchAdapter.on_fault_long(self)."
        ),
        risk_level="LOW",
        note="Critical because Right Joystick ↔ engine sound behavior must remain intact."
    ),
    PatchPoint(
        method_name="open_faults / close_faults",
        action=(
            "After or before screen changes, call RemotePiHMIPatchAdapter.on_screen_open(self) "
            "or RemotePiHMIPatchAdapter.on_screen_close(self)."
        ),
        risk_level="LOW",
        note="Only mirrors state; does not alter fault UI flow."
    ),
    PatchPoint(
        method_name="open_battery / close_top_screen",
        action=(
            "Call RemotePiHMIPatchAdapter.on_screen_open(self) or "
            "RemotePiHMIPatchAdapter.on_screen_close(self) around screen transitions."
        ),
        risk_level="LOW",
        note="Preserves current top icon navigation behavior."
    ),
    PatchPoint(
        method_name="open_camera / close_camera",
        action=(
            "Keep current camera logic but add integration sync via "
            "RemotePiHMIPatchAdapter.on_screen_open(self) / on_screen_close(self)."
        ),
        risk_level="LOW",
        note="No camera flow rewrite required."
    ),
)
# ============================================================
# PROTECTED AREAS
# ============================================================
PROTECTED_AREAS: Final[tuple[ProtectedArea, ...]] = (
    ProtectedArea(
        name="on_btn main decision flow",
        reason="This is the current working interaction core of the HMI."
    ),
    ProtectedArea(
        name="update_control_loop",
        reason="This is the live control pipeline for joystick-to-action behavior."
    ),
    ProtectedArea(
        name="Right Joystick short press logic",
        reason="Engine sound / engine buzzer principle is tied to this behavior."
    ),
    ProtectedArea(
        name="FaultButton long press behavior",
        reason="Current fault screen opening method is already working and should remain stable."
    ),
    ProtectedArea(
        name="CoolingStatusIcon usage",
        reason="MC/RC are status indicators, not command buttons."
    ),
    ProtectedArea(
        name="shutdown_system",
        reason="Existing grouped safe-stop behavior must remain intact."
    ),
    ProtectedArea(
        name="KV layout structure",
        reason="Visual HMI structure is already aligned with the functional design."
    ),
    ProtectedArea(
        name="HardwareManager internal behavior",
        reason="Do not refactor hardware simulation/legacy layer during HMI integration stage."
    ),
)
# ============================================================
# FINAL PLAN
# ============================================================
FINAL_PATCH_PLAN: Final[PatchPlan] = PatchPlan(
    title="RemotePi HMI Final Minimal Integration Patch Plan",
    strategy=(
        "Use HYBRID integration mode. "
        "Preserve all current HMI behavior while mirroring and forwarding "
        "standardized events into the runtime stack."
    ),
    required_imports=REQUIRED_IMPORTS,
    build_stage_actions=BUILD_STAGE_ACTIONS,
    patch_points=PATCH_POINTS,
    protected_areas=PROTECTED_AREAS,
    recommended_profile="HYBRID_MIRROR_AND_FORWARD",
    summary=(
        "Do not rewrite the legacy HMI. "
        "Attach the hybrid integration manager, use the patch adapter at low-risk "
        "entry points, preserve joystick/fault/camera behavior, and let the "
        "runtime stack grow alongside the current HMI."
    ),
)


# ============================================================
# MODULE-R029
# ============================================================

# runtime/remotepi_runtime_wiring_stage2.py
"""
MODULE-R029
RemotePi Runtime Wiring Stage-2
-------------------------------

Purpose:
    Stage-2 runtime wiring layer for RemotePi.

Scope:
    Add second-stage runtime services on top of Stage-1 integration:
        - telemetry manager
        - local command executor
        - watchdog supervisor
        - safe shutdown manager

Design goals:
    - Preserve working legacy HMI behavior
    - Allow partial runtime activation without hard dependency on every adapter
    - Provide safe fallback implementations
    - Keep wiring explicit and inspectable
"""
import time
from dataclasses import dataclass
from typing import Any, Callable, Optional
from runtime.remotepi_telemetry_manager import RemotePiTelemetryManager
from runtime.remotepi_local_command_executor import RemotePiLocalCommandExecutor
from runtime.remotepi_watchdog_supervisor import (
    RemotePiWatchdogSupervisor,
    WatchdogDecision,
)
from runtime.remotepi_safe_shutdown_manager import (
    RemotePiSafeShutdownManager,
    ShutdownReason,
)
# ============================================================
# CONFIG
# ============================================================
@dataclass
class RuntimeWiringStage2Config:
    telemetry_period_sec: float = 0.25
    watchdog_period_sec: float = 0.50
    auto_apply_watchdog_actions: bool = True
    auto_shutdown_on_request: bool = True
    emit_status_logs: bool = True
# ============================================================
# MAIN CLASS
# ============================================================
class RemotePiRuntimeWiringStage2:
    """
    Stage-2 runtime composition helper.
    Expected Stage-1 objects:
        - state_store
        - event_router
        - mode_fsm
        - hmi_integration_manager
    This class wires:
        - telemetry manager
        - local command executor
        - watchdog supervisor
        - safe shutdown manager
    """
    def __init__(
        self,
        *,
        state_store,
        event_router=None,
        mode_fsm=None,
        hmi_integration_manager=None,
        logger=None,
        config: Optional[RuntimeWiringStage2Config] = None,
        status_sink: Optional[Callable[[str, dict], None]] = None,
    ):
        self.state_store = state_store
        self.event_router = event_router
        self.mode_fsm = mode_fsm
        self.hmi_integration_manager = hmi_integration_manager
        self.logger = logger
        self.config = config or RuntimeWiringStage2Config()
        self.status_sink = status_sink
        self.telemetry_manager: Optional[RemotePiTelemetryManager] = None
        self.local_command_executor: Optional[RemotePiLocalCommandExecutor] = None
        self.watchdog_supervisor: Optional[RemotePiWatchdogSupervisor] = None
        self.safe_shutdown_manager: Optional[RemotePiSafeShutdownManager] = None
        self._last_telemetry_ts = 0.0
        self._last_watchdog_ts = 0.0
        self._shutdown_started = False
    # --------------------------------------------------------
    # STATUS
    # --------------------------------------------------------
    def _emit_status(self, topic: str, **payload) -> None:
        if not self.config.emit_status_logs:
            return
        if self.status_sink is not None:
            self.status_sink(topic, {
                "ts": time.time(),
                **payload,
            })
    # --------------------------------------------------------
    # SAFE FALLBACK ADAPTERS
    # --------------------------------------------------------
    @staticmethod
    def _noop_output_writer(name: str, state: bool) -> None:
        _ = (name, state)
    @staticmethod
    def _noop_ui_fault_hook(payload: dict) -> None:
        _ = payload
    @staticmethod
    def _noop_platform_shutdown(payload: dict) -> None:
        _ = payload
    @staticmethod
    def _default_network_status_reader() -> dict:
        return {
            "network_online": True,
            "network_weak": False,
            "master_link_ok": True,
            "adc1_online": True,
            "adc2_online": True,
            "i2c_ok": True,
            "wifi_connected": True,
            "bluetooth_connected": False,
            "ethernet_link": False,
        }
    @staticmethod
    def _default_ui_health_reader() -> bool:
        return True
    @staticmethod
    def _default_system_active_reader() -> bool:
        return False
    @staticmethod
    def _default_adc_reader(channel_name: str) -> float:
        # Safe placeholder values
        defaults = {
            "BATTERY_VOLTAGE_SENSE": 2.2,
            "LM35_TEMP": 28.0,
            "NTC_BATTERY_TEMP": 29.0,
        }
        return float(defaults.get(channel_name, 0.0))
    @staticmethod
    def _default_gpio_writer(name: str, state: bool) -> None:
        _ = (name, state)
    # --------------------------------------------------------
    # STATE / LINK READERS
    # --------------------------------------------------------
    def _state_reader(self) -> dict:
        try:
            return self.state_store.to_dict()
        except Exception:
            return {}
    def _link_status_reader(self) -> dict:
        # If hmi integration manager exists, there may be no real link manager yet.
        # We still provide a sane shape for watchdog.
        return {
            "state": "UP",
            "connected": True,
            "master_link_ok": True,
            "last_rx_ts": time.time(),
            "last_tx_ts": time.time(),
            "reconnect_count": 0,
            "last_error": None,
        }
    # --------------------------------------------------------
    # OUTPUT STATE HOOK
    # --------------------------------------------------------
    def _state_store_output_hook(self, output_name: str, state: bool) -> None:
        try:
            if output_name == "FAN":
                self.state_store.set_fan_active(bool(state))
            elif output_name == "BUZZER":
                self.state_store.set_buzzer_active(bool(state))
        except Exception as exc:
            self._emit_status(
                "stage2/output_hook_error",
                output_name=output_name,
                error=str(exc),
            )
    # --------------------------------------------------------
    # EVENT / COMMAND SINKS
    # --------------------------------------------------------
    def _telemetry_event_sink(self, topic_or_event: str, payload: dict) -> None:
        # Mirror some health/telemetry data into state store when possible
        try:
            if topic_or_event == "remotepi/telemetry":
                batt = float(payload.get("battery_voltage", 0.0))
                batt_temp = float(payload.get("battery_temp_c", 0.0))
                local_temp = float(payload.get("local_temp_c", 0.0))
                fan_active = bool(payload.get("remote_fan_active", False))
                bucket = "STATE_BATTERY_NORMAL"
                if batt <= 10:
                    bucket = "STATE_BATTERY_SHUTDOWN"
                elif batt <= 20:
                    bucket = "STATE_BATTERY_CRITICAL"
                elif batt <= 40:
                    bucket = "STATE_BATTERY_WARNING"
                self.state_store.update_battery(
                    voltage=batt,
                    percent_est=batt,
                    bucket=bucket,
                )
                self.state_store.update_thermal(
                    local_temp_c=local_temp,
                    battery_temp_c=batt_temp,
                    thermal_state="STATE_TEMP_NORMAL",
                )
                self.state_store.set_fan_active(fan_active)
            elif topic_or_event == "remotepi/health":
                self.state_store.update_safety(
                    severity=str(payload.get("severity", "NORMAL")),
                    primary_state=str(payload.get("primary_state", "STATE_READY")),
                    accept_user_control=bool(payload.get("accept_user_control", True)),
                    allow_new_motion_commands=bool(payload.get("allow_new_motion_commands", True)),
                    request_shutdown=bool(payload.get("request_shutdown", False)),
                    ui_fault_latched=bool(payload.get("ui_fault_latched", False)),
                    summary=str(payload.get("summary", "")),
                    warnings=list(payload.get("warnings", [])),
                    faults=list(payload.get("faults", [])),
                    thermal_state=str(payload.get("thermal_state", "STATE_TEMP_NORMAL")),
                )
        except Exception as exc:
            self._emit_status(
                "stage2/telemetry_sink_error",
                topic_or_event=topic_or_event,
                error=str(exc),
            )
    def _notify_master_sink(self, command_name: str, payload: dict) -> None:
        # Stage-2 deliberately does not force transport/link.
        # If event_router exists, emit as observability only.
        self._emit_status(
            "stage2/notify_master",
            command_name=command_name,
            payload=payload,
        )
    # --------------------------------------------------------
    # BUILDERS
    # --------------------------------------------------------
    def build_local_command_executor(
        self,
        *,
        gpio_writer: Optional[Callable[[str, bool], None]] = None,
        ui_fault_hook: Optional[Callable[[dict], None]] = None,
    ) -> RemotePiLocalCommandExecutor:
        self.local_command_executor = RemotePiLocalCommandExecutor(
            gpio_writer=gpio_writer or self._noop_output_writer,
            ui_fault_hook=ui_fault_hook or self._noop_ui_fault_hook,
            state_store_hook=self._state_store_output_hook,
        )
        self._emit_status("stage2/local_executor_built")
        return self.local_command_executor
    def build_telemetry_manager(
        self,
        *,
        adc_reader: Optional[Callable[[str], float]] = None,
        output_writer: Optional[Callable[[str, bool], None]] = None,
        network_status_reader: Optional[Callable[[], dict]] = None,
        ui_health_reader: Optional[Callable[[], bool]] = None,
        system_active_reader: Optional[Callable[[], bool]] = None,
    ) -> RemotePiTelemetryManager:
        self.telemetry_manager = RemotePiTelemetryManager(
            adc_reader=adc_reader or self._default_adc_reader,
            output_writer=output_writer or self._default_gpio_writer,
            event_sink=self._telemetry_event_sink,
            network_status_reader=network_status_reader or self._default_network_status_reader,
            ui_health_reader=ui_health_reader or self._default_ui_health_reader,
            system_active_reader=system_active_reader or self._default_system_active_reader,
        )
        self._emit_status("stage2/telemetry_manager_built")
        return self.telemetry_manager
    def build_watchdog_supervisor(self) -> RemotePiWatchdogSupervisor:
        self.watchdog_supervisor = RemotePiWatchdogSupervisor(
            state_reader=self._state_reader,
            link_status_reader=self._link_status_reader,
            event_sink=lambda topic, payload: self._emit_status(
                "stage2/watchdog_event",
                watchdog_topic=topic,
                payload=payload,
            ),
        )
        self._emit_status("stage2/watchdog_built")
        return self.watchdog_supervisor
    def build_safe_shutdown_manager(
        self,
        *,
        link_manager=None,
        command_transport=None,
        platform_shutdown_hook: Optional[Callable[[dict], None]] = None,
    ) -> RemotePiSafeShutdownManager:
        self.safe_shutdown_manager = RemotePiSafeShutdownManager(
            state_store=self.state_store,
            local_command_executor=self.local_command_executor,
            link_manager=link_manager,
            command_transport=command_transport,
            logger=self.logger,
            notify_master_sink=self._notify_master_sink,
            platform_shutdown_hook=platform_shutdown_hook or self._noop_platform_shutdown,
        )
        self._emit_status("stage2/safe_shutdown_built")
        return self.safe_shutdown_manager
    # --------------------------------------------------------
    # ALL-IN-ONE BUILD
    # --------------------------------------------------------
    def build_all(
        self,
        *,
        adc_reader: Optional[Callable[[str], float]] = None,
        gpio_writer: Optional[Callable[[str, bool], None]] = None,
        ui_fault_hook: Optional[Callable[[dict], None]] = None,
        network_status_reader: Optional[Callable[[], dict]] = None,
        ui_health_reader: Optional[Callable[[], bool]] = None,
        system_active_reader: Optional[Callable[[], bool]] = None,
        link_manager=None,
        command_transport=None,
        platform_shutdown_hook: Optional[Callable[[dict], None]] = None,
    ) -> None:
        if self.local_command_executor is None:
            self.build_local_command_executor(
                gpio_writer=gpio_writer,
                ui_fault_hook=ui_fault_hook,
            )
        if self.telemetry_manager is None:
            self.build_telemetry_manager(
                adc_reader=adc_reader,
                output_writer=gpio_writer,
                network_status_reader=network_status_reader,
                ui_health_reader=ui_health_reader,
                system_active_reader=system_active_reader,
            )
        if self.watchdog_supervisor is None:
            self.build_watchdog_supervisor()
        if self.safe_shutdown_manager is None:
            self.build_safe_shutdown_manager(
                link_manager=link_manager,
                command_transport=command_transport,
                platform_shutdown_hook=platform_shutdown_hook,
            )
        self._emit_status("stage2/build_all_complete")
    # --------------------------------------------------------
    # WATCHDOG ACTIONS
    # --------------------------------------------------------
    def apply_watchdog_decision(self, decision: WatchdogDecision) -> None:
        self._emit_status(
            "stage2/watchdog_decision",
            severity=decision.severity.value,
            warnings=list(decision.warnings),
            faults=list(decision.faults),
            request_shutdown=decision.request_shutdown,
            summary=decision.summary,
        )
        if self.local_command_executor is not None:
            if decision.force_fault_view:
                self.local_command_executor.open_fault_view({
                    "source": "WATCHDOG",
                    "summary": decision.summary,
                    "faults": list(decision.faults),
                    "warnings": list(decision.warnings),
                })
            if decision.force_buzzer == "WARNING":
                self.local_command_executor.execute("CMD_BUZZER_WARNING", {})
            elif decision.force_buzzer == "FAULT":
                self.local_command_executor.execute("CMD_BUZZER_FAULT", {})
            elif decision.force_buzzer == "CRITICAL":
                self.local_command_executor.execute("CMD_BUZZER_CRITICAL", {})
        if (
            decision.request_shutdown
            and self.config.auto_shutdown_on_request
            and self.safe_shutdown_manager is not None
            and not self._shutdown_started
        ):
            self._shutdown_started = True
            req = self.safe_shutdown_manager.request_shutdown(
                reason=ShutdownReason.WATCHDOG_REQUEST,
                source="WATCHDOG_SUPERVISOR",
                detail={
                    "summary": decision.summary,
                    "faults": list(decision.faults),
                    "warnings": list(decision.warnings),
                },
            )
            result = self.safe_shutdown_manager.execute(req)
            self._emit_status(
                "stage2/shutdown_executed",
                ok=result.ok,
                stage=result.stage.value,
                summary=result.summary,
            )
    # --------------------------------------------------------
    # TICK
    # --------------------------------------------------------
    def tick(self) -> None:
        now = time.time()
        if self.telemetry_manager is not None:
            if (now - self._last_telemetry_ts) >= self.config.telemetry_period_sec:
                try:
                    self.telemetry_manager.tick()
                except Exception as exc:
                    self._emit_status("stage2/telemetry_tick_error", error=str(exc))
                self._last_telemetry_ts = now
        if self.watchdog_supervisor is not None:
            if (now - self._last_watchdog_ts) >= self.config.watchdog_period_sec:
                try:
                    decision = self.watchdog_supervisor.tick()
                    if self.config.auto_apply_watchdog_actions:
                        self.apply_watchdog_decision(decision)
                except Exception as exc:
                    self._emit_status("stage2/watchdog_tick_error", error=str(exc))
                self._last_watchdog_ts = now
    # --------------------------------------------------------
    # INSPECTION
    # --------------------------------------------------------
    def get_status_dict(self) -> dict:
        return {
            "telemetry_manager_ready": self.telemetry_manager is not None,
            "local_command_executor_ready": self.local_command_executor is not None,
            "watchdog_supervisor_ready": self.watchdog_supervisor is not None,
            "safe_shutdown_manager_ready": self.safe_shutdown_manager is not None,
            "last_telemetry_ts": self._last_telemetry_ts,
            "last_watchdog_ts": self._last_watchdog_ts,
            "shutdown_started": self._shutdown_started,
            "config": {
                "telemetry_period_sec": self.config.telemetry_period_sec,
                "watchdog_period_sec": self.config.watchdog_period_sec,
                "auto_apply_watchdog_actions": self.config.auto_apply_watchdog_actions,
                "auto_shutdown_on_request": self.config.auto_shutdown_on_request,
            },
        }


# ============================================================
# MODULE-R030
# ============================================================

# runtime/remotepi_state_store.py
"""
MODULE-R030
RemotePi State Store - Final Compatibility Revision
---------------------------------------------------

Purpose:
    Central runtime SSOT state container for RemotePi.

Responsibilities:
    - Hold live runtime state in one place
    - Track modes, warnings, faults, telemetry, health and outputs
    - Provide safe update methods
    - Provide compatibility helpers for FSM / service mode / stage2 wiring
    - Provide snapshot export for HMI / logger / transport

Design:
    Thread-safe mutable runtime state with compatibility helpers.
"""
import time
from dataclasses import asdict, dataclass, field
from threading import RLock
from typing import Any, Optional
# ============================================================
# DATA MODELS
# ============================================================
@dataclass
class ModeState:
    active_mode: str = "STATE_CONTROL_MODE_MENU"
    system_running: bool = False
    autonom_enabled: bool = False
@dataclass
class ThermalState:
    local_temp_c: float = 0.0
    battery_temp_c: float = 0.0
    thermal_state: str = "STATE_TEMP_NORMAL"
    fan_active: bool = False
@dataclass
class BatteryState:
    voltage: float = 0.0
    percent_est: float = 0.0
    bucket: str = "STATE_BATTERY_NORMAL"
@dataclass
class NetworkState:
    wifi_connected: bool = False
    bluetooth_connected: bool = False
    ethernet_link: bool = False
    master_link_ok: bool = False
    network_online: bool = False
    network_weak: bool = False
@dataclass
class InputState:
    left_x: float = 0.0
    left_y: float = 0.0
    right_x: float = 0.0
    right_y: float = 0.0
    left_button_pressed: bool = False
    right_button_pressed: bool = False
    last_input_ts: float = 0.0
@dataclass
class SafetyState:
    severity: str = "NORMAL"
    primary_state: str = "STATE_BOOTING"
    accept_user_control: bool = False
    allow_new_motion_commands: bool = False
    request_shutdown: bool = False
    ui_fault_latched: bool = False
    summary: str = ""
@dataclass
class OutputState:
    remote_fan_active: bool = False
    buzzer_active: bool = False
@dataclass
class RuntimeState:
    ts: float = field(default_factory=time.time)
    boot_ts: float = field(default_factory=time.time)
    mode: ModeState = field(default_factory=ModeState)
    thermal: ThermalState = field(default_factory=ThermalState)
    battery: BatteryState = field(default_factory=BatteryState)
    network: NetworkState = field(default_factory=NetworkState)
    inputs: InputState = field(default_factory=InputState)
    safety: SafetyState = field(default_factory=SafetyState)
    outputs: OutputState = field(default_factory=OutputState)
    warnings: list[str] = field(default_factory=list)
    faults: list[str] = field(default_factory=list)
    last_event: Optional[str] = None
    last_command: Optional[str] = None
    uptime_sec: float = 0.0
# ============================================================
# MAIN STORE
# ============================================================
class RemotePiStateStore:
    def __init__(self) -> None:
        self._lock = RLock()
        self._state = RuntimeState()
    # --------------------------------------------------------
    # INTERNAL
    # --------------------------------------------------------
    def _touch(self) -> None:
        self._state.ts = time.time()
        self._state.uptime_sec = self._state.ts - self._state.boot_ts
    # --------------------------------------------------------
    # MODE / SYSTEM
    # --------------------------------------------------------
    def set_active_mode(self, mode_name: str) -> None:
        with self._lock:
            self._state.mode.active_mode = str(mode_name)
            self._touch()
    def get_active_mode(self) -> str:
        with self._lock:
            return self._state.mode.active_mode
    def set_system_running(self, running: bool) -> None:
        with self._lock:
            self._state.mode.system_running = bool(running)
            self._touch()
    def is_system_running(self) -> bool:
        with self._lock:
            return bool(self._state.mode.system_running)
    def set_autonom_enabled(self, enabled: bool) -> None:
        with self._lock:
            self._state.mode.autonom_enabled = bool(enabled)
            self._touch()
    def is_autonom_enabled(self) -> bool:
        with self._lock:
            return bool(self._state.mode.autonom_enabled)
    # --------------------------------------------------------
    # INPUTS
    # --------------------------------------------------------
    def update_left_joystick(self, x: float, y: float) -> None:
        with self._lock:
            self._state.inputs.left_x = float(x)
            self._state.inputs.left_y = float(y)
            self._state.inputs.last_input_ts = time.time()
            self._touch()
    def update_right_joystick(self, x: float, y: float) -> None:
        with self._lock:
            self._state.inputs.right_x = float(x)
            self._state.inputs.right_y = float(y)
            self._state.inputs.last_input_ts = time.time()
            self._touch()
    def set_left_button(self, pressed: bool) -> None:
        with self._lock:
            self._state.inputs.left_button_pressed = bool(pressed)
            self._state.inputs.last_input_ts = time.time()
            self._touch()
    def set_right_button(self, pressed: bool) -> None:
        with self._lock:
            self._state.inputs.right_button_pressed = bool(pressed)
            self._state.inputs.last_input_ts = time.time()
            self._touch()
    # --------------------------------------------------------
    # BATTERY / THERMAL
    # --------------------------------------------------------
    def update_battery(self, voltage: float, percent_est: float, bucket: str) -> None:
        with self._lock:
            self._state.battery.voltage = float(voltage)
            self._state.battery.percent_est = float(percent_est)
            self._state.battery.bucket = str(bucket)
            self._touch()
    def update_thermal(self, local_temp_c: float, battery_temp_c: float, thermal_state: str) -> None:
        with self._lock:
            self._state.thermal.local_temp_c = float(local_temp_c)
            self._state.thermal.battery_temp_c = float(battery_temp_c)
            self._state.thermal.thermal_state = str(thermal_state)
            self._touch()
    # --------------------------------------------------------
    # NETWORK
    # --------------------------------------------------------
    def update_network(
        self,
        *,
        wifi_connected: bool,
        bluetooth_connected: bool,
        ethernet_link: bool,
        master_link_ok: bool,
        network_online: bool,
        network_weak: bool,
    ) -> None:
        with self._lock:
            self._state.network.wifi_connected = bool(wifi_connected)
            self._state.network.bluetooth_connected = bool(bluetooth_connected)
            self._state.network.ethernet_link = bool(ethernet_link)
            self._state.network.master_link_ok = bool(master_link_ok)
            self._state.network.network_online = bool(network_online)
            self._state.network.network_weak = bool(network_weak)
            self._touch()
    # --------------------------------------------------------
    # OUTPUTS
    # --------------------------------------------------------
    def set_fan_active(self, active: bool) -> None:
        with self._lock:
            self._state.outputs.remote_fan_active = bool(active)
            self._state.thermal.fan_active = bool(active)
            self._touch()
    def is_fan_active(self) -> bool:
        with self._lock:
            return bool(self._state.outputs.remote_fan_active)
    def set_buzzer_active(self, active: bool) -> None:
        with self._lock:
            self._state.outputs.buzzer_active = bool(active)
            self._touch()
    def is_buzzer_active(self) -> bool:
        with self._lock:
            return bool(self._state.outputs.buzzer_active)
    # --------------------------------------------------------
    # SAFETY
    # --------------------------------------------------------
    def update_safety(
        self,
        *,
        severity: str,
        primary_state: str,
        accept_user_control: bool,
        allow_new_motion_commands: bool,
        request_shutdown: bool,
        ui_fault_latched: bool,
        summary: str,
        warnings: list[str],
        faults: list[str],
        thermal_state: Optional[str] = None,
    ) -> None:
        with self._lock:
            self._state.safety.severity = str(severity)
            self._state.safety.primary_state = str(primary_state)
            self._state.safety.accept_user_control = bool(accept_user_control)
            self._state.safety.allow_new_motion_commands = bool(allow_new_motion_commands)
            self._state.safety.request_shutdown = bool(request_shutdown)
            self._state.safety.ui_fault_latched = bool(ui_fault_latched)
            self._state.safety.summary = str(summary)
            self._state.warnings = list(warnings)
            self._state.faults = list(faults)
            if thermal_state is not None:
                self._state.thermal.thermal_state = str(thermal_state)
            self._touch()
    def set_motion_allowed(self, allowed: bool) -> None:
        with self._lock:
            self._state.safety.allow_new_motion_commands = bool(allowed)
            self._touch()
    def is_motion_allowed(self) -> bool:
        with self._lock:
            return bool(self._state.safety.allow_new_motion_commands)
    def accept_user_control(self) -> bool:
        with self._lock:
            return bool(self._state.safety.accept_user_control)
    def is_safe_to_run(self) -> bool:
        with self._lock:
            sev = str(self._state.safety.severity)
            if sev in ("FAULT", "CRITICAL", "SHUTDOWN"):
                return False
            if bool(self._state.safety.request_shutdown):
                return False
            return True
    def get_safety(self) -> dict:
        with self._lock:
            return {
                "severity": self._state.safety.severity,
                "primary_state": self._state.safety.primary_state,
                "accept_user_control": self._state.safety.accept_user_control,
                "allow_new_motion_commands": self._state.safety.allow_new_motion_commands,
                "request_shutdown": self._state.safety.request_shutdown,
                "ui_fault_latched": self._state.safety.ui_fault_latched,
                "summary": self._state.safety.summary,
            }
    # --------------------------------------------------------
    # TRACE
    # --------------------------------------------------------
    def set_last_event(self, event_name: str) -> None:
        with self._lock:
            self._state.last_event = str(event_name)
            self._touch()
    def set_last_command(self, command_name: str) -> None:
        with self._lock:
            self._state.last_command = str(command_name)
            self._touch()
    # --------------------------------------------------------
    # QUICK READS
    # --------------------------------------------------------
    def has_faults(self) -> bool:
        with self._lock:
            return len(self._state.faults) > 0
    def get_faults(self) -> list[str]:
        with self._lock:
            return list(self._state.faults)
    def get_warnings(self) -> list[str]:
        with self._lock:
            return list(self._state.warnings)
    def get_last_event(self) -> Optional[str]:
        with self._lock:
            return self._state.last_event
    def get_last_command(self) -> Optional[str]:
        with self._lock:
            return self._state.last_command
    # --------------------------------------------------------
    # RESET / CLEAR
    # --------------------------------------------------------
    def clear_fault_latch(self) -> None:
        with self._lock:
            self._state.safety.ui_fault_latched = False
            self._touch()
    def clear_warnings(self) -> None:
        with self._lock:
            self._state.warnings.clear()
            self._touch()
    def clear_faults(self) -> None:
        with self._lock:
            self._state.faults.clear()
            self._touch()
    def reset_runtime_inputs(self) -> None:
        with self._lock:
            self._state.inputs = InputState()
            self._touch()
    # --------------------------------------------------------
    # SNAPSHOT / EXPORT
    # --------------------------------------------------------
    def snapshot(self) -> RuntimeState:
        with self._lock:
            state_dict = asdict(self._state)
            return RuntimeState(
                ts=state_dict["ts"],
                boot_ts=state_dict["boot_ts"],
                mode=ModeState(**state_dict["mode"]),
                thermal=ThermalState(**state_dict["thermal"]),
                battery=BatteryState(**state_dict["battery"]),
                network=NetworkState(**state_dict["network"]),
                inputs=InputState(**state_dict["inputs"]),
                safety=SafetyState(**state_dict["safety"]),
                outputs=OutputState(**state_dict["outputs"]),
                warnings=list(state_dict["warnings"]),
                faults=list(state_dict["faults"]),
                last_event=state_dict["last_event"],
                last_command=state_dict["last_command"],
                uptime_sec=state_dict["uptime_sec"],
            )
    def to_dict(self) -> dict[str, Any]:
        with self._lock:
            self._touch()
            return asdict(self._state)


# ============================================================
# MODULE-R031
# ============================================================

# runtime/remotepi_mode_fsm.py
"""
MODULE-R031
RemotePi Mode FSM - Final Compatibility Revision
------------------------------------------------

Purpose:
    High-level operational mode state machine for RemotePi.

Responsibilities:
    - Manage active control mode
    - Enforce motion permission rules
    - Integrate safety/watchdog/shutdown transitions
    - Provide deterministic mode transitions
    - Mirror FSM state into RemotePiStateStore

Compatible with:
    - RemotePiStateStore final compatibility revision
    - Hybrid HMI integration flow
"""
import time
from enum import Enum
from dataclasses import dataclass
# ============================================================
# ENUMS
# ============================================================
class RemoteMode(str, Enum):
    BOOT = "BOOT"
    CONTROL_MENU = "CONTROL_MENU"
    MANUAL_CONTROL = "MANUAL_CONTROL"
    SERVICE_MODE = "SERVICE_MODE"
    FAULT_LOCK = "FAULT_LOCK"
    SAFE_SHUTDOWN = "SAFE_SHUTDOWN"
# ============================================================
# DATA MODEL
# ============================================================
@dataclass
class ModeSnapshot:
    ts: float
    mode: RemoteMode
    system_running: bool
    motion_allowed: bool
    user_control_allowed: bool
# ============================================================
# MAIN FSM
# ============================================================
class RemotePiModeFSM:
    def __init__(self, state_store):
        self.state_store = state_store
        self._mode = RemoteMode.BOOT
        self._last_transition_ts = time.time()
        self._apply_permissions()
    # --------------------------------------------------------
    @property
    def mode(self) -> RemoteMode:
        return self._mode
    @property
    def last_transition_ts(self) -> float:
        return self._last_transition_ts
    # --------------------------------------------------------
    # INTERNAL
    # --------------------------------------------------------
    def _set_mode(self, mode: RemoteMode) -> None:
        self._mode = mode
        self._last_transition_ts = time.time()
        self._apply_permissions()
    def _apply_permissions(self) -> None:
        """
        Sync permissions and visible mode into state store.
        """
        if self._mode == RemoteMode.BOOT:
            self.state_store.set_active_mode("BOOT")
            self.state_store.set_system_running(False)
            self.state_store.set_motion_allowed(False)
        elif self._mode == RemoteMode.CONTROL_MENU:
            self.state_store.set_active_mode("CONTROL_MENU")
            self.state_store.set_system_running(False)
            self.state_store.set_motion_allowed(False)
        elif self._mode == RemoteMode.MANUAL_CONTROL:
            self.state_store.set_active_mode("MANUAL_CONTROL")
            self.state_store.set_system_running(True)
            self.state_store.set_motion_allowed(True)
        elif self._mode == RemoteMode.SERVICE_MODE:
            self.state_store.set_active_mode("SERVICE_MODE")
            self.state_store.set_system_running(False)
            self.state_store.set_motion_allowed(False)
        elif self._mode == RemoteMode.FAULT_LOCK:
            self.state_store.set_active_mode("FAULT_LOCK")
            self.state_store.set_system_running(False)
            self.state_store.set_motion_allowed(False)
        elif self._mode == RemoteMode.SAFE_SHUTDOWN:
            self.state_store.set_active_mode("SAFE_SHUTDOWN")
            self.state_store.set_system_running(False)
            self.state_store.set_motion_allowed(False)
    # --------------------------------------------------------
    # EXPLICIT TRANSITIONS
    # --------------------------------------------------------
    def to_boot(self) -> None:
        self._set_mode(RemoteMode.BOOT)
    def to_control_menu(self) -> None:
        self._set_mode(RemoteMode.CONTROL_MENU)
    def to_manual(self) -> bool:
        if not self.state_store.is_safe_to_run():
            return False
        self._set_mode(RemoteMode.MANUAL_CONTROL)
        return True
    def to_service(self) -> None:
        self._set_mode(RemoteMode.SERVICE_MODE)
    def to_fault_lock(self) -> None:
        self._set_mode(RemoteMode.FAULT_LOCK)
    def to_shutdown(self) -> None:
        self._set_mode(RemoteMode.SAFE_SHUTDOWN)
    # --------------------------------------------------------
    # SAFETY / WATCHDOG OVERRIDE
    # --------------------------------------------------------
    def safety_override(self) -> None:
        safety = self.state_store.get_safety()
        sev = str(safety.get("severity", "NORMAL"))
        request_shutdown = bool(safety.get("request_shutdown", False))
        if request_shutdown or sev == "SHUTDOWN":
            self.to_shutdown()
            return
        if sev in ("FAULT", "CRITICAL"):
            self.to_fault_lock()
            return
        if self._mode == RemoteMode.BOOT:
            # Normal healthy boot exit path
            self.to_control_menu()
    # --------------------------------------------------------
    # CONDITIONAL ENTRY HELPERS
    # --------------------------------------------------------
    def enter_manual_if_allowed(self) -> bool:
        return self.to_manual()
    def enter_service_if_stopped(self) -> bool:
        if self.state_store.is_system_running():
            return False
        self.to_service()
        return True
    def return_to_menu(self) -> None:
        self.to_control_menu()
    # --------------------------------------------------------
    # SNAPSHOT
    # --------------------------------------------------------
    def snapshot(self) -> ModeSnapshot:
        return ModeSnapshot(
            ts=time.time(),
            mode=self._mode,
            system_running=self.state_store.is_system_running(),
            motion_allowed=self.state_store.is_motion_allowed(),
            user_control_allowed=self.state_store.accept_user_control(),
        )
    def to_dict(self) -> dict:
        snap = self.snapshot()
        return {
            "ts": snap.ts,
            "mode": snap.mode.value,
            "system_running": snap.system_running,
            "motion_allowed": snap.motion_allowed,
            "user_control_allowed": snap.user_control_allowed,
            "last_transition_ts": self._last_transition_ts,
        }


# ============================================================
# MODULE-R032
# ============================================================

# runtime/remotepi_event_router.py
"""
MODULE-R032
RemotePi Event Router - Final Compatibility Revision
----------------------------------------------------

Purpose:
    Central event routing layer for RemotePi runtime.

Responsibilities:
    - Accept UI events and joystick events
    - Convert them into normalized command events
    - Respect current safety policy
    - Respect current active control mode
    - Gate motion commands when faults/critical states are active
    - Mirror selected routing state into state store when available

Compatible with:
    - RemotePiStateStore final compatibility revision
    - RemotePiModeFSM final compatibility revision
    - Hybrid HMI integration flow
"""
import time
from dataclasses import dataclass, field
from typing import Callable, Final, Optional
from hardware.remotepi_fault_policy import FaultPolicyDecision, Severity
from hardware.remotepi_signal_names import (
    CMD_BUZZER_BUTTON_ACK,
    CMD_FAULT_ACK,
    CMD_FAULT_VIEW_OPEN,
    CMD_JOYSTICK_LEFT_UPDATE,
    CMD_JOYSTICK_RIGHT_UPDATE,
    CMD_LIGHT_HIGH_BEAM_TOGGLE,
    CMD_LIGHT_LOW_BEAM_TOGGLE,
    CMD_LIGHT_PARKING_TOGGLE,
    CMD_LIGHT_RIG_FLOOR_TOGGLE,
    CMD_LIGHT_ROTATION_TOGGLE,
    CMD_LIGHT_SIGNAL_LHR_TOGGLE,
    CMD_MODE_AUTONOM,
    CMD_MODE_DRIVER,
    CMD_MODE_DRAWWORKS,
    CMD_MODE_MENU,
    CMD_MODE_ROTARY_TABLE,
    CMD_MODE_SANDLINE,
    CMD_MODE_WHEEL,
    CMD_MODE_WINCH,
    CMD_SYSTEM_START,
    CMD_SYSTEM_STOP,
    EVENT_LEFT_JOYSTICK_BUTTON_LONG,
    EVENT_LEFT_JOYSTICK_BUTTON_SHORT,
    EVENT_LEFT_JOYSTICK_MOVE,
    EVENT_RIGHT_JOYSTICK_BUTTON_LONG,
    EVENT_RIGHT_JOYSTICK_BUTTON_SHORT,
    EVENT_RIGHT_JOYSTICK_MOVE,
    EVENT_UI_AUTONOM,
    EVENT_UI_DRIVER,
    EVENT_UI_DRAWWORKS,
    EVENT_UI_FAULT,
    EVENT_UI_HIGH_BEAM_LIGHT,
    EVENT_UI_LOW_BEAM_LIGHT,
    EVENT_UI_MENU,
    EVENT_UI_PARKING_LIGHT,
    EVENT_UI_RIG_FLOOR_LIGHT,
    EVENT_UI_ROTARY_TABLE,
    EVENT_UI_SANDLINE,
    EVENT_UI_SIGNAL_LHR_LIGHT,
    EVENT_UI_START_STOP,
    EVENT_UI_WHEEL,
    EVENT_UI_WINCH,
    STATE_CONTROL_MODE_AUTONOM,
    STATE_CONTROL_MODE_DRIVER,
    STATE_CONTROL_MODE_DRAWWORKS,
    STATE_CONTROL_MODE_MENU,
    STATE_CONTROL_MODE_ROTARY_TABLE,
    STATE_CONTROL_MODE_SANDLINE,
    STATE_CONTROL_MODE_WHEEL,
    STATE_CONTROL_MODE_WINCH,
    TOPIC_COMMANDS,
    TOPIC_EVENTS,
)
# ============================================================
# CONSTANT TABLES
# ============================================================
UI_MODE_EVENT_TO_STATE: Final[dict[str, str]] = {
    EVENT_UI_WHEEL: STATE_CONTROL_MODE_WHEEL,
    EVENT_UI_DRIVER: STATE_CONTROL_MODE_DRIVER,
    EVENT_UI_DRAWWORKS: STATE_CONTROL_MODE_DRAWWORKS,
    EVENT_UI_SANDLINE: STATE_CONTROL_MODE_SANDLINE,
    EVENT_UI_WINCH: STATE_CONTROL_MODE_WINCH,
    EVENT_UI_ROTARY_TABLE: STATE_CONTROL_MODE_ROTARY_TABLE,
    EVENT_UI_AUTONOM: STATE_CONTROL_MODE_AUTONOM,
    EVENT_UI_MENU: STATE_CONTROL_MODE_MENU,
}
UI_MODE_EVENT_TO_COMMAND: Final[dict[str, str]] = {
    EVENT_UI_WHEEL: CMD_MODE_WHEEL,
    EVENT_UI_DRIVER: CMD_MODE_DRIVER,
    EVENT_UI_DRAWWORKS: CMD_MODE_DRAWWORKS,
    EVENT_UI_SANDLINE: CMD_MODE_SANDLINE,
    EVENT_UI_WINCH: CMD_MODE_WINCH,
    EVENT_UI_ROTARY_TABLE: CMD_MODE_ROTARY_TABLE,
    EVENT_UI_AUTONOM: CMD_MODE_AUTONOM,
    EVENT_UI_MENU: CMD_MODE_MENU,
}
UI_ACTION_EVENT_TO_COMMAND: Final[dict[str, str]] = {
    EVENT_UI_PARKING_LIGHT: CMD_LIGHT_PARKING_TOGGLE,
    EVENT_UI_LOW_BEAM_LIGHT: CMD_LIGHT_LOW_BEAM_TOGGLE,
    EVENT_UI_HIGH_BEAM_LIGHT: CMD_LIGHT_HIGH_BEAM_TOGGLE,
    EVENT_UI_SIGNAL_LHR_LIGHT: CMD_LIGHT_SIGNAL_LHR_TOGGLE,
    EVENT_UI_RIG_FLOOR_LIGHT: CMD_LIGHT_RIG_FLOOR_TOGGLE,
    EVENT_UI_ROTATION_LIGHT: CMD_LIGHT_ROTATION_TOGGLE,
}
MOTION_ENABLED_MODES: Final[set[str]] = {
    STATE_CONTROL_MODE_WHEEL,
    STATE_CONTROL_MODE_DRIVER,
    STATE_CONTROL_MODE_DRAWWORKS,
    STATE_CONTROL_MODE_SANDLINE,
    STATE_CONTROL_MODE_WINCH,
    STATE_CONTROL_MODE_ROTARY_TABLE,
    "MANUAL_CONTROL",   # FSM top-level compatible
}
NON_MOTION_MODES: Final[set[str]] = {
    STATE_CONTROL_MODE_AUTONOM,
    STATE_CONTROL_MODE_MENU,
    "BOOT",
    "CONTROL_MENU",
    "SERVICE_MODE",
    "FAULT_LOCK",
    "SAFE_SHUTDOWN",
}
# ============================================================
# DATA MODELS
# ============================================================
@dataclass
class RouterState:
    active_mode: str = STATE_CONTROL_MODE_MENU
    system_running: bool = False
    last_fault_policy: Optional[FaultPolicyDecision] = None
    last_event_ts: float = field(default_factory=time.time)
# ============================================================
# MAIN CLASS
# ============================================================
class RemotePiEventRouter:
    def __init__(
        self,
        command_sink: Callable[[str, dict], None],
        event_sink: Callable[[str, dict], None],
        state_store=None,
        mode_fsm=None,
    ):
        """
        command_sink(command_name, payload)
            Used for normalized command output toward upper layers / transport.
        event_sink(topic_or_event_name, payload)
            Used for internal observability/logging.
        state_store:
            Optional RemotePiStateStore-compatible object.
        mode_fsm:
            Optional RemotePiModeFSM-compatible object.
        """
        self.command_sink = command_sink
        self.event_sink = event_sink
        self.state_store = state_store
        self.mode_fsm = mode_fsm
        self.state = RouterState()
    # --------------------------------------------------------
    # INTERNAL HELPERS
    # --------------------------------------------------------
    def _sync_state_store_mode(self, mode_name: str) -> None:
        if self.state_store is not None and hasattr(self.state_store, "set_active_mode"):
            self.state_store.set_active_mode(mode_name)
    def _sync_state_store_running(self, running: bool) -> None:
        if self.state_store is not None and hasattr(self.state_store, "set_system_running"):
            self.state_store.set_system_running(running)
    def _sync_trace(self, event_name: Optional[str] = None, command_name: Optional[str] = None) -> None:
        if self.state_store is None:
            return
        if event_name and hasattr(self.state_store, "set_last_event"):
            self.state_store.set_last_event(event_name)
        if command_name and hasattr(self.state_store, "set_last_command"):
            self.state_store.set_last_command(command_name)
    def _effective_mode(self) -> str:
        if self.state_store is not None and hasattr(self.state_store, "get_active_mode"):
            try:
                return str(self.state_store.get_active_mode())
            except Exception:
                pass
        return self.state.active_mode
    def _effective_running(self) -> bool:
        if self.state_store is not None and hasattr(self.state_store, "is_system_running"):
            try:
                return bool(self.state_store.is_system_running())
            except Exception:
                pass
        return self.state.system_running
    # --------------------------------------------------------
    def update_fault_policy(self, decision: FaultPolicyDecision) -> None:
        self.state.last_fault_policy = decision
        self.event_sink(TOPIC_EVENTS, {
            "ts": time.time(),
            "type": "FAULT_POLICY_UPDATE",
            "severity": decision.severity.value,
            "primary_state": decision.primary_state,
            "allow_new_motion_commands": decision.allow_new_motion_commands,
            "accept_user_control": decision.accept_user_control,
        })
    # --------------------------------------------------------
    def _policy(self) -> FaultPolicyDecision:
        if self.state.last_fault_policy is None:
            return FaultPolicyDecision(
                severity=Severity.WARNING,
                primary_state="STATE_WARNING",
                thermal_state="STATE_TEMP_WARNING",
                warnings=["BOOTSTRAP_POLICY_MISSING"],
                faults=[],
                force_fan_on=False,
                request_shutdown=False,
                buzzer_class="WARNING",  # type: ignore[arg-type]
                ui_fault_latched=False,
                accept_user_control=True,
                allow_new_motion_commands=False,
                summary="No fault policy available yet; motion locked by default.",
            )
        return self.state.last_fault_policy
    # --------------------------------------------------------
    def _emit_command(self, command: str, payload: Optional[dict] = None) -> None:
        payload = payload or {}
        payload.setdefault("ts", time.time())
        payload.setdefault("mode", self._effective_mode())
        self.command_sink(command, payload)
        self._sync_trace(command_name=command)
        self.event_sink(TOPIC_COMMANDS, {
            "command": command,
            **payload,
        })
    # --------------------------------------------------------
    def _ack_button(self) -> None:
        self._emit_command(CMD_BUZZER_BUTTON_ACK, {})
    # --------------------------------------------------------
    def _set_mode_from_ui_event(self, event_name: str) -> None:
        next_state = UI_MODE_EVENT_TO_STATE[event_name]
        next_command = UI_MODE_EVENT_TO_COMMAND[event_name]
        # Router internal state
        self.state.active_mode = next_state
        # State store sync
        self._sync_state_store_mode(next_state)
        # FSM sync
        if self.mode_fsm is not None:
            if event_name == EVENT_UI_MENU and hasattr(self.mode_fsm, "to_control_menu"):
                self.mode_fsm.to_control_menu()
            elif event_name == EVENT_UI_AUTONOM and hasattr(self.mode_fsm, "to_control_menu"):
                self.mode_fsm.to_control_menu()
            elif event_name in (
                EVENT_UI_WHEEL,
                EVENT_UI_DRIVER,
                EVENT_UI_DRAWWORKS,
                EVENT_UI_SANDLINE,
                EVENT_UI_WINCH,
                EVENT_UI_ROTARY_TABLE,
            ):
                if hasattr(self.mode_fsm, "to_manual"):
                    self.mode_fsm.to_manual()
        self._emit_command(next_command, {"selected_mode": next_state})
    # --------------------------------------------------------
    def _handle_start_stop(self) -> None:
        policy = self._policy()
        currently_running = self._effective_running()
        if currently_running:
            self.state.system_running = False
            self._sync_state_store_running(False)
            self._emit_command(CMD_SYSTEM_STOP, {"reason": "UI_START_STOP"})
            return
        if policy.accept_user_control and not policy.request_shutdown:
            self.state.system_running = True
            self._sync_state_store_running(True)
            self._emit_command(CMD_SYSTEM_START, {"reason": "UI_START_STOP"})
        else:
            self.event_sink(TOPIC_EVENTS, {
                "ts": time.time(),
                "type": "START_BLOCKED_BY_POLICY",
                "severity": policy.severity.value,
                "summary": policy.summary,
            })
    # --------------------------------------------------------
    def _handle_fault_button(self, payload: dict) -> None:
        policy = self._policy()
        press_type = str(payload.get("press_type", "short")).lower()
        if press_type == "long":
            self._emit_command(CMD_FAULT_VIEW_OPEN, {
                "faults": list(policy.faults),
                "warnings": list(policy.warnings),
                "reason": "FAULT_LONG_PRESS",
            })
            return
        if policy.ui_fault_latched or policy.faults:
            self._emit_command(CMD_FAULT_VIEW_OPEN, {
                "faults": list(policy.faults),
                "warnings": list(policy.warnings),
            })
        else:
            self._emit_command(CMD_FAULT_ACK, {"reason": "UI_FAULT_TAP_NO_ACTIVE_FAULT"})
    # --------------------------------------------------------
    def _handle_ui_event(self, event_name: str, payload: dict) -> None:
        self.state.last_event_ts = time.time()
        self._sync_trace(event_name=event_name)
        if event_name in UI_MODE_EVENT_TO_STATE:
            self._set_mode_from_ui_event(event_name)
            self._ack_button()
            return
        if event_name == EVENT_UI_START_STOP:
            self._handle_start_stop()
            self._ack_button()
            return
        if event_name == EVENT_UI_FAULT:
            self._handle_fault_button(payload)
            self._ack_button()
            return
        if event_name in UI_ACTION_EVENT_TO_COMMAND:
            self._emit_command(UI_ACTION_EVENT_TO_COMMAND[event_name], payload)
            self._ack_button()
            return
        self.event_sink(TOPIC_EVENTS, {
            "ts": time.time(),
            "type": "UNHANDLED_UI_EVENT",
            "event": event_name,
            "payload": payload,
        })
    # --------------------------------------------------------
    def _motion_allowed(self) -> bool:
        policy = self._policy()
        if self.state_store is not None and hasattr(self.state_store, "is_motion_allowed"):
            try:
                return bool(self.state_store.is_motion_allowed()) and self._effective_running()
            except Exception:
                pass
        return policy.allow_new_motion_commands and self._effective_running()
    # --------------------------------------------------------
    def _build_motion_payload(self, side: str, payload: dict) -> dict:
        x = float(payload.get("x", 0.0))
        y = float(payload.get("y", 0.0))
        return {
            "side": side,
            "mode": self._effective_mode(),
            "x": x,
            "y": y,
            "magnitude": (x * x + y * y) ** 0.5,
            "ts": payload.get("ts", time.time()),
        }
    # --------------------------------------------------------
    def _handle_left_joystick_move(self, payload: dict) -> None:
        current_mode = self._effective_mode()
        if current_mode not in MOTION_ENABLED_MODES:
            self.event_sink(TOPIC_EVENTS, {
                "ts": time.time(),
                "type": "LEFT_JOYSTICK_IGNORED_MODE",
                "mode": current_mode,
                "payload": payload,
            })
            return
        if not self._motion_allowed():
            self.event_sink(TOPIC_EVENTS, {
                "ts": time.time(),
                "type": "LEFT_JOYSTICK_BLOCKED_POLICY",
                "mode": current_mode,
                "payload": payload,
            })
            return
        self._emit_command(CMD_JOYSTICK_LEFT_UPDATE, self._build_motion_payload("LEFT", payload))
    # --------------------------------------------------------
    def _handle_right_joystick_move(self, payload: dict) -> None:
        current_mode = self._effective_mode()
        if current_mode not in MOTION_ENABLED_MODES:
            self.event_sink(TOPIC_EVENTS, {
                "ts": time.time(),
                "type": "RIGHT_JOYSTICK_IGNORED_MODE",
                "mode": current_mode,
                "payload": payload,
            })
            return
        if not self._motion_allowed():
            self.event_sink(TOPIC_EVENTS, {
                "ts": time.time(),
                "type": "RIGHT_JOYSTICK_BLOCKED_POLICY",
                "mode": current_mode,
                "payload": payload,
            })
            return
        self._emit_command(CMD_JOYSTICK_RIGHT_UPDATE, self._build_motion_payload("RIGHT", payload))
    # --------------------------------------------------------
    def _handle_joystick_button(self, side: str, event_name: str, payload: dict) -> None:
        self._sync_trace(event_name=event_name)
        self.event_sink(TOPIC_EVENTS, {
            "ts": time.time(),
            "type": "JOYSTICK_BUTTON",
            "side": side,
            "event": event_name,
            "mode": self._effective_mode(),
            "payload": payload,
        })
        if event_name in (EVENT_LEFT_JOYSTICK_BUTTON_SHORT, EVENT_RIGHT_JOYSTICK_BUTTON_SHORT):
            self._ack_button()
            return
        if event_name in (EVENT_LEFT_JOYSTICK_BUTTON_LONG, EVENT_RIGHT_JOYSTICK_BUTTON_LONG):
            self._emit_command(CMD_FAULT_VIEW_OPEN, {
                "reason": "JOYSTICK_LONG_PRESS",
                "side": side,
            })
            return
    # --------------------------------------------------------
    def route_event(self, event_name: str, payload: Optional[dict] = None) -> None:
        payload = payload or {}
        self.state.last_event_ts = time.time()
        self._sync_trace(event_name=event_name)
        if event_name.startswith("EVENT_UI_"):
            self._handle_ui_event(event_name, payload)
            return
        if event_name == EVENT_LEFT_JOYSTICK_MOVE:
            self._handle_left_joystick_move(payload)
            return
        if event_name == EVENT_RIGHT_JOYSTICK_MOVE:
            self._handle_right_joystick_move(payload)
            return
        if event_name in (EVENT_LEFT_JOYSTICK_BUTTON_SHORT, EVENT_LEFT_JOYSTICK_BUTTON_LONG):
            self._handle_joystick_button("LEFT", event_name, payload)
            return
        if event_name in (EVENT_RIGHT_JOYSTICK_BUTTON_SHORT, EVENT_RIGHT_JOYSTICK_BUTTON_LONG):
            self._handle_joystick_button("RIGHT", event_name, payload)
            return
        self.event_sink(TOPIC_EVENTS, {
            "ts": time.time(),
            "type": "UNROUTED_EVENT",
            "event": event_name,
            "payload": payload,
            "mode": self._effective_mode(),
        })


# ============================================================
# MODULE-R033
# ============================================================

# runtime/remotepi_hybrid_integration_manager.py
"""
MODULE-R033
RemotePi Hybrid Integration Manager - Final Compatibility Revision
------------------------------------------------------------------

Purpose:
    Runtime coordination layer for staged coexistence between the existing
    legacy Kivy HMI and the newer RemotePi runtime stack.

Responsibilities:
    - Own the integration profile
    - Wire mapper and runtime bridge
    - Apply per-event integration policy
    - Preserve legacy HMI behavior while forwarding standardized events
    - Support passive / hybrid / active staged migration
    - Mirror HMI state into runtime state store in a controlled way

Compatible with:
    - RemotePiStateStore final compatibility revision
    - RemotePiModeFSM final compatibility revision
    - RemotePiEventRouter final compatibility revision
    - HMI patch adapter / stage2 runtime wiring
"""
import time
from dataclasses import dataclass
from typing import Any, Optional, Callable
from runtime.remotepi_hmi_event_mapper import RemotePiHMIEventMapper
from runtime.remotepi_hmi_runtime_bridge import (
    RemotePiHMIRuntimeBridge,
    HMIRuntimeBridgeConfig,
)
from runtime.remotepi_integration_profile import (
    IntegrationProfile,
    DEFAULT_INTEGRATION_PROFILE,
    get_event_policy,
)
# ============================================================
# DATA MODELS
# ============================================================
@dataclass
class HybridIntegrationStatus:
    ts: float
    profile_name: str
    bridge_mode: str
    mapper_bound: bool
    bridge_ready: bool
    last_event_name: Optional[str]
    last_snapshot_ts: float
# ============================================================
# MAIN CLASS
# ============================================================
class RemotePiHybridIntegrationManager:
    def __init__(
        self,
        *,
        profile: IntegrationProfile = DEFAULT_INTEGRATION_PROFILE,
        mode_fsm=None,
        event_router=None,
        state_store=None,
        status_sink: Optional[Callable[[str, dict], None]] = None,
    ):
        self.profile = profile
        self.mode_fsm = mode_fsm
        self.event_router = event_router
        self.state_store = state_store
        self.status_sink = status_sink
        self.mapper: Optional[RemotePiHMIEventMapper] = None
        self.bridge: Optional[RemotePiHMIRuntimeBridge] = None
        self._last_event_name: Optional[str] = None
        self._last_snapshot_ts: float = 0.0
    # --------------------------------------------------------
    # INTERNAL
    # --------------------------------------------------------
    def _emit_status(self, topic: str, **payload) -> None:
        if self.status_sink is not None:
            self.status_sink(topic, {
                "ts": time.time(),
                **payload,
            })
    def _mirror_policy_trace(self, event_name: str, policy) -> None:
        if self.state_store is None:
            return
        try:
            if hasattr(self.state_store, "set_last_event"):
                self.state_store.set_last_event(event_name)
        except Exception:
            pass
    # --------------------------------------------------------
    # BUILD / WIRING
    # --------------------------------------------------------
    def build(self) -> None:
        bridge_cfg = HMIRuntimeBridgeConfig(
            mode=self.profile.bridge_mode,
            mirror_hmi_state=True,
            forward_events_to_router=True,
            drive_fsm_from_hmi=True,
            emit_status_logs=True,
        )
        self.bridge = RemotePiHMIRuntimeBridge(
            mode_fsm=self.mode_fsm,
            event_router=self.event_router,
            state_store=self.state_store,
            status_sink=self.status_sink,
            config=bridge_cfg,
        )
        self.mapper = RemotePiHMIEventMapper(
            event_sink=self.handle_hmi_event,
            status_sink=self.status_sink,
        )
        self._emit_status(
            "integration_manager/built",
            profile_name=self.profile.name,
            bridge_mode=self.profile.bridge_mode,
            has_state_store=self.state_store is not None,
            has_mode_fsm=self.mode_fsm is not None,
            has_event_router=self.event_router is not None,
        )
    # --------------------------------------------------------
    # APP BINDING
    # --------------------------------------------------------
    def bind_app(self, app: Any) -> None:
        if self.mapper is None or self.bridge is None:
            self.build()
        assert self.mapper is not None
        self.mapper.bind_existing_app(app)
        setattr(app, "hmi_mapper", self.mapper)
        setattr(app, "hmi_runtime_bridge", self.bridge)
        setattr(app, "hmi_integration_manager", self)
        self._emit_status(
            "integration_manager/app_bound",
            app_class=app.__class__.__name__,
            profile_name=self.profile.name,
        )
    # --------------------------------------------------------
    # POLICY-DRIVEN EVENT HANDLING
    # --------------------------------------------------------
    def handle_hmi_event(self, event_name: str, payload: Optional[dict] = None) -> None:
        payload = payload or {}
        self._last_event_name = event_name
        policy = get_event_policy(event_name, self.profile)
        self._mirror_policy_trace(event_name, policy)
        self._emit_status(
            "integration_manager/event_received",
            event_name=event_name,
            payload=payload,
            forward_to_runtime=policy.forward_to_runtime,
            keep_legacy_behavior=policy.keep_legacy_behavior,
            mirror_to_state_store=policy.mirror_to_state_store,
            drive_fsm=policy.drive_fsm,
        )
        if self.bridge is None:
            return
        if policy.forward_to_runtime:
            self.bridge.handle_hmi_event(event_name, payload)
    # --------------------------------------------------------
    # SNAPSHOT SYNC
    # --------------------------------------------------------
    def sync_from_app(self, app: Any) -> None:
        if self.bridge is None:
            return
        self.bridge.sync_from_app(app)
        self._last_snapshot_ts = time.time()
        self._emit_status(
            "integration_manager/app_synced",
            screen_name=getattr(getattr(app, "sm", None), "current", "unknown"),
            active_mode=getattr(app, "active_mode", None),
            system_started=bool(getattr(app, "is_system_started", False)),
        )
    # --------------------------------------------------------
    # MAPPER ACCESS HELPERS
    # --------------------------------------------------------
    def map_button_from_app(self, app: Any, btn_instance: Any, name: str):
        if self.mapper is None:
            return None
        return self.mapper.map_button(
            name=name,
            button_state=getattr(btn_instance, "state", None),
            active_mode=getattr(app, "active_mode", None),
            is_system_started=bool(getattr(app, "is_system_started", False)),
            is_autonom_active=bool(getattr(app, "is_autonom_active", False)),
        )
    def map_top_icon_from_app(self, icon_name: str):
        if self.mapper is None:
            return None
        return self.mapper.map_top_icon(icon_name)
    def map_fault_short_from_app(self, app: Any):
        if self.mapper is None:
            return None
        return self.mapper.map_fault_short_press(
            int(getattr(app, "fault_level", 0))
        )
    def map_fault_long_from_app(self, app: Any):
        if self.mapper is None:
            return None
        return self.mapper.map_fault_long_press(
            int(getattr(app, "fault_level", 0)),
            fault_count=len(getattr(app, "fault_messages", [])),
        )
    def map_left_joystick_long(self):
        if self.mapper is None:
            return None
        return self.mapper.map_left_joystick_button("long")
    def map_right_joystick_short(self, engine_sound_enabled: bool):
        if self.mapper is None:
            return None
        return self.mapper.map_right_joystick_button(
            "short",
            bool(engine_sound_enabled),
        )
    # --------------------------------------------------------
    # HEARTBEAT
    # --------------------------------------------------------
    def emit_hmi_heartbeat(self, app: Any):
        if self.mapper is None:
            return None
        result = self.mapper.emit_snapshot_heartbeat(app)
        self.sync_from_app(app)
        return result
    # --------------------------------------------------------
    # PROFILE CONTROL
    # --------------------------------------------------------
    def set_profile(self, profile: IntegrationProfile) -> None:
        self.profile = profile
        if self.bridge is not None:
            self.bridge.config = HMIRuntimeBridgeConfig(
                mode=profile.bridge_mode,
                mirror_hmi_state=True,
                forward_events_to_router=True,
                drive_fsm_from_hmi=True,
                emit_status_logs=True,
            )
        self._emit_status(
            "integration_manager/profile_changed",
            profile_name=profile.name,
            bridge_mode=profile.bridge_mode,
        )
    # --------------------------------------------------------
    # INSPECTION
    # --------------------------------------------------------
    def get_status(self) -> HybridIntegrationStatus:
        bridge_mode = self.profile.bridge_mode
        if self.bridge is not None:
            bridge_mode = self.bridge.config.mode
        return HybridIntegrationStatus(
            ts=time.time(),
            profile_name=self.profile.name,
            bridge_mode=bridge_mode,
            mapper_bound=self.mapper is not None,
            bridge_ready=self.bridge is not None,
            last_event_name=self._last_event_name,
            last_snapshot_ts=self._last_snapshot_ts,
        )
    def get_status_dict(self) -> dict:
        status = self.get_status()
        return {
            "ts": status.ts,
            "profile_name": status.profile_name,
            "bridge_mode": status.bridge_mode,
            "mapper_bound": status.mapper_bound,
            "bridge_ready": status.bridge_ready,
            "last_event_name": status.last_event_name,
            "last_snapshot_ts": status.last_snapshot_ts,
        }


# ============================================================
# MODULE-R034
# ============================================================

# runtime/remotepi_runtime_wiring_stage2.py
"""
MODULE-R034
RemotePi Runtime Wiring Stage-2 - Final Compatibility Revision
--------------------------------------------------------------

Purpose:
    Stage-2 runtime wiring layer for RemotePi.

Scope:
    Add second-stage runtime services on top of Stage-1 integration:
        - telemetry manager
        - local command executor
        - watchdog supervisor
        - safe shutdown manager

Design goals:
    - Preserve working legacy HMI behavior
    - Allow partial runtime activation without hard dependency on every adapter
    - Provide safe fallback implementations
    - Keep wiring explicit and inspectable
    - Stay compatible with final StateStore / ModeFSM / EventRouter / HybridIntegrationManager
"""
import time
from dataclasses import dataclass
from typing import Any, Callable, Optional
from runtime.remotepi_telemetry_manager import RemotePiTelemetryManager
from runtime.remotepi_local_command_executor import RemotePiLocalCommandExecutor
from runtime.remotepi_watchdog_supervisor import (
    RemotePiWatchdogSupervisor,
    WatchdogDecision,
)
from runtime.remotepi_safe_shutdown_manager import (
    RemotePiSafeShutdownManager,
    ShutdownReason,
)
# ============================================================
# CONFIG
# ============================================================
@dataclass
class RuntimeWiringStage2Config:
    telemetry_period_sec: float = 0.25
    watchdog_period_sec: float = 0.50
    auto_apply_watchdog_actions: bool = True
    auto_shutdown_on_request: bool = True
    emit_status_logs: bool = True
# ============================================================
# MAIN CLASS
# ============================================================
class RemotePiRuntimeWiringStage2:
    """
    Stage-2 runtime composition helper.
    Expected Stage-1 objects:
        - state_store
        - event_router
        - mode_fsm
        - hmi_integration_manager
    This class wires:
        - telemetry manager
        - local command executor
        - watchdog supervisor
        - safe shutdown manager
    """
    def __init__(
        self,
        *,
        state_store,
        event_router=None,
        mode_fsm=None,
        hmi_integration_manager=None,
        logger=None,
        config: Optional[RuntimeWiringStage2Config] = None,
        status_sink: Optional[Callable[[str, dict], None]] = None,
    ):
        self.state_store = state_store
        self.event_router = event_router
        self.mode_fsm = mode_fsm
        self.hmi_integration_manager = hmi_integration_manager
        self.logger = logger
        self.config = config or RuntimeWiringStage2Config()
        self.status_sink = status_sink
        self.telemetry_manager: Optional[RemotePiTelemetryManager] = None
        self.local_command_executor: Optional[RemotePiLocalCommandExecutor] = None
        self.watchdog_supervisor: Optional[RemotePiWatchdogSupervisor] = None
        self.safe_shutdown_manager: Optional[RemotePiSafeShutdownManager] = None
        self._last_telemetry_ts = 0.0
        self._last_watchdog_ts = 0.0
        self._shutdown_started = False
        self._last_watchdog_decision: Optional[WatchdogDecision] = None
    # --------------------------------------------------------
    # STATUS
    # --------------------------------------------------------
    def _emit_status(self, topic: str, **payload) -> None:
        if not self.config.emit_status_logs:
            return
        if self.status_sink is not None:
            self.status_sink(topic, {
                "ts": time.time(),
                **payload,
            })
    # --------------------------------------------------------
    # SAFE FALLBACK ADAPTERS
    # --------------------------------------------------------
    @staticmethod
    def _noop_output_writer(name: str, state: bool) -> None:
        _ = (name, state)
    @staticmethod
    def _noop_ui_fault_hook(payload: dict) -> None:
        _ = payload
    @staticmethod
    def _noop_platform_shutdown(payload: dict) -> None:
        _ = payload
    @staticmethod
    def _default_network_status_reader() -> dict:
        return {
            "network_online": True,
            "network_weak": False,
            "master_link_ok": True,
            "adc1_online": True,
            "adc2_online": True,
            "i2c_ok": True,
            "wifi_connected": True,
            "bluetooth_connected": False,
            "ethernet_link": False,
        }
    @staticmethod
    def _default_ui_health_reader() -> bool:
        return True
    @staticmethod
    def _default_system_active_reader() -> bool:
        return False
    @staticmethod
    def _default_adc_reader(channel_name: str) -> float:
        defaults = {
            "BATTERY_VOLTAGE_SENSE": 24.0,
            "LM35_TEMP": 28.0,
            "NTC_BATTERY_TEMP": 29.0,
        }
        return float(defaults.get(channel_name, 0.0))
    @staticmethod
    def _default_gpio_writer(name: str, state: bool) -> None:
        _ = (name, state)
    # --------------------------------------------------------
    # STATE / LINK READERS
    # --------------------------------------------------------
    def _state_reader(self) -> dict:
        try:
            return self.state_store.to_dict()
        except Exception as exc:
            self._emit_status("stage2/state_reader_error", error=str(exc))
            return {}
    def _link_status_reader(self) -> dict:
        # Final link manager henüz zorunlu değil; watchdog için güvenli şekil döndürülür.
        return {
            "state": "UP",
            "connected": True,
            "master_link_ok": True,
            "last_rx_ts": time.time(),
            "last_tx_ts": time.time(),
            "reconnect_count": 0,
            "last_error": None,
        }
    # --------------------------------------------------------
    # OUTPUT STATE HOOK
    # --------------------------------------------------------
    def _state_store_output_hook(self, output_name: str, state: bool) -> None:
        try:
            if output_name == "FAN":
                self.state_store.set_fan_active(bool(state))
            elif output_name == "BUZZER":
                self.state_store.set_buzzer_active(bool(state))
        except Exception as exc:
            self._emit_status(
                "stage2/output_hook_error",
                output_name=output_name,
                error=str(exc),
            )
    # --------------------------------------------------------
    # TELEMETRY / HEALTH EVENT SINK
    # --------------------------------------------------------
    def _telemetry_event_sink(self, topic_or_event: str, payload: dict) -> None:
        try:
            if topic_or_event == "remotepi/telemetry":
                batt = float(payload.get("battery_voltage", 0.0))
                batt_temp = float(payload.get("battery_temp_c", 0.0))
                local_temp = float(payload.get("local_temp_c", 0.0))
                fan_active = bool(payload.get("remote_fan_active", False))
                bucket = "STATE_BATTERY_NORMAL"
                if batt <= 10:
                    bucket = "STATE_BATTERY_SHUTDOWN"
                elif batt <= 20:
                    bucket = "STATE_BATTERY_CRITICAL"
                elif batt <= 40:
                    bucket = "STATE_BATTERY_WARNING"
                self.state_store.update_battery(
                    voltage=batt,
                    percent_est=batt,
                    bucket=bucket,
                )
                self.state_store.update_thermal(
                    local_temp_c=local_temp,
                    battery_temp_c=batt_temp,
                    thermal_state="STATE_TEMP_NORMAL",
                )
                self.state_store.set_fan_active(fan_active)
            elif topic_or_event == "remotepi/health":
                self.state_store.update_safety(
                    severity=str(payload.get("severity", "NORMAL")),
                    primary_state=str(payload.get("primary_state", "STATE_READY")),
                    accept_user_control=bool(payload.get("accept_user_control", True)),
                    allow_new_motion_commands=bool(payload.get("allow_new_motion_commands", True)),
                    request_shutdown=bool(payload.get("request_shutdown", False)),
                    ui_fault_latched=bool(payload.get("ui_fault_latched", False)),
                    summary=str(payload.get("summary", "")),
                    warnings=list(payload.get("warnings", [])),
                    faults=list(payload.get("faults", [])),
                    thermal_state=str(payload.get("thermal_state", "STATE_TEMP_NORMAL")),
                )
            # EventRouter policy update hook is optional
            if self.event_router is not None and topic_or_event == "remotepi/health":
                # create minimal policy update only if router uses explicit fault policy
                pass
        except Exception as exc:
            self._emit_status(
                "stage2/telemetry_sink_error",
                topic_or_event=topic_or_event,
                error=str(exc),
            )
    # --------------------------------------------------------
    # MASTER NOTIFY
    # --------------------------------------------------------
    def _notify_master_sink(self, command_name: str, payload: dict) -> None:
        self._emit_status(
            "stage2/notify_master",
            command_name=command_name,
            payload=payload,
        )
    # --------------------------------------------------------
    # BUILDERS
    # --------------------------------------------------------
    def build_local_command_executor(
        self,
        *,
        gpio_writer: Optional[Callable[[str, bool], None]] = None,
        ui_fault_hook: Optional[Callable[[dict], None]] = None,
    ) -> RemotePiLocalCommandExecutor:
        self.local_command_executor = RemotePiLocalCommandExecutor(
            gpio_writer=gpio_writer or self._noop_output_writer,
            ui_fault_hook=ui_fault_hook or self._noop_ui_fault_hook,
            state_store_hook=self._state_store_output_hook,
        )
        self._emit_status("stage2/local_executor_built")
        return self.local_command_executor
    def build_telemetry_manager(
        self,
        *,
        adc_reader: Optional[Callable[[str], float]] = None,
        output_writer: Optional[Callable[[str, bool], None]] = None,
        network_status_reader: Optional[Callable[[], dict]] = None,
        ui_health_reader: Optional[Callable[[], bool]] = None,
        system_active_reader: Optional[Callable[[], bool]] = None,
    ) -> RemotePiTelemetryManager:
        self.telemetry_manager = RemotePiTelemetryManager(
            adc_reader=adc_reader or self._default_adc_reader,
            output_writer=output_writer or self._default_gpio_writer,
            event_sink=self._telemetry_event_sink,
            network_status_reader=network_status_reader or self._default_network_status_reader,
            ui_health_reader=ui_health_reader or self._default_ui_health_reader,
            system_active_reader=system_active_reader or self._default_system_active_reader,
        )
        self._emit_status("stage2/telemetry_manager_built")
        return self.telemetry_manager
    def build_watchdog_supervisor(self) -> RemotePiWatchdogSupervisor:
        self.watchdog_supervisor = RemotePiWatchdogSupervisor(
            state_reader=self._state_reader,
            link_status_reader=self._link_status_reader,
            event_sink=lambda topic, payload: self._emit_status(
                "stage2/watchdog_event",
                watchdog_topic=topic,
                payload=payload,
            ),
        )
        self._emit_status("stage2/watchdog_built")
        return self.watchdog_supervisor
    def build_safe_shutdown_manager(
        self,
        *,
        link_manager=None,
        command_transport=None,
        platform_shutdown_hook: Optional[Callable[[dict], None]] = None,
    ) -> RemotePiSafeShutdownManager:
        self.safe_shutdown_manager = RemotePiSafeShutdownManager(
            state_store=self.state_store,
            local_command_executor=self.local_command_executor,
            link_manager=link_manager,
            command_transport=command_transport,
            logger=self.logger,
            notify_master_sink=self._notify_master_sink,
            platform_shutdown_hook=platform_shutdown_hook or self._noop_platform_shutdown,
        )
        self._emit_status("stage2/safe_shutdown_built")
        return self.safe_shutdown_manager
    # --------------------------------------------------------
    # ALL-IN-ONE BUILD
    # --------------------------------------------------------
    def build_all(
        self,
        *,
        adc_reader: Optional[Callable[[str], float]] = None,
        gpio_writer: Optional[Callable[[str, bool], None]] = None,
        ui_fault_hook: Optional[Callable[[dict], None]] = None,
        network_status_reader: Optional[Callable[[], dict]] = None,
        ui_health_reader: Optional[Callable[[], bool]] = None,
        system_active_reader: Optional[Callable[[], bool]] = None,
        link_manager=None,
        command_transport=None,
        platform_shutdown_hook: Optional[Callable[[dict], None]] = None,
    ) -> None:
        if self.local_command_executor is None:
            self.build_local_command_executor(
                gpio_writer=gpio_writer,
                ui_fault_hook=ui_fault_hook,
            )
        if self.telemetry_manager is None:
            self.build_telemetry_manager(
                adc_reader=adc_reader,
                output_writer=gpio_writer,
                network_status_reader=network_status_reader,
                ui_health_reader=ui_health_reader,
                system_active_reader=system_active_reader,
            )
        if self.watchdog_supervisor is None:
            self.build_watchdog_supervisor()
        if self.safe_shutdown_manager is None:
            self.build_safe_shutdown_manager(
                link_manager=link_manager,
                command_transport=command_transport,
                platform_shutdown_hook=platform_shutdown_hook,
            )
        self._emit_status("stage2/build_all_complete")
    # --------------------------------------------------------
    # WATCHDOG ACTIONS
    # --------------------------------------------------------
    def apply_watchdog_decision(self, decision: WatchdogDecision) -> None:
        self._last_watchdog_decision = decision
        self._emit_status(
            "stage2/watchdog_decision",
            severity=decision.severity.value,
            warnings=list(decision.warnings),
            faults=list(decision.faults),
            request_shutdown=decision.request_shutdown,
            summary=decision.summary,
        )
        # Safety state mirror
        try:
            self.state_store.update_safety(
                severity=decision.severity.value,
                primary_state="STATE_SHUTDOWN" if decision.request_shutdown else "STATE_ACTIVE",
                accept_user_control=(decision.severity.value not in ("FAULT", "CRITICAL", "SHUTDOWN")),
                allow_new_motion_commands=(decision.severity.value == "NORMAL"),
                request_shutdown=bool(decision.request_shutdown),
                ui_fault_latched=bool(decision.force_fault_view),
                summary=str(decision.summary),
                warnings=list(decision.warnings),
                faults=list(decision.faults),
            )
        except Exception as exc:
            self._emit_status("stage2/safety_mirror_error", error=str(exc))
        # FSM override
        if self.mode_fsm is not None and hasattr(self.mode_fsm, "safety_override"):
            try:
                self.mode_fsm.safety_override()
            except Exception as exc:
                self._emit_status("stage2/fsm_override_error", error=str(exc))
        # Local actions
        if self.local_command_executor is not None:
            if decision.force_fault_view:
                self.local_command_executor.open_fault_view({
                    "source": "WATCHDOG",
                    "summary": decision.summary,
                    "faults": list(decision.faults),
                    "warnings": list(decision.warnings),
                })
            if decision.force_buzzer == "WARNING":
                self.local_command_executor.execute("CMD_BUZZER_WARNING", {})
            elif decision.force_buzzer == "FAULT":
                self.local_command_executor.execute("CMD_BUZZER_FAULT", {})
            elif decision.force_buzzer == "CRITICAL":
                self.local_command_executor.execute("CMD_BUZZER_CRITICAL", {})
        # Safe shutdown
        if (
            decision.request_shutdown
            and self.config.auto_shutdown_on_request
            and self.safe_shutdown_manager is not None
            and not self._shutdown_started
        ):
            self._shutdown_started = True
            req = self.safe_shutdown_manager.request_shutdown(
                reason=ShutdownReason.WATCHDOG_REQUEST,
                source="WATCHDOG_SUPERVISOR",
                detail={
                    "summary": decision.summary,
                    "faults": list(decision.faults),
                    "warnings": list(decision.warnings),
                },
            )
            result = self.safe_shutdown_manager.execute(req)
            self._emit_status(
                "stage2/shutdown_executed",
                ok=result.ok,
                stage=result.stage.value,
                summary=result.summary,
            )
    # --------------------------------------------------------
    # TICK
    # --------------------------------------------------------
    def tick(self) -> None:
        now = time.time()
        if self.telemetry_manager is not None:
            if (now - self._last_telemetry_ts) >= self.config.telemetry_period_sec:
                try:
                    self.telemetry_manager.tick()
                except Exception as exc:
                    self._emit_status("stage2/telemetry_tick_error", error=str(exc))
                self._last_telemetry_ts = now
        if self.watchdog_supervisor is not None:
            if (now - self._last_watchdog_ts) >= self.config.watchdog_period_sec:
                try:
                    decision = self.watchdog_supervisor.tick()
                    if self.config.auto_apply_watchdog_actions:
                        self.apply_watchdog_decision(decision)
                except Exception as exc:
                    self._emit_status("stage2/watchdog_tick_error", error=str(exc))
                self._last_watchdog_ts = now
    # --------------------------------------------------------
    # INSPECTION
    # --------------------------------------------------------
    def get_status_dict(self) -> dict:
        return {
            "telemetry_manager_ready": self.telemetry_manager is not None,
            "local_command_executor_ready": self.local_command_executor is not None,
            "watchdog_supervisor_ready": self.watchdog_supervisor is not None,
            "safe_shutdown_manager_ready": self.safe_shutdown_manager is not None,
            "last_telemetry_ts": self._last_telemetry_ts,
            "last_watchdog_ts": self._last_watchdog_ts,
            "shutdown_started": self._shutdown_started,
            "last_watchdog_decision": None if self._last_watchdog_decision is None else {
                "severity": self._last_watchdog_decision.severity.value,
                "warnings": list(self._last_watchdog_decision.warnings),
                "faults": list(self._last_watchdog_decision.faults),
                "request_shutdown": self._last_watchdog_decision.request_shutdown,
                "summary": self._last_watchdog_decision.summary,
            },
            "config": {
                "telemetry_period_sec": self.config.telemetry_period_sec,
                "watchdog_period_sec": self.config.watchdog_period_sec,
                "auto_apply_watchdog_actions": self.config.auto_apply_watchdog_actions,
                "auto_shutdown_on_request": self.config.auto_shutdown_on_request,
            },
        }


# ============================================================
# MODULE-R035
# ============================================================

# runtime/remotepi_runtime_lifecycle.py
"""
MODULE-R035
RemotePi Runtime Lifecycle
--------------------------

Purpose:
    Manage high-level lifecycle phases of the RemotePi runtime.

Responsibilities:
    - Control boot-to-ready transition
    - Control ready-to-running transition
    - Handle fault entry / recovery flow
    - Handle shutdown lock state
    - Coordinate with state store and mode FSM
    - Provide deterministic lifecycle gating for runtime services

Compatible with:
    - RemotePiStateStore final compatibility revision
    - RemotePiModeFSM final compatibility revision
    - Hybrid integration / Stage-2 runtime wiring
"""
import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Callable
# ============================================================
# ENUMS
# ============================================================
class LifecycleState(str, Enum):
    BOOTING = "BOOTING"
    READY = "READY"
    RUNNING = "RUNNING"
    FAULTED = "FAULTED"
    RECOVERING = "RECOVERING"
    SHUTDOWN = "SHUTDOWN"
# ============================================================
# DATA MODELS
# ============================================================
@dataclass
class LifecycleSnapshot:
    ts: float
    lifecycle_state: LifecycleState
    active_mode: str
    system_running: bool
    motion_allowed: bool
    shutdown_requested: bool
    summary: str
# ============================================================
# MAIN CLASS
# ============================================================
class RemotePiRuntimeLifecycle:
    def __init__(
        self,
        *,
        state_store,
        mode_fsm=None,
        status_sink: Optional[Callable[[str, dict], None]] = None,
    ):
        self.state_store = state_store
        self.mode_fsm = mode_fsm
        self.status_sink = status_sink
        self._state = LifecycleState.BOOTING
        self._last_transition_ts = time.time()
        self._summary = "Lifecycle initialized in BOOTING state."
        self._apply_state()
    # --------------------------------------------------------
    # INTERNAL
    # --------------------------------------------------------
    def _emit_status(self, topic: str, **payload) -> None:
        if self.status_sink is not None:
            self.status_sink(topic, {
                "ts": time.time(),
                **payload,
            })
    def _transition(self, next_state: LifecycleState, summary: str) -> None:
        self._state = next_state
        self._last_transition_ts = time.time()
        self._summary = summary
        self._apply_state()
        self._emit_status(
            "runtime_lifecycle/transition",
            lifecycle_state=self._state.value,
            summary=summary,
        )
    def _apply_state(self) -> None:
        if self._state == LifecycleState.BOOTING:
            self.state_store.update_safety(
                severity="BOOT",
                primary_state="STATE_BOOTING",
                accept_user_control=False,
                allow_new_motion_commands=False,
                request_shutdown=False,
                ui_fault_latched=False,
                summary=self._summary,
                warnings=[],
                faults=[],
            )
            if self.mode_fsm is not None and hasattr(self.mode_fsm, "to_boot"):
                self.mode_fsm.to_boot()
        elif self._state == LifecycleState.READY:
            self.state_store.update_safety(
                severity="NORMAL",
                primary_state="STATE_READY",
                accept_user_control=True,
                allow_new_motion_commands=False,
                request_shutdown=False,
                ui_fault_latched=False,
                summary=self._summary,
                warnings=[],
                faults=[],
            )
            if self.mode_fsm is not None and hasattr(self.mode_fsm, "to_control_menu"):
                self.mode_fsm.to_control_menu()
        elif self._state == LifecycleState.RUNNING:
            self.state_store.update_safety(
                severity="NORMAL",
                primary_state="STATE_ACTIVE",
                accept_user_control=True,
                allow_new_motion_commands=True,
                request_shutdown=False,
                ui_fault_latched=False,
                summary=self._summary,
                warnings=[],
                faults=[],
            )
            self.state_store.set_system_running(True)
        elif self._state == LifecycleState.FAULTED:
            self.state_store.update_safety(
                severity="FAULT",
                primary_state="STATE_FAULT",
                accept_user_control=False,
                allow_new_motion_commands=False,
                request_shutdown=False,
                ui_fault_latched=True,
                summary=self._summary,
                warnings=[],
                faults=["LIFECYCLE_FAULTED"],
            )
            self.state_store.set_system_running(False)
            if self.mode_fsm is not None and hasattr(self.mode_fsm, "to_fault_lock"):
                self.mode_fsm.to_fault_lock()
        elif self._state == LifecycleState.RECOVERING:
            self.state_store.update_safety(
                severity="WARNING",
                primary_state="STATE_RECOVERING",
                accept_user_control=False,
                allow_new_motion_commands=False,
                request_shutdown=False,
                ui_fault_latched=True,
                summary=self._summary,
                warnings=["LIFECYCLE_RECOVERING"],
                faults=[],
            )
            self.state_store.set_system_running(False)
        elif self._state == LifecycleState.SHUTDOWN:
            self.state_store.update_safety(
                severity="SHUTDOWN",
                primary_state="STATE_SHUTDOWN",
                accept_user_control=False,
                allow_new_motion_commands=False,
                request_shutdown=True,
                ui_fault_latched=True,
                summary=self._summary,
                warnings=[],
                faults=["LIFECYCLE_SHUTDOWN"],
            )
            self.state_store.set_system_running(False)
            if self.mode_fsm is not None and hasattr(self.mode_fsm, "to_shutdown"):
                self.mode_fsm.to_shutdown()
    # --------------------------------------------------------
    # EXPLICIT LIFECYCLE COMMANDS
    # --------------------------------------------------------
    def enter_ready(self) -> None:
        self._transition(
            LifecycleState.READY,
            "Boot completed, system ready."
        )
    def start_runtime(self) -> bool:
        if self._state not in (LifecycleState.READY, LifecycleState.RECOVERING):
            self._emit_status(
                "runtime_lifecycle/start_blocked",
                reason="invalid_state",
                lifecycle_state=self._state.value,
            )
            return False
        if not self.state_store.is_safe_to_run():
            self._emit_status(
                "runtime_lifecycle/start_blocked",
                reason="state_store_not_safe",
                lifecycle_state=self._state.value,
            )
            return False
        if self.mode_fsm is not None and hasattr(self.mode_fsm, "to_manual"):
            self.mode_fsm.to_manual()
        self._transition(
            LifecycleState.RUNNING,
            "Runtime entered RUNNING state."
        )
        return True
    def enter_fault(self, summary: str = "Lifecycle fault entered.") -> None:
        self._transition(
            LifecycleState.FAULTED,
            summary,
        )
    def begin_recovery(self, summary: str = "Recovery started.") -> bool:
        if self._state != LifecycleState.FAULTED:
            self._emit_status(
                "runtime_lifecycle/recovery_blocked",
                reason="not_faulted",
                lifecycle_state=self._state.value,
            )
            return False
        self._transition(
            LifecycleState.RECOVERING,
            summary,
        )
        return True
    def finish_recovery(self) -> bool:
        if self._state != LifecycleState.RECOVERING:
            self._emit_status(
                "runtime_lifecycle/recovery_finish_blocked",
                reason="not_recovering",
                lifecycle_state=self._state.value,
            )
            return False
        self.state_store.clear_fault_latch()
        self.state_store.clear_faults()
        self.state_store.clear_warnings()
        self._transition(
            LifecycleState.READY,
            "Recovery completed, system returned to READY."
        )
        return True
    def request_shutdown(self, summary: str = "Shutdown requested.") -> None:
        self._transition(
            LifecycleState.SHUTDOWN,
            summary,
        )
    # --------------------------------------------------------
    # AUTO ALIGNMENT
    # --------------------------------------------------------
    def auto_align_from_state(self) -> None:
        safety = self.state_store.get_safety()
        severity = str(safety.get("severity", "NORMAL"))
        request_shutdown = bool(safety.get("request_shutdown", False))
        if request_shutdown or severity == "SHUTDOWN":
            if self._state != LifecycleState.SHUTDOWN:
                self.request_shutdown("Lifecycle auto-aligned to SHUTDOWN.")
            return
        if severity in ("FAULT", "CRITICAL"):
            if self._state != LifecycleState.FAULTED:
                self.enter_fault("Lifecycle auto-aligned to FAULTED.")
            return
        if self._state == LifecycleState.BOOTING and severity in ("NORMAL", "WARNING"):
            self.enter_ready()
    # --------------------------------------------------------
    # ACCESSORS
    # --------------------------------------------------------
    @property
    def lifecycle_state(self) -> LifecycleState:
        return self._state
    @property
    def last_transition_ts(self) -> float:
        return self._last_transition_ts
    def snapshot(self) -> LifecycleSnapshot:
        return LifecycleSnapshot(
            ts=time.time(),
            lifecycle_state=self._state,
            active_mode=self.state_store.get_active_mode(),
            system_running=self.state_store.is_system_running(),
            motion_allowed=self.state_store.is_motion_allowed(),
            shutdown_requested=bool(self.state_store.get_safety().get("request_shutdown", False)),
            summary=self._summary,
        )
    def to_dict(self) -> dict:
        snap = self.snapshot()
        return {
            "ts": snap.ts,
            "lifecycle_state": snap.lifecycle_state.value,
            "active_mode": snap.active_mode,
            "system_running": snap.system_running,
            "motion_allowed": snap.motion_allowed,
            "shutdown_requested": snap.shutdown_requested,
            "summary": snap.summary,
            "last_transition_ts": self._last_transition_ts,
        }


# ============================================================
# MODULE-R036
# ============================================================

# runtime/remotepi_safety_supervisor.py
"""
MODULE-R036
RemotePi Safety Supervisor
--------------------------

Purpose:
    High-level safety orchestration layer for RemotePi.

Responsibilities:
    - Monitor battery / thermal / ADC / UI / comm health inputs
    - Escalate safety conditions into lifecycle / FSM / state store
    - Apply deterministic safety decisions
    - Request fault / recovery / shutdown transitions when needed

Compatible with:
    - RemotePiStateStore final compatibility revision
    - RemotePiModeFSM final compatibility revision
    - RemotePiRuntimeLifecycle
"""
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional
# ============================================================
# ENUMS
# ============================================================
class SafetyLevel(str, Enum):
    NORMAL = "NORMAL"
    WARNING = "WARNING"
    FAULT = "FAULT"
    CRITICAL = "CRITICAL"
    SHUTDOWN = "SHUTDOWN"
# ============================================================
# DATA MODELS
# ============================================================
@dataclass
class SafetyThresholds:
    battery_warning_pct: float = 40.0
    battery_fault_pct: float = 20.0
    battery_shutdown_pct: float = 10.0
    local_temp_warning_c: float = 55.0
    local_temp_fault_c: float = 65.0
    local_temp_shutdown_c: float = 75.0
    battery_temp_warning_c: float = 50.0
    battery_temp_fault_c: float = 60.0
    battery_temp_shutdown_c: float = 70.0
    joystick_stuck_abs_threshold: float = 0.85
    joystick_stuck_duration_sec: float = 8.0
@dataclass
class SafetyDecision:
    level: SafetyLevel
    warnings: list[str] = field(default_factory=list)
    faults: list[str] = field(default_factory=list)
    request_fault_state: bool = False
    request_recovery_hold: bool = False
    request_shutdown: bool = False
    force_fan_on: bool = False
    summary: str = "Safety healthy."
# ============================================================
# MAIN CLASS
# ============================================================
class RemotePiSafetySupervisor:
    def __init__(
        self,
        *,
        state_store,
        runtime_lifecycle=None,
        mode_fsm=None,
        network_status_reader: Optional[Callable[[], dict]] = None,
        ui_health_reader: Optional[Callable[[], bool]] = None,
        thresholds: Optional[SafetyThresholds] = None,
        status_sink: Optional[Callable[[str, dict], None]] = None,
    ):
        self.state_store = state_store
        self.runtime_lifecycle = runtime_lifecycle
        self.mode_fsm = mode_fsm
        self.network_status_reader = network_status_reader or (lambda: {})
        self.ui_health_reader = ui_health_reader or (lambda: True)
        self.thresholds = thresholds or SafetyThresholds()
        self.status_sink = status_sink
        self._last_nonzero_motion_ts = 0.0
        self._last_decision: Optional[SafetyDecision] = None
    # --------------------------------------------------------
    # INTERNAL
    # --------------------------------------------------------
    def _emit_status(self, topic: str, **payload) -> None:
        if self.status_sink is not None:
            self.status_sink(topic, {
                "ts": time.time(),
                **payload,
            })
    def _current_state(self) -> dict:
        try:
            return self.state_store.to_dict()
        except Exception:
            return {}
    def _current_network(self) -> dict:
        try:
            return dict(self.network_status_reader())
        except Exception:
            return {}
    # --------------------------------------------------------
    # CHECKS
    # --------------------------------------------------------
    def _check_battery(self, state: dict, decision: SafetyDecision) -> None:
        battery = state.get("battery", {})
        pct = float(battery.get("percent_est", 0.0))
        if pct <= self.thresholds.battery_shutdown_pct:
            decision.level = SafetyLevel.SHUTDOWN
            decision.request_shutdown = True
            decision.faults.append("BATTERY_SHUTDOWN_THRESHOLD")
            return
        if pct <= self.thresholds.battery_fault_pct:
            if decision.level in (SafetyLevel.NORMAL, SafetyLevel.WARNING):
                decision.level = SafetyLevel.FAULT
            decision.request_fault_state = True
            decision.faults.append("BATTERY_FAULT_THRESHOLD")
            return
        if pct <= self.thresholds.battery_warning_pct:
            if decision.level == SafetyLevel.NORMAL:
                decision.level = SafetyLevel.WARNING
            decision.warnings.append("BATTERY_WARNING_THRESHOLD")
    def _check_thermal(self, state: dict, decision: SafetyDecision) -> None:
        thermal = state.get("thermal", {})
        local_temp = float(thermal.get("local_temp_c", 0.0))
        battery_temp = float(thermal.get("battery_temp_c", 0.0))
        if (
            local_temp >= self.thresholds.local_temp_shutdown_c
            or battery_temp >= self.thresholds.battery_temp_shutdown_c
        ):
            decision.level = SafetyLevel.SHUTDOWN
            decision.request_shutdown = True
            decision.force_fan_on = True
            decision.faults.append("THERMAL_SHUTDOWN_THRESHOLD")
            return
        if (
            local_temp >= self.thresholds.local_temp_fault_c
            or battery_temp >= self.thresholds.battery_temp_fault_c
        ):
            if decision.level in (SafetyLevel.NORMAL, SafetyLevel.WARNING):
                decision.level = SafetyLevel.FAULT
            decision.request_fault_state = True
            decision.force_fan_on = True
            decision.faults.append("THERMAL_FAULT_THRESHOLD")
            return
        if (
            local_temp >= self.thresholds.local_temp_warning_c
            or battery_temp >= self.thresholds.battery_temp_warning_c
        ):
            if decision.level == SafetyLevel.NORMAL:
                decision.level = SafetyLevel.WARNING
            decision.force_fan_on = True
            decision.warnings.append("THERMAL_WARNING_THRESHOLD")
    def _check_network_and_ui(self, decision: SafetyDecision) -> None:
        net = self._current_network()
        ui_ok = bool(self.ui_health_reader())
        if not ui_ok:
            if decision.level in (SafetyLevel.NORMAL, SafetyLevel.WARNING):
                decision.level = SafetyLevel.FAULT
            decision.request_fault_state = True
            decision.faults.append("UI_HEALTH_FAIL")
        if not bool(net.get("i2c_ok", True)):
            if decision.level in (SafetyLevel.NORMAL, SafetyLevel.WARNING):
                decision.level = SafetyLevel.FAULT
            decision.request_fault_state = True
            decision.faults.append("I2C_NOT_OK")
        if not bool(net.get("adc1_online", True)):
            if decision.level in (SafetyLevel.NORMAL, SafetyLevel.WARNING):
                decision.level = SafetyLevel.FAULT
            decision.request_fault_state = True
            decision.faults.append("ADC1_OFFLINE")
        if not bool(net.get("adc2_online", True)):
            if decision.level in (SafetyLevel.NORMAL, SafetyLevel.WARNING):
                decision.level = SafetyLevel.FAULT
            decision.request_fault_state = True
            decision.faults.append("ADC2_OFFLINE")
        if not bool(net.get("master_link_ok", True)):
            if decision.level == SafetyLevel.NORMAL:
                decision.level = SafetyLevel.WARNING
            decision.warnings.append("MASTER_LINK_NOT_OK")
    def _check_joystick_anomaly(self, state: dict, decision: SafetyDecision) -> None:
        inputs = state.get("inputs", {})
        values = [
            abs(float(inputs.get("left_x", 0.0))),
            abs(float(inputs.get("left_y", 0.0))),
            abs(float(inputs.get("right_x", 0.0))),
            abs(float(inputs.get("right_y", 0.0))),
        ]
        max_abs = max(values) if values else 0.0
        now = time.time()
        if max_abs >= self.thresholds.joystick_stuck_abs_threshold:
            if self._last_nonzero_motion_ts <= 0:
                self._last_nonzero_motion_ts = now
            elif (now - self._last_nonzero_motion_ts) >= self.thresholds.joystick_stuck_duration_sec:
                if decision.level in (SafetyLevel.NORMAL, SafetyLevel.WARNING):
                    decision.level = SafetyLevel.FAULT
                decision.request_fault_state = True
                decision.faults.append("JOYSTICK_STUCK_ANOMALY")
        else:
            self._last_nonzero_motion_ts = 0.0
    # --------------------------------------------------------
    # DECISION BUILD
    # --------------------------------------------------------
    def evaluate(self) -> SafetyDecision:
        state = self._current_state()
        decision = SafetyDecision(level=SafetyLevel.NORMAL)
        self._check_battery(state, decision)
        if not decision.request_shutdown:
            self._check_thermal(state, decision)
        if not decision.request_shutdown:
            self._check_network_and_ui(decision)
        if not decision.request_shutdown:
            self._check_joystick_anomaly(state, decision)
        if decision.level == SafetyLevel.NORMAL:
            decision.summary = "Safety healthy."
        else:
            parts = [f"level={decision.level.value}"]
            if decision.warnings:
                parts.append("warnings=" + ",".join(decision.warnings))
            if decision.faults:
                parts.append("faults=" + ",".join(decision.faults))
            if decision.request_shutdown:
                parts.append("shutdown=TRUE")
            if decision.force_fan_on:
                parts.append("fan=FORCED_ON")
            decision.summary = " | ".join(parts)
        self._last_decision = decision
        return decision
    # --------------------------------------------------------
    # APPLY
    # --------------------------------------------------------
    def apply(self, decision: Optional[SafetyDecision] = None) -> SafetyDecision:
        decision = decision or self.evaluate()
        # mirror state store safety
        try:
            self.state_store.update_safety(
                severity=decision.level.value,
                primary_state=(
                    "STATE_SHUTDOWN" if decision.request_shutdown
                    else "STATE_FAULT" if decision.request_fault_state
                    else "STATE_WARNING" if decision.level == SafetyLevel.WARNING
                    else "STATE_READY"
                ),
                accept_user_control=(decision.level in (SafetyLevel.NORMAL, SafetyLevel.WARNING)),
                allow_new_motion_commands=(decision.level == SafetyLevel.NORMAL),
                request_shutdown=decision.request_shutdown,
                ui_fault_latched=(decision.level in (SafetyLevel.FAULT, SafetyLevel.CRITICAL, SafetyLevel.SHUTDOWN)),
                summary=decision.summary,
                warnings=list(decision.warnings),
                faults=list(decision.faults),
            )
        except Exception as exc:
            self._emit_status("safety_supervisor/state_store_update_error", error=str(exc))
        # fan forcing
        if decision.force_fan_on:
            try:
                self.state_store.set_fan_active(True)
            except Exception:
                pass
        # FSM override
        if self.mode_fsm is not None:
            try:
                if decision.request_shutdown and hasattr(self.mode_fsm, "to_shutdown"):
                    self.mode_fsm.to_shutdown()
                elif decision.request_fault_state and hasattr(self.mode_fsm, "to_fault_lock"):
                    self.mode_fsm.to_fault_lock()
            except Exception as exc:
                self._emit_status("safety_supervisor/fsm_error", error=str(exc))
        # lifecycle override
        if self.runtime_lifecycle is not None:
            try:
                if decision.request_shutdown and hasattr(self.runtime_lifecycle, "request_shutdown"):
                    self.runtime_lifecycle.request_shutdown(decision.summary)
                elif decision.request_fault_state and hasattr(self.runtime_lifecycle, "enter_fault"):
                    self.runtime_lifecycle.enter_fault(decision.summary)
            except Exception as exc:
                self._emit_status("safety_supervisor/lifecycle_error", error=str(exc))
        self._emit_status(
            "safety_supervisor/applied",
            level=decision.level.value,
            warnings=list(decision.warnings),
            faults=list(decision.faults),
            request_fault_state=decision.request_fault_state,
            request_shutdown=decision.request_shutdown,
            force_fan_on=decision.force_fan_on,
            summary=decision.summary,
        )
        return decision
    # --------------------------------------------------------
    # TICK
    # --------------------------------------------------------
    def tick(self) -> SafetyDecision:
        decision = self.evaluate()
        return self.apply(decision)
    # --------------------------------------------------------
    # INSPECTION
    # --------------------------------------------------------
    def get_last_decision_dict(self) -> dict:
        if self._last_decision is None:
            return {
                "level": "UNKNOWN",
                "warnings": [],
                "faults": [],
                "request_fault_state": False,
                "request_recovery_hold": False,
                "request_shutdown": False,
                "force_fan_on": False,
                "summary": "No decision yet.",
            }
        return {
            "level": self._last_decision.level.value,
            "warnings": list(self._last_decision.warnings),
            "faults": list(self._last_decision.faults),
            "request_fault_state": self._last_decision.request_fault_state,
            "request_recovery_hold": self._last_decision.request_recovery_hold,
            "request_shutdown": self._last_decision.request_shutdown,
            "force_fan_on": self._last_decision.force_fan_on,
            "summary": self._last_decision.summary,
        }


# ============================================================
# MODULE-R037
# ============================================================

# runtime/remotepi_runtime_snapshot_bus.py
"""
MODULE-R037
RemotePi Runtime Snapshot Bus
-----------------------------

Purpose:
    Collect and unify runtime state from multiple RemotePi runtime layers.

Responsibilities:
    - Read snapshot/status data from runtime modules
    - Build one combined runtime snapshot
    - Expose compact and full views
    - Provide a stable export surface for telemetry, diagnostics and service tools

Compatible with:
    - RemotePiStateStore final compatibility revision
    - RemotePiModeFSM final compatibility revision
    - RemotePiRuntimeLifecycle
    - RemotePiSafetySupervisor
    - RemotePiWatchdogSupervisor
    - RemotePiHybridIntegrationManager final compatibility revision
    - RemotePiRuntimeWiringStage2 final compatibility revision
"""
import time
from dataclasses import dataclass, field, asdict, is_dataclass
from typing import Any, Callable, Optional
# ============================================================
# DATA MODELS
# ============================================================
@dataclass
class SnapshotSection:
    name: str
    ok: bool
    summary: str
    data: dict[str, Any] = field(default_factory=dict)
@dataclass
class RemotePiRuntimeSnapshot:
    created_ts: float
    overall_ok: bool
    overall_summary: str
    state_store: dict[str, Any] = field(default_factory=dict)
    mode_fsm: dict[str, Any] = field(default_factory=dict)
    lifecycle: dict[str, Any] = field(default_factory=dict)
    safety_supervisor: dict[str, Any] = field(default_factory=dict)
    watchdog: dict[str, Any] = field(default_factory=dict)
    integration_manager: dict[str, Any] = field(default_factory=dict)
    stage2_wiring: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    faults: list[str] = field(default_factory=list)
    sections: list[SnapshotSection] = field(default_factory=list)
# ============================================================
# HELPERS
# ============================================================
def _to_plain_dict(obj: Any) -> dict[str, Any]:
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return dict(obj)
    if is_dataclass(obj):
        return asdict(obj)
    if hasattr(obj, "to_dict") and callable(obj.to_dict):
        try:
            return dict(obj.to_dict())
        except Exception:
            pass
    if hasattr(obj, "__dict__"):
        return dict(vars(obj))
    return {"value": obj}
def _safe_call(fn: Callable[[], Any]) -> tuple[bool, Any]:
    try:
        return True, fn()
    except Exception as exc:
        return False, {"error": str(exc)}
# ============================================================
# MAIN CLASS
# ============================================================
class RemotePiRuntimeSnapshotBus:
    def __init__(
        self,
        *,
        state_store=None,
        mode_fsm=None,
        runtime_lifecycle=None,
        safety_supervisor=None,
        watchdog_supervisor=None,
        hybrid_integration_manager=None,
        runtime_wiring_stage2=None,
    ):
        self.state_store = state_store
        self.mode_fsm = mode_fsm
        self.runtime_lifecycle = runtime_lifecycle
        self.safety_supervisor = safety_supervisor
        self.watchdog_supervisor = watchdog_supervisor
        self.hybrid_integration_manager = hybrid_integration_manager
        self.runtime_wiring_stage2 = runtime_wiring_stage2
    # --------------------------------------------------------
    # SECTION BUILDERS
    # --------------------------------------------------------
    def _build_state_store_section(self, data: dict[str, Any]) -> SnapshotSection:
        safety = data.get("safety", {})
        severity = str(safety.get("severity", "UNKNOWN"))
        faults = list(data.get("faults", []))
        warnings = list(data.get("warnings", []))
        ok = severity not in ("FAULT", "CRITICAL", "SHUTDOWN") and not faults
        summary = (
            f"active_mode={data.get('mode', {}).get('active_mode', 'UNKNOWN')} | "
            f"running={data.get('mode', {}).get('system_running', False)} | "
            f"severity={severity} | "
            f"faults={len(faults)} | warnings={len(warnings)}"
        )
        return SnapshotSection(
            name="state_store",
            ok=ok,
            summary=summary,
            data=data,
        )
    def _build_mode_fsm_section(self, data: dict[str, Any]) -> SnapshotSection:
        mode = str(data.get("mode", "UNKNOWN"))
        ok = mode not in ("FAULT_LOCK", "SAFE_SHUTDOWN")
        summary = (
            f"mode={mode} | "
            f"system_running={data.get('system_running', False)} | "
            f"motion_allowed={data.get('motion_allowed', False)}"
        )
        return SnapshotSection(
            name="mode_fsm",
            ok=ok,
            summary=summary,
            data=data,
        )
    def _build_lifecycle_section(self, data: dict[str, Any]) -> SnapshotSection:
        lifecycle_state = str(data.get("lifecycle_state", "UNKNOWN"))
        ok = lifecycle_state not in ("FAULTED", "SHUTDOWN")
        summary = (
            f"lifecycle={lifecycle_state} | "
            f"active_mode={data.get('active_mode', 'UNKNOWN')} | "
            f"running={data.get('system_running', False)}"
        )
        return SnapshotSection(
            name="runtime_lifecycle",
            ok=ok,
            summary=summary,
            data=data,
        )
    def _build_safety_section(self, data: dict[str, Any]) -> SnapshotSection:
        level = str(data.get("level", "UNKNOWN"))
        ok = level not in ("FAULT", "CRITICAL", "SHUTDOWN")
        summary = (
            f"level={level} | "
            f"faults={len(data.get('faults', []))} | "
            f"warnings={len(data.get('warnings', []))} | "
            f"shutdown={data.get('request_shutdown', False)}"
        )
        return SnapshotSection(
            name="safety_supervisor",
            ok=ok,
            summary=summary,
            data=data,
        )
    def _build_watchdog_section(self, data: dict[str, Any]) -> SnapshotSection:
        severity = str(data.get("severity", "UNKNOWN"))
        ok = severity not in ("FAULT", "CRITICAL", "SHUTDOWN")
        summary = (
            f"severity={severity} | "
            f"faults={len(data.get('faults', []))} | "
            f"warnings={len(data.get('warnings', []))} | "
            f"shutdown={data.get('request_shutdown', False)}"
        )
        return SnapshotSection(
            name="watchdog_supervisor",
            ok=ok,
            summary=summary,
            data=data,
        )
    def _build_integration_section(self, data: dict[str, Any]) -> SnapshotSection:
        bridge_mode = str(data.get("bridge_mode", "UNKNOWN"))
        ok = bool(data.get("mapper_bound", False)) and bool(data.get("bridge_ready", False))
        summary = (
            f"profile={data.get('profile_name', 'UNKNOWN')} | "
            f"bridge_mode={bridge_mode} | "
            f"mapper_bound={data.get('mapper_bound', False)} | "
            f"bridge_ready={data.get('bridge_ready', False)}"
        )
        return SnapshotSection(
            name="hybrid_integration_manager",
            ok=ok,
            summary=summary,
            data=data,
        )
    def _build_stage2_section(self, data: dict[str, Any]) -> SnapshotSection:
        ok = (
            bool(data.get("telemetry_manager_ready", False))
            and bool(data.get("local_command_executor_ready", False))
            and bool(data.get("watchdog_supervisor_ready", False))
            and bool(data.get("safe_shutdown_manager_ready", False))
        )
        summary = (
            f"telemetry={data.get('telemetry_manager_ready', False)} | "
            f"local_executor={data.get('local_command_executor_ready', False)} | "
            f"watchdog={data.get('watchdog_supervisor_ready', False)} | "
            f"shutdown={data.get('safe_shutdown_manager_ready', False)}"
        )
        return SnapshotSection(
            name="runtime_wiring_stage2",
            ok=ok,
            summary=summary,
            data=data,
        )
    # --------------------------------------------------------
    # READERS
    # --------------------------------------------------------
    def _read_state_store(self) -> dict[str, Any]:
        if self.state_store is None:
            return {}
        if hasattr(self.state_store, "to_dict"):
            return dict(self.state_store.to_dict())
        return _to_plain_dict(self.state_store)
    def _read_mode_fsm(self) -> dict[str, Any]:
        if self.mode_fsm is None:
            return {}
        if hasattr(self.mode_fsm, "to_dict"):
            return dict(self.mode_fsm.to_dict())
        return _to_plain_dict(self.mode_fsm)
    def _read_lifecycle(self) -> dict[str, Any]:
        if self.runtime_lifecycle is None:
            return {}
        if hasattr(self.runtime_lifecycle, "to_dict"):
            return dict(self.runtime_lifecycle.to_dict())
        return _to_plain_dict(self.runtime_lifecycle)
    def _read_safety_supervisor(self) -> dict[str, Any]:
        if self.safety_supervisor is None:
            return {}
        if hasattr(self.safety_supervisor, "get_last_decision_dict"):
            return dict(self.safety_supervisor.get_last_decision_dict())
        return _to_plain_dict(self.safety_supervisor)
    def _read_watchdog(self) -> dict[str, Any]:
        if self.watchdog_supervisor is None:
            return {}
        if hasattr(self.watchdog_supervisor, "_last_decision") and self.watchdog_supervisor._last_decision is not None:
            d = self.watchdog_supervisor._last_decision
            return {
                "severity": d.severity.value,
                "warnings": list(d.warnings),
                "faults": list(d.faults),
                "request_shutdown": d.request_shutdown,
                "summary": d.summary,
            }
        return {}
    def _read_integration_manager(self) -> dict[str, Any]:
        if self.hybrid_integration_manager is None:
            return {}
        if hasattr(self.hybrid_integration_manager, "get_status_dict"):
            return dict(self.hybrid_integration_manager.get_status_dict())
        return _to_plain_dict(self.hybrid_integration_manager)
    def _read_stage2(self) -> dict[str, Any]:
        if self.runtime_wiring_stage2 is None:
            return {}
        if hasattr(self.runtime_wiring_stage2, "get_status_dict"):
            return dict(self.runtime_wiring_stage2.get_status_dict())
        return _to_plain_dict(self.runtime_wiring_stage2)
    # --------------------------------------------------------
    # SNAPSHOT BUILD
    # --------------------------------------------------------
    def build_snapshot(self) -> RemotePiRuntimeSnapshot:
        ok_state, state_store_data = _safe_call(self._read_state_store)
        ok_mode, mode_fsm_data = _safe_call(self._read_mode_fsm)
        ok_lifecycle, lifecycle_data = _safe_call(self._read_lifecycle)
        ok_safety, safety_data = _safe_call(self._read_safety_supervisor)
        ok_watchdog, watchdog_data = _safe_call(self._read_watchdog)
        ok_integration, integration_data = _safe_call(self._read_integration_manager)
        ok_stage2, stage2_data = _safe_call(self._read_stage2)
        state_store_data = _to_plain_dict(state_store_data)
        mode_fsm_data = _to_plain_dict(mode_fsm_data)
        lifecycle_data = _to_plain_dict(lifecycle_data)
        safety_data = _to_plain_dict(safety_data)
        watchdog_data = _to_plain_dict(watchdog_data)
        integration_data = _to_plain_dict(integration_data)
        stage2_data = _to_plain_dict(stage2_data)
        sections = [
            self._build_state_store_section(state_store_data),
            self._build_mode_fsm_section(mode_fsm_data),
            self._build_lifecycle_section(lifecycle_data),
            self._build_safety_section(safety_data),
            self._build_watchdog_section(watchdog_data),
            self._build_integration_section(integration_data),
            self._build_stage2_section(stage2_data),
        ]
        warnings: list[str] = []
        faults: list[str] = []
        warnings.extend(state_store_data.get("warnings", []))
        warnings.extend(safety_data.get("warnings", []))
        warnings.extend(watchdog_data.get("warnings", []))
        faults.extend(state_store_data.get("faults", []))
        faults.extend(safety_data.get("faults", []))
        faults.extend(watchdog_data.get("faults", []))
        warnings = list(dict.fromkeys(str(x) for x in warnings))
        faults = list(dict.fromkeys(str(x) for x in faults))
        overall_ok = all(section.ok for section in sections) and not faults
        overall_summary = " | ".join([
            f"overall_ok={overall_ok}",
            f"faults={len(faults)}",
            f"warnings={len(warnings)}",
            f"state={sections[0].summary}",
            f"fsm={sections[1].summary}",
            f"lifecycle={sections[2].summary}",
            f"safety={sections[3].summary}",
            f"watchdog={sections[4].summary}",
            f"integration={sections[5].summary}",
            f"stage2={sections[6].summary}",
        ])
        return RemotePiRuntimeSnapshot(
            created_ts=time.time(),
            overall_ok=overall_ok,
            overall_summary=overall_summary,
            state_store=state_store_data,
            mode_fsm=mode_fsm_data,
            lifecycle=lifecycle_data,
            safety_supervisor=safety_data,
            watchdog=watchdog_data,
            integration_manager=integration_data,
            stage2_wiring=stage2_data,
            warnings=warnings,
            faults=faults,
            sections=sections,
        )
    # --------------------------------------------------------
    # EXPORT VIEWS
    # --------------------------------------------------------
    def build_compact_snapshot(self) -> dict[str, Any]:
        snap = self.build_snapshot()
        return {
            "created_ts": snap.created_ts,
            "overall_ok": snap.overall_ok,
            "overall_summary": snap.overall_summary,
            "warnings": list(snap.warnings),
            "faults": list(snap.faults),
        }
    def build_service_snapshot(self) -> dict[str, Any]:
        snap = self.build_snapshot()
        return {
            "created_ts": snap.created_ts,
            "overall_ok": snap.overall_ok,
            "overall_summary": snap.overall_summary,
            "state_store": snap.state_store,
            "mode_fsm": snap.mode_fsm,
            "lifecycle": snap.lifecycle,
            "safety_supervisor": snap.safety_supervisor,
            "watchdog": snap.watchdog,
            "integration_manager": snap.integration_manager,
            "stage2_wiring": snap.stage2_wiring,
            "warnings": list(snap.warnings),
            "faults": list(snap.faults),
            "sections": [asdict(section) for section in snap.sections],
        }


# ============================================================
# MODULE-R038
# ============================================================

# runtime/remotepi_hardware_runtime_bridge.py
"""
MODULE-R038
RemotePi Hardware Runtime Bridge
--------------------------------

Purpose:
    Bridge normalized runtime commands and telemetry requests to actual
    RemotePi hardware adapters.

Responsibilities:
    - Read joystick / ADC / thermal / battery inputs
    - Execute normalized runtime commands on hardware
    - Provide safe hardware abstraction for Stage-2 and future runtime layers
    - Support both legacy HardwareManager-style adapters and future dedicated adapters

Design goals:
    - Non-invasive transition from legacy HMI hardware layer
    - Explicit adapter interfaces
    - Safe fallback behavior
"""
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional
# ============================================================
# DATA MODELS
# ============================================================
@dataclass
class HardwareBridgeConfig:
    joystick_scale_divisor: float = 100.0
    adc_default_battery_voltage: float = 24.0
    adc_default_local_temp_c: float = 28.0
    adc_default_battery_temp_c: float = 29.0
    emit_status_logs: bool = True
@dataclass
class HardwareSnapshot:
    ts: float
    left_x: float = 0.0
    left_y: float = 0.0
    right_x: float = 0.0
    right_y: float = 0.0
    left_button_pressed: bool = False
    right_button_pressed: bool = False
    battery_voltage: float = 0.0
    local_temp_c: float = 0.0
    battery_temp_c: float = 0.0
    fan_active: bool = False
    buzzer_active: bool = False
    parking_light_on: bool = False
    low_beam_on: bool = False
    high_beam_on: bool = False
    signal_lhr_on: bool = False
    rig_floor_light_on: bool = False
    rotation_light_on: bool = False
# ============================================================
# MAIN CLASS
# ============================================================
class RemotePiHardwareRuntimeBridge:
    def __init__(
        self,
        *,
        legacy_hw=None,
        adc_reader: Optional[Callable[[str], float]] = None,
        gpio_writer: Optional[Callable[[str, bool], None]] = None,
        gpio_reader: Optional[Callable[[str], bool]] = None,
        status_sink: Optional[Callable[[str, dict], None]] = None,
        config: Optional[HardwareBridgeConfig] = None,
    ):
        """
        legacy_hw:
            Existing HardwareManager-like object with methods such as:
                - read_joystick(side, axis)
                - read_left_joystick_button()
                - read_right_joystick_button()
                - set_servo(angle)
                - set_motor_driver(speed, engine_sound_enabled=True)
                - set_drawworks_motor(speed, engine_sound_enabled=True)
                - set_sandline_motor(speed, engine_sound_enabled=True)
                - set_winch_motor(speed, engine_sound_enabled=True)
                - set_rotary_motor(speed, engine_sound_enabled=True)
                - set_signal_mode(enabled)
                - set_parking_light(enabled)
                - set_low_beam_light(enabled)
                - set_high_beam_light(enabled)
                - set_rig_floor_light(enabled)
                - set_rotation_light(enabled)
                - stop_all_outputs()
        adc_reader(channel_name) -> float:
            Optional future ADS1115-style reader.
        gpio_writer(name, state) -> None:
            Optional generic runtime GPIO writer.
        gpio_reader(name) -> bool:
            Optional generic runtime GPIO reader.
        """
        self.legacy_hw = legacy_hw
        self.adc_reader = adc_reader
        self.gpio_writer = gpio_writer
        self.gpio_reader = gpio_reader
        self.status_sink = status_sink
        self.config = config or HardwareBridgeConfig()
        self._fan_active = False
        self._buzzer_active = False
        self._parking_light_on = False
        self._low_beam_on = False
        self._high_beam_on = False
        self._signal_lhr_on = False
        self._rig_floor_light_on = False
        self._rotation_light_on = False
    # --------------------------------------------------------
    # INTERNAL
    # --------------------------------------------------------
    def _emit_status(self, topic: str, **payload) -> None:
        if not self.config.emit_status_logs:
            return
        if self.status_sink is not None:
            self.status_sink(topic, {
                "ts": time.time(),
                **payload,
            })
    def _safe_call(self, fn: Callable, *args, default=None, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            self._emit_status(
                "hardware_bridge/call_error",
                function=getattr(fn, "__name__", str(fn)),
                error=str(exc),
            )
            return default
    # --------------------------------------------------------
    # INPUT READS
    # --------------------------------------------------------
    def read_joystick_axis(self, side: str, axis: str) -> float:
        side = str(side).upper()
        axis = str(axis).upper()
        if self.legacy_hw is not None and hasattr(self.legacy_hw, "read_joystick"):
            raw = self._safe_call(self.legacy_hw.read_joystick, side, axis, default=0.0)
            try:
                return float(raw) / float(self.config.joystick_scale_divisor)
            except Exception:
                return 0.0
        return 0.0
    def read_left_button(self) -> bool:
        if self.legacy_hw is not None and hasattr(self.legacy_hw, "read_left_joystick_button"):
            return bool(self._safe_call(self.legacy_hw.read_left_joystick_button, default=False))
        return False
    def read_right_button(self) -> bool:
        if self.legacy_hw is not None and hasattr(self.legacy_hw, "read_right_joystick_button"):
            return bool(self._safe_call(self.legacy_hw.read_right_joystick_button, default=False))
        return False
    def read_adc(self, channel_name: str) -> float:
        if self.adc_reader is not None:
            val = self._safe_call(self.adc_reader, channel_name, default=None)
            if val is not None:
                try:
                    return float(val)
                except Exception:
                    pass
        defaults = {
            "BATTERY_VOLTAGE_SENSE": self.config.adc_default_battery_voltage,
            "LM35_TEMP": self.config.adc_default_local_temp_c,
            "NTC_BATTERY_TEMP": self.config.adc_default_battery_temp_c,
        }
        return float(defaults.get(channel_name, 0.0))
    # --------------------------------------------------------
    # OUTPUT WRITES - GENERIC
    # --------------------------------------------------------
    def write_gpio(self, name: str, state: bool) -> None:
        if self.gpio_writer is not None:
            self._safe_call(self.gpio_writer, name, bool(state), default=None)
    # --------------------------------------------------------
    # LIGHTS / OUTPUTS
    # --------------------------------------------------------
    def set_remote_fan(self, state: bool) -> None:
        self._fan_active = bool(state)
        self.write_gpio("REMOTE_FAN_CTRL", state)
    def set_remote_buzzer(self, state: bool) -> None:
        self._buzzer_active = bool(state)
        self.write_gpio("REMOTE_BUZZER_CTRL", state)
    def set_parking_light(self, state: bool) -> None:
        self._parking_light_on = bool(state)
        if self.legacy_hw is not None and hasattr(self.legacy_hw, "set_parking_light"):
            self._safe_call(self.legacy_hw.set_parking_light, bool(state), default=None)
        else:
            self.write_gpio("PARKING_LIGHT", state)
    def set_low_beam_light(self, state: bool) -> None:
        self._low_beam_on = bool(state)
        if self.legacy_hw is not None and hasattr(self.legacy_hw, "set_low_beam_light"):
            self._safe_call(self.legacy_hw.set_low_beam_light, bool(state), default=None)
        else:
            self.write_gpio("LOW_BEAM_LIGHT", state)
    def set_high_beam_light(self, state: bool) -> None:
        self._high_beam_on = bool(state)
        if self.legacy_hw is not None and hasattr(self.legacy_hw, "set_high_beam_light"):
            self._safe_call(self.legacy_hw.set_high_beam_light, bool(state), default=None)
        else:
            self.write_gpio("HIGH_BEAM_LIGHT", state)
    def set_signal_lhr_light(self, state: bool) -> None:
        self._signal_lhr_on = bool(state)
        if self.legacy_hw is not None and hasattr(self.legacy_hw, "set_signal_mode"):
            self._safe_call(self.legacy_hw.set_signal_mode, bool(state), default=None)
        else:
            self.write_gpio("SIGNAL_LHR_LIGHT", state)
    def set_rig_floor_light(self, state: bool) -> None:
        self._rig_floor_light_on = bool(state)
        if self.legacy_hw is not None and hasattr(self.legacy_hw, "set_rig_floor_light"):
            self._safe_call(self.legacy_hw.set_rig_floor_light, bool(state), default=None)
        else:
            self.write_gpio("RIG_FLOOR_LIGHT", state)
    def set_rotation_light(self, state: bool) -> None:
        self._rotation_light_on = bool(state)
        if self.legacy_hw is not None and hasattr(self.legacy_hw, "set_rotation_light"):
            self._safe_call(self.legacy_hw.set_rotation_light, bool(state), default=None)
        else:
            self.write_gpio("ROTATION_LIGHT", state)
    # --------------------------------------------------------
    # MOTION / SERVO / MOTOR CONTROL
    # --------------------------------------------------------
    def set_wheel_servo(self, value: float) -> None:
        if self.legacy_hw is not None and hasattr(self.legacy_hw, "set_servo"):
            # Legacy path appears angle-like; for now pass through scaled value
            self._safe_call(self.legacy_hw.set_servo, value, default=None)
    def set_driver_motor(self, value: float, engine_sound_enabled: bool = True) -> None:
        if self.legacy_hw is not None and hasattr(self.legacy_hw, "set_motor_driver"):
            self._safe_call(
                self.legacy_hw.set_motor_driver,
                value,
                engine_sound_enabled=bool(engine_sound_enabled),
                default=None,
            )
    def set_drawworks_motor(self, value: float, engine_sound_enabled: bool = True) -> None:
        if self.legacy_hw is not None and hasattr(self.legacy_hw, "set_drawworks_motor"):
            self._safe_call(
                self.legacy_hw.set_drawworks_motor,
                value,
                engine_sound_enabled=bool(engine_sound_enabled),
                default=None,
            )
    def set_sandline_motor(self, value: float, engine_sound_enabled: bool = True) -> None:
        if self.legacy_hw is not None and hasattr(self.legacy_hw, "set_sandline_motor"):
            self._safe_call(
                self.legacy_hw.set_sandline_motor,
                value,
                engine_sound_enabled=bool(engine_sound_enabled),
                default=None,
            )
    def set_winch_motor(self, value: float, engine_sound_enabled: bool = True) -> None:
        if self.legacy_hw is not None and hasattr(self.legacy_hw, "set_winch_motor"):
            self._safe_call(
                self.legacy_hw.set_winch_motor,
                value,
                engine_sound_enabled=bool(engine_sound_enabled),
                default=None,
            )
    def set_rotary_motor(self, value: float, engine_sound_enabled: bool = True) -> None:
        if self.legacy_hw is not None and hasattr(self.legacy_hw, "set_rotary_motor"):
            self._safe_call(
                self.legacy_hw.set_rotary_motor,
                value,
                engine_sound_enabled=bool(engine_sound_enabled),
                default=None,
            )
    def stop_all_outputs(self) -> None:
        self._fan_active = False
        self._buzzer_active = False
        self._parking_light_on = False
        self._low_beam_on = False
        self._high_beam_on = False
        self._signal_lhr_on = False
        self._rig_floor_light_on = False
        self._rotation_light_on = False
        if self.legacy_hw is not None and hasattr(self.legacy_hw, "stop_all_outputs"):
            self._safe_call(self.legacy_hw.stop_all_outputs, default=None)
        # Generic fallback
        self.write_gpio("REMOTE_FAN_CTRL", False)
        self.write_gpio("REMOTE_BUZZER_CTRL", False)
        self.write_gpio("PARKING_LIGHT", False)
        self.write_gpio("LOW_BEAM_LIGHT", False)
        self.write_gpio("HIGH_BEAM_LIGHT", False)
        self.write_gpio("SIGNAL_LHR_LIGHT", False)
        self.write_gpio("RIG_FLOOR_LIGHT", False)
        self.write_gpio("ROTATION_LIGHT", False)
    # --------------------------------------------------------
    # NORMALIZED COMMAND ENTRY
    # --------------------------------------------------------
    def execute_runtime_command(self, command_name: str, payload: Optional[dict] = None) -> None:
        payload = payload or {}
        cmd = str(command_name)
        self._emit_status(
            "hardware_bridge/command_received",
            command_name=cmd,
            payload=payload,
        )
        # Lights
        if cmd == "CMD_LIGHT_PARKING_TOGGLE":
            self.set_parking_light(bool(payload.get("state", not self._parking_light_on)))
            return
        if cmd == "CMD_LIGHT_LOW_BEAM_TOGGLE":
            self.set_low_beam_light(bool(payload.get("state", not self._low_beam_on)))
            return
        if cmd == "CMD_LIGHT_HIGH_BEAM_TOGGLE":
            self.set_high_beam_light(bool(payload.get("state", not self._high_beam_on)))
            return
        if cmd == "CMD_LIGHT_SIGNAL_LHR_TOGGLE":
            self.set_signal_lhr_light(bool(payload.get("state", not self._signal_lhr_on)))
            return
        if cmd == "CMD_LIGHT_RIG_FLOOR_TOGGLE":
            self.set_rig_floor_light(bool(payload.get("state", not self._rig_floor_light_on)))
            return
        if cmd == "CMD_LIGHT_ROTATION_TOGGLE":
            self.set_rotation_light(bool(payload.get("state", not self._rotation_light_on)))
            return
        # Motion
        if cmd == "CMD_JOYSTICK_LEFT_UPDATE":
            mode = str(payload.get("mode", ""))
            x = float(payload.get("x", 0.0))
            y = float(payload.get("y", 0.0))
            engine_sound_enabled = bool(payload.get("engine_sound_enabled", True))
            if mode in ("STATE_CONTROL_MODE_WHEEL", "WHEEL", "MANUAL_CONTROL"):
                self.set_wheel_servo(x)
                return
            if mode in ("STATE_CONTROL_MODE_SANDLINE", "SANDLINE"):
                self.set_sandline_motor(y, engine_sound_enabled=engine_sound_enabled)
                return
            if mode in ("STATE_CONTROL_MODE_WINCH", "WINCH"):
                self.set_winch_motor(x, engine_sound_enabled=engine_sound_enabled)
                return
            if mode in ("STATE_CONTROL_MODE_ROTARY_TABLE", "ROTARY TABLE"):
                self.set_rotary_motor(y, engine_sound_enabled=engine_sound_enabled)
                return
            return
        if cmd == "CMD_JOYSTICK_RIGHT_UPDATE":
            mode = str(payload.get("mode", ""))
            y = float(payload.get("y", 0.0))
            engine_sound_enabled = bool(payload.get("engine_sound_enabled", True))
            if mode in ("STATE_CONTROL_MODE_DRIVER", "DRIVER"):
                self.set_driver_motor(y, engine_sound_enabled=engine_sound_enabled)
                return
            if mode in ("STATE_CONTROL_MODE_DRAWWORKS", "DRAWWORKS"):
                self.set_drawworks_motor(y, engine_sound_enabled=engine_sound_enabled)
                return
            return
        # Local executor style
        if cmd == "CMD_REMOTE_FAN_ON":
            self.set_remote_fan(True)
            return
        if cmd == "CMD_REMOTE_FAN_OFF":
            self.set_remote_fan(False)
            return
        if cmd in ("CMD_BUZZER_WARNING", "CMD_BUZZER_FAULT", "CMD_BUZZER_CRITICAL", "CMD_BUZZER_BUTTON_ACK", "CMD_BUZZER_BOOT_OK"):
            # Remote buzzer here only tracks generic state. Tone/pattern implementation can stay in local executor.
            self.set_remote_buzzer(True)
            return
        if cmd == "CMD_SYSTEM_STOP":
            self.stop_all_outputs()
            return
        self._emit_status(
            "hardware_bridge/command_unhandled",
            command_name=cmd,
        )
    # --------------------------------------------------------
    # SNAPSHOT
    # --------------------------------------------------------
    def build_snapshot(self) -> HardwareSnapshot:
        return HardwareSnapshot(
            ts=time.time(),
            left_x=self.read_joystick_axis("LEFT", "X"),
            left_y=self.read_joystick_axis("LEFT", "Y"),
            right_x=self.read_joystick_axis("RIGHT", "X"),
            right_y=self.read_joystick_axis("RIGHT", "Y"),
            left_button_pressed=self.read_left_button(),
            right_button_pressed=self.read_right_button(),
            battery_voltage=self.read_adc("BATTERY_VOLTAGE_SENSE"),
            local_temp_c=self.read_adc("LM35_TEMP"),
            battery_temp_c=self.read_adc("NTC_BATTERY_TEMP"),
            fan_active=self._fan_active,
            buzzer_active=self._buzzer_active,
            parking_light_on=self._parking_light_on,
            low_beam_on=self._low_beam_on,
            high_beam_on=self._high_beam_on,
            signal_lhr_on=self._signal_lhr_on,
            rig_floor_light_on=self._rig_floor_light_on,
            rotation_light_on=self._rotation_light_on,
        )
    def to_dict(self) -> dict[str, Any]:
        snap = self.build_snapshot()
        return {
            "ts": snap.ts,
            "left_x": snap.left_x,
            "left_y": snap.left_y,
            "right_x": snap.right_x,
            "right_y": snap.right_y,
            "left_button_pressed": snap.left_button_pressed,
            "right_button_pressed": snap.right_button_pressed,
            "battery_voltage": snap.battery_voltage,
            "local_temp_c": snap.local_temp_c,
            "battery_temp_c": snap.battery_temp_c,
            "fan_active": snap.fan_active,
            "buzzer_active": snap.buzzer_active,
            "parking_light_on": snap.parking_light_on,
            "low_beam_on": snap.low_beam_on,
            "high_beam_on": snap.high_beam_on,
            "signal_lhr_on": snap.signal_lhr_on,
            "rig_floor_light_on": snap.rig_floor_light_on,
            "rotation_light_on": snap.rotation_light_on,
        }


# ============================================================
# MODULE-R039
# ============================================================

# runtime/remotepi_link_orchestration_manager.py
"""
MODULE-R039
RemotePi Link Orchestration Manager
-----------------------------------

Purpose:
    Manage the runtime communication link between RemotePi and MasterPi.

Responsibilities:
    - Track link connectivity state
    - Handle heartbeat freshness
    - Detect RX/TX silence and communication degradation
    - Drive reconnect attempts with backoff
    - Mirror link state into RemotePiStateStore
    - Escalate link failures into safety / lifecycle friendly signals

Design goals:
    - Transport-agnostic
    - Deterministic state transitions
    - Safe defaults
"""
import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional
# ============================================================
# ENUMS
# ============================================================
class LinkState(str, Enum):
    DOWN = "DOWN"
    CONNECTING = "CONNECTING"
    UP = "UP"
    DEGRADED = "DEGRADED"
    LOST = "LOST"
# ============================================================
# DATA MODELS
# ============================================================
@dataclass
class LinkOrchestrationConfig:
    rx_timeout_sec: float = 3.0
    tx_timeout_sec: float = 3.0
    degraded_after_sec: float = 1.5
    reconnect_initial_backoff_sec: float = 1.0
    reconnect_max_backoff_sec: float = 10.0
    emit_status_logs: bool = True
@dataclass
class LinkSnapshot:
    ts: float
    state: LinkState
    connected: bool
    master_link_ok: bool
    last_rx_ts: float
    last_tx_ts: float
    reconnect_count: int
    last_error: Optional[str]
    summary: str
# ============================================================
# MAIN CLASS
# ============================================================
class RemotePiLinkOrchestrationManager:
    def __init__(
        self,
        *,
        state_store=None,
        runtime_lifecycle=None,
        safety_supervisor=None,
        transport_connect: Optional[Callable[[], bool]] = None,
        transport_disconnect: Optional[Callable[[], None]] = None,
        transport_is_connected: Optional[Callable[[], bool]] = None,
        transport_send_heartbeat: Optional[Callable[[], bool]] = None,
        status_sink: Optional[Callable[[str, dict], None]] = None,
        config: Optional[LinkOrchestrationConfig] = None,
    ):
        self.state_store = state_store
        self.runtime_lifecycle = runtime_lifecycle
        self.safety_supervisor = safety_supervisor
        self.transport_connect = transport_connect or (lambda: True)
        self.transport_disconnect = transport_disconnect or (lambda: None)
        self.transport_is_connected = transport_is_connected or (lambda: True)
        self.transport_send_heartbeat = transport_send_heartbeat or (lambda: True)
        self.status_sink = status_sink
        self.config = config or LinkOrchestrationConfig()
        self._state = LinkState.DOWN
        self._connected = False
        self._master_link_ok = False
        self._last_rx_ts = 0.0
        self._last_tx_ts = 0.0
        self._last_error: Optional[str] = None
        self._reconnect_count = 0
        self._next_reconnect_ts = 0.0
        self._current_backoff_sec = self.config.reconnect_initial_backoff_sec
        self._touch_state_store()
    # --------------------------------------------------------
    # INTERNAL
    # --------------------------------------------------------
    def _emit_status(self, topic: str, **payload) -> None:
        if not self.config.emit_status_logs:
            return
        if self.status_sink is not None:
            self.status_sink(topic, {
                "ts": time.time(),
                **payload,
            })
    def _set_state(self, state: LinkState, summary: str = "") -> None:
        self._state = state
        self._touch_state_store()
        self._emit_status(
            "link_orchestrator/state_changed",
            state=state.value,
            connected=self._connected,
            master_link_ok=self._master_link_ok,
            reconnect_count=self._reconnect_count,
            summary=summary,
        )
    def _touch_state_store(self) -> None:
        if self.state_store is None:
            return
        try:
            if hasattr(self.state_store, "update_network"):
                self.state_store.update_network(
                    wifi_connected=self._connected,
                    bluetooth_connected=False,
                    ethernet_link=False,
                    master_link_ok=self._master_link_ok,
                    network_online=self._connected,
                    network_weak=(self._state == LinkState.DEGRADED),
                )
        except Exception as exc:
            self._emit_status("link_orchestrator/state_store_error", error=str(exc))
    def _schedule_reconnect(self) -> None:
        self._reconnect_count += 1
        self._next_reconnect_ts = time.time() + self._current_backoff_sec
        self._current_backoff_sec = min(
            self._current_backoff_sec * 2.0,
            self.config.reconnect_max_backoff_sec,
        )
    def _reset_reconnect_backoff(self) -> None:
        self._current_backoff_sec = self.config.reconnect_initial_backoff_sec
        self._next_reconnect_ts = 0.0
    # --------------------------------------------------------
    # TRANSPORT EVENTS
    # --------------------------------------------------------
    def note_rx(self) -> None:
        self._last_rx_ts = time.time()
        self._connected = True
        self._master_link_ok = True
        if self._state in (LinkState.DOWN, LinkState.CONNECTING, LinkState.DEGRADED, LinkState.LOST):
            self._set_state(LinkState.UP, "RX received, link healthy.")
        else:
            self._touch_state_store()
    def note_tx(self) -> None:
        self._last_tx_ts = time.time()
        self._connected = True
        self._touch_state_store()
    def note_error(self, error_text: str) -> None:
        self._last_error = str(error_text)
        self._connected = False
        self._master_link_ok = False
        self._set_state(LinkState.LOST, f"Transport error: {error_text}")
        self._schedule_reconnect()
    # --------------------------------------------------------
    # CONNECTION CONTROL
    # --------------------------------------------------------
    def connect(self) -> bool:
        self._set_state(LinkState.CONNECTING, "Attempting connection.")
        try:
            ok = bool(self.transport_connect())
        except Exception as exc:
            self._last_error = str(exc)
            ok = False
        if ok:
            self._connected = True
            self._master_link_ok = True
            now = time.time()
            self._last_rx_ts = now
            self._last_tx_ts = now
            self._reset_reconnect_backoff()
            self._set_state(LinkState.UP, "Transport connected.")
            return True
        self._connected = False
        self._master_link_ok = False
        self._set_state(LinkState.DOWN, "Transport connect failed.")
        self._schedule_reconnect()
        return False
    def disconnect(self) -> None:
        try:
            self.transport_disconnect()
        except Exception as exc:
            self._last_error = str(exc)
        self._connected = False
        self._master_link_ok = False
        self._set_state(LinkState.DOWN, "Transport disconnected.")
        self._schedule_reconnect()
    # --------------------------------------------------------
    # HEARTBEAT / STATE LOGIC
    # --------------------------------------------------------
    def _update_from_transport_connected(self) -> None:
        try:
            connected = bool(self.transport_is_connected())
        except Exception as exc:
            self._last_error = str(exc)
            connected = False
        if not connected:
            self._connected = False
            self._master_link_ok = False
            if self._state not in (LinkState.DOWN, LinkState.LOST):
                self._set_state(LinkState.LOST, "Transport connection lost.")
            self._schedule_reconnect()
            return
        self._connected = True
    def _evaluate_freshness(self) -> None:
        now = time.time()
        rx_age = now - self._last_rx_ts if self._last_rx_ts > 0 else float("inf")
        tx_age = now - self._last_tx_ts if self._last_tx_ts > 0 else float("inf")
        if rx_age > self.config.rx_timeout_sec:
            self._master_link_ok = False
            self._set_state(LinkState.LOST, f"RX timeout ({rx_age:.2f}s).")
            self._schedule_reconnect()
            return
        if rx_age > self.config.degraded_after_sec or tx_age > self.config.degraded_after_sec:
            self._master_link_ok = True
            if self._state != LinkState.DEGRADED:
                self._set_state(LinkState.DEGRADED, "Link freshness degraded.")
            return
        self._master_link_ok = True
        if self._state != LinkState.UP:
            self._set_state(LinkState.UP, "Link healthy.")
    def _maybe_send_heartbeat(self) -> None:
        now = time.time()
        tx_age = now - self._last_tx_ts if self._last_tx_ts > 0 else float("inf")
        if tx_age < self.config.tx_timeout_sec:
            return
        try:
            ok = bool(self.transport_send_heartbeat())
        except Exception as exc:
            self.note_error(f"heartbeat_send_exception: {exc}")
            return
        if ok:
            self.note_tx()
        else:
            self.note_error("heartbeat_send_failed")
    def _maybe_reconnect(self) -> None:
        now = time.time()
        if now < self._next_reconnect_ts:
            return
        self.connect()
    # --------------------------------------------------------
    # SAFETY / LIFECYCLE SIDE EFFECTS
    # --------------------------------------------------------
    def _apply_runtime_side_effects(self) -> None:
        if self._state in (LinkState.LOST, LinkState.DOWN):
            if self.runtime_lifecycle is not None:
                try:
                    self.runtime_lifecycle.enter_fault("Link lost / disconnected.")
                except Exception as exc:
                    self._emit_status("link_orchestrator/lifecycle_error", error=str(exc))
        elif self._state == LinkState.DEGRADED:
            # degraded: lifecycle zorla fault'a atılmaz, state store network_weak yeterli
            pass
    # --------------------------------------------------------
    # TICK
    # --------------------------------------------------------
    def tick(self) -> None:
        if self._state in (LinkState.DOWN, LinkState.LOST):
            self._maybe_reconnect()
            self._touch_state_store()
            return
        self._update_from_transport_connected()
        if not self._connected:
            self._touch_state_store()
            self._apply_runtime_side_effects()
            return
        self._maybe_send_heartbeat()
        self._evaluate_freshness()
        self._touch_state_store()
        self._apply_runtime_side_effects()
    # --------------------------------------------------------
    # ACCESSORS
    # --------------------------------------------------------
    @property
    def state(self) -> LinkState:
        return self._state
    def snapshot(self) -> LinkSnapshot:
        return LinkSnapshot(
            ts=time.time(),
            state=self._state,
            connected=self._connected,
            master_link_ok=self._master_link_ok,
            last_rx_ts=self._last_rx_ts,
            last_tx_ts=self._last_tx_ts,
            reconnect_count=self._reconnect_count,
            last_error=self._last_error,
            summary=(
                f"state={self._state.value} | "
                f"connected={self._connected} | "
                f"master_link_ok={self._master_link_ok} | "
                f"reconnect_count={self._reconnect_count}"
            ),
        )
    def to_dict(self) -> dict:
        snap = self.snapshot()
        return {
            "ts": snap.ts,
            "state": snap.state.value,
            "connected": snap.connected,
            "master_link_ok": snap.master_link_ok,
            "last_rx_ts": snap.last_rx_ts,
            "last_tx_ts": snap.last_tx_ts,
            "reconnect_count": snap.reconnect_count,
            "last_error": snap.last_error,
            "summary": snap.summary,
        }


# ============================================================
# MODULE-R040
# ============================================================

# runtime/remotepi_command_transport.py
"""
MODULE-R040
RemotePi Command Transport
--------------------------

Purpose:
    Transport-agnostic command/event exchange layer for RemotePi runtime.

Responsibilities:
    - Provide a unified transport interface
    - Send normalized command payloads outward
    - Receive inbound payloads and normalize them
    - Support integration with link orchestration manager
    - Remain transport-agnostic for MQTT / socket / serial adapters

Design goals:
    - Safe fallback behavior
    - Explicit connect/disconnect/send/poll API
    - Minimal assumptions about underlying transport
"""
import json
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Optional
# ============================================================
# ENUMS
# ============================================================
class TransportState(str, Enum):
    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    ERROR = "ERROR"
# ============================================================
# DATA MODELS
# ============================================================
@dataclass
class CommandTransportConfig:
    emit_status_logs: bool = True
    auto_json_encode: bool = True
    auto_json_decode: bool = True
@dataclass
class TransportSnapshot:
    ts: float
    state: TransportState
    connected: bool
    last_tx_ts: float
    last_rx_ts: float
    tx_count: int
    rx_count: int
    last_error: Optional[str]
    summary: str
# ============================================================
# MAIN CLASS
# ============================================================
class RemotePiCommandTransport:
    def __init__(
        self,
        *,
        connect_fn: Optional[Callable[[], bool]] = None,
        disconnect_fn: Optional[Callable[[], None]] = None,
        is_connected_fn: Optional[Callable[[], bool]] = None,
        send_fn: Optional[Callable[[str], bool]] = None,
        poll_fn: Optional[Callable[[], Optional[str]]] = None,
        inbound_sink: Optional[Callable[[str, dict], None]] = None,
        status_sink: Optional[Callable[[str, dict], None]] = None,
        config: Optional[CommandTransportConfig] = None,
    ):
        """
        connect_fn() -> bool
        disconnect_fn() -> None
        is_connected_fn() -> bool
        send_fn(raw_text:str) -> bool
        poll_fn() -> Optional[str]
            returns one raw inbound frame/message or None
        inbound_sink(message_type, payload)
            normalized inbound dispatch target
        """
        self.connect_fn = connect_fn or (lambda: True)
        self.disconnect_fn = disconnect_fn or (lambda: None)
        self.is_connected_fn = is_connected_fn or (lambda: True)
        self.send_fn = send_fn or (lambda raw: True)
        self.poll_fn = poll_fn or (lambda: None)
        self.inbound_sink = inbound_sink
        self.status_sink = status_sink
        self.config = config or CommandTransportConfig()
        self._state = TransportState.DISCONNECTED
        self._last_tx_ts = 0.0
        self._last_rx_ts = 0.0
        self._tx_count = 0
        self._rx_count = 0
        self._last_error: Optional[str] = None
    # --------------------------------------------------------
    # INTERNAL
    # --------------------------------------------------------
    def _emit_status(self, topic: str, **payload) -> None:
        if not self.config.emit_status_logs:
            return
        if self.status_sink is not None:
            self.status_sink(topic, {
                "ts": time.time(),
                **payload,
            })
    def _set_state(self, state: TransportState, summary: str = "") -> None:
        self._state = state
        self._emit_status(
            "command_transport/state_changed",
            state=state.value,
            summary=summary,
        )
    def _encode_outbound(self, message_type: str, payload: dict) -> str:
        frame = {
            "ts": time.time(),
            "type": str(message_type),
            "payload": dict(payload),
        }
        if self.config.auto_json_encode:
            return json.dumps(frame, ensure_ascii=False)
        return str(frame)
    def _decode_inbound(self, raw: str) -> tuple[str, dict]:
        if self.config.auto_json_decode:
            obj = json.loads(raw)
            return str(obj.get("type", "UNKNOWN")), dict(obj.get("payload", {}))
        return "RAW", {"raw": raw}
    # --------------------------------------------------------
    # CONNECTION
    # --------------------------------------------------------
    def connect(self) -> bool:
        self._set_state(TransportState.CONNECTING, "Connecting transport.")
        try:
            ok = bool(self.connect_fn())
        except Exception as exc:
            self._last_error = str(exc)
            self._set_state(TransportState.ERROR, f"connect exception: {exc}")
            return False
        if ok:
            self._set_state(TransportState.CONNECTED, "Transport connected.")
            return True
        self._set_state(TransportState.DISCONNECTED, "Transport connect failed.")
        return False
    def disconnect(self) -> None:
        try:
            self.disconnect_fn()
        except Exception as exc:
            self._last_error = str(exc)
            self._set_state(TransportState.ERROR, f"disconnect exception: {exc}")
            return
        self._set_state(TransportState.DISCONNECTED, "Transport disconnected.")
    def is_connected(self) -> bool:
        try:
            return bool(self.is_connected_fn())
        except Exception as exc:
            self._last_error = str(exc)
            self._set_state(TransportState.ERROR, f"is_connected exception: {exc}")
            return False
    # --------------------------------------------------------
    # SEND / RECEIVE
    # --------------------------------------------------------
    def send_command(self, command_name: str, payload: Optional[dict] = None) -> bool:
        payload = payload or {}
        raw = self._encode_outbound(command_name, payload)
        try:
            ok = bool(self.send_fn(raw))
        except Exception as exc:
            self._last_error = str(exc)
            self._set_state(TransportState.ERROR, f"send exception: {exc}")
            return False
        if ok:
            self._tx_count += 1
            self._last_tx_ts = time.time()
            self._emit_status(
                "command_transport/tx",
                command_name=command_name,
                payload=payload,
            )
            return True
        self._last_error = "send_fn returned False"
        self._set_state(TransportState.ERROR, "Outbound send failed.")
        return False
    def poll_once(self) -> bool:
        try:
            raw = self.poll_fn()
        except Exception as exc:
            self._last_error = str(exc)
            self._set_state(TransportState.ERROR, f"poll exception: {exc}")
            return False
        if not raw:
            return False
        try:
            message_type, payload = self._decode_inbound(raw)
        except Exception as exc:
            self._last_error = str(exc)
            self._emit_status(
                "command_transport/rx_decode_error",
                raw=raw,
                error=str(exc),
            )
            return False
        self._rx_count += 1
        self._last_rx_ts = time.time()
        self._emit_status(
            "command_transport/rx",
            message_type=message_type,
            payload=payload,
        )
        if self.inbound_sink is not None:
            try:
                self.inbound_sink(message_type, payload)
            except Exception as exc:
                self._last_error = str(exc)
                self._emit_status(
                    "command_transport/inbound_sink_error",
                    message_type=message_type,
                    error=str(exc),
                )
                return False
        return True
    # --------------------------------------------------------
    # HEARTBEAT
    # --------------------------------------------------------
    def send_heartbeat(self) -> bool:
        return self.send_command("HEARTBEAT", {"alive": True})
    # --------------------------------------------------------
    # SNAPSHOT
    # --------------------------------------------------------
    @property
    def state(self) -> TransportState:
        return self._state
    def snapshot(self) -> TransportSnapshot:
        connected = self.is_connected() if self._state != TransportState.ERROR else False
        return TransportSnapshot(
            ts=time.time(),
            state=self._state,
            connected=connected,
            last_tx_ts=self._last_tx_ts,
            last_rx_ts=self._last_rx_ts,
            tx_count=self._tx_count,
            rx_count=self._rx_count,
            last_error=self._last_error,
            summary=(
                f"state={self._state.value} | "
                f"connected={connected} | "
                f"tx={self._tx_count} | "
                f"rx={self._rx_count}"
            ),
        )
    def to_dict(self) -> dict:
        snap = self.snapshot()
        return {
            "ts": snap.ts,
            "state": snap.state.value,
            "connected": snap.connected,
            "last_tx_ts": snap.last_tx_ts,
            "last_rx_ts": snap.last_rx_ts,
            "tx_count": snap.tx_count,
            "rx_count": snap.rx_count,
            "last_error": snap.last_error,
            "summary": snap.summary,
        }


# ============================================================
# MODULE-R041
# ============================================================

# runtime/remotepi_startup_orchestrator.py
"""
MODULE-R041
RemotePi Startup Orchestrator
-----------------------------

Purpose:
    Deterministic startup sequence manager for RemotePi runtime.

Responsibilities:
    - Bring runtime modules up in a controlled order
    - Perform dependency checks
    - Coordinate boot -> ready transition
    - Record startup phases and failures
    - Keep startup side effects centralized

Design goals:
    - Explicit startup phases
    - Safe failure handling
    - Compatible with partial deployments
"""
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional
# ============================================================
# ENUMS
# ============================================================
class StartupPhase(str, Enum):
    INIT = "INIT"
    CHECK_DEPENDENCIES = "CHECK_DEPENDENCIES"
    HARDWARE_BRIDGE = "HARDWARE_BRIDGE"
    TRANSPORT = "TRANSPORT"
    LINK = "LINK"
    STAGE2 = "STAGE2"
    SAFETY = "SAFETY"
    SNAPSHOT = "SNAPSHOT"
    READY = "READY"
    FAILED = "FAILED"
# ============================================================
# DATA MODELS
# ============================================================
@dataclass
class StartupRecord:
    ts: float
    phase: StartupPhase
    ok: bool
    summary: str
@dataclass
class StartupSnapshot:
    ts: float
    phase: StartupPhase
    ready: bool
    failed: bool
    records: list[dict] = field(default_factory=list)
    summary: str = ""
# ============================================================
# MAIN CLASS
# ============================================================
class RemotePiStartupOrchestrator:
    def __init__(
        self,
        *,
        runtime_lifecycle=None,
        state_store=None,
        hardware_bridge=None,
        command_transport=None,
        link_manager=None,
        runtime_wiring_stage2=None,
        safety_supervisor=None,
        snapshot_bus=None,
        status_sink: Optional[Callable[[str, dict], None]] = None,
    ):
        self.runtime_lifecycle = runtime_lifecycle
        self.state_store = state_store
        self.hardware_bridge = hardware_bridge
        self.command_transport = command_transport
        self.link_manager = link_manager
        self.runtime_wiring_stage2 = runtime_wiring_stage2
        self.safety_supervisor = safety_supervisor
        self.snapshot_bus = snapshot_bus
        self.status_sink = status_sink
        self._phase = StartupPhase.INIT
        self._ready = False
        self._failed = False
        self._records: list[StartupRecord] = []
        self._last_error: Optional[str] = None
    # --------------------------------------------------------
    # INTERNAL
    # --------------------------------------------------------
    def _emit_status(self, topic: str, **payload) -> None:
        if self.status_sink is not None:
            self.status_sink(topic, {
                "ts": time.time(),
                **payload,
            })
    def _record(self, phase: StartupPhase, ok: bool, summary: str) -> None:
        self._phase = phase
        rec = StartupRecord(
            ts=time.time(),
            phase=phase,
            ok=ok,
            summary=summary,
        )
        self._records.append(rec)
        self._emit_status(
            "startup_orchestrator/phase",
            phase=phase.value,
            ok=ok,
            summary=summary,
        )
    def _fail(self, phase: StartupPhase, summary: str) -> bool:
        self._failed = True
        self._ready = False
        self._phase = StartupPhase.FAILED
        self._last_error = summary
        self._record(phase, False, summary)
        if self.runtime_lifecycle is not None:
            try:
                self.runtime_lifecycle.enter_fault(f"Startup failed: {summary}")
            except Exception:
                pass
        return False
    # --------------------------------------------------------
    # CHECKS
    # --------------------------------------------------------
    def _check_dependencies(self) -> bool:
        self._record(StartupPhase.CHECK_DEPENDENCIES, True, "Checking startup dependencies.")
        if self.runtime_lifecycle is None:
            return self._fail(StartupPhase.CHECK_DEPENDENCIES, "runtime_lifecycle missing")
        if self.state_store is None:
            return self._fail(StartupPhase.CHECK_DEPENDENCIES, "state_store missing")
        return True
    def _bring_hardware_bridge(self) -> bool:
        self._record(StartupPhase.HARDWARE_BRIDGE, True, "Hardware bridge phase entered.")
        if self.hardware_bridge is None:
            # optional but expected
            self._emit_status(
                "startup_orchestrator/warning",
                phase=StartupPhase.HARDWARE_BRIDGE.value,
                summary="hardware_bridge missing; continuing with degraded startup",
            )
        return True
    def _bring_transport(self) -> bool:
        self._record(StartupPhase.TRANSPORT, True, "Transport phase entered.")
        if self.command_transport is None:
            self._emit_status(
                "startup_orchestrator/warning",
                phase=StartupPhase.TRANSPORT.value,
                summary="command_transport missing; continuing without external link",
            )
            return True
        try:
            self.command_transport.connect()
        except Exception as exc:
            return self._fail(StartupPhase.TRANSPORT, f"command_transport connect exception: {exc}")
        return True
    def _bring_link(self) -> bool:
        self._record(StartupPhase.LINK, True, "Link phase entered.")
        if self.link_manager is None:
            self._emit_status(
                "startup_orchestrator/warning",
                phase=StartupPhase.LINK.value,
                summary="link_manager missing; continuing without orchestrated link",
            )
            return True
        try:
            self.link_manager.connect()
        except Exception as exc:
            return self._fail(StartupPhase.LINK, f"link_manager connect exception: {exc}")
        return True
    def _bring_stage2(self) -> bool:
        self._record(StartupPhase.STAGE2, True, "Stage-2 runtime phase entered.")
        if self.runtime_wiring_stage2 is None:
            self._emit_status(
                "startup_orchestrator/warning",
                phase=StartupPhase.STAGE2.value,
                summary="runtime_wiring_stage2 missing; continuing without stage2 services",
            )
            return True
        return True
    def _bring_safety(self) -> bool:
        self._record(StartupPhase.SAFETY, True, "Safety phase entered.")
        if self.safety_supervisor is None:
            self._emit_status(
                "startup_orchestrator/warning",
                phase=StartupPhase.SAFETY.value,
                summary="safety_supervisor missing; continuing without supervisor",
            )
            return True
        try:
            self.safety_supervisor.tick()
        except Exception as exc:
            return self._fail(StartupPhase.SAFETY, f"safety supervisor startup tick failed: {exc}")
        return True
    def _bring_snapshot(self) -> bool:
        self._record(StartupPhase.SNAPSHOT, True, "Snapshot phase entered.")
        if self.snapshot_bus is None:
            self._emit_status(
                "startup_orchestrator/warning",
                phase=StartupPhase.SNAPSHOT.value,
                summary="snapshot_bus missing; continuing without snapshot aggregation",
            )
            return True
        try:
            self.snapshot_bus.build_compact_snapshot()
        except Exception as exc:
            return self._fail(StartupPhase.SNAPSHOT, f"snapshot bus startup build failed: {exc}")
        return True
    # --------------------------------------------------------
    # STARTUP
    # --------------------------------------------------------
    def startup(self) -> bool:
        self._ready = False
        self._failed = False
        self._last_error = None
        self._records.clear()
        self._phase = StartupPhase.INIT
        self._record(StartupPhase.INIT, True, "Startup initiated.")
        try:
            if hasattr(self.runtime_lifecycle, "to_dict"):
                pass
        except Exception:
            pass
        if not self._check_dependencies():
            return False
        if not self._bring_hardware_bridge():
            return False
        if not self._bring_transport():
            return False
        if not self._bring_link():
            return False
        if not self._bring_stage2():
            return False
        if not self._bring_safety():
            return False
        if not self._bring_snapshot():
            return False
        try:
            self.runtime_lifecycle.enter_ready()
        except Exception as exc:
            return self._fail(StartupPhase.READY, f"runtime_lifecycle enter_ready failed: {exc}")
        self._ready = True
        self._failed = False
        self._record(StartupPhase.READY, True, "Startup completed successfully.")
        return True
    # --------------------------------------------------------
    # ACCESSORS
    # --------------------------------------------------------
    @property
    def phase(self) -> StartupPhase:
        return self._phase
    @property
    def ready(self) -> bool:
        return self._ready
    @property
    def failed(self) -> bool:
        return self._failed
    def snapshot(self) -> StartupSnapshot:
        return StartupSnapshot(
            ts=time.time(),
            phase=self._phase,
            ready=self._ready,
            failed=self._failed,
            records=[
                {
                    "ts": rec.ts,
                    "phase": rec.phase.value,
                    "ok": rec.ok,
                    "summary": rec.summary,
                }
                for rec in self._records
            ],
            summary=(
                f"phase={self._phase.value} | "
                f"ready={self._ready} | "
                f"failed={self._failed} | "
                f"records={len(self._records)}"
            ),
        )
    def to_dict(self) -> dict:
        snap = self.snapshot()
        return {
            "ts": snap.ts,
            "phase": snap.phase.value,
            "ready": snap.ready,
            "failed": snap.failed,
            "records": list(snap.records),
            "summary": snap.summary,
            "last_error": self._last_error,
        }


# ============================================================
# MODULE-R042
# ============================================================

# runtime/remotepi_runtime_supervisor.py
"""
MODULE-R042
RemotePi Runtime Supervisor
---------------------------

Purpose:
    Top-level runtime coordinator for RemotePi.

Responsibilities:
    - Supervise startup orchestration
    - Run coordinated periodic ticks
    - Supervise lifecycle, safety, link and stage2 runtime services
    - Expose a unified health/status snapshot
    - Provide controlled shutdown entry

Compatible with:
    - RemotePiRuntimeLifecycle
    - RemotePiSafetySupervisor
    - RemotePiLinkOrchestrationManager
    - RemotePiRuntimeWiringStage2
    - RemotePiStartupOrchestrator
    - RemotePiRuntimeSnapshotBus
"""
import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional
# ============================================================
# ENUMS
# ============================================================
class SupervisorState(str, Enum):
    INIT = "INIT"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    DEGRADED = "DEGRADED"
    FAULTED = "FAULTED"
    SHUTDOWN = "SHUTDOWN"
# ============================================================
# DATA MODELS
# ============================================================
@dataclass
class SupervisorSnapshot:
    ts: float
    state: SupervisorState
    startup_ready: bool
    lifecycle_state: str
    link_state: str
    safety_level: str
    summary: str
# ============================================================
# MAIN CLASS
# ============================================================
class RemotePiRuntimeSupervisor:
    def __init__(
        self,
        *,
        runtime_lifecycle=None,
        safety_supervisor=None,
        link_manager=None,
        runtime_wiring_stage2=None,
        startup_orchestrator=None,
        snapshot_bus=None,
        status_sink: Optional[Callable[[str, dict], None]] = None,
    ):
        self.runtime_lifecycle = runtime_lifecycle
        self.safety_supervisor = safety_supervisor
        self.link_manager = link_manager
        self.runtime_wiring_stage2 = runtime_wiring_stage2
        self.startup_orchestrator = startup_orchestrator
        self.snapshot_bus = snapshot_bus
        self.status_sink = status_sink
        self._state = SupervisorState.INIT
        self._last_tick_ts = 0.0
        self._last_error: Optional[str] = None
    # --------------------------------------------------------
    # INTERNAL
    # --------------------------------------------------------
    def _emit_status(self, topic: str, **payload) -> None:
        if self.status_sink is not None:
            self.status_sink(topic, {
                "ts": time.time(),
                **payload,
            })
    def _set_state(self, state: SupervisorState, summary: str = "") -> None:
        self._state = state
        self._emit_status(
            "runtime_supervisor/state_changed",
            state=state.value,
            summary=summary,
        )
    def _safe_call(self, fn, *args, default=None, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            self._last_error = str(exc)
            self._emit_status(
                "runtime_supervisor/call_error",
                function=getattr(fn, "__name__", str(fn)),
                error=str(exc),
            )
            return default
    # --------------------------------------------------------
    # STARTUP
    # --------------------------------------------------------
    def startup(self) -> bool:
        self._set_state(SupervisorState.STARTING, "Runtime supervisor startup initiated.")
        if self.startup_orchestrator is None:
            self._last_error = "startup_orchestrator missing"
            self._set_state(SupervisorState.FAULTED, "Startup orchestrator missing.")
            return False
        ok = self._safe_call(self.startup_orchestrator.startup, default=False)
        if not ok:
            self._set_state(SupervisorState.FAULTED, "Startup orchestration failed.")
            return False
        self._set_state(SupervisorState.RUNNING, "Runtime supervisor startup completed.")
        return True
    # --------------------------------------------------------
    # PERIODIC TICK
    # --------------------------------------------------------
    def tick(self) -> None:
        self._last_tick_ts = time.time()
        # Link manager
        if self.link_manager is not None:
            self._safe_call(self.link_manager.tick, default=None)
        # Stage-2 runtime
        if self.runtime_wiring_stage2 is not None:
            self._safe_call(self.runtime_wiring_stage2.tick, default=None)
        # Safety supervisor
        if self.safety_supervisor is not None:
            self._safe_call(self.safety_supervisor.tick, default=None)
        # Lifecycle auto alignment
        if self.runtime_lifecycle is not None and hasattr(self.runtime_lifecycle, "auto_align_from_state"):
            self._safe_call(self.runtime_lifecycle.auto_align_from_state, default=None)
        # Re-evaluate supervisor state
        self._refresh_supervisor_state()
    # --------------------------------------------------------
    # STATE EVALUATION
    # --------------------------------------------------------
    def _refresh_supervisor_state(self) -> None:
        lifecycle_state = "UNKNOWN"
        link_state = "UNKNOWN"
        safety_level = "UNKNOWN"
        if self.runtime_lifecycle is not None and hasattr(self.runtime_lifecycle, "lifecycle_state"):
            try:
                lifecycle_state = self.runtime_lifecycle.lifecycle_state.value
            except Exception:
                pass
        if self.link_manager is not None and hasattr(self.link_manager, "state"):
            try:
                link_state = self.link_manager.state.value
            except Exception:
                pass
        if self.safety_supervisor is not None and hasattr(self.safety_supervisor, "get_last_decision_dict"):
            try:
                safety_level = str(self.safety_supervisor.get_last_decision_dict().get("level", "UNKNOWN"))
            except Exception:
                pass
        if lifecycle_state == "SHUTDOWN":
            self._set_state(SupervisorState.SHUTDOWN, "Lifecycle in shutdown.")
            return
        if lifecycle_state == "FAULTED" or safety_level in ("FAULT", "CRITICAL", "SHUTDOWN"):
            self._set_state(SupervisorState.FAULTED, "Fault condition detected by lifecycle/safety.")
            return
        if link_state in ("DEGRADED", "LOST", "DOWN"):
            self._set_state(SupervisorState.DEGRADED, f"Link not healthy: {link_state}")
            return
        self._set_state(SupervisorState.RUNNING, "Runtime healthy.")
    # --------------------------------------------------------
    # SHUTDOWN
    # --------------------------------------------------------
    def request_shutdown(self, summary: str = "Supervisor requested shutdown.") -> None:
        if self.runtime_lifecycle is not None and hasattr(self.runtime_lifecycle, "request_shutdown"):
            self._safe_call(self.runtime_lifecycle.request_shutdown, summary, default=None)
        self._set_state(SupervisorState.SHUTDOWN, summary)
    # --------------------------------------------------------
    # SNAPSHOT
    # --------------------------------------------------------
    def snapshot(self) -> SupervisorSnapshot:
        startup_ready = False
        lifecycle_state = "UNKNOWN"
        link_state = "UNKNOWN"
        safety_level = "UNKNOWN"
        if self.startup_orchestrator is not None and hasattr(self.startup_orchestrator, "ready"):
            try:
                startup_ready = bool(self.startup_orchestrator.ready)
            except Exception:
                pass
        if self.runtime_lifecycle is not None and hasattr(self.runtime_lifecycle, "lifecycle_state"):
            try:
                lifecycle_state = self.runtime_lifecycle.lifecycle_state.value
            except Exception:
                pass
        if self.link_manager is not None and hasattr(self.link_manager, "state"):
            try:
                link_state = self.link_manager.state.value
            except Exception:
                pass
        if self.safety_supervisor is not None and hasattr(self.safety_supervisor, "get_last_decision_dict"):
            try:
                safety_level = str(self.safety_supervisor.get_last_decision_dict().get("level", "UNKNOWN"))
            except Exception:
                pass
        return SupervisorSnapshot(
            ts=time.time(),
            state=self._state,
            startup_ready=startup_ready,
            lifecycle_state=lifecycle_state,
            link_state=link_state,
            safety_level=safety_level,
            summary=(
                f"state={self._state.value} | "
                f"startup_ready={startup_ready} | "
                f"lifecycle={lifecycle_state} | "
                f"link={link_state} | "
                f"safety={safety_level}"
            ),
        )
    def to_dict(self) -> dict:
        snap = self.snapshot()
        data = {
            "ts": snap.ts,
            "state": snap.state.value,
            "startup_ready": snap.startup_ready,
            "lifecycle_state": snap.lifecycle_state,
            "link_state": snap.link_state,
            "safety_level": snap.safety_level,
            "summary": snap.summary,
            "last_tick_ts": self._last_tick_ts,
            "last_error": self._last_error,
        }
        if self.snapshot_bus is not None and hasattr(self.snapshot_bus, "build_compact_snapshot"):
            compact = self._safe_call(self.snapshot_bus.build_compact_snapshot, default=None)
            if compact is not None:
                data["runtime_snapshot_compact"] = compact
        return data


# ============================================================
# MODULE-R043
# ============================================================

# runtime/remotepi_mqtt_transport_adapter.py
"""
MODULE-R043
RemotePi MQTT Transport Adapter
-------------------------------

Purpose:
    MQTT-specific transport adapter for RemotePi command transport.

Responsibilities:
    - Connect/disconnect to MQTT broker
    - Publish outbound runtime command frames
    - Subscribe to inbound topics
    - Buffer inbound messages for polling
    - Expose transport callbacks compatible with RemotePiCommandTransport

Design goals:
    - Safe fallback behavior
    - Minimal blocking
    - Clear topic separation
"""
import time
from collections import deque
from dataclasses import dataclass
from typing import Optional, Callable
# ============================================================
# OPTIONAL MQTT IMPORT
# ============================================================
try:
    import paho.mqtt.client as mqtt
except Exception:
    mqtt = None
# ============================================================
# CONFIG
# ============================================================
@dataclass
class MQTTTransportConfig:
    broker_host: str = "127.0.0.1"
    broker_port: int = 1883
    keepalive_sec: int = 30
    client_id: str = "RemotePiRuntime"
    outbound_topic: str = "remotepi/runtime/outbound"
    inbound_topic: str = "remotepi/runtime/inbound"
    status_topic: str = "remotepi/runtime/status"
    max_inbound_queue: int = 200
    auto_start_loop: bool = True
    emit_status_logs: bool = True
# ============================================================
# MAIN CLASS
# ============================================================
class RemotePiMQTTTransportAdapter:
    def __init__(
        self,
        *,
        config: Optional[MQTTTransportConfig] = None,
        status_sink: Optional[Callable[[str, dict], None]] = None,
    ):
        self.config = config or MQTTTransportConfig()
        self.status_sink = status_sink
        self._client = None
        self._connected = False
        self._last_error: Optional[str] = None
        self._inbound_queue = deque(maxlen=self.config.max_inbound_queue)
        self._last_rx_ts = 0.0
        self._last_tx_ts = 0.0
        self._build_client()
    # --------------------------------------------------------
    # INTERNAL
    # --------------------------------------------------------
    def _emit_status(self, topic: str, **payload) -> None:
        if not self.config.emit_status_logs:
            return
        if self.status_sink is not None:
            self.status_sink(topic, {
                "ts": time.time(),
                **payload,
            })
    def _build_client(self) -> None:
        if mqtt is None:
            self._last_error = "paho.mqtt.client unavailable"
            self._client = None
            self._emit_status(
                "mqtt_adapter/init_error",
                error=self._last_error,
            )
            return
        try:
            self._client = mqtt.Client(client_id=self.config.client_id)
            self._client.on_connect = self._on_connect
            self._client.on_disconnect = self._on_disconnect
            self._client.on_message = self._on_message
        except Exception as exc:
            self._last_error = str(exc)
            self._client = None
            self._emit_status(
                "mqtt_adapter/init_error",
                error=str(exc),
        
            )
    # --------------------------------------------------------
    # MQTT CALLBACKS
    # --------------------------------------------------------
    def _on_connect(self, client, userdata, flags, rc):
        ok = int(rc) == 0
        self._connected = ok
        if ok:
            try:
                client.subscribe(self.config.inbound_topic)
            except Exception as exc:
                self._last_error = str(exc)
                self._emit_status(
                    "mqtt_adapter/subscribe_error",
                    error=str(exc),
                    topic=self.config.inbound_topic,
                )
        self._emit_status(
            "mqtt_adapter/on_connect",
            ok=ok,
            rc=rc,
            inbound_topic=self.config.inbound_topic,
        )
    def _on_disconnect(self, client, userdata, rc):
        self._connected = False
        self._emit_status(
            "mqtt_adapter/on_disconnect",
            rc=rc,
        )
    def _on_message(self, client, userdata, msg):
        try:
            raw = msg.payload.decode("utf-8", errors="ignore")
        except Exception as exc:
            self._last_error = str(exc)
            self._emit_status(
                "mqtt_adapter/decode_error",
                error=str(exc),
                topic=getattr(msg, "topic", ""),
            )
            return
        self._inbound_queue.append(raw)
        self._last_rx_ts = time.time()
        self._emit_status(
            "mqtt_adapter/rx",
            topic=getattr(msg, "topic", ""),
            size=len(raw),
        )
    # --------------------------------------------------------
    # PUBLIC API FOR R040
    # --------------------------------------------------------
    def connect(self) -> bool:
        if self._client is None:
            self._last_error = self._last_error or "client not available"
            return False
        try:
            self._client.connect(
                self.config.broker_host,
                self.config.broker_port,
                self.config.keepalive_sec,
            )
            if self.config.auto_start_loop:
                self._client.loop_start()
            self._emit_status(
                "mqtt_adapter/connect_called",
                broker_host=self.config.broker_host,
                broker_port=self.config.broker_port,
            )
            return True
        except Exception as exc:
            self._last_error = str(exc)
            self._connected = False
            self._emit_status(
                "mqtt_adapter/connect_error",
                error=str(exc),
            )
            return False
    def disconnect(self) -> None:
        if self._client is None:
            return
        try:
            self._client.disconnect()
        except Exception as exc:
            self._last_error = str(exc)
            self._emit_status(
                "mqtt_adapter/disconnect_error",
                error=str(exc),
            )
        try:
            if self.config.auto_start_loop:
                self._client.loop_stop()
        except Exception:
            pass
        self._connected = False
    def is_connected(self) -> bool:
        return bool(self._connected)
    def send(self, raw_text: str) -> bool:
        if self._client is None or not self._connected:
            self._last_error = "mqtt not connected"
            return False
        try:
            info = self._client.publish(self.config.outbound_topic, raw_text, qos=0)
            ok = getattr(info, "rc", 1) == 0
        except Exception as exc:
            self._last_error = str(exc)
            self._emit_status(
                "mqtt_adapter/send_error",
                error=str(exc),
            )
            return False
        if ok:
            self._last_tx_ts = time.time()
            self._emit_status(
                "mqtt_adapter/tx",
                topic=self.config.outbound_topic,
                size=len(raw_text),
            )
            return True
        self._last_error = "publish rc != 0"
        return False
    def poll(self) -> Optional[str]:
        if not self._inbound_queue:
            return None
        return self._inbound_queue.popleft()
    def send_status(self, payload_text: str) -> bool:
        if self._client is None or not self._connected:
            self._last_error = "mqtt not connected"
            return False
        try:
            info = self._client.publish(self.config.status_topic, payload_text, qos=0)
            ok = getattr(info, "rc", 1) == 0
        except Exception as exc:
            self._last_error = str(exc)
            self._emit_status(
                "mqtt_adapter/status_send_error",
                error=str(exc),
            )
            return False
        return bool(ok)
    # --------------------------------------------------------
    # SNAPSHOT
    # --------------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "broker_host": self.config.broker_host,
            "broker_port": self.config.broker_port,
            "client_id": self.config.client_id,
            "outbound_topic": self.config.outbound_topic,
            "inbound_topic": self.config.inbound_topic,
            "status_topic": self.config.status_topic,
            "connected": self._connected,
            "last_rx_ts": self._last_rx_ts,
            "last_tx_ts": self._last_tx_ts,
            "queued_inbound": len(self._inbound_queue),
            "last_error": self._last_error,
        }


# ============================================================
# MODULE-R044
# ============================================================

# runtime/remotepi_inbound_message_router.py
"""
MODULE-R044
RemotePi Inbound Message Router
-------------------------------

Purpose:
    Route normalized inbound transport messages to appropriate RemotePi runtime targets.

Responsibilities:
    - Accept inbound message_type + payload
    - Update link freshness
    - Mirror selected MasterPi state into RemotePi state store
    - Feed cooling/battery/fault information into runtime state
    - Trigger lifecycle / safety friendly actions on inbound requests

Design goals:
    - Deterministic routing
    - Safe fallback behavior
    - Minimal assumptions about transport
"""
import time
from dataclasses import dataclass
from typing import Callable, Optional
# ============================================================
# DATA MODELS
# ============================================================
@dataclass
class InboundRouterConfig:
    emit_status_logs: bool = True
    accept_remote_shutdown_request: bool = True
    accept_remote_fault_sync: bool = True
    accept_remote_battery_sync: bool = True
    accept_remote_cooling_sync: bool = True
# ============================================================
# MAIN CLASS
# ============================================================
class RemotePiInboundMessageRouter:
    def __init__(
        self,
        *,
        state_store=None,
        link_manager=None,
        runtime_lifecycle=None,
        safety_supervisor=None,
        hybrid_integration_manager=None,
        hmi_cooling_update_hook: Optional[Callable[[str, str], None]] = None,
        hmi_fault_open_hook: Optional[Callable[[], None]] = None,
        status_sink: Optional[Callable[[str, dict], None]] = None,
        config: Optional[InboundRouterConfig] = None,
    ):
        self.state_store = state_store
        self.link_manager = link_manager
        self.runtime_lifecycle = runtime_lifecycle
        self.safety_supervisor = safety_supervisor
        self.hybrid_integration_manager = hybrid_integration_manager
        self.hmi_cooling_update_hook = hmi_cooling_update_hook
        self.hmi_fault_open_hook = hmi_fault_open_hook
        self.status_sink = status_sink
        self.config = config or InboundRouterConfig()
        self._last_message_type: Optional[str] = None
        self._last_message_ts: float = 0.0
        self._last_ack_id: Optional[str] = None
        self._last_error: Optional[str] = None
    # --------------------------------------------------------
    # INTERNAL
    # --------------------------------------------------------
    def _emit_status(self, topic: str, **payload) -> None:
        if not self.config.emit_status_logs:
            return
        if self.status_sink is not None:
            self.status_sink(topic, {
                "ts": time.time(),
                **payload,
            })
    def _note_message(self, message_type: str) -> None:
        self._last_message_type = str(message_type)
        self._last_message_ts = time.time()
        if self.link_manager is not None and hasattr(self.link_manager, "note_rx"):
            try:
                self.link_manager.note_rx()
            except Exception as exc:
                self._last_error = str(exc)
                self._emit_status("inbound_router/link_note_rx_error", error=str(exc))
        if self.state_store is not None and hasattr(self.state_store, "set_last_event"):
            try:
                self.state_store.set_last_event(f"INBOUND:{message_type}")
            except Exception:
                pass
    # --------------------------------------------------------
    # ROUTE HELPERS
    # --------------------------------------------------------
    def _handle_heartbeat(self, payload: dict) -> None:
        self._emit_status(
            "inbound_router/heartbeat",
            payload=payload,
        )
    def _handle_ack(self, payload: dict) -> None:
        self._last_ack_id = str(payload.get("ack_id", payload.get("command_id", "")))
        self._emit_status(
            "inbound_router/ack",
            ack_id=self._last_ack_id,
            payload=payload,
        )
    def _handle_nack(self, payload: dict) -> None:
        self._emit_status(
            "inbound_router/nack",
            payload=payload,
        )
    def _handle_master_state(self, payload: dict) -> None:
        if self.state_store is None:
            return
        try:
            if "network_online" in payload or "master_link_ok" in payload:
                self.state_store.update_network(
                    wifi_connected=bool(payload.get("wifi_connected", True)),
                    bluetooth_connected=bool(payload.get("bluetooth_connected", False)),
                    ethernet_link=bool(payload.get("ethernet_link", False)),
                    master_link_ok=bool(payload.get("master_link_ok", True)),
                    network_online=bool(payload.get("network_online", True)),
                    network_weak=bool(payload.get("network_weak", False)),
                )
        except Exception as exc:
            self._last_error = str(exc)
            self._emit_status("inbound_router/master_state_error", error=str(exc))
    def _handle_cooling_state(self, payload: dict) -> None:
        if not self.config.accept_remote_cooling_sync:
            return
        mc_state = str(payload.get("mc_state", "COMM_LOST"))
        rc_state = str(payload.get("rc_state", "COMM_LOST"))
        if self.hmi_cooling_update_hook is not None:
            try:
                self.hmi_cooling_update_hook(mc_state, rc_state)
            except Exception as exc:
                self._last_error = str(exc)
                self._emit_status("inbound_router/cooling_hook_error", error=str(exc))
        if self.state_store is not None and hasattr(self.state_store, "set_fan_active"):
            try:
                self.state_store.set_fan_active(rc_state == "ON")
            except Exception:
                pass
        self._emit_status(
            "inbound_router/cooling_state",
            mc_state=mc_state,
            rc_state=rc_state,
        )
    def _handle_battery_sync(self, payload: dict) -> None:
        if not self.config.accept_remote_battery_sync or self.state_store is None:
            return
        try:
            voltage = float(payload.get("voltage", payload.get("battery_voltage", 0.0)))
            percent = float(payload.get("percent", payload.get("percent_est", 0.0)))
            bucket = str(payload.get("bucket", "STATE_BATTERY_NORMAL"))
            self.state_store.update_battery(
                voltage=voltage,
                percent_est=percent,
                bucket=bucket,
            )
        except Exception as exc:
            self._last_error = str(exc)
            self._emit_status("inbound_router/battery_sync_error", error=str(exc))
    def _handle_fault_sync(self, payload: dict) -> None:
        if not self.config.accept_remote_fault_sync or self.state_store is None:
            return
        try:
            severity = str(payload.get("severity", "WARNING"))
            summary = str(payload.get("summary", "Inbound fault sync"))
            warnings = list(payload.get("warnings", []))
            faults = list(payload.get("faults", []))
            request_shutdown = bool(payload.get("request_shutdown", False))
            ui_fault_latched = bool(payload.get("ui_fault_latched", bool(faults)))
            self.state_store.update_safety(
                severity=severity,
                primary_state=str(payload.get("primary_state", "STATE_FAULT")),
                accept_user_control=bool(payload.get("accept_user_control", False)),
                allow_new_motion_commands=bool(payload.get("allow_new_motion_commands", False)),
                request_shutdown=request_shutdown,
                ui_fault_latched=ui_fault_latched,
                summary=summary,
                warnings=warnings,
                faults=faults,
            )
            if request_shutdown and self.runtime_lifecycle is not None and hasattr(self.runtime_lifecycle, "request_shutdown"):
                self.runtime_lifecycle.request_shutdown(summary)
            elif faults and self.runtime_lifecycle is not None and hasattr(self.runtime_lifecycle, "enter_fault"):
                self.runtime_lifecycle.enter_fault(summary)
            if faults and self.hmi_fault_open_hook is not None:
                try:
                    self.hmi_fault_open_hook()
                except Exception:
                    pass
        except Exception as exc:
            self._last_error = str(exc)
            self._emit_status("inbound_router/fault_sync_error", error=str(exc))
    def _handle_shutdown_request(self, payload: dict) -> None:
        if not self.config.accept_remote_shutdown_request:
            return
        summary = str(payload.get("summary", "Inbound remote shutdown request"))
        if self.runtime_lifecycle is not None and hasattr(self.runtime_lifecycle, "request_shutdown"):
            try:
                self.runtime_lifecycle.request_shutdown(summary)
            except Exception as exc:
                self._last_error = str(exc)
                self._emit_status("inbound_router/shutdown_request_error", error=str(exc))
    def _handle_runtime_snapshot(self, payload: dict) -> None:
        self._emit_status(
            "inbound_router/runtime_snapshot",
            payload=payload,
        )
    # --------------------------------------------------------
    # PUBLIC ENTRY
    # --------------------------------------------------------
    def route_inbound(self, message_type: str, payload: Optional[dict] = None) -> None:
        payload = payload or {}
        msg_type = str(message_type).upper()
        self._note_message(msg_type)
        self._emit_status(
            "inbound_router/message_received",
            message_type=msg_type,
            payload=payload,
        )
        if msg_type in ("HEARTBEAT", "PONG", "HEARTBEAT_ACK"):
            self._handle_heartbeat(payload)
            return
        if msg_type == "ACK":
            self._handle_ack(payload)
            return
        if msg_type == "NACK":
            self._handle_nack(payload)
            return
        if msg_type in ("MASTER_STATE", "MASTER_STATE_UPDATE"):
            self._handle_master_state(payload)
            return
        if msg_type in ("COOLING_STATE", "FAN_STATE_UPDATE"):
            self._handle_cooling_state(payload)
            return
        if msg_type in ("BATTERY_SYNC", "BATTERY_STATE"):
            self._handle_battery_sync(payload)
            return
        if msg_type in ("FAULT_SYNC", "FAULT_STATE", "ALARM_SYNC"):
            self._handle_fault_sync(payload)
            return
        if msg_type in ("SHUTDOWN_REQUEST", "REMOTE_SHUTDOWN"):
            self._handle_shutdown_request(payload)
            return
        if msg_type in ("RUNTIME_SNAPSHOT", "SNAPSHOT"):
            self._handle_runtime_snapshot(payload)
            return
        self._emit_status(
            "inbound_router/unhandled_message",
            message_type=msg_type,
            payload=payload,
        )
    # --------------------------------------------------------
    # SNAPSHOT
    # --------------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "last_message_type": self._last_message_type,
            "last_message_ts": self._last_message_ts,
            "last_ack_id": self._last_ack_id,
            "last_error": self._last_error,
            "config": {
                "accept_remote_shutdown_request": self.config.accept_remote_shutdown_request,
                "accept_remote_fault_sync": self.config.accept_remote_fault_sync,
                "accept_remote_battery_sync": self.config.accept_remote_battery_sync,
                "accept_remote_cooling_sync": self.config.accept_remote_cooling_sync,
            },
        }


# ============================================================
# MODULE-R045
# ============================================================

# runtime/remotepi_runtime_bootstrap.py
"""
MODULE-R045
RemotePi Runtime Bootstrap
--------------------------

Purpose:
    Build and wire the full RemotePi runtime object graph in one place.

Responsibilities:
    - Instantiate runtime modules
    - Wire dependencies in the correct order
    - Provide one bootstrap result object
    - Keep HMI build() cleaner
    - Support optional MQTT transport wiring

Design goals:
    - Deterministic construction
    - Safe defaults
    - Partial deployment friendly
"""
from dataclasses import dataclass
from typing import Any, Callable, Optional
from runtime.remotepi_state_store import RemotePiStateStore
from runtime.remotepi_mode_fsm import RemotePiModeFSM
from runtime.remotepi_event_router import RemotePiEventRouter
from runtime.remotepi_runtime_lifecycle import RemotePiRuntimeLifecycle
from runtime.remotepi_safety_supervisor import RemotePiSafetySupervisor
from runtime.remotepi_runtime_snapshot_bus import RemotePiRuntimeSnapshotBus
from runtime.remotepi_hardware_runtime_bridge import RemotePiHardwareRuntimeBridge
from runtime.remotepi_runtime_wiring_stage2 import RemotePiRuntimeWiringStage2
from runtime.remotepi_hybrid_integration_manager import RemotePiHybridIntegrationManager
from runtime.remotepi_integration_profile import build_hybrid_profile
from runtime.remotepi_command_transport import RemotePiCommandTransport
from runtime.remotepi_mqtt_transport_adapter import (
    RemotePiMQTTTransportAdapter,
    MQTTTransportConfig,
)
from runtime.remotepi_link_orchestration_manager import RemotePiLinkOrchestrationManager
from runtime.remotepi_inbound_message_router import RemotePiInboundMessageRouter
from runtime.remotepi_startup_orchestrator import RemotePiStartupOrchestrator
from runtime.remotepi_runtime_supervisor import RemotePiRuntimeSupervisor
# ============================================================
# DATA MODELS
# ============================================================
@dataclass
class RemotePiRuntimeBundle:
    state_store: RemotePiStateStore
    mode_fsm: RemotePiModeFSM
    event_router: RemotePiEventRouter
    runtime_lifecycle: RemotePiRuntimeLifecycle
    safety_supervisor: RemotePiSafetySupervisor
    snapshot_bus: RemotePiRuntimeSnapshotBus
    hardware_bridge: RemotePiHardwareRuntimeBridge
    stage2_wiring: RemotePiRuntimeWiringStage2
    integration_manager: RemotePiHybridIntegrationManager
    command_transport: RemotePiCommandTransport
    mqtt_adapter: Optional[RemotePiMQTTTransportAdapter]
    link_manager: RemotePiLinkOrchestrationManager
    inbound_router: RemotePiInboundMessageRouter
    startup_orchestrator: RemotePiStartupOrchestrator
    runtime_supervisor: RemotePiRuntimeSupervisor
@dataclass
class RemotePiRuntimeBootstrapConfig:
    enable_mqtt_adapter: bool = True
    mqtt_broker_host: str = "127.0.0.1"
    mqtt_broker_port: int = 1883
    mqtt_client_id: str = "RemotePiRuntime"
    mqtt_outbound_topic: str = "remotepi/runtime/outbound"
    mqtt_inbound_topic: str = "masterpi/runtime/inbound"
    mqtt_status_topic: str = "remotepi/runtime/status"
# ============================================================
# MAIN BOOTSTRAP
# ============================================================
class RemotePiRuntimeBootstrap:
    def __init__(
        self,
        *,
        config: Optional[RemotePiRuntimeBootstrapConfig] = None,
        status_sink: Optional[Callable[[str, dict], None]] = None,
    ):
        self.config = config or RemotePiRuntimeBootstrapConfig()
        self.status_sink = status_sink
    def _emit_status(self, topic: str, **payload) -> None:
        if self.status_sink is not None:
            self.status_sink(topic, payload)
    def build(
        self,
        *,
        legacy_hw=None,
        app=None,
        stage2_adc_reader: Optional[Callable[[str], float]] = None,
        stage2_gpio_writer: Optional[Callable[[str, bool], None]] = None,
        stage2_ui_fault_hook: Optional[Callable[[dict], None]] = None,
        stage2_network_status_reader: Optional[Callable[[], dict]] = None,
        stage2_ui_health_reader: Optional[Callable[[], bool]] = None,
        stage2_system_active_reader: Optional[Callable[[], bool]] = None,
        hmi_cooling_update_hook: Optional[Callable[[str, str], None]] = None,
        hmi_fault_open_hook: Optional[Callable[[], None]] = None,
    ) -> RemotePiRuntimeBundle:
        # ----------------------------------------------------
        # Core state + mode + lifecycle
        # ----------------------------------------------------
        state_store = RemotePiStateStore()
        mode_fsm = RemotePiModeFSM(
            state_store=state_store
        )
        runtime_lifecycle = RemotePiRuntimeLifecycle(
            state_store=state_store,
            mode_fsm=mode_fsm,
            status_sink=self.status_sink,
        )
        # ----------------------------------------------------
        # Hardware bridge
        # ----------------------------------------------------
        hardware_bridge = RemotePiHardwareRuntimeBridge(
            legacy_hw=legacy_hw,
            status_sink=self.status_sink,
        )
        # ----------------------------------------------------
        # Event router
        # ----------------------------------------------------
        event_router = RemotePiEventRouter(
            command_sink=lambda command_name, payload: hardware_bridge.execute_runtime_command(command_name, payload),
            event_sink=lambda topic, payload: self._emit_status("bootstrap/event_router_event", topic=topic, payload=payload),
            state_store=state_store,
            mode_fsm=mode_fsm,
        )
        # ----------------------------------------------------
        # Hybrid HMI integration manager
        # ----------------------------------------------------
        integration_manager = RemotePiHybridIntegrationManager(
            profile=build_hybrid_profile(),
            mode_fsm=mode_fsm,
            event_router=event_router,
            state_store=state_store,
            status_sink=self.status_sink,
        )
        if app is not None:
            integration_manager.bind_app(app)
        # ----------------------------------------------------
        # Transport + MQTT adapter
        # ----------------------------------------------------
        mqtt_adapter = None
        if self.config.enable_mqtt_adapter:
            mqtt_adapter = RemotePiMQTTTransportAdapter(
                config=MQTTTransportConfig(
                    broker_host=self.config.mqtt_broker_host,
                    broker_port=self.config.mqtt_broker_port,
                    client_id=self.config.mqtt_client_id,
                    outbound_topic=self.config.mqtt_outbound_topic,
                    inbound_topic=self.config.mqtt_inbound_topic,
                    status_topic=self.config.mqtt_status_topic,
                ),
                status_sink=self.status_sink,
            )
        command_transport = RemotePiCommandTransport(
            connect_fn=(mqtt_adapter.connect if mqtt_adapter else (lambda: True)),
            disconnect_fn=(mqtt_adapter.disconnect if mqtt_adapter else (lambda: None)),
            is_connected_fn=(mqtt_adapter.is_connected if mqtt_adapter else (lambda: True)),
            send_fn=(mqtt_adapter.send if mqtt_adapter else (lambda raw: True)),
            poll_fn=(mqtt_adapter.poll if mqtt_adapter else (lambda: None)),
            inbound_sink=None,   # inbound router aşağıda bağlanacak
            status_sink=self.status_sink,
        )
        # ----------------------------------------------------
        # Link manager
        # ----------------------------------------------------
        link_manager = RemotePiLinkOrchestrationManager(
            state_store=state_store,
            runtime_lifecycle=runtime_lifecycle,
            safety_supervisor=None,
            transport_connect=command_transport.connect,
            transport_disconnect=command_transport.disconnect,
            transport_is_connected=command_transport.is_connected,
            transport_send_heartbeat=command_transport.send_heartbeat,
            status_sink=self.status_sink,
        )
        # ----------------------------------------------------
        # Inbound router
        # ----------------------------------------------------
        inbound_router = RemotePiInboundMessageRouter(
            state_store=state_store,
            link_manager=link_manager,
            runtime_lifecycle=runtime_lifecycle,
            safety_supervisor=None,
            hybrid_integration_manager=integration_manager,
            hmi_cooling_update_hook=hmi_cooling_update_hook,
            hmi_fault_open_hook=hmi_fault_open_hook,
            status_sink=self.status_sink,
        )
        command_transport.inbound_sink = inbound_router.route_inbound
        # ----------------------------------------------------
        # Stage-2 wiring
        # ----------------------------------------------------
        stage2_wiring = RemotePiRuntimeWiringStage2(
            state_store=state_store,
            event_router=event_router,
            mode_fsm=mode_fsm,
            hmi_integration_manager=integration_manager,
            logger=None,
            status_sink=self.status_sink,
        )
        stage2_wiring.build_all(
            adc_reader=stage2_adc_reader,
            gpio_writer=stage2_gpio_writer,
            ui_fault_hook=stage2_ui_fault_hook,
            network_status_reader=stage2_network_status_reader,
            ui_health_reader=stage2_ui_health_reader,
            system_active_reader=stage2_system_active_reader,
            link_manager=link_manager,
            command_transport=command_transport,
            platform_shutdown_hook=None,
        )
        # ----------------------------------------------------
        # Safety supervisor
        # ----------------------------------------------------
        safety_supervisor = RemotePiSafetySupervisor(
            state_store=state_store,
            runtime_lifecycle=runtime_lifecycle,
            mode_fsm=mode_fsm,
            network_status_reader=stage2_network_status_reader,
            ui_health_reader=stage2_ui_health_reader,
            status_sink=self.status_sink,
        )
        # tamamlayıcı referanslar
        link_manager.safety_supervisor = safety_supervisor
        inbound_router.safety_supervisor = safety_supervisor
        # ----------------------------------------------------
        # Snapshot bus
        # ----------------------------------------------------
        snapshot_bus = RemotePiRuntimeSnapshotBus(
            state_store=state_store,
            mode_fsm=mode_fsm,
            runtime_lifecycle=runtime_lifecycle,
            safety_supervisor=safety_supervisor,
            watchdog_supervisor=stage2_wiring.watchdog_supervisor,
            hybrid_integration_manager=integration_manager,
            runtime_wiring_stage2=stage2_wiring,
        )
        # ----------------------------------------------------
        # Startup orchestrator
        # ----------------------------------------------------
        startup_orchestrator = RemotePiStartupOrchestrator(
            runtime_lifecycle=runtime_lifecycle,
            state_store=state_store,
            hardware_bridge=hardware_bridge,
            command_transport=command_transport,
            link_manager=link_manager,
            runtime_wiring_stage2=stage2_wiring,
            safety_supervisor=safety_supervisor,
            snapshot_bus=snapshot_bus,
            status_sink=self.status_sink,
        )
        # ----------------------------------------------------
        # Runtime supervisor
        # ----------------------------------------------------
        runtime_supervisor = RemotePiRuntimeSupervisor(
            runtime_lifecycle=runtime_lifecycle,
            safety_supervisor=safety_supervisor,
            link_manager=link_manager,
            runtime_wiring_stage2=stage2_wiring,
            startup_orchestrator=startup_orchestrator,
            snapshot_bus=snapshot_bus,
            status_sink=self.status_sink,
        )
        bundle = RemotePiRuntimeBundle(
            state_store=state_store,
            mode_fsm=mode_fsm,
            event_router=event_router,
            runtime_lifecycle=runtime_lifecycle,
            safety_supervisor=safety_supervisor,
            snapshot_bus=snapshot_bus,
            hardware_bridge=hardware_bridge,
            stage2_wiring=stage2_wiring,
            integration_manager=integration_manager,
            command_transport=command_transport,
            mqtt_adapter=mqtt_adapter,
            link_manager=link_manager,
            inbound_router=inbound_router,
            startup_orchestrator=startup_orchestrator,
            runtime_supervisor=runtime_supervisor,
        )
        self._emit_status(
            "runtime_bootstrap/build_complete",
            mqtt_enabled=self.config.enable_mqtt_adapter,
            has_app=app is not None,
        )
        return bundle


# ============================================================
# MODULE-R047
# ============================================================

# runtime/remotepi_runtime_validation_suite.py
"""
MODULE-R047
RemotePi Runtime Validation Suite
---------------------------------

Purpose:
    Validation and smoke-test suite for RemotePi runtime architecture.

Responsibilities:
    - Verify runtime bootstrap integrity
    - Verify supervisor startup flow
    - Verify snapshot generation
    - Verify lifecycle transitions
    - Verify safety supervisor execution
    - Verify stage2/link/transport integration does not crash

Design goals:
    - Lightweight
    - Deterministic
    - No heavy external dependencies
    - Useful both in development and field diagnostics
"""
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional
# ============================================================
# DATA MODELS
# ============================================================
@dataclass
class ValidationResult:
    name: str
    ok: bool
    summary: str
    details: dict[str, Any] = field(default_factory=dict)
@dataclass
class ValidationReport:
    ts: float
    overall_ok: bool
    passed: int
    failed: int
    results: list[ValidationResult] = field(default_factory=list)
    def to_dict(self) -> dict[str, Any]:
        return {
            "ts": self.ts,
            "overall_ok": self.overall_ok,
            "passed": self.passed,
            "failed": self.failed,
            "results": [
                {
                    "name": r.name,
                    "ok": r.ok,
                    "summary": r.summary,
                    "details": dict(r.details),
                }
                for r in self.results
            ],
        }
# ============================================================
# MAIN CLASS
# ============================================================
class RemotePiRuntimeValidationSuite:
    def __init__(
        self,
        *,
        status_sink: Optional[Callable[[str, dict], None]] = None,
    ):
        self.status_sink = status_sink
    # --------------------------------------------------------
    # INTERNAL
    # --------------------------------------------------------
    def _emit_status(self, topic: str, **payload) -> None:
        if self.status_sink is not None:
            self.status_sink(topic, {
                "ts": time.time(),
                **payload,
            })
    def _ok(self, name: str, summary: str, **details) -> ValidationResult:
        self._emit_status("runtime_validation/pass", name=name, summary=summary, details=details)
        return ValidationResult(name=name, ok=True, summary=summary, details=details)
    def _fail(self, name: str, summary: str, **details) -> ValidationResult:
        self._emit_status("runtime_validation/fail", name=name, summary=summary, details=details)
        return ValidationResult(name=name, ok=False, summary=summary, details=details)
    def _safe(self, name: str, fn: Callable[[], Any]) -> ValidationResult:
        try:
            value = fn()
            return self._ok(name, "executed without exception", returned_type=type(value).__name__)
        except Exception as exc:
            return self._fail(name, f"exception: {exc}", error=str(exc))
    # --------------------------------------------------------
    # TESTS
    # --------------------------------------------------------
    def validate_bundle_presence(self, runtime_bundle) -> ValidationResult:
        required = [
            "state_store",
            "mode_fsm",
            "event_router",
            "runtime_lifecycle",
            "safety_supervisor",
            "snapshot_bus",
            "hardware_bridge",
            "stage2_wiring",
            "integration_manager",
            "command_transport",
            "link_manager",
            "inbound_router",
            "startup_orchestrator",
            "runtime_supervisor",
        ]
        missing = [name for name in required if not hasattr(runtime_bundle, name)]
        if missing:
            return self._fail(
                "bundle_presence",
                "runtime bundle missing required attributes",
                missing=missing,
            )
        return self._ok(
            "bundle_presence",
            "runtime bundle contains all required attributes",
            required_count=len(required),
        )
    def validate_startup_orchestrator(self, runtime_bundle) -> ValidationResult:
        orchestrator = runtime_bundle.startup_orchestrator
        try:
            ok = bool(orchestrator.startup())
        except Exception as exc:
            return self._fail("startup_orchestrator", f"startup exception: {exc}", error=str(exc))
        if not ok:
            data = orchestrator.to_dict() if hasattr(orchestrator, "to_dict") else {}
            return self._fail(
                "startup_orchestrator",
                "startup returned False",
                startup=data,
            )
        return self._ok(
            "startup_orchestrator",
            "startup completed successfully",
            startup=(orchestrator.to_dict() if hasattr(orchestrator, "to_dict") else {}),
        )
    def validate_runtime_supervisor(self, runtime_bundle) -> ValidationResult:
        supervisor = runtime_bundle.runtime_supervisor
        try:
            supervisor.tick()
            data = supervisor.to_dict() if hasattr(supervisor, "to_dict") else {}
        except Exception as exc:
            return self._fail("runtime_supervisor", f"tick exception: {exc}", error=str(exc))
        return self._ok(
            "runtime_supervisor",
            "supervisor tick executed",
            supervisor=data,
        )
    def validate_snapshot_bus(self, runtime_bundle) -> ValidationResult:
        snapshot_bus = runtime_bundle.snapshot_bus
        try:
            compact = snapshot_bus.build_compact_snapshot()
            service = snapshot_bus.build_service_snapshot()
        except Exception as exc:
            return self._fail("snapshot_bus", f"snapshot exception: {exc}", error=str(exc))
        if "overall_ok" not in compact:
            return self._fail(
                "snapshot_bus",
                "compact snapshot missing overall_ok",
                compact=compact,
            )
        return self._ok(
            "snapshot_bus",
            "compact and service snapshot generated",
            compact_keys=list(compact.keys()),
            service_keys=list(service.keys()),
        )
    def validate_lifecycle_transitions(self, runtime_bundle) -> ValidationResult:
        lifecycle = runtime_bundle.runtime_lifecycle
        try:
            lifecycle.enter_ready()
            ready_dict = lifecycle.to_dict()
            started = lifecycle.start_runtime()
            running_dict = lifecycle.to_dict()
            lifecycle.enter_fault("validation fault")
            fault_dict = lifecycle.to_dict()
            lifecycle.begin_recovery("validation recovery")
            lifecycle.finish_recovery()
            recovered_dict = lifecycle.to_dict()
        except Exception as exc:
            return self._fail("lifecycle_transitions", f"exception: {exc}", error=str(exc))
        return self._ok(
            "lifecycle_transitions",
            "lifecycle transitions executed",
            started=bool(started),
            ready_state=ready_dict.get("lifecycle_state"),
            running_state=running_dict.get("lifecycle_state"),
            fault_state=fault_dict.get("lifecycle_state"),
            recovered_state=recovered_dict.get("lifecycle_state"),
        )
    def validate_safety_supervisor(self, runtime_bundle) -> ValidationResult:
        safety = runtime_bundle.safety_supervisor
        try:
            decision = safety.tick()
            data = safety.get_last_decision_dict()
        except Exception as exc:
            return self._fail("safety_supervisor", f"tick exception: {exc}", error=str(exc))
        return self._ok(
            "safety_supervisor",
            "safety supervisor tick executed",
            decision_type=type(decision).__name__,
            last_decision=data,
        )
    def validate_stage2_wiring(self, runtime_bundle) -> ValidationResult:
        stage2 = runtime_bundle.stage2_wiring
        try:
            stage2.tick()
            data = stage2.get_status_dict()
        except Exception as exc:
            return self._fail("stage2_wiring", f"tick exception: {exc}", error=str(exc))
        return self._ok(
            "stage2_wiring",
            "stage2 tick executed",
            stage2=data,
        )
    def validate_link_manager(self, runtime_bundle) -> ValidationResult:
        link = runtime_bundle.link_manager
        try:
            link.tick()
            data = link.to_dict() if hasattr(link, "to_dict") else {}
        except Exception as exc:
            return self._fail("link_manager", f"tick exception: {exc}", error=str(exc))
        return self._ok(
            "link_manager",
            "link manager tick executed",
            link=data,
        )
    def validate_command_transport(self, runtime_bundle) -> ValidationResult:
        transport = runtime_bundle.command_transport
        try:
            connected_before = transport.is_connected()
            heartbeat_ok = transport.send_heartbeat()
            transport.poll_once()
            data = transport.to_dict()
        except Exception as exc:
            return self._fail("command_transport", f"transport exception: {exc}", error=str(exc))
        return self._ok(
            "command_transport",
            "transport basic operations executed",
            connected_before=connected_before,
            heartbeat_ok=heartbeat_ok,
            transport=data,
        )
    def validate_hardware_bridge_snapshot(self, runtime_bundle) -> ValidationResult:
        bridge = runtime_bundle.hardware_bridge
        try:
            snap = bridge.to_dict()
        except Exception as exc:
            return self._fail("hardware_bridge_snapshot", f"snapshot exception: {exc}", error=str(exc))
        required_keys = [
            "left_x",
            "left_y",
            "right_x",
            "right_y",
            "battery_voltage",
            "local_temp_c",
            "battery_temp_c",
        ]
        missing = [k for k in required_keys if k not in snap]
        if missing:
            return self._fail(
                "hardware_bridge_snapshot",
                "hardware bridge snapshot missing required keys",
                missing=missing,
            )
        return self._ok(
            "hardware_bridge_snapshot",
            "hardware bridge snapshot generated",
            keys=list(snap.keys()),
        )
    # --------------------------------------------------------
    # SUITE
    # --------------------------------------------------------
    def run_full_validation(self, runtime_bundle) -> ValidationReport:
        results = [
            self.validate_bundle_presence(runtime_bundle),
            self.validate_startup_orchestrator(runtime_bundle),
            self.validate_runtime_supervisor(runtime_bundle),
            self.validate_snapshot_bus(runtime_bundle),
            self.validate_lifecycle_transitions(runtime_bundle),
            self.validate_safety_supervisor(runtime_bundle),
            self.validate_stage2_wiring(runtime_bundle),
            self.validate_link_manager(runtime_bundle),
            self.validate_command_transport(runtime_bundle),
            self.validate_hardware_bridge_snapshot(runtime_bundle),
        ]
        passed = sum(1 for r in results if r.ok)
        failed = sum(1 for r in results if not r.ok)
        overall_ok = failed == 0
        report = ValidationReport(
            ts=time.time(),
            overall_ok=overall_ok,
            passed=passed,
            failed=failed,
            results=results,
        )
        self._emit_status(
            "runtime_validation/report_ready",
            overall_ok=overall_ok,
            passed=passed,
            failed=failed,
        )
        return report


# ============================================================
# MODULE-R048
# ============================================================

# runtime/remotepi_fault_injection_harness.py
"""
MODULE-R048
RemotePi Fault Injection Harness
--------------------------------

Purpose:
    Controlled fault injection tool for RemotePi runtime validation.

Responsibilities:
    - Inject synthetic battery / thermal / ADC / UI / link / joystick faults
    - Drive state store into controlled fault conditions
    - Trigger safety supervisor / lifecycle / supervisor reactions
    - Support deterministic field validation scenarios

Design goals:
    - Safe and reversible
    - Deterministic
    - Independent from transport/hardware when needed
"""
import time
from dataclasses import dataclass
from typing import Callable, Optional
# ============================================================
# DATA MODELS
# ============================================================
@dataclass
class FaultInjectionConfig:
    emit_status_logs: bool = True
# ============================================================
# MAIN CLASS
# ============================================================
class RemotePiFaultInjectionHarness:
    def __init__(
        self,
        *,
        state_store=None,
        runtime_lifecycle=None,
        safety_supervisor=None,
        runtime_supervisor=None,
        link_manager=None,
        network_status_override_hook: Optional[Callable[[dict], None]] = None,
        ui_health_override_hook: Optional[Callable[[bool], None]] = None,
        status_sink: Optional[Callable[[str, dict], None]] = None,
        config: Optional[FaultInjectionConfig] = None,
    ):
        self.state_store = state_store
        self.runtime_lifecycle = runtime_lifecycle
        self.safety_supervisor = safety_supervisor
        self.runtime_supervisor = runtime_supervisor
        self.link_manager = link_manager
        self.network_status_override_hook = network_status_override_hook
        self.ui_health_override_hook = ui_health_override_hook
        self.status_sink = status_sink
        self.config = config or FaultInjectionConfig()
        self._last_fault_name: Optional[str] = None
        self._last_fault_ts: float = 0.0
        self._active_faults: set[str] = set()
    # --------------------------------------------------------
    # INTERNAL
    # --------------------------------------------------------
    def _emit_status(self, topic: str, **payload) -> None:
        if not self.config.emit_status_logs:
            return
        if self.status_sink is not None:
            self.status_sink(topic, {
                "ts": time.time(),
                **payload,
            })
    def _mark_fault(self, name: str) -> None:
        self._last_fault_name = str(name)
        self._last_fault_ts = time.time()
        self._active_faults.add(str(name))
        self._emit_status(
            "fault_injection/injected",
            fault_name=name,
            active_faults=sorted(self._active_faults),
        )
    def _reapply_runtime(self) -> None:
        if self.safety_supervisor is not None and hasattr(self.safety_supervisor, "tick"):
            try:
                self.safety_supervisor.tick()
            except Exception as exc:
                self._emit_status("fault_injection/safety_tick_error", error=str(exc))
        if self.runtime_lifecycle is not None and hasattr(self.runtime_lifecycle, "auto_align_from_state"):
            try:
                self.runtime_lifecycle.auto_align_from_state()
            except Exception as exc:
                self._emit_status("fault_injection/lifecycle_align_error", error=str(exc))
        if self.runtime_supervisor is not None and hasattr(self.runtime_supervisor, "tick"):
            try:
                self.runtime_supervisor.tick()
            except Exception as exc:
                self._emit_status("fault_injection/supervisor_tick_error", error=str(exc))
    # --------------------------------------------------------
    # BATTERY FAULTS
    # --------------------------------------------------------
    def inject_battery_warning(self) -> None:
        if self.state_store is None:
            return
        self.state_store.update_battery(
            voltage=38.0,
            percent_est=35.0,
            bucket="STATE_BATTERY_WARNING",
        )
        self._mark_fault("BATTERY_WARNING")
        self._reapply_runtime()
    def inject_battery_fault(self) -> None:
        if self.state_store is None:
            return
        self.state_store.update_battery(
            voltage=20.0,
            percent_est=15.0,
            bucket="STATE_BATTERY_CRITICAL",
        )
        self._mark_fault("BATTERY_FAULT")
        self._reapply_runtime()
    def inject_battery_shutdown(self) -> None:
        if self.state_store is None:
            return
        self.state_store.update_battery(
            voltage=10.0,
            percent_est=5.0,
            bucket="STATE_BATTERY_SHUTDOWN",
        )
        self._mark_fault("BATTERY_SHUTDOWN")
        self._reapply_runtime()
    # --------------------------------------------------------
    # THERMAL FAULTS
    # --------------------------------------------------------
    def inject_local_overtemp_warning(self) -> None:
        if self.state_store is None:
            return
        self.state_store.update_thermal(
            local_temp_c=58.0,
            battery_temp_c=30.0,
            thermal_state="STATE_TEMP_WARNING",
        )
        self._mark_fault("LOCAL_OVERTEMP_WARNING")
        self._reapply_runtime()
    def inject_local_overtemp_fault(self) -> None:
        if self.state_store is None:
            return
        self.state_store.update_thermal(
            local_temp_c=68.0,
            battery_temp_c=35.0,
            thermal_state="STATE_TEMP_FAULT",
        )
        self._mark_fault("LOCAL_OVERTEMP_FAULT")
        self._reapply_runtime()
    def inject_local_overtemp_shutdown(self) -> None:
        if self.state_store is None:
            return
        self.state_store.update_thermal(
            local_temp_c=80.0,
            battery_temp_c=36.0,
            thermal_state="STATE_TEMP_SHUTDOWN",
        )
        self._mark_fault("LOCAL_OVERTEMP_SHUTDOWN")
        self._reapply_runtime()
    def inject_battery_overtemp_fault(self) -> None:
        if self.state_store is None:
            return
        self.state_store.update_thermal(
            local_temp_c=32.0,
            battery_temp_c=62.0,
            thermal_state="STATE_TEMP_FAULT",
        )
        self._mark_fault("BATTERY_OVERTEMP_FAULT")
        self._reapply_runtime()
    # --------------------------------------------------------
    # NETWORK / ADC / UI FAULTS
    # --------------------------------------------------------
    def inject_adc1_offline(self) -> None:
        if self.network_status_override_hook is not None:
            self.network_status_override_hook({
                "adc1_online": False,
            })
        self._mark_fault("ADC1_OFFLINE")
        self._reapply_runtime()
    def inject_adc2_offline(self) -> None:
        if self.network_status_override_hook is not None:
            self.network_status_override_hook({
                "adc2_online": False,
            })
        self._mark_fault("ADC2_OFFLINE")
        self._reapply_runtime()
    def inject_i2c_fault(self) -> None:
        if self.network_status_override_hook is not None:
            self.network_status_override_hook({
                "i2c_ok": False,
            })
        self._mark_fault("I2C_FAULT")
        self._reapply_runtime()
    def inject_master_link_lost(self) -> None:
        if self.network_status_override_hook is not None:
            self.network_status_override_hook({
                "master_link_ok": False,
                "network_online": False,
                "network_weak": True,
            })
        if self.link_manager is not None and hasattr(self.link_manager, "note_error"):
            try:
                self.link_manager.note_error("fault_injection_master_link_lost")
            except Exception:
                pass
        self._mark_fault("MASTER_LINK_LOST")
        self._reapply_runtime()
    def inject_ui_health_fail(self) -> None:
        if self.ui_health_override_hook is not None:
            self.ui_health_override_hook(False)
        self._mark_fault("UI_HEALTH_FAIL")
        self._reapply_runtime()
    # --------------------------------------------------------
    # JOYSTICK ANOMALY
    # --------------------------------------------------------
    def inject_joystick_stuck(self) -> None:
        if self.state_store is None:
            return
        # normalized high absolute values
        self.state_store.update_left_joystick(0.95, 0.95)
        self.state_store.update_right_joystick(0.92, 0.91)
        self._mark_fault("JOYSTICK_STUCK")
        self._reapply_runtime()
    # --------------------------------------------------------
    # MANUAL SAFETY/FSM/LIFECYCLE FAULTS
    # --------------------------------------------------------
    def inject_fault_lock(self, summary: str = "Manual injected fault lock.") -> None:
        if self.runtime_lifecycle is not None and hasattr(self.runtime_lifecycle, "enter_fault"):
            self.runtime_lifecycle.enter_fault(summary)
        self._mark_fault("FAULT_LOCK")
        self._reapply_runtime()
    def inject_shutdown_request(self, summary: str = "Manual injected shutdown request.") -> None:
        if self.runtime_lifecycle is not None and hasattr(self.runtime_lifecycle, "request_shutdown"):
            self.runtime_lifecycle.request_shutdown(summary)
        self._mark_fault("SHUTDOWN_REQUEST")
        self._reapply_runtime()
    # --------------------------------------------------------
    # RESET
    # --------------------------------------------------------
    def clear_injected_faults(self) -> None:
        self._active_faults.clear()
        if self.state_store is not None:
            try:
                self.state_store.update_battery(
                    voltage=55.0,
                    percent_est=100.0,
                    bucket="STATE_BATTERY_NORMAL",
                )
                self.state_store.update_thermal(
                    local_temp_c=28.0,
                    battery_temp_c=29.0,
                    thermal_state="STATE_TEMP_NORMAL",
                )
                self.state_store.update_network(
                    wifi_connected=True,
                    bluetooth_connected=False,
                    ethernet_link=False,
                    master_link_ok=True,
                    network_online=True,
                    network_weak=False,
                )
                self.state_store.clear_faults()
                self.state_store.clear_warnings()
                self.state_store.clear_fault_latch()
                self.state_store.update_safety(
                    severity="NORMAL",
                    primary_state="STATE_READY",
                    accept_user_control=True,
                    allow_new_motion_commands=False,
                    request_shutdown=False,
                    ui_fault_latched=False,
                    summary="Fault injection cleared.",
                    warnings=[],
                    faults=[],
                )
            except Exception as exc:
                self._emit_status("fault_injection/clear_state_store_error", error=str(exc))
        if self.ui_health_override_hook is not None:
            try:
                self.ui_health_override_hook(True)
            except Exception:
                pass
        if self.network_status_override_hook is not None:
            try:
                self.network_status_override_hook({
                    "adc1_online": True,
                    "adc2_online": True,
                    "i2c_ok": True,
                    "master_link_ok": True,
                    "network_online": True,
                    "network_weak": False,
                })
            except Exception:
                pass
        if self.runtime_lifecycle is not None:
            try:
                if hasattr(self.runtime_lifecycle, "begin_recovery"):
                    self.runtime_lifecycle.begin_recovery("Fault injection clear recovery.")
                if hasattr(self.runtime_lifecycle, "finish_recovery"):
                    self.runtime_lifecycle.finish_recovery()
            except Exception:
                pass
        self._emit_status(
            "fault_injection/cleared",
            active_faults=[],
        )
    # --------------------------------------------------------
    # SNAPSHOT
    # --------------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "last_fault_name": self._last_fault_name,
            "last_fault_ts": self._last_fault_ts,
            "active_faults": sorted(self._active_faults),
        }


# ============================================================
# MODULE-R049
# ============================================================

# runtime/remotepi_diagnostics_snapshot_exporter.py
"""
MODULE-R049
RemotePi Diagnostics Snapshot Exporter
--------------------------------------

Purpose:
    Export RemotePi runtime snapshot data into service/diagnostic friendly formats.

Responsibilities:
    - Read from RemotePiRuntimeSnapshotBus
    - Build compact diagnostics reports
    - Build full service diagnostics reports
    - Export JSON/text summaries
    - Provide consistent field-service output

Design goals:
    - Human-readable
    - Machine-readable
    - Safe fallback behavior
"""
import json
import time
from dataclasses import dataclass
from typing import Any, Callable, Optional
# ============================================================
# DATA MODELS
# ============================================================
@dataclass
class DiagnosticsExporterConfig:
    emit_status_logs: bool = True
    indent_json: int = 2
    include_sections_in_text: bool = True
# ============================================================
# MAIN CLASS
# ============================================================
class RemotePiDiagnosticsSnapshotExporter:
    def __init__(
        self,
        *,
        snapshot_bus,
        status_sink: Optional[Callable[[str, dict], None]] = None,
        config: Optional[DiagnosticsExporterConfig] = None,
    ):
        self.snapshot_bus = snapshot_bus
        self.status_sink = status_sink
        self.config = config or DiagnosticsExporterConfig()
        self._last_export_ts: float = 0.0
        self._last_error: Optional[str] = None
    # --------------------------------------------------------
    # INTERNAL
    # --------------------------------------------------------
    def _emit_status(self, topic: str, **payload) -> None:
        if not self.config.emit_status_logs:
            return
        if self.status_sink is not None:
            self.status_sink(topic, {
                "ts": time.time(),
                **payload,
            })
    def _safe_snapshot(self) -> dict[str, Any]:
        try:
            report = self.snapshot_bus.build_service_snapshot()
            self._last_export_ts = time.time()
            return dict(report)
        except Exception as exc:
            self._last_error = str(exc)
            self._emit_status(
                "diagnostics_exporter/snapshot_error",
                error=str(exc),
            )
            return {
                "created_ts": time.time(),
                "overall_ok": False,
                "overall_summary": f"snapshot export failed: {exc}",
                "warnings": [],
                "faults": [str(exc)],
                "sections": [],
            }
    # --------------------------------------------------------
    # EXPORT BUILDERS
    # --------------------------------------------------------
    def build_compact_report(self) -> dict[str, Any]:
        snap = self._safe_snapshot()
        report = {
            "created_ts": snap.get("created_ts", time.time()),
            "overall_ok": bool(snap.get("overall_ok", False)),
            "overall_summary": str(snap.get("overall_summary", "")),
            "warning_count": len(snap.get("warnings", [])),
            "fault_count": len(snap.get("faults", [])),
            "warnings": list(snap.get("warnings", [])),
            "faults": list(snap.get("faults", [])),
        }
        self._emit_status(
            "diagnostics_exporter/compact_report",
            overall_ok=report["overall_ok"],
            warning_count=report["warning_count"],
            fault_count=report["fault_count"],
        )
        return report
    def build_full_report(self) -> dict[str, Any]:
        snap = self._safe_snapshot()
        report = {
            "report_type": "REMOTEPI_FULL_DIAGNOSTICS",
            "created_ts": snap.get("created_ts", time.time()),
            "overall_ok": bool(snap.get("overall_ok", False)),
            "overall_summary": str(snap.get("overall_summary", "")),
            "warnings": list(snap.get("warnings", [])),
            "faults": list(snap.get("faults", [])),
            "state_store": dict(snap.get("state_store", {})),
            "mode_fsm": dict(snap.get("mode_fsm", {})),
            "lifecycle": dict(snap.get("lifecycle", {})),
            "safety_supervisor": dict(snap.get("safety_supervisor", {})),
            "watchdog": dict(snap.get("watchdog", {})),
            "integration_manager": dict(snap.get("integration_manager", {})),
            "stage2_wiring": dict(snap.get("stage2_wiring", {})),
            "sections": list(snap.get("sections", [])),
        }
        self._emit_status(
            "diagnostics_exporter/full_report",
            overall_ok=report["overall_ok"],
            section_count=len(report["sections"]),
        )
        return report
    # --------------------------------------------------------
    # JSON EXPORT
    # --------------------------------------------------------
    def export_compact_json(self) -> str:
        report = self.build_compact_report()
        return json.dumps(report, ensure_ascii=False, indent=self.config.indent_json)
    def export_full_json(self) -> str:
        report = self.build_full_report()
        return json.dumps(report, ensure_ascii=False, indent=self.config.indent_json)
    # --------------------------------------------------------
    # TEXT EXPORT
    # --------------------------------------------------------
    def export_text_summary(self) -> str:
        snap = self._safe_snapshot()
        lines = [
            "REMOTEPI DIAGNOSTICS SUMMARY",
            f"created_ts: {snap.get('created_ts', time.time())}",
            f"overall_ok: {snap.get('overall_ok', False)}",
            f"overall_summary: {snap.get('overall_summary', '')}",
            f"warning_count: {len(snap.get('warnings', []))}",
            f"fault_count: {len(snap.get('faults', []))}",
        ]
        warnings = list(snap.get("warnings", []))
        faults = list(snap.get("faults", []))
        if warnings:
            lines.append("warnings:")
            for item in warnings:
                lines.append(f"  - {item}")
        if faults:
            lines.append("faults:")
            for item in faults:
                lines.append(f"  - {item}")
        if self.config.include_sections_in_text:
            sections = list(snap.get("sections", []))
            if sections:
                lines.append("sections:")
                for section in sections:
                    if isinstance(section, dict):
                        lines.append(
                            f"  - {section.get('name', 'unknown')}: "
                            f"ok={section.get('ok', False)} | "
                            f"{section.get('summary', '')}"
                        )
        text = "\n".join(lines)
        self._emit_status(
            "diagnostics_exporter/text_summary",
            line_count=len(lines),
        )
        return text
    # --------------------------------------------------------
    # SERVICE REPORT
    # --------------------------------------------------------
    def build_service_ticket_payload(self) -> dict[str, Any]:
        snap = self._safe_snapshot()
        state_store = dict(snap.get("state_store", {}))
        lifecycle = dict(snap.get("lifecycle", {}))
        safety = dict(snap.get("safety_supervisor", {}))
        integration = dict(snap.get("integration_manager", {}))
        stage2 = dict(snap.get("stage2_wiring", {}))
        payload = {
            "ticket_type": "REMOTEPI_SERVICE_DIAGNOSTICS",
            "created_ts": snap.get("created_ts", time.time()),
            "overall_ok": bool(snap.get("overall_ok", False)),
            "overall_summary": str(snap.get("overall_summary", "")),
            "active_mode": state_store.get("mode", {}).get("active_mode", "UNKNOWN"),
            "system_running": state_store.get("mode", {}).get("system_running", False),
            "battery_bucket": state_store.get("battery", {}).get("bucket", "UNKNOWN"),
            "thermal_state": state_store.get("thermal", {}).get("thermal_state", "UNKNOWN"),
            "lifecycle_state": lifecycle.get("lifecycle_state", "UNKNOWN"),
            "safety_level": safety.get("level", "UNKNOWN"),
            "bridge_mode": integration.get("bridge_mode", "UNKNOWN"),
            "stage2_ready": {
                "telemetry_manager_ready": stage2.get("telemetry_manager_ready", False),
                "local_command_executor_ready": stage2.get("local_command_executor_ready", False),
                "watchdog_supervisor_ready": stage2.get("watchdog_supervisor_ready", False),
                "safe_shutdown_manager_ready": stage2.get("safe_shutdown_manager_ready", False),
            },
            "warnings": list(snap.get("warnings", [])),
            "faults": list(snap.get("faults", [])),
        }
        self._emit_status(
            "diagnostics_exporter/service_ticket_payload",
            overall_ok=payload["overall_ok"],
            safety_level=payload["safety_level"],
            lifecycle_state=payload["lifecycle_state"],
        )
        return payload
    # --------------------------------------------------------
    # SNAPSHOT
    # --------------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return {
            "last_export_ts": self._last_export_ts,
            "last_error": self._last_error,
            "config": {
                "indent_json": self.config.indent_json,
                "include_sections_in_text": self.config.include_sections_in_text,
            },
        }


# ============================================================
# MODULE-R050
# ============================================================

# runtime/remotepi_service_mode_console.py
"""
MODULE-R050
RemotePi Service Mode Console
-----------------------------

Purpose:
    Provide a controlled service/maintenance console for RemotePi runtime.

Responsibilities:
    - Read runtime status
    - Trigger maintenance actions
    - Run diagnostics export
    - Trigger fault injection scenarios
    - Clear injected faults
    - Run simple output tests
    - Assist field-service workflows

Design goals:
    - Safe command surface
    - Human-friendly responses
    - Non-invasive to runtime architecture
"""
import time
from dataclasses import dataclass
from typing import Any, Callable, Optional
# ============================================================
# DATA MODELS
# ============================================================
@dataclass
class ServiceConsoleConfig:
    emit_status_logs: bool = True
    allow_fault_injection: bool = True
    allow_output_tests: bool = True
# ============================================================
# MAIN CLASS
# ============================================================
class RemotePiServiceModeConsole:
    def __init__(
        self,
        *,
        runtime_bundle=None,
        diagnostics_exporter=None,
        fault_injection_harness=None,
        status_sink: Optional[Callable[[str, dict], None]] = None,
        config: Optional[ServiceConsoleConfig] = None,
    ):
        self.runtime_bundle = runtime_bundle
        self.diagnostics_exporter = diagnostics_exporter
        self.fault_injection_harness = fault_injection_harness
        self.status_sink = status_sink
        self.config = config or ServiceConsoleConfig()
        self._last_command: Optional[str] = None
        self._last_result: Optional[dict] = None
        self._last_error: Optional[str] = None
    # --------------------------------------------------------
    # INTERNAL
    # --------------------------------------------------------
    def _emit_status(self, topic: str, **payload) -> None:
        if not self.config.emit_status_logs:
            return
        if self.status_sink is not None:
            self.status_sink(topic, {
                "ts": time.time(),
                **payload,
            })
    def _result(self, ok: bool, command: str, summary: str, **data) -> dict[str, Any]:
        self._last_command = command
        self._last_result = {
            "ok": ok,
            "command": command,
            "summary": summary,
            "data": dict(data),
            "ts": time.time(),
        }
        if not ok:
            self._last_error = summary
        self._emit_status(
            "service_console/result",
            ok=ok,
            command=command,
            summary=summary,
        )
        return dict(self._last_result)
    def _get(self, name: str):
        if self.runtime_bundle is None:
            return None
        return getattr(self.runtime_bundle, name, None)
    # --------------------------------------------------------
    # STATUS / READS
    # --------------------------------------------------------
    def cmd_status(self) -> dict[str, Any]:
        supervisor = self._get("runtime_supervisor")
        if supervisor is None or not hasattr(supervisor, "to_dict"):
            return self._result(False, "status", "runtime_supervisor unavailable")
        try:
            data = supervisor.to_dict()
            return self._result(True, "status", "runtime supervisor status collected", supervisor=data)
        except Exception as exc:
            return self._result(False, "status", f"status failed: {exc}")
    def cmd_snapshot_compact(self) -> dict[str, Any]:
        snapshot_bus = self._get("snapshot_bus")
        if snapshot_bus is None or not hasattr(snapshot_bus, "build_compact_snapshot"):
            return self._result(False, "snapshot_compact", "snapshot_bus unavailable")
        try:
            data = snapshot_bus.build_compact_snapshot()
            return self._result(True, "snapshot_compact", "compact snapshot collected", snapshot=data)
        except Exception as exc:
            return self._result(False, "snapshot_compact", f"compact snapshot failed: {exc}")
    def cmd_snapshot_full(self) -> dict[str, Any]:
        snapshot_bus = self._get("snapshot_bus")
        if snapshot_bus is None or not hasattr(snapshot_bus, "build_service_snapshot"):
            return self._result(False, "snapshot_full", "snapshot_bus unavailable")
        try:
            data = snapshot_bus.build_service_snapshot()
            return self._result(True, "snapshot_full", "full snapshot collected", snapshot=data)
        except Exception as exc:
            return self._result(False, "snapshot_full", f"full snapshot failed: {exc}")
    def cmd_diagnostics_text(self) -> dict[str, Any]:
        if self.diagnostics_exporter is None or not hasattr(self.diagnostics_exporter, "export_text_summary"):
            return self._result(False, "diagnostics_text", "diagnostics_exporter unavailable")
        try:
            text = self.diagnostics_exporter.export_text_summary()
            return self._result(True, "diagnostics_text", "text diagnostics exported", text=text)
        except Exception as exc:
            return self._result(False, "diagnostics_text", f"diagnostics text failed: {exc}")
    def cmd_diagnostics_json(self) -> dict[str, Any]:
        if self.diagnostics_exporter is None or not hasattr(self.diagnostics_exporter, "export_full_json"):
            return self._result(False, "diagnostics_json", "diagnostics_exporter unavailable")
        try:
            text = self.diagnostics_exporter.export_full_json()
            return self._result(True, "diagnostics_json", "json diagnostics exported", json=text)
        except Exception as exc:
            return self._result(False, "diagnostics_json", f"diagnostics json failed: {exc}")
    # --------------------------------------------------------
    # STARTUP / RECOVERY / SHUTDOWN
    # --------------------------------------------------------
    def cmd_startup(self) -> dict[str, Any]:
        orchestrator = self._get("startup_orchestrator")
        if orchestrator is None or not hasattr(orchestrator, "startup"):
            return self._result(False, "startup", "startup_orchestrator unavailable")
        try:
            ok = bool(orchestrator.startup())
            return self._result(ok, "startup", "startup executed", startup=orchestrator.to_dict() if hasattr(orchestrator, "to_dict") else {})
        except Exception as exc:
            return self._result(False, "startup", f"startup failed: {exc}")
    def cmd_recovery(self) -> dict[str, Any]:
        lifecycle = self._get("runtime_lifecycle")
        if lifecycle is None:
            return self._result(False, "recovery", "runtime_lifecycle unavailable")
        try:
            started = False
            finished = False
            if hasattr(lifecycle, "begin_recovery"):
                started = bool(lifecycle.begin_recovery("Service console recovery"))
            if hasattr(lifecycle, "finish_recovery"):
                finished = bool(lifecycle.finish_recovery())
            return self._result(
                started or finished,
                "recovery",
                "recovery attempted",
                started=started,
                finished=finished,
                lifecycle=lifecycle.to_dict() if hasattr(lifecycle, "to_dict") else {},
            )
        except Exception as exc:
            return self._result(False, "recovery", f"recovery failed: {exc}")
    def cmd_shutdown(self) -> dict[str, Any]:
        supervisor = self._get("runtime_supervisor")
        if supervisor is None or not hasattr(supervisor, "request_shutdown"):
            return self._result(False, "shutdown", "runtime_supervisor unavailable")
        try:
            supervisor.request_shutdown("Service console shutdown request.")
            return self._result(True, "shutdown", "shutdown requested", supervisor=supervisor.to_dict() if hasattr(supervisor, "to_dict") else {})
        except Exception as exc:
            return self._result(False, "shutdown", f"shutdown failed: {exc}")
    # --------------------------------------------------------
    # OUTPUT TESTS
    # --------------------------------------------------------
    def cmd_test_output(self, output_name: str, state: bool) -> dict[str, Any]:
        if not self.config.allow_output_tests:
            return self._result(False, "test_output", "output tests disabled", output_name=output_name)
        hardware_bridge = self._get("hardware_bridge")
        if hardware_bridge is None:
            return self._result(False, "test_output", "hardware_bridge unavailable", output_name=output_name)
        name = str(output_name).upper()
        st = bool(state)
        try:
            if name == "PARKING_LIGHT":
                hardware_bridge.set_parking_light(st)
            elif name == "LOW_BEAM_LIGHT":
                hardware_bridge.set_low_beam_light(st)
            elif name == "HIGH_BEAM_LIGHT":
                hardware_bridge.set_high_beam_light(st)
            elif name == "SIGNAL_LHR_LIGHT":
                hardware_bridge.set_signal_lhr_light(st)
            elif name == "RIG_FLOOR_LIGHT":
                hardware_bridge.set_rig_floor_light(st)
            elif name == "ROTATION_LIGHT":
                hardware_bridge.set_rotation_light(st)
            elif name == "REMOTE_FAN":
                hardware_bridge.set_remote_fan(st)
            elif name == "REMOTE_BUZZER":
                hardware_bridge.set_remote_buzzer(st)
            else:
                return self._result(False, "test_output", "unknown output name", output_name=name)
            return self._result(True, "test_output", "output test executed", output_name=name, state=st)
        except Exception as exc:
            return self._result(False, "test_output", f"output test failed: {exc}", output_name=name)
    # --------------------------------------------------------
    # FAULT INJECTION
    # --------------------------------------------------------
    def cmd_inject_fault(self, fault_name: str) -> dict[str, Any]:
        if not self.config.allow_fault_injection:
            return self._result(False, "inject_fault", "fault injection disabled", fault_name=fault_name)
        if self.fault_injection_harness is None:
            return self._result(False, "inject_fault", "fault_injection_harness unavailable", fault_name=fault_name)
        fault = str(fault_name).upper()
        mapping = {
            "BATTERY_WARNING": "inject_battery_warning",
            "BATTERY_FAULT": "inject_battery_fault",
            "BATTERY_SHUTDOWN": "inject_battery_shutdown",
            "LOCAL_OVERTEMP_WARNING": "inject_local_overtemp_warning",
            "LOCAL_OVERTEMP_FAULT": "inject_local_overtemp_fault",
            "LOCAL_OVERTEMP_SHUTDOWN": "inject_local_overtemp_shutdown",
            "BATTERY_OVERTEMP_FAULT": "inject_battery_overtemp_fault",
            "ADC1_OFFLINE": "inject_adc1_offline",
            "ADC2_OFFLINE": "inject_adc2_offline",
            "I2C_FAULT": "inject_i2c_fault",
            "MASTER_LINK_LOST": "inject_master_link_lost",
            "UI_HEALTH_FAIL": "inject_ui_health_fail",
            "JOYSTICK_STUCK": "inject_joystick_stuck",
            "FAULT_LOCK": "inject_fault_lock",
            "SHUTDOWN_REQUEST": "inject_shutdown_request",
        }
        method_name = mapping.get(fault)
        if method_name is None or not hasattr(self.fault_injection_harness, method_name):
            return self._result(False, "inject_fault", "unknown injectable fault", fault_name=fault)
        try:
            getattr(self.fault_injection_harness, method_name)()
            return self._result(
                True,
                "inject_fault",
                "fault injection executed",
                fault_name=fault,
                harness=self.fault_injection_harness.to_dict() if hasattr(self.fault_injection_harness, "to_dict") else {},
            )
        except Exception as exc:
            return self._result(False, "inject_fault", f"fault injection failed: {exc}", fault_name=fault)
    def cmd_clear_injected_faults(self) -> dict[str, Any]:
        if self.fault_injection_harness is None or not hasattr(self.fault_injection_harness, "clear_injected_faults"):
            return self._result(False, "clear_injected_faults", "fault_injection_harness unavailable")
        try:
            self.fault_injection_harness.clear_injected_faults()
            return self._result(
                True,
                "clear_injected_faults",
                "injected faults cleared",
                harness=self.fault_injection_harness.to_dict() if hasattr(self.fault_injection_harness, "to_dict") else {},
            )
        except Exception as exc:
            return self._result(False, "clear_injected_faults", f"clear faults failed: {exc}")
    # --------------------------------------------------------
    # GENERIC DISPATCH
    # --------------------------------------------------------
    def run_command(self, command_name: str, **kwargs) -> dict[str, Any]:
        cmd = str(command_name).lower().strip()
        if cmd == "status":
            return self.cmd_status()
        if cmd == "snapshot_compact":
            return self.cmd_snapshot_compact()
        if cmd == "snapshot_full":
            return self.cmd_snapshot_full()
        if cmd == "diagnostics_text":
            return self.cmd_diagnostics_text()
        if cmd == "diagnostics_json":
            return self.cmd_diagnostics_json()
        if cmd == "startup":
            return self.cmd_startup()
        if cmd == "recovery":
            return self.cmd_recovery()
        if cmd == "shutdown":
            return self.cmd_shutdown()
        if cmd == "test_output":
            return self.cmd_test_output(
                kwargs.get("output_name", ""),
                bool(kwargs.get("state", False)),
            )
        if cmd == "inject_fault":
            return self.cmd_inject_fault(kwargs.get("fault_name", ""))
        if cmd == "clear_injected_faults":
            return self.cmd_clear_injected_faults()
        return self._result(False, "run_command", "unknown service console command", command_name=cmd)
    # --------------------------------------------------------
    # SNAPSHOT
    # --------------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return {
            "last_command": self._last_command,
            "last_result": self._last_result,
            "last_error": self._last_error,
            "config": {
                "allow_fault_injection": self.config.allow_fault_injection,
                "allow_output_tests": self.config.allow_output_tests,
            },
        }


# ============================================================
# MODULE-R051
# ============================================================

# runtime/remotepi_runtime_health_scorer.py
"""
MODULE-R051
RemotePi Runtime Health Scorer
------------------------------

Purpose:
    Compute a quantitative runtime health score for RemotePi.

Responsibilities:
    - Read runtime snapshot/state inputs
    - Score lifecycle / safety / link / stage2 / supervisor health
    - Produce a weighted health score
    - Provide a simple operational grade

Design goals:
    - Deterministic
    - Explainable deductions
    - Useful for service diagnostics and field health checks
"""
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional
# ============================================================
# DATA MODELS
# ============================================================
@dataclass
class RuntimeHealthScorerConfig:
    emit_status_logs: bool = True
    max_score: int = 100
@dataclass
class HealthScoreResult:
    ts: float
    score: int
    grade: str
    overall_ok: bool
    deductions: list[dict[str, Any]] = field(default_factory=list)
    summary: str = ""
# ============================================================
# MAIN CLASS
# ============================================================
class RemotePiRuntimeHealthScorer:
    def __init__(
        self,
        *,
        snapshot_bus=None,
        diagnostics_exporter=None,
        status_sink: Optional[Callable[[str, dict], None]] = None,
        config: Optional[RuntimeHealthScorerConfig] = None,
    ):
        self.snapshot_bus = snapshot_bus
        self.diagnostics_exporter = diagnostics_exporter
        self.status_sink = status_sink
        self.config = config or RuntimeHealthScorerConfig()
        self._last_result: Optional[HealthScoreResult] = None
        self._last_error: Optional[str] = None
    # --------------------------------------------------------
    # INTERNAL
    # --------------------------------------------------------
    def _emit_status(self, topic: str, **payload) -> None:
        if not self.config.emit_status_logs:
            return
        if self.status_sink is not None:
            self.status_sink(topic, {
                "ts": time.time(),
                **payload,
            })
    def _safe_snapshot(self) -> dict[str, Any]:
        try:
            if self.snapshot_bus is not None and hasattr(self.snapshot_bus, "build_service_snapshot"):
                return dict(self.snapshot_bus.build_service_snapshot())
            if self.diagnostics_exporter is not None and hasattr(self.diagnostics_exporter, "build_full_report"):
                return dict(self.diagnostics_exporter.build_full_report())
            return {
                "overall_ok": False,
                "overall_summary": "No snapshot source available.",
                "faults": ["NO_SNAPSHOT_SOURCE"],
                "warnings": [],
            }
        except Exception as exc:
            self._last_error = str(exc)
            self._emit_status("health_scorer/snapshot_error", error=str(exc))
            return {
                "overall_ok": False,
                "overall_summary": f"Snapshot read failed: {exc}",
                "faults": [str(exc)],
                "warnings": [],
            }
    def _deduct(self, deductions: list[dict[str, Any]], points: int, reason: str, **data) -> None:
        deductions.append({
            "points": int(points),
            "reason": reason,
            "data": dict(data),
        })
    def _grade(self, score: int) -> str:
        if score >= 90:
            return "A"
        if score >= 75:
            return "B"
        if score >= 60:
            return "C"
        if score >= 40:
            return "D"
        return "F"
    # --------------------------------------------------------
    # SCORING
    # --------------------------------------------------------
    def compute(self) -> HealthScoreResult:
        snap = self._safe_snapshot()
        deductions: list[dict[str, Any]] = []
        score = int(self.config.max_score)
        faults = list(snap.get("faults", []))
        warnings = list(snap.get("warnings", []))
        lifecycle = dict(snap.get("lifecycle", {}))
        safety = dict(snap.get("safety_supervisor", {}))
        stage2 = dict(snap.get("stage2_wiring", {}))
        integration = dict(snap.get("integration_manager", {}))
        # Global faults/warnings
        if faults:
            self._deduct(deductions, min(40, 10 * len(faults)), "runtime_faults_present", faults=faults)
        if warnings:
            self._deduct(deductions, min(20, 3 * len(warnings)), "runtime_warnings_present", warnings=warnings)
        # Lifecycle
        lifecycle_state = str(lifecycle.get("lifecycle_state", "UNKNOWN"))
        if lifecycle_state == "FAULTED":
            self._deduct(deductions, 25, "lifecycle_faulted")
        elif lifecycle_state == "SHUTDOWN":
            self._deduct(deductions, 50, "lifecycle_shutdown")
        elif lifecycle_state == "RECOVERING":
            self._deduct(deductions, 12, "lifecycle_recovering")
        elif lifecycle_state == "BOOTING":
            self._deduct(deductions, 8, "lifecycle_booting")
        elif lifecycle_state == "UNKNOWN":
            self._deduct(deductions, 10, "lifecycle_unknown")
        # Safety
        safety_level = str(safety.get("level", "UNKNOWN"))
        if safety_level == "WARNING":
            self._deduct(deductions, 8, "safety_warning")
        elif safety_level == "FAULT":
            self._deduct(deductions, 25, "safety_fault")
        elif safety_level == "CRITICAL":
            self._deduct(deductions, 40, "safety_critical")
        elif safety_level == "SHUTDOWN":
            self._deduct(deductions, 55, "safety_shutdown")
        elif safety_level == "UNKNOWN":
            self._deduct(deductions, 10, "safety_unknown")
        # Stage-2 readiness
        if stage2:
            if not bool(stage2.get("telemetry_manager_ready", False)):
                self._deduct(deductions, 6, "stage2_telemetry_not_ready")
            if not bool(stage2.get("local_command_executor_ready", False)):
                self._deduct(deductions, 6, "stage2_local_executor_not_ready")
            if not bool(stage2.get("watchdog_supervisor_ready", False)):
                self._deduct(deductions, 8, "stage2_watchdog_not_ready")
            if not bool(stage2.get("safe_shutdown_manager_ready", False)):
                self._deduct(deductions, 8, "stage2_shutdown_manager_not_ready")
        else:
            self._deduct(deductions, 15, "stage2_missing")
        # Integration manager health
        if integration:
            if not bool(integration.get("mapper_bound", False)):
                self._deduct(deductions, 5, "integration_mapper_not_bound")
            if not bool(integration.get("bridge_ready", False)):
                self._deduct(deductions, 5, "integration_bridge_not_ready")
        else:
            self._deduct(deductions, 10, "integration_manager_missing")
        # Snapshot overall status
        if not bool(snap.get("overall_ok", False)):
            self._deduct(deductions, 10, "snapshot_overall_not_ok", summary=snap.get("overall_summary", ""))
        total_deduction = sum(item["points"] for item in deductions)
        score = max(0, score - total_deduction)
        grade = self._grade(score)
        overall_ok = score >= 75 and not faults and lifecycle_state not in ("FAULTED", "SHUTDOWN")
        summary = (
            f"score={score}/{self.config.max_score} | "
            f"grade={grade} | "
            f"faults={len(faults)} | "
            f"warnings={len(warnings)} | "
            f"lifecycle={lifecycle_state} | "
            f"safety={safety_level}"
        )
        result = HealthScoreResult(
            ts=time.time(),
            score=score,
            grade=grade,
            overall_ok=overall_ok,
            deductions=deductions,
            summary=summary,
        )
        self._last_result = result
        self._emit_status(
            "health_scorer/computed",
            score=score,
            grade=grade,
            overall_ok=overall_ok,
            deduction_count=len(deductions),
        )
        return result
    # --------------------------------------------------------
    # EXPORT
    # --------------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        if self._last_result is None:
            result = self.compute()
        else:
            result = self._last_result
        return {
            "ts": result.ts,
            "score": result.score,
            "grade": result.grade,
            "overall_ok": result.overall_ok,
            "deductions": list(result.deductions),
            "summary": result.summary,
            "last_error": self._last_error,
        }


# ============================================================
# MODULE-R052
# ============================================================

# runtime/remotepi_field_debug_recorder.py
"""
MODULE-R052
RemotePi Field Debug Recorder
-----------------------------

Purpose:
    Record field-debug history for RemotePi runtime.

Responsibilities:
    - Record runtime events with timestamps
    - Record periodic runtime snapshots
    - Mark fault points in the timeline
    - Export debug history in machine/human friendly formats
    - Help answer what happened before the fault?"
Design goals:
    - Lightweight ring-buffer style storage
    - Safe fallback behavior
    - Useful in field diagnostics
"""


import json
import time
from collections import deque
from dataclasses import dataclass
from typing import Any, Callable, Optional


# ============================================================
# DATA MODELS
# ============================================================

@dataclass(frozen=True)
class FieldDebugRecorderConfig:
    max_event_records: int = 500
    max_snapshot_records: int = 200
    emit_status_logs: bool = True
    json_indent: int = 2


# ============================================================
# MAIN CLASS
# ============================================================

class RemotePiFieldDebugRecorder:
    def __init__(
        self,
        *,
        snapshot_bus=None,
        status_sink: Optional[Callable[[str, dict], None]] = None,
        config: Optional[FieldDebugRecorderConfig] = None,
    ):
        self.snapshot_bus = snapshot_bus
        self.status_sink = status_sink
        self.config = config or FieldDebugRecorderConfig()

        self._event_records = deque(maxlen=self.config.max_event_records)
        self._snapshot_records = deque(maxlen=self.config.max_snapshot_records)
        self._fault_markers = deque(maxlen=100)

        self._last_error: Optional[str] = None
        self._last_record_ts: float = 0.0

    # --------------------------------------------------------
    # INTERNAL
    # --------------------------------------------------------

    def _emit_status(self, topic: str, **payload) -> None:
        if not self.config.emit_status_logs:
            return
        if self.status_sink is not None:
            self.status_sink(topic, {
                "ts": time.time(),
                **payload,
            })
    def _safe_snapshot(self) -> dict[str, Any]:
        if self.snapshot_bus is None or not hasattr(self.snapshot_bus, "build_service_snapshot"):
            return {
                "created_ts": time.time(),
                "overall_ok": False,
                "overall_summary": "snapshot_bus unavailable",
                "warnings": [],
                "faults": ["SNAPSHOT_BUS_UNAVAILABLE"],
            }
        try:
            return dict(self.snapshot_bus.build_service_snapshot())
        except Exception as exc:
            self._last_error = str(exc)
            self._emit_status("field_debug_recorder/snapshot_error", error=str(exc))
            return {
                "created_ts": time.time(),
                "overall_ok": False,
                "overall_summary": f"snapshot error: {exc}",
                "warnings": [],
                "faults": [str(exc)],
            }
    # --------------------------------------------------------
    # RECORDERS
    # --------------------------------------------------------
    def record_event(self, event_type: str, payload: Optional[dict] = None) -> None:
        payload = payload or {}
        rec = {
            "ts": time.time(),
            "type": str(event_type),
            "payload": dict(payload),
        }
        self._event_records.append(rec)
        self._last_record_ts = rec["ts"]
        self._emit_status(
            "field_debug_recorder/event_recorded",
            event_type=event_type,
            event_count=len(self._event_records),
        )
    def record_snapshot(self, label: str = "periodic") -> None:
        snap = self._safe_snapshot()
        rec = {
            "ts": time.time(),
            "label": str(label),
            "snapshot": snap,
        }
        self._snapshot_records.append(rec)
        self._last_record_ts = rec["ts"]
        self._emit_status(
            "field_debug_recorder/snapshot_recorded",
            label=label,
            snapshot_count=len(self._snapshot_records),
        )
    def mark_fault(self, fault_name: str, summary: str = "") -> None:
        marker = {
            "ts": time.time(),
            "fault_name": str(fault_name),
            "summary": str(summary),
            "event_index": len(self._event_records),
            "snapshot_index": len(self._snapshot_records),
        }
        self._fault_markers.append(marker)
        self._last_record_ts = marker["ts"]
        # fault anında otomatik snapshot
        self.record_snapshot(label=f"fault:{fault_name}")
        self._emit_status(
            "field_debug_recorder/fault_marked",
            fault_name=fault_name,
            fault_marker_count=len(self._fault_markers),
        )
    # --------------------------------------------------------
    # READERS
    # --------------------------------------------------------
    def get_recent_events(self, limit: int = 20) -> list[dict[str, Any]]:
        limit = max(1, int(limit))
        return list(self._event_records)[-limit:]
    def get_recent_snapshots(self, limit: int = 10) -> list[dict[str, Any]]:
        limit = max(1, int(limit))
        return list(self._snapshot_records)[-limit:]
    def get_fault_markers(self, limit: int = 20) -> list[dict[str, Any]]:
        limit = max(1, int(limit))
        return list(self._fault_markers)[-limit:]
    # --------------------------------------------------------
    # EXPORT
    # --------------------------------------------------------
    def build_debug_bundle(self) -> dict[str, Any]:
        return {
            "created_ts": time.time(),
            "event_count": len(self._event_records),
            "snapshot_count": len(self._snapshot_records),
            "fault_marker_count": len(self._fault_markers),
            "recent_events": self.get_recent_events(50),
            "recent_snapshots": self.get_recent_snapshots(20),
            "fault_markers": self.get_fault_markers(20),
            "last_error": self._last_error,
        }
    def export_json(self) -> str:
        bundle = self.build_debug_bundle()
        return json.dumps(bundle, ensure_ascii=False, indent=self.config.json_indent)
    def export_text_summary(self) -> str:
        lines = [
            "REMOTEPI FIELD DEBUG RECORDER",
            f"created_ts: {time.time()}",
            f"event_count: {len(self._event_records)}",
            f"snapshot_count: {len(self._snapshot_records)}",
            f"fault_marker_count: {len(self._fault_markers)}",
        ]
        if self._fault_markers:
            lines.append("fault_markers:")
            for marker in list(self._fault_markers)[-10:]:
                lines.append(
                    f"  - ts={marker['ts']} | "
                    f"fault={marker['fault_name']} | "
                    f"summary={marker['summary']}"
                )
        if self._event_records:
            lines.append("recent_events:")
            for rec in list(self._event_records)[-10:]:
                lines.append(
                    f"  - ts={rec['ts']} | type={rec['type']} | payload={rec['payload']}"
                )
        if self._snapshot_records:
            lines.append("recent_snapshots:")
            for rec in list(self._snapshot_records)[-5:]:
                snap = rec["snapshot"]
                lines.append(
                    f"  - ts={rec['ts']} | label={rec['label']} | "
                    f"overall_ok={snap.get('overall_ok', False)} | "
                    f"summary={snap.get('overall_summary', '')}"
                )
        return "\n".join(lines)
    # --------------------------------------------------------
    # CLEAR
    # --------------------------------------------------------
    def clear(self) -> None:
        self._event_records.clear()
        self._snapshot_records.clear()
        self._fault_markers.clear()
        self._emit_status(
            "field_debug_recorder/cleared",
            event_count=0,
            snapshot_count=0,
            fault_marker_count=0,
        )
    # --------------------------------------------------------
    # SNAPSHOT
    # --------------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return {
            "event_count": len(self._event_records),
            "snapshot_count": len(self._snapshot_records),
            "fault_marker_count": len(self._fault_markers),
            "last_record_ts": self._last_record_ts,
            "last_error": self._last_error,
            "config": {
                "max_event_records": self.config.max_event_records,
                "max_snapshot_records": self.config.max_snapshot_records,
            },
        }


# ============================================================
# MODULE-R053
# ============================================================

# runtime/remotepi_ads1115_native_adapter.py
"""
MODULE-R053
RemotePi ADS1115 Native Adapter
-------------------------------

Purpose:
    Native dual-ADS1115 reader for RemotePi runtime.

Responsibilities:
    - Open one or two ADS1115 devices
    - Read raw channel voltages
    - Expose named logical channels
    - Support joystick, battery and temperature analog inputs
    - Provide basic adapter health and diagnostics

Design goals:
    - Safe fallback behavior
    - Deterministic logical channel naming
    - Compatible with runtime hardware bridge / stage2 ADC readers
"""
import time
from dataclasses import dataclass, field
from typing import Callable, Optional
# ============================================================
# OPTIONAL IMPORTS
# ============================================================
try:
    import board
    import busio
    import adafruit_ads1x15.ads1115 as ADS
    from adafruit_ads1x15.analog_in import AnalogIn
except Exception:
    board = None
    busio = None
    ADS = None
    AnalogIn = None
# ============================================================
# CONFIG / MODELS
# ============================================================
@dataclass
class ADS1115DeviceConfig:
    name: str
    i2c_address: int
@dataclass
class LogicalChannelConfig:
    logical_name: str
    device_name: str
    pin_name: str
    scale: float = 1.0
    offset: float = 0.0
    clamp_min: Optional[float] = None
    clamp_max: Optional[float] = None
@dataclass
class ADS1115NativeAdapterConfig:
    gain: int = 1
    data_rate: int = 128
    emit_status_logs: bool = True
@dataclass
class ADSAdapterSnapshot:
    ts: float
    adapter_ready: bool
    i2c_ready: bool
    device_status: dict
    logical_channels: dict
    last_error: Optional[str]
    summary: str
# ============================================================
# MAIN CLASS
# ============================================================
class RemotePiADS1115NativeAdapter:
    DEFAULT_DEVICES = (
        ADS1115DeviceConfig(name="ADC1", i2c_address=0x48),
        ADS1115DeviceConfig(name="ADC2", i2c_address=0x49),
    )
    DEFAULT_LOGICAL_CHANNELS = (
        LogicalChannelConfig("LEFT_JOYSTICK_X", "ADC1", "P0", scale=1.0),
        LogicalChannelConfig("LEFT_JOYSTICK_Y", "ADC1", "P1", scale=1.0),
        LogicalChannelConfig("RIGHT_JOYSTICK_X", "ADC1", "P2", scale=1.0),
        LogicalChannelConfig("RIGHT_JOYSTICK_Y", "ADC1", "P3", scale=1.0),
        LogicalChannelConfig("BATTERY_VOLTAGE_SENSE", "ADC2", "P0", scale=11.0),
        LogicalChannelConfig("LM35_TEMP", "ADC2", "P1", scale=100.0),
        LogicalChannelConfig("NTC_BATTERY_TEMP", "ADC2", "P2", scale=100.0),
        LogicalChannelConfig("SPARE_ANALOG", "ADC2", "P3", scale=1.0),
    )
    def __init__(
        self,
        *,
        devices: Optional[tuple[ADS1115DeviceConfig, ...]] = None,
        logical_channels: Optional[tuple[LogicalChannelConfig, ...]] = None,
        status_sink: Optional[Callable[[str, dict], None]] = None,
        config: Optional[ADS1115NativeAdapterConfig] = None,
    ):
        self.devices_cfg = devices or self.DEFAULT_DEVICES
        self.logical_channels_cfg = logical_channels or self.DEFAULT_LOGICAL_CHANNELS
        self.status_sink = status_sink
        self.config = config or ADS1115NativeAdapterConfig()
        self._i2c = None
        self._ads_devices = {}
        self._channel_objects = {}
        self._last_error: Optional[str] = None
        self._adapter_ready = False
        self._i2c_ready = False
        self._build()
    # --------------------------------------------------------
    # INTERNAL
    # --------------------------------------------------------
    def _emit_status(self, topic: str, **payload) -> None:
        if not self.config.emit_status_logs:
            return
        if self.status_sink is not None:
            self.status_sink(topic, {
                "ts": time.time(),
                **payload,
            })
    def _pin_constant(self, pin_name: str):
        if ADS is None:
            raise RuntimeError("ADS library unavailable")
        pin_name = str(pin_name).upper()
        mapping = {
            "P0": ADS.P0,
            "P1": ADS.P1,
            "P2": ADS.P2,
            "P3": ADS.P3,
        }
        if pin_name not in mapping:
            raise ValueError(f"unsupported ADS pin: {pin_name}")
        return mapping[pin_name]
    def _build(self) -> None:
        if board is None or busio is None or ADS is None or AnalogIn is None:
            self._last_error = "ADS1115 dependencies unavailable"
            self._adapter_ready = False
            self._i2c_ready = False
            self._emit_status("ads1115_native/init_unavailable", error=self._last_error)
            return
        try:
            self._i2c = busio.I2C(board.SCL, board.SDA)
            self._i2c_ready = True
        except Exception as exc:
            self._last_error = str(exc)
            self._adapter_ready = False
            self._i2c_ready = False
            self._emit_status("ads1115_native/i2c_error", error=str(exc))
            return
        # Build ADS devices
        all_ok = True
        for dev in self.devices_cfg:
            try:
                ads = ADS.ADS1115(self._i2c, address=dev.i2c_address)
                ads.gain = self.config.gain
                ads.data_rate = self.config.data_rate
                self._ads_devices[dev.name] = ads
            except Exception as exc:
                all_ok = False
                self._last_error = str(exc)
                self._emit_status(
                    "ads1115_native/device_error",
                    device_name=dev.name,
                    address=hex(dev.i2c_address),
                    error=str(exc),
                )
        # Build logical channels
        for ch_cfg in self.logical_channels_cfg:
            ads = self._ads_devices.get(ch_cfg.device_name)
            if ads is None:
                continue
            try:
                chan = AnalogIn(ads, self._pin_constant(ch_cfg.pin_name))
                self._channel_objects[ch_cfg.logical_name] = (chan, ch_cfg)
            except Exception as exc:
                all_ok = False
                self._last_error = str(exc)
                self._emit_status(
                    "ads1115_native/channel_error",
                    logical_name=ch_cfg.logical_name,
                    device_name=ch_cfg.device_name,
                    pin_name=ch_cfg.pin_name,
                    error=str(exc),
                )
        self._adapter_ready = all_ok and bool(self._channel_objects)
        self._emit_status(
            "ads1115_native/build_complete",
            adapter_ready=self._adapter_ready,
            device_count=len(self._ads_devices),
            logical_channel_count=len(self._channel_objects),
        )
    def _apply_channel_scaling(self, voltage: float, cfg: LogicalChannelConfig) -> float:
        value = (float(voltage) * float(cfg.scale)) + float(cfg.offset)
        if cfg.clamp_min is not None:
            value = max(float(cfg.clamp_min), value)
        if cfg.clamp_max is not None:
            value = min(float(cfg.clamp_max), value)
        return value
    # --------------------------------------------------------
    # PUBLIC READ API
    # --------------------------------------------------------
    def is_ready(self) -> bool:
        return bool(self._adapter_ready)
    def has_device(self, device_name: str) -> bool:
        return str(device_name) in self._ads_devices
    def has_channel(self, logical_name: str) -> bool:
        return str(logical_name) in self._channel_objects
    def read_voltage(self, logical_name: str) -> float:
        logical_name = str(logical_name)
        if logical_name not in self._channel_objects:
            raise KeyError(f"unknown logical ADS channel: {logical_name}")
        chan, _cfg = self._channel_objects[logical_name]
        return float(chan.voltage)
    def read(self, logical_name: str) -> float:
        logical_name = str(logical_name)
        if logical_name not in self._channel_objects:
            raise KeyError(f"unknown logical ADS channel: {logical_name}")
        chan, cfg = self._channel_objects[logical_name]
        voltage = float(chan.voltage)
        return self._apply_channel_scaling(voltage, cfg)
    def try_read(self, logical_name: str, default: float = 0.0) -> float:
        try:
            return float(self.read(logical_name))
        except Exception as exc:
            self._last_error = str(exc)
            self._emit_status(
                "ads1115_native/read_error",
                logical_name=logical_name,
                error=str(exc),
            )
            return float(default)
    # --------------------------------------------------------
    # BULK READS
    # --------------------------------------------------------
    def read_all(self) -> dict[str, float]:
        result = {}
        for logical_name in self._channel_objects.keys():
            result[logical_name] = self.try_read(logical_name, default=0.0)
        return result
    def read_all_voltages(self) -> dict[str, float]:
        result = {}
        for logical_name in self._channel_objects.keys():
            try:
                result[logical_name] = self.read_voltage(logical_name)
            except Exception:
                result[logical_name] = 0.0
        return result
    # --------------------------------------------------------
    # HEALTH / DIAGNOSTICS
    # --------------------------------------------------------
    def build_device_status(self) -> dict:
        status = {}
        for dev in self.devices_cfg:
            status[dev.name] = {
                "address": hex(dev.i2c_address),
                "ready": dev.name in self._ads_devices,
            }
        return status
    def build_logical_channel_status(self) -> dict:
        data = {}
        for ch_cfg in self.logical_channels_cfg:
            data[ch_cfg.logical_name] = {
                "device_name": ch_cfg.device_name,
                "pin_name": ch_cfg.pin_name,
                "available": ch_cfg.logical_name in self._channel_objects,
                "scale": ch_cfg.scale,
                "offset": ch_cfg.offset,
            }
        return data
    def snapshot(self) -> ADSAdapterSnapshot:
        return ADSAdapterSnapshot(
            ts=time.time(),
            adapter_ready=self._adapter_ready,
            i2c_ready=self._i2c_ready,
            device_status=self.build_device_status(),
            logical_channels=self.build_logical_channel_status(),
            last_error=self._last_error,
            summary=(
                f"adapter_ready={self._adapter_ready} | "
                f"i2c_ready={self._i2c_ready} | "
                f"devices={len(self._ads_devices)} | "
                f"channels={len(self._channel_objects)}"
            ),
        )
    def to_dict(self) -> dict:
        snap = self.snapshot()
        return {
            "ts": snap.ts,
            "adapter_ready": snap.adapter_ready,
            "i2c_ready": snap.i2c_ready,
            "device_status": snap.device_status,
            "logical_channels": snap.logical_channels,
            "last_error": snap.last_error,
            "summary": snap.summary,
        }


# ============================================================
# MODULE-R054
# ============================================================

# runtime/remotepi_pca9685_native_adapter.py
"""
MODULE-R054
RemotePi PCA9685 Native Adapter
-------------------------------

Purpose:
    Native PCA9685 PWM/servo driver adapter for RemotePi runtime.

Responsibilities:
    - Open and control PCA9685
    - Drive servo channels with angle-based API
    - Drive raw PWM channels
    - Provide safe all-off shutdown behavior
    - Expose adapter diagnostics

Design goals:
    - Safe fallback behavior
    - Deterministic channel control
    - Compatible with runtime hardware bridge / actuator layers
"""
import time
from dataclasses import dataclass
from typing import Callable, Optional
# ============================================================
# OPTIONAL IMPORTS
# ============================================================
try:
    import board
    import busio
    from adafruit_pca9685 import PCA9685
except Exception:
    board = None
    busio = None
    PCA9685 = None
# ============================================================
# CONFIG / MODELS
# ============================================================
@dataclass
class PCA9685ChannelConfig:
    logical_name: str
    channel_index: int
    mode: str = "pwm"          # "pwm" | "servo"
    min_us: int = 500
    max_us: int = 2500
    angle_min: float = -90.0
    angle_max: float = 90.0
@dataclass
class PCA9685NativeAdapterConfig:
    i2c_address: int = 0x40
    frequency_hz: int = 50
    emit_status_logs: bool = True
@dataclass
class PCA9685AdapterSnapshot:
    ts: float
    adapter_ready: bool
    i2c_ready: bool
    channel_status: dict
    last_error: Optional[str]
    summary: str
# ============================================================
# MAIN CLASS
# ============================================================
class RemotePiPCA9685NativeAdapter:
    DEFAULT_CHANNELS = (
        PCA9685ChannelConfig(
            logical_name="WHEEL_SERVO",
            channel_index=0,
            mode="servo",
            min_us=500,
            max_us=2500,
            angle_min=-90.0,
            angle_max=90.0,
        ),
        PCA9685ChannelConfig(
            logical_name="AUX_PWM_1",
            channel_index=1,
            mode="pwm",
        ),
        PCA9685ChannelConfig(
            logical_name="AUX_PWM_2",
            channel_index=2,
            mode="pwm",
        ),
        PCA9685ChannelConfig(
            logical_name="AUX_PWM_3",
            channel_index=3,
            mode="pwm",
        ),
    )
    def __init__(
        self,
        *,
        channels: Optional[tuple[PCA9685ChannelConfig, ...]] = None,
        status_sink: Optional[Callable[[str, dict], None]] = None,
        config: Optional[PCA9685NativeAdapterConfig] = None,
    ):
        self.channels_cfg = channels or self.DEFAULT_CHANNELS
        self.status_sink = status_sink
        self.config = config or PCA9685NativeAdapterConfig()
        self._i2c = None
        self._pca = None
        self._adapter_ready = False
        self._i2c_ready = False
        self._last_error: Optional[str] = None
        self._channel_cfg_map = {
            cfg.logical_name: cfg for cfg in self.channels_cfg
        }
        self._last_channel_values: dict[str, dict] = {}
        self._build()
    # --------------------------------------------------------
    # INTERNAL
    # --------------------------------------------------------
    def _emit_status(self, topic: str, **payload) -> None:
        if not self.config.emit_status_logs:
            return
        if self.status_sink is not None:
            self.status_sink(topic, {
                "ts": time.time(),
                **payload,
            })
    def _build(self) -> None:
        if board is None or busio is None or PCA9685 is None:
            self._last_error = "PCA9685 dependencies unavailable"
            self._adapter_ready = False
            self._i2c_ready = False
            self._emit_status("pca9685_native/init_unavailable", error=self._last_error)
            return
        try:
            self._i2c = busio.I2C(board.SCL, board.SDA)
            self._i2c_ready = True
        except Exception as exc:
            self._last_error = str(exc)
            self._adapter_ready = False
            self._i2c_ready = False
            self._emit_status("pca9685_native/i2c_error", error=str(exc))
            return
        try:
            self._pca = PCA9685(self._i2c, address=self.config.i2c_address)
            self._pca.frequency = int(self.config.frequency_hz)
            self._adapter_ready = True
            self._emit_status(
                "pca9685_native/build_complete",
                adapter_ready=True,
                address=hex(self.config.i2c_address),
                frequency_hz=self.config.frequency_hz,
                channel_count=len(self.channels_cfg),
            )
        except Exception as exc:
            self._last_error = str(exc)
            self._adapter_ready = False
            self._emit_status("pca9685_native/build_error", error=str(exc))
    def _require_ready(self) -> None:
        if not self._adapter_ready or self._pca is None:
            raise RuntimeError("PCA9685 adapter not ready")
    def _clamp(self, value: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, float(value)))
    def _servo_angle_to_pulse_us(self, angle: float, cfg: PCA9685ChannelConfig) -> int:
        angle = self._clamp(angle, cfg.angle_min, cfg.angle_max)
        span_angle = float(cfg.angle_max - cfg.angle_min)
        if span_angle <= 0:
            raise ValueError("invalid servo angle span")
        ratio = (angle - cfg.angle_min) / span_angle
        pulse = int(cfg.min_us + ratio * (cfg.max_us - cfg.min_us))
        return pulse
    def _pulse_us_to_duty_cycle(self, pulse_us: int) -> int:
        """
        Convert microsecond pulse width to 16-bit duty cycle for current PWM frequency.
        """
        period_us = 1_000_000.0 / float(self.config.frequency_hz)
        duty_ratio = float(pulse_us) / period_us
        duty = int(self._clamp(duty_ratio * 65535.0, 0.0, 65535.0))
        return duty
    def _set_channel_duty(self, channel_index: int, duty_cycle: int) -> None:
        self._require_ready()
        duty_cycle = int(self._clamp(duty_cycle, 0, 65535))
        self._pca.channels[channel_index].duty_cycle = duty_cycle
    # --------------------------------------------------------
    # PUBLIC API
    # --------------------------------------------------------
    def is_ready(self) -> bool:
        return bool(self._adapter_ready)
    def has_channel(self, logical_name: str) -> bool:
        return str(logical_name) in self._channel_cfg_map
    def set_pwm_duty(self, logical_name: str, duty_cycle: int) -> None:
        logical_name = str(logical_name)
        if logical_name not in self._channel_cfg_map:
            raise KeyError(f"unknown PCA9685 logical channel: {logical_name}")
        cfg = self._channel_cfg_map[logical_name]
        self._set_channel_duty(cfg.channel_index, duty_cycle)
        self._last_channel_values[logical_name] = {
            "mode": "pwm",
            "duty_cycle": int(duty_cycle),
        }
        self._emit_status(
            "pca9685_native/set_pwm_duty",
            logical_name=logical_name,
            channel_index=cfg.channel_index,
            duty_cycle=int(duty_cycle),
        )
    def set_pwm_ratio(self, logical_name: str, ratio_0_1: float) -> None:
        ratio = self._clamp(ratio_0_1, 0.0, 1.0)
        duty = int(ratio * 65535.0)
        self.set_pwm_duty(logical_name, duty)
    def set_servo_angle(self, logical_name: str, angle_deg: float) -> None:
        logical_name = str(logical_name)
        if logical_name not in self._channel_cfg_map:
            raise KeyError(f"unknown PCA9685 logical channel: {logical_name}")
        cfg = self._channel_cfg_map[logical_name]
        if cfg.mode != "servo":
            raise ValueError(f"channel {logical_name} is not configured as servo")
        pulse_us = self._servo_angle_to_pulse_us(float(angle_deg), cfg)
        duty = self._pulse_us_to_duty_cycle(pulse_us)
        self._set_channel_duty(cfg.channel_index, duty)
        self._last_channel_values[logical_name] = {
            "mode": "servo",
            "angle_deg": float(angle_deg),
            "pulse_us": int(pulse_us),
            "duty_cycle": int(duty),
        }
        self._emit_status(
            "pca9685_native/set_servo_angle",
            logical_name=logical_name,
            channel_index=cfg.channel_index,
            angle_deg=float(angle_deg),
            pulse_us=int(pulse_us),
            duty_cycle=int(duty),
        )
    def set_servo_normalized(self, logical_name: str, normalized: float) -> None:
        """
        normalized in [-1.0, +1.0]
        """
        logical_name = str(logical_name)
        if logical_name not in self._channel_cfg_map:
            raise KeyError(f"unknown PCA9685 logical channel: {logical_name}")
        cfg = self._channel_cfg_map[logical_name]
        normalized = self._clamp(normalized, -1.0, 1.0)
        center = (cfg.angle_min + cfg.angle_max) / 2.0
        half_span = (cfg.angle_max - cfg.angle_min) / 2.0
        angle = center + normalized * half_span
        self.set_servo_angle(logical_name, angle)
    def disable_channel(self, logical_name: str) -> None:
        logical_name = str(logical_name)
        if logical_name not in self._channel_cfg_map:
            raise KeyError(f"unknown PCA9685 logical channel: {logical_name}")
        cfg = self._channel_cfg_map[logical_name]
        self._set_channel_duty(cfg.channel_index, 0)
        self._last_channel_values[logical_name] = {
            "mode": cfg.mode,
            "disabled": True,
            "duty_cycle": 0,
        }
        self._emit_status(
            "pca9685_native/disable_channel",
            logical_name=logical_name,
            channel_index=cfg.channel_index,
        )
    def all_off(self) -> None:
        self._require_ready()
        for cfg in self.channels_cfg:
            try:
                self._set_channel_duty(cfg.channel_index, 0)
                self._last_channel_values[cfg.logical_name] = {
                    "mode": cfg.mode,
                    "disabled": True,
                    "duty_cycle": 0,
                }
            except Exception as exc:
                self._last_error = str(exc)
                self._emit_status(
                    "pca9685_native/all_off_error",
                    logical_name=cfg.logical_name,
                    channel_index=cfg.channel_index,
                    error=str(exc),
                )
        self._emit_status("pca9685_native/all_off")
    # --------------------------------------------------------
    # DIAGNOSTICS
    # --------------------------------------------------------
    def build_channel_status(self) -> dict:
        status = {}
        for cfg in self.channels_cfg:
            status[cfg.logical_name] = {
                "channel_index": cfg.channel_index,
                "mode": cfg.mode,
                "configured": True,
                "last_value": self._last_channel_values.get(cfg.logical_name),
            }
        return status
    def snapshot(self) -> PCA9685AdapterSnapshot:
        return PCA9685AdapterSnapshot(
            ts=time.time(),
            adapter_ready=self._adapter_ready,
            i2c_ready=self._i2c_ready,
            channel_status=self.build_channel_status(),
            last_error=self._last_error,
            summary=(
                f"adapter_ready={self._adapter_ready} | "
                f"i2c_ready={self._i2c_ready} | "
                f"channels={len(self.channels_cfg)}"
            ),
        )
    def to_dict(self) -> dict:
        snap = self.snapshot()
        return {
            "ts": snap.ts,
            "adapter_ready": snap.adapter_ready,
            "i2c_ready": snap.i2c_ready,
            "channel_status": snap.channel_status,
            "last_error": snap.last_error,
            "summary": snap.summary,
            "config": {
                "i2c_address": hex(self.config.i2c_address),
                "frequency_hz": self.config.frequency_hz,
            },
        }


# ============================================================
# MODULE-R055
# ============================================================

# runtime/remotepi_gpio_signal_abstraction_layer.py
"""
MODULE-R055
RemotePi GPIO Signal Abstraction Layer
--------------------------------------

Purpose:
    Logical GPIO signal abstraction layer for RemotePi runtime.

Responsibilities:
    - Manage named GPIO output signals
    - Hide physical BCM pin numbers from upper runtime layers
    - Provide safe write/readback API
    - Support grouped all-off behavior
    - Expose diagnostics and signal state snapshot

Design goals:
    - Safe fallback if RPi.GPIO unavailable
    - Deterministic logical naming
    - Compatible with runtime hardware bridge / service tools
"""
import time
from dataclasses import dataclass
from typing import Callable, Optional
# ============================================================
# OPTIONAL GPIO IMPORT
# ============================================================
try:
    import RPi.GPIO as GPIO
except Exception:
    GPIO = None
# ============================================================
# CONFIG / MODELS
# ============================================================
@dataclass
class GPIOSignalConfig:
    logical_name: str
    bcm_pin: int
    active_high: bool = True
    default_on_start: bool = False
    category: str = "general"
@dataclass
class GPIOSignalLayerConfig:
    set_warnings: bool = False
    emit_status_logs: bool = True
@dataclass
class GPIOSignalLayerSnapshot:
    ts: float
    gpio_ready: bool
    signal_status: dict
    last_error: Optional[str]
    summary: str
# ============================================================
# MAIN CLASS
# ============================================================
class RemotePiGPIOSignalAbstractionLayer:
    DEFAULT_SIGNALS = (
        GPIOSignalConfig("REV_BUZZER", 20, active_high=True, default_on_start=False, category="buzzer"),
        GPIOSignalConfig("REV_LED", 26, active_high=True, default_on_start=False, category="light"),
        GPIOSignalConfig("ENGINE_BUZZER_ENABLE", 18, active_high=True, default_on_start=False, category="buzzer"),
        GPIOSignalConfig("SIGNAL_LEFT", 23, active_high=True, default_on_start=False, category="signal"),
        GPIOSignalConfig("SIGNAL_RIGHT", 24, active_high=True, default_on_start=False, category="signal"),
        GPIOSignalConfig("PARKING_LIGHT", 5, active_high=True, default_on_start=False, category="light"),
        GPIOSignalConfig("LOW_BEAM_LIGHT", 6, active_high=True, default_on_start=False, category="light"),
        GPIOSignalConfig("HIGH_BEAM_LIGHT", 13, active_high=True, default_on_start=False, category="light"),
        GPIOSignalConfig("RIG_FLOOR_LIGHT", 19, active_high=True, default_on_start=False, category="light"),
        GPIOSignalConfig("ROTATION_LIGHT", 21, active_high=True, default_on_start=False, category="light"),
        GPIOSignalConfig("REMOTE_FAN_CTRL", 17, active_high=True, default_on_start=False, category="fan"),
    )
    def __init__(
        self,
        *,
        signals: Optional[tuple[GPIOSignalConfig, ...]] = None,
        status_sink: Optional[Callable[[str, dict], None]] = None,
        config: Optional[GPIOSignalLayerConfig] = None,
    ):
        self.signals_cfg = signals or self.DEFAULT_SIGNALS
        self.status_sink = status_sink
        self.config = config or GPIOSignalLayerConfig()
        self._gpio_ready = False
        self._last_error: Optional[str] = None
        self._signal_cfg_map = {cfg.logical_name: cfg for cfg in self.signals_cfg}
        self._signal_state_cache = {cfg.logical_name: bool(cfg.default_on_start) for cfg in self.signals_cfg}
        self._build()
    # --------------------------------------------------------
    # INTERNAL
    # --------------------------------------------------------
    def _emit_status(self, topic: str, **payload) -> None:
        if not self.config.emit_status_logs:
            return
        if self.status_sink is not None:
            self.status_sink(topic, {
                "ts": time.time(),
                **payload,
            })
    def _build(self) -> None:
        if GPIO is None:
            self._last_error = "RPi.GPIO unavailable"
            self._gpio_ready = False
            self._emit_status("gpio_sal/init_unavailable", error=self._last_error)
            return
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(bool(self.config.set_warnings))
            for cfg in self.signals_cfg:
                GPIO.setup(cfg.bcm_pin, GPIO.OUT)
                raw_value = GPIO.HIGH if self._signal_state_cache[cfg.logical_name] == cfg.active_high else GPIO.LOW
                GPIO.output(cfg.bcm_pin, raw_value)
            self._gpio_ready = True
            self._emit_status(
                "gpio_sal/build_complete",
                gpio_ready=True,
                signal_count=len(self.signals_cfg),
            )
        except Exception as exc:
            self._last_error = str(exc)
            self._gpio_ready = False
            self._emit_status("gpio_sal/build_error", error=str(exc))
    def _require_known_signal(self, logical_name: str) -> GPIOSignalConfig:
        logical_name = str(logical_name)
        if logical_name not in self._signal_cfg_map:
            raise KeyError(f"unknown logical GPIO signal: {logical_name}")
        return self._signal_cfg_map[logical_name]
    def _logical_to_raw(self, logical_state: bool, cfg: GPIOSignalConfig):
        if GPIO is None:
            return None
        is_physically_on = bool(logical_state) == bool(cfg.active_high)
        return GPIO.HIGH if is_physically_on else GPIO.LOW
    # --------------------------------------------------------
    # PUBLIC API
    # --------------------------------------------------------
    def is_ready(self) -> bool:
        return bool(self._gpio_ready)
    def has_signal(self, logical_name: str) -> bool:
        return str(logical_name) in self._signal_cfg_map
    def write(self, logical_name: str, state: bool) -> None:
        cfg = self._require_known_signal(logical_name)
        logical_name = cfg.logical_name
        state = bool(state)
        if self._gpio_ready and GPIO is not None:
            raw = self._logical_to_raw(state, cfg)
            GPIO.output(cfg.bcm_pin, raw)
        self._signal_state_cache[logical_name] = state
        self._emit_status(
            "gpio_sal/write",
            logical_name=logical_name,
            bcm_pin=cfg.bcm_pin,
            state=state,
            active_high=cfg.active_high,
        )
    def read_cached(self, logical_name: str) -> bool:
        cfg = self._require_known_signal(logical_name)
        return bool(self._signal_state_cache[cfg.logical_name])
    def toggle(self, logical_name: str) -> bool:
        cfg = self._require_known_signal(logical_name)
        new_state = not bool(self._signal_state_cache[cfg.logical_name])
        self.write(cfg.logical_name, new_state)
        return new_state
    def write_group(self, category: str, state: bool) -> None:
        category = str(category)
        for cfg in self.signals_cfg:
            if cfg.category == category:
                self.write(cfg.logical_name, state)
        self._emit_status(
            "gpio_sal/write_group",
            category=category,
            state=bool(state),
        )
    def all_off(self) -> None:
        for cfg in self.signals_cfg:
            self.write(cfg.logical_name, False)
        self._emit_status("gpio_sal/all_off")
    # --------------------------------------------------------
    # CONVENIENCE METHODS
    # --------------------------------------------------------
    def set_signal_lhr(self, enabled: bool) -> None:
        self.write("SIGNAL_LEFT", enabled)
        self.write("SIGNAL_RIGHT", enabled)
    def set_parking_light(self, enabled: bool) -> None:
        self.write("PARKING_LIGHT", enabled)
    def set_low_beam_light(self, enabled: bool) -> None:
        self.write("LOW_BEAM_LIGHT", enabled)
    def set_high_beam_light(self, enabled: bool) -> None:
        self.write("HIGH_BEAM_LIGHT", enabled)
    def set_rig_floor_light(self, enabled: bool) -> None:
        self.write("RIG_FLOOR_LIGHT", enabled)
    def set_rotation_light(self, enabled: bool) -> None:
        self.write("ROTATION_LIGHT", enabled)
    def set_remote_fan(self, enabled: bool) -> None:
        self.write("REMOTE_FAN_CTRL", enabled)
    def set_reverse_alarm(self, enabled: bool) -> None:
        self.write("REV_BUZZER", enabled)
        self.write("REV_LED", enabled)
    # --------------------------------------------------------
    # DIAGNOSTICS
    # --------------------------------------------------------
    def build_signal_status(self) -> dict:
        status = {}
        for cfg in self.signals_cfg:
            status[cfg.logical_name] = {
                "bcm_pin": cfg.bcm_pin,
                "active_high": cfg.active_high,
                "category": cfg.category,
                "state_cached": bool(self._signal_state_cache[cfg.logical_name]),
            }
        return status
    def snapshot(self) -> GPIOSignalLayerSnapshot:
        return GPIOSignalLayerSnapshot(
            ts=time.time(),
            gpio_ready=self._gpio_ready,
            signal_status=self.build_signal_status(),
            last_error=self._last_error,
            summary=(
                f"gpio_ready={self._gpio_ready} | "
                f"signals={len(self.signals_cfg)}"
            ),
        )
    def to_dict(self) -> dict:
        snap = self.snapshot()
        return {
            "ts": snap.ts,
            "gpio_ready": snap.gpio_ready,
            "signal_status": snap.signal_status,
            "last_error": snap.last_error,
            "summary": snap.summary,
        }


# ============================================================
# MODULE-R056
# ============================================================

# runtime/remotepi_dual_joystick_native_driver.py
"""
MODULE-R056
RemotePi Dual Joystick Native Driver
------------------------------------

Purpose:
    Native dual-joystick driver for RemotePi runtime.

Responsibilities:
    - Read two joystick analog sticks from ADS1115 logical channels
    - Read left/right joystick buttons from GPIO readers
    - Apply calibration, deadzone and normalization
    - Provide deterministic left/right X/Y state
    - Expose diagnostics/snapshot data for runtime and service tools

Design goals:
    - Safe fallback behavior
    - Stable normalized outputs in [-1.0, +1.0]
    - Compatible with safety supervisor / hardware runtime bridge
"""
import time
from dataclasses import dataclass
from typing import Callable, Optional
# ============================================================
# CONFIG / MODELS
# ============================================================
@dataclass
class JoystickAxisConfig:
    logical_name: str
    center_value: float = 0.0
    min_value: float = -1.0
    max_value: float = 1.0
    deadzone: float = 0.05
    invert: bool = False
@dataclass
class DualJoystickNativeDriverConfig:
    emit_status_logs: bool = True
    default_button_state: bool = False
    clamp_output: bool = True
@dataclass
class JoystickAxisSnapshot:
    raw_value: float
    centered_value: float
    normalized_value: float
@dataclass
class DualJoystickSnapshot:
    ts: float
    left_x: dict
    left_y: dict
    right_x: dict
    right_y: dict
    left_button_pressed: bool
    right_button_pressed: bool
    last_error: Optional[str]
    summary: str
# ============================================================
# MAIN CLASS
# ============================================================
class RemotePiDualJoystickNativeDriver:
    DEFAULT_AXIS_CONFIGS = {
        "LEFT_X": JoystickAxisConfig("LEFT_JOYSTICK_X"),
        "LEFT_Y": JoystickAxisConfig("LEFT_JOYSTICK_Y"),
        "RIGHT_X": JoystickAxisConfig("RIGHT_JOYSTICK_X"),
        "RIGHT_Y": JoystickAxisConfig("RIGHT_JOYSTICK_Y"),
    }
    def __init__(
        self,
        *,
        adc_adapter,
        left_button_reader: Optional[Callable[[], bool]] = None,
        right_button_reader: Optional[Callable[[], bool]] = None,
        axis_configs: Optional[dict[str, JoystickAxisConfig]] = None,
        status_sink: Optional[Callable[[str, dict], None]] = None,
        config: Optional[DualJoystickNativeDriverConfig] = None,
    ):
        self.adc_adapter = adc_adapter
        self.left_button_reader = left_button_reader
        self.right_button_reader = right_button_reader
        self.axis_configs = axis_configs or dict(self.DEFAULT_AXIS_CONFIGS)
        self.status_sink = status_sink
        self.config = config or DualJoystickNativeDriverConfig()
        self._last_error: Optional[str] = None
        self._last_axis_cache: dict[str, JoystickAxisSnapshot] = {}
    # --------------------------------------------------------
    # INTERNAL
    # --------------------------------------------------------
    def _emit_status(self, topic: str, **payload) -> None:
        if not self.config.emit_status_logs:
            return
        if self.status_sink is not None:
            self.status_sink(topic, {
                "ts": time.time(),
                **payload,
            })
    def _clamp(self, value: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, float(value)))
    def _read_raw_axis(self, axis_key: str) -> float:
        cfg = self.axis_configs[axis_key]
        try:
            if hasattr(self.adc_adapter, "try_read"):
                return float(self.adc_adapter.try_read(cfg.logical_name, default=cfg.center_value))
            if hasattr(self.adc_adapter, "read"):
                return float(self.adc_adapter.read(cfg.logical_name))
            raise RuntimeError("adc_adapter has no read/try_read")
        except Exception as exc:
            self._last_error = str(exc)
            self._emit_status(
                "dual_joystick/read_raw_axis_error",
                axis_key=axis_key,
                logical_name=cfg.logical_name,
                error=str(exc),
            )
            return float(cfg.center_value)
    def _normalize_axis(self, axis_key: str) -> JoystickAxisSnapshot:
        cfg = self.axis_configs[axis_key]
        raw = self._read_raw_axis(axis_key)
        centered = raw - float(cfg.center_value)
        pos_span = float(cfg.max_value - cfg.center_value)
        neg_span = float(cfg.center_value - cfg.min_value)
        if centered >= 0:
            denom = pos_span if pos_span > 0 else 1.0
            normalized = centered / denom
        else:
            denom = neg_span if neg_span > 0 else 1.0
            normalized = centered / denom
        if cfg.invert:
            normalized = -normalized
        if abs(normalized) < float(cfg.deadzone):
            normalized = 0.0
        if self.config.clamp_output:
            normalized = self._clamp(normalized, -1.0, 1.0)
        snap = JoystickAxisSnapshot(
            raw_value=float(raw),
            centered_value=float(centered),
            normalized_value=float(normalized),
        )
        self._last_axis_cache[axis_key] = snap
        return snap
    def _read_button(self, reader: Optional[Callable[[], bool]], side: str) -> bool:
        if reader is None:
            return bool(self.config.default_button_state)
        try:
            return bool(reader())
        except Exception as exc:
            self._last_error = str(exc)
            self._emit_status(
                "dual_joystick/button_read_error",
                side=side,
                error=str(exc),
            )
            return bool(self.config.default_button_state)
    # --------------------------------------------------------
    # CALIBRATION
    # --------------------------------------------------------
    def calibrate_center_from_current(self) -> None:
        for axis_key, cfg in self.axis_configs.items():
            current = self._read_raw_axis(axis_key)
            self.axis_configs[axis_key] = JoystickAxisConfig(
                logical_name=cfg.logical_name,
                center_value=float(current),
                min_value=cfg.min_value,
                max_value=cfg.max_value,
                deadzone=cfg.deadzone,
                invert=cfg.invert,
            )
        self._emit_status(
            "dual_joystick/center_calibrated",
            centers={k: v.center_value for k, v in self.axis_configs.items()},
        )
    def set_deadzone(self, axis_key: str, deadzone: float) -> None:
        if axis_key not in self.axis_configs:
            raise KeyError(f"unknown axis_key: {axis_key}")
        cfg = self.axis_configs[axis_key]
        self.axis_configs[axis_key] = JoystickAxisConfig(
            logical_name=cfg.logical_name,
            center_value=cfg.center_value,
            min_value=cfg.min_value,
            max_value=cfg.max_value,
            deadzone=float(deadzone),
            invert=cfg.invert,
        )
    # --------------------------------------------------------
    # PUBLIC READ API
    # --------------------------------------------------------
    def read_left_x(self) -> float:
        return self._normalize_axis("LEFT_X").normalized_value
    def read_left_y(self) -> float:
        return self._normalize_axis("LEFT_Y").normalized_value
    def read_right_x(self) -> float:
        return self._normalize_axis("RIGHT_X").normalized_value
    def read_right_y(self) -> float:
        return self._normalize_axis("RIGHT_Y").normalized_value
    def read_left_button(self) -> bool:
        return self._read_button(self.left_button_reader, "LEFT")
    def read_right_button(self) -> bool:
        return self._read_button(self.right_button_reader, "RIGHT")
    def read_left(self) -> dict:
        x = self._normalize_axis("LEFT_X")
        y = self._normalize_axis("LEFT_Y")
        return {
            "x": x.normalized_value,
            "y": y.normalized_value,
            "button_pressed": self.read_left_button(),
        }
    def read_right(self) -> dict:
        x = self._normalize_axis("RIGHT_X")
        y = self._normalize_axis("RIGHT_Y")
        return {
            "x": x.normalized_value,
            "y": y.normalized_value,
            "button_pressed": self.read_right_button(),
        }
    def read_all(self) -> dict:
        return {
            "left_x": self.read_left_x(),
            "left_y": self.read_left_y(),
            "right_x": self.read_right_x(),
            "right_y": self.read_right_y(),
            "left_button_pressed": self.read_left_button(),
            "right_button_pressed": self.read_right_button(),
        }
    # --------------------------------------------------------
    # DIAGNOSTICS
    # --------------------------------------------------------
    def _axis_snapshot_dict(self, axis_key: str) -> dict:
        snap = self._normalize_axis(axis_key)
        cfg = self.axis_configs[axis_key]
        return {
            "logical_name": cfg.logical_name,
            "raw_value": snap.raw_value,
            "centered_value": snap.centered_value,
            "normalized_value": snap.normalized_value,
            "center_value": cfg.center_value,
            "min_value": cfg.min_value,
            "max_value": cfg.max_value,
            "deadzone": cfg.deadzone,
            "invert": cfg.invert,
        }
    def snapshot(self) -> DualJoystickSnapshot:
        left_x = self._axis_snapshot_dict("LEFT_X")
        left_y = self._axis_snapshot_dict("LEFT_Y")
        right_x = self._axis_snapshot_dict("RIGHT_X")
        right_y = self._axis_snapshot_dict("RIGHT_Y")
        left_btn = self.read_left_button()
        right_btn = self.read_right_button()
        return DualJoystickSnapshot(
            ts=time.time(),
            left_x=left_x,
            left_y=left_y,
            right_x=right_x,
            right_y=right_y,
            left_button_pressed=left_btn,
            right_button_pressed=right_btn,
            last_error=self._last_error,
            summary=(
                f"L=({left_x['normalized_value']:.3f},{left_y['normalized_value']:.3f}) | "
                f"R=({right_x['normalized_value']:.3f},{right_y['normalized_value']:.3f}) | "
                f"LB={left_btn} | RB={right_btn}"
            ),
        )
    def to_dict(self) -> dict:
        snap = self.snapshot()
        return {
            "ts": snap.ts,
            "left_x": snap.left_x,
            "left_y": snap.left_y,
            "right_x": snap.right_x,
            "right_y": snap.right_y,
            "left_button_pressed": snap.left_button_pressed,
            "right_button_pressed": snap.right_button_pressed,
            "last_error": snap.last_error,
            "summary": snap.summary,
        }


# ============================================================
# MODULE-R057
# ============================================================

# runtime/remotepi_runtime_performance_governor.py
"""
MODULE-R057
RemotePi Runtime Performance Governor
-------------------------------------

Purpose:
    Runtime performance governor for RemotePi.

Responsibilities:
    - Manage recommended tick rates for runtime services
    - Adjust service cadence based on system health/load conditions
    - Reduce non-critical workload in degraded conditions
    - Provide deterministic performance profiles

Design goals:
    - Lightweight
    - Deterministic
    - Easy to integrate with supervisor/tick loops
"""
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional
# ============================================================
# ENUMS
# ============================================================
class PerformanceMode(str, Enum):
    NORMAL = "NORMAL"
    REDUCED = "REDUCED"
    CRITICAL = "CRITICAL"
# ============================================================
# CONFIG / MODELS
# ============================================================
@dataclass
class ServiceIntervalProfile:
    supervisor_tick_sec: float
    link_tick_sec: float
    stage2_tick_sec: float
    safety_tick_sec: float
    snapshot_tick_sec: float
    debug_record_tick_sec: float
@dataclass
class RuntimePerformanceGovernorConfig:
    emit_status_logs: bool = True
    normal_profile: ServiceIntervalProfile = ServiceIntervalProfile(
        supervisor_tick_sec=0.10,
        link_tick_sec=0.10,
        stage2_tick_sec=0.10,
        safety_tick_sec=0.25,
        snapshot_tick_sec=1.00,
        debug_record_tick_sec=1.50,
    )
    reduced_profile: ServiceIntervalProfile = ServiceIntervalProfile(
        supervisor_tick_sec=0.15,
        link_tick_sec=0.20,
        stage2_tick_sec=0.20,
        safety_tick_sec=0.35,
        snapshot_tick_sec=2.00,
        debug_record_tick_sec=3.00,
    )
    critical_profile: ServiceIntervalProfile = ServiceIntervalProfile(
        supervisor_tick_sec=0.20,
        link_tick_sec=0.30,
        stage2_tick_sec=0.30,
        safety_tick_sec=0.40,
        snapshot_tick_sec=4.00,
        debug_record_tick_sec=5.00,
    )
@dataclass
class PerformanceGovernorSnapshot:
    ts: float
    mode: PerformanceMode
    recommended_intervals: dict[str, float]
    reasons: list[str] = field(default_factory=list)
    last_error: Optional[str] = None
    summary: str = ""
# ============================================================
# MAIN CLASS
# ============================================================
class RemotePiRuntimePerformanceGovernor:
    def __init__(
        self,
        *,
        snapshot_bus=None,
        health_scorer=None,
        status_sink: Optional[Callable[[str, dict], None]] = None,
        config: Optional[RuntimePerformanceGovernorConfig] = None,
    ):
        self.snapshot_bus = snapshot_bus
        self.health_scorer = health_scorer
        self.status_sink = status_sink
        self.config = config or RuntimePerformanceGovernorConfig()
        self._mode = PerformanceMode.NORMAL
        self._reasons: list[str] = []
        self._last_error: Optional[str] = None
        self._last_compute_ts: float = 0.0
    # --------------------------------------------------------
    # INTERNAL
    # --------------------------------------------------------
    def _emit_status(self, topic: str, **payload) -> None:
        if self.config.emit_status_logs and self.status_sink is not None:
            self.status_sink(topic, {
                "ts": time.time(),
                **payload,
            })
    def _get_snapshot(self) -> dict[str, Any]:
        if self.snapshot_bus is not None and hasattr(self.snapshot_bus, "build_service_snapshot"):
            try:
                return dict(self.snapshot_bus.build_service_snapshot())
            except Exception as exc:
                self._last_error = str(exc)
        return {
            "overall_ok": False,
            "faults": ["SNAPSHOT_UNAVAILABLE"],
            "warnings": [],
            "lifecycle": {},
            "safety_supervisor": {},
            "stage2_wiring": {},
        }
    def _get_health(self) -> dict[str, Any]:
        if self.health_scorer is not None and hasattr(self.health_scorer, "to_dict"):
            try:
                return dict(self.health_scorer.to_dict())
            except Exception as exc:
                self._last_error = str(exc)
        return {
            "score": 50,
            "grade": "D",
            "overall_ok": False,
            "summary": "health unavailable",
        }
    def _profile_for_mode(self, mode: PerformanceMode) -> ServiceIntervalProfile:
        if mode == PerformanceMode.NORMAL:
            return self.config.normal_profile
        if mode == PerformanceMode.REDUCED:
            return self.config.reduced_profile
        return self.config.critical_profile
    # --------------------------------------------------------
    # MODE COMPUTE
    # --------------------------------------------------------
    def compute_mode(self) -> PerformanceMode:
        snap = self._get_snapshot()
        health = self._get_health()
        reasons: list[str] = []
        faults = list(snap.get("faults", []))
        warnings = list(snap.get("warnings", []))
        lifecycle = dict(snap.get("lifecycle", {}))
        safety = dict(snap.get("safety_supervisor", {}))
        health_score = int(health.get("score", 50))
        lifecycle_state = str(lifecycle.get("lifecycle_state", "UNKNOWN"))
        safety_level = str(safety.get("level", "UNKNOWN"))
        mode = PerformanceMode.NORMAL
        if lifecycle_state in ("FAULTED", "SHUTDOWN"):
            mode = PerformanceMode.CRITICAL
            reasons.append(f"lifecycle={lifecycle_state}")
        if safety_level in ("FAULT", "CRITICAL", "SHUTDOWN"):
            mode = PerformanceMode.CRITICAL
            reasons.append(f"safety={safety_level}")
        if faults:
            mode = PerformanceMode.CRITICAL
            reasons.append(f"fault_count={len(faults)}")
        if mode != PerformanceMode.CRITICAL:
            if warnings or health_score < 75 or not bool(snap.get("overall_ok", False)):
                mode = PerformanceMode.REDUCED
                if warnings:
                    reasons.append(f"warning_count={len(warnings)}")
                if health_score < 75:
                    reasons.append(f"health_score={health_score}")
                if not bool(snap.get("overall_ok", False)):
                    reasons.append("snapshot_overall_not_ok")
        if not reasons:
            reasons.append("runtime_healthy")
        self._mode = mode
        self._reasons = reasons
        self._last_compute_ts = time.time()
        self._emit_status(
            "performance_governor/mode_computed",
            mode=mode.value,
            reasons=reasons,
            health_score=health_score,
        )
        return mode
    # --------------------------------------------------------
    # INTERVALS
    # --------------------------------------------------------
    def get_recommended_intervals(self) -> dict[str, float]:
        mode = self.compute_mode()
        profile = self._profile_for_mode(mode)
        return {
            "supervisor_tick_sec": profile.supervisor_tick_sec,
            "link_tick_sec": profile.link_tick_sec,
            "stage2_tick_sec": profile.stage2_tick_sec,
            "safety_tick_sec": profile.safety_tick_sec,
            "snapshot_tick_sec": profile.snapshot_tick_sec,
            "debug_record_tick_sec": profile.debug_record_tick_sec,
        }
    def should_run(self, service_name: str, last_run_ts: float) -> bool:
        now = time.time()
        intervals = self.get_recommended_intervals()
        interval_key = f"{service_name}_sec"
        if interval_key not in intervals:
            # unknown service: safe default
            return True
        elapsed = now - float(last_run_ts)
        return elapsed >= float(intervals[interval_key])
    # --------------------------------------------------------
    # SNAPSHOT
    # --------------------------------------------------------
    @property
    def mode(self) -> PerformanceMode:
        return self._mode
    def snapshot(self) -> PerformanceGovernorSnapshot:
        intervals = self.get_recommended_intervals()
        return PerformanceGovernorSnapshot(
            ts=time.time(),
            mode=self._mode,
            recommended_intervals=intervals,
            reasons=list(self._reasons),
            last_error=self._last_error,
            summary=(
                f"mode={self._mode.value} | "
                f"reasons={','.join(self._reasons)}"
            ),
        )
    def to_dict(self) -> dict[str, Any]:
        snap = self.snapshot()
        return {
            "ts": snap.ts,
            "mode": snap.mode.value,
            "recommended_intervals": dict(snap.recommended_intervals),
            "reasons": list(snap.reasons),
            "last_error": snap.last_error,
            "summary": snap.summary,
            "last_compute_ts": self._last_compute_ts,
        }


# ============================================================
# MODULE-R058
# ============================================================

# runtime/remotepi_multi_link_failover_manager.py
"""
MODULE-R058
RemotePi Multi-Link Failover Manager
------------------------------------

Purpose:
    Manage multiple transport/link paths for RemotePi runtime.

Responsibilities:
    - Maintain an ordered set of link candidates
    - Select an active link
    - Fail over when current link becomes unhealthy
    - Optionally fail back to preferred link when it recovers
    - Provide unified connect/send/poll/status surface

Design goals:
    - Deterministic link selection
    - Safe fallback behavior
    - Transport-agnostic integration
"""
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional
# ============================================================
# DATA MODELS
# ============================================================
@dataclass
class LinkCandidateConfig:
    name: str
    priority: int
@dataclass
class MultiLinkFailoverConfig:
    emit_status_logs: bool = True
    auto_failback_to_preferred: bool = True
    switch_cooldown_sec: float = 1.0
@dataclass
class MultiLinkSnapshot:
    ts: float
    active_link_name: Optional[str]
    active_priority: Optional[int]
    healthy_links: list[str] = field(default_factory=list)
    unhealthy_links: list[str] = field(default_factory=list)
    switch_count: int = 0
    last_switch_ts: float = 0.0
    last_error: Optional[str] = None
    summary: str = ""
# ============================================================
# MAIN CLASS
# ============================================================
class RemotePiMultiLinkFailoverManager:
    def __init__(
        self,
        *,
        link_candidates: list[tuple[LinkCandidateConfig, Any]],
        status_sink: Optional[Callable[[str, dict], None]] = None,
        config: Optional[MultiLinkFailoverConfig] = None,
    ):
        """
        link_candidates:
            list of (LinkCandidateConfig, link_object)
        link_object expected surface:
            - connect() -> bool           [optional]
            - disconnect() -> None       [optional]
            - tick() -> None             [optional]
            - to_dict() -> dict          [optional]
            - state / is_connected()     [optional]
        """
        if not link_candidates:
            raise ValueError("link_candidates cannot be empty")
        self.status_sink = status_sink
        self.config = config or MultiLinkFailoverConfig()
        self._candidates: list[tuple[LinkCandidateConfig, Any]] = sorted(
            link_candidates,
            key=lambda item: int(item[0].priority)
        )
        self._active_name: Optional[str] = None
        self._switch_count = 0
        self._last_switch_ts = 0.0
        self._last_error: Optional[str] = None
    # --------------------------------------------------------
    # INTERNAL
    # --------------------------------------------------------
    def _emit_status(self, topic: str, **payload) -> None:
        if self.config.emit_status_logs and self.status_sink is not None:
            self.status_sink(topic, {
                "ts": time.time(),
                **payload,
            })
    def _candidate_names(self) -> list[str]:
        return [cfg.name for cfg, _obj in self._candidates]
    def _get_candidate(self, name: str):
        for cfg, obj in self._candidates:
            if cfg.name == name:
                return cfg, obj
        return None, None
    def _safe_call(self, obj: Any, method_name: str, *args, default=None, **kwargs):
        if obj is None or not hasattr(obj, method_name):
            return default
        try:
            return getattr(obj, method_name)(*args, **kwargs)
        except Exception as exc:
            self._last_error = str(exc)
            self._emit_status(
                "multi_link/call_error",
                method_name=method_name,
                error=str(exc),
            )
            return default
    def _candidate_health(self, obj: Any) -> bool:
        # 1) explicit state enum/string
        if hasattr(obj, "state"):
            try:
                state = getattr(obj, "state")
                value = getattr(state, "value", state)
                value = str(value).upper()
                if value in ("UP", "CONNECTED", "RUNNING"):
                    return True
                if value in ("DEGRADED",):
                    return True
                if value in ("DOWN", "LOST", "DISCONNECTED", "ERROR"):
                    return False
            except Exception:
                pass
        # 2) explicit is_connected
        if hasattr(obj, "is_connected"):
            try:
                return bool(obj.is_connected())
            except Exception:
                return False
        # 3) dict snapshot
        if hasattr(obj, "to_dict"):
            try:
                d = obj.to_dict()
                if "connected" in d:
                    return bool(d["connected"])
                if "master_link_ok" in d:
                    return bool(d["master_link_ok"])
            except Exception:
                return False
        return False
    def _healthy_candidates(self) -> list[tuple[LinkCandidateConfig, Any]]:
        result = []
        for cfg, obj in self._candidates:
            if self._candidate_health(obj):
                result.append((cfg, obj))
        return result
    def _now_can_switch(self) -> bool:
        return (time.time() - self._last_switch_ts) >= float(self.config.switch_cooldown_sec)
    def _set_active(self, name: Optional[str]) -> None:
        if name == self._active_name:
            return
        self._active_name = name
        self._switch_count += 1
        self._last_switch_ts = time.time()
        self._emit_status(
            "multi_link/active_switched",
            active_link_name=name,
            switch_count=self._switch_count,
        )
    def _best_healthy_candidate(self):
        healthy = self._healthy_candidates()
        if not healthy:
            return None, None
        return healthy[0]
    # --------------------------------------------------------
    # CONNECTION CONTROL
    # --------------------------------------------------------
    def connect_all(self) -> None:
        for cfg, obj in self._candidates:
            self._safe_call(obj, "connect", default=None)
            self._emit_status("multi_link/connect_attempt", candidate=cfg.name)
    def disconnect_all(self) -> None:
        for cfg, obj in self._candidates:
            self._safe_call(obj, "disconnect", default=None)
            self._emit_status("multi_link/disconnect_attempt", candidate=cfg.name)
        self._active_name = None
    def force_active(self, name: str) -> bool:
        cfg, obj = self._get_candidate(name)
        if cfg is None:
            self._last_error = f"unknown candidate: {name}"
            return False
        if not self._candidate_health(obj):
            self._last_error = f"candidate not healthy: {name}"
            return False
        self._set_active(cfg.name)
        return True
    # --------------------------------------------------------
    # FAILOVER LOGIC
    # --------------------------------------------------------
    def _ensure_active_selected(self) -> None:
        if self._active_name is not None:
            return
        cfg, _obj = self._best_healthy_candidate()
        if cfg is not None:
            self._set_active(cfg.name)
    def _evaluate_failover(self) -> None:
        active_cfg, active_obj = self._get_candidate(self._active_name) if self._active_name else (None, None)
        # no active -> choose best healthy
        if active_cfg is None:
            self._ensure_active_selected()
            return
        active_healthy = self._candidate_health(active_obj)
        # active unhealthy -> fail over
        if not active_healthy:
            if not self._now_can_switch():
                return
            best_cfg, _best_obj = self._best_healthy_candidate()
            if best_cfg is not None:
                self._set_active(best_cfg.name)
            else:
                self._set_active(None)
            return
        # active healthy but maybe fail back to preferred
        if self.config.auto_failback_to_preferred:
            preferred_cfg, preferred_obj = self._candidates[0]
            if preferred_cfg.name != self._active_name:
                if self._candidate_health(preferred_obj) and self._now_can_switch():
                    self._set_active(preferred_cfg.name)
    # --------------------------------------------------------
    # TICK / UNIFIED API
    # --------------------------------------------------------
    def tick(self) -> None:
        for _cfg, obj in self._candidates:
            self._safe_call(obj, "tick", default=None)
        self._evaluate_failover()
    def send_via_active(self, raw_or_payload: Any) -> bool:
        if self._active_name is None:
            self._ensure_active_selected()
        cfg, obj = self._get_candidate(self._active_name) if self._active_name else (None, None)
        if cfg is None:
            self._last_error = "no active link"
            return False
        # try common names
        for method_name in ("send", "send_command", "publish"):
            if hasattr(obj, method_name):
                result = self._safe_call(obj, method_name, raw_or_payload, default=False)
                return bool(result)
        self._last_error = f"active link has no send method: {cfg.name}"
        return False
    def poll_active_once(self) -> bool:
        if self._active_name is None:
            self._ensure_active_selected()
        cfg, obj = self._get_candidate(self._active_name) if self._active_name else (None, None)
        if cfg is None:
            return False
        for method_name in ("poll_once", "poll"):
            if hasattr(obj, method_name):
                result = self._safe_call(obj, method_name, default=False)
                return bool(result) if result is not None else False
        return False
    # --------------------------------------------------------
    # STATUS
    # --------------------------------------------------------
    @property
    def active_link_name(self) -> Optional[str]:
        return self._active_name
    def to_dict(self) -> dict[str, Any]:
        healthy_links = []
        unhealthy_links = []
        detailed = {}
        for cfg, obj in self._candidates:
            healthy = self._candidate_health(obj)
            if healthy:
                healthy_links.append(cfg.name)
            else:
                unhealthy_links.append(cfg.name)
            d = None
            if hasattr(obj, "to_dict"):
                d = self._safe_call(obj, "to_dict", default=None)
            detailed[cfg.name] = {
                "priority": cfg.priority,
                "healthy": healthy,
                "details": d,
            }
        active_priority = None
        if self._active_name is not None:
            cfg, _obj = self._get_candidate(self._active_name)
            if cfg is not None:
                active_priority = cfg.priority
        snap = MultiLinkSnapshot(
            ts=time.time(),
            active_link_name=self._active_name,
            active_priority=active_priority,
            healthy_links=healthy_links,
            unhealthy_links=unhealthy_links,
            switch_count=self._switch_count,
            last_switch_ts=self._last_switch_ts,
            last_error=self._last_error,
            summary=(
                f"active={self._active_name} | "
                f"healthy={healthy_links} | "
                f"unhealthy={unhealthy_links} | "
                f"switch_count={self._switch_count}"
            ),
        )
        return {
            "ts": snap.ts,
            "active_link_name": snap.active_link_name,
            "active_priority": snap.active_priority,
            "healthy_links": list(snap.healthy_links),
            "unhealthy_links": list(snap.unhealthy_links),
            "switch_count": snap.switch_count,
            "last_switch_ts": snap.last_switch_ts,
            "last_error": snap.last_error,
            "summary": snap.summary,
            "candidates": detailed,
        }


# ============================================================
# MODULE-R059
# ============================================================

# runtime/remotepi_autonomous_mission_kernel.py
"""
MODULE-R059
RemotePi Autonomous Mission Kernel
----------------------------------

Purpose:
    Autonomous mission execution kernel for RemotePi runtime.

Responsibilities:
    - Hold mission definitions and mission steps
    - Execute mission steps sequentially
    - Support arm / start / pause / resume / abort
    - Track mission progress and step outcomes
    - Stay compatible with lifecycle / safety restrictions

Design goals:
    - Deterministic mission progression
    - Safe abort behavior
    - Minimal assumptions about actual actuator layer
"""
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional
# ============================================================
# ENUMS
# ============================================================
class MissionState(str, Enum):
    IDLE = "IDLE"
    ARMED = "ARMED"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    ABORTED = "ABORTED"
    FAILED = "FAILED"
class MissionStepState(str, Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    DONE = "DONE"
    FAILED = "FAILED"
    ABORTED = "ABORTED"
    TIMEOUT = "TIMEOUT"
# ============================================================
# MODELS
# ============================================================
@dataclass
class MissionStep:
    name: str
    action_name: str
    payload: dict[str, Any] = field(default_factory=dict)
    timeout_sec: float = 5.0
@dataclass
class MissionDefinition:
    mission_name: str
    steps: list[MissionStep] = field(default_factory=list)
@dataclass
class ActiveStepRuntime:
    index: int
    name: str
    action_name: str
    started_ts: float
    timeout_sec: float
    state: MissionStepState = MissionStepState.ACTIVE
    payload: dict[str, Any] = field(default_factory=dict)
    result: dict[str, Any] = field(default_factory=dict)
@dataclass
class MissionSnapshot:
    ts: float
    mission_name: Optional[str]
    mission_state: MissionState
    current_step_index: int
    total_steps: int
    progress_ratio: float
    last_error: Optional[str]
    summary: str
# ============================================================
# MAIN CLASS
# ============================================================
class RemotePiAutonomousMissionKernel:
    def __init__(
        self,
        *,
        runtime_lifecycle=None,
        state_store=None,
        command_sink: Optional[Callable[[str, dict], None]] = None,
        status_sink: Optional[Callable[[str, dict], None]] = None,
    ):
        self.runtime_lifecycle = runtime_lifecycle
        self.state_store = state_store
        self.command_sink = command_sink or (lambda command_name, payload: None)
        self.status_sink = status_sink
        self._mission: Optional[MissionDefinition] = None
        self._mission_state = MissionState.IDLE
        self._current_step_index = -1
        self._active_step: Optional[ActiveStepRuntime] = None
        self._step_history: list[dict[str, Any]] = []
        self._last_error: Optional[str] = None
        self._last_tick_ts: float = 0.0
    # --------------------------------------------------------
    # INTERNAL
    # --------------------------------------------------------
    def _emit_status(self, topic: str, **payload) -> None:
        if self.status_sink is not None:
            self.status_sink(topic, {
                "ts": time.time(),
                **payload,
            })
    def _set_state(self, state: MissionState, summary: str = "") -> None:
        self._mission_state = state
        self._emit_status(
            "autonomous_kernel/state_changed",
            mission_state=state.value,
            summary=summary,
        )
    def _can_run_autonomous(self) -> bool:
        if self.runtime_lifecycle is not None and hasattr(self.runtime_lifecycle, "to_dict"):
            try:
                lifecycle = self.runtime_lifecycle.to_dict()
                lifecycle_state = str(lifecycle.get("lifecycle_state", "UNKNOWN"))
                if lifecycle_state not in ("READY", "RUNNING"):
                    return False
            except Exception:
                return False
        if self.state_store is not None and hasattr(self.state_store, "get_safety"):
            try:
                safety = self.state_store.get_safety()
                severity = str(safety.get("severity", "UNKNOWN"))
                if severity in ("FAULT", "CRITICAL", "SHUTDOWN"):
                    return False
            except Exception:
                return False
        return True
    def _start_step(self, index: int) -> None:
        if self._mission is None:
            raise RuntimeError("no active mission")
        step = self._mission.steps[index]
        self._active_step = ActiveStepRuntime(
            index=index,
            name=step.name,
            action_name=step.action_name,
            started_ts=time.time(),
            timeout_sec=float(step.timeout_sec),
            state=MissionStepState.ACTIVE,
            payload=dict(step.payload),
        )
        self._current_step_index = index
        self._emit_status(
            "autonomous_kernel/step_started",
            index=index,
            step_name=step.name,
            action_name=step.action_name,
        )
        try:
            self.command_sink(step.action_name, dict(step.payload))
        except Exception as exc:
            self._last_error = str(exc)
            self._active_step.state = MissionStepState.FAILED
            self._active_step.result = {"error": str(exc)}
    def _finalize_active_step(self, state: MissionStepState, result: Optional[dict] = None) -> None:
        if self._active_step is None:
            return
        self._active_step.state = state
        self._active_step.result = dict(result or {})
        self._step_history.append({
            "index": self._active_step.index,
            "name": self._active_step.name,
            "action_name": self._active_step.action_name,
            "started_ts": self._active_step.started_ts,
            "timeout_sec": self._active_step.timeout_sec,
            "state": self._active_step.state.value,
            "payload": dict(self._active_step.payload),
            "result": dict(self._active_step.result),
        })
        self._emit_status(
            "autonomous_kernel/step_finalized",
            index=self._active_step.index,
            step_name=self._active_step.name,
            state=self._active_step.state.value,
            result=self._active_step.result,
        )
        self._active_step = None
    def _advance(self) -> None:
        if self._mission is None:
            self._set_state(MissionState.IDLE, "No mission loaded.")
            return
        next_index = self._current_step_index + 1
        if next_index >= len(self._mission.steps):
            self._set_state(MissionState.COMPLETED, "Mission completed.")
            return
        self._start_step(next_index)
    # --------------------------------------------------------
    # MISSION MANAGEMENT
    # --------------------------------------------------------
    def load_mission(self, mission: MissionDefinition) -> None:
        self._mission = mission
        self._current_step_index = -1
        self._active_step = None
        self._step_history.clear()
        self._last_error = None
        self._set_state(MissionState.IDLE, f"Mission loaded: {mission.mission_name}")
    def arm(self) -> bool:
        if self._mission is None:
            self._last_error = "no mission loaded"
            return False
        if not self._can_run_autonomous():
            self._last_error = "runtime not safe for autonomous mode"
            return False
        self._set_state(MissionState.ARMED, "Mission armed.")
        return True
    def start(self) -> bool:
        if self._mission is None:
            self._last_error = "no mission loaded"
            return False
        if self._mission_state not in (MissionState.ARMED, MissionState.PAUSED):
            self._last_error = f"invalid start state: {self._mission_state.value}"
            return False
        if not self._can_run_autonomous():
            self._last_error = "runtime not safe for autonomous execution"
            return False
        self._set_state(MissionState.RUNNING, "Mission running.")
        if self._active_step is None:
            self._advance()
        return True
    def pause(self) -> bool:
        if self._mission_state != MissionState.RUNNING:
            self._last_error = "mission not running"
            return False
        self._set_state(MissionState.PAUSED, "Mission paused.")
        return True
    def resume(self) -> bool:
        if self._mission_state != MissionState.PAUSED:
            self._last_error = "mission not paused"
            return False
        return self.start()
    def abort(self, summary: str = "Mission aborted.") -> None:
        if self._active_step is not None:
            self._finalize_active_step(MissionStepState.ABORTED, {"summary": summary})
        self._set_state(MissionState.ABORTED, summary)
    # --------------------------------------------------------
    # STEP FEEDBACK
    # --------------------------------------------------------
    def mark_step_done(self, result: Optional[dict] = None) -> bool:
        if self._active_step is None:
            self._last_error = "no active step"
            return False
        self._finalize_active_step(MissionStepState.DONE, result)
        self._advance()
        return True
    def mark_step_failed(self, result: Optional[dict] = None) -> bool:
        if self._active_step is None:
            self._last_error = "no active step"
            return False
        self._finalize_active_step(MissionStepState.FAILED, result)
        self._set_state(MissionState.FAILED, "Mission step failed.")
        return True
    # --------------------------------------------------------
    # TICK
    # --------------------------------------------------------
    def tick(self) -> None:
        self._last_tick_ts = time.time()
        if self._mission_state != MissionState.RUNNING:
            return
        if not self._can_run_autonomous():
            self.abort("Autonomous execution aborted by lifecycle/safety constraint.")
            return
        if self._active_step is None:
            self._advance()
            return
        elapsed = time.time() - self._active_step.started_ts
        if elapsed > self._active_step.timeout_sec:
            self._finalize_active_step(
                MissionStepState.TIMEOUT,
                {"elapsed_sec": elapsed},
            )
            self._set_state(MissionState.FAILED, "Mission step timeout.")
    # --------------------------------------------------------
    # SNAPSHOT
    # --------------------------------------------------------
    @property
    def mission_state(self) -> MissionState:
        return self._mission_state
    def to_dict(self) -> dict[str, Any]:
        total_steps = len(self._mission.steps) if self._mission is not None else 0
        if total_steps <= 0:
            progress_ratio = 0.0
        else:
            completed_steps = len([s for s in self._step_history if s["state"] == MissionStepState.DONE.value])
            progress_ratio = completed_steps / float(total_steps)
        snap = MissionSnapshot(
            ts=time.time(),
            mission_name=(self._mission.mission_name if self._mission is not None else None),
            mission_state=self._mission_state,
            current_step_index=self._current_step_index,
            total_steps=total_steps,
            progress_ratio=progress_ratio,
            last_error=self._last_error,
            summary=(
                f"mission={self._mission.mission_name if self._mission else None} | "
                f"state={self._mission_state.value} | "
                f"step={self._current_step_index} | "
                f"progress={progress_ratio:.2f}"
            ),
        )
        return {
            "ts": snap.ts,
            "mission_name": snap.mission_name,
            "mission_state": snap.mission_state.value,
            "current_step_index": snap.current_step_index,
            "total_steps": snap.total_steps,
            "progress_ratio": snap.progress_ratio,
            "active_step": None if self._active_step is None else {
                "index": self._active_step.index,
                "name": self._active_step.name,
                "action_name": self._active_step.action_name,
                "started_ts": self._active_step.started_ts,
                "timeout_sec": self._active_step.timeout_sec,
                "state": self._active_step.state.value,
                "payload": dict(self._active_step.payload),
                "result": dict(self._active_step.result),
            },
            "step_history": list(self._step_history),
            "last_error": snap.last_error,
            "summary": snap.summary,
            "last_tick_ts": self._last_tick_ts,
        }


# ============================================================
# MODULE-R060
# ============================================================

# runtime/remotepi_runtime_digital_twin_publisher.py
"""
MODULE-R060
RemotePi Runtime Digital Twin Publisher
---------------------------------------

Purpose:
    Publish RemotePi runtime state as a digital twin payload for SCADA/cloud/service systems.

Responsibilities:
    - Read runtime state from snapshot bus and related modules
    - Build compact or full digital twin payloads
    - Publish payloads through an abstract publish sink
    - Support periodic publishing
    - Expose last publish status and diagnostics

Design goals:
    - Transport-agnostic
    - Deterministic payload structure
    - Safe fallback behavior
"""
import json
import time
from dataclasses import dataclass
from typing import Any, Callable, Optional
# ============================================================
# CONFIG / MODELS
# ============================================================
@dataclass
class DigitalTwinPublisherConfig:
    node_id: str = "RemotePi"
    twin_version: str = "1.0"
    publish_topic: str = "remotepi/digital_twin"
    default_publish_interval_sec: float = 2.0
    emit_status_logs: bool = True
    json_indent: int = 2
@dataclass
class DigitalTwinSnapshot:
    ts: float
    node_id: str
    publish_count: int
    last_publish_ts: float
    last_publish_ok: bool
    last_error: Optional[str]
    summary: str
# ============================================================
# MAIN CLASS
# ============================================================
class RemotePiRuntimeDigitalTwinPublisher:
    def __init__(
        self,
        *,
        snapshot_bus=None,
        runtime_supervisor=None,
        health_scorer=None,
        diagnostics_exporter=None,
        mission_kernel=None,
        publish_sink: Optional[Callable[[str, dict], bool]] = None,
        status_sink: Optional[Callable[[str, dict], None]] = None,
        config: Optional[DigitalTwinPublisherConfig] = None,
    ):
        self.snapshot_bus = snapshot_bus
        self.runtime_supervisor = runtime_supervisor
        self.health_scorer = health_scorer
        self.diagnostics_exporter = diagnostics_exporter
        self.mission_kernel = mission_kernel
        self.publish_sink = publish_sink or (lambda topic, payload: True)
        self.status_sink = status_sink
        self.config = config or DigitalTwinPublisherConfig()
        self._publish_count = 0
        self._last_publish_ts = 0.0
        self._last_publish_ok = False
        self._last_error: Optional[str] = None
        self._last_tick_ts: float = 0.0
    # --------------------------------------------------------
    # INTERNAL
    # --------------------------------------------------------
    def _emit_status(self, topic: str, **payload) -> None:
        if self.config.emit_status_logs and self.status_sink is not None:
            self.status_sink(topic, {
                "ts": time.time(),
                **payload,
            })
    def _safe_runtime_snapshot(self) -> dict[str, Any]:
        if self.snapshot_bus is not None and hasattr(self.snapshot_bus, "build_service_snapshot"):
            try:
                return dict(self.snapshot_bus.build_service_snapshot())
            except Exception as exc:
                self._last_error = str(exc)
        return {
            "created_ts": time.time(),
            "overall_ok": False,
            "overall_summary": "runtime snapshot unavailable",
            "warnings": [],
            "faults": ["RUNTIME_SNAPSHOT_UNAVAILABLE"],
        }
    def _safe_supervisor(self) -> dict[str, Any]:
        if self.runtime_supervisor is not None and hasattr(self.runtime_supervisor, "to_dict"):
            try:
                return dict(self.runtime_supervisor.to_dict())
            except Exception as exc:
                self._last_error = str(exc)
        return {}
    def _safe_health(self) -> dict[str, Any]:
        if self.health_scorer is not None and hasattr(self.health_scorer, "to_dict"):
            try:
                return dict(self.health_scorer.to_dict())
            except Exception as exc:
                self._last_error = str(exc)
        return {}
    def _safe_diagnostics(self) -> dict[str, Any]:
        if self.diagnostics_exporter is not None and hasattr(self.diagnostics_exporter, "build_compact_report"):
            try:
                return dict(self.diagnostics_exporter.build_compact_report())
            except Exception as exc:
                self._last_error = str(exc)
        return {}
    def _safe_mission(self) -> dict[str, Any]:
        if self.mission_kernel is not None and hasattr(self.mission_kernel, "to_dict"):
            try:
                return dict(self.mission_kernel.to_dict())
            except Exception as exc:
                self._last_error = str(exc)
        return {}
    # --------------------------------------------------------
    # PAYLOAD BUILDERS
    # --------------------------------------------------------
    def build_compact_payload(self) -> dict[str, Any]:
        runtime_snap = self._safe_runtime_snapshot()
        supervisor = self._safe_supervisor()
        health = self._safe_health()
        mission = self._safe_mission()
        payload = {
            "node_type": "RemotePi",
            "node_id": self.config.node_id,
            "twin_version": self.config.twin_version,
            "created_ts": time.time(),
            "runtime_created_ts": runtime_snap.get("created_ts", time.time()),
            "overall_ok": bool(runtime_snap.get("overall_ok", False)),
            "overall_summary": str(runtime_snap.get("overall_summary", "")),
            "warnings": list(runtime_snap.get("warnings", [])),
            "faults": list(runtime_snap.get("faults", [])),
            "supervisor": {
                "state": supervisor.get("state", "UNKNOWN"),
                "lifecycle_state": supervisor.get("lifecycle_state", "UNKNOWN"),
                "link_state": supervisor.get("link_state", "UNKNOWN"),
                "safety_level": supervisor.get("safety_level", "UNKNOWN"),
            },
            "health": {
                "score": health.get("score"),
                "grade": health.get("grade"),
                "overall_ok": health.get("overall_ok"),
            },
            "mission": {
                "mission_name": mission.get("mission_name"),
                "mission_state": mission.get("mission_state"),
                "progress_ratio": mission.get("progress_ratio"),
            },
        }
        return payload
    def build_full_payload(self) -> dict[str, Any]:
        runtime_snap = self._safe_runtime_snapshot()
        supervisor = self._safe_supervisor()
        health = self._safe_health()
        diagnostics = self._safe_diagnostics()
        mission = self._safe_mission()
        payload = {
            "node_type": "RemotePi",
            "node_id": self.config.node_id,
            "twin_version": self.config.twin_version,
            "publish_topic": self.config.publish_topic,
            "created_ts": time.time(),
            "runtime": runtime_snap,
            "supervisor": supervisor,
            "health": health,
            "diagnostics": diagnostics,
            "mission": mission,
            "publisher_status": {
                "publish_count": self._publish_count,
                "last_publish_ts": self._last_publish_ts,
                "last_publish_ok": self._last_publish_ok,
                "last_error": self._last_error,
            },
        }
        return payload
    def build_full_json(self) -> str:
        return json.dumps(
            self.build_full_payload(),
            ensure_ascii=False,
            indent=self.config.json_indent,
        )
    # --------------------------------------------------------
    # PUBLISH
    # --------------------------------------------------------
    def publish_compact(self) -> bool:
        payload = self.build_compact_payload()
        try:
            ok = bool(self.publish_sink(self.config.publish_topic, payload))
        except Exception as exc:
            self._last_error = str(exc)
            self._last_publish_ok = False
            self._emit_status(
                "digital_twin/publish_compact_error",
                error=str(exc),
            )
            return False
        self._publish_count += 1
        self._last_publish_ts = time.time()
        self._last_publish_ok = ok
        self._emit_status(
            "digital_twin/publish_compact",
            ok=ok,
            publish_count=self._publish_count,
            topic=self.config.publish_topic,
        )
        return ok
    def publish_full(self) -> bool:
        payload = self.build_full_payload()
        try:
            ok = bool(self.publish_sink(self.config.publish_topic, payload))
        except Exception as exc:
            self._last_error = str(exc)
            self._last_publish_ok = False
            self._emit_status(
                "digital_twin/publish_full_error",
                error=str(exc),
            )
            return False
        self._publish_count += 1
        self._last_publish_ts = time.time()
        self._last_publish_ok = ok
        self._emit_status(
            "digital_twin/publish_full",
            ok=ok,
            publish_count=self._publish_count,
            topic=self.config.publish_topic,
        )
        return ok
    # --------------------------------------------------------
    # PERIODIC TICK
    # --------------------------------------------------------
    def tick(self, publish_interval_sec: Optional[float] = None, full: bool = False) -> bool:
        self._last_tick_ts = time.time()
        interval = float(
            publish_interval_sec
            if publish_interval_sec is not None
            else self.config.default_publish_interval_sec
        )
        if self._last_publish_ts <= 0:
            return self.publish_full() if full else self.publish_compact()
        if (time.time() - self._last_publish_ts) < interval:
            return False
        return self.publish_full() if full else self.publish_compact()
    # --------------------------------------------------------
    # SNAPSHOT
    # --------------------------------------------------------
    def snapshot(self) -> DigitalTwinSnapshot:
        return DigitalTwinSnapshot(
            ts=time.time(),
            node_id=self.config.node_id,
            publish_count=self._publish_count,
            last_publish_ts=self._last_publish_ts,
            last_publish_ok=self._last_publish_ok,
            last_error=self._last_error,
            summary=(
                f"node_id={self.config.node_id} | "
                f"publish_count={self._publish_count} | "
                f"last_publish_ok={self._last_publish_ok}"
            ),
        )
    def to_dict(self) -> dict[str, Any]:
        snap = self.snapshot()
        return {
            "ts": snap.ts,
            "node_id": snap.node_id,
            "publish_count": snap.publish_count,
            "last_publish_ts": snap.last_publish_ts,
            "last_publish_ok": snap.last_publish_ok,
            "last_error": snap.last_error,
            "summary": snap.summary,
            "last_tick_ts": self._last_tick_ts,
            "config": {
                "twin_version": self.config.twin_version,
                "publish_topic": self.config.publish_topic,
                "default_publish_interval_sec": self.config.default_publish_interval_sec,
            },
        }


# ============================================================
# FINAL HMI APP (runtime-connected)
# ============================================================

# -*- coding: utf-8 -*-
from kivy.config import Config
Config.set("graphics", "resizable", "0")
Config.set("graphics", "width", "800")
Config.set("graphics", "height", "480")
Config.set("graphics", "position", "custom")
Config.set("graphics", "left", "50")
Config.set("graphics", "top", "50")
from kivy.app import App
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.behaviors import ToggleButtonBehavior, ButtonBehavior
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.textinput import TextInput
from kivy.uix.modalview import ModalView
from kivy.uix.scrollview import ScrollView
from kivy.properties import (
    StringProperty, BooleanProperty, ObjectProperty,
    NumericProperty, ListProperty
)
from kivy.graphics.texture import Texture
import os
import time
import math
import json
import random
import subprocess
import threading
# =========================================================
# RUNTIME IMPORTS
# =========================================================
from runtime.remotepi_integration_profile import build_hybrid_profile
from runtime.remotepi_hybrid_integration_manager import RemotePiHybridIntegrationManager
from runtime.remotepi_hmi_patch_adapter import RemotePiHMIPatchAdapter
from runtime.remotepi_state_store import RemotePiStateStore
from runtime.remotepi_event_router import RemotePiEventRouter
from runtime.remotepi_mode_fsm import RemotePiModeFSM
from runtime.remotepi_runtime_wiring_stage2 import RemotePiRuntimeWiringStage2
from runtime.remotepi_runtime_lifecycle import RemotePiRuntimeLifecycle
from runtime.remotepi_safety_supervisor import RemotePiSafetySupervisor
from runtime.remotepi_runtime_snapshot_bus import RemotePiRuntimeSnapshotBus
from runtime.remotepi_hardware_runtime_bridge import RemotePiHardwareRuntimeBridge
# =========================================================
# OPTIONAL LIBRARIES
# =========================================================
try:
    import paho.mqtt.client as mqtt
except ImportError:
    mqtt = None
try:
    import cv2
except Exception:
    cv2 = None
# =========================================================
# KEYBOARD POPUP
# =========================================================
class KeyboardPopup(ModalView):
    def __init__(self, title_text, callback_func, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (0.9, 0.85)
        self.auto_dismiss = False
        self.callback = callback_func
        self.title = title_text
        main_layout = BoxLayout(orientation="vertical", padding=10, spacing=10)
        lbl_title = Label(
            text=self.title,
            size_hint_y=None,
            height=30,
            font_size="18sp",
            bold=True,
            color=(0, 0.8, 1, 1),
        )
        main_layout.add_widget(lbl_title)
        self.txt_input = TextInput(
            multiline=False,
            size_hint_y=None,
            height=40,
            font_size="20sp",
        )
        main_layout.add_widget(self.txt_input)
        keys_layout = GridLayout(cols=12, spacing=5)
        row1 = ["q", "w", "e", "r", "t", "y", "u", "ı", "o", "p", "ğ", "ü"]
        row2 = ["a", "s", "d", "f", "g", "h", "j", "k", "l", "ş", "i", ","]
        row3 = ["z", "x", "c", "v", "b", "n", "m", "ö", "ç", ".", "@", "-"]
        for key in row1 + row2 + row3:
            btn = Button(text=key, font_size="18sp", bold=True)
            btn.bind(on_release=self.add_char)
            keys_layout.add_widget(btn)
        main_layout.add_widget(keys_layout)
        bottom_layout = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=50,
            spacing=10,
        )
        btn_backspace = Button(
            text="SIL",
            size_hint_x=0.2,
            background_color=(1, 0.3, 0.3, 1),
        )
        btn_backspace.bind(on_release=self.backspace)
        btn_space = Button(text="BOSLUK", size_hint_x=0.4)
        btn_space.bind(on_release=lambda x: self.add_char(x, " "))
        btn_cancel = Button(
            text="IPTAL",
            size_hint_x=0.2,
            background_color=(0.5, 0.5, 0.5, 1),
        )
        btn_cancel.bind(on_release=self.dismiss)
        btn_connect = Button(
            text="BAGLAN",
            size_hint_x=0.2,
            background_color=(0, 1, 0, 1),
        )
        btn_connect.bind(on_release=self.confirm)
        bottom_layout.add_widget(btn_backspace)
        bottom_layout.add_widget(btn_space)
        bottom_layout.add_widget(btn_cancel)
        bottom_layout.add_widget(btn_connect)
        main_layout.add_widget(bottom_layout)
        self.add_widget(main_layout)
    def add_char(self, instance, char=None):
        self.txt_input.text += char if char is not None else instance.text
    def backspace(self, instance):
        self.txt_input.text = self.txt_input.text[:-1]
    def confirm(self, instance):
        if self.callback:
            self.callback(self.txt_input.text)
        self.dismiss()
# =========================================================
# SYSTEM HELPERS
# =========================================================
def get_wifi_networks():
    networks = []
    wifi_interface = "wlan0"
    try:
        if os.path.exists("/sys/class/net/"):
            for iface in os.listdir("/sys/class/net/"):
                if os.path.exists(f"/sys/class/net/{iface}/wireless"):
                    wifi_interface = iface
                    break
    except Exception:
        pass
    try:
        subprocess.call(f"sudo ip link set {wifi_interface} up", shell=True)
        output = subprocess.check_output(
            f"sudo iwlist {wifi_interface} scan",
            shell=True
        ).decode("utf-8", errors="ignore")
        for line in output.split("\n"):
            line = line.strip()
            if "ESSID" in line:
                parts = line.split('"')
                if len(parts) > 1:
                    ssid = parts[1]
                    if ssid and ssid not in networks and "\\x00" not in ssid:
                        networks.append(ssid)
        if not networks:
            networks.append(f"Ag Bulunamadi ({wifi_interface})")
    except Exception:
        networks.append("TARAMA HATASI")
    return networks
def get_bluetooth_devices():
    devices = []
    try:
        output = subprocess.check_output(
            "hcitool scan",
            shell=True
        ).decode("utf-8", errors="ignore")
        lines = output.split("\n")[1:]
        for line in lines:
            if line.strip():
                parts = line.split("\t")
                if len(parts) > 1:
                    dev_name = parts[-1].strip()
                    if dev_name:
                        devices.append(dev_name)
        if not devices:
            devices.append("Cihaz Bulunamadi")
    except Exception:
        devices.append("HC-05 (Ornek)")
    return devices
# =========================================================
# MQTT MANAGER
# =========================================================
class MQTTManager:
    def __init__(self, broker_ip="192.168.1.100"):
        self.client = None
        self.broker_ip = broker_ip
        self.connected = False
        if mqtt is not None:
            try:
                self.client = mqtt.Client(client_id="RemotePi_HMI")
            except Exception:
                self.client = None
        if self.client:
            self.connect()
    def connect(self):
        try:
            self.client.connect(self.broker_ip, 1883, 60)
            self.client.loop_start()
            self.connected = True
            print(f"[MQTT] Connected to {self.broker_ip}")
        except Exception as e:
            self.connected = False
            print(f"[MQTT] Connection Error: {e}")
    def publish_control(self, payload: dict):
        if not self.client or not self.connected:
            return
        try:
            self.client.publish("remotepi/control", json.dumps(payload), qos=0)
        except Exception as e:
            print(f"[MQTT] Publish Error: {e}")
# =========================================================
# LEGACY HARDWARE MANAGER
# =========================================================
class HardwareManager:
    """
    Legacy-compatible hardware manager.
    Right joystick -> engine sound / engine buzzer principle korunur.
    """
    def __init__(self):
        self.sim_counter = 0.0
        self.PIN_REV_BUZZER = 20
        self.PIN_REV_LED = 26
        self.PIN_ENGINE_BUZZER = 18
        self.PIN_SIG_LEFT = 23
        self.PIN_SIG_RIGHT = 24
        self.PIN_PARKING_LIGHT = 5
        self.PIN_LOW_BEAM_LIGHT = 6
        self.PIN_HIGH_BEAM_LIGHT = 13
        self.PIN_RIG_FLOOR_LIGHT = 19
        self.PIN_ROTATION_LIGHT = 21
        self.GPIO = None
        self.gpio_available = False
        self.pwm_engine = None
        try:
            import RPi.GPIO as GPIO
            self.GPIO = GPIO
            self.GPIO.setmode(GPIO.BCM)
            self.GPIO.setwarnings(False)
            outputs = [
                self.PIN_REV_BUZZER,
                self.PIN_REV_LED,
                self.PIN_SIG_LEFT,
                self.PIN_SIG_RIGHT,
                self.PIN_PARKING_LIGHT,
                self.PIN_LOW_BEAM_LIGHT,
                self.PIN_HIGH_BEAM_LIGHT,
                self.PIN_RIG_FLOOR_LIGHT,
                self.PIN_ROTATION_LIGHT,
            ]
            for pin in outputs:
                self.GPIO.setup(pin, self.GPIO.OUT)
                self.GPIO.output(pin, False)
            self.GPIO.setup(self.PIN_ENGINE_BUZZER, self.GPIO.OUT)
            self.pwm_engine = self.GPIO.PWM(self.PIN_ENGINE_BUZZER, 50)
            self.pwm_engine.start(0)
            self.gpio_available = True
            print("[GPIO] Ready")
        except ImportError:
            print("[GPIO] RPi.GPIO not found, simulation mode")
        except Exception as e:
            print(f"[GPIO] Init error: {e}")
    def read_joystick(self, joystick_side, axis):
        self.sim_counter += 0.1
        val = math.sin(self.sim_counter) * 50
        if int(self.sim_counter * 10) % 5 == 0:
            return 0
        return int(val)
    def read_left_joystick_button(self):
        return False
    def read_right_joystick_button(self):
        return False
    def set_servo(self, angle):
        pass
    def set_motor_driver(self, speed, engine_sound_enabled=True):
        is_reverse = speed < -5
        if self.gpio_available:
            self.GPIO.output(self.PIN_REV_LED, is_reverse)
            self.GPIO.output(self.PIN_REV_BUZZER, is_reverse)
        if engine_sound_enabled:
            self.set_engine_buzzer(abs(speed))
        else:
            self.stop_engine_buzzer()
    def set_drawworks_motor(self, speed, engine_sound_enabled=True):
        if engine_sound_enabled:
            self.set_engine_buzzer(abs(speed))
        else:
            self.stop_engine_buzzer()
    def set_sandline_motor(self, speed, engine_sound_enabled=True):
        if engine_sound_enabled:
            self.set_engine_buzzer(abs(speed))
        else:
            self.stop_engine_buzzer()
    def set_winch_motor(self, speed, engine_sound_enabled=True):
        if engine_sound_enabled:
            self.set_engine_buzzer(abs(speed))
        else:
            self.stop_engine_buzzer()
    def set_rotary_motor(self, speed, engine_sound_enabled=True):
        if engine_sound_enabled:
            self.set_engine_buzzer(abs(speed))
        else:
            self.stop_engine_buzzer()
    def set_engine_buzzer(self, intensity):
        if not self.gpio_available or self.pwm_engine is None:
            return
        if intensity < 5:
            self.pwm_engine.ChangeDutyCycle(0)
            return
        freq = 50 + (intensity * 1.5)
        duty = min(60, max(15, intensity))
        self.pwm_engine.ChangeFrequency(freq)
        self.pwm_engine.ChangeDutyCycle(duty)
    def stop_engine_buzzer(self):
        if self.gpio_available and self.pwm_engine is not None:
            self.pwm_engine.ChangeDutyCycle(0)
    def set_signal_mode(self, enabled):
        if not self.gpio_available:
            return
        self.GPIO.output(self.PIN_SIG_LEFT, bool(enabled))
        self.GPIO.output(self.PIN_SIG_RIGHT, bool(enabled))
    def set_parking_light(self, enabled):
        if self.gpio_available:
            self.GPIO.output(self.PIN_PARKING_LIGHT, bool(enabled))
    def set_low_beam_light(self, enabled):
        if self.gpio_available:
            self.GPIO.output(self.PIN_LOW_BEAM_LIGHT, bool(enabled))
    def set_high_beam_light(self, enabled):
        if self.gpio_available:
            self.GPIO.output(self.PIN_HIGH_BEAM_LIGHT, bool(enabled))
    def set_rig_floor_light(self, enabled):
        if self.gpio_available:
            self.GPIO.output(self.PIN_RIG_FLOOR_LIGHT, bool(enabled))
    def set_rotation_light(self, enabled):
        if self.gpio_available:
            self.GPIO.output(self.PIN_ROTATION_LIGHT, bool(enabled))
    def stop_all_outputs(self):
        if self.gpio_available:
            self.GPIO.output(self.PIN_REV_BUZZER, False)
            self.GPIO.output(self.PIN_REV_LED, False)
            self.GPIO.output(self.PIN_SIG_LEFT, False)
            self.GPIO.output(self.PIN_SIG_RIGHT, False)
            self.GPIO.output(self.PIN_PARKING_LIGHT, False)
            self.GPIO.output(self.PIN_LOW_BEAM_LIGHT, False)
            self.GPIO.output(self.PIN_HIGH_BEAM_LIGHT, False)
            self.GPIO.output(self.PIN_RIG_FLOOR_LIGHT, False)
            self.GPIO.output(self.PIN_ROTATION_LIGHT, False)
            self.stop_engine_buzzer()
hw = HardwareManager()
# =========================================================
# UI CLASSES
# =========================================================
class IconToggle(ToggleButtonBehavior, Image):
    icon_name = StringProperty("")
class RootUI(Screen):
    pass
class CameraUI(Screen):
    cam_view = ObjectProperty(None)
    recording = BooleanProperty(False)
class FaultUI(Screen):
    pass
class BatteryUI(Screen):
    pass
class WifiUI(Screen):
    def on_enter(self):
        self.scan_networks()
    def scan_networks(self):
        self.ids.list_layout.clear_widgets()
        self.ids.list_layout.add_widget(
            Label(
                text="Kart Algilaniyor ve Taraniyor...",
                size_hint_y=None,
                height=40,
                color=(1, 1, 1, 1)
            )
        )
        threading.Thread(target=self._scan_thread, daemon=True).start()
    def _scan_thread(self):
        time.sleep(0.5)
        networks = get_wifi_networks()
        Clock.schedule_once(lambda dt: self._update_list(networks), 0)
    def _update_list(self, networks):
        self.ids.list_layout.clear_widgets()
        if not networks:
            self.ids.list_layout.add_widget(
                Label(text="Hicbir Ag Bulunamadi!", size_hint_y=None, height=40)
            )
            return
        for ssid in networks:
            if "HATASI" in ssid or "Hata" in ssid:
                btn = Button(
                    text=ssid,
                    size_hint_y=None,
                    height=50,
                    background_color=(1, 0, 0, 1)
                )
            else:
                btn = Button(text=ssid, size_hint_y=None, height=50)
            btn.bind(on_release=self.on_network_select)
            self.ids.list_layout.add_widget(btn)
    def on_network_select(self, instance):
        ssid = instance.text
        kb = KeyboardPopup(
            title_text=f"'{ssid}' icin Sifre Gir:",
            callback_func=lambda pwd: self.connect_to_network(ssid, pwd)
        )
        kb.open()
    def connect_to_network(self, ssid, password):
        print(f"[WIFI] BAGLANIYOR -> {ssid} / {password}")
        self.ids.list_layout.clear_widgets()
        self.ids.list_layout.add_widget(
            Label(
                text=f"'{ssid}' agina baglaniliyor...",
                color=(0, 1, 0, 1)
            )
        )
class BluetoothUI(Screen):
    def on_enter(self):
        self.scan_devices()
    def scan_devices(self):
        self.ids.list_layout.clear_widgets()
        self.ids.list_layout.add_widget(
            Label(text="BT Cihazlar Araniyor...", size_hint_y=None, height=40)
        )
        threading.Thread(target=self._scan_thread, daemon=True).start()
    def _scan_thread(self):
        time.sleep(0.5)
        devices = get_bluetooth_devices()
        Clock.schedule_once(lambda dt: self._update_list(devices), 0)
    def _update_list(self, devices):
        self.ids.list_layout.clear_widgets()
        if not devices:
            self.ids.list_layout.add_widget(
                Label(text="BT Cihaz Yok", size_hint_y=None, height=40)
            )
            return
        for dev in devices:
            btn = Button(text=dev, size_hint_y=None, height=50)
            btn.bind(on_release=self.on_device_select)
            self.ids.list_layout.add_widget(btn)
    def on_device_select(self, instance):
        dev_name = instance.text
        kb = KeyboardPopup(
            title_text=f"'{dev_name}' icin PIN Gir:",
            callback_func=lambda pin: self.pair_device(dev_name, pin)
        )
        kb.open()
    def pair_device(self, dev_name, pin):
        print(f"[BT] ESLESILIYOR -> {dev_name} / {pin}")
        self.ids.list_layout.clear_widgets()
        self.ids.list_layout.add_widget(
            Label(
                text=f"'{dev_name}' ile eslesiliyor...",
                color=(0, 1, 0, 1)
            )
        )
class FaultButton(ButtonBehavior, Label):
    _lp_ev = None
    _long_pressed = False
    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return super().on_touch_down(touch)
        ret = super().on_touch_down(touch)
        self._long_pressed = False
        if self._lp_ev:
            self._lp_ev.cancel()
        self._lp_ev = Clock.schedule_once(self._do_long_press, 2.0)
        return ret
    def on_touch_up(self, touch):
        if self._lp_ev:
            self._lp_ev.cancel()
            self._lp_ev = None
        if self._long_pressed and self.collide_point(*touch.pos):
            self._long_pressed = False
            return True
        return super().on_touch_up(touch)
    def _do_long_press(self, dt):
        self._lp_ev = None
        self._long_pressed = True
        try:
            App.get_running_app().open_faults()
        except Exception:
            pass
# =========================================================
# KV STRING
# =========================================================
KV = r"""
# BURAYA SENİN EN GÜNCEL KV BLOĞUNU BİREBİR KOY.
# Hiç değiştirme.
# Son gönderdiğin HMI layout aynen burada kalmalı.
"""


# =========================================================
# MAIN APP
# =========================================================
class RemotePiHMIApp(App):
    # Fault system
    fault_level = NumericProperty(0)
    fault_blink_on = BooleanProperty(True)
    fault_messages = ListProperty([])
    fault_text = StringProperty("Ariza Yok.")
    system_status = StringProperty("Hazir.")
    # System state
    is_system_started = BooleanProperty(False)
    is_autonom_active = BooleanProperty(False)
    active_mode = StringProperty(None, allownone=True)
    engine_sound_enabled = BooleanProperty(True)
    parking_light_on = BooleanProperty(False)
    low_beam_on = BooleanProperty(False)
    high_beam_on = BooleanProperty(False)
    signal_lhr_on = BooleanProperty(False)
    rig_floor_light_on = BooleanProperty(False)
    rotation_light_on = BooleanProperty(False)
    # Battery
    batt_m_level = NumericProperty(100)
    batt_r_level = NumericProperty(100)
    # Cooling
    mc_fan_state = StringProperty("COMM_LOST")
    rc_fan_state = StringProperty("COMM_LOST")
    # Recovery
    _recovery_in_progress = BooleanProperty(False)
    _recovery_ev = None
    # Joystick
    _left_btn_press_ts = None
    _left_btn_long_fired = False
    _right_btn_prev = False
    _left_btn_prev = False
    SAFETY_MAP = {
        "WHEEL": {"side": "LEFT", "axis": "X"},
        "DRIVER": {"side": "RIGHT", "axis": "Y"},
        "DRAWWORKS": {"side": "RIGHT", "axis": "Y"},
        "SANDLINE": {"side": "LEFT", "axis": "Y"},
        "WINCH": {"side": "LEFT", "axis": "X"},
        "ROTARY TABLE": {"side": "LEFT", "axis": "Y"},
    }
    SAFETY_DEADZONE = 5
    # -----------------------------------------------------
    # RUNTIME LOG / SINK HELPERS
    # -----------------------------------------------------
    def _runtime_status_sink(self, topic: str, payload: dict):
        try:
            print(f"[RUNTIME:{topic}] {payload}")
        except Exception:
            pass
    def _runtime_command_sink(self, command_name: str, payload: dict):
        try:
            print(f"[CMD] {command_name} -> {payload}")
            if hasattr(self, "hardware_runtime_bridge") and self.hardware_runtime_bridge is not None:
                self.hardware_runtime_bridge.execute_runtime_command(command_name, payload)
        except Exception as e:
            self.add_fault(f"Command sink hatasi: {e}", level_hint=1)
    def _runtime_event_sink(self, topic_or_event: str, payload: dict):
        try:
            print(f"[EVT] {topic_or_event} -> {payload}")
        except Exception:
            pass
    # -----------------------------------------------------
    # HARDWARE / STAGE-2 HELPERS
    # -----------------------------------------------------
    def _stage2_adc_reader(self, channel_name: str) -> float:
        if hasattr(self, "hardware_runtime_bridge") and self.hardware_runtime_bridge is not None:
            return float(self.hardware_runtime_bridge.read_adc(channel_name))
        if channel_name == "BATTERY_VOLTAGE_SENSE":
            return float(self.batt_r_level)
        if channel_name == "LM35_TEMP":
            return 28.0
        if channel_name == "NTC_BATTERY_TEMP":
            return 29.0
        return 0.0
    def _stage2_gpio_writer(self, name: str, state: bool) -> None:
        try:
            if hasattr(self, "hardware_runtime_bridge") and self.hardware_runtime_bridge is not None:
                self.hardware_runtime_bridge.write_gpio(name, state)
            if name == "REMOTE_FAN_CTRL":
                self.rc_fan_state = "ON" if state else "OFF"
            elif name == "REMOTE_BUZZER_CTRL":
                pass
        except Exception as e:
            self.add_fault(f"GPIO writer hatasi: {e}", level_hint=1)
    def _stage2_ui_fault_hook(self, payload: dict) -> None:
        try:
            self.open_faults()
        except Exception:
            pass
    def _stage2_network_status_reader(self) -> dict:
        current_screen = getattr(self.sm, "current", "home") if hasattr(self, "sm") else "home"
        return {
            "network_online": True,
            "network_weak": False,
            "master_link_ok": True,
            "adc1_online": True,
            "adc2_online": True,
            "i2c_ok": True,
            "wifi_connected": current_screen != "wifi" or True,
            "bluetooth_connected": False,
            "ethernet_link": False,
        }
    def _stage2_ui_health_reader(self) -> bool:
        return True
    def _stage2_system_active_reader(self) -> bool:
        return bool(self.is_system_started)
    # -----------------------------------------------------
    # BUILD
    # -----------------------------------------------------
    def build(self):
        self.title = "RemotePiHMI"
        Builder.load_string(KV)
        self.sm = ScreenManager()
        self.home = RootUI()
        self.cam = CameraUI()
        self.faults = FaultUI()
        self.battery_ui = BatteryUI()
        self.wifi_ui = WifiUI()
        self.bluetooth_ui = BluetoothUI()
        self.sm.add_widget(self.home)
        self.sm.add_widget(self.cam)
        self.sm.add_widget(self.faults)
        self.sm.add_widget(self.battery_ui)
        self.sm.add_widget(self.wifi_ui)
        self.sm.add_widget(self.bluetooth_ui)
        self.mqtt = MQTTManager(broker_ip="192.168.1.100")
        # ---------------------------------------------
        # HARDWARE RUNTIME BRIDGE
        # ---------------------------------------------
        self.hardware_runtime_bridge = RemotePiHardwareRuntimeBridge(
            legacy_hw=hw,
            adc_reader=None,
            gpio_writer=None,
            gpio_reader=None,
            status_sink=self._runtime_status_sink,
        )
        # ---------------------------------------------
        # STAGE-1 CORE
        # ---------------------------------------------
        self.runtime_state_store = RemotePiStateStore()
        self.runtime_event_router = RemotePiEventRouter(
            command_sink=self._runtime_command_sink,
            event_sink=self._runtime_event_sink,
            state_store=self.runtime_state_store,
            mode_fsm=None,
        )
        self.runtime_mode_fsm = RemotePiModeFSM(
            state_store=self.runtime_state_store
        )
        self.runtime_event_router.mode_fsm = self.runtime_mode_fsm
        self.runtime_lifecycle = RemotePiRuntimeLifecycle(
            state_store=self.runtime_state_store,
            mode_fsm=self.runtime_mode_fsm,
            status_sink=self._runtime_status_sink,
        )
        # ---------------------------------------------
        # HYBRID INTEGRATION MANAGER
        # ---------------------------------------------
        self.hmi_integration_manager = RemotePiHybridIntegrationManager(
            profile=build_hybrid_profile(),
            mode_fsm=self.runtime_mode_fsm,
            event_router=self.runtime_event_router,
            state_store=self.runtime_state_store,
            status_sink=self._runtime_status_sink,
        )
        RemotePiHMIPatchAdapter.bind_app(self)
        # ---------------------------------------------
        # STAGE-2 WIRING
        # ---------------------------------------------
        self.runtime_wiring_stage2 = RemotePiRuntimeWiringStage2(
            state_store=self.runtime_state_store,
            event_router=self.runtime_event_router,
            mode_fsm=self.runtime_mode_fsm,
            hmi_integration_manager=self.hmi_integration_manager,
            logger=None,
            status_sink=self._runtime_status_sink,
        )
        self.runtime_wiring_stage2.build_all(
            adc_reader=self._stage2_adc_reader,
            gpio_writer=self._stage2_gpio_writer,
            ui_fault_hook=self._stage2_ui_fault_hook,
            network_status_reader=self._stage2_network_status_reader,
            ui_health_reader=self._stage2_ui_health_reader,
            system_active_reader=self._stage2_system_active_reader,
            link_manager=None,
            command_transport=None,
            platform_shutdown_hook=None,
        )
        # ---------------------------------------------
        # SAFETY SUPERVISOR
        # ---------------------------------------------
        self.runtime_safety_supervisor = RemotePiSafetySupervisor(
            state_store=self.runtime_state_store,
            runtime_lifecycle=self.runtime_lifecycle,
            mode_fsm=self.runtime_mode_fsm,
            network_status_reader=self._stage2_network_status_reader,
            ui_health_reader=self._stage2_ui_health_reader,
            status_sink=self._runtime_status_sink,
        )
        # ---------------------------------------------
        # SNAPSHOT BUS
        # ---------------------------------------------
        self.runtime_snapshot_bus = RemotePiRuntimeSnapshotBus(
            state_store=self.runtime_state_store,
            mode_fsm=self.runtime_mode_fsm,
            runtime_lifecycle=self.runtime_lifecycle,
            safety_supervisor=self.runtime_safety_supervisor,
            watchdog_supervisor=self.runtime_wiring_stage2.watchdog_supervisor,
            hybrid_integration_manager=self.hmi_integration_manager,
            runtime_wiring_stage2=self.runtime_wiring_stage2,
        )
        # ---------------------------------------------
        # UI/Camera internals
        # ---------------------------------------------
        self._cap = None
        self._frame = None
        self._update_ev = None
        self._recording = False
        self._writer = None
        self._rec_path = None
        self._out_dir = os.path.join("assets", "captures")
        os.makedirs(self._out_dir, exist_ok=True)
        self._cam_icon = None
        self._batt_icon = None
        self._wifi_icon = None
        self._bt_icon = None
        # ---------------------------------------------
        # Initial lifecycle
        # ---------------------------------------------
        self.runtime_lifecycle.enter_ready()
        # ---------------------------------------------
        # Schedulers
        # ---------------------------------------------
        Clock.schedule_once(self._grab_home_ids, 0)
        Clock.schedule_interval(self._fault_blink_tick, 0.5)
        Clock.schedule_interval(self.update_control_loop, 0.05)
        Clock.schedule_interval(self._update_batteries, 5.0)
        Clock.schedule_interval(self._poll_joystick_buttons, 0.05)
        Clock.schedule_interval(self._emit_hmi_integration_heartbeat, 1.0)
        Clock.schedule_interval(self._stage2_runtime_tick, 0.10)
        Clock.schedule_interval(self._safety_supervisor_tick, 0.25)
        return self.sm
    # -----------------------------------------------------
    # TICKS
    # -----------------------------------------------------
    def _emit_hmi_integration_heartbeat(self, dt):
        RemotePiHMIPatchAdapter.emit_heartbeat(self)
    def _stage2_runtime_tick(self, dt):
        try:
            if self.runtime_wiring_stage2 is not None:
                self.runtime_wiring_stage2.tick()
        except Exception as e:
            self.add_fault(f"Stage-2 runtime tick hatasi: {e}", level_hint=1)
    def _safety_supervisor_tick(self, dt):
        try:
            if self.runtime_safety_supervisor is not None:
                self.runtime_safety_supervisor.tick()
            if self.runtime_lifecycle is not None:
                self.runtime_lifecycle.auto_align_from_state()
        except Exception as e:
            self.add_fault(f"Safety supervisor tick hatasi: {e}", level_hint=1)
    # -----------------------------------------------------
    # UI HELPERS
    # -----------------------------------------------------
    def _grab_home_ids(self, *_):
        try:
            self._cam_icon = self.home.ids.cam_icon
            self._batt_icon = self.home.ids.batt_icon
            self._wifi_icon = self.home.ids.wifi_icon
            self._bt_icon = self.home.ids.bt_icon
        except Exception:
            pass
    def _turn_off_left_mode_buttons(self, except_btn=None):
        panel = self.home.ids.left_panel
        for child in panel.children:
            if child == except_btn:
                continue
            if hasattr(child, "state"):
                child.state = "normal"
    def _sync_right_button_states(self):
        panel = self.home.ids.right_panel
        for child in panel.children:
            if not hasattr(child, "state"):
                continue
            txt = getattr(child, "text", "")
            if txt == "START / STOP":
                child.state = "down" if self.is_system_started else "normal"
            elif txt == "PARKING LIGHT":
                child.state = "down" if self.parking_light_on else "normal"
            elif txt == "LOW BEAM LIGHT":
                child.state = "down" if self.low_beam_on else "normal"
            elif txt == "HIGH BEAM LIGHT":
                child.state = "down" if self.high_beam_on else "normal"
            elif txt == "SIGNAL(LHR)LIGHT":
                child.state = "down" if self.signal_lhr_on else "normal"
            elif txt == "RIG FLOOR LIGHT":
                child.state = "down" if self.rig_floor_light_on else "normal"
            elif txt == "ROTATION LIGHT":
                child.state = "down" if self.rotation_light_on else "normal"
    # -----------------------------------------------------
    # FAULT SYSTEM
    # -----------------------------------------------------
    def _fault_blink_tick(self, dt):
        if self.fault_level == 2:
            self.fault_blink_on = not self.fault_blink_on
        else:
            self.fault_blink_on = True
    def set_fault_level(self, level):
        self.fault_level = max(0, min(2, int(level)))
    def add_fault(self, msg, level_hint=1):
        ts = time.strftime("%H:%M:%S")
        self.fault_messages.append(f"[{ts}] {msg}")
        self._refresh_fault_text()
        self.set_fault_level(max(self.fault_level, level_hint))
    def clear_faults(self):
        self.fault_messages = []
        self._refresh_fault_text()
    def _refresh_fault_text(self):
        self.fault_text = "\n".join(self.fault_messages) if self.fault_messages else "Ariza Yok."
    def reset_recovery(self):
        if self._recovery_in_progress:
            return
        self._recovery_in_progress = True
        self.system_status = "Kurtarma baslatildi..."
        if self._recovery_ev:
            self._recovery_ev.cancel()
        self._recovery_ev = Clock.schedule_once(self._recovery_finish, 0.2)
    def _recovery_finish(self, dt):
        self.clear_faults()
        self.set_fault_level(0)
        self.system_status = "Sistem Hazir."
        self._recovery_in_progress = False
        try:
            self.runtime_lifecycle.begin_recovery("Manual HMI recovery started.")
            self.runtime_lifecycle.finish_recovery()
        except Exception:
            pass
    def open_faults(self):
        self._refresh_fault_text()
        if hasattr(self, "hmi_mapper"):
            self.hmi_mapper.map_screen_open("faults")
        RemotePiHMIPatchAdapter.on_screen_open(self)
        self.sm.current = "faults"
    def close_faults(self):
        if hasattr(self, "hmi_mapper"):
            self.hmi_mapper.map_screen_close("faults")
        RemotePiHMIPatchAdapter.on_screen_close(self)
        self.sm.current = "home"
    def on_fault(self):
        RemotePiHMIPatchAdapter.on_fault_short(self)
        print(f"[FAULT] Current level = {self.fault_level}")
    # -----------------------------------------------------
    # COOLING STATUS
    # -----------------------------------------------------
    def update_cooling_status(self, mc_state: str, rc_state: str):
        allowed = {"ON", "OFF", "FAULT", "COMM_LOST"}
        self.mc_fan_state = mc_state if mc_state in allowed else "COMM_LOST"
        self.rc_fan_state = rc_state if rc_state in allowed else "COMM_LOST"
        RemotePiHMIPatchAdapter.sync_now(self)
    # -----------------------------------------------------
    # TOP ICONS
    # -----------------------------------------------------
    def on_top_icon(self, widget):
        RemotePiHMIPatchAdapter.on_top_icon(self, widget.icon_name)
        print(f"[TOP] {widget.icon_name}")
        if widget.icon_name == "battery":
            self.open_battery()
        elif widget.icon_name == "wifi":
            widget.state = "down"
            self.sm.current = "wifi"
            if hasattr(self, "hmi_mapper"):
                self.hmi_mapper.map_screen_open("wifi")
            RemotePiHMIPatchAdapter.on_screen_open(self)
        elif widget.icon_name == "bluetooth":
            widget.state = "down"
            self.sm.current = "bluetooth"
            if hasattr(self, "hmi_mapper"):
                self.hmi_mapper.map_screen_open("bluetooth")
            RemotePiHMIPatchAdapter.on_screen_open(self)
    def close_top_screen(self):
        current_screen = getattr(self.sm, "current", "unknown")
        if hasattr(self, "hmi_mapper") and current_screen in ("wifi", "bluetooth", "battery"):
            self.hmi_mapper.map_screen_close(current_screen)
        RemotePiHMIPatchAdapter.on_screen_close(self)
        if self._wifi_icon:
            self._wifi_icon.state = "normal"
        if self._bt_icon:
            self._bt_icon.state = "normal"
        if self._batt_icon:
            self._batt_icon.state = "normal"
        self.sm.current = "home"
    def open_battery(self):
        if hasattr(self, "hmi_mapper"):
            self.hmi_mapper.map_screen_open("battery")
        RemotePiHMIPatchAdapter.on_screen_open(self)
        if self._batt_icon:
            self._batt_icon.state = "down"
        self.sm.current = "battery"
    # -----------------------------------------------------
    # CAMERA
    # -----------------------------------------------------
    def open_camera(self):
        if hasattr(self, "hmi_mapper"):
            self.hmi_mapper.map_camera_open()
            self.hmi_mapper.map_screen_open("camera")
        RemotePiHMIPatchAdapter.on_screen_open(self)
        if self._cam_icon:
            self._cam_icon.state = "down"
        self.sm.current = "camera"
        self.start_camera()
    def close_camera(self):
        if hasattr(self, "hmi_mapper"):
            self.hmi_mapper.map_camera_close()
            self.hmi_mapper.map_screen_close("camera")
        RemotePiHMIPatchAdapter.on_screen_close(self)
        self.stop_record(force=True)
        self.stop_camera()
        if self._cam_icon:
            self._cam_icon.state = "normal"
        self.sm.current = "home"
    def start_camera(self):
        if cv2 is None or self._cap is not None:
            return
        self._cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
        self._cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc("M", "J", "P", "G"))
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        if not self._cap.isOpened():
            self._cap = None
            self.add_fault("Kamera acilamadi.", level_hint=1)
            return
        self._update_ev = Clock.schedule_interval(self._update_frame, 1.0 / 30.0)
    def stop_camera(self):
        if self._update_ev:
            self._update_ev.cancel()
            self._update_ev = None
        if self._cap:
            self._cap.release()
            self._cap = None
        self._frame = None
    def _update_frame(self, dt):
        if not self._cap:
            return
        ret, frame = self._cap.read()
        if not ret:
            return
        self._frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        buf = self._frame.tobytes()
        tex = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt="rgb")
        tex.blit_buffer(buf, colorfmt="rgb", bufferfmt="ubyte")
        tex.flip_vertical()
        if self.cam.ids.cam_view:
            self.cam.ids.cam_view.texture = tex
        if self._recording and self._writer:
            self._writer.write(cv2.cvtColor(self._frame, cv2.COLOR_RGB2BGR))
    def take_photo(self):
        if self._frame is None or cv2 is None:
            return
        ts = time.strftime("%Y%m%d_%H%M%S")
        path = os.path.join(self._out_dir, f"photo_{ts}.jpg")
        cv2.imwrite(path, cv2.cvtColor(self._frame, cv2.COLOR_RGB2BGR))
        print(f"[CAM] Photo saved: {path}")
    def toggle_record(self):
        if self._recording:
            self.stop_record()
        else:
            self.start_record()
    def start_record(self):
        if not self._cap or cv2 is None:
            return
        ts = time.strftime("%Y%m%d_%H%M%S")
        self._rec_path = os.path.join(self._out_dir, f"vid_{ts}.mp4")
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        self._writer = cv2.VideoWriter(self._rec_path, fourcc, 20.0, (640, 480))
        self._recording = True
        self.cam.recording = True
        print(f"[CAM] Recording started: {self._rec_path}")
    def stop_record(self, force=False):
        if self._recording or force:
            self._recording = False
            self.cam.recording = False
            if self._writer:
                self._writer.release()
                self._writer = None
            print("[CAM] Recording stopped")
    # -----------------------------------------------------
    # BATTERY
    # -----------------------------------------------------
    def _update_batteries(self, dt):
        if self.batt_m_level > 10:
            self.batt_m_level -= 1
        if self.batt_r_level > 5:
            self.batt_r_level -= random.randint(1, 3)
        RemotePiHMIPatchAdapter.sync_now(self)
    # -----------------------------------------------------
    # JOYSTICK BUTTONS
    # -----------------------------------------------------
    def _poll_joystick_buttons(self, dt):
        try:
            if self.hardware_runtime_bridge is not None:
                left_now = self.hardware_runtime_bridge.read_left_button()
                right_now = self.hardware_runtime_bridge.read_right_button()
            else:
                left_now = hw.read_left_joystick_button()
                right_now = hw.read_right_joystick_button()
            # Right joystick short press -> engine sound / engine buzzer principle korunur
            if right_now and not self._right_btn_prev:
                self.engine_sound_enabled = not self.engine_sound_enabled
                RemotePiHMIPatchAdapter.on_right_joystick_short(
                    self,
                    self.engine_sound_enabled,
                )
                state_text = "ACIK" if self.engine_sound_enabled else "KAPALI"
                print(f"[JOY-R BTN] Engine sound -> {state_text}")
            if left_now and not self._left_btn_prev:
                self._left_btn_press_ts = time.time()
                self._left_btn_long_fired = False
            if left_now and self._left_btn_press_ts is not None and not self._left_btn_long_fired:
                if (time.time() - self._left_btn_press_ts) >= 2.0:
                    self._left_btn_long_fired = True
                    RemotePiHMIPatchAdapter.on_left_joystick_long(self)
                    RemotePiHMIPatchAdapter.on_fault_long(self)
                    print("[JOY-L BTN] Long press detected")
                    self.open_faults()
            if not left_now:
                self._left_btn_press_ts = None
                self._left_btn_long_fired = False
            self._left_btn_prev = left_now
            self._right_btn_prev = right_now
        except Exception as e:
            self.add_fault(f"Joystick buton okuma hatasi: {e}", level_hint=1)
    # -----------------------------------------------------
    # LEGACY CONTROL LOOP
    # -----------------------------------------------------
    def update_control_loop(self, dt):
        mode = self.active_mode
        val = 0
        if self.is_system_started and not self.is_autonom_active and mode:
            if mode == "WHEEL":
                val = hw.read_joystick("LEFT", "X")
                hw.set_servo(val)
            elif mode == "DRIVER":
                val = hw.read_joystick("RIGHT", "Y")
                hw.set_motor_driver(val, engine_sound_enabled=self.engine_sound_enabled)
            elif mode == "DRAWWORKS":
                val = hw.read_joystick("RIGHT", "Y")
                hw.set_drawworks_motor(val, engine_sound_enabled=self.engine_sound_enabled)
            elif mode == "SANDLINE":
                val = hw.read_joystick("LEFT", "Y")
                hw.set_sandline_motor(val, engine_sound_enabled=self.engine_sound_enabled)
            elif mode == "WINCH":
                val = hw.read_joystick("LEFT", "X")
                hw.set_winch_motor(val, engine_sound_enabled=self.engine_sound_enabled)
            elif mode == "ROTARY TABLE":
                val = hw.read_joystick("LEFT", "Y")
                hw.set_rotary_motor(val, engine_sound_enabled=self.engine_sound_enabled)
        payload = {
            "ts": time.time(),
            "active": self.is_system_started,
            "autonom": self.is_autonom_active,
            "mode": mode,
            "val": val,
            "engine_sound": self.engine_sound_enabled,
            "parking_light": self.parking_light_on,
            "low_beam": self.low_beam_on,
            "high_beam": self.high_beam_on,
            "signal_lhr": self.signal_lhr_on,
            "rig_floor_light": self.rig_floor_light_on,
            "rotation_light": self.rotation_light_on,
        }
        self.mqtt.publish_control(payload)
    # -----------------------------------------------------
    # BUTTON ACTIONS
    # -----------------------------------------------------
    def on_btn(self, btn_instance, name):
        try:
            RemotePiHMIPatchAdapter.on_button(self, btn_instance, name)
            if name == "START_STOP":
                if btn_instance.state == "down":
                    self.is_system_started = True
                    self.system_status = "Sistem Baslatildi."
                    print("[SYSTEM] STARTED")
                    try:
                        self.runtime_lifecycle.start_runtime()
                    except Exception:
                        pass
                else:
                    self.shutdown_system()
                self._sync_right_button_states()
                RemotePiHMIPatchAdapter.sync_now(self)
                return
            if not self.is_system_started:
                if btn_instance.state == "down":
                    btn_instance.state = "normal"
                    print(f"[BLOCK] Sistem kapali. {name} engellendi.")
                return
            if name == "PARKING LIGHT":
                self.parking_light_on = (btn_instance.state == "down")
                hw.set_parking_light(self.parking_light_on)
                print(f"[LIGHT] PARKING LIGHT -> {self.parking_light_on}")
                RemotePiHMIPatchAdapter.sync_now(self)
                return
            if name == "LOW BEAM LIGHT":
                self.low_beam_on = (btn_instance.state == "down")
                hw.set_low_beam_light(self.low_beam_on)
                print(f"[LIGHT] LOW BEAM LIGHT -> {self.low_beam_on}")
                RemotePiHMIPatchAdapter.sync_now(self)
                return
            if name == "HIGH BEAM LIGHT":
                self.high_beam_on = (btn_instance.state == "down")
                hw.set_high_beam_light(self.high_beam_on)
                print(f"[LIGHT] HIGH BEAM LIGHT -> {self.high_beam_on}")
                RemotePiHMIPatchAdapter.sync_now(self)
                return
            if name == "SIGNAL(LHR)LIGHT":
                self.signal_lhr_on = (btn_instance.state == "down")
                hw.set_signal_mode(self.signal_lhr_on)
                print(f"[LIGHT] SIGNAL(LHR)LIGHT -> {self.signal_lhr_on}")
                RemotePiHMIPatchAdapter.sync_now(self)
                return
            if name == "RIG FLOOR LIGHT":
                self.rig_floor_light_on = (btn_instance.state == "down")
                hw.set_rig_floor_light(self.rig_floor_light_on)
                print(f"[LIGHT] RIG FLOOR LIGHT -> {self.rig_floor_light_on}")
                RemotePiHMIPatchAdapter.sync_now(self)
                return
            if name == "ROTATION LIGHT":
                self.rotation_light_on = (btn_instance.state == "down")
                hw.set_rotation_light(self.rotation_light_on)
                print(f"[LIGHT] ROTATION LIGHT -> {self.rotation_light_on}")
                RemotePiHMIPatchAdapter.sync_now(self)
                return
            if name == "AUTONOM":
                if btn_instance.state == "down":
                    self.is_autonom_active = True
                    self.active_mode = "AUTONOM"
                    self.system_status = "Otonom mod aktif."
                    self._turn_off_left_mode_buttons(except_btn=btn_instance)
                    print("[AUTONOM] ACTIVE")
                else:
                    self.is_autonom_active = False
                    self.active_mode = None
                    self.system_status = "Otonom mod pasif."
                    print("[AUTONOM] PASSIVE")
                RemotePiHMIPatchAdapter.sync_now(self)
                return
            if self.is_autonom_active:
                if btn_instance.state == "down":
                    btn_instance.state = "normal"
                    print(f"[BLOCK] Otonom aktif. {name} engellendi.")
                return
            if name == "MENU":
                if btn_instance.state == "down":
                    print("[MENU] Su an gorev tanimli degil.")
                else:
                    print("[MENU] kapandi.")
                RemotePiHMIPatchAdapter.sync_now(self)
                return
            if btn_instance.state == "down":
                safety_rule = self.SAFETY_MAP.get(name)
                if safety_rule:
                    current_val = hw.read_joystick(safety_rule["side"], safety_rule["axis"])
                    if abs(current_val) > self.SAFETY_DEADZONE:
                        btn_instance.state = "normal"
                        self.add_fault(
                            f"GUVENLIK: {name} reddedildi! Joy 0 degil ({current_val}%)",
                            level_hint=1
                        )
                        print(f"[SAFETY] {name} rejected, joystick not zero")
                        RemotePiHMIPatchAdapter.sync_now(self)
                        return
                self.active_mode = name
                self.system_status = f"{name} aktif."
                self._turn_off_left_mode_buttons(except_btn=btn_instance)
                print(f"[MODE] {name} ACTIVE")
            else:
                if self.active_mode == name:
                    self.active_mode = None
                    hw.stop_engine_buzzer()
                    self.system_status = "Hazir."
                    print(f"[MODE] {name} PASSIVE")
            RemotePiHMIPatchAdapter.sync_now(self)
        except Exception as e:
            print(f"[ERROR] {e}")
            self.add_fault(f"Yazilim Hatasi: {e}", level_hint=2)
            RemotePiHMIPatchAdapter.sync_now(self)
    # -----------------------------------------------------
    # SYSTEM SHUTDOWN
    # -----------------------------------------------------
    def shutdown_system(self):
        self.is_system_started = False
        self.is_autonom_active = False
        self.active_mode = None
        self.system_status = "Sistem Durduruldu."
        self.parking_light_on = False
        self.low_beam_on = False
        self.high_beam_on = False
        self.signal_lhr_on = False
        self.rig_floor_light_on = False
        self.rotation_light_on = False
        hw.set_signal_mode(False)
        hw.set_parking_light(False)
        hw.set_low_beam_light(False)
        hw.set_high_beam_light(False)
        hw.set_rig_floor_light(False)
        hw.set_rotation_light(False)
        hw.stop_all_outputs()
        self._turn_off_left_mode_buttons(except_btn=None)
        self._sync_right_button_states()
        print("[SYSTEM] STOPPED")
        try:
            self.runtime_lifecycle.request_shutdown("HMI shutdown_system called.")
        except Exception:
            pass
        RemotePiHMIPatchAdapter.sync_now(self)
    # -----------------------------------------------------
    # OPTIONAL DEBUG EXPORT
    # -----------------------------------------------------
    def build_runtime_snapshot(self) -> dict:
        try:
            return self.runtime_snapshot_bus.build_service_snapshot()
        except Exception as e:
            return {"error": str(e)}
if __name__ == "__main__":
    RemotePiHMIApp().run()


# ============================================================
# FAZ-2 PATCH SET — (entegre edildi, ayrı çalıştırılmaz)
# ============================================================
# --- yeni method ---
def _emit_hmi_mapper_heartbeat(self, dt):
    if hasattr(self, "hmi_mapper"):
        self.hmi_mapper.emit_snapshot_heartbeat(self)
# --- open_faults / close_faults ---
def open_faults(self):
    self._refresh_fault_text()
    if hasattr(self, "hmi_mapper"):
        self.hmi_mapper.map_screen_open("faults")
    self.sm.current = "faults"
def close_faults(self):
    if hasattr(self, "hmi_mapper"):
        self.hmi_mapper.map_screen_close("faults")
    self.sm.current = "home"
# --- open_battery ---
def open_battery(self):
    if hasattr(self, "hmi_mapper"):
        self.hmi_mapper.map_screen_open("battery")
    if self._batt_icon:
        self._batt_icon.state = "down"
    self.sm.current = "battery"
# --- close_top_screen ---
def close_top_screen(self):
    current_screen = getattr(self.sm, "current", "unknown")
    if hasattr(self, "hmi_mapper") and current_screen in ("wifi", "bluetooth", "battery"):
        self.hmi_mapper.map_screen_close(current_screen)
    if self._wifi_icon:
        self._wifi_icon.state = "normal"
    if self._bt_icon:
        self._bt_icon.state = "normal"
    if self._batt_icon:
        self._batt_icon.state = "normal"
    self.sm.current = "home"
# --- open_camera / close_camera ---
def open_camera(self):
    if hasattr(self, "hmi_mapper"):
        self.hmi_mapper.map_camera_open()
        self.hmi_mapper.map_screen_open("camera")
    if self._cam_icon:
        self._cam_icon.state = "down"
    self.sm.current = "camera"
    self.start_camera()
def close_camera(self):
    if hasattr(self, "hmi_mapper"):
        self.hmi_mapper.map_camera_close()
        self.hmi_mapper.map_screen_close("camera")
    self.stop_record(force=True)
    self.stop_camera()
    if self._cam_icon:
        self._cam_icon.state = "normal"
    self.sm.current = "home"