"""SDCX HID Protocol decoder and parser (Read-Only)."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .transport import HidTransport

logger = logging.getLogger(__name__)

# Protocol Command Codes
CMD_GROUP_CONFIG = 0x06
SUB_GET_KEYBOARD_CONFIG = 5
SUB_GET_KEY_INFOS = 7
SUB_GET_KEYMAP = 8
SUB_GET_LIGHT_CONFIG = 10
SUB_GET_KEY_RGB = 19
SUB_GET_MODE_DEFAULTS = 22

# Light Modes
LIGHT_MODES = {
    0: "Off",
    1: "Steady",
    2: "Breath",
    3: "Press-Lit",
    4: "Tidal",
    5: "Custom (Per-Key)",
}

# Key Action Types
TYPE_MOUSE = 16
TYPE_MOUSE_MOVE = 17
TYPE_DISABLED = 19
TYPE_CONTROL = 31
TYPE_STANDARD = 32
TYPE_CONSUMER = 48
TYPE_SYSTEM = 64
TYPE_MACRO = 96
TYPE_WEBSITE = 128
TYPE_COMBINATION = 255

TYPE_NAMES = {
    TYPE_MOUSE: "Mouse",
    TYPE_MOUSE_MOVE: "Mouse Move",
    TYPE_DISABLED: "Disabled",
    TYPE_CONTROL: "Control",
    TYPE_STANDARD: "Keyboard",
    TYPE_CONSUMER: "Consumer / Multimedia",
    TYPE_SYSTEM: "System Control",
    TYPE_MACRO: "Macro",
    TYPE_WEBSITE: "Open URL",
    TYPE_COMBINATION: "Combination",
}

# Standard HID Keyboard Usage Tables (subset for human display)
HID_KEY_NAMES: Dict[int, str] = {
    0x04: "A", 0x05: "B", 0x06: "C", 0x07: "D", 0x08: "E", 0x09: "F", 0x0A: "G",
    0x0B: "H", 0x0C: "I", 0x0D: "J", 0x0E: "K", 0x0F: "L", 0x10: "M", 0x11: "N",
    0x12: "O", 0x13: "P", 0x14: "Q", 0x15: "R", 0x16: "S", 0x17: "T", 0x18: "U",
    0x19: "V", 0x1A: "W", 0x1B: "X", 0x1C: "Y", 0x1D: "Z",
    0x1E: "1", 0x1F: "2", 0x20: "3", 0x21: "4", 0x22: "5",
    0x23: "6", 0x24: "7", 0x25: "8", 0x26: "9", 0x27: "0",
    0x28: "Enter", 0x29: "Escape", 0x2A: "Backspace", 0x2B: "Tab", 0x2C: "Space",
    0x2D: "-", 0x2E: "=", 0x2F: "[", 0x30: "]", 0x31: "\\",
    0x33: ";", 0x34: "'", 0x35: "`", 0x36: ",", 0x37: ".", 0x38: "/",
    0x39: "CapsLock",
    0x3A: "F1", 0x3B: "F2", 0x3C: "F3", 0x3D: "F4", 0x3E: "F5", 0x3F: "F6",
    0x40: "F7", 0x41: "F8", 0x42: "F9", 0x43: "F10", 0x44: "F11", 0x45: "F12",
    0x46: "PrintScreen", 0x47: "ScrollLock", 0x48: "Pause",
    0x49: "Insert", 0x4A: "Home", 0x4B: "PageUp", 0x4C: "Delete", 0x4D: "End", 0x4E: "PageDown",
    0x4F: "RightArrow", 0x50: "LeftArrow", 0x51: "DownArrow", 0x52: "UpArrow",
    0x68: "F13", 0x69: "F14", 0x6A: "F15", 0x6B: "F16", 0x6C: "F17", 0x6D: "F18",
    0x6E: "F19", 0x6F: "F20", 0x70: "F21", 0x71: "F22", 0x72: "F23", 0x73: "F24",
}

CONSUMER_KEY_NAMES: Dict[int, str] = {
    0xCD: "Play / Pause",
    0xB5: "Next Track",
    0xB6: "Previous Track",
    0xB7: "Stop",
    0xE2: "Mute",
    0xE9: "Volume Up",
    0xEA: "Volume Down",
    0x183: "Media Player",
    0x192: "Calculator",
    0x194: "Local Machine Browser",
    0x223: "Home Web Browser",
    0x224: "Back",
    0x225: "Forward",
    0x226: "Stop Browser",
    0x227: "Refresh",
}

# Physical Key Mapping for HCY-K006 (6 keys + 1 rotary knob)
PHYSICAL_KEYS = [
    (0, "Key 1 (Row 1, Col 1)"),
    (1, "Key 2 (Row 1, Col 2)"),
    (2, "Key 3 (Row 1, Col 3)"),
    (3, "Key 4 (Row 2, Col 1)"),
    (4, "Key 5 (Row 2, Col 2)"),
    (5, "Key 6 (Row 2, Col 3)"),
    (16, "Knob Press"),
    (17, "Knob CW (Turn Right)"),
    (18, "Knob CCW (Turn Left)"),
]


@dataclass(frozen=True)
class DeviceConfig:
    version: int
    pid: int
    firmware_version: int
    work_mode: int
    link_status: int
    battery_level: int
    is_charging: bool
    profile_count: int
    active_profile: int
    layer_count: int
    active_layer: int
    auto_sleep_seconds: int
    serial_number: str


@dataclass(frozen=True)
class LightConfig:
    mode: int
    mode_name: str
    brightness: int
    speed: int
    direction: int
    color_type: int
    single_color_index: int
    hue: int
    sat: int
    val: int

    @property
    def hue_degrees(self) -> int:
        return int(self.hue * 360 / 255)

    @property
    def sat_percent(self) -> int:
        return int(self.sat * 100 / 255)

    @property
    def val_percent(self) -> int:
        return int(self.val * 100 / 255)


@dataclass(frozen=True)
class KeyBinding:
    index: int
    label: str
    type_id: int
    type_name: str
    code1: int
    code2: int
    code3: int
    description: str


def decode_key_description(type_id: int, c1: int, c2: int, c3: int) -> str:
    """Translate 4-byte key config into readable description."""
    if type_id == TYPE_DISABLED or (type_id == 0 and c1 == 0 and c2 == 0 and c3 == 0):
        return "Disabled / Unassigned"

    if type_id == TYPE_STANDARD:
        mods: List[str] = []
        if c1 & 0x01: mods.append("Ctrl")
        if c1 & 0x02: mods.append("Shift")
        if c1 & 0x04: mods.append("Alt")
        if c1 & 0x08: mods.append("Win")
        if c1 & 0x10: mods.append("RCtrl")
        if c1 & 0x20: mods.append("RShift")
        if c1 & 0x40: mods.append("RAlt")
        if c1 & 0x80: mods.append("RWin")

        key_name = HID_KEY_NAMES.get(c2, f"Usage(0x{c2:02X})")
        if mods:
            return f"{' + '.join(mods)} + {key_name}"
        return key_name

    if type_id == TYPE_CONSUMER:
        code = c1 | (c2 << 8)
        return CONSUMER_KEY_NAMES.get(code, f"Consumer(0x{code:04X})")

    if type_id == TYPE_MOUSE:
        parts: List[str] = []
        if c1 & 0x01: parts.append("Left Click")
        if c1 & 0x02: parts.append("Right Click")
        if c1 & 0x04: parts.append("Middle Click")
        if c1 & 0x08: parts.append("Mouse 4")
        if c1 & 0x10: parts.append("Mouse 5")
        if c3 == 1: parts.append("Wheel Up")
        elif c3 == 255: parts.append("Wheel Down")
        return " + ".join(parts) if parts else "Mouse Action"

    if type_id == TYPE_MACRO:
        return f"Macro Slot {c1}"

    return f"Raw[{type_id}, 0x{c1:02X}, 0x{c2:02X}, 0x{c3:02X}]"


class SdcxProtocol:
    """Encapsulates safe SDCX protocol operations."""

    def __init__(self, transport: HidTransport):
        self.transport = transport

    def get_device_config(self) -> DeviceConfig:
        """Fetch general device configuration, firmware, and status."""
        resp = self.transport.transfer(CMD_GROUP_CONFIG, SUB_GET_KEYBOARD_CONFIG)
        if len(resp) < 20 or resp[0] != 0xAA or resp[1] != SUB_GET_KEYBOARD_CONFIG:
            raise ValueError(f"Invalid device info response: {resp[:8]!r}")

        payload_len = resp[2]
        payload = resp[5 : 5 + payload_len]

        version = payload[0] | (payload[1] << 8)
        pid = payload[2] | (payload[3] << 8)
        firmware = payload[4] | (payload[5] << 8)
        work_mode = payload[6]
        link_status = payload[7]
        battery = payload[8]
        charge = bool(payload[9])
        profile_cnt = payload[10]
        profile = payload[11]
        layer_cnt = payload[12]
        layer = payload[13]

        sleep_time = 0
        if payload_len >= 16:
            sleep_time = payload[14] | (payload[15] << 8)

        serial = ""
        if len(resp) >= 43 and payload_len >= 40:
            serial_bytes = bytes(resp[21:43])
            serial = serial_bytes.split(b"\x00")[0].decode("ascii", errors="replace")

        return DeviceConfig(
            version=version,
            pid=pid,
            firmware_version=firmware,
            work_mode=work_mode,
            link_status=link_status,
            battery_level=battery,
            is_charging=charge,
            profile_count=profile_cnt,
            active_profile=profile,
            layer_count=layer_cnt,
            active_layer=layer,
            auto_sleep_seconds=sleep_time,
            serial_number=serial,
        )

    def get_light_config(self) -> LightConfig:
        """Fetch current global lighting configuration."""
        resp = self.transport.transfer(CMD_GROUP_CONFIG, SUB_GET_LIGHT_CONFIG)
        if len(resp) < 16 or resp[0] != 0xAA or resp[1] != SUB_GET_LIGHT_CONFIG:
            raise ValueError(f"Invalid light config response: {resp[:8]!r}")

        # resp[5:16] is the 11-byte config:
        # [type, 0, mode, brightness, speed, direction, color, singleColorIndex, h, s, v]
        p = resp[5:16]
        mode = p[2]
        return LightConfig(
            mode=mode,
            mode_name=LIGHT_MODES.get(mode, f"Mode {mode}"),
            brightness=p[3],
            speed=p[4],
            direction=p[5],
            color_type=p[6],
            single_color_index=p[7],
            hue=p[8],
            sat=p[9],
            val=p[10],
        )

    def get_keymap(self, layer: int = 0) -> List[KeyBinding]:
        """Fetch keybindings for all addressable physical keys and knob actions."""
        # Read two chunks (offsets 0 and 56) to cover all indices up to 18 (18*4 = 72 bytes)
        key_data = bytearray()
        for offset in (0, 56):
            payload = bytes([58, offset & 0xFF, (offset >> 8) & 0xFF, 0, layer])
            resp = self.transport.transfer(CMD_GROUP_CONFIG, SUB_GET_KEYMAP, payload)
            if len(resp) >= 64 and resp[0] == 0xAA and resp[1] in (SUB_GET_KEYMAP, SUB_GET_KEY_INFOS):
                key_data.extend(resp[8:64])
            else:
                logger.warning(f"Unexpected response reading keymap chunk offset={offset}: resp[0..4]={list(resp[:4])}")

        bindings: List[KeyBinding] = []
        for idx, label in PHYSICAL_KEYS:
            byte_pos = idx * 4
            if byte_pos + 4 <= len(key_data):
                t = key_data[byte_pos]
                c1 = key_data[byte_pos + 1]
                c2 = key_data[byte_pos + 2]
                c3 = key_data[byte_pos + 3]
                desc = decode_key_description(t, c1, c2, c3)
                t_name = TYPE_NAMES.get(t, f"Type {t}")
                bindings.append(
                    KeyBinding(
                        index=idx,
                        label=label,
                        type_id=t,
                        type_name=t_name,
                        code1=c1,
                        code2=c2,
                        code3=c3,
                        description=desc,
                    )
                )

        return bindings
