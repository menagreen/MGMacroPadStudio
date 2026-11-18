"""Unit tests for SdcxProtocol decoder."""
from unittest.mock import MagicMock
from app.hid.protocol import SdcxProtocol, TYPE_STANDARD, TYPE_CONSUMER


def test_decode_device_config():
    transport = MagicMock()
    # Mock response for CMD_GET_KEYBOARD_CONFIG:
    # [0xAA, 0x05, len=14, 0, 0, version_lo, version_hi, pid_lo, pid_hi, fw_lo, fw_hi,
    #  workMode, linkStatus, battery, charge, profileCnt, profile, layerCnt, layer, autoSleep_lo, autoSleep_hi]
    raw = bytearray([0xAA, 0x05, 14, 0, 0])
    raw.extend([
        0x01, 0x00,  # version = 1
        0x81, 0xDC,  # pid = 0xDC81
        0x68, 0x00,  # firmware = 104
        0x00,        # workMode = 0
        0x01,        # linkStatus = 1
        0x64,        # battery = 100%
        0x00,        # charge = False
        0x06,        # profileCnt = 6
        0x00,        # profile = 0
        0x01,        # layerCnt = 1
        0x01,        # layer = 1
        0x00, 0x00,  # autoSleep = 0
    ])
    raw.extend(b"\x00" * (64 - len(raw)))
    transport.transfer.return_value = bytes(raw)

    proto = SdcxProtocol(transport)
    cfg = proto.get_device_config()

    assert cfg.version == 1
    assert cfg.pid == 0xDC81
    assert cfg.firmware_version == 104
    assert cfg.profile_count == 6
    assert cfg.active_profile == 0
    assert cfg.battery_level == 100
    assert not cfg.is_charging


def test_decode_light_config():
    transport = MagicMock()
    # Mock response for CMD_GET_LIGHT_CONFIG:
    # [0xAA, 0x0A, len=11, 0, 0, type, 0, mode, brightness, speed, direction, color, singleColorIndex, h, s, v]
    raw = bytearray([0xAA, 0x0A, 11, 0, 0])
    raw.extend([
        0x01, 0x00,  # type, reserved
        0x04,        # mode = 4 (Tidal)
        0x04,        # brightness = 4
        0x02,        # speed = 2
        0x00,        # direction = 0
        0x00,        # color = 0 (palette)
        0x07,        # singleColorIndex = 7
        0xFF, 0xFF, 0xFF, # h, s, v
    ])
    raw.extend(b"\x00" * (64 - len(raw)))
    transport.transfer.return_value = bytes(raw)

    proto = SdcxProtocol(transport)
    light = proto.get_light_config()

    assert light.mode == 4
    assert light.mode_name == "Tidal"
    assert light.brightness == 4
    assert light.speed == 2
    assert light.hue == 255
    assert light.val_percent == 100


def test_decode_keymap():
    transport = MagicMock()
    # Return mock chunk 0 (offset 0) with Key 1..6 = Ctrl + A
    chunk0 = bytearray([0xAA, 0x07, 58, 0, 0, 0, 0, 0])
    for _ in range(6):
        chunk0.extend([TYPE_STANDARD, 0x01, 0x04, 0x00])  # Ctrl + A
    chunk0.extend(b"\x00" * (64 - len(chunk0)))

    # Return mock chunk 1 (offset 56) with Knob
    # Key 16 (Knob press = mute) at offset 64 (index 8 in chunk1 payload)
    chunk1 = bytearray([0xAA, 0x07, 58, 0, 0, 0, 0, 0])
    chunk1.extend(b"\x00" * 8)
    chunk1.extend([TYPE_CONSUMER, 0xE2, 0x00, 0x00])  # Key 16: Mute
    chunk1.extend([TYPE_CONSUMER, 0xE9, 0x00, 0x00])  # Key 17: Vol +
    chunk1.extend([TYPE_CONSUMER, 0xEA, 0x00, 0x00])  # Key 18: Vol -
    chunk1.extend(b"\x00" * (64 - len(chunk1)))

    transport.transfer.side_effect = [bytes(chunk0), bytes(chunk1)]

    proto = SdcxProtocol(transport)
    bindings = proto.get_keymap(0)

    assert len(bindings) == 9
    assert bindings[0].label.startswith("Key 1")
    assert bindings[0].description == "Ctrl + A"
    assert bindings[6].label == "Knob Press"
    assert bindings[6].description == "Mute"
    assert bindings[7].label.startswith("Knob CW")
    assert bindings[7].description == "Volume Up"
    assert bindings[8].label.startswith("Knob CCW")
    assert bindings[8].description == "Volume Down"


def test_set_key_binding():
    transport = MagicMock()
    transport.transfer.return_value = bytes([0xAA, 16, 1] + [0] * 61)
    proto = SdcxProtocol(transport)

    ok = proto.set_key_binding(key_index=0, type_id=TYPE_STANDARD, c1=0, c2=0x1E)
    assert ok
    call_args = transport.transfer.call_args[0]
    assert call_args[0] == 0x06
    assert call_args[1] == 16
    payload = call_args[2]
    assert payload[0] == 7
    assert payload[6] == TYPE_STANDARD
    assert payload[8] == 0x1E


def test_set_light_config():
    transport = MagicMock()
    transport.transfer.return_value = bytes([0xAA, 11] + [0] * 62)
    proto = SdcxProtocol(transport)

    ok = proto.set_light_config(mode=1, brightness=4, speed=2, color_type=1, hue=120)
    assert ok
    call_args = transport.transfer.call_args[0]
    assert call_args[0] == 0x06
    assert call_args[1] == 11

