"""Unit tests for HID device discovery."""
from unittest.mock import patch
from app.hid.discovery import HidDiscovery, CONFIG_USAGE_PAGE, CONFIG_USAGE


MOCK_RAW_DEVICES = [
    {
        "path": b"\\\\?\\HID#VID_6D80&PID_DC81&MI_00&Col01#...",
        "vendor_id": 0x6D80,
        "product_id": 0xDC81,
        "interface_number": 0,
        "usage_page": 1,
        "usage": 6,
        "release_number": 0x0100,
        "manufacturer_string": "SDINNOVATION",
        "product_string": "SDStdKeyboard",
        "serial_number": "475620678182",
    },
    {
        "path": b"\\\\?\\HID#VID_6D80&PID_DC81&MI_02#...",
        "vendor_id": 0x6D80,
        "product_id": 0xDC81,
        "interface_number": 2,
        "usage_page": CONFIG_USAGE_PAGE,
        "usage": CONFIG_USAGE,
        "release_number": 0x0100,
        "manufacturer_string": "SDINNOVATION",
        "product_string": "SIDE-KEYBOARD",
        "serial_number": "475620678182",
    },
]


def test_enumerate_devices():
    with patch("hid.enumerate", return_value=MOCK_RAW_DEVICES):
        disc = HidDiscovery(0x6D80, 0xDC81)
        devices = disc.enumerate_all()

        assert len(devices) == 2
        assert devices[0].interface_number == 0
        assert not devices[0].is_config_channel
        assert "Keyboard" in devices[0].interface_description

        assert devices[1].interface_number == 2
        assert devices[1].is_config_channel
        assert "Vendor Config Channel" in devices[1].interface_description


def test_find_config_interface():
    with patch("hid.enumerate", return_value=MOCK_RAW_DEVICES):
        disc = HidDiscovery(0x6D80, 0xDC81)
        cfg = disc.find_config_interface()

        assert cfg is not None
        assert cfg.interface_number == 2
        assert cfg.product == "SIDE-KEYBOARD"
