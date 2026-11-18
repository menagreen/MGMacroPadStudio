"""HID transport layer for safe communication with the device."""
from __future__ import annotations

import logging
import threading
from typing import Callable, List, Optional
import hid

logger = logging.getLogger(__name__)

REPORT_SIZE = 64


class TransportError(Exception):
    """Base exception for transport communication errors."""


class ReadOnlyViolationError(TransportError):
    """Raised when an unauthorized write is attempted during read-only mode."""


class HidTransport:
    """Manages raw HID communication with the config channel.

    Enforces safety guards:
    - Whitelist for safe query commands in read-only mode.
    - Automatic report ID 0 framing for Windows hidapi.
    - Interception of asynchronous lighting notifications (0xAA 0xFA).
    - Thread-safe command-response synchronization.
    """

    # Safe read-only subcommands (Group 0x06):
    # 5: Get keyboard config
    # 7: Get key infos
    # 8: Get keymap
    # 10: Get light config
    # 12: Get macro
    # 19: Get key RGB
    # 22: Get mode defaults
    # 65: Get URL
    SAFE_READ_COMMANDS = {5, 7, 8, 10, 12, 19, 22, 65}

    def __init__(self, read_only: bool = True):
        self._device: Optional[hid.device] = None
        self._lock = threading.Lock()
        self.read_only = read_only
        self.on_async_event: Optional[Callable[[bytes], None]] = None

    @property
    def is_connected(self) -> bool:
        return self._device is not None

    def open(self, path: bytes) -> None:
        """Open HID device by raw path."""
        with self._lock:
            if self._device is not None:
                self.close()
            try:
                dev = hid.device()
                dev.open_path(path)
                self._device = dev
                logger.info(f"Opened HID device at {path!r}")
            except Exception as e:
                self._device = None
                raise TransportError(f"Failed to open HID device: {e}") from e

    def close(self) -> None:
        """Close HID device."""
        with self._lock:
            if self._device is not None:
                try:
                    self._device.close()
                except Exception as e:
                    logger.warning(f"Error while closing device: {e}")
                finally:
                    self._device = None
                    logger.info("Closed HID device.")

    def transfer(self, group: int, subcommand: int, payload: bytes = b"", timeout_ms: int = 1000) -> bytes:
        """Execute a synchronized command-response transfer.

        On Windows hidapi:
        - Output report 0 expects: [0x00, group, subcommand, ...payload] padded to 65 bytes.
        - Input report returns 64 bytes.
        """
        with self._lock:
            if self._device is None:
                raise TransportError("Device is not connected.")

            # Safety check
            if group != 0x06:
                raise TransportError(f"Command group {hex(group)} is blocked. Only configuration group 0x06 is permitted.")

            if self.read_only:
                if subcommand not in self.SAFE_READ_COMMANDS:
                    raise ReadOnlyViolationError(
                        f"Command group={hex(group)}, sub={hex(subcommand)} is blocked. "
                        f"Device is in strict read-only mode."
                    )

            # Build 64-byte wire payload: [group, subcommand, ...payload]
            wire = bytearray([group, subcommand])
            wire.extend(payload)
            if len(wire) > REPORT_SIZE:
                raise TransportError(f"Payload too large: {len(wire)} > {REPORT_SIZE}")
            wire.extend(b"\x00" * (REPORT_SIZE - len(wire)))

            # Prepend report ID (0x00) for Windows hidapi
            output_report = bytes([0x00]) + bytes(wire)

            try:
                written = self._device.write(output_report)
                if written < 0:
                    raise TransportError("HID write failed.")
            except Exception as e:
                raise TransportError(f"Error during HID write: {e}") from e

            # Read response, filtering unsolicited async notifications (0xAA 0xFA)
            start_time_out = timeout_ms
            while True:
                try:
                    data = self._device.read(REPORT_SIZE, start_time_out)
                    if not data:
                        raise TransportError("HID read timeout: device did not respond.")

                    resp = bytes(data)
                    # Check for unsolicited async light notification
                    if len(resp) >= 2 and resp[0] == 0xAA and resp[1] == 0xFA:
                        logger.debug("Received asynchronous light event from device.")
                        if self.on_async_event:
                            self.on_async_event(resp)
                        continue

                    return resp
                except Exception as e:
                    if isinstance(e, TransportError):
                        raise
                    raise TransportError(f"Error during HID read: {e}") from e
