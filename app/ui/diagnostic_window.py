"""Diagnostic & Configuration Window with Profiles, Per-Key RGB, and Tray Support."""
from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from ctypes import wintypes

from PySide6.QtCore import Qt, QTimer, Signal, QObject
from PySide6.QtGui import QColor, QFont, QKeyEvent, QIcon, QPixmap, QPainter, QAction
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSlider,
    QSystemTrayIcon,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.hid.discovery import HidDiscovery, HidDeviceInfo
from app.hid.transport import HidTransport
from app.hid.protocol import (
    PHYSICAL_KEYS,
    SdcxProtocol,
    DeviceConfig,
    LightConfig,
    KeyBinding,
    TYPE_STANDARD,
    TYPE_CONSUMER,
    TYPE_DISABLED,
    LIGHT_MODES,
)
from app.diagnostics.event_monitor import WindowsRawInputManager, InputEvent
from app.profiles.profile_manager import ProfileManager, Profile, KeyConfig

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
    padding: 7px 14px;
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
QPushButton.colorSwatch {
    border: 1px solid #3E475B;
    border-radius: 4px;
    min-width: 28px;
    max-width: 28px;
    min-height: 28px;
    max-height: 28px;
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

COLOR_SWATCHES = [
    ("Cian", (0, 173, 181)),
    ("Rojo", (255, 30, 30)),
    ("Verde", (30, 215, 96)),
    ("Azul", (0, 114, 255)),
    ("Púrpura", (155, 93, 229)),
    ("Naranja", (255, 87, 34)),
    ("Amarillo", (255, 204, 0)),
    ("Blanco", (255, 255, 255)),
    ("Apagado", (0, 0, 0)),
]

PRESET_KEYS = [
    ("Cambio de Perfil (Ciclo Siguiente)", TYPE_STANDARD, 0, 0x73, 0),
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


def create_tray_icon_pixmap(color: Tuple[int, int, int]) -> QIcon:
    """Generate a clean square status icon for the system tray."""
    pix = QPixmap(32, 32)
    pix.fill(Qt.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(QColor(*color))
    painter.setPen(Qt.NoPen)
    painter.drawRoundedRect(4, 4, 24, 24, 6, 6)
    painter.end()
    return QIcon(pix)


class DiagnosticWindow(QMainWindow):
    """Main window with hardware synchronization, profiles, per-key RGB and system tray."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("MacroPad Studio — Gestor de Perfiles & RGB")
        self.resize(1200, 840)
        self.setStyleSheet(DARK_STYLE)

        self.discovery = HidDiscovery()
        self.transport = HidTransport(read_only=False)
        self.protocol = SdcxProtocol(self.transport)
        self.profile_mgr = ProfileManager()

        self.bridge = EventBridge()
        self.bridge.event_received.connect(self._on_input_event)
        self.raw_input = WindowsRawInputManager(callback=self.bridge.event_received.emit)

        self.key_buttons: Dict[int, QPushButton] = {}
        self.knob_button: Optional[QPushButton] = None
        self.selected_key_index: int = 0
        self.current_key_color: Tuple[int, int, int] = (0, 173, 181)

        self.setFocusPolicy(Qt.StrongFocus)
        self._init_ui()
        self._init_tray()

        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.scan_and_inspect)
        self.refresh_timer.start(4000)

        QTimer.singleShot(200, self._initial_sync)

    def _initial_sync(self):
        self.scan_and_inspect()
        self._load_active_profile_ui()

    def _init_tray(self):
        self.tray_icon = QSystemTrayIcon(create_tray_icon_pixmap((0, 173, 181)), self)
        self.tray_icon.setToolTip("MacroPad Studio — Activo en segundo plano")

        tray_menu = QMenu()
        open_action = tray_menu.addAction("Abrir MacroPad Studio")
        open_action.triggered.connect(self._show_window)

        next_action = tray_menu.addAction("Siguiente Perfil (Tecla 6)")
        next_action.triggered.connect(self._cycle_profile)

        tray_menu.addSeparator()

        self.tray_profile_menu = tray_menu.addMenu("Cambiar Perfil")
        self._rebuild_tray_profiles()

        tray_menu.addSeparator()
        quit_action = tray_menu.addAction("Salir Completamente")
        quit_action.triggered.connect(self._force_quit)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _rebuild_tray_profiles(self):
        self.tray_profile_menu.clear()
        for p in self.profile_mgr.profiles:
            act = self.tray_profile_menu.addAction(p.name)
            act.setCheckable(True)
            act.setChecked(p.id == self.profile_mgr.active_profile.id)
            act.triggered.connect(lambda chk=False, pid=p.id: self._select_profile_by_id(pid))

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self._show_window()

    def _show_window(self):
        self.show()
        self.setWindowState(self.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)
        self.raise_()
        self.activateWindow()

    def _force_quit(self):
        self.tray_icon.hide()
        self.transport.close()
        QApplication.quit()

    def closeEvent(self, event):
        if self.tray_cb.isChecked():
            event.ignore()
            self.hide()
            self.tray_icon.showMessage(
                "MacroPad Studio",
                f"La aplicación sigue activa en segundo plano.\nPerfil activo: {self.profile_mgr.active_profile.name}",
                QSystemTrayIcon.Information,
                2000,
            )
        else:
            self.tray_icon.hide()
            self.transport.close()
            super().closeEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        if not getattr(self, "_raw_input_registered", False):
            self._raw_input_registered = True
            hwnd = int(self.winId())
            self.raw_input.register(hwnd)

    def nativeEvent(self, eventType, message):
        if message:
            try:
                msg = wintypes.MSG.from_address(int(message))
                if msg.message == 0x00FF:  # WM_INPUT
                    self.raw_input.process_raw_input(msg.lParam)
            except Exception as e:
                logger.debug(f"nativeEvent error: {e}")
        return super().nativeEvent(eventType, message)

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(10)

        # Header Bar: Title + Profile Selector + Status
        header = QHBoxLayout()
        title = QLabel("MacroPad Studio — Gestor de Perfiles & RGB")
        title.setObjectName("titleLabel")
        header.addWidget(title)
        header.addStretch()

        header.addWidget(QLabel("<b>Perfil Activo:</b>"))
        self.profile_combo = QComboBox()
        self.profile_combo.setMinimumWidth(180)
        for p in self.profile_mgr.profiles:
            self.profile_combo.addItem(p.name, p.id)
        self.profile_combo.currentIndexChanged.connect(self._on_profile_combo_changed)
        header.addWidget(self.profile_combo)

        btn_new_profile = QPushButton("+ Nuevo")
        btn_new_profile.setToolTip("Crear un nuevo perfil")
        btn_new_profile.setProperty("class", "secondaryBtn")
        btn_new_profile.clicked.connect(self._create_new_profile)
        header.addWidget(btn_new_profile)

        btn_color_profile = QPushButton("Color Perfil")
        btn_color_profile.setToolTip("Cambiar el color temático de este perfil")
        btn_color_profile.setProperty("class", "secondaryBtn")
        btn_color_profile.clicked.connect(self._change_profile_theme_color)
        header.addWidget(btn_color_profile)

        btn_del_profile = QPushButton("Eliminar")
        btn_del_profile.setToolTip("Eliminar el perfil actual")
        btn_del_profile.setProperty("class", "secondaryBtn")
        btn_del_profile.clicked.connect(self._delete_current_profile)
        header.addWidget(btn_del_profile)

        btn_apply_profile = QPushButton("Aplicar al Hardware")
        btn_apply_profile.setProperty("class", "actionBtn")
        btn_apply_profile.clicked.connect(self._apply_current_profile_to_hardware)
        header.addWidget(btn_apply_profile)

        self.status_badge = QLabel("Conectando...")
        self.status_badge.setObjectName("badgeOk")
        header.addWidget(self.status_badge)

        self.tray_cb = QCheckBox("Minimizar a la bandeja al cerrar")
        self.tray_cb.setChecked(True)
        self.tray_cb.setStyleSheet("margin-left: 8px; color: #A0ABC0;")
        header.addWidget(self.tray_cb)

        main_layout.addLayout(header)

        # Main Workspace
        work_layout = QHBoxLayout()
        work_layout.setSpacing(12)

        # Left Column: Visual Macropad + Key & Per-Key Color Editor
        left_col = QVBoxLayout()
        left_col.setSpacing(10)

        pad_frame = QFrame()
        pad_frame.setObjectName("deviceCard")
        pad_vbox = QVBoxLayout(pad_frame)

        pad_header = QHBoxLayout()
        pad_title = QLabel("Macropad Físico (Haz clic para editar tecla y color)")
        pad_title.setStyleSheet("font-weight: bold; color: #00ADB5;")
        pad_header.addWidget(pad_title)
        pad_header.addStretch()

        self.profile_badge = QLabel("Perfil: General")
        self.profile_badge.setStyleSheet("color: #FFFFFF; font-weight: bold; padding: 2px 6px; border-radius: 4px;")
        pad_header.addWidget(self.profile_badge)
        pad_vbox.addLayout(pad_header)

        # 6 Keys + Knob Grid
        grid = QGridLayout()
        grid.setSpacing(10)
        key_defs = [
            (0, "KEY 1", 0, 0),
            (1, "KEY 2", 0, 1),
            (2, "KEY 3", 0, 2),
            (3, "KEY 4", 1, 0),
            (4, "KEY 5", 1, 1),
            (5, "KEY 6\n[Perfil]", 1, 2),
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

        self.control_detail = QLabel("Selecciona cualquier tecla o gira la perilla para probar o editar.")
        self.control_detail.setStyleSheet("color: #00ADB5; font-weight: bold; font-size: 12px; padding: 4px;")
        self.control_detail.setAlignment(Qt.AlignCenter)
        pad_vbox.addWidget(self.control_detail)

        left_col.addWidget(pad_frame)

        # Quick profile switch info
        tip_frame = QFrame()
        tip_frame.setObjectName("deviceCard")
        tip_vbox = QVBoxLayout(tip_frame)
        tip_text = QLabel(
            "💡 <b>Tip de Cambio de Perfil:</b><br>"
            "Presiona la <b>Tecla 6</b> en el macropad (o pulsa 'Siguiente Perfil') para alternar entre "
            "<b>General</b> (Cian), <b>Streaming</b> (Púrpura) y <b>Multimedia</b> (Naranja). "
            "El hardware cambiará automáticamente de color y de funciones."
        )
        tip_text.setWordWrap(True)
        tip_text.setStyleSheet("color: #E0E6ED; font-size: 12px;")
        tip_vbox.addWidget(tip_text)
        left_col.addWidget(tip_frame)

        work_layout.addLayout(left_col, stretch=5)

        # Right Column: Key Config Editor + Color Picker per key
        right_col = QVBoxLayout()
        right_col.setSpacing(10)

        # Editor Card
        editor_frame = QFrame()
        editor_frame.setObjectName("deviceCard")
        editor_vbox = QVBoxLayout(editor_frame)
        self.editor_title = QLabel("Configurar Control: Key 1")
        self.editor_title.setStyleSheet("font-weight: bold; color: #00ADB5; font-size: 14px;")
        editor_vbox.addWidget(self.editor_title)

        form_layout = QHBoxLayout()
        form_layout.addWidget(QLabel("Función asignada:"))
        self.preset_combo = QComboBox()
        for label, _, _, _, _ in PRESET_KEYS:
            self.preset_combo.addItem(label)
        form_layout.addWidget(self.preset_combo, stretch=1)

        btn_save_key = QPushButton("Guardar Función")
        btn_save_key.setProperty("class", "actionBtn")
        btn_save_key.clicked.connect(self._save_selected_key_action)
        form_layout.addWidget(btn_save_key)
        editor_vbox.addLayout(form_layout)

        # Per-key Color Palette
        editor_vbox.addSpacing(6)
        color_header = QLabel("Color RGB de Fondo para esta tecla:")
        color_header.setStyleSheet("font-weight: bold; color: #E0E6ED;")
        editor_vbox.addWidget(color_header)

        swatch_layout = QHBoxLayout()
        swatch_layout.setSpacing(6)
        for name, rgb in COLOR_SWATCHES:
            sw_btn = QPushButton()
            sw_btn.setObjectName("colorSwatch")
            sw_btn.setToolTip(name)
            sw_btn.setCursor(Qt.PointingHandCursor)
            hex_col = f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
            sw_btn.setStyleSheet(f"background-color: {hex_col}; border: 1px solid #3E475B; border-radius: 4px; min-width: 26px; min-height: 26px;")
            sw_btn.clicked.connect(lambda chk=False, c=rgb: self._set_selected_key_color(c))
            swatch_layout.addWidget(sw_btn)

        btn_custom_color = QPushButton("Color Libre...")
        btn_custom_color.setProperty("class", "secondaryBtn")
        btn_custom_color.clicked.connect(self._open_custom_color_dialog)
        swatch_layout.addWidget(btn_custom_color)

        btn_fill_all = QPushButton("Pintar Todas")
        btn_fill_all.setToolTip("Aplica este color a todas las teclas del perfil")
        btn_fill_all.setProperty("class", "secondaryBtn")
        btn_fill_all.clicked.connect(self._apply_selected_color_to_all_keys)
        swatch_layout.addWidget(btn_fill_all)

        swatch_layout.addStretch()
        editor_vbox.addLayout(swatch_layout)

        right_col.addWidget(editor_frame)

        # Keymap and Profiles summary table
        keymap_frame = QFrame()
        keymap_frame.setObjectName("deviceCard")
        keymap_vbox = QVBoxLayout(keymap_frame)
        keymap_title = QLabel("Mapeo y Colores del Perfil Actual")
        keymap_title.setStyleSheet("font-weight: bold; color: #00ADB5;")
        keymap_vbox.addWidget(keymap_title)

        self.keymap_table = QTableWidget(0, 4)
        self.keymap_table.setHorizontalHeaderLabels(["Control", "Acción Actual", "Color RGB", "Destino"])
        self.keymap_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.keymap_table.setFixedHeight(150)
        keymap_vbox.addWidget(self.keymap_table)
        right_col.addWidget(keymap_frame)

        work_layout.addLayout(right_col, stretch=6)
        main_layout.addLayout(work_layout, stretch=6)

        # Bottom Area: Live Log
        log_frame = QFrame()
        log_frame.setObjectName("deviceCard")
        log_vbox = QVBoxLayout(log_frame)

        log_header = QHBoxLayout()
        log_title = QLabel("Monitor de Entrada en Tiempo Real")
        log_title.setStyleSheet("font-weight: bold; color: #00ADB5;")
        log_header.addWidget(log_title)
        log_header.addStretch()

        clear_btn = QPushButton("Limpiar Log")
        clear_btn.clicked.connect(self.log_text_clear)
        log_header.addWidget(clear_btn)
        log_vbox.addLayout(log_header)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFixedHeight(110)
        log_vbox.addWidget(self.log_text)

        main_layout.addWidget(log_frame, stretch=3)

    def log_text_clear(self):
        self.log_text.clear()

    def log_message(self, msg: str):
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self.log_text.append(f"[{timestamp}] {msg}")

    def _select_control(self, idx: int):
        self.selected_key_index = idx
        label_text = f"Key {idx + 1}" if idx < 6 else ("Knob Press" if idx == 16 else ("Knob CW" if idx == 17 else "Knob CCW"))
        self.editor_title.setText(f"Configurar Control: {label_text} (Índice {idx})")

        profile = self.profile_mgr.active_profile
        curr_cfg = profile.key_bindings.get(idx)
        if curr_cfg:
            self.control_detail.setText(f"Editando: <b>{label_text}</b> | Acción: <font color='#00ADB5'>{curr_cfg.label}</font>")

    def _set_selected_key_color(self, rgb: Tuple[int, int, int]):
        idx = self.selected_key_index
        profile = self.profile_mgr.active_profile
        profile.key_colors[idx] = rgb
        self.profile_mgr.save()

        # Update button visual styling immediately
        hex_col = f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
        if idx in self.key_buttons:
            self.key_buttons[idx].setStyleSheet(f"border: 2px solid {hex_col};")
        elif self.knob_button and idx in (16, 17, 18):
            self.knob_button.setStyleSheet(f"border: 3px solid {hex_col};")

        # Synchronize color to hardware immediately
        try:
            self.protocol.set_light_config(mode=5, brightness=4, speed=2, color_type=0)
            self.protocol.set_key_color(idx, rgb[0], rgb[1], rgb[2])
            self.log_message(f"Color de tecla {idx} actualizado a RGB {rgb} en firmware.")
            self._update_table_view()
        except Exception as e:
            self.log_message(f"Error escribiendo color: {e}")

    def _open_custom_color_dialog(self):
        color = QColorDialog.getColor(QColor(0, 173, 181), self, "Seleccionar Color RGB")
        if color.isValid():
            rgb = (color.red(), color.green(), color.blue())
            self._set_selected_key_color(rgb)

    def _save_selected_key_action(self):
        idx = self.selected_key_index
        preset_idx = self.preset_combo.currentIndex()
        if preset_idx < 0:
            return

        label, t, c1, c2, c3 = PRESET_KEYS[preset_idx]
        is_switch = ("Cambio de Perfil" in label)

        profile = self.profile_mgr.active_profile
        profile.key_bindings[idx] = KeyConfig(t, c1, c2, c3, label, is_profile_switch=is_switch)
        self.profile_mgr.save()

        # Write to macropad firmware immediately
        try:
            self.protocol.set_key_binding(idx, t, c1, c2, c3)
            self.log_message(f"Función guardada en firmware: Control {idx} -> '{label}'")
            self._update_table_view()
            self._update_key_labels()
        except Exception as e:
            self.log_message(f"Error escribiendo función: {e}")

    def _create_new_profile(self):
        name, ok = QInputDialog.getText(self, "Nuevo Perfil", "Nombre del nuevo perfil (ej. Blender, Valorant, Edición):")
        if ok and name.strip():
            color = QColorDialog.getColor(QColor(0, 173, 181), self, f"Color Temático para '{name}'")
            theme_rgb = (color.red(), color.green(), color.blue()) if color.isValid() else (0, 173, 181)
            new_p = self.profile_mgr.create_profile(name.strip(), theme_color=theme_rgb)
            self._rebuild_profile_combo()
            self._load_active_profile_ui()
            self._apply_current_profile_to_hardware()
            self.log_message(f"Nuevo perfil creado y activado: '{new_p.name}'")

    def _delete_current_profile(self):
        curr = self.profile_mgr.active_profile
        if len(self.profile_mgr.profiles) <= 1:
            QMessageBox.warning(self, "No permitido", "Debe existir al menos un perfil activo.")
            return

        res = QMessageBox.question(
            self,
            "Eliminar Perfil",
            f"¿Estás seguro de que deseas eliminar el perfil '{curr.name}'?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if res == QMessageBox.Yes:
            self.profile_mgr.delete_profile(curr.id)
            self._rebuild_profile_combo()
            self._load_active_profile_ui()
            self._apply_current_profile_to_hardware()
            self.log_message(f"Perfil eliminado: '{curr.name}'")

    def _change_profile_theme_color(self):
        curr = self.profile_mgr.active_profile
        color = QColorDialog.getColor(QColor(*curr.theme_color), self, f"Color Temático para '{curr.name}'")
        if color.isValid():
            rgb = (color.red(), color.green(), color.blue())
            self.profile_mgr.set_profile_theme_color(curr.id, rgb)
            self._load_active_profile_ui()
            self._apply_current_profile_to_hardware()
            self.log_message(f"Color temático de '{curr.name}' actualizado a RGB {rgb}.")

    def _apply_selected_color_to_all_keys(self):
        idx = self.selected_key_index
        curr = self.profile_mgr.active_profile
        col = curr.key_colors.get(idx, curr.theme_color)
        self.profile_mgr.set_profile_theme_color(curr.id, col)
        self._load_active_profile_ui()
        self._apply_current_profile_to_hardware()
        self.log_message(f"Pintadas todas las teclas del perfil '{curr.name}' con el color RGB {col}.")

    def _rebuild_profile_combo(self):
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        for p in self.profile_mgr.profiles:
            self.profile_combo.addItem(p.name, p.id)
        self.profile_combo.setCurrentIndex(self.profile_mgr.active_profile_index)
        self.profile_combo.blockSignals(False)
        self._rebuild_tray_profiles()

    def _on_profile_combo_changed(self, index: int):
        if index < 0 or index >= len(self.profile_mgr.profiles):
            return
        p = self.profile_mgr.profiles[index]
        self.profile_mgr.active_profile_index = index
        self.profile_mgr.save()
        self._load_active_profile_ui()
        self._apply_current_profile_to_hardware()

    def _select_profile_by_id(self, profile_id: str):
        p = self.profile_mgr.set_active_profile_by_id(profile_id)
        if p:
            self._load_active_profile_ui()
            self._apply_current_profile_to_hardware()

    def _cycle_profile(self):
        """Switch to next profile in order and apply to hardware."""
        p = self.profile_mgr.next_profile()
        self.log_message(f"¡CAMBIO DE PERFIL! Nuevo perfil activo: '{p.name}'")
        self._load_active_profile_ui()
        self._apply_current_profile_to_hardware()

        # Update tray icon and notify
        self.tray_icon.setIcon(create_tray_icon_pixmap(p.theme_color))
        self.tray_icon.showMessage("Perfil Cambiado", f"Nuevo perfil: {p.name}", QSystemTrayIcon.Information, 1200)

    def _load_active_profile_ui(self):
        p = self.profile_mgr.active_profile
        # Update combo without triggering infinite signal
        self.profile_combo.blockSignals(True)
        self.profile_combo.setCurrentIndex(self.profile_mgr.active_profile_index)
        self.profile_combo.blockSignals(False)

        hex_theme = f"#{p.theme_color[0]:02x}{p.theme_color[1]:02x}{p.theme_color[2]:02x}"
        self.profile_badge.setText(f"Perfil: {p.name}")
        self.profile_badge.setStyleSheet(f"background-color: {hex_theme}; color: #FFFFFF; font-weight: bold; padding: 3px 8px; border-radius: 4px;")
        self.tray_icon.setIcon(create_tray_icon_pixmap(p.theme_color))

        self._update_key_labels()
        self._update_table_view()
        self._rebuild_tray_profiles()

    def _update_key_labels(self):
        p = self.profile_mgr.active_profile
        for idx in range(6):
            if idx in self.key_buttons:
                cfg = p.key_bindings.get(idx)
                short_text = cfg.label.split("(")[0].strip() if cfg else "Vacía"
                col = p.key_colors.get(idx, p.theme_color)
                hex_c = f"#{col[0]:02x}{col[1]:02x}{col[2]:02x}"
                self.key_buttons[idx].setText(f"KEY {idx+1}\n[{short_text}]")
                self.key_buttons[idx].setStyleSheet(f"border: 2px solid {hex_c};")

        # Knob border
        k_col = p.key_colors.get(16, p.theme_color)
        hex_k = f"#{k_col[0]:02x}{k_col[1]:02x}{k_col[2]:02x}"
        if self.knob_button:
            self.knob_button.setStyleSheet(f"border: 3px solid {hex_k};")

    def _update_table_view(self):
        p = self.profile_mgr.active_profile
        self.keymap_table.setRowCount(len(PHYSICAL_KEYS))
        for r, (idx, label) in enumerate(PHYSICAL_KEYS):
            cfg = p.key_bindings.get(idx)
            action_desc = cfg.label if cfg else "No configurado"
            col = p.key_colors.get(idx, p.theme_color)
            hex_c = f"#{col[0]:02x}{col[1]:02x}{col[2]:02x}"

            self.keymap_table.setItem(r, 0, QTableWidgetItem(label))
            self.keymap_table.setItem(r, 1, QTableWidgetItem(action_desc))
            color_item = QTableWidgetItem(f"RGB {col}")
            color_item.setForeground(QColor(col[0], col[1], col[2]))
            self.keymap_table.setItem(r, 2, color_item)
            self.keymap_table.setItem(r, 3, QTableWidgetItem("Firmware Flash"))

    def _apply_current_profile_to_hardware(self):
        """Write entire active profile keybindings and colors to hardware."""
        try:
            self.profile_mgr.apply_to_hardware(self.protocol)
            self.log_message(f"Perfil '{self.profile_mgr.active_profile.name}' sincronizado con el hardware físico.")
        except Exception as e:
            self.log_message(f"Error aplicando perfil al hardware: {e}")

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()

        # F24 triggers profile switch!
        if key == Qt.Key_F24:
            self._cycle_profile()
            event.accept()
            return

        # F13..F18
        if Qt.Key_F13 <= key <= Qt.Key_F18:
            idx = key - Qt.Key_F13
            # If Key 6 (idx 5) is pressed and bound to profile switch
            if idx == 5:
                cfg = self.profile_mgr.active_profile.key_bindings.get(5)
                if cfg and cfg.is_profile_switch:
                    self._cycle_profile()
                    event.accept()
                    return
            self._trigger_key_visual(idx, f"F{13+idx}")
            event.accept()
            return

        # Numbers 1..6
        if Qt.Key_1 <= key <= Qt.Key_6:
            idx = key - Qt.Key_1
            if idx == 5:
                cfg = self.profile_mgr.active_profile.key_bindings.get(5)
                if cfg and cfg.is_profile_switch:
                    self._cycle_profile()
                    event.accept()
                    return
            self._trigger_key_visual(idx, f"'{idx+1}'")
            event.accept()
            return

        # Knob multimedia keys
        if key == Qt.Key_VolumeMute:
            self._trigger_knob_visual("Mute")
            event.accept()
            return
        elif key == Qt.Key_VolumeUp:
            self._trigger_knob_visual("Vol +")
            event.accept()
            return
        elif key == Qt.Key_VolumeDown:
            self._trigger_knob_visual("Vol -")
            event.accept()
            return

        super().keyPressEvent(event)

    def _trigger_key_visual(self, idx: int, name: str):
        if idx in self.key_buttons:
            btn = self.key_buttons[idx]
            p = self.profile_mgr.active_profile
            col = p.key_colors.get(idx, p.theme_color)
            hex_c = f"#{col[0]:02x}{col[1]:02x}{col[2]:02x}"
            btn.setStyleSheet(f"background-color: {hex_c}; color: #FFFFFF; border: 2px solid #FFFFFF;")
            QTimer.singleShot(250, lambda b=btn, c=hex_c: b.setStyleSheet(f"border: 2px solid {c};"))
            self.control_detail.setText(f"<font color='{hex_c}'><b>¡Tecla Física {idx+1} Pulsada!</b> Acción: {name}</font>")
            self.log_message(f"ENTRADA MACROPAD: Tecla Física {idx+1} ({name})")

    def _trigger_knob_visual(self, action: str):
        if self.knob_button:
            p = self.profile_mgr.active_profile
            col = p.key_colors.get(16, p.theme_color)
            hex_c = f"#{col[0]:02x}{col[1]:02x}{col[2]:02x}"
            self.knob_button.setStyleSheet(f"background-color: {hex_c}; color: #FFFFFF; border: 3px solid #FFFFFF;")
            QTimer.singleShot(250, lambda: self.knob_button.setStyleSheet(f"border: 3px solid {hex_c};"))
            self.control_detail.setText(f"<font color='{hex_c}'><b>¡Perilla Detectada!</b> Acción: {action}</font>")
            self.log_message(f"ENTRADA MACROPAD: Perilla ({action})")

    def _on_input_event(self, evt: InputEvent):
        """Handle incoming input events and highlight individual keys."""
        # Check for profile switch key (F24 or Key 6 configured as switch)
        if evt.vk_code == 0x87 or "F24" in evt.key_name:  # VK_F24
            self._cycle_profile()
            return

        # Check for Key 1..6 or F13..F18 from RawInput
        for i in range(6):
            if f"Key {i+1}" in evt.key_name or evt.key_name == f"Key F{13+i}":
                if i == 5 and self.profile_mgr.active_profile.key_bindings.get(5, KeyConfig(0,0,0,0)).is_profile_switch:
                    self._cycle_profile()
                    return
                self._trigger_key_visual(i, evt.key_name)
                return

        # Check for virtual key numbers '1'..'6'
        if ord('1') <= evt.vk_code <= ord('6'):
            idx = evt.vk_code - ord('1')
            if idx == 5 and self.profile_mgr.active_profile.key_bindings.get(5, KeyConfig(0,0,0,0)).is_profile_switch:
                self._cycle_profile()
                return
            self._trigger_key_visual(idx, f"'{chr(evt.vk_code)}'")
            return

        # Check for virtual key F13..F18
        if 0x7C <= evt.vk_code <= 0x81:
            idx = evt.vk_code - 0x7C
            if idx == 5 and self.profile_mgr.active_profile.key_bindings.get(5, KeyConfig(0,0,0,0)).is_profile_switch:
                self._cycle_profile()
                return
            self._trigger_key_visual(idx, f"F{13+idx}")
            return

        # Check knob
        if "Knob" in evt.key_name or evt.vk_code in (0xAD, 0xAE, 0xAF):
            action = "Mute" if evt.vk_code == 0xAD else ("Vol +" if evt.vk_code == 0xAF else "Vol -")
            self._trigger_knob_visual(action)
            return

    def scan_and_inspect(self):
        interfaces = self.discovery.enumerate_all()
        if not interfaces:
            self.status_badge.setText("Desconectado")
            self.status_badge.setObjectName("badgeWarn")
            self.status_badge.setStyle(self.status_badge.style())
            return

        self.status_badge.setText("Conectado (Hardware OK)")
        self.status_badge.setObjectName("badgeOk")
        self.status_badge.setStyle(self.status_badge.style())

        cfg_iface = self.discovery.find_config_interface()
        if cfg_iface and not self.transport.is_connected:
            try:
                self.transport.open(cfg_iface.path)
            except Exception as e:
                logger.error(f"Error opening transport: {e}")
