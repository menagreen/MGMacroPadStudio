"""HID communication and discovery module."""
from .discovery import HidDiscovery, HidDeviceInfo
from .transport import HidTransport
from .protocol import SdcxProtocol, DeviceConfig, LightConfig, KeyBinding

__all__ = [
    "HidDiscovery",
    "HidDeviceInfo",
    "HidTransport",
    "SdcxProtocol",
    "DeviceConfig",
    "LightConfig",
    "KeyBinding",
]
