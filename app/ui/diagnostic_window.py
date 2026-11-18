"""Diagnostic Window for Phase 1 - HID Inspection & Real-Time Monitoring."""
from __future__ import annotations

import logging
from typing import List, Optional
from datetime import datetime

from PySide6.QtCore import Qt, QTimer, Signal, QObject
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.hid.discovery import HidDiscovery, HidDeviceInfo
from app.hid.transport import HidTransport
from app.hid.protocol import SdcxProtocol, DeviceConfig, LightConfig, KeyBinding
from app.diagnostics.event_monitor import WindowsInputMonitor, InputEvent

logger = logging.getLogger(__name__)

DARK_STYLE = """
QMainWindow, QWidget {
    background-color: #121418;
    color: #E0E6ED;
    font-family: 'Segoe UI', sans-serif;
    font-size: 13px;
}
QFrame#deviceCard {
    background-color: #1A1D24;
    border: 1px solid #2A2F3D;
    border-radius: 8px;
    padding: 12px;
}
QPushButton#macropadKey {
    background-color: #252A36;
    border: 2px solid #363D4E;
    border-radius: 6px;
    color: #F0F4F8;
    font-weight: bold;
    font-size: 14px;
    min-width: 90px;
    min-height: 70px;
}
QPushButton#macropadKey:hover {
    border-color: #00ADB5;
    background-color: #2D3342;
}
QPushButton#macropadKeyActive {
    background-color: #00ADB5;
    border: 2px solid #393E46;
    border-radius: 6px;
    color: #FFFFFF;
    font-weight: bold;
    font-size: 14px;
    min-width: 90px;
    min-height: 70px;
}
QPushButton#macropadKnob {
    background-color: #222831;
    border: 3px solid #FF5722;
    border-radius: 35px;
    color: #FFFFFF;
    font-weight: bold;
    font-size: 12px;
    min-width: 70px;
    min-height: 70px;
    max-width: 70px;
    max-height: 70px;
}
QTableWidget {
    background-color: #1A1D24;
    border: 1px solid #2A2F3D;
    border-radius: 6px;
    gridline-color: #2A2F3D;
}
QHeaderView::section {
    background-color: #252A36;
    color: #00ADB5;
    font-weight: bold;
    border: none;
    padding: 6px;
}
QTextEdit {
    background-color: #0F1115;
    border: 1px solid #2A2F3D;
    border-radius: 6px;
    color: #00FFCC;
    font-family: 'Consolas', monospace;
    font-size: 12px;
}
QLabel#badgeOk {
    background-color: #00ADB5;
    color: #FFFFFF;
    font-weight: bold;
    padding: 4px 10px;
    border-radius: 4px;
}
QLabel#badgeWarn {
    background-color: #E67E22;
    color: #FFFFFF;
    font-weight: bold;
    padding: 4px 10px;
    border-radius: 4px;
}
QLabel#titleLabel {
    font-size: 18px;
    font-weight: bold;
    color: #00ADB5;
}
"""


class EventBridge(QObject):
    event_received = Signal(InputEvent)


class DiagnosticWindow(QMainWindow):
    """Main window for Phase 1 hardware diagnostics and live input monitor."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("MacroPad Studio — Diagnóstico HID (Fase 1)")
        self.resize(1100, 750)
        self.setStyleSheet(DARK_STYLE)

        self.discovery = HidDiscovery()
        self.transport = HidTransport(read_only=True)
        self.protocol = SdcxProtocol(self.transport)

        self.bridge = EventBridge()
        self.bridge.event_received.connect(self._on_input_event)

        self.input_monitor = WindowsInputMonitor(callback=self.bridge.event_received.emit)
        self.key_buttons: dict[int, QPushButton] = {}
        self.knob_button: Optional[QPushButton] = None

        self._init_ui()
        self.input_monitor.start()

        # Timer to poll connection and refresh status
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.scan_and_inspect)
        self.refresh_timer.start(3000)

        # Initial scan
        QTimer.singleShot(100, self.scan_and_inspect)

    def closeEvent(self, event):
        self.input_monitor.stop()
        self.transport.close()
        super().closeEvent(event)

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(14)

        # Header Bar
        header = QHBoxLayout()
        title = QLabel("MacroPad Studio — Fase 1: Diagnóstico e Inspección HID")
        title.setObjectName("titleLabel")
        header.addWidget(title)
        header.addStretch()

        self.status_badge = QLabel("Buscando dispositivo...")
        self.status_badge.setObjectName("badgeWarn")
        header.addWidget(self.status_badge)

        self.safe_badge = QLabel("FASE 1: SOLO LECTURA (Hardware Protegido)")
        self.safe_badge.setToolTip("En esta fase no se sobrescribe la memoria flash del macropad para evitar desconfiguraciones accidentales.")
        self.safe_badge.setObjectName("badgeOk")
        header.addWidget(self.safe_badge)

        main_layout.addLayout(header)

        # Middle Area: Left (Visual Pad + Info), Right (Interfaces & Keymap)
        mid_layout = QHBoxLayout()
        mid_layout.setSpacing(14)

        # Left Column: Visual representation
        left_col = QVBoxLayout()
        left_col.setSpacing(12)

        # Visual Pad Frame
        pad_frame = QFrame()
        pad_frame.setObjectName("deviceCard")
        pad_vbox = QVBoxLayout(pad_frame)
        pad_title = QLabel("Representación Física del Macropad")
        pad_title.setStyleSheet("font-weight: bold; color: #00ADB5;")
        pad_vbox.addWidget(pad_title)

        grid = QGridLayout()
        grid.setSpacing(10)

        # 6 Keys: 2 rows of 3
        key_defs = [
            (0, "KEY 1", 0, 0),
            (1, "KEY 2", 0, 1),
            (2, "KEY 3", 0, 2),
            (3, "KEY 4", 1, 0),
            (4, "KEY 5", 1, 1),
            (5, "KEY 6", 1, 2),
        ]
        for idx, text, r, c in key_defs:
            btn = QPushButton(text)
            btn.setObjectName("macropadKey")
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, i=idx: self._select_control(i))
            self.key_buttons[idx] = btn
            grid.addWidget(btn, r, c)

        # Knob button on the right
        self.knob_button = QPushButton("KNOB\n(Vol/Mute)")
        self.knob_button.setObjectName("macropadKnob")
        self.knob_button.setCursor(Qt.PointingHandCursor)
        self.knob_button.clicked.connect(lambda: self._select_control(16))
        grid.addWidget(self.knob_button, 0, 3, 2, 1, Qt.AlignCenter)

        pad_vbox.addLayout(grid)

        # Control detail label below the pad
        self.control_detail = QLabel("Haz clic en cualquier tecla o presiona una tecla física en el macropad.")
        self.control_detail.setStyleSheet("color: #A0ABC0; font-size: 12px; padding: 4px;")
        self.control_detail.setAlignment(Qt.AlignCenter)
        pad_vbox.addWidget(self.control_detail)

        left_col.addWidget(pad_frame)

        # Device Info Card
        info_frame = QFrame()
        info_frame.setObjectName("deviceCard")
        info_vbox = QVBoxLayout(info_frame)
        info_title = QLabel("Información de Hardware")
        info_title.setStyleSheet("font-weight: bold; color: #00ADB5;")
        info_vbox.addWidget(info_title)

        self.info_label = QLabel("Conectando al dispositivo...")
        self.info_label.setWordWrap(True)
        info_vbox.addWidget(self.info_label)

        left_col.addWidget(info_frame)
        mid_layout.addLayout(left_col, stretch=4)

        # Right Column: Interface Table & Factory Keymap Table
        right_col = QVBoxLayout()
        right_col.setSpacing(12)

        # Interfaces Table
        ifaces_frame = QFrame()
        ifaces_frame.setObjectName("deviceCard")
        ifaces_vbox = QVBoxLayout(ifaces_frame)
        ifaces_title = QLabel("Interfaces HID Detectadas")
        ifaces_title.setStyleSheet("font-weight: bold; color: #00ADB5;")
        ifaces_vbox.addWidget(ifaces_title)

        self.iface_table = QTableWidget(0, 4)
        self.iface_table.setHorizontalHeaderLabels(["MI", "Tipo / Colección", "Usage Page", "Usage"])
        self.iface_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.iface_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.iface_table.setFixedHeight(140)
        ifaces_vbox.addWidget(self.iface_table)
        right_col.addWidget(ifaces_frame)

        # Keymap Table
        keymap_frame = QFrame()
        keymap_frame.setObjectName("deviceCard")
        keymap_vbox = QVBoxLayout(keymap_frame)
        keymap_title = QLabel("Configuración Leída del Firmware (Capa 0)")
        keymap_title.setStyleSheet("font-weight: bold; color: #00ADB5;")
        keymap_vbox.addWidget(keymap_title)

        self.keymap_table = QTableWidget(0, 4)
        self.keymap_table.setHorizontalHeaderLabels(["Control", "Tipo", "Acción Actual", "Bytes Raw"])
        self.keymap_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.keymap_table.setFixedHeight(180)
        keymap_vbox.addWidget(self.keymap_table)
        right_col.addWidget(keymap_frame)

        mid_layout.addLayout(right_col, stretch=6)
        main_layout.addLayout(mid_layout, stretch=6)

        # Bottom Area: Live Event Monitor Log
        log_frame = QFrame()
        log_frame.setObjectName("deviceCard")
        log_vbox = QVBoxLayout(log_frame)

        log_header = QHBoxLayout()
        log_title = QLabel("Monitor de Entrada en Tiempo Real (Live Event Log)")
        log_title.setStyleSheet("font-weight: bold; color: #00ADB5;")
        log_header.addWidget(log_title)
        log_header.addStretch()

        clear_btn = QPushButton("Limpiar Log")
        clear_btn.clicked.connect(self._clear_log)
        log_header.addWidget(clear_btn)
        log_vbox.addLayout(log_header)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFixedHeight(150)
        log_vbox.addWidget(self.log_text)

        main_layout.addWidget(log_frame, stretch=3)

    def _clear_log(self):
        self.log_text.clear()

    def log_message(self, msg: str):
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self.log_text.append(f"[{timestamp}] {msg}")

    def _select_control(self, idx: int):
        """Display details when user clicks a button in the visual representation."""
        if idx in self.key_buttons:
            name = f"Tecla Física {idx + 1} (Índice firmware: {idx})"
            action = "Ctrl + A (Keyboard)"
            raw = "[32, 0x01, 0x04, 0x00]"
            self.control_detail.setText(f"<b>{name}</b> | Acción: <font color='#00ADB5'>{action}</font> | Raw: {raw}")
            btn = self.key_buttons[idx]
            btn.setStyleSheet("border-color: #00ADB5; background-color: #2D3342;")
            QTimer.singleShot(400, lambda b=btn: b.setStyleSheet(""))
        elif idx in (16, 17, 18):
            self.control_detail.setText(
                "<b>Perilla Rotatoria (3 Acciones):</b> "
                "Pulsar: <font color='#FF5722'>Mute</font> | "
                "Giro Der: <font color='#00ADB5'>Vol +</font> | "
                "Giro Izq: <font color='#00ADB5'>Vol -</font>"
            )
            if self.knob_button:
                self.knob_button.setStyleSheet("background-color: #FF5722; color: #FFFFFF;")
                QTimer.singleShot(400, lambda: self.knob_button.setStyleSheet(""))

    def _on_input_event(self, evt: InputEvent):
        """Handle incoming input events and highlight UI."""
        self.log_message(f"ENTRADA: {evt.event_type:10s} | {evt.key_name:20s} | {evt.details}")

        # Highlight keys
        if "Ctrl + A" in evt.key_name or "Key 1..6" in evt.key_name or evt.vk_code == ord('A'):
            self.control_detail.setText("<font color='#00ADB5'><b>¡Tecla Física Detectada!</b> Acción recibida: Ctrl + A</font>")
            for btn in self.key_buttons.values():
                btn.setStyleSheet("background-color: #00ADB5; color: #FFFFFF; border: 2px solid #FFFFFF;")
                QTimer.singleShot(300, lambda b=btn: b.setStyleSheet(""))
        elif "Knob" in evt.key_name or evt.vk_code in (0xAD, 0xAE, 0xAF):
            action_desc = "Silencio (Mute)" if evt.vk_code == 0xAD else ("Volumen +" if evt.vk_code == 0xAF else "Volumen -")
            self.control_detail.setText(f"<font color='#FF5722'><b>¡Perilla Detectada!</b> Acción: {action_desc}</font>")
            if self.knob_button:
                self.knob_button.setStyleSheet("background-color: #FF5722; color: #FFFFFF; border: 3px solid #FFFFFF;")
                QTimer.singleShot(300, lambda: self.knob_button.setStyleSheet(""))

    def scan_and_inspect(self):
        """Scan HID devices and inspect macropad state."""
        interfaces = self.discovery.enumerate_all()
        if not interfaces:
            self.status_badge.setText("Desconectado")
            self.status_badge.setObjectName("badgeWarn")
            self.status_badge.setStyle(self.status_badge.style())
            self.info_label.setText("No se detectó ningún dispositivo con VID 0x6D80 y PID 0xDC81.")
            self.iface_table.setRowCount(0)
            self.keymap_table.setRowCount(0)
            return

        self.status_badge.setText(f"Conectado ({len(interfaces)} interfaces)")
        self.status_badge.setObjectName("badgeOk")
        self.status_badge.setStyle(self.status_badge.style())

        # Populate interface table
        self.iface_table.setRowCount(len(interfaces))
        for r, iface in enumerate(interfaces):
            self.iface_table.setItem(r, 0, QTableWidgetItem(f"MI_{iface.interface_number:02d}"))
            self.iface_table.setItem(r, 1, QTableWidgetItem(iface.interface_description))
            self.iface_table.setItem(r, 2, QTableWidgetItem(f"0x{iface.usage_page:04X}"))
            self.iface_table.setItem(r, 3, QTableWidgetItem(f"0x{iface.usage:02X}"))

        # Inspect config channel if not already open
        cfg_iface = self.discovery.find_config_interface()
        if not cfg_iface:
            self.info_label.setText("Se detectaron interfaces HID, pero no el canal de configuración (MI_02).")
            return

        try:
            if not self.transport.is_connected:
                self.transport.open(cfg_iface.path)

            dev_cfg = self.protocol.get_device_config()
            light_cfg = self.protocol.get_light_config()
            bindings = self.protocol.get_keymap(0)

            # Update info text
            info_lines = [
                f"<b>Modelo:</b> {cfg_iface.product} ({cfg_iface.manufacturer})",
                f"<b>VID / PID:</b> 0x{cfg_iface.vendor_id:04X} : 0x{cfg_iface.product_id:04X}",
                f"<b>Firmware:</b> v{dev_cfg.firmware_version} | <b>Revisión:</b> 0x{cfg_iface.release_number:04X}",
                f"<b>Perfiles soportados:</b> {dev_cfg.profile_count} (Activo: {dev_cfg.active_profile})",
                f"<b>Batería / Conexión:</b> {dev_cfg.battery_level}% | Modo: {dev_cfg.work_mode}",
                f"<b>Iluminación RGB actual:</b> {light_cfg.mode_name} (Brillo: {light_cfg.brightness}/4, Vel: {light_cfg.speed}/4)",
            ]
            self.info_label.setText("<br>".join(info_lines))

            # Update keymap table
            self.keymap_table.setRowCount(len(bindings))
            for r, b in enumerate(bindings):
                self.keymap_table.setItem(r, 0, QTableWidgetItem(b.label))
                self.keymap_table.setItem(r, 1, QTableWidgetItem(b.type_name))
                self.keymap_table.setItem(r, 2, QTableWidgetItem(b.description))
                self.keymap_table.setItem(
                    r,
                    3,
                    QTableWidgetItem(f"[{b.type_id}, 0x{b.code1:02X}, 0x{b.code2:02X}, 0x{b.code3:02X}]"),
                )

        except Exception as e:
            logger.error(f"Error inspecting device: {e}")
            self.info_label.setText(f"Error al leer configuración: {e}")
