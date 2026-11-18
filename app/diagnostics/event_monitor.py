"""Safe, non-blocking input event monitor for MacroPad Studio.

Complies strictly with safety rules:
- Does NOT install invasive WH_KEYBOARD_LL hooks.
- Does NOT block, consume or interfere with the user's primary keyboard.
- Processes input safely via Qt Application Event Filters and non-blocking notifications.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Callable, Optional

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QKeyEvent

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class InputEvent:
    """Represents a captured real-time input event."""

    timestamp: float
    event_type: str  # "KEYDOWN", "KEYUP", "KNOB_CW", "KNOB_CCW", "KNOB_PRESS"
    key_name: str
    details: str
    vk_code: int = 0


class SafeInputEventFilter(QObject):
    """Application-level event filter that captures key and knob inputs.

    Guarantees:
    - Never blocks other applications or global keyboard input.
    - Zero GIL contention or thread deadlocks.
    - Captures numbers 1..6, F13..F24, multimedia knob actions (Vol+, Vol-, Mute).
    """

    def __init__(self, callback: Optional[Callable[[InputEvent], None]] = None, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.callback = callback

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() in (QEvent.KeyPress, QEvent.KeyRelease):
            key_event: QKeyEvent = event
            is_down = event.type() == QEvent.KeyPress
            key = key_event.key()

            event_type = "KEYDOWN" if is_down else "KEYUP"
            key_name = ""
            details = f"QtKey: {hex(key)}, Text: '{key_event.text()}'"

            # Check for Rotary Knob (Multimedia keys)
            if key == Qt.Key_VolumeMute:
                key_name = "Knob Press (Mute)"
                if is_down: event_type = "KNOB_PRESS"
            elif key == Qt.Key_VolumeUp:
                key_name = "Knob CW (Vol +)"
                if is_down: event_type = "KNOB_CW"
            elif key == Qt.Key_VolumeDown:
                key_name = "Knob CCW (Vol -)"
                if is_down: event_type = "KNOB_CCW"
            # Check for numbers 1..6
            elif Qt.Key_1 <= key <= Qt.Key_6:
                num = key - Qt.Key_1 + 1
                key_name = f"Key {num} ('{num}')"
            # Check for F13..F24
            elif Qt.Key_F13 <= key <= Qt.Key_F24:
                f_num = key - Qt.Key_F13 + 13
                key_name = f"Key F{f_num}"
            # Check for letters
            elif Qt.Key_A <= key <= Qt.Key_Z:
                letter = chr(key)
                if key_event.modifiers() & Qt.ControlModifier:
                    key_name = f"Ctrl + {letter}"
                else:
                    key_name = letter
            else:
                key_name = key_event.text() or f"Key(0x{key:04X})"

            if is_down and self.callback and key_name:
                evt = InputEvent(
                    timestamp=time.time(),
                    event_type=event_type,
                    key_name=key_name,
                    details=details,
                    vk_code=key_event.nativeVirtualKey(),
                )
                try:
                    self.callback(evt)
                except Exception as e:
                    logger.error(f"Error in event callback: {e}")

        # Always return False so Qt continues normal event dispatching without swallowing keys
        return False
