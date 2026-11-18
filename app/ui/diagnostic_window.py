"""Diagnostic & Configuration Window for MacroPad Studio."""
from __future__ import annotations

import logging
from typing import Dict, List, Optional
from datetime import datetime

from PySide6.QtCore import Qt, QTimer, Signal, QObject
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSlider,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.hid.discovery import HidDiscovery, HidDeviceInfo
from app.hid.transport import HidTransport
from app.hid.protocol import (
    SdcxProtocol,
    DeviceConfig,
    LightConfig,
    KeyBinding,
    TYPE_STANDARD,
    TYPE_CONSUMER,
    TYPE_DISABLED,
    LIGHT_MODES,
)
from app.diagnostics.event_monitor import SafeInputEventFilter, InputEvent

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
    font-size: 13px;
    min-width: 85px;
    min-height: 65px;
}
QPushButton#macropadKey:hover {
    border-color: #00ADB5;
    background-color: #2D3342;
}
QPushButton#macropadKnob {
    background-color: #222831;
    border: 3px solid #FF5722;
    border-radius: 35px;
    color: #FFFFFF;
    font-weight: bold;
    font-size: 11px;
    min-width: 70px;
    min-height: 70px;
    max-width: 70px;
    max-height: 70px;
}
QPushButton.actionBtn {
    background-color: #00ADB5;
    color: #FFFFFF;
    font-weight: bold;
    border: none;
    border-radius: 5px;
    padding: 8px 14px;
}
QPushButton.actionBtn:hover {
    background-color: #00C4CC;
}
QPushButton.secondaryBtn {
    background-color: #2D3342;
    color: #E0E6ED;
    border: 1px solid #3E475B;
    border-radius: 5px;
    padding: 6px 12px;
}
QPushButton.secondaryBtn:hover {
    background-color: #383F52;
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
QComboBox, QSlider {
    background-color: #252A36;
    border: 1px solid #363D4E;
    border-radius: 4px;
    padding: 4px;
    color: #FFFFFF;
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

PRESET_KEYS = [
    ("Número 1", TYPE_STANDARD, 0, 0x1E, 0),
    ("Número 2", TYPE_STANDARD, 0, 0x1F, 0),
    ("Número 3", TYPE_STANDARD, 0, 0x20, 0),
    ("Número 4", TYPE_STANDARD, 0, 0x21, 0),
    ("Número 5", TYPE_STANDARD, 0, 0x22, 0),
    ("Número 6", TYPE_STANDARD, 0, 0x23, 0),
    ("F13 (Para OBS / Macros)", TYPE_STANDARD, 0, 0x68, 0),
    ("F14 (Para OBS / Macros)", TYPE_STANDARD, 0, 0x69, 0),
    ("F15 (Para OBS / Macros)", TYPE_STANDARD, 0, 0x6A, 0),
    ("F16 (Para OBS / Macros)", TYPE_STANDARD, 0, 0x6B, 0),
    ("F17 (Para OBS / Macros)", TYPE_STANDARD, 0, 0x6C, 0),
    ("F18 (Para OBS / Macros)", TYPE_STANDARD, 0, 0x6D, 0),
    ("Ctrl + C (Copiar)", TYPE_STANDARD, 1, 0x06, 0),
    ("Ctrl + V (Pegar)", TYPE_STANDARD, 1, 0x19, 0),
    ("Ctrl + Z (Deshacer)", TYPE_STANDARD, 1, 0x1D, 0),
    ("Enter", TYPE_STANDARD, 0, 0x28, 0),
    ("Espacio", TYPE_STANDARD, 0, 0x2C, 0),
    ("Escape", TYPE_STANDARD, 0, 0x29, 0),
    ("Play / Pause (Multimedia)", TYPE_CONSUMER, 0xCD, 0, 0),
    ("Siguiente Pista (Multimedia)", TYPE_CONSUMER, 0xB5, 0, 0),
    ("Pista Anterior (Multimedia)", TYPE_CONSUMER, 0xB6, 0, 0),
    ("Silencio / Mute", TYPE_CONSUMER, 0xE2, 0, 0),
    ("Subir Volumen", TYPE_CONSUMER, 0xE9, 0, 0),
    ("Bajar Volumen", TYPE_CONSUMER, 0xEA, 0, 0),
    ("Ctrl + A (Fábrica)", TYPE_STANDARD, 1, 0x04, 0),
]


class EventBridge(QObject):
    event_received = Signal(InputEvent)


class DiagnosticWindow(QMainWindow):
    """Main window for hardware diagnostics, configuration and live input monitor."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("MacroPad Studio — Configurador HID")
        self.resize(1180, 800)
        self.setStyleSheet(DARK_STYLE)

        self.discovery = HidDiscovery()
        self.transport = HidTransport(read_only=False)
        self.protocol = SdcxProtocol(self.transport)

        self.bridge = EventBridge()
        self.bridge.event_received.connect(self._on_input_event)

        # Non-blocking application event filter - does NOT touch Windows hook chain or primary keyboard
        self.event_filter = SafeInputEventFilter(callback=self.bridge.event_received.emit)
        QApplication.instance().installEventFilter(self.event_filter)

        self.key_buttons: Dict[int, QPushButton] = {}
        self.knob_button: Optional[QPushButton] = None
        self.selected_key_index: int = 0
        self.current_bindings: List[KeyBinding] = []

        self._init_ui()

        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.scan_and_inspect)
        self.refresh_timer.start(3500)

        QTimer.singleShot(150, self.scan_and_inspect)

    def closeEvent(self, event):
        app = QApplication.instance()
        if app and hasattr(self, "event_filter"):
            app.removeEventFilter(self.event_filter)
        self.transport.close()
        super().closeEvent(event)

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # Header Bar
        header = QHBoxLayout()
        title = QLabel("MacroPad Studio — Configurador & Diagnóstico HID")
        title.setObjectName("titleLabel")
        header.addWidget(title)
        header.addStretch()

        self.status_badge = QLabel("Buscando dispositivo...")
        self.status_badge.setObjectName("badgeWarn")
        header.addWidget(self.status_badge)

        self.safe_badge = QLabel("ESCRITURA HABILITADA (Hardware Activo)")
        self.safe_badge.setObjectName("badgeOk")
        header.addWidget(self.safe_badge)

        main_layout.addLayout(header)

        # Top area: Visual Pad & Device info (Left) + Quick Configuration (Right)
        top_layout = QHBoxLayout()
        top_layout.setSpacing(14)

        # Left Column: Visual representation
        left_col = QVBoxLayout()
        left_col.setSpacing(10)

        pad_frame = QFrame()
        pad_frame.setObjectName("deviceCard")
        pad_vbox = QVBoxLayout(pad_frame)
        pad_title = QLabel("Representación Física del Macropad")
        pad_title.setStyleSheet("font-weight: bold; color: #00ADB5;")
        pad_vbox.addWidget(pad_title)

        grid = QGridLayout()
        grid.setSpacing(10)

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

        self.knob_button = QPushButton("KNOB\n(Vol/Mute)")
        self.knob_button.setObjectName("macropadKnob")
        self.knob_button.setCursor(Qt.PointingHandCursor)
        self.knob_button.clicked.connect(lambda: self._select_control(16))
        grid.addWidget(self.knob_button, 0, 3, 2, 1, Qt.AlignCenter)

        pad_vbox.addLayout(grid)

        self.control_detail = QLabel("Selecciona una tecla para editar su acción en el firmware.")
        self.control_detail.setStyleSheet("color: #00ADB5; font-weight: bold; font-size: 12px; padding: 4px;")
        self.control_detail.setAlignment(Qt.AlignCenter)
        pad_vbox.addWidget(self.control_detail)

        left_col.addWidget(pad_frame)

        # Quick Actions Frame
        quick_frame = QFrame()
        quick_frame.setObjectName("deviceCard")
        quick_vbox = QVBoxLayout(quick_frame)
        quick_title = QLabel("Asignaciones Rápidas de Teclas")
        quick_title.setStyleSheet("font-weight: bold; color: #00ADB5;")
        quick_vbox.addWidget(quick_title)

        quick_btns = QHBoxLayout()
        btn_num = QPushButton("Asignar Teclas '1' a '6'")
        btn_num.setProperty("class", "actionBtn")
        btn_num.clicked.connect(self._auto_map_numbers)
        quick_btns.addWidget(btn_num)

        btn_fkeys = QPushButton("Asignar F13..F18 (OBS)")
        btn_fkeys.setProperty("class", "actionBtn")
        btn_fkeys.clicked.connect(self._auto_map_fkeys)
        quick_btns.addWidget(btn_fkeys)

        btn_reset = QPushButton("Reset Fábrica (Ctrl+A)")
        btn_reset.setProperty("class", "secondaryBtn")
        btn_reset.clicked.connect(self._auto_map_factory)
        quick_btns.addWidget(btn_reset)

        quick_vbox.addLayout(quick_btns)
        left_col.addWidget(quick_frame)

        top_layout.addLayout(left_col, stretch=5)

        # Right Column: Key Config Editor + RGB Control
        right_col = QVBoxLayout()
        right_col.setSpacing(10)

        # Key Editor Card
        editor_frame = QFrame()
        editor_frame.setObjectName("deviceCard")
        editor_vbox = QVBoxLayout(editor_frame)
        self.editor_title = QLabel("Editor de Tecla Seleccionada: Key 1")
        self.editor_title.setStyleSheet("font-weight: bold; color: #00ADB5; font-size: 14px;")
        editor_vbox.addWidget(self.editor_title)

        form_layout = QHBoxLayout()
        form_layout.addWidget(QLabel("Acción predefinida:"))
        self.preset_combo = QComboBox()
        for label, _, _, _, _ in PRESET_KEYS:
            self.preset_combo.addItem(label)
        form_layout.addWidget(self.preset_combo, stretch=1)

        btn_apply_key = QPushButton("Guardar en Firmware")
        btn_apply_key.setProperty("class", "actionBtn")
        btn_apply_key.clicked.connect(self._apply_selected_key)
        form_layout.addWidget(btn_apply_key)
        editor_vbox.addLayout(form_layout)

        right_col.addWidget(editor_frame)

        # RGB Control Card
        rgb_frame = QFrame()
        rgb_frame.setObjectName("deviceCard")
        rgb_vbox = QVBoxLayout(rgb_frame)
        rgb_title = QLabel("Control de Iluminación RGB")
        rgb_title.setStyleSheet("font-weight: bold; color: #00ADB5; font-size: 14px;")
        rgb_vbox.addWidget(rgb_title)

        rgb_controls = QHBoxLayout()
        rgb_controls.addWidget(QLabel("Modo:"))
        self.rgb_mode_combo = QComboBox()
        for mode_val, mode_name in LIGHT_MODES.items():
            self.rgb_mode_combo.addItem(f"{mode_val}: {mode_name}", mode_val)
        rgb_controls.addWidget(self.rgb_mode_combo)

        rgb_controls.addWidget(QLabel("Brillo (0..4):"))
        self.rgb_brightness_slider = QSlider(Qt.Horizontal)
        self.rgb_brightness_slider.setRange(0, 4)
        self.rgb_brightness_slider.setValue(4)
        rgb_controls.addWidget(self.rgb_brightness_slider)

        rgb_controls.addWidget(QLabel("Velocidad (0..4):"))
        self.rgb_speed_slider = QSlider(Qt.Horizontal)
        self.rgb_speed_slider.setRange(0, 4)
        self.rgb_speed_slider.setValue(2)
        rgb_controls.addWidget(self.rgb_speed_slider)

        btn_apply_rgb = QPushButton("Aplicar RGB")
        btn_apply_rgb.setProperty("class", "actionBtn")
        btn_apply_rgb.clicked.connect(self._apply_rgb)
        rgb_controls.addWidget(btn_apply_rgb)

        rgb_vbox.addLayout(rgb_controls)
        right_col.addWidget(rgb_frame)

        # Keymap table
        keymap_frame = QFrame()
        keymap_frame.setObjectName("deviceCard")
        keymap_vbox = QVBoxLayout(keymap_frame)
        keymap_title = QLabel("Configuración Actual del Firmware")
        keymap_title.setStyleSheet("font-weight: bold; color: #00ADB5;")
        keymap_vbox.addWidget(keymap_title)

        self.keymap_table = QTableWidget(0, 4)
        self.keymap_table.setHorizontalHeaderLabels(["Control", "Tipo", "Acción Actual", "Bytes Raw"])
        self.keymap_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.keymap_table.setFixedHeight(140)
        keymap_vbox.addWidget(self.keymap_table)
        right_col.addWidget(keymap_frame)

        top_layout.addLayout(right_col, stretch=6)
        main_layout.addLayout(top_layout, stretch=6)

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
        self.log_text.setFixedHeight(120)
        log_vbox.addWidget(self.log_text)

        main_layout.addWidget(log_frame, stretch=3)

    def _clear_log(self):
        self.log_text.clear()

    def log_message(self, msg: str):
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self.log_text.append(f"[{timestamp}] {msg}")

    def _select_control(self, idx: int):
        self.selected_key_index = idx
        label_text = f"Key {idx + 1}" if idx < 6 else ("Knob Press" if idx == 16 else ("Knob CW" if idx == 17 else "Knob CCW"))
        self.editor_title.setText(f"Editor de Control Seleccionado: {label_text} (Índice {idx})")
        self.control_detail.setText(f"Editando: <b>{label_text}</b> — Selecciona una acción en el panel derecho y pulsa 'Guardar en Firmware'.")

    def _apply_selected_key(self):
        idx = self.selected_key_index
        preset_idx = self.preset_combo.currentIndex()
        if preset_idx < 0 or preset_idx >= len(PRESET_KEYS):
            return

        name, t, c1, c2, c3 = PRESET_KEYS[preset_idx]
        try:
            ok = self.protocol.set_key_binding(idx, t, c1, c2, c3)
            if ok:
                self.log_message(f"Firmware actualizado: Control {idx} configurado como '{name}'")
                self.scan_and_inspect()
            else:
                self.log_message(f"Error: Dispositivo no confirmó escritura para control {idx}")
        except Exception as e:
            self.log_message(f"Error escribiendo en hardware: {e}")

    def _auto_map_numbers(self):
        """Map keys 1..6 to numbers 1..6."""
        self.log_message("Escribiendo auto-mapeo: Teclas 1 a 6...")
        for i in range(6):
            usage = 0x1E + i  # 1 to 6
            self.protocol.set_key_binding(i, TYPE_STANDARD, 0, usage, 0)
        self.log_message("Auto-mapeo a números 1..6 completado.")
        self.scan_and_inspect()

    def _auto_map_fkeys(self):
        """Map keys 1..6 to F13..F18."""
        self.log_message("Escribiendo auto-mapeo: F13 a F18 (ideal para OBS)...")
        for i in range(6):
            usage = 0x68 + i  # F13 to F18
            self.protocol.set_key_binding(i, TYPE_STANDARD, 0, usage, 0)
        self.log_message("Auto-mapeo a F13..F18 completado.")
        self.scan_and_inspect()

    def _auto_map_factory(self):
        """Reset keys 1..6 to factory Ctrl+A."""
        self.log_message("Restableciendo teclas a configuración de fábrica (Ctrl+A)...")
        for i in range(6):
            self.protocol.set_key_binding(i, TYPE_STANDARD, 1, 0x04, 0)
        self.scan_and_inspect()

    def _apply_rgb(self):
        mode_val = self.rgb_mode_combo.currentData()
        brightness = self.rgb_brightness_slider.value()
        speed = self.rgb_speed_slider.value()
        try:
            ok = self.protocol.set_light_config(mode_val, brightness, speed)
            if ok:
                self.log_message(f"RGB actualizado: Modo {mode_val}, Brillo {brightness}, Velocidad {speed}")
            else:
                self.log_message("Error: Dispositivo no confirmó actualización RGB")
        except Exception as e:
            self.log_message(f"Error aplicando RGB: {e}")

    def _on_input_event(self, evt: InputEvent):
        """Handle incoming input events and highlight individual keys."""
        self.log_message(f"ENTRADA: {evt.event_type:10s} | {evt.key_name:20s} | {evt.details}")

        # Check for Key 1..6
        for i in range(6):
            if f"Key {i+1}" in evt.key_name:
                if i in self.key_buttons:
                    btn = self.key_buttons[i]
                    btn.setStyleSheet("background-color: #00ADB5; color: #FFFFFF; border: 2px solid #FFFFFF;")
                    QTimer.singleShot(250, lambda b=btn: b.setStyleSheet(""))
                    self.control_detail.setText(f"<font color='#00ADB5'><b>¡Tecla Física {i+1} Pulsada!</b> Reporte: '{evt.key_name}'</font>")
                return

        # Check knob
        if "Knob" in evt.key_name:
            if self.knob_button:
                self.knob_button.setStyleSheet("background-color: #FF5722; color: #FFFFFF; border: 3px solid #FFFFFF;")
                QTimer.singleShot(250, lambda: self.knob_button.setStyleSheet(""))
                self.control_detail.setText(f"<font color='#FF5722'><b>¡Perilla Detectada!</b> Acción: {evt.key_name}</font>")
                return

        # Fallback for Ctrl + A
        if "Ctrl + A" in evt.key_name:
            for btn in self.key_buttons.values():
                btn.setStyleSheet("background-color: #E67E22; color: #FFFFFF;")
                QTimer.singleShot(250, lambda b=btn: b.setStyleSheet(""))
            self.control_detail.setText("<font color='#E67E22'>Pulsación detectada con mapeo compartido de fábrica (Ctrl+A).</font>")

    def scan_and_inspect(self):
        """Scan HID devices and inspect macropad state."""
        interfaces = self.discovery.enumerate_all()
        if not interfaces:
            self.status_badge.setText("Desconectado")
            self.status_badge.setObjectName("badgeWarn")
            self.status_badge.setStyle(self.status_badge.style())
            self.keymap_table.setRowCount(0)
            return

        self.status_badge.setText(f"Conectado ({len(interfaces)} interfaces)")
        self.status_badge.setObjectName("badgeOk")
        self.status_badge.setStyle(self.status_badge.style())

        cfg_iface = self.discovery.find_config_interface()
        if not cfg_iface:
            return

        try:
            if not self.transport.is_connected:
                self.transport.open(cfg_iface.path)

            bindings = self.protocol.get_keymap(0)
            self.current_bindings = bindings

            # Update key button texts with their real current binding
            for b in bindings:
                if b.index in self.key_buttons:
                    btn = self.key_buttons[b.index]
                    btn.setText(f"KEY {b.index + 1}\n[{b.description}]")

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
