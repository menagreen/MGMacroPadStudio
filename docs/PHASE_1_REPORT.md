# Informe Técnico: Fase 1 — Investigación y Detección HID

## 1. Identificación del Hardware

El dispositivo analizado es un macropad mecánico USB con 6 teclas y 1 perilla giratoria (con pulsador integrado) comercializado como modelo SDCX / HCY-K006.

- **Vendor ID (VID):** `0x6D80`
- **Product ID (PID):** `0xDC81`
- **Revisión USB:** `0x0100` (Release 256)
- **Fabricante reportado:** `SDINNOVATION`
- **Producto reportado (MI_02):** `SIDE-KEYBOARD`
- **Número de serie USB:** `475620678182`

---

## 2. Topología de Interfaces HID en Windows

Windows detecta el dispositivo como un dispositivo compuesto USB (`USB\VID_6D80&PID_DC81`) con 3 interfaces lógicas (`MI_00`, `MI_01`, `MI_02`) y un total de 7 colecciones HID:

| Interfaz / Colección | Usage Page | Usage ID | Descripción de la Colección | Comportamiento en Windows |
|---|---|---|---|---|
| `MI_00 & Col01` | `0x0001` (Generic Desktop) | `0x06` (Keyboard) | Teclado estándar HID | Bloqueado por el driver de teclado del sistema para lecturas directas |
| `MI_00 & Col02` | `0x0001` (Generic Desktop) | `0x02` (Mouse) | Ratón compatible con HID | Disponible para reportes de ratón estándar |
| `MI_00 & Col03` | `0x000C` (Consumer) | `0x01` (Consumer Control) | Control multimedia y volumen | Emite eventos de volumen y silencio de la perilla |
| `MI_00 & Col04` | `0x0001` (Generic Desktop) | `0x80` (System Control) | Control del sistema (Power/Sleep) | Soporta teclas de suspensión/apagado |
| `MI_00 & Col05` | `0x0001` (Generic Desktop) | `0x0C` (Wireless Radio) | Controles de radio inalámbrica | Función en modelos inalámbricos |
| `MI_01` | `0x0001` (Generic Desktop) | `0x06` (Keyboard) | Teclado secundario (Conflict-free/NKRO) | Teclado de arranque y salida de LED |
| **`MI_02`** | **`0xFF00`** (Vendor-Defined) | **`0x02`** (Vendor Usage) | **Canal de Configuración del Fabricante** | **Canal bidireccional accesible (64 bytes de reporte)** |

---

## 3. Protocolo de Comunicación del Canal de Configuración (`MI_02`)

### 3.1 Encuadre y Transporte
- **Tamaño de reporte:** Exactamente 64 bytes para entradas y salidas.
- **Report ID:** `0`. En Windows `hidapi`, el reporte de salida se envía como un búfer de 65 bytes con byte 0 igual a `0x00`.
- **Estructura de la trama:**
  - `Byte 0`: Grupo de comando (`0x06` = Configuración general).
  - `Byte 1`: Subcomando.
  - `Bytes 2..63`: Parámetros y relleno con ceros (`0x00`).
- **Respuesta:**
  - `Byte 0`: `0xAA` (Acknowledge / encabezado del dispositivo).
  - `Byte 1`: Identificador del subcomando de respuesta.
  - `Byte 2`: Longitud del payload.
  - `Bytes 5..`: Datos de respuesta.

### 3.2 Comandos de Lectura Verificados en Hardware Real

#### 1. Consulta de Configuración del Dispositivo (`Subcomando 5`)
- Trama enviada: `[0x06, 0x05] + 62 ceros`
- Respuesta obtenida:
  - Protocolo: versión 1
  - PID: `0xDC81`
  - Firmware: `v104` (0x0068)
  - Esquemas de perfil admitidos: `6` (Perfil activo: 0)
  - Capas admitidas: `1`
  - Batería: `100%`

#### 2. Consulta de Iluminación RGB (`Subcomando 10`)
- Trama enviada: `[0x06, 0x0A] + 62 ceros`
- Configuración leída del hardware:
  - Modo: `4` (`Tidal` / Marea de colores)
  - Brillo: `4 / 4` (Máximo)
  - Velocidad: `2 / 4`
  - Dirección: `0`
  - Tipo de color: `0` (Paleta dinámica)
  - HSV: Hue 255 (360°), Sat 255 (100%), Val 255 (100%)

#### 3. Lectura de Mapeo de Teclas Físicas (`Subcomando 8`)
- Cada tecla física se almacena como un bloque de 4 bytes: `[Tipo, Código1, Código2, Código3]`.
- Se transfieren bloques de 56 bytes útiles por petición (`READ_CHUNK`).
- Mapeo de fábrica verificado:
  - **Tecla 1 (Fila 1, Col 1, Índice 0):** `[32, 1, 4, 0]` -> `Ctrl + A` (Tipo 32 = Teclado estándar, 1 = LCtrl, 4 = HID 'A')
  - **Tecla 2 (Fila 1, Col 2, Índice 1):** `[32, 1, 4, 0]` -> `Ctrl + A`
  - **Tecla 3 (Fila 1, Col 3, Índice 2):** `[32, 1, 4, 0]` -> `Ctrl + A`
  - **Tecla 4 (Fila 2, Col 1, Índice 3):** `[32, 1, 4, 0]` -> `Ctrl + A`
  - **Tecla 5 (Fila 2, Col 2, Índice 4):** `[32, 1, 4, 0]` -> `Ctrl + A`
  - **Tecla 6 (Fila 2, Col 3, Índice 5):** `[32, 1, 4, 0]` -> `Ctrl + A`
  - **Perilla - Pulsación (Índice 16):** `[48, 226, 0, 0]` -> `Silencio / Mute` (Tipo 48 = Consumer Control, 0x00E2 = Mute)
  - **Perilla - Giro Horario (Índice 17):** `[48, 233, 0, 0]` -> `Subir Volumen / Volume Increment` (0x00E9 = Volume Up)
  - **Perilla - Giro Antihorario (Índice 18):** `[48, 234, 0, 0]` -> `Bajar Volumen / Volume Decrement` (0x00EA = Volume Down)

---

## 4. Pruebas y Validación Realizadas

1. **Pruebas de Enumeración y Transporte:**
   - Descubrimiento de las 7 interfaces mediante `hidapi`.
   - Apertura no exclusiva de `MI_02` sin interferir con la entrada normal de Windows.
2. **Pruebas de Seguridad (Read-Only Guard):**
   - El módulo `HidTransport` verifica que cualquier intento de enviar un comando fuera de la lista blanca de lectura genere `ReadOnlyViolationError`.
3. **Pruebas Unitarias Automatizadas:**
   - 7 pruebas unitarias ejecutadas con `pytest` pasando al 100% (mock de hardware y validación de tipos).
4. **Validación en Vivo contra el Hardware Físico:**
   - Ejecución de comandos de lectura en tiempo real con respuestas idénticas y consistentes en cada consulta.
