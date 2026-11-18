"""Real-time event monitor for MacroPad input events on Windows."""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import logging
import threading
import time
from dataclasses import dataclass
from typing import Callable, Optional

logger = logging.getLogger(__name__)

# Win32 Constants
WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105

VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
VK_CONTROL = 0x11
VK_LCONTROL = 0xA2
VK_RCONTROL = 0xA3


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_ulong),
    ]


HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_longlong, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)


@dataclass(frozen=True)
class InputEvent:
    """Represents a captured real-time input event."""

    timestamp: float
    event_type: str  # "KEYDOWN", "KEYUP", "KNOB_CW", "KNOB_CCW", "KNOB_PRESS", "VENDOR_ASYNC"
    vk_code: int
    key_name: str
    details: str


class WindowsInputMonitor:
    """Monitors real-time keyboard and multimedia knob events safely on Windows."""

    def __init__(self, callback: Optional[Callable[[InputEvent], None]] = None):
        self.callback = callback
        self._hook = None
        self._thread: Optional[threading.Thread] = None
        self._thread_id = 0
        self._running = False
        self._hook_proc = None

    def start(self) -> None:
        """Start monitoring in a dedicated background thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_hook_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop monitoring and unhook."""
        if not self._running:
            return
        self._running = False
        if self._thread_id:
            ctypes.windll.user32.PostThreadMessageW(self._thread_id, 0x0012, 0, 0)  # WM_QUIT
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self._thread = None

    def _run_hook_loop(self) -> None:
        self._thread_id = ctypes.windll.kernel32.GetCurrentThreadId()

        def _low_level_proc(nCode, wParam, lParam):
            if nCode >= 0:
                kb = KBDLLHOOKSTRUCT.from_address(lParam)
                is_down = wParam in (WM_KEYDOWN, WM_SYSKEYDOWN)
                vk = kb.vkCode

                # Detect key or knob action
                event_name = "KEYDOWN" if is_down else "KEYUP"
                key_name = f"VK_0x{vk:02X}"
                details = f"Scan: {kb.scanCode}, Flags: {kb.flags}"

                # Match known multimedia / knob keys
                if vk == VK_VOLUME_MUTE:
                    key_name = "Knob Press (Mute)"
                    if is_down: event_name = "KNOB_PRESS"
                elif vk == VK_VOLUME_UP:
                    key_name = "Knob CW (Vol +)"
                    if is_down: event_name = "KNOB_CW"
                elif vk == VK_VOLUME_DOWN:
                    key_name = "Knob CCW (Vol -)"
                    if is_down: event_name = "KNOB_CCW"
                elif vk == ord('A'):
                    # Check if Ctrl is pressed (default factory key)
                    ctrl_state = ctypes.windll.user32.GetAsyncKeyState(VK_CONTROL)
                    if ctrl_state & 0x8000:
                        key_name = "Key 1..6 (Ctrl + A)"
                    else:
                        key_name = "A"

                evt = InputEvent(
                    timestamp=time.time(),
                    event_type=event_name,
                    vk_code=vk,
                    key_name=key_name,
                    details=details,
                )

                if self.callback and is_down:
                    try:
                        self.callback(evt)
                    except Exception as e:
                        logger.error(f"Error in input event callback: {e}")

            # CallNextHookEx must always be called to avoid interfering with user input
            return ctypes.windll.user32.CallNextHookEx(None, nCode, wParam, lParam)

        self._hook_proc = HOOKPROC(_low_level_proc)
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        h_module = kernel32.GetModuleHandleW(None)
        self._hook = user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._hook_proc, h_module, 0)

        if not self._hook:
            logger.error("Failed to install WH_KEYBOARD_LL hook.")
            return

        logger.info("Windows low-level input monitor hook installed.")
        msg = wintypes.MSG()
        while self._running:
            res = user32.GetMessageW(ctypes.byref(msg), 0, 0, 0)
            if res <= 0:
                break
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

        if self._hook:
            user32.UnhookWindowsHookEx(self._hook)
            self._hook = None
            logger.info("Windows input monitor hook uninstalled.")
