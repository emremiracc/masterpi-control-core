# -*- coding: utf-8 -*-
"""
MODULE-156 (FINAL - Unified)
integration/masterpi_hardware_runtime_stack.py

Final integrated hardware runtime stack for MasterPi.
Birleştirilmiş tek modül — Modül 1..87 + MODULE-88..164 tüm tasarım iterasyonları.

Revision focus (MODULE-156):
- RuntimeConfig integration
- TelemetryLogger integration
- StartupShutdownSequence integration
- FSM integration
- board-aware runtime construction
- CommandSchema validation/normalization integration
- SafetyInterlock integration
- RemoteLinkWatchdog integration
- explicit SSOT-backed runtime initialization
- granular error event emission
- centralized event constants usage
"""

from __future__ import annotations

import json
import math
import os
import threading
import time
from dataclasses import dataclass, field, asdict, fields, is_dataclass
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

# =========================================================
# OPTIONAL HARDWARE IMPORT
# =========================================================
try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    _GPIO_AVAILABLE = True
except Exception:
    GPIO = None
    _GPIO_AVAILABLE = False

try:
    import paho.mqtt.client as mqtt
    _MQTT_AVAILABLE = True
except Exception:
    mqtt = None
    _MQTT_AVAILABLE = False

# =========================================================
# CORE — EVENT NAMES  (MODULE-123)
# =========================================================
EVENT_RUNTIME_HEARTBEAT       = "runtime.heartbeat"
EVENT_SYSTEM_STARTED          = "system.started"
EVENT_SYSTEM_STOPPED          = "system.stopped"
EVENT_MODE_CHANGED            = "system.mode_changed"
EVENT_AUTONOM_ACTIVATED       = "system.autonom_activated"
EVENT_AUTONOM_DEACTIVATED     = "system.autonom_deactivated"
EVENT_FAULT_RAISED             = "fault.raised"
EVENT_FAULT_CLEARED            = "fault.cleared"
EVENT_SAFETY_BLOCKED           = "safety.blocked"
EVENT_REMOTE_LINK_UP           = "remote_link.up"
EVENT_REMOTE_LINK_DOWN         = "remote_link.down"
EVENT_MOTOR_COMMAND            = "motor.command"
EVENT_LIGHT_COMMAND            = "light.command"
EVENT_ALARM_COMMAND            = "alarm.command"
EVENT_COOLING_STATUS_UPDATE    = "cooling.status_update"
EVENT_ADC_READING              = "adc.reading"
EVENT_TELEMETRY_SNAPSHOT       = "telemetry.snapshot"

# =========================================================
# CORE — FAULT CODES  (MODULE-121)
# =========================================================
FAULT_CODE_MOTOR_EMERGENCY_STOP   = "FAULT_MOTOR_EMERGENCY_STOP"
FAULT_CODE_SAFETY_INTERLOCK       = "FAULT_SAFETY_INTERLOCK"
FAULT_CODE_REMOTE_LINK_LOST       = "FAULT_REMOTE_LINK_LOST"
FAULT_CODE_GPIO_INIT_FAILED       = "FAULT_GPIO_INIT_FAILED"
FAULT_CODE_ADC_READ_ERROR         = "FAULT_ADC_READ_ERROR"
FAULT_CODE_COOLING_FAULT          = "FAULT_COOLING_FAULT"
FAULT_CODE_COMMAND_INVALID        = "FAULT_COMMAND_INVALID"
FAULT_CODE_WATCHDOG_TIMEOUT       = "FAULT_WATCHDOG_TIMEOUT"
FAULT_CODE_STARTUP_FAILED         = "FAULT_STARTUP_FAILED"
FAULT_CODE_SHUTDOWN_FAILED        = "FAULT_SHUTDOWN_FAILED"
FAULT_CODE_SOFTWARE_ERROR         = "FAULT_SOFTWARE_ERROR"

# =========================================================
# CORE — COMMAND SCHEMA  (MODULE-138)
# =========================================================
COMMAND_TYPE_MOTOR   = "motor"
COMMAND_TYPE_LIGHT   = "light"
COMMAND_TYPE_ALARM   = "alarm"
COMMAND_TYPE_COOLING = "cooling"
COMMAND_TYPE_SYSTEM  = "system"

VALID_MODES = {
    "WHEEL", "DRIVER", "DRAWWORKS", "SANDLINE",
    "WINCH", "ROTARY TABLE", "AUTONOM", None
}

VALID_LIGHT_KEYS = {
    "parking_light", "low_beam", "high_beam",
    "signal_lhr", "rig_floor_light", "rotation_light"
}

VALID_COOLING_STATES = {"ON", "OFF", "FAULT", "COMM_LOST"}


@dataclass
class CommandPayload:
    """Normalized, validated command payload — single source of truth."""
    ts: float = 0.0
    active: bool = False
    autonom: bool = False
    mode: Optional[str] = None
    val: float = 0.0
    engine_sound: bool = True
    parking_light: bool = False
    low_beam: bool = False
    high_beam: bool = False
    signal_lhr: bool = False
    rig_floor_light: bool = False
    rotation_light: bool = False

    @staticmethod
    def from_dict(raw: Dict[str, Any]) -> "CommandPayload":
        """Validate and normalize an incoming raw command dict."""
        if not isinstance(raw, dict):
            raise ValueError("CommandPayload: raw must be a dict")
        c = CommandPayload()
        c.ts            = float(raw.get("ts", time.time()))
        c.active        = bool(raw.get("active", False))
        c.autonom       = bool(raw.get("autonom", False))
        mode            = raw.get("mode", None)
        c.mode          = mode if mode in VALID_MODES else None
        c.val           = max(-100.0, min(100.0, float(raw.get("val", 0.0))))
        c.engine_sound  = bool(raw.get("engine_sound", True))
        c.parking_light   = bool(raw.get("parking_light", False))
        c.low_beam        = bool(raw.get("low_beam", False))
        c.high_beam       = bool(raw.get("high_beam", False))
        c.signal_lhr      = bool(raw.get("signal_lhr", False))
        c.rig_floor_light = bool(raw.get("rig_floor_light", False))
        c.rotation_light  = bool(raw.get("rotation_light", False))
        return c

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# =========================================================
# CORE — RUNTIME CONFIG  (MODULE-155)
# =========================================================
@dataclass
class LoopIntervalsConfig:
    control_loop_hz: float = 20.0       # Hz
    adc_poll_hz: float     = 5.0
    telemetry_hz: float    = 1.0
    watchdog_hz: float     = 2.0

    @property
    def control_interval(self) -> float:
        return 1.0 / max(1.0, self.control_loop_hz)

    @property
    def adc_interval(self) -> float:
        return 1.0 / max(1.0, self.adc_poll_hz)

    @property
    def telemetry_interval(self) -> float:
        return 1.0 / max(0.1, self.telemetry_hz)


@dataclass
class SafetyConfig:
    watchdog_timeout_s: float = 2.0
    motor_deadzone_pct: float = 5.0
    max_motor_speed_pct: float = 100.0
    emergency_stop_on_link_loss: bool = True


@dataclass
class HardwareConfig:
    board: str = "rpi4"          # rpi4 | rpi3 | sim
    mqtt_broker_ip: str = "192.168.1.100"
    mqtt_broker_port: int = 1883
    mqtt_topic_control: str = "remotepi/control"
    mqtt_topic_status: str  = "masterpi/status"
    telemetry_log_dir: str = "logs"
    telemetry_max_files: int = 10


@dataclass
class RuntimeConfig:
    loops: LoopIntervalsConfig = field(default_factory=LoopIntervalsConfig)
    safety: SafetyConfig = field(default_factory=SafetyConfig)
    hardware: HardwareConfig = field(default_factory=HardwareConfig)

    @staticmethod
    def from_dict(overrides: Dict[str, Any]) -> "RuntimeConfig":
        cfg = RuntimeConfig()
        if "loops" in overrides:
            for k, v in overrides["loops"].items():
                if hasattr(cfg.loops, k):
                    setattr(cfg.loops, k, v)
        if "safety" in overrides:
            for k, v in overrides["safety"].items():
                if hasattr(cfg.safety, k):
                    setattr(cfg.safety, k, v)
        if "hardware" in overrides:
            for k, v in overrides["hardware"].items():
                if hasattr(cfg.hardware, k):
                    setattr(cfg.hardware, k, v)
        return cfg

    def to_dict(self) -> Dict[str, Any]:
        return {
            "loops":    asdict(self.loops),
            "safety":   asdict(self.safety),
            "hardware": asdict(self.hardware),
        }


# =========================================================
# CORE — RUNTIME CONFIG LOADER  (MODULE-160)
# =========================================================
class RuntimeConfigLoader:
    DEFAULT_PATH = "masterpi_config.json"

    @staticmethod
    def load(path: Optional[str] = None) -> RuntimeConfig:
        p = path or RuntimeConfigLoader.DEFAULT_PATH
        if os.path.exists(p):
            try:
                with open(p, "r") as f:
                    overrides = json.load(f)
                return RuntimeConfig.from_dict(overrides)
            except Exception as e:
                print(f"[ConfigLoader] Failed to load {p}: {e}, using defaults")
        return RuntimeConfig()

    @staticmethod
    def save(cfg: RuntimeConfig, path: Optional[str] = None) -> None:
        p = path or RuntimeConfigLoader.DEFAULT_PATH
        try:
            with open(p, "w") as f:
                json.dump(cfg.to_dict(), f, indent=2)
        except Exception as e:
            print(f"[ConfigLoader] Failed to save: {e}")


# =========================================================
# CORE — EVENT BUS  (MODULE-117)
# =========================================================
class EventBus:
    """Lightweight, thread-safe pub/sub event bus."""

    def __init__(self):
        self._listeners: Dict[str, List[Callable]] = {}
        self._lock = threading.Lock()

    def subscribe(self, event_name: str, callback: Callable) -> None:
        with self._lock:
            self._listeners.setdefault(event_name, []).append(callback)

    def unsubscribe(self, event_name: str, callback: Callable) -> None:
        with self._lock:
            listeners = self._listeners.get(event_name, [])
            if callback in listeners:
                listeners.remove(callback)

    def emit(self, event_name: str, payload: Any = None) -> None:
        with self._lock:
            callbacks = list(self._listeners.get(event_name, []))
        for cb in callbacks:
            try:
                cb(event_name, payload)
            except Exception as e:
                print(f"[EventBus] Error in listener for '{event_name}': {e}")

    def emit_error(self, fault_code: str, message: str, level: int = 1) -> None:
        self.emit(EVENT_FAULT_RAISED, {
            "fault_code": fault_code,
            "message": message,
            "level": level,
            "ts": time.time(),
        })


# =========================================================
# CORE — SYSTEM STATE  (MODULE-118)
# =========================================================
@dataclass
class SystemState:
    """Single source of truth for runtime system state."""
    is_started: bool = False
    is_autonom: bool = False
    active_mode: Optional[str] = None
    engine_sound_enabled: bool = True
    parking_light: bool = False
    low_beam: bool = False
    high_beam: bool = False
    signal_lhr: bool = False
    rig_floor_light: bool = False
    rotation_light: bool = False
    mc_fan_state: str = "COMM_LOST"
    rc_fan_state: str = "COMM_LOST"
    batt_master_pct: float = 100.0
    batt_remote_pct: float = 100.0
    fault_level: int = 0
    remote_link_alive: bool = False
    last_command_ts: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# =========================================================
# CORE — FSM  (MODULE-135)
# =========================================================
FSM_STATE_IDLE      = "IDLE"
FSM_STATE_RUNNING   = "RUNNING"
FSM_STATE_AUTONOM   = "AUTONOM"
FSM_STATE_FAULT     = "FAULT"
FSM_STATE_SHUTDOWN  = "SHUTDOWN"

FSM_TRANSITIONS: Dict[str, Set[str]] = {
    FSM_STATE_IDLE:     {FSM_STATE_RUNNING, FSM_STATE_SHUTDOWN},
    FSM_STATE_RUNNING:  {FSM_STATE_IDLE, FSM_STATE_AUTONOM, FSM_STATE_FAULT, FSM_STATE_SHUTDOWN},
    FSM_STATE_AUTONOM:  {FSM_STATE_RUNNING, FSM_STATE_FAULT, FSM_STATE_SHUTDOWN},
    FSM_STATE_FAULT:    {FSM_STATE_IDLE, FSM_STATE_SHUTDOWN},
    FSM_STATE_SHUTDOWN: set(),
}


class MasterPiFSM:
    """Finite State Machine for MasterPi runtime lifecycle."""

    def __init__(self, bus: EventBus):
        self._state = FSM_STATE_IDLE
        self._lock  = threading.Lock()
        self._bus   = bus
        self._entered_at = time.time()

    @property
    def state(self) -> str:
        return self._state

    def transition(self, target: str) -> bool:
        with self._lock:
            allowed = FSM_TRANSITIONS.get(self._state, set())
            if target not in allowed:
                print(f"[FSM] Illegal transition {self._state} → {target}")
                return False
            prev = self._state
            self._state = target
            self._entered_at = time.time()
        self._bus.emit(EVENT_MODE_CHANGED, {"from": prev, "to": target, "ts": time.time()})
        print(f"[FSM] {prev} → {target}")
        return True

    def is_operational(self) -> bool:
        return self._state in (FSM_STATE_RUNNING, FSM_STATE_AUTONOM)

    def time_in_state(self) -> float:
        return time.time() - self._entered_at


# =========================================================
# CORE — SAFETY INTERLOCK  (MODULE-140)
# =========================================================
@dataclass
class InterlockDecision:
    allowed: bool
    reason: Optional[str] = None
    fault_code: Optional[str] = None


class SafetyInterlock:
    """Central command permission policy for MasterPi."""

    MOTOR_MODES = {"WHEEL", "DRIVER", "DRAWWORKS", "SANDLINE", "WINCH", "ROTARY TABLE"}

    def __init__(self, cfg: SafetyConfig, fsm: MasterPiFSM, bus: EventBus):
        self._cfg = cfg
        self._fsm = fsm
        self._bus = bus

    def check_command(self, cmd: CommandPayload, state: SystemState) -> InterlockDecision:
        # System not started
        if not cmd.active:
            return InterlockDecision(allowed=True)

        # FSM must be operational
        if not self._fsm.is_operational():
            return InterlockDecision(
                allowed=False,
                reason=f"FSM not operational: {self._fsm.state}",
                fault_code=FAULT_CODE_SAFETY_INTERLOCK,
            )

        # Remote link must be alive for motor commands
        if cmd.mode in self.MOTOR_MODES and not state.remote_link_alive:
            return InterlockDecision(
                allowed=False,
                reason="Remote link not alive",
                fault_code=FAULT_CODE_REMOTE_LINK_LOST,
            )

        # Motor value within bounds
        if cmd.mode in self.MOTOR_MODES:
            if abs(cmd.val) > self._cfg.max_motor_speed_pct:
                return InterlockDecision(
                    allowed=False,
                    reason=f"Motor val {cmd.val} exceeds max {self._cfg.max_motor_speed_pct}",
                    fault_code=FAULT_CODE_SAFETY_INTERLOCK,
                )

        return InterlockDecision(allowed=True)

    def emergency_stop_required(self, state: SystemState) -> bool:
        if not state.remote_link_alive and self._cfg.emergency_stop_on_link_loss:
            return True
        if state.fault_level >= 2:
            return True
        return False


# =========================================================
# CORE — REMOTE LINK WATCHDOG  (MODULE-142)
# =========================================================
class RemoteLinkWatchdog:
    """Tracks remote heartbeat freshness and link health."""

    def __init__(self, timeout_s: float, bus: EventBus):
        self._timeout   = timeout_s
        self._bus       = bus
        self._last_beat = 0.0
        self._alive     = False
        self._lock      = threading.Lock()

    def heartbeat(self, ts: Optional[float] = None) -> None:
        with self._lock:
            self._last_beat = ts or time.time()
            was_alive = self._alive
            self._alive = True
        if not was_alive:
            self._bus.emit(EVENT_REMOTE_LINK_UP, {"ts": self._last_beat})
            print("[Watchdog] Remote link UP")

    def check(self) -> bool:
        with self._lock:
            elapsed = time.time() - self._last_beat
            was_alive = self._alive
            alive = self._last_beat > 0 and elapsed < self._timeout
            self._alive = alive
        if was_alive and not alive:
            self._bus.emit(EVENT_REMOTE_LINK_DOWN, {"elapsed": elapsed})
            self._bus.emit_error(FAULT_CODE_REMOTE_LINK_LOST,
                                 f"Remote link lost after {elapsed:.1f}s", level=2)
            print(f"[Watchdog] Remote link DOWN (timeout {elapsed:.1f}s)")
        return alive

    @property
    def is_alive(self) -> bool:
        return self._alive


# =========================================================
# CORE — TELEMETRY LOGGER  (MODULE-153)
# =========================================================
class TelemetryLogger:
    """Persistent JSONL logger for runtime events and snapshots."""

    def __init__(self, log_dir: str = "logs", max_files: int = 10):
        self._log_dir   = log_dir
        self._max_files = max_files
        self._lock      = threading.Lock()
        self._event_fh  = None
        self._snap_fh   = None
        self._open_logs()

    def _open_logs(self) -> None:
        try:
            os.makedirs(self._log_dir, exist_ok=True)
            ts = time.strftime("%Y%m%d_%H%M%S")
            self._event_fh = open(os.path.join(self._log_dir, f"events_{ts}.jsonl"), "a")
            self._snap_fh  = open(os.path.join(self._log_dir, f"snapshots_{ts}.jsonl"), "a")
            self._rotate_old_logs()
        except Exception as e:
            print(f"[Telemetry] Log open failed: {e}")

    def _rotate_old_logs(self) -> None:
        try:
            for prefix in ("events_", "snapshots_"):
                files = sorted([
                    f for f in os.listdir(self._log_dir)
                    if f.startswith(prefix) and f.endswith(".jsonl")
                ])
                while len(files) > self._max_files:
                    os.remove(os.path.join(self._log_dir, files.pop(0)))
        except Exception:
            pass

    def log_event(self, event_name: str, payload: Any) -> None:
        with self._lock:
            if self._event_fh:
                try:
                    self._event_fh.write(json.dumps({
                        "ts": time.time(), "event": event_name, "payload": payload
                    }) + "\n")
                    self._event_fh.flush()
                except Exception:
                    pass

    def log_snapshot(self, snapshot: Dict[str, Any]) -> None:
        with self._lock:
            if self._snap_fh:
                try:
                    self._snap_fh.write(json.dumps(snapshot) + "\n")
                    self._snap_fh.flush()
                except Exception:
                    pass

    def close(self) -> None:
        with self._lock:
            for fh in (self._event_fh, self._snap_fh):
                try:
                    if fh:
                        fh.close()
                except Exception:
                    pass
            self._event_fh = None
            self._snap_fh  = None


# =========================================================
# CORE — STARTUP / SHUTDOWN SEQUENCE  (MODULE-151)
# =========================================================
@dataclass
class SequenceStep:
    name: str
    fn: Callable
    critical: bool = True


@dataclass
class SequenceReport:
    success: bool
    steps_ok: List[str] = field(default_factory=list)
    steps_failed: List[str] = field(default_factory=list)
    elapsed_s: float = 0.0


class StartupShutdownSequence:
    """Ordered startup / shutdown step orchestration."""

    def __init__(self):
        self._startup_steps:  List[SequenceStep] = []
        self._shutdown_steps: List[SequenceStep] = []

    def add_startup_step(self, name: str, fn: Callable, critical: bool = True) -> None:
        self._startup_steps.append(SequenceStep(name, fn, critical))

    def add_shutdown_step(self, name: str, fn: Callable, critical: bool = False) -> None:
        self._shutdown_steps.append(SequenceStep(name, fn, critical))

    def run_startup(self) -> SequenceReport:
        return self._run(self._startup_steps, "STARTUP")

    def run_shutdown(self) -> SequenceReport:
        return self._run(self._shutdown_steps, "SHUTDOWN")

    def _run(self, steps: List[SequenceStep], label: str) -> SequenceReport:
        t0 = time.time()
        ok, failed = [], []
        for step in steps:
            try:
                step.fn()
                ok.append(step.name)
                print(f"[{label}] ✓ {step.name}")
            except Exception as e:
                failed.append(step.name)
                print(f"[{label}] ✗ {step.name}: {e}")
                if step.critical:
                    print(f"[{label}] Critical step failed — aborting")
                    return SequenceReport(
                        success=False, steps_ok=ok, steps_failed=failed,
                        elapsed_s=time.time() - t0
                    )
        return SequenceReport(
            success=True, steps_ok=ok, steps_failed=failed,
            elapsed_s=time.time() - t0
        )


# =========================================================
# HARDWARE — GPIO BINDING MAP  (MODULE-128)
# SSOT: MasterPi_v3_12_6_SYNCED_en_guncel.xlsx — GPIO_MASTER_MAP + Connections
# =========================================================
@dataclass
class GPIOPin:
    pin_bcm: int   # BCM numarası
    label: str
    group: str     # alarm | cooling | light_gpio | i2c
    mode: str      # OUT | PWM | I2C


class GPIOMap:
    """
    MasterPi GPIO SSOT — sadece doğrudan GPIO'ya bağlı pinler.
    Motor, servo ve LED gruplarının büyük çoğunluğu PCA9685 I2C üzerinden
    sürülür; bu tabloda yer almaz.

    GPIO_MASTER_MAP (xlsx) referansı:
      GPIO25  Pin22  → MASTER_FAN_CTRL  (12V fan, low-side MOSFET)
      GPIO20  Pin38  → BUZZER#1 Reverse Warning
      GPIO26  Pin37  → REVERSE_LAMP (12V, MOSFET)
      GPIO18  Pin12  → BUZZER#2 Engine Sound (PWM0, KY-006)
      GPIO13  Pin33  → RIG_FLOOR_LIGHT (9–12V, MOSFET)
      GPIO16  Pin36  → SIGNAL_LIGHT_RIGHT (Sarı LED Sağ)
      GPIO21  Pin40  → SIGNAL_LIGHT_LEFT  (Sarı LED Sol)
      GPIO2/3        → I2C (PCA9685 + ADS1115#1 + ADS1115#2)
    """

    PINS: List[GPIOPin] = [
        # Cooling — MC fan (12V, low-side MOSFET)
        GPIOPin(pin_bcm=25, label="MASTER_FAN_CTRL",    group="cooling",    mode="PWM"),
        # Alarm — Buzzer#1 reverse warning (digital/PWM)
        GPIOPin(pin_bcm=20, label="BUZZER1_REVERSE",    group="alarm",      mode="OUT"),
        # Alarm — Buzzer#2 engine sound (PWM0, KY-006 passive buzzer)
        GPIOPin(pin_bcm=18, label="BUZZER2_ENGINE",     group="alarm",      mode="PWM"),
        # Light — Reverse lamp (12V, low-side MOSFET)
        GPIOPin(pin_bcm=26, label="REVERSE_LAMP",       group="light_gpio", mode="OUT"),
        # Light — Rig floor light (9-12V, MOSFET, GPIO13)
        GPIOPin(pin_bcm=13, label="RIG_FLOOR_LIGHT",    group="light_gpio", mode="OUT"),
        # Light — Signal (LHR) sarı LED sol (GPIO21)
        GPIOPin(pin_bcm=21, label="SIGNAL_LIGHT_LEFT",  group="light_gpio", mode="OUT"),
        # Light — Signal (LHR) sarı LED sağ (GPIO16)
        GPIOPin(pin_bcm=16, label="SIGNAL_LIGHT_RIGHT", group="light_gpio", mode="OUT"),
        # I2C bus (PCA9685 + ADS1115#1 + ADS1115#2)
        GPIOPin(pin_bcm=2,  label="I2C_SDA",            group="i2c",        mode="I2C"),
        GPIOPin(pin_bcm=3,  label="I2C_SCL",            group="i2c",        mode="I2C"),
    ]

    @classmethod
    def by_label(cls, label: str) -> Optional[GPIOPin]:
        for p in cls.PINS:
            if p.label == label:
                return p
        return None

    @classmethod
    def by_group(cls, group: str) -> List[GPIOPin]:
        return [p for p in cls.PINS if p.group == group]

    @classmethod
    def validate_no_conflicts(cls) -> List[str]:
        seen: Dict[int, str] = {}
        conflicts = []
        for p in cls.PINS:
            if p.pin_bcm in seen:
                conflicts.append(f"BCM{p.pin_bcm}: {seen[p.pin_bcm]} vs {p.label}")
            else:
                seen[p.pin_bcm] = p.label
        return conflicts


# =========================================================
# HARDWARE — PCA9685 CHANNEL MAP  (Connections xlsx)
# I2C addr 0x40 — tüm motor/servo/LED PWM kanalları burada
# =========================================================
class PCA9685ChannelMap:
    """
    PCA9685 16-kanal PWM genişletici kanal atamaları.
    SSOT: Connections sekmesi (xlsx).

    CH0  → LED Grup1 Kırmızı (Parking Light) — MOSFET
    CH1  → LED Grup3 Beyaz soluk (Low Beam)  — MOSFET
    CH2  → LED Grup4 Beyaz keskin (High Beam)— MOSFET
    CH3  → LED Grup5 Tepe Lambası (Rotation) — MOSFET
    CH4  → BTS7960B RPWM (Driver ileri hız)
    CH5  → BTS7960B LPWM (Driver geri hız)
    CH6  → Servo PWM (Wheel direksiyon)
    CH7  → Servo yedek (opsiyonel)
    CH8  → L298P#1 IN1 (DRAWWORKS M1 yön A)
    CH9  → L298P#1 IN2 (DRAWWORKS M1 yön B)
    CH10 → L298P#2 IN4 (ROTARY TABLE M4 yön B)
    CH11 → L298P#1 IN3 (SANDLINE M2 yön A)
    CH12 → L298P#1 IN4 (SANDLINE M2 yön B)
    CH13 → L298P#2 IN1 (WINCH M3 yön A)
    CH14 → L298P#2 IN2 (WINCH M3 yön B)
    CH15 → L298P#2 IN3 (ROTARY TABLE M4 yön A)
    """
    # LED grupları (PCA9685 CH → MOSFET → LED)
    CH_LED_PARKING   = 0   # Grup1 Kırmızı
    CH_LED_LOW_BEAM  = 1   # Grup3 Beyaz soluk
    CH_LED_HIGH_BEAM = 2   # Grup4 Beyaz keskin
    CH_LED_ROTATION  = 3   # Grup5 Tepe lambası

    # BTS7960B (Driver/ana sürüş motoru)
    CH_BTS_RPWM = 4
    CH_BTS_LPWM = 5

    # Servo (Wheel)
    CH_SERVO    = 6

    # L298P#1 — M1=DRAWWORKS, M2=SANDLINE
    CH_L298P1_M1_IN1 = 8   # DRAWWORKS yön A
    CH_L298P1_M1_IN2 = 9   # DRAWWORKS yön B
    CH_L298P1_M2_IN3 = 11  # SANDLINE yön A
    CH_L298P1_M2_IN4 = 12  # SANDLINE yön B

    # L298P#2 — M3=WINCH, M4=ROTARY TABLE
    CH_L298P2_M3_IN1 = 13  # WINCH yön A
    CH_L298P2_M3_IN2 = 14  # WINCH yön B
    CH_L298P2_M4_IN3 = 15  # ROTARY TABLE yön A
    CH_L298P2_M4_IN4 = 10  # ROTARY TABLE yön B (xlsx: CH10)

    PCA_ADDR    = 0x40
    PCA_FREQ_HZ = 50        # Servo için 50Hz; LED/motor için de yeterli


# =========================================================
# HARDWARE — PCA9685 DRIVER  (I2C)
# =========================================================
class PCA9685Driver:
    """
    PCA9685 16-kanal PWM sürücü.
    adafruit-circuitpython-pca9685 kütüphanesi kullanır.
    Mevcut değilse simülasyon modunda çalışır.
    """
    FULL_ON  = 4096
    FULL_OFF = 0

    def __init__(self, i2c_addr: int = PCA9685ChannelMap.PCA_ADDR,
                 freq_hz: int = PCA9685ChannelMap.PCA_FREQ_HZ):
        self._pca    = None
        self._addr   = i2c_addr
        self._freq   = freq_hz
        self._avail  = False

    def initialize(self) -> None:
        try:
            import board
            import busio
            from adafruit_pca9685 import PCA9685
            i2c = busio.I2C(board.SCL, board.SDA)
            self._pca = PCA9685(i2c, address=self._addr)
            self._pca.frequency = self._freq
            self._avail = True
            print(f"[PCA9685] Initialized addr=0x{self._addr:02X} freq={self._freq}Hz")
        except Exception as e:
            print(f"[PCA9685] Not available: {e} — simulation mode")
            self._avail = False

    def set_duty(self, channel: int, duty_pct: float) -> None:
        """duty_pct: 0..100"""
        if not self._avail or self._pca is None:
            return
        val = int(duty_pct / 100.0 * self.FULL_ON)
        val = max(0, min(self.FULL_ON, val))
        self._pca.channels[channel].duty_cycle = val << 4  # 12-bit → 16-bit

    def set_raw(self, channel: int, on: int, off: int) -> None:
        """Direct 12-bit on/off register write."""
        if not self._avail or self._pca is None:
            return
        self._pca.channels[channel].duty_cycle = off << 4

    def set_digital(self, channel: int, high: bool) -> None:
        self.set_duty(channel, 100.0 if high else 0.0)

    def set_servo_us(self, channel: int, pulse_us: float,
                     period_us: float = 20000.0) -> None:
        """Servo pulse width in microseconds (500..2500µs tipik)."""
        duty = pulse_us / period_us * 100.0
        self.set_duty(channel, duty)

    def all_off(self) -> None:
        if not self._avail or self._pca is None:
            return
        for ch in range(16):
            self.set_duty(ch, 0)

    def cleanup(self) -> None:
        self.all_off()
        self._avail = False

    @property
    def available(self) -> bool:
        return self._avail


# =========================================================
# HARDWARE — MOTOR RUNTIME  (MODULE-129)
# SSOT: Connections xlsx
#   BTS7960B  → PCA9685 CH4(RPWM) / CH5(LPWM)    → DRIVER modu
#   L298P#1 M1→ PCA9685 CH8/CH9                   → DRAWWORKS
#   L298P#1 M2→ PCA9685 CH11/CH12                 → SANDLINE
#   L298P#2 M3→ PCA9685 CH13/CH14                 → WINCH
#   L298P#2 M4→ PCA9685 CH15/CH10                 → ROTARY TABLE
#   Servo      → PCA9685 CH6                       → WHEEL
# =========================================================
class MotorRuntime:
    """
    Tüm motor kontrolü PCA9685 üzerinden.
    BTS7960B: RPWM/LPWM çifti — çift yön PWM.
    L298P: IN çiftleri — yön + hız (IN1/IN2 terslenerek).
    Servo: 50Hz PWM, 500–2500µs pulse width.
    """

    # Servo pulse width sınırları (µs)
    SERVO_CENTER_US = 1500
    SERVO_MIN_US    = 500
    SERVO_MAX_US    = 2500

    def __init__(self, pca: PCA9685Driver):
        self._pca = pca
        self._initialized = False

    def initialize(self) -> None:
        self._pca.initialize()
        self._pca.all_off()
        self._initialized = True
        print("[MotorRuntime] Initialized (PCA9685)")

    # ----------------------------------------------------------
    # BTS7960B — DRIVER (tek yüksek akımlı DC motor)
    # RPWM = ileri, LPWM = geri; biri aktifken diğeri 0
    # ----------------------------------------------------------
    def set_driver(self, speed_pct: float) -> None:
        speed = max(-100.0, min(100.0, speed_pct))
        if speed >= 0:
            self._pca.set_duty(PCA9685ChannelMap.CH_BTS_RPWM, speed)
            self._pca.set_duty(PCA9685ChannelMap.CH_BTS_LPWM, 0)
        else:
            self._pca.set_duty(PCA9685ChannelMap.CH_BTS_RPWM, 0)
            self._pca.set_duty(PCA9685ChannelMap.CH_BTS_LPWM, abs(speed))

    # ----------------------------------------------------------
    # L298P yön mantığı: IN1=HIGH/IN2=LOW = ileri; tersi = geri
    # Hız: IN1 PWM duty (yüksek duty = yüksek hız)
    # ----------------------------------------------------------
    def _set_l298p(self, ch_in1: int, ch_in2: int, speed_pct: float) -> None:
        speed = max(-100.0, min(100.0, speed_pct))
        if speed >= 0:
            self._pca.set_duty(ch_in1, abs(speed))
            self._pca.set_digital(ch_in2, False)
        else:
            self._pca.set_digital(ch_in1, False)
            self._pca.set_duty(ch_in2, abs(speed))

    def set_drawworks(self, speed_pct: float) -> None:
        self._set_l298p(PCA9685ChannelMap.CH_L298P1_M1_IN1,
                        PCA9685ChannelMap.CH_L298P1_M1_IN2, speed_pct)

    def set_sandline(self, speed_pct: float) -> None:
        self._set_l298p(PCA9685ChannelMap.CH_L298P1_M2_IN3,
                        PCA9685ChannelMap.CH_L298P1_M2_IN4, speed_pct)

    def set_winch(self, speed_pct: float) -> None:
        self._set_l298p(PCA9685ChannelMap.CH_L298P2_M3_IN1,
                        PCA9685ChannelMap.CH_L298P2_M3_IN2, speed_pct)

    def set_rotary(self, speed_pct: float) -> None:
        self._set_l298p(PCA9685ChannelMap.CH_L298P2_M4_IN3,
                        PCA9685ChannelMap.CH_L298P2_M4_IN4, speed_pct)

    # ----------------------------------------------------------
    # Servo — WHEEL direksiyon
    # angle_pct: -100..100 → 500..2500µs pulse
    # ----------------------------------------------------------
    def set_wheel(self, angle_pct: float) -> None:
        angle = max(-100.0, min(100.0, angle_pct))
        pulse_us = self.SERVO_CENTER_US + (angle / 100.0) * (
            self.SERVO_MAX_US - self.SERVO_CENTER_US
        )
        pulse_us = max(self.SERVO_MIN_US, min(self.SERVO_MAX_US, pulse_us))
        self._pca.set_servo_us(PCA9685ChannelMap.CH_SERVO, pulse_us)

    def stop_all(self) -> None:
        self._pca.all_off()
        # Servo'yu merkeze döndür
        self._pca.set_servo_us(PCA9685ChannelMap.CH_SERVO, self.SERVO_CENTER_US)

    def cleanup(self) -> None:
        self.stop_all()
        self._pca.cleanup()
        self._initialized = False


# =========================================================
# HARDWARE — LIGHT RUNTIME  (MODULE-130)
# SSOT: Connections xlsx
#   PCA9685 CH0 → Parking Light  (Grup1 Kırmızı, MOSFET)
#   PCA9685 CH1 → Low Beam       (Grup3 Beyaz soluk, MOSFET)
#   PCA9685 CH2 → High Beam      (Grup4 Beyaz keskin, MOSFET)
#   PCA9685 CH3 → Rotation Light (Grup5 Tepe lambası, MOSFET)
#   GPIO13      → Rig Floor Light (9-12V, MOSFET)
#   GPIO16      → Signal LHR Sağ  (Sarı LED)
#   GPIO21      → Signal LHR Sol  (Sarı LED)
#   GPIO26      → Reverse Lamp    (12V, MOSFET) — DRIVER moduna bağlı
# =========================================================
class LightRuntime:
    """
    LED/Lamba kontrolü:
    - PCA9685 üzerindeki LED grupları (CH0-CH3)
    - GPIO'ya bağlı özel lambalar (Rig Floor, Signal, Reverse)
    """

    def __init__(self, pca: PCA9685Driver):
        self._pca = pca

    def initialize(self) -> None:
        # GPIO ışıkları
        if _GPIO_AVAILABLE:
            for p in GPIOMap.by_group("light_gpio"):
                GPIO.setup(p.pin_bcm, GPIO.OUT)
                GPIO.output(p.pin_bcm, GPIO.LOW)
        print("[LightRuntime] Initialized")

    # PCA9685 LED kanalları (0=OFF, 100=tam parlak)
    def _pca_set(self, channel: int, enabled: bool, duty: float = 100.0) -> None:
        self._pca.set_duty(channel, duty if enabled else 0.0)

    # GPIO ışık kontrolü
    def _gpio_set(self, label: str, enabled: bool) -> None:
        if not _GPIO_AVAILABLE:
            return
        p = GPIOMap.by_label(label)
        if p:
            GPIO.output(p.pin_bcm, GPIO.HIGH if enabled else GPIO.LOW)

    def set_parking_light(self, enabled: bool) -> None:
        self._pca_set(PCA9685ChannelMap.CH_LED_PARKING, enabled)

    def set_low_beam(self, enabled: bool) -> None:
        # Soluk beyaz → %35 duty (xlsx önerisi)
        self._pca_set(PCA9685ChannelMap.CH_LED_LOW_BEAM, enabled, duty=35.0)

    def set_high_beam(self, enabled: bool) -> None:
        # Keskin beyaz → %90 duty (xlsx önerisi)
        self._pca_set(PCA9685ChannelMap.CH_LED_HIGH_BEAM, enabled, duty=90.0)

    def set_rotation_light(self, enabled: bool) -> None:
        self._pca_set(PCA9685ChannelMap.CH_LED_ROTATION, enabled)

    def set_rig_floor_light(self, enabled: bool) -> None:
        self._gpio_set("RIG_FLOOR_LIGHT", enabled)

    def set_signal_lhr(self, enabled: bool) -> None:
        # Her iki sarı LED aynı anda (LHR = Left+Right)
        self._gpio_set("SIGNAL_LIGHT_LEFT",  enabled)
        self._gpio_set("SIGNAL_LIGHT_RIGHT", enabled)

    def set_reverse_lamp(self, enabled: bool) -> None:
        self._gpio_set("REVERSE_LAMP", enabled)

    def set(self, key: str, enabled: bool) -> None:
        dispatch = {
            "parking_light":   self.set_parking_light,
            "low_beam":        self.set_low_beam,
            "high_beam":       self.set_high_beam,
            "rotation_light":  self.set_rotation_light,
            "rig_floor_light": self.set_rig_floor_light,
            "signal_lhr":      self.set_signal_lhr,
            "rev_led":         self.set_reverse_lamp,
        }
        fn = dispatch.get(key)
        if fn:
            fn(enabled)

    def apply_command(self, cmd: CommandPayload) -> None:
        for key in VALID_LIGHT_KEYS:
            self.set(key, bool(getattr(cmd, key, False)))
        # Reverse lamp: DRIVER modunda geri gidişte ON
        self.set_reverse_lamp(cmd.mode == "DRIVER" and cmd.val < -5)

    def all_off(self) -> None:
        for ch in (PCA9685ChannelMap.CH_LED_PARKING,
                   PCA9685ChannelMap.CH_LED_LOW_BEAM,
                   PCA9685ChannelMap.CH_LED_HIGH_BEAM,
                   PCA9685ChannelMap.CH_LED_ROTATION):
            self._pca.set_duty(ch, 0)
        for label in ("RIG_FLOOR_LIGHT", "SIGNAL_LIGHT_LEFT",
                      "SIGNAL_LIGHT_RIGHT", "REVERSE_LAMP"):
            self._gpio_set(label, False)


# =========================================================
# HARDWARE — ALARM RUNTIME  (MODULE-131)
# SSOT: Connections xlsx
#   GPIO20 → BUZZER#1 Reverse Warning (digital)
#   GPIO18 → BUZZER#2 Engine Sound    (PWM0, KY-006)
# =========================================================
class AlarmRuntime:
    """
    Buzzer#1: Reverse Warning — GPIO20, dijital ON/OFF.
    Buzzer#2: Caterpillar Engine Sound — GPIO18 PWM0 (KY-006 pasif buzzer).
    """

    PWM_FREQ_BASE = 100   # Hz — KY-006 için başlangıç frekansı

    def __init__(self):
        self._engine_pwm = None

    def initialize(self) -> None:
        if not _GPIO_AVAILABLE:
            print("[AlarmRuntime] GPIO not available — simulation mode")
            return
        # Buzzer#1 — dijital OUT
        p1 = GPIOMap.by_label("BUZZER1_REVERSE")
        if p1:
            GPIO.setup(p1.pin_bcm, GPIO.OUT)
            GPIO.output(p1.pin_bcm, GPIO.LOW)
        # Buzzer#2 — PWM (KY-006 pasif buzzer, ses frekans ile üretilir)
        p2 = GPIOMap.by_label("BUZZER2_ENGINE")
        if p2:
            GPIO.setup(p2.pin_bcm, GPIO.OUT)
            self._engine_pwm = GPIO.PWM(p2.pin_bcm, self.PWM_FREQ_BASE)
            self._engine_pwm.start(0)
        print("[AlarmRuntime] Initialized")

    def set_reverse_buzzer(self, enabled: bool) -> None:
        """Buzzer#1 — kısa aralıklı REVERSE_WARNING."""
        if not _GPIO_AVAILABLE:
            return
        p = GPIOMap.by_label("BUZZER1_REVERSE")
        if p:
            GPIO.output(p.pin_bcm, GPIO.HIGH if enabled else GPIO.LOW)

    def set_engine_sound(self, intensity_pct: float) -> None:
        """
        Buzzer#2 — Caterpillar Engine Sound.
        intensity_pct: 0..100 → frekans ve duty oranını ayarlar.
        0-5 arası → sessiz (rölanti altı).
        """
        if not _GPIO_AVAILABLE or self._engine_pwm is None:
            return
        if intensity_pct < 5:
            self._engine_pwm.ChangeDutyCycle(0)
            return
        # Frekans: 100Hz (rölanti) → 250Hz (tam gaz)
        freq = int(100 + (intensity_pct / 100.0) * 150)
        # Duty: %30 sabit (KY-006 için optimum ses)
        self._engine_pwm.ChangeFrequency(freq)
        self._engine_pwm.ChangeDutyCycle(30)

    def stop_all(self) -> None:
        self.set_reverse_buzzer(False)
        self.set_engine_sound(0)

    def cleanup(self) -> None:
        self.stop_all()
        if self._engine_pwm:
            try:
                self._engine_pwm.stop()
            except Exception:
                pass
        self._engine_pwm = None


# =========================================================
# HARDWARE — COOLING RUNTIME  (MODULE-132)
# SSOT: Connections xlsx
#   GPIO25 Pin22 → MASTER_FAN_CTRL (12V fan, low-side MOSFET, MasterPi)
#   RC fan → RemotePi GPIO18 (MasterPi sadece state takibi yapar)
# =========================================================
class CoolingRuntime:
    """
    MasterPi MC fan: GPIO25, low-side MOSFET, dijital ON/OFF
    (xlsx'te PWM opsiyonel; temel kullanım: ≥40°C → ON).
    RC fan: RemotePi'de, MasterPi sadece state bilgisini publish eder.
    """

    def __init__(self):
        self._mc_pwm = None

    def initialize(self) -> None:
        if not _GPIO_AVAILABLE:
            print("[CoolingRuntime] GPIO not available — simulation mode")
            return
        p = GPIOMap.by_label("MASTER_FAN_CTRL")
        if p:
            GPIO.setup(p.pin_bcm, GPIO.OUT)
            GPIO.output(p.pin_bcm, GPIO.LOW)
            # PWM opsiyonel — şimdilik dijital ON/OFF
            self._mc_pwm = GPIO.PWM(p.pin_bcm, 25000)  # 25kHz sessiz PWM
            self._mc_pwm.start(0)
        print("[CoolingRuntime] Initialized (MC fan GPIO25)")

    def set_mc_fan(self, duty_pct: float) -> None:
        """0=OFF, 100=tam hız."""
        if self._mc_pwm:
            self._mc_pwm.ChangeDutyCycle(max(0.0, min(100.0, duty_pct)))
        elif _GPIO_AVAILABLE:
            p = GPIOMap.by_label("MASTER_FAN_CTRL")
            if p:
                GPIO.output(p.pin_bcm, GPIO.HIGH if duty_pct > 0 else GPIO.LOW)

    def set_rc_fan(self, duty_pct: float) -> None:
        """RC fan RemotePi'de — MasterPi sadece state'i loglar."""
        pass  # RemotePi kendi fanını yönetir

    def stop_all(self) -> None:
        self.set_mc_fan(0)

    def cleanup(self) -> None:
        self.stop_all()
        if self._mc_pwm:
            try:
                self._mc_pwm.stop()
            except Exception:
                pass
        self._mc_pwm = None


# =========================================================
# HARDWARE — ADC RUNTIME  (MODULE-134)
# SSOT: I2C_ADC_MAP + Connections xlsx
#   ADS1115#1  I2C 0x48 (ADDR→GND)  — MasterPi
#     A0: Batarya voltaj ölçümü
#     A1: LM35D sıcaklık sensörü
#     A2: NTC batarya sıcaklık
#     A3: Yedek
#   ADS1115#2  I2C 0x49 (ADDR→3.3V) — MasterPi (ADXL335 tilt safety)
#     A0: ADXL335 X_OUT
#     A1: ADXL335 Y_OUT
#     A2: ADXL335 Z_OUT
#     A3: Yedek
# =========================================================
class ADCRuntime:
    """
    İki ADS1115 ADC okuyucu.
    #1 (0x48): Batarya + sıcaklık kanalları.
    #2 (0x49): ADXL335 tilt sensörü (Selective Safety Logic).
    """

    ADS1115_1_ADDR = 0x48  # ADDR → GND
    ADS1115_2_ADDR = 0x49  # ADDR → 3.3V

    def __init__(self):
        self._ads1 = None   # Batarya/sıcaklık
        self._ads2 = None   # ADXL335 tilt
        self._available = False

    def initialize(self) -> None:
        try:
            import board
            import busio
            import adafruit_ads1x15.ads1115 as ADS
            i2c = busio.I2C(board.SCL, board.SDA)
            self._ads1 = ADS.ADS1115(i2c, address=self.ADS1115_1_ADDR)
            self._ads2 = ADS.ADS1115(i2c, address=self.ADS1115_2_ADDR)
            self._available = True
            print("[ADCRuntime] ADS1115 #1(0x48) + #2(0x49) initialized")
        except Exception as e:
            print(f"[ADCRuntime] Not available: {e} — simulation mode")
            self._available = False

    def _read(self, ads_instance: Any, channel: int) -> float:
        try:
            from adafruit_ads1x15.analog_in import AnalogIn
            import adafruit_ads1x15.ads1115 as ADS
            ch = AnalogIn(ads_instance, getattr(ADS, f"P{channel}"))
            return ch.voltage
        except Exception as e:
            print(f"[ADCRuntime] Read error: {e}")
            return 0.0

    def read_channel(self, channel: int, ads_num: int = 1) -> float:
        """ads_num=1 → ADS1115#1, ads_num=2 → ADS1115#2"""
        if not self._available:
            return 3.3 + math.sin(time.time() * 0.1 + channel + ads_num) * 0.1
        ads = self._ads1 if ads_num == 1 else self._ads2
        if ads is None:
            return 0.0
        return self._read(ads, channel)

    def read_battery_voltage(self) -> float:
        """ADS1115#1 A0 — batarya voltaj bölücü."""
        return self.read_channel(0, ads_num=1)

    def read_temperature_lm35(self) -> float:
        """ADS1115#1 A1 — LM35D → °C (10mV/°C)."""
        v = self.read_channel(1, ads_num=1)
        return v * 100.0  # 10mV/°C

    def read_tilt_x(self) -> float:
        """ADS1115#2 A0 — ADXL335 X ekseni."""
        return self.read_channel(0, ads_num=2)

    def read_tilt_y(self) -> float:
        """ADS1115#2 A1 — ADXL335 Y ekseni."""
        return self.read_channel(1, ads_num=2)

    def read_tilt_z(self) -> float:
        """ADS1115#2 A2 — ADXL335 Z ekseni."""
        return self.read_channel(2, ads_num=2)

    # Eski API uyumluluğu (stack'teki _adc_loop için)
    def read_battery_master(self) -> float:
        return self.read_battery_voltage()

    def read_battery_remote(self) -> float:
        """RemotePi bataryası ADC'si RemotePi'de — sim değer döner."""
        return 3.7 + math.sin(time.time() * 0.05) * 0.1

    def voltage_to_percent(self, voltage: float,
                           v_max: float = 12.6, v_min: float = 9.0) -> float:
        """12V LiPo pack için voltaj → yüzde."""
        pct = (voltage - v_min) / max(0.01, v_max - v_min) * 100.0
        return max(0.0, min(100.0, pct))


# =========================================================
# INTEGRATION — COMMAND TRANSPORT CONTRACT  (MODULE-150)
# =========================================================
PACKET_TYPE_COMMAND    = "command"
PACKET_TYPE_HEARTBEAT  = "heartbeat"
PACKET_TYPE_ACK        = "ack"
PACKET_TYPE_NACK       = "nack"
PACKET_TYPE_STATUS     = "status"


@dataclass
class TransportPacket:
    packet_type: str
    payload: Dict[str, Any] = field(default_factory=dict)
    ts: float = field(default_factory=time.time)

    def to_json(self) -> str:
        return json.dumps({"packet_type": self.packet_type, "payload": self.payload, "ts": self.ts})

    @staticmethod
    def from_json(raw: str) -> "TransportPacket":
        d = json.loads(raw)
        return TransportPacket(
            packet_type=d.get("packet_type", PACKET_TYPE_COMMAND),
            payload=d.get("payload", d),
            ts=d.get("ts", time.time()),
        )


# =========================================================
# INTEGRATION — MASTERPI TRANSPORT ADAPTER  (MODULE-158)
# =========================================================
class MasterPiTransportAdapter:
    """
    MQTT transport → MasterPi runtime stack adapter.
    - Validates incoming transport packets
    - Converts heartbeat packets into RemoteLinkWatchdog updates
    - Converts command packets into stack command dispatch
    - Returns ACK/NACK/STATUS in transport contract format
    """

    def __init__(self, cfg: HardwareConfig, stack: "MasterPiHardwareRuntimeStack"):
        self._cfg   = cfg
        self._stack = stack
        self._client = None
        self._connected = False

    def connect(self) -> None:
        if not _MQTT_AVAILABLE:
            print("[Transport] paho-mqtt not available — transport disabled")
            return
        try:
            self._client = mqtt.Client(client_id="MasterPi_Runtime")
            self._client.on_connect    = self._on_connect
            self._client.on_disconnect = self._on_disconnect
            self._client.on_message    = self._on_message
            self._client.connect(self._cfg.mqtt_broker_ip, self._cfg.mqtt_broker_port, 60)
            self._client.loop_start()
            print(f"[Transport] Connecting to {self._cfg.mqtt_broker_ip}:{self._cfg.mqtt_broker_port}")
        except Exception as e:
            print(f"[Transport] Connect error: {e}")

    def _on_connect(self, client, userdata, flags, rc) -> None:
        if rc == 0:
            self._connected = True
            self._client.subscribe(self._cfg.mqtt_topic_control)
            print(f"[Transport] Connected, subscribed to {self._cfg.mqtt_topic_control}")
        else:
            print(f"[Transport] Connect failed rc={rc}")

    def _on_disconnect(self, client, userdata, rc) -> None:
        self._connected = False
        print(f"[Transport] Disconnected rc={rc}")

    def _on_message(self, client, userdata, msg) -> None:
        try:
            raw_str = msg.payload.decode("utf-8")
            raw_dict = json.loads(raw_str)

            # Legacy RemotePi flat payload (no packet_type wrapper)
            if "packet_type" not in raw_dict:
                cmd = CommandPayload.from_dict(raw_dict)
                self._stack.dispatch_command(cmd)
                return

            # Transport contract packet
            pkt = TransportPacket.from_json(raw_str)
            if pkt.packet_type == PACKET_TYPE_HEARTBEAT:
                self._stack.watchdog.heartbeat(pkt.ts)
            elif pkt.packet_type == PACKET_TYPE_COMMAND:
                cmd = CommandPayload.from_dict(pkt.payload)
                result = self._stack.dispatch_command(cmd)
                self._send_ack(result)
            else:
                print(f"[Transport] Unknown packet type: {pkt.packet_type}")
        except Exception as e:
            print(f"[Transport] Message error: {e}")

    def _send_ack(self, success: bool) -> None:
        if not self._connected:
            return
        pkt_type = PACKET_TYPE_ACK if success else PACKET_TYPE_NACK
        payload = TransportPacket(packet_type=pkt_type, payload={"ok": success})
        try:
            self._client.publish(self._cfg.mqtt_topic_status, payload.to_json(), qos=0)
        except Exception:
            pass

    def publish_status(self, status: Dict[str, Any]) -> None:
        if not self._connected:
            return
        pkt = TransportPacket(packet_type=PACKET_TYPE_STATUS, payload=status)
        try:
            self._client.publish(self._cfg.mqtt_topic_status, pkt.to_json(), qos=0)
        except Exception:
            pass

    def disconnect(self) -> None:
        if self._client:
            try:
                self._client.loop_stop()
                self._client.disconnect()
            except Exception:
                pass
        self._connected = False


# =========================================================
# INTEGRATION — RUNTIME EVENT BINDINGS  (MODULE-144)
# =========================================================
def bind_runtime_events(
    bus: EventBus,
    state: SystemState,
    fsm: MasterPiFSM,
    motor: MotorRuntime,
    light: LightRuntime,
    alarm: AlarmRuntime,
    cooling: CoolingRuntime,
    telemetry: TelemetryLogger,
) -> None:
    """
    Fault-policy aware + FSM-integrated event bindings.
    Wires EventBus events to hardware runtimes.
    """

    def on_fault_raised(event_name: str, payload: Any) -> None:
        if not isinstance(payload, dict):
            return
        level = payload.get("level", 1)
        state.fault_level = max(state.fault_level, level)
        telemetry.log_event(event_name, payload)
        if level >= 2:
            motor.stop_all()
            alarm.stop_all()
            light.all_off()
            if fsm.is_operational():
                fsm.transition(FSM_STATE_FAULT)

    def on_remote_link_down(event_name: str, payload: Any) -> None:
        state.remote_link_alive = False
        telemetry.log_event(event_name, payload)

    def on_remote_link_up(event_name: str, payload: Any) -> None:
        state.remote_link_alive = True
        telemetry.log_event(event_name, payload)

    def on_system_stopped(event_name: str, payload: Any) -> None:
        motor.stop_all()
        alarm.stop_all()
        light.all_off()
        cooling.stop_all()
        telemetry.log_event(event_name, payload)

    def on_telemetry_snapshot(event_name: str, payload: Any) -> None:
        telemetry.log_snapshot(payload)

    def on_mode_changed(event_name: str, payload: Any) -> None:
        telemetry.log_event(event_name, payload)

    bus.subscribe(EVENT_FAULT_RAISED,        on_fault_raised)
    bus.subscribe(EVENT_REMOTE_LINK_DOWN,    on_remote_link_down)
    bus.subscribe(EVENT_REMOTE_LINK_UP,      on_remote_link_up)
    bus.subscribe(EVENT_SYSTEM_STOPPED,      on_system_stopped)
    bus.subscribe(EVENT_TELEMETRY_SNAPSHOT,  on_telemetry_snapshot)
    bus.subscribe(EVENT_MODE_CHANGED,        on_mode_changed)


# =========================================================
# INTEGRATION — MASTERPI HARDWARE RUNTIME STACK  (MODULE-156)
# =========================================================
class MasterPiHardwareRuntimeStack:
    """
    Final integrated hardware runtime stack for MasterPi.

    Composes:
      RuntimeConfig → FSM → EventBus → SystemState
      SafetyInterlock → RemoteLinkWatchdog
      MotorRuntime → LightRuntime → AlarmRuntime → CoolingRuntime → ADCRuntime
      TelemetryLogger → StartupShutdownSequence
      MasterPiTransportAdapter

    Usage:
        stack = MasterPiHardwareRuntimeStack()
        stack.start()           # runs startup sequence + begins loops
        # ... dispatch_command() called from transport on each MQTT message
        stack.stop()            # graceful shutdown
    """

    def __init__(self, config_path: Optional[str] = None):
        # --- Config ---
        self.cfg = RuntimeConfigLoader.load(config_path)

        # --- Validate GPIO map ---
        conflicts = GPIOMap.validate_no_conflicts()
        if conflicts:
            print(f"[RuntimeStack] GPIO conflicts detected: {conflicts}")

        # --- Core ---
        self.bus      = EventBus()
        self.state    = SystemState()
        self.fsm      = MasterPiFSM(self.bus)
        self.telemetry = TelemetryLogger(
            log_dir=self.cfg.hardware.telemetry_log_dir,
            max_files=self.cfg.hardware.telemetry_max_files,
        )

        # --- Safety ---
        self.watchdog  = RemoteLinkWatchdog(
            timeout_s=self.cfg.safety.watchdog_timeout_s,
            bus=self.bus,
        )
        self.interlock = SafetyInterlock(self.cfg.safety, self.fsm, self.bus)

        # --- Hardware ---
        self.pca     = PCA9685Driver()
        self.motor   = MotorRuntime(self.pca)
        self.light   = LightRuntime(self.pca)
        self.alarm   = AlarmRuntime()
        self.cooling = CoolingRuntime()
        self.adc     = ADCRuntime()

        # --- Transport ---
        self.transport = MasterPiTransportAdapter(self.cfg.hardware, self)

        # --- Sequence ---
        self.sequence = StartupShutdownSequence()
        self._build_startup_sequence()
        self._build_shutdown_sequence()

        # --- Bind events ---
        bind_runtime_events(
            self.bus, self.state, self.fsm,
            self.motor, self.light, self.alarm, self.cooling, self.telemetry
        )

        # --- Loop threads ---
        self._running = False
        self._threads: List[threading.Thread] = []

    # ----------------------------------------------------------
    # SEQUENCE BUILDERS
    # ----------------------------------------------------------
    def _build_startup_sequence(self) -> None:
        self.sequence.add_startup_step("gpio_validate",     self._step_validate_gpio,   critical=True)
        self.sequence.add_startup_step("gpio_init",         self._step_init_gpio,        critical=True)
        self.sequence.add_startup_step("motor_init",        self.motor.initialize,       critical=True)
        self.sequence.add_startup_step("light_init",        self.light.initialize,       critical=True)
        self.sequence.add_startup_step("alarm_init",        self.alarm.initialize,       critical=False)
        self.sequence.add_startup_step("cooling_init",      self.cooling.initialize,     critical=False)
        self.sequence.add_startup_step("adc_init",          self.adc.initialize,         critical=False)
        self.sequence.add_startup_step("transport_connect", self.transport.connect,      critical=False)
        self.sequence.add_startup_step("fsm_to_running",    self._step_fsm_to_running,   critical=True)

    def _build_shutdown_sequence(self) -> None:
        self.sequence.add_shutdown_step("fsm_to_shutdown",   self._step_fsm_to_shutdown,   critical=False)
        self.sequence.add_shutdown_step("motor_stop",         self.motor.stop_all,           critical=False)
        self.sequence.add_shutdown_step("alarm_stop",         self.alarm.stop_all,           critical=False)
        self.sequence.add_shutdown_step("light_off",          self.light.all_off,            critical=False)
        self.sequence.add_shutdown_step("cooling_stop",       self.cooling.stop_all,         critical=False)
        self.sequence.add_shutdown_step("transport_disconnect", self.transport.disconnect,   critical=False)
        self.sequence.add_shutdown_step("motor_cleanup",      self.motor.cleanup,            critical=False)
        self.sequence.add_shutdown_step("alarm_cleanup",      self.alarm.cleanup,            critical=False)
        self.sequence.add_shutdown_step("cooling_cleanup",    self.cooling.cleanup,          critical=False)
        self.sequence.add_shutdown_step("telemetry_close",    self.telemetry.close,          critical=False)
        if _GPIO_AVAILABLE:
            self.sequence.add_shutdown_step("gpio_cleanup", GPIO.cleanup,                    critical=False)

    def _step_validate_gpio(self) -> None:
        conflicts = GPIOMap.validate_no_conflicts()
        if conflicts:
            raise RuntimeError(f"GPIO conflicts: {conflicts}")

    def _step_init_gpio(self) -> None:
        if _GPIO_AVAILABLE:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)

    def _step_fsm_to_running(self) -> None:
        if not self.fsm.transition(FSM_STATE_RUNNING):
            raise RuntimeError("FSM could not transition to RUNNING")
        self.state.is_started = True
        self.bus.emit(EVENT_SYSTEM_STARTED, {"ts": time.time()})

    def _step_fsm_to_shutdown(self) -> None:
        self.fsm.transition(FSM_STATE_SHUTDOWN)

    # ----------------------------------------------------------
    # PUBLIC API
    # ----------------------------------------------------------
    def start(self) -> bool:
        print("[RuntimeStack] Starting...")
        report = self.sequence.run_startup()
        if not report.success:
            self.bus.emit_error(FAULT_CODE_STARTUP_FAILED,
                                f"Startup failed at: {report.steps_failed}", level=2)
            return False
        self._running = True
        self._spawn_loops()
        print(f"[RuntimeStack] Started in {report.elapsed_s:.2f}s")
        return True

    def stop(self) -> None:
        print("[RuntimeStack] Stopping...")
        self._running = False
        for t in self._threads:
            t.join(timeout=2.0)
        self._threads.clear()
        self.state.is_started = False
        self.bus.emit(EVENT_SYSTEM_STOPPED, {"ts": time.time()})
        self.sequence.run_shutdown()
        print("[RuntimeStack] Stopped")

    def dispatch_command(self, cmd: CommandPayload) -> bool:
        """
        Main command entry point — called by TransportAdapter on each incoming packet.
        Returns True if command was accepted and applied.
        """
        # Always feed watchdog on any packet
        self.watchdog.heartbeat(cmd.ts)

        # Validate via SafetyInterlock
        decision = self.interlock.check_command(cmd, self.state)
        if not decision.allowed:
            self.bus.emit(EVENT_SAFETY_BLOCKED, {
                "reason": decision.reason,
                "fault_code": decision.fault_code,
                "ts": time.time(),
            })
            if decision.fault_code:
                self.bus.emit_error(decision.fault_code, decision.reason or "", level=1)
            return False

        # Apply state
        self.state.last_command_ts = cmd.ts
        self.state.is_started      = cmd.active
        self.state.is_autonom      = cmd.autonom
        self.state.active_mode     = cmd.mode
        self.state.engine_sound_enabled = cmd.engine_sound

        # Emergency stop check
        if self.interlock.emergency_stop_required(self.state):
            self.motor.stop_all()
            self.alarm.stop_all()
            self.light.all_off()
            self.bus.emit_error(FAULT_CODE_MOTOR_EMERGENCY_STOP, "Emergency stop triggered", level=2)
            return False

        # System off — stop all
        if not cmd.active:
            self.motor.stop_all()
            self.alarm.stop_all()
            self.light.all_off()
            return True

        # Apply lights
        self.light.apply_command(cmd)

        # Apply motor mode
        self._apply_motor_command(cmd)

        return True

    def _apply_motor_command(self, cmd: CommandPayload) -> None:
        mode = cmd.mode
        val  = cmd.val
        deadzone = self.cfg.safety.motor_deadzone_pct

        def deadzoned(v: float) -> float:
            return v if abs(v) > deadzone else 0.0

        speed = deadzoned(val)

        if mode == "WHEEL":
            self.motor.set_wheel(speed)
        elif mode == "DRIVER":
            self.motor.set_driver(speed)
            self.alarm.set_reverse_buzzer(val < -deadzone)
            if cmd.engine_sound:
                self.alarm.set_engine_sound(abs(speed))
            else:
                self.alarm.set_engine_sound(0)
        elif mode == "DRAWWORKS":
            self.motor.set_drawworks(speed)
            if cmd.engine_sound:
                self.alarm.set_engine_sound(abs(speed))
        elif mode == "SANDLINE":
            self.motor.set_sandline(speed)
        elif mode == "WINCH":
            self.motor.set_winch(speed)
        elif mode == "ROTARY TABLE":
            self.motor.set_rotary(speed)
        elif mode == "AUTONOM":
            # Autonomous mode: handled externally
            self.bus.emit(EVENT_MODE_CHANGED, {"mode": "AUTONOM", "val": val})
        else:
            self.motor.stop_all()
            self.alarm.set_engine_sound(0)

        self.bus.emit(EVENT_MOTOR_COMMAND, {"mode": mode, "val": val, "speed_applied": speed})

    def update_cooling_status(self, mc_state: str, rc_state: str) -> None:
        """Call when fan status is received from field bus / sensors."""
        self.state.mc_fan_state = mc_state if mc_state in VALID_COOLING_STATES else "COMM_LOST"
        self.state.rc_fan_state = rc_state if rc_state in VALID_COOLING_STATES else "COMM_LOST"
        self.bus.emit(EVENT_COOLING_STATUS_UPDATE, {
            "mc": self.state.mc_fan_state,
            "rc": self.state.rc_fan_state,
        })
        if "FAULT" in (self.state.mc_fan_state, self.state.rc_fan_state):
            self.bus.emit_error(FAULT_CODE_COOLING_FAULT,
                                f"Cooling fault — MC:{self.state.mc_fan_state} RC:{self.state.rc_fan_state}",
                                level=1)

    def get_status_snapshot(self) -> Dict[str, Any]:
        return {
            "ts":         time.time(),
            "fsm_state":  self.fsm.state,
            "state":      self.state.to_dict(),
            "remote_link_alive": self.watchdog.is_alive,
        }

    # ----------------------------------------------------------
    # BACKGROUND LOOPS
    # ----------------------------------------------------------
    def _spawn_loops(self) -> None:
        loops = [
            ("watchdog_loop",  self._watchdog_loop,  self.cfg.loops.control_interval),
            ("adc_loop",       self._adc_loop,       self.cfg.loops.adc_interval),
            ("telemetry_loop", self._telemetry_loop, self.cfg.loops.telemetry_interval),
        ]
        for name, fn, interval in loops:
            t = threading.Thread(target=fn, args=(interval,), name=name, daemon=True)
            t.start()
            self._threads.append(t)

    def _watchdog_loop(self, interval: float) -> None:
        while self._running:
            alive = self.watchdog.check()
            self.state.remote_link_alive = alive
            time.sleep(interval)

    def _adc_loop(self, interval: float) -> None:
        while self._running:
            try:
                v_master = self.adc.read_battery_master()
                v_remote = self.adc.read_battery_remote()
                self.state.batt_master_pct = self.adc.voltage_to_percent(v_master)
                self.state.batt_remote_pct = self.adc.voltage_to_percent(v_remote)
                self.bus.emit(EVENT_ADC_READING, {
                    "batt_master_v":   v_master,
                    "batt_remote_v":   v_remote,
                    "batt_master_pct": self.state.batt_master_pct,
                    "batt_remote_pct": self.state.batt_remote_pct,
                })
            except Exception as e:
                self.bus.emit_error(FAULT_CODE_ADC_READ_ERROR, str(e), level=1)
            time.sleep(interval)

    def _telemetry_loop(self, interval: float) -> None:
        while self._running:
            try:
                snapshot = self.get_status_snapshot()
                self.bus.emit(EVENT_TELEMETRY_SNAPSHOT, snapshot)
                self.transport.publish_status(snapshot)
            except Exception as e:
                print(f"[TelemetryLoop] Error: {e}")
            time.sleep(interval)


# =========================================================
# CORE — TELEMETRY ROTATION MANAGER  (MODULE-161)
# =========================================================
class TelemetryRotationManager:
    """
    Telemetry log rotation and disk safety manager for MasterPi.
    - Rotates JSONL log files when they exceed size threshold
    - Retains only a limited number of rotated files
    - Provides basic disk free-space safety checks
    """

    DEFAULT_MAX_FILE_SIZE_MB = 10
    DEFAULT_MIN_FREE_MB      = 100

    def __init__(
        self,
        log_dir: str = "logs",
        max_file_size_mb: float = DEFAULT_MAX_FILE_SIZE_MB,
        max_rotated_files: int = 10,
        min_free_mb: float = DEFAULT_MIN_FREE_MB,
    ):
        self._log_dir          = log_dir
        self._max_bytes        = int(max_file_size_mb * 1024 * 1024)
        self._max_rotated      = max_rotated_files
        self._min_free_bytes   = int(min_free_mb * 1024 * 1024)

    def check_and_rotate(self) -> List[str]:
        """
        Scan log_dir for oversized JSONL files, rotate them.
        Returns list of rotated file names.
        """
        rotated = []
        if not os.path.isdir(self._log_dir):
            return rotated
        for fname in os.listdir(self._log_dir):
            if not fname.endswith(".jsonl"):
                continue
            fpath = os.path.join(self._log_dir, fname)
            try:
                if os.path.getsize(fpath) >= self._max_bytes:
                    ts  = time.strftime("%Y%m%d_%H%M%S")
                    dst = fpath.replace(".jsonl", f"_{ts}.jsonl.bak")
                    os.rename(fpath, dst)
                    rotated.append(fname)
                    print(f"[RotationMgr] Rotated: {fname} → {os.path.basename(dst)}")
            except Exception as e:
                print(f"[RotationMgr] Rotate error {fname}: {e}")
        self._prune_old_backups()
        return rotated

    def _prune_old_backups(self) -> None:
        if not os.path.isdir(self._log_dir):
            return
        backups = sorted([
            f for f in os.listdir(self._log_dir)
            if f.endswith(".jsonl.bak")
        ])
        while len(backups) > self._max_rotated:
            victim = os.path.join(self._log_dir, backups.pop(0))
            try:
                os.remove(victim)
                print(f"[RotationMgr] Pruned: {os.path.basename(victim)}")
            except Exception as e:
                print(f"[RotationMgr] Prune error: {e}")

    def disk_safe(self) -> bool:
        """Returns True if free disk space is above minimum threshold."""
        try:
            import shutil
            free = shutil.disk_usage(self._log_dir).free
            return free >= self._min_free_bytes
        except Exception:
            return True  # assume safe if check fails

    def get_disk_status(self) -> Dict[str, Any]:
        try:
            import shutil
            usage = shutil.disk_usage(self._log_dir)
            return {
                "total_mb": usage.total / 1024 / 1024,
                "used_mb":  usage.used  / 1024 / 1024,
                "free_mb":  usage.free  / 1024 / 1024,
                "safe":     usage.free  >= self._min_free_bytes,
            }
        except Exception as e:
            return {"error": str(e), "safe": True}


# =========================================================
# INTEGRATION — UDP TRANSPORT DRIVER  (MODULE-162)
# =========================================================
class UDPTransportDriver:
    """
    UDP transport driver for RemotePi <-> MasterPi communication.
    Alternative to MQTT — lower latency, no broker required.

    - Receives JSON packets over UDP
    - Passes packets into MasterPiTransportAdapter logic
    - Sends ACK/NACK/STATUS responses back to sender
    """

    DEFAULT_HOST = "0.0.0.0"
    DEFAULT_PORT = 5005
    BUFFER_SIZE  = 4096

    def __init__(
        self,
        stack: "MasterPiHardwareRuntimeStack",
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
    ):
        self._stack   = stack
        self._host    = host
        self._port    = port
        self._sock: Optional[Any] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_sender: Optional[Tuple[str, int]] = None

    def start(self) -> None:
        import socket
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.settimeout(1.0)
        self._sock.bind((self._host, self._port))
        self._running = True
        self._thread  = threading.Thread(
            target=self._recv_loop, name="udp_recv", daemon=True
        )
        self._thread.start()
        print(f"[UDP] Listening on {self._host}:{self._port}")

    def _recv_loop(self) -> None:
        while self._running:
            try:
                data, addr = self._sock.recvfrom(self.BUFFER_SIZE)
                self._last_sender = addr
                self._handle(data.decode("utf-8", errors="ignore"), addr)
            except OSError:
                pass  # timeout — loop continues
            except Exception as e:
                print(f"[UDP] Recv error: {e}")

    def _handle(self, raw: str, addr: Tuple[str, int]) -> None:
        try:
            raw_dict = json.loads(raw)

            # Legacy flat payload (no packet_type)
            if "packet_type" not in raw_dict:
                cmd     = CommandPayload.from_dict(raw_dict)
                success = self._stack.dispatch_command(cmd)
                self._send_response(
                    TransportPacket(
                        packet_type=PACKET_TYPE_ACK if success else PACKET_TYPE_NACK,
                        payload={"ok": success},
                    ),
                    addr,
                )
                return

            pkt = TransportPacket.from_json(raw)
            if pkt.packet_type == PACKET_TYPE_HEARTBEAT:
                self._stack.watchdog.heartbeat(pkt.ts)
                self._send_response(
                    TransportPacket(packet_type=PACKET_TYPE_ACK, payload={"ok": True}),
                    addr,
                )
            elif pkt.packet_type == PACKET_TYPE_COMMAND:
                cmd     = CommandPayload.from_dict(pkt.payload)
                success = self._stack.dispatch_command(cmd)
                self._send_response(
                    TransportPacket(
                        packet_type=PACKET_TYPE_ACK if success else PACKET_TYPE_NACK,
                        payload={"ok": success},
                    ),
                    addr,
                )
        except Exception as e:
            print(f"[UDP] Handle error: {e}")

    def _send_response(self, pkt: TransportPacket, addr: Tuple[str, int]) -> None:
        if self._sock is None:
            return
        try:
            self._sock.sendto(pkt.to_json().encode("utf-8"), addr)
        except Exception as e:
            print(f"[UDP] Send error: {e}")

    def publish_status(self, status: Dict[str, Any]) -> None:
        """Push a STATUS packet to last known sender."""
        if self._sock is None or self._last_sender is None:
            return
        pkt = TransportPacket(packet_type=PACKET_TYPE_STATUS, payload=status)
        self._send_response(pkt, self._last_sender)

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
        print("[UDP] Stopped")


# =========================================================
# TOOLS — MASTERPI COMMISSIONING TOOL  (MODULE-163)
# =========================================================
@dataclass
class CommissionStepResult:
    name: str
    passed: bool
    detail: str = ""


class MasterPiCommissioningTool:
    """
    Hardware commissioning / field verification tool for MasterPi.
    - Quick field checks for critical subsystems
    - Validates that core outputs respond through runtime stack
    - Run before live operation
    """

    def __init__(self, stack: "MasterPiHardwareRuntimeStack"):
        self._stack = stack

    def run_all(self) -> List[CommissionStepResult]:
        results = []
        results += self._check_gpio_map()
        results += self._check_motor_ping()
        results += self._check_light_ping()
        results += self._check_adc_read()
        results += self._check_cooling_ping()
        results += self._check_fsm_state()
        self._print_report(results)
        return results

    def _check_gpio_map(self) -> List[CommissionStepResult]:
        conflicts = GPIOMap.validate_no_conflicts()
        if conflicts:
            return [CommissionStepResult("gpio_map", False, f"Conflicts: {conflicts}")]
        pin_count = len(GPIOMap.PINS)
        return [CommissionStepResult("gpio_map", True, f"{pin_count} pins, no conflicts")]

    def _check_motor_ping(self) -> List[CommissionStepResult]:
        results = []
        motors = [
            ("wheel",     lambda: self._stack.motor.set_wheel(10)),
            ("driver",    lambda: self._stack.motor.set_driver(10)),
            ("drawworks", lambda: self._stack.motor.set_drawworks(10)),
            ("sandline",  lambda: self._stack.motor.set_sandline(10)),
            ("winch",     lambda: self._stack.motor.set_winch(10)),
            ("rotary",    lambda: self._stack.motor.set_rotary(10)),
        ]
        for name, fn in motors:
            try:
                fn()
                time.sleep(0.1)
                self._stack.motor.stop_all()
                results.append(CommissionStepResult(f"motor_{name}", True, "pulse OK"))
            except Exception as e:
                results.append(CommissionStepResult(f"motor_{name}", False, str(e)))
        return results

    def _check_light_ping(self) -> List[CommissionStepResult]:
        results = []
        for key in VALID_LIGHT_KEYS:
            try:
                self._stack.light.set(key, True)
                time.sleep(0.05)
                self._stack.light.set(key, False)
                results.append(CommissionStepResult(f"light_{key}", True, "toggle OK"))
            except Exception as e:
                results.append(CommissionStepResult(f"light_{key}", False, str(e)))
        return results

    def _check_adc_read(self) -> List[CommissionStepResult]:
        results = []
        for ch in range(2):
            try:
                v = self._stack.adc.read_channel(ch)
                results.append(CommissionStepResult(f"adc_ch{ch}", True, f"{v:.3f}V"))
            except Exception as e:
                results.append(CommissionStepResult(f"adc_ch{ch}", False, str(e)))
        return results

    def _check_cooling_ping(self) -> List[CommissionStepResult]:
        results = []
        try:
            self._stack.cooling.set_mc_fan(50)
            self._stack.cooling.set_rc_fan(50)
            time.sleep(0.1)
            self._stack.cooling.stop_all()
            results.append(CommissionStepResult("cooling_fans", True, "50% pulse OK"))
        except Exception as e:
            results.append(CommissionStepResult("cooling_fans", False, str(e)))
        return results

    def _check_fsm_state(self) -> List[CommissionStepResult]:
        state = self._stack.fsm.state
        ok = state == FSM_STATE_RUNNING
        return [CommissionStepResult("fsm_state", ok, f"FSM={state}")]

    @staticmethod
    def _print_report(results: List[CommissionStepResult]) -> None:
        print("\n" + "=" * 50)
        print("MASTERPI COMMISSIONING REPORT")
        print("=" * 50)
        passed = sum(1 for r in results if r.passed)
        for r in results:
            icon = "✓" if r.passed else "✗"
            print(f"  [{icon}] {r.name:<28} {r.detail}")
        print("-" * 50)
        print(f"  Result: {passed}/{len(results)} passed")
        print("=" * 50 + "\n")


# =========================================================
# TOOLS — THERMAL LIVE CALIBRATION UTILITY  (MODULE-164)
# =========================================================
@dataclass
class ThermalCalibrationProfile:
    """
    Thermal calibration profile for MasterPi cooling system.
    Maps temperature readings to fan duty cycle percentages.
    """
    mc_temp_min_c: float = 30.0
    mc_temp_max_c: float = 75.0
    mc_fan_min_pct: float = 20.0
    mc_fan_max_pct: float = 100.0
    rc_temp_min_c: float = 30.0
    rc_temp_max_c: float = 70.0
    rc_fan_min_pct: float = 20.0
    rc_fan_max_pct: float = 100.0
    overheat_threshold_c: float = 80.0

    def mc_duty_for_temp(self, temp_c: float) -> float:
        return self._interpolate(
            temp_c,
            self.mc_temp_min_c, self.mc_temp_max_c,
            self.mc_fan_min_pct, self.mc_fan_max_pct,
        )

    def rc_duty_for_temp(self, temp_c: float) -> float:
        return self._interpolate(
            temp_c,
            self.rc_temp_min_c, self.rc_temp_max_c,
            self.rc_fan_min_pct, self.rc_fan_max_pct,
        )

    @staticmethod
    def _interpolate(
        val: float,
        in_min: float, in_max: float,
        out_min: float, out_max: float,
    ) -> float:
        if val <= in_min:
            return out_min
        if val >= in_max:
            return out_max
        return out_min + (val - in_min) / (in_max - in_min) * (out_max - out_min)

    def is_overheat(self, temp_c: float) -> bool:
        return temp_c >= self.overheat_threshold_c


class ThermalLiveCalibrationUtility:
    """
    Live calibration utility for MasterPi thermal management.
    Run interactively or via script to tune thermal profiles.
    """

    def __init__(
        self,
        stack: "MasterPiHardwareRuntimeStack",
        profile: Optional[ThermalCalibrationProfile] = None,
    ):
        self._stack   = stack
        self._profile = profile or ThermalCalibrationProfile()

    def apply_thermal_control(self, mc_temp_c: float, rc_temp_c: float) -> Dict[str, Any]:
        """
        Apply fan duty based on current temperatures.
        Call this periodically from a monitoring loop.
        """
        mc_duty = self._profile.mc_duty_for_temp(mc_temp_c)
        rc_duty = self._profile.rc_duty_for_temp(rc_temp_c)

        self._stack.cooling.set_mc_fan(mc_duty)
        self._stack.cooling.set_rc_fan(rc_duty)

        mc_state = "ON"
        rc_state = "ON"

        if self._profile.is_overheat(mc_temp_c):
            mc_state = "FAULT"
            self._stack.bus.emit_error(
                FAULT_CODE_COOLING_FAULT,
                f"MC overheat: {mc_temp_c:.1f}°C",
                level=2,
            )
        if self._profile.is_overheat(rc_temp_c):
            rc_state = "FAULT"
            self._stack.bus.emit_error(
                FAULT_CODE_COOLING_FAULT,
                f"RC overheat: {rc_temp_c:.1f}°C",
                level=2,
            )

        self._stack.update_cooling_status(mc_state, rc_state)

        return {
            "mc_temp_c": mc_temp_c, "mc_duty_pct": mc_duty, "mc_state": mc_state,
            "rc_temp_c": rc_temp_c, "rc_duty_pct": rc_duty, "rc_state": rc_state,
        }

    def interactive_tune(self) -> None:
        """CLI tool — interactive profile tuning loop."""
        print("\n[ThermalCal] Live Calibration — type 'q' to quit")
        while True:
            try:
                raw = input("mc_temp rc_temp > ").strip()
                if raw.lower() == "q":
                    break
                parts = raw.split()
                if len(parts) != 2:
                    print("  Usage: <mc_temp_c> <rc_temp_c>")
                    continue
                mc_t = float(parts[0])
                rc_t = float(parts[1])
                result = self.apply_thermal_control(mc_t, rc_t)
                print(
                    f"  MC: {mc_t:.1f}°C → {result['mc_duty_pct']:.1f}% [{result['mc_state']}]  "
                    f"RC: {rc_t:.1f}°C → {result['rc_duty_pct']:.1f}% [{result['rc_state']}]"
                )
            except (KeyboardInterrupt, EOFError):
                break
            except ValueError:
                print("  Invalid input")
        print("[ThermalCal] Exiting")


# =========================================================
# FULL SYSTEM — MAIN CONTROLLER  (Modül-86)
# =========================================================
class FullSystemMainController:
    """
    MasterPi full system main controller.
    Tüm runtime katmanlarını, transport'u, UDP driver'ı,
    thermal yönetimi ve commissioning aracını tek ana
    kontrol döngüsünde birleştirir.
    """

    def __init__(self, config_path: Optional[str] = None, use_udp: bool = False):
        self.stack       = MasterPiHardwareRuntimeStack(config_path=config_path)
        self.rotation_mgr = TelemetryRotationManager(
            log_dir=self.stack.cfg.hardware.telemetry_log_dir
        )
        self.thermal     = ThermalLiveCalibrationUtility(self.stack)
        self.commissioning = MasterPiCommissioningTool(self.stack)
        self._use_udp    = use_udp
        self._udp: Optional[UDPTransportDriver] = None
        self._running    = False

    def run(self) -> None:
        import signal

        def on_signal(sig, frame):
            print("\n[FullSystem] Shutdown signal received")
            self._running = False

        signal.signal(signal.SIGINT,  on_signal)
        signal.signal(signal.SIGTERM, on_signal)

        print("[FullSystem] Starting MasterPi...")

        if not self.stack.start():
            print("[FullSystem] Stack startup failed — aborting")
            return

        # Optional UDP transport alongside MQTT
        if self._use_udp:
            self._udp = UDPTransportDriver(self.stack)
            self._udp.start()

        # Run commissioning check before going live
        self.commissioning.run_all()

        self._running = True
        print("[FullSystem] MasterPi is LIVE. Press Ctrl+C to stop.")

        _rotation_tick = 0
        while self._running:
            time.sleep(1)
            _rotation_tick += 1

            # Log rotation every 60 seconds
            if _rotation_tick % 60 == 0:
                self.rotation_mgr.check_and_rotate()
                if not self.rotation_mgr.disk_safe():
                    self.stack.bus.emit_error(
                        FAULT_CODE_SOFTWARE_ERROR,
                        "Disk space low — telemetry may be lost",
                        level=1,
                    )

        self._shutdown()

    def _shutdown(self) -> None:
        print("[FullSystem] Shutting down...")
        if self._udp:
            self._udp.stop()
        self.stack.stop()
        print("[FullSystem] Done.")


# =========================================================
# FULL SYSTEM — BOOT ENTRY  (Modül-87)
# =========================================================
def main() -> None:
    """
    MasterPi sisteminin gerçek saha çalıştırma giriş noktası.
    Linux systemd / manuel terminal / servis launcher buraya çağırır.

    Ortam değişkenleri:
      MASTERPI_CONFIG   — config JSON dosyası yolu (opsiyonel)
      MASTERPI_UDP      — "1" ise UDP transport da başlatılır
    """
    config_path = os.environ.get("MASTERPI_CONFIG", None)
    use_udp     = os.environ.get("MASTERPI_UDP", "0") == "1"

    controller = FullSystemMainController(config_path=config_path, use_udp=use_udp)
    controller.run()


# =========================================================
# ENTRY POINT
# =========================================================
if __name__ == "__main__":
    main()