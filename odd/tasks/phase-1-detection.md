# Phase 1: HID Detection, Descriptors & Safe Event Monitoring

## Objective
Establish the foundational HID layer for MacroPad Studio on Windows, reliably detect the `6D80:DC81` device, enumerate all interfaces, parse descriptors/reports, read factory keymaps/lighting safely without writes, and provide a real-time event monitor.

## Tasks
- [x] Task 1: Project structure, dependency configuration, and base packaging (`requirements.txt`, `pyproject.toml`).
- [x] Task 2: HID device discovery and interface enumeration engine (`app/hid/discovery.py`, `app/hid/descriptors.py`).
- [x] Task 3: Low-level HID transport layer supporting Windows overlapped I/O via `hidapi` (`app/hid/transport.py`).
- [x] Task 4: SDCX protocol decoder with read-only inspection methods for device info, light config, and keymap (`app/hid/protocol.py`).
- [x] Task 5: Real-time input event monitor with Windows Raw Input / hook support to capture key and knob events (`app/diagnostics/event_monitor.py`).
- [x] Task 6: Modern Phase 1 UI / Diagnostic tool and CLI runner (`app/main.py`, `app/ui/`).
- [x] Task 7: Unit tests with mocked hardware and execution against the physical device (`tests/`).

