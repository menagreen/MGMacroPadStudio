"""HID device discovery and enumeration."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional
import hid

logger = logging.getLogger(__name__)

DEFAULT_VID = 0x6D80
DEFAULT_PID = 0xDC81
CONFIG_USAGE_PAGE = 0xFF00
CONFIG_USAGE = 0x02


@dataclass(frozen=True)
class HidDeviceInfo:
    """Represents an enumerated HID interface."""

    path: bytes
    path_str: str
    vendor_id: int
    product_id: int
    interface_number: int
    usage_page: int
    usage: int
    release_number: int
    manufacturer: str
    product: str
    serial_number: str

    @property
    def is_config_channel(self) -> bool:
        """Determines if this interface is the vendor-defined config channel."""
        # Either usage_page 0xFF00 / usage 0x02 or interface 2 with vendor usage page
        return (self.usage_page == CONFIG_USAGE_PAGE and self.usage == CONFIG_USAGE) or (
            self.interface_number == 2 and self.usage_page == CONFIG_USAGE_PAGE
        )

    @property
    def interface_description(self) -> str:
        """Human-readable description based on Usage Page and Usage ID."""
        if self.is_config_channel:
            return "Vendor Config Channel (MI_02)"
        if self.usage_page == 0x01:  # Generic Desktop
            if self.usage == 0x06:
                return f"Keyboard (MI_{self.interface_number:02d})"
            if self.usage == 0x02:
                return f"Mouse (MI_{self.interface_number:02d})"
            if self.usage == 0x80:
                return f"System Control (MI_{self.interface_number:02d})"
            if self.usage == 0x0C:
                return f"Wireless Radio Controls (MI_{self.interface_number:02d})"
            return f"Generic Desktop ({hex(self.usage)})"
        if self.usage_page == 0x0C:  # Consumer
            return f"Consumer Controls (Multimedia/Volume) (MI_{self.interface_number:02d})"
        return f"Unknown (Page: {hex(self.usage_page)}, Usage: {hex(self.usage)})"


class HidDiscovery:
    """Discovers and filters HID interfaces for MacroPad Studio."""

    def __init__(self, vendor_id: int = DEFAULT_VID, product_id: int = DEFAULT_PID):
        self.vendor_id = vendor_id
        self.product_id = product_id

    def enumerate_all(self) -> List[HidDeviceInfo]:
        """Enumerate all HID interfaces matching VID and PID."""
        devices: List[HidDeviceInfo] = []
        try:
            raw_devices = hid.enumerate(self.vendor_id, self.product_id)
        except Exception as e:
            logger.error(f"Failed to enumerate HID devices: {e}")
            return devices

        for d in raw_devices:
            raw_path = d.get("path", b"")
            path_bytes = raw_path if isinstance(raw_path, bytes) else raw_path.encode("utf-8")
            path_str = path_bytes.decode("utf-8", errors="replace")

            info = HidDeviceInfo(
                path=path_bytes,
                path_str=path_str,
                vendor_id=d.get("vendor_id", 0),
                product_id=d.get("product_id", 0),
                interface_number=d.get("interface_number", -1),
                usage_page=d.get("usage_page", 0),
                usage=d.get("usage", 0),
                release_number=d.get("release_number", 0),
                manufacturer=d.get("manufacturer_string") or "Unknown",
                product=d.get("product_string") or "Unknown",
                serial_number=d.get("serial_number") or "",
            )
            devices.append(info)

        return devices

    def find_config_interface(self) -> Optional[HidDeviceInfo]:
        """Find the specific vendor configuration interface (MI_02)."""
        interfaces = self.enumerate_all()
        for iface in interfaces:
            if iface.is_config_channel:
                return iface
        return None
