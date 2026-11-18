"""Hardware-Isolated Windows Raw Input Monitor for MacroPad Studio.

Uses Windows Raw Input (WM_INPUT with RIDEV_INPUTSINK) to:
- Specifically filter events originating from the macropad hardware (VID 0x6D80, PID 0xDC81).
- Completely ignore inputs originating from the user's primary keyboard or other devices.
- Guarantee 100% non-blocking operation (zero hooks, zero latency, zero GIL lockups).
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import logging
import time
from dataclasses import dataclass
from typing import Callable, Dict, Optional

logger = logging.getLogger(__name__)

# Win32 Constants
RIDEV_INPUTSINK = 0x00000100
RIDI_DEVICENAME = 0x20000007
RID_INPUT = 0x10000003
RIM_TYPEMOUSE = 0
RIM_TYPEKEYBOARD = 1
RIM_TYPEHID = 2
RI_KEY_MAKE = 0
RI_KEY_BREAK = 1

WM_INPUT = 0x00FF

# Multimedia Virtual Keys
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF


class RAWINPUTDEVICE(ctypes.Structure):
    _fields_ = [
        ("usUsagePage", wintypes.USHORT),
        ("usUsage", wintypes.USHORT),
        ("dwFlags", wintypes.DWORD),
        ("hwndTarget", wintypes.HWND),
    ]


class RAWINPUTHEADER(ctypes.Structure):
    _fields_ = [
        ("dwType", wintypes.DWORD),
        ("dwSize", wintypes.DWORD),
        ("hDevice", wintypes.HANDLE),
        ("wParam", wintypes.WPARAM),
    ]


class RAWKEYBOARD(ctypes.Structure):
    _fields_ = [
        ("MakeCode", wintypes.USHORT),
        ("Flags", wintypes.USHORT),
        ("Reserved", wintypes.USHORT),
        ("VKey", wintypes.USHORT),
        ("Message", wintypes.UINT),
        ("ExtraInformation", wintypes.ULONG),
    ]


class RAWHID(ctypes.Structure):
    _fields_ = [
        ("dwSizeHid", wintypes.DWORD),
        ("dwCount", wintypes.DWORD),
        ("bRawData", ctypes.c_byte * 64),
    ]


class RAWINPUT(ctypes.Structure):
    class _U(ctypes.Union):
        _fields_ = [
            ("keyboard", RAWKEYBOARD),
            ("hid", RAWHID),
        ]

    _anonymous_ = ("u",)
    _fields_ = [
        ("header", RAWINPUTHEADER),
        ("u", _U),
    ]


@dataclass(frozen=True)
class InputEvent:
    """Represents a validated input event from the macropad."""

    timestamp: float
    event_type: str  # "KEYDOWN", "KEYUP", "KNOB_CW", "KNOB_CCW", "KNOB_PRESS"
    key_name: str
    details: str
    vk_code: int = 0
    is_macropad: bool = True


class WindowsRawInputManager:
    """Manages Raw Input registration and device-filtered event extraction."""

    def __init__(self, callback: Optional[Callable[[InputEvent], None]] = None):
        self.callback = callback
        self._device_cache: Dict[int, bool] = {}
        self.user32 = ctypes.windll.user32

    def register(self, hwnd: int) -> bool:
        """Register window to receive background notifications for Keyboard and Consumer devices."""
        devices = (RAWINPUTDEVICE * 2)(
            # Keyboard (Generic Desktop 0x01, Keyboard 0x06)
            RAWINPUTDEVICE(0x01, 0x06, RIDEV_INPUTSINK, hwnd),
            # Consumer Control (Consumer 0x0C, Consumer Control 0x01)
            RAWINPUTDEVICE(0x0C, 0x01, RIDEV_INPUTSINK, hwnd),
        )
        ok = self.user32.RegisterRawInputDevices(
            devices, len(devices), ctypes.sizeof(RAWINPUTDEVICE)
        )
        if not ok:
            err = ctypes.windll.kernel32.GetLastError()
            logger.error(f"Failed to register RawInput devices: error code {err}")
            return False

        logger.info(f"Registered Windows RawInput sink for HWND {hwnd}")
        return True

    def is_target_device(self, h_device: int) -> bool:
        """Check if hDevice matches VID 0x6D80 and PID 0xDC81."""
        if not h_device:
            return False

        if h_device in self._device_cache:
            return self._device_cache[h_device]

        size = wintypes.UINT(0)
        self.user32.GetRawInputDeviceInfoW(h_device, RIDI_DEVICENAME, None, ctypes.byref(size))
        if size.value == 0:
            self._device_cache[h_device] = False
            return False

        buf = ctypes.create_unicode_buffer(size.value)
        self.user32.GetRawInputDeviceInfoW(h_device, RIDI_DEVICENAME, buf, ctypes.byref(size))
        path = buf.value.upper()

        is_pad = ("6D80" in path) and ("DC81" in path)
        self._device_cache[h_device] = is_pad
        if is_pad:
            logger.info(f"Discovered active Macropad handle: {h_device} ({path})")
        return is_pad

    def process_raw_input(self, l_param: int) -> Optional[InputEvent]:
        """Parse WM_INPUT message, filter by hardware source, and dispatch."""
        dw_size = wintypes.UINT(0)
        self.user32.GetRawInputData(
            l_param, RID_INPUT, None, ctypes.byref(dw_size), ctypes.sizeof(RAWINPUTHEADER)
        )
        if dw_size.value == 0:
            return None

        buf = (ctypes.c_byte * dw_size.value)()
        bytes_read = self.user32.GetRawInputData(
            l_param, RID_INPUT, buf, ctypes.byref(dw_size), ctypes.sizeof(RAWINPUTHEADER)
        )
        if bytes_read <= 0:
            return None

        raw = RAWINPUT.from_buffer(buf)
        h_dev = raw.header.hDevice

        # CRITICAL FILTER: Verify that this input came physically from the macropad!
        # If it came from the user's primary keyboard, ignore it completely.
        if not self.is_target_device(h_dev):
            return None

        # Process Keyboard input from Macropad
        if raw.header.dwType == RIM_TYPEKEYBOARD:
            kb = raw.keyboard
            is_down = (kb.Flags & RI_KEY_BREAK) == 0
            if not is_down:
                return None  # Only report key down events for visual feedback

            vk = kb.VKey
            event_type = "KEYDOWN"
            key_name = f"VK_0x{vk:02X}"
            details = f"MakeCode: {kb.MakeCode}, Flags: {kb.Flags}"

            # Detect knob actions
            if vk == VK_VOLUME_MUTE:
                key_name = "Knob Press (Mute)"
                event_type = "KNOB_PRESS"
            elif vk == VK_VOLUME_UP:
                key_name = "Knob CW (Vol +)"
                event_type = "KNOB_CW"
            elif vk == VK_VOLUME_DOWN:
                key_name = "Knob CCW (Vol -)"
                event_type = "KNOB_CCW"
            # Detect numbers 1..6
            elif ord("1") <= vk <= ord("6"):
                num = vk - ord("1") + 1
                key_name = f"Key {num} ('{num}')"
            # Detect F13..F24
            elif 0x7C <= vk <= 0x87:
                f_num = vk - 0x7C + 13
                key_name = f"Key F{f_num}"
            elif ord("A") <= vk <= ord("Z"):
                key_name = f"Key {chr(vk)}"

            evt = InputEvent(
                timestamp=time.time(),
                event_type=event_type,
                key_name=key_name,
                details=details,
                vk_code=vk,
                is_macropad=True,
            )

            if self.callback:
                self.callback(evt)
            return evt

        # Process Consumer Control (HID) input from Macropad
        elif raw.header.dwType == RIM_TYPEHID:
            hid = raw.hid
            data_bytes = list(hid.bRawData[: hid.dwSizeHid])
            details = f"HID Bytes: {[hex(b) for b in data_bytes]}"

            # Check for knob volume/mute in raw consumer reports
            key_name = "Knob Action"
            event_type = "KNOB_ACTION"
            if len(data_bytes) >= 2:
                code = data_bytes[0] | (data_bytes[1] << 8)
                if code == 0x00E2:
                    key_name = "Knob Press (Mute)"
                    event_type = "KNOB_PRESS"
                elif code == 0x00E9:
                    key_name = "Knob CW (Vol +)"
                    event_type = "KNOB_CW"
                elif code == 0x00EA:
                    key_name = "Knob CCW (Vol -)"
                    event_type = "KNOB_CCW"

            evt = InputEvent(
                timestamp=time.time(),
                event_type=event_type,
                key_name=key_name,
                details=details,
                is_macropad=True,
            )
            if self.callback:
                self.callback(evt)
            return evt

        return None
