# ⚡ MacroPad Studio by MenaGreen

<p align="center">
  <img src="assets/icon.png" width="128" height="128" alt="MG Logo" />
  <br>
  <b>Standalone USB HID Configurator & Lightweight Windows Background Daemon</b>
  <br>
  <i>Designed for SDCX 6-Key Mechanical Macropads + Rotary Knob with RGB Lighting</i>
  <br><br>
  <a href="#english">English</a> • <a href="#español">Español</a>
</p>

---

<a name="english"></a>
## 🇬🇧 English

### Overview
**MacroPad Studio by MenaGreen** is a fast, standalone Windows 11 utility written in pure Rust. It allows you to configure physical key mappings, per-key RGB lighting, rotary knob actions, and profiles for low-cost SDCX mechanical macropads without relying on proprietary Chinese software or cloud tools.

### Key Features
- **100% Native Rust:** Single portable `.exe` with zero external dependencies, no Python runtime, and low memory usage (~5 MB RAM, 0% CPU).
- **Dual Mode (GUI & Service):**
  - **Interactive GUI:** GPU-accelerated dark cyber interface built with `egui` to tweak lighting, bindings, and profiles.
  - **Background Daemon (`--service`):** Invisible background listener for global hotkeys (F13–F18, OBS scenes, F24 profile cycling) that works while gaming or with windows minimized.
- **Per-Key RGB Lighting:** Individual color picker, quick color presets (MenaGreen, Cyan, OBS Violet, Orange, Red, Blue), and batch fill.
- **Hardware Profile Cycling:** Map Key 6 to cycle profiles on hardware with instant LED theme changes.
- **OBS Studio Friendly:** Dedicated shortcuts (`F13`–`F18`) to toggle mute, switch scenes, and control recordings without conflicting with typing keyboards.
- **Windows Autostart:** One-click toggle in the UI or via PowerShell script to run silently on user login (`HKCU Run`).

### Hardware Specifications
- **VID:** `0x6D80` | **PID:** `0xDC81` (SDCX / SDINNOVATION)
- **Interface:** `MI_02` (Vendor-Defined HID, Usage Page: `0xFF00`, Usage: `0x02`)
- **Protocol:** 64-byte raw HID reports (`Group 0x06`) over native Windows HID driver (no WinUSB/Zadig required).

### Quick Start
1. Download `MacroPadStudio-v1.0.0-windows-x64.zip` from [Releases](https://github.com/menagreen/MGMacroPadStudio/releases).
2. Extract and run `MacroPadStudio.exe`.
3. Select any key to assign shortcuts, customize colors, and click **Guardar y Aplicar al Hardware**.

### OBS Studio Setup (for Background Scene Switching)
1. In OBS Studio, open **Settings** → **Advanced** → **Hotkeys**.
2. Under **Hotkey Focus Behavior**, choose **"Never disable hotkeys"**.
3. In **Settings** → **Hotkeys**, bind your scenes or mute toggles to `F13` through `F18`.

### Building from Source
Requires [Rust and Cargo](https://rustup.rs/) on Windows x64:
```bash
git clone https://github.com/menagreen/MGMacroPadStudio.git
cd MGMacroPadStudio
cargo build --release
```
The optimized executable will be located at `target/release/macropad-studio.exe`.

---

<a name="español"></a>
## 🇪🇸 Español

### Descripción
**MacroPad Studio by MenaGreen** es una herramienta nativa para Windows 11 desarrollada en Rust puro. Permite configurar atajos de teclado físicos, iluminación RGB por tecla, acciones de la perilla rotativa y múltiples perfiles para macropads mecánicos SDCX sin depender de software privativo ni navegadores web.

### Características Principales
- **100% Rust Nativo:** Un solo ejecutable portátil sin dependencias externas, sin Python y con consumo mínimo (~5 MB de RAM, 0% CPU).
- **Modo Dual (GUI y Servicio):**
  - **Configurador Visual:** Interfaz moderna estilo obsidiana/acrílico acelerada por GPU (`egui`) para personalizar colores, atajos y perfiles.
  - **Daemon de Fondo (`--service`):** Escucha atajos globales en segundo plano (`F13` a `F18`, cambio de escenas de OBS y `F24` para alternar perfiles) funcionando en juegos a pantalla completa o con ventanas minimizadas.
- **Iluminación RGB por Tecla:** Selector libre de color RGB, paleta con presets rápidos (MenaGreen, Cyan, OBS Violeta, etc.) y botón para pintar todo el pad.
- **Cambio de Perfil por Hardware:** Tecla 6 configurada para rotar perfiles en la memoria física con cambio de color instantáneo.
- **Optimizado para OBS Studio:** Asignación directa de teclas `F13` a `F18` para silenciar micrófono, cambiar escenas e iniciar grabación sin colisiones con tu teclado principal.
- **Inicio Automático en Windows:** Interruptor de activación en la interfaz o mediante script para inicio silencioso al encender la PC (`HKCU Run`).

### Especificaciones de Hardware
- **VID:** `0x6D80` | **PID:** `0xDC81` (SDCX / SDINNOVATION)
- **Interfaz:** `MI_02` (Vendor-Defined HID, Usage Page: `0xFF00`, Usage: `0x02`)
- **Protocolo:** Reportes directos de 64 bytes (`Grupo 0x06`) utilizando el controlador nativo de Windows (sin drivers Zadig ni WinUSB).

### Guía de Inicio Rápido
1. Descarga el paquete `MacroPadStudio-v1.0.0-windows-x64.zip` desde [Releases](https://github.com/menagreen/MGMacroPadStudio/releases).
2. Descomprime y ejecuta `MacroPadStudio.exe`.
3. Selecciona cualquier tecla física, asigna su acción y color, y pulsa **Guardar y Aplicar al Hardware**.

### Configuración en OBS Studio (para cambio de escena minimizado)
1. En OBS Studio ve a **Ajustes** → **Avanzado** → sección **Atajos**.
2. En **Comportamiento del foco de teclas rápidas**, selecciona **"No desactivar nunca las teclas de acceso rápido"**.
3. En **Ajustes** → **Atajos**, vincula tus escenas a `F13` hasta `F18`.

### Compilación desde el Código
Requiere [Rust y Cargo](https://rustup.rs/) en Windows x64:
```bash
git clone https://github.com/menagreen/MGMacroPadStudio.git
cd MGMacroPadStudio
cargo build --release
```
El ejecutable compilado se generará en `target/release/macropad-studio.exe`.

---

## 📜 License / Licencia
MIT License. Developed by **MenaGreen**.
