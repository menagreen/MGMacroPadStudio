"""Unit tests for HID transport and safety guards."""
from unittest.mock import MagicMock
import pytest

from app.hid.transport import HidTransport, ReadOnlyViolationError, TransportError


def test_read_only_protection():
    transport = HidTransport(read_only=True)
    transport._device = MagicMock()

    # Subcommand 11 is SET_LIGHT (write), must be rejected
    with pytest.raises(ReadOnlyViolationError):
        transport.transfer(group=0x06, subcommand=11, payload=bytes(11))

    # Subcommand 9 is SET_KEYMAP (write), must be rejected
    with pytest.raises(ReadOnlyViolationError):
        transport.transfer(group=0x06, subcommand=9, payload=bytes(59))

    # Bootloader command (group 0x55) must be rejected
    with pytest.raises(ReadOnlyViolationError):
        transport.transfer(group=0x55, subcommand=0)


def test_transfer_framing():
    transport = HidTransport(read_only=True)
    mock_dev = MagicMock()
    mock_dev.write.return_value = 65
    mock_dev.read.return_value = [0xAA, 0x05, 0x0E] + [0] * 61
    transport._device = mock_dev

    # Read command 5 (GET_KEYBOARD_CONFIG) is allowed in read-only
    resp = transport.transfer(group=0x06, subcommand=5)

    assert len(resp) == 64
    assert resp[0] == 0xAA
    assert resp[1] == 0x05

    # Check report ID prefix in write call
    written_buf = mock_dev.write.call_args[0][0]
    assert len(written_buf) == 65
    assert written_buf[0] == 0x00  # Report ID 0
    assert written_buf[1] == 0x06  # Group
    assert written_buf[2] == 0x05  # Subcommand
