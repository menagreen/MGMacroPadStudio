# ⚡ MacroPad Studio by MenaGreen

<p align="center">
  <img src="assets/icon.png" width="128" height="128" alt="MG Logo" />
  <br>
  <b>Configurador USB HID y Daemon en Segundo Plano para Windows 11</b>
  <br>
  <i>Diseñado para Macropads SDCX de 6 teclas mecánicas + 1 perilla rotativa con RGB</i>
</p>

<p align="center">
  <a href="https://github.com/menagreen/MGMacroPadStudio/releases"><img src="https://img.shields.io/badge/Release-v1.0.0-00FF88?style=for-the-badge" alt="Release" /></a>
  <img src="https://img.shields.io/badge/Platform-Windows%2011-00E5FF?style=for-the-badge&logo=windows" alt="Platform" />
  <img src="https://img.shields.io/badge/Rust-2021%20Edition-black?style=for-the-badge&logo=rust" alt="Rust" />
  <img src="https://img.shields.io/badge/License-MIT-white?style=for-the-badge" alt="License" />
</p>

---

## 🌟 Características

- ⚡ **100% Rust Nativo:** Un solo ejecutable sin dependencias externas, Python ni frameworks pesados.
- 🎨 **Interfaz Moderna Cyberpunk:** Tema oscuro estilo obsidiana/acrílico con efectos neón MenaGreen (`#00FF88`) y Cyan (`#00E5FF`).
- 🔘 **Visualizador Interactivo:** Representación visual de 6 teclas mecánicas y 1 perilla rotativa con iluminación RGB dinámica por tecla.
- 🌈 **Control de Iluminación RGB:**
  - Selector de color individual por tecla.
  - Paleta rápida con presets de streaming y gaming.
  - Botón de pintado masivo ("Pintar Todo el Pad").
  - Modos de luz (Personalizado por tecla, Estático, Respiración, Arcoíris) con control de brillo y velocidad.
- 🎬 **Integración para Streaming y OBS:**
  - Asignación rápida de teclas `F13` a `F18` para cambio de escenas, mute de micrófono y grabación sin conflictos con teclados estándar.
- 🔄 **Cambio Dinámico de Perfiles:**
  - Tecla física 6 configurada como ciclo de perfiles con cambio de color físico instantáneo.
  - Creación y eliminación de perfiles persistentes en `data/profiles.json`.
- 🪟 **Servicio en Segundo Plano Invisible:**
  - Puede ejecutarse como servicio en segundo plano con **0% de consumo de CPU** y **~5 MB de RAM**.
  - Funciona con juegos en pantalla completa y ventanas minimizadas.
  - Opción de inicio automático con Windows en 1 clic.

---

## 🔌 Hardware Compatible

- **Familia:** SDCX / SDINNOVATION USB Macropad
- **Identificadores:** `VID: 0x6D80` | `PID: 0xDC81`
- **Canal de Configuración:** `MI_02` (Vendor-Defined HID, UsagePage: `0xFF00`, Usage: `0x02`)
- **Protocolo:** Comunicación directa por reportes de 64 bytes (`Group 0x06`) sin requerir drivers WinUSB ni Zadig.

---

## 🚀 Uso Rápido

### Descargar y Ejecutar
1. Descarga el paquete `MacroPadStudio-v1.0.0-windows-x64.zip` desde [Releases](https://github.com/menagreen/MGMacroPadStudio/releases).
2. Descomprime en la carpeta de tu preferencia.
3. Ejecuta `MacroPadStudio.exe` para abrir el configurador visual.

### Modo Daemon / Servicio en Segundo Plano
Para ejecutar el daemon en segundo plano que escucha los atajos globales y gestiona el cambio de perfil sin interfaz gráfica:
```powershell
.\MacroPadStudio.exe --service
```

O instala el inicio automático permanente con Windows usando el script incluido:
```powershell
.\scripts\install-service.ps1
```

---

## ⚙️ Configuración para OBS Studio

Para que OBS cambie escenas cuando estés dentro de un juego o con OBS en segundo plano:
1. En OBS Studio ve a **Ajustes** → **Avanzado** → sección **Atajos**.
2. En **Comportamiento del foco de teclas rápidas**, selecciona:
   👉 **"No desactivar nunca las teclas de acceso rápido"**.
3. En **Ajustes** → **Atajos**, asigna tus escenas a las teclas `F13` a `F18`.

---

## 🛠️ Compilación desde el Código Fuente

Requisitos: [Rust y Cargo](https://rustup.rs/) (Windows x64).

```bash
# Clonar el repositorio
git clone https://github.com/menagreen/MGMacroPadStudio.git
cd MGMacroPadStudio

# Compilar en modo Release optimizado
cargo build --release

# El binario se genera en:
# target/release/macropad-studio.exe
```

---

## 📜 Licencia

Distribuido bajo la Licencia MIT. Consulta el archivo [LICENSE](LICENSE) para más detalles.

Desarrollado por **MenaGreen**.
