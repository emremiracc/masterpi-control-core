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
# MQTT TOPICS  (MasterPi ile senkron — değiştirme)
# =========================================================
MQTT_BROKER_IP       = "192.168.1.100"   # MasterPi IP — gerekirse değiştir
MQTT_TOPIC_CONTROL   = "remotepi/control"   # RemotePi → MasterPi
MQTT_TOPIC_STATUS    = "masterpi/status"    # MasterPi → RemotePi

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
            text=self.title, size_hint_y=None, height=30,
            font_size="18sp", bold=True, color=(0, 0.8, 1, 1)
        )
        main_layout.add_widget(lbl_title)
        self.txt_input = TextInput(multiline=False, size_hint_y=None, height=40, font_size="20sp")
        main_layout.add_widget(self.txt_input)
        keys_layout = GridLayout(cols=12, spacing=5)
        row1 = ["q","w","e","r","t","y","u","ı","o","p","ğ","ü"]
        row2 = ["a","s","d","f","g","h","j","k","l","ş","i",","]
        row3 = ["z","x","c","v","b","n","m","ö","ç",".","@","-"]
        for key in row1 + row2 + row3:
            btn = Button(text=key, font_size="18sp", bold=True)
            btn.bind(on_release=self.add_char)
            keys_layout.add_widget(btn)
        main_layout.add_widget(keys_layout)
        bottom_layout = BoxLayout(orientation="horizontal", size_hint_y=None, height=50, spacing=10)
        btn_backspace = Button(text="SIL", size_hint_x=0.2, background_color=(1, 0.3, 0.3, 1))
        btn_backspace.bind(on_release=self.backspace)
        btn_space = Button(text="BOSLUK", size_hint_x=0.4)
        btn_space.bind(on_release=lambda x: self.add_char(x, " "))
        btn_cancel = Button(text="IPTAL", size_hint_x=0.2, background_color=(0.5, 0.5, 0.5, 1))
        btn_cancel.bind(on_release=self.dismiss)
        btn_connect = Button(text="BAGLAN", size_hint_x=0.2, background_color=(0, 1, 0, 1))
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
            f"sudo iwlist {wifi_interface} scan", shell=True
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
        output = subprocess.check_output("hcitool scan", shell=True).decode("utf-8", errors="ignore")
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
    """
    RemotePi MQTT yöneticisi.
    - remotepi/control  → MasterPi'ye komut gönderir (publish)
    - masterpi/status   → MasterPi'den durum alır (subscribe)
    """
    def __init__(self, broker_ip=MQTT_BROKER_IP, on_master_status=None):
        self.client = None
        self.broker_ip = broker_ip
        self.connected = False
        self.on_master_status = on_master_status  # callback: masterpi/status geldiğinde
        if mqtt is not None:
            try:
                self.client = mqtt.Client(client_id="RemotePi_HMI")
                self.client.on_connect    = self._on_connect
                self.client.on_disconnect = self._on_disconnect
                self.client.on_message    = self._on_message
            except Exception:
                self.client = None
        if self.client:
            self.connect()

    def connect(self):
        try:
            self.client.connect(self.broker_ip, 1883, 60)
            self.client.loop_start()
            self.connected = True
            print(f"[MQTT] Connecting to {self.broker_ip}")
        except Exception as e:
            self.connected = False
            print(f"[MQTT] Connection Error: {e}")

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connected = True
            # MasterPi'den gelen durum mesajlarını dinle
            client.subscribe(MQTT_TOPIC_STATUS)
            print(f"[MQTT] Connected. Subscribed to {MQTT_TOPIC_STATUS}")
        else:
            self.connected = False
            print(f"[MQTT] Connect failed rc={rc}")

    def _on_disconnect(self, client, userdata, rc):
        self.connected = False
        print(f"[MQTT] Disconnected rc={rc}")

    def _on_message(self, client, userdata, msg):
        """masterpi/status mesajı geldiğinde çağrılır."""
        try:
            raw = msg.payload.decode("utf-8")
            data = json.loads(raw)
            # packet_type wrapper varsa payload'u al
            if "packet_type" in data and "payload" in data:
                data = data["payload"]
            if self.on_master_status:
                Clock.schedule_once(lambda dt: self.on_master_status(data), 0)
        except Exception as e:
            print(f"[MQTT] Message parse error: {e}")

    def publish_control(self, payload: dict):
        if not self.client or not self.connected:
            return
        try:
            self.client.publish(MQTT_TOPIC_CONTROL, json.dumps(payload), qos=0)
        except Exception as e:
            print(f"[MQTT] Publish Error: {e}")

# =========================================================
# HARDWARE MANAGER
# =========================================================
class HardwareManager:
    def __init__(self):
        self.sim_counter = 0.0
        self.PIN_REV_BUZZER    = 20
        self.PIN_REV_LED       = 26
        self.PIN_ENGINE_BUZZER = 18
        self.PIN_SIG_LEFT      = 23
        self.PIN_SIG_RIGHT     = 24
        self.PIN_PARKING_LIGHT  = 5
        self.PIN_LOW_BEAM_LIGHT = 6
        self.PIN_HIGH_BEAM_LIGHT = 13
        self.PIN_RIG_FLOOR_LIGHT = 19
        self.PIN_ROTATION_LIGHT  = 21
        self.GPIO = None
        self.gpio_available = False
        self.pwm_engine = None
        try:
            import RPi.GPIO as GPIO
            self.GPIO = GPIO
            self.GPIO.setmode(GPIO.BCM)
            self.GPIO.setwarnings(False)
            outputs = [
                self.PIN_REV_BUZZER, self.PIN_REV_LED,
                self.PIN_SIG_LEFT, self.PIN_SIG_RIGHT,
                self.PIN_PARKING_LIGHT, self.PIN_LOW_BEAM_LIGHT,
                self.PIN_HIGH_BEAM_LIGHT, self.PIN_RIG_FLOOR_LIGHT,
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
            Label(text="Kart Algilaniyor ve Taraniyor...", size_hint_y=None, height=40, color=(1, 1, 1, 1))
        )
        threading.Thread(target=self._scan_thread, daemon=True).start()

    def _scan_thread(self):
        time.sleep(0.5)
        networks = get_wifi_networks()
        Clock.schedule_once(lambda dt: self._update_list(networks), 0)

    def _update_list(self, networks):
        self.ids.list_layout.clear_widgets()
        if not networks:
            self.ids.list_layout.add_widget(Label(text="Hicbir Ag Bulunamadi!", size_hint_y=None, height=40))
            return
        for ssid in networks:
            if "HATASI" in ssid or "Hata" in ssid:
                btn = Button(text=ssid, size_hint_y=None, height=50, background_color=(1, 0, 0, 1))
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
            Label(text=f"'{ssid}' agina baglaniliyor...", color=(0, 1, 0, 1))
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
            self.ids.list_layout.add_widget(Label(text="BT Cihaz Yok", size_hint_y=None, height=40))
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
            Label(text=f"'{dev_name}' ile eslesiliyor...", color=(0, 1, 0, 1))
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
#:import dp kivy.metrics.dp

<TextButton@ToggleButtonBehavior+Label>:
    font_size: "18sp"
    bold: True
    halign: "center"
    valign: "middle"
    text_size: self.size
    color: (1.00, 0.55, 0.15, 1) if self.state == "down" else (1, 1, 1, 1)
    canvas.before:
        Color:
            rgba: (0.20, 0.68, 1.00, 0.55) if self.state == "normal" else (1.00, 0.55, 0.15, 0.55)
        RoundedRectangle:
            pos: (self.x - dp(5), self.y - dp(5))
            size: (self.width + dp(10), self.height + dp(10))
            radius: [dp(14)]
        Color:
            rgba: (0.20, 0.68, 1.00, 0.14) if self.state == "normal" else (1.00, 0.55, 0.15, 0.14)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(12)]
        Color:
            rgba: (.25, .27, .30, 1)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(12)]
        Color:
            rgba: (1, 1, 1, 0.06)
        RoundedRectangle:
            pos: (self.x, self.y + self.height * 0.55)
            size: (self.width, self.height * 0.45)
            radius: [dp(12)]

<FaultButton>:
    font_size: "18sp"
    bold: True
    halign: "center"
    valign: "middle"
    text_size: self.size
    color: (1, 1, 1, 1)
    canvas.before:
        Color:
            rgba: (1.00, 0.20, 0.20, (0.65 if app.fault_blink_on else 0.12)) if app.fault_level == 2 else (1.00, 0.20, 0.20, 0.55) if app.fault_level == 1 else (0.20, 1.00, 0.20, 0.55)
        RoundedRectangle:
            pos: (self.x - dp(5), self.y - dp(5))
            size: (self.width + dp(10), self.height + dp(10))
            radius: [dp(14)]
        Color:
            rgba: (1.00, 0.20, 0.20, (0.18 if app.fault_blink_on else 0.06)) if app.fault_level == 2 else (1.00, 0.20, 0.20, 0.14) if app.fault_level == 1 else (0.20, 1.00, 0.20, 0.14)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(12)]
        Color:
            rgba: (.25, .27, .30, 1)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(12)]

<IconToggle>:
    canvas.before:
        Color:
            rgba: (1.00, 0.55, 0.15, 0.55) if self.state == "down" else (0, 0, 0, 0)
        RoundedRectangle:
            pos: (self.x - dp(6), self.y - dp(6))
            size: (self.width + dp(12), self.height + dp(12))
            radius: [dp(12)]
        Color:
            rgba: (1.00, 0.55, 0.15, 0.14) if self.state == "down" else (0, 0, 0, 0)
        RoundedRectangle:
            pos: (self.x - dp(3), self.y - dp(3))
            size: (self.width + dp(6), self.height + dp(6))
            radius: [dp(10)]

# ---------------------------------------------------------
# COOLING STATUS INDICATOR  (STATUS only - no EVT)
# State string: "ON" | "OFF" | "FAULT" | "COMM_LOST"
# ON=Green  OFF=Red  FAULT=Amber  COMM_LOST=Gray
# ---------------------------------------------------------
<CoolingStatusIcon@Widget>:
    label_text: "??"
    state_str: "COMM_LOST"
    size_hint: None, None
    size: dp(58), dp(58)
    canvas.before:
        Color:
            rgba: (0.10, 0.11, 0.13, 1)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(10)]
        Color:
            rgba: (0.0, 0.75, 0.2, 0.35) if self.state_str == "ON" else (0.85, 0.08, 0.08, 0.35) if self.state_str == "OFF" else (1.0, 0.55, 0.0, 0.35) if self.state_str == "FAULT" else (0.4, 0.4, 0.4, 0.25)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(10)]
        Color:
            rgba: (0.0, 0.90, 0.25, 1) if self.state_str == "ON" else (0.95, 0.15, 0.15, 1) if self.state_str == "OFF" else (1.0, 0.60, 0.0, 1) if self.state_str == "FAULT" else (0.55, 0.55, 0.55, 1)
        Line:
            rounded_rectangle: (self.x + dp(2), self.y + dp(2), self.width - dp(4), self.height - dp(4), dp(8))
            width: dp(2.5)
    Label:
        text: root.label_text
        font_size: "20sp"
        bold: True
        color: (0.0, 1.0, 0.35, 1) if root.state_str == "ON" else (1.0, 0.35, 0.35, 1) if root.state_str == "OFF" else (1.0, 0.72, 0.0, 1) if root.state_str == "FAULT" else (0.75, 0.75, 0.75, 1)
        halign: "center"
        valign: "middle"
        pos: (root.x, root.y)
        size: (root.width, root.height)

<WifiUI>:
    name: "wifi"
    canvas.before:
        Color:
            rgba: 0.08, 0.09, 0.11, 1
        Rectangle:
            pos: self.pos
            size: self.size
    BoxLayout:
        orientation: "vertical"
        padding: dp(20)
        spacing: dp(10)
        Label:
            text: "KULLANILABILIR WI-FI AGLARI"
            font_size: "20sp"
            bold: True
            color: (0, 0.8, 1, 1)
            size_hint_y: None
            height: dp(50)
        ScrollView:
            BoxLayout:
                id: list_layout
                orientation: "vertical"
                size_hint_y: None
                height: self.minimum_height
                spacing: dp(5)
        TextButton:
            text: "GERI"
            size_hint_y: None
            height: dp(60)
            on_release: app.close_top_screen()

<BluetoothUI>:
    name: "bluetooth"
    canvas.before:
        Color:
            rgba: 0.08, 0.09, 0.11, 1
        Rectangle:
            pos: self.pos
            size: self.size
    BoxLayout:
        orientation: "vertical"
        padding: dp(20)
        spacing: dp(10)
        Label:
            text: "BLUETOOTH CIHAZLAR"
            font_size: "20sp"
            bold: True
            color: (0, 0.4, 1, 1)
            size_hint_y: None
            height: dp(50)
        ScrollView:
            BoxLayout:
                id: list_layout
                orientation: "vertical"
                size_hint_y: None
                height: self.minimum_height
                spacing: dp(5)
        TextButton:
            text: "GERI"
            size_hint_y: None
            height: dp(60)
            on_release: app.close_top_screen()

<BatteryUI>:
    name: "battery"
    canvas.before:
        Color:
            rgba: 0.08, 0.09, 0.11, 1
        Rectangle:
            pos: self.pos
            size: self.size
    BoxLayout:
        orientation: "vertical"
        padding: dp(40)
        spacing: dp(30)
        Label:
            text: "BATARYA DURUMU"
            font_size: "24sp"
            bold: True
            color: (0, 0.8, 1, 1)
            size_hint_y: None
            height: dp(50)
        BoxLayout:
            orientation: "vertical"
            size_hint_y: None
            height: dp(80)
            spacing: dp(5)
            Label:
                text: "Ana Batarya (Master): " + str(int(app.batt_m_level)) + "%"
                font_size: "18sp"
                halign: "left"
                text_size: self.size
                color: (1, 1, 1, 1)
            BoxLayout:
                size_hint_y: None
                height: dp(30)
                canvas:
                    Color:
                        rgba: 0.2, 0.2, 0.2, 1
                    RoundedRectangle:
                        pos: self.pos
                        size: self.size
                        radius: [dp(5)]
                    Color:
                        rgba: (0, 1, 0, 1) if app.batt_m_level > 50 else (1, 1, 0, 1) if app.batt_m_level > 20 else (1, 0, 0, 1)
                    RoundedRectangle:
                        pos: self.pos
                        size: (self.width * (app.batt_m_level / 100.0), self.height)
                        radius: [dp(5)]
        BoxLayout:
            orientation: "vertical"
            size_hint_y: None
            height: dp(80)
            spacing: dp(5)
            Label:
                text: "Kumanda Bataryasi (Remote): " + str(int(app.batt_r_level)) + "%"
                font_size: "18sp"
                halign: "left"
                text_size: self.size
                color: (1, 1, 1, 1)
            BoxLayout:
                size_hint_y: None
                height: dp(30)
                canvas:
                    Color:
                        rgba: 0.2, 0.2, 0.2, 1
                    RoundedRectangle:
                        pos: self.pos
                        size: self.size
                        radius: [dp(5)]
                    Color:
                        rgba: (0, 1, 0, 1) if app.batt_r_level > 50 else (1, 1, 0, 1) if app.batt_r_level > 20 else (1, 0, 0, 1)
                    RoundedRectangle:
                        pos: self.pos
                        size: (self.width * (app.batt_r_level / 100.0), self.height)
                        radius: [dp(5)]
        Widget:
        TextButton:
            text: "GERI"
            size_hint_y: None
            height: dp(60)
            on_release: app.close_top_screen()

<RootUI>:
    name: "home"
    canvas.before:
        Color:
            rgba: 0.06, 0.07, 0.09, 1
        Rectangle:
            pos: self.pos
            size: self.size
    Image:
        source: "assets/bg_texture.png"
        allow_stretch: True
        keep_ratio: False
        pos: root.pos
        size: root.size
        opacity: 1
    BoxLayout:
        orientation: "vertical"
        pos: root.pos
        size: root.size

        # ---- TOP BAR ----
        FloatLayout:
            size_hint_y: None
            height: dp(52)
            Label:
                text: "OPERATIONAL CONTROLS"
                color: .75,.75,.75,1
                font_size: "12sp"
                bold: True
                size_hint: None, 1
                width: dp(250)
                text_size: self.size
                halign: "left"
                valign: "middle"
                pos_hint: {"x": 0.04, "center_y": 0.5}
            BoxLayout:
                size_hint: None, None
                size: dp(150), dp(40)
                spacing: dp(12)
                pos_hint: {"center_x": 0.5, "center_y": 0.5}
                IconToggle:
                    id: bt_icon
                    icon_name: "bluetooth"
                    source: "assets/icons/bluetooth.png"
                    size_hint: None, None
                    size: dp(32), dp(32)
                    on_release: app.on_top_icon(self)
                IconToggle:
                    id: wifi_icon
                    icon_name: "wifi"
                    source: "assets/icons/wifi.png"
                    size_hint: None, None
                    size: dp(32), dp(32)
                    on_release: app.on_top_icon(self)
                IconToggle:
                    id: batt_icon
                    icon_name: "battery"
                    source: "assets/icons/battery.png"
                    size_hint: None, None
                    size: dp(40), dp(24)
                    on_release: app.on_top_icon(self)

        # ---- MAIN CONTENT ROW ----
        BoxLayout:
            size_hint_y: None
            height: dp(425)
            padding: dp(18), dp(12)
            spacing: dp(18)

            # LEFT PANEL
            BoxLayout:
                id: left_panel
                orientation: "vertical"
                size_hint_x: None
                width: dp(240)
                spacing: dp(12)
                TextButton:
                    text: "WHEEL"
                    on_release: app.on_btn(self, "WHEEL")
                TextButton:
                    text: "DRIVER"
                    on_release: app.on_btn(self, "DRIVER")
                TextButton:
                    text: "DRAWWORKS"
                    on_release: app.on_btn(self, "DRAWWORKS")
                TextButton:
                    text: "SANDLINE"
                    on_release: app.on_btn(self, "SANDLINE")
                TextButton:
                    text: "WINCH"
                    on_release: app.on_btn(self, "WINCH")
                TextButton:
                    text: "ROTARY TABLE"
                    on_release: app.on_btn(self, "ROTARY TABLE")
                TextButton:
                    text: "AUTONOM"
                    on_release: app.on_btn(self, "AUTONOM")
                TextButton:
                    text: "MENU"
                    on_release: app.on_btn(self, "MENU")

            # CENTER FLOAT
            FloatLayout:
                Image:
                    source: "assets/orhan_cakir.png"
                    allow_stretch: True
                    keep_ratio: True
                    size_hint: None, None
                    size: dp(460), dp(310)
                    pos_hint: {"center_x": .5, "center_y": .52}
                Widget:
                    size_hint: None, None
                    size: dp(92), dp(92)
                    pos_hint: {"center_x": .5, "center_y": .16}
                    canvas.before:
                        Color:
                            rgba: (1.0, 0.55, 0.15, 0.14)
                        RoundedRectangle:
                            pos: (self.x - dp(2), self.y - dp(2))
                            size: (self.width + dp(4), self.height + dp(4))
                            radius: [dp(18)]
                        Color:
                            rgba: (.16, .18, .21, 0.92)
                        RoundedRectangle:
                            pos: self.pos
                            size: self.size
                            radius: [dp(16)]
                IconToggle:
                    id: cam_icon
                    icon_name: "camera"
                    source: "assets/camera.png"
                    allow_stretch: True
                    keep_ratio: True
                    size_hint: None, None
                    size: dp(70), dp(70)
                    pos_hint: {"center_x": .5, "center_y": .16}
                    on_release: app.open_camera()
                CoolingStatusIcon:
                    id: mc_cooling_icon
                    label_text: "MC"
                    state_str: app.mc_fan_state
                    pos_hint: {"right": 0.28, "center_y": .16}
                CoolingStatusIcon:
                    id: rc_cooling_icon
                    label_text: "RC"
                    state_str: app.rc_fan_state
                    pos_hint: {"x": 0.72, "center_y": .16}

            # RIGHT PANEL
            BoxLayout:
                id: right_panel
                orientation: "vertical"
                size_hint_x: None
                width: dp(240)
                spacing: dp(12)
                TextButton:
                    text: "START / STOP"
                    on_release: app.on_btn(self, "START_STOP")
                TextButton:
                    text: "PARKING LIGHT"
                    on_release: app.on_btn(self, "PARKING LIGHT")
                TextButton:
                    text: "LOW BEAM LIGHT"
                    on_release: app.on_btn(self, "LOW BEAM LIGHT")
                TextButton:
                    text: "HIGH BEAM LIGHT"
                    on_release: app.on_btn(self, "HIGH BEAM LIGHT")
                TextButton:
                    text: "SIGNAL(LHR)LIGHT"
                    on_release: app.on_btn(self, "SIGNAL(LHR)LIGHT")
                TextButton:
                    text: "RIG FLOOR LIGHT"
                    on_release: app.on_btn(self, "RIG FLOOR LIGHT")
                TextButton:
                    text: "ROTATION LIGHT"
                    on_release: app.on_btn(self, "ROTATION LIGHT")
                FaultButton:
                    text: "FAULT"
                    on_release: app.on_fault()

<CameraUI>:
    name: "camera"
    canvas.before:
        Color:
            rgba: 0.03, 0.04, 0.06, 1
        Rectangle:
            pos: self.pos
            size: self.size
    FloatLayout:
        Image:
            id: cam_view
            allow_stretch: True
            keep_ratio: True
            size_hint: None, None
            size: dp(760), dp(390)
            pos_hint: {"center_x": 0.5, "top": 0.98}
        BoxLayout:
            size_hint: None, None
            size: dp(760), dp(70)
            spacing: dp(14)
            pos_hint: {"center_x": 0.5, "y": 0.03}
            TextButton:
                text: "GERI"
                group: "camgrp"
                on_release: app.close_camera()
            TextButton:
                text: "FOTO"
                group: "camgrp"
                on_release: app.take_photo()
            TextButton:
                text: "KAYIT"
                group: "camgrp"
                on_release: app.toggle_record()
        Label:
            text: "KAYITTA" if root.recording else ""
            color: (1, 0.35, 0.35, 1)
            bold: True
            font_size: "18sp"
            pos_hint: {"right": 0.98, "top": 0.98}

<FaultUI>:
    name: "faults"
    canvas.before:
        Color:
            rgba: 0.03, 0.04, 0.06, 1
        Rectangle:
            pos: self.pos
            size: self.size
    BoxLayout:
        orientation: "vertical"
        padding: dp(18), dp(12)
        spacing: dp(12)
        BoxLayout:
            size_hint_y: None
            height: dp(52)
            spacing: dp(12)
            Label:
                text: "ARIZALAR"
                color: (0.9, 0.9, 0.9, 1)
                font_size: "20sp"
                bold: True
                halign: "left"
                valign: "middle"
                text_size: self.size
            TextButton:
                text: "SIFIRLA"
                group: "faultgrp"
                size_hint_x: None
                width: dp(180)
                on_release: app.reset_recovery()
            TextButton:
                text: "GERI"
                group: "faultgrp"
                size_hint_x: None
                width: dp(180)
                on_release: app.close_faults()
        Label:
            text: app.system_status
            color: (0.8, 0.8, 0.8, 1)
            font_size: "14sp"
            halign: "left"
            valign: "middle"
            text_size: (self.width, None)
            size_hint_y: None
            height: dp(22)
        ScrollView:
            do_scroll_x: False
            Label:
                text: app.fault_text
                color: (0.85, 0.85, 0.85, 1)
                font_size: "16sp"
                halign: "left"
                valign: "top"
                text_size: (self.width, None)
                size_hint_y: None
                height: self.texture_size[1] + dp(20)
"""

# =========================================================
# MAIN APP
# =========================================================
class RemotePiHMIApp(App):
    # Fault system
    fault_level     = NumericProperty(0)
    fault_blink_on  = BooleanProperty(True)
    fault_messages  = ListProperty([])
    fault_text      = StringProperty("Ariza Yok.")
    system_status   = StringProperty("Hazir.")

    # System state
    is_system_started   = BooleanProperty(False)
    is_autonom_active   = BooleanProperty(False)
    active_mode         = StringProperty(None, allownone=True)
    engine_sound_enabled = BooleanProperty(True)
    parking_light_on    = BooleanProperty(False)
    low_beam_on         = BooleanProperty(False)
    high_beam_on        = BooleanProperty(False)
    signal_lhr_on       = BooleanProperty(False)
    rig_floor_light_on  = BooleanProperty(False)
    rotation_light_on   = BooleanProperty(False)

    # Battery
    batt_m_level = NumericProperty(100)
    batt_r_level = NumericProperty(100)

    # Cooling status — MasterPi'den MQTT ile güncellenir
    mc_fan_state = StringProperty("COMM_LOST")
    rc_fan_state = StringProperty("COMM_LOST")

    # Recovery
    _recovery_in_progress = BooleanProperty(False)
    _recovery_ev = None

    # Joystick button tracking
    _left_btn_press_ts  = None
    _left_btn_long_fired = False
    _right_btn_prev     = False
    _left_btn_prev      = False

    SAFETY_MAP = {
        "WHEEL":        {"side": "LEFT",  "axis": "X"},
        "DRIVER":       {"side": "RIGHT", "axis": "Y"},
        "DRAWWORKS":    {"side": "RIGHT", "axis": "Y"},
        "SANDLINE":     {"side": "LEFT",  "axis": "Y"},
        "WINCH":        {"side": "LEFT",  "axis": "X"},
        "ROTARY TABLE": {"side": "LEFT",  "axis": "Y"},
    }
    SAFETY_DEADZONE = 5

    def build(self):
        self.title = "RemotePiHMI"
        Builder.load_string(KV)
        self.sm           = ScreenManager()
        self.home         = RootUI()
        self.cam          = CameraUI()
        self.faults       = FaultUI()
        self.battery_ui   = BatteryUI()
        self.wifi_ui      = WifiUI()
        self.bluetooth_ui = BluetoothUI()
        self.sm.add_widget(self.home)
        self.sm.add_widget(self.cam)
        self.sm.add_widget(self.faults)
        self.sm.add_widget(self.battery_ui)
        self.sm.add_widget(self.wifi_ui)
        self.sm.add_widget(self.bluetooth_ui)

        # MQTT — MasterPi status callback bağlı
        self.mqtt = MQTTManager(
            broker_ip=MQTT_BROKER_IP,
            on_master_status=self._on_master_status,
        )

        self._cap        = None
        self._frame      = None
        self._update_ev  = None
        self._recording  = False
        self._writer     = None
        self._rec_path   = None
        self._out_dir    = os.path.join("assets", "captures")
        os.makedirs(self._out_dir, exist_ok=True)
        self._cam_icon   = None
        self._batt_icon  = None
        self._wifi_icon  = None
        self._bt_icon    = None

        Clock.schedule_once(self._grab_home_ids, 0)
        Clock.schedule_interval(self._fault_blink_tick, 0.5)
        Clock.schedule_interval(self.update_control_loop, 0.05)
        Clock.schedule_interval(self._update_batteries, 5.0)
        Clock.schedule_interval(self._poll_joystick_buttons, 0.05)
        return self.sm

    # =====================================================
    # MASTERPI STATUS HANDLER  ← YENİ EKLENEN ENTEGRASYON
    # masterpi/status topic'inden gelen veriyi işler
    # =====================================================
    def _on_master_status(self, data: dict):
        """
        MasterPi'den gelen status snapshot'ını işler.
        Güncellenen alanlar:
          - state.mc_fan_state  → MC cooling ikonu
          - state.rc_fan_state  → RC cooling ikonu
          - state.batt_master_pct → batarya göstergesi
          - state.batt_remote_pct → batarya göstergesi
          - fault_level          → FAULT butonu rengi
        """
        try:
            state = data.get("state", data)  # nested veya flat olabilir

            # Fan durumları
            mc = state.get("mc_fan_state", None)
            rc = state.get("rc_fan_state", None)
            if mc or rc:
                self.update_cooling_status(
                    mc or self.mc_fan_state,
                    rc or self.rc_fan_state,
                )

            # Batarya seviyeleri
            batt_m = state.get("batt_master_pct", None)
            batt_r = state.get("batt_remote_pct", None)
            if batt_m is not None:
                self.batt_m_level = float(batt_m)
            if batt_r is not None:
                self.batt_r_level = float(batt_r)

            # Fault seviyesi
            fault_lvl = state.get("fault_level", None)
            if fault_lvl is not None:
                self.set_fault_level(int(fault_lvl))

        except Exception as e:
            print(f"[STATUS] Parse error: {e}")

    # =====================================================
    # UI HELPERS
    # =====================================================
    def _grab_home_ids(self, *_):
        try:
            self._cam_icon  = self.home.ids.cam_icon
            self._batt_icon = self.home.ids.batt_icon
            self._wifi_icon = self.home.ids.wifi_icon
            self._bt_icon   = self.home.ids.bt_icon
        except Exception:
            pass

    def _turn_off_left_mode_buttons(self, except_btn=None):
        panel = self.home.ids.left_panel
        for child in panel.children:
            if child == except_btn:
                continue
            if hasattr(child, "state"):
                child.state = "normal"

    def _turn_off_right_buttons_except_fault(self, except_btn=None):
        panel = self.home.ids.right_panel
        for child in panel.children:
            if child == except_btn:
                continue
            if hasattr(child, "state"):
                if getattr(child, "text", "") == "FAULT":
                    continue
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

    # =====================================================
    # FAULT SYSTEM
    # =====================================================
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

    def open_faults(self):
        self._refresh_fault_text()
        self.sm.current = "faults"

    def close_faults(self):
        self.sm.current = "home"

    def on_fault(self):
        print(f"[FAULT] Current level = {self.fault_level}")

    # =====================================================
    # COOLING STATUS UPDATE
    # =====================================================
    def update_cooling_status(self, mc_state: str, rc_state: str):
        allowed = {"ON", "OFF", "FAULT", "COMM_LOST"}
        self.mc_fan_state = mc_state if mc_state in allowed else "COMM_LOST"
        self.rc_fan_state = rc_state if rc_state in allowed else "COMM_LOST"

    # =====================================================
    # TOP ICONS
    # =====================================================
    def on_top_icon(self, widget):
        print(f"[TOP] {widget.icon_name}")
        if widget.icon_name == "battery":
            self.open_battery()
        elif widget.icon_name == "wifi":
            widget.state = "down"
            self.sm.current = "wifi"
        elif widget.icon_name == "bluetooth":
            widget.state = "down"
            self.sm.current = "bluetooth"

    def close_top_screen(self):
        if self._wifi_icon:
            self._wifi_icon.state = "normal"
        if self._bt_icon:
            self._bt_icon.state = "normal"
        if self._batt_icon:
            self._batt_icon.state = "normal"
        self.sm.current = "home"

    def open_battery(self):
        if self._batt_icon:
            self._batt_icon.state = "down"
        self.sm.current = "battery"

    # =====================================================
    # CAMERA
    # =====================================================
    def open_camera(self):
        if self._cam_icon:
            self._cam_icon.state = "down"
        self.sm.current = "camera"
        self.start_camera()

    def close_camera(self):
        self.stop_record(force=True)
        self.stop_camera()
        if self._cam_icon:
            self._cam_icon.state = "normal"
        self.sm.current = "home"

    def start_camera(self):
        if cv2 is None or self._cap is not None:
            return
        self._cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
        self._cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc("M","J","P","G"))
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

    # =====================================================
    # BATTERY
    # =====================================================
    def _update_batteries(self, dt):
        # Gerçek batarya verisi MasterPi'den MQTT ile gelir.
        # MQTT bağlı değilse simülasyon olarak yavaşça azalt.
        if not self.mqtt.connected:
            if self.batt_m_level > 10:
                self.batt_m_level -= 1
            if self.batt_r_level > 5:
                self.batt_r_level -= random.randint(1, 3)

    # =====================================================
    # JOYSTICK BUTTONS
    # =====================================================
    def _poll_joystick_buttons(self, dt):
        try:
            left_now  = hw.read_left_joystick_button()
            right_now = hw.read_right_joystick_button()
            if right_now and not self._right_btn_prev:
                self.engine_sound_enabled = not self.engine_sound_enabled
                state_text = "ACIK" if self.engine_sound_enabled else "KAPALI"
                print(f"[JOY-R BTN] Engine sound -> {state_text}")
            if left_now and not self._left_btn_prev:
                self._left_btn_press_ts = time.time()
                self._left_btn_long_fired = False
            if left_now and self._left_btn_press_ts is not None and not self._left_btn_long_fired:
                if (time.time() - self._left_btn_press_ts) >= 2.0:
                    self._left_btn_long_fired = True
                    print("[JOY-L BTN] Long press detected")
                    self.open_faults()
            if not left_now:
                self._left_btn_press_ts = None
                self._left_btn_long_fired = False
            self._left_btn_prev  = left_now
            self._right_btn_prev = right_now
        except Exception as e:
            self.add_fault(f"Joystick buton okuma hatasi: {e}", level_hint=1)

    # =====================================================
    # CONTROL LOOP
    # =====================================================
    def update_control_loop(self, dt):
        mode = self.active_mode
        val  = 0
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
            "ts":              time.time(),
            "active":          self.is_system_started,
            "autonom":         self.is_autonom_active,
            "mode":            mode,
            "val":             val,
            "engine_sound":    self.engine_sound_enabled,
            "parking_light":   self.parking_light_on,
            "low_beam":        self.low_beam_on,
            "high_beam":       self.high_beam_on,
            "signal_lhr":      self.signal_lhr_on,
            "rig_floor_light": self.rig_floor_light_on,
            "rotation_light":  self.rotation_light_on,
        }
        self.mqtt.publish_control(payload)

    # =====================================================
    # BUTTON ACTIONS
    # =====================================================
    def on_btn(self, btn_instance, name):
        try:
            if name == "START_STOP":
                if btn_instance.state == "down":
                    self.is_system_started = True
                    self.system_status = "Sistem Baslatildi."
                    print("[SYSTEM] STARTED")
                else:
                    self.shutdown_system()
                self._sync_right_button_states()
                return

            if not self.is_system_started:
                if btn_instance.state == "down":
                    btn_instance.state = "normal"
                    print(f"[BLOCK] Sistem kapali. {name} engellendi.")
                return

            if name == "PARKING LIGHT":
                self.parking_light_on = (btn_instance.state == "down")
                hw.set_parking_light(self.parking_light_on)
                return
            if name == "LOW BEAM LIGHT":
                self.low_beam_on = (btn_instance.state == "down")
                hw.set_low_beam_light(self.low_beam_on)
                return
            if name == "HIGH BEAM LIGHT":
                self.high_beam_on = (btn_instance.state == "down")
                hw.set_high_beam_light(self.high_beam_on)
                return
            if name == "SIGNAL(LHR)LIGHT":
                self.signal_lhr_on = (btn_instance.state == "down")
                hw.set_signal_mode(self.signal_lhr_on)
                return
            if name == "RIG FLOOR LIGHT":
                self.rig_floor_light_on = (btn_instance.state == "down")
                hw.set_rig_floor_light(self.rig_floor_light_on)
                return
            if name == "ROTATION LIGHT":
                self.rotation_light_on = (btn_instance.state == "down")
                hw.set_rotation_light(self.rotation_light_on)
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

        except Exception as e:
            print(f"[ERROR] {e}")
            self.add_fault(f"Yazilim Hatasi: {e}", level_hint=2)

    def shutdown_system(self):
        self.is_system_started   = False
        self.is_autonom_active   = False
        self.active_mode         = None
        self.system_status       = "Sistem Durduruldu."
        self.parking_light_on    = False
        self.low_beam_on         = False
        self.high_beam_on        = False
        self.signal_lhr_on       = False
        self.rig_floor_light_on  = False
        self.rotation_light_on   = False
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


if __name__ == "__main__":
    RemotePiHMIApp().run()