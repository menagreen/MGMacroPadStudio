# MacroPad Studio

Aplicación de escritorio nativa para Windows (Windows 11) diseñada para inspeccionar, diagnosticar, configurar y administrar macropads USB económicos basados en el ecosistema **SDCX / SDINNOVATION** (`VID: 0x6D80`, `PID: 0xDC81`).

---

## Estado del Proyecto — Fase 1: Investigación y Detección HID

La **Fase 1** está completada y validada contra hardware físico real conectado al sistema.

### Capacidades Verificadas en Hardware Real:
- **Detección automática USB:** Enumeración de las 7 colecciones/interfaces HID expuestas por el dispositivo compuesto (`MI_00`, `MI_01`, `MI_02`).
- **Aislamiento seguro del canal de configuración:** Identificación precisa de la interfaz `MI_02` (`UsagePage: 0xFF00`, `Usage: 0x02`, Vendor-Defined), la cual no está bloqueada por el subsistema de teclado de Windows.
- **Protocolo SDCX implementado (Solo Lectura):**
  - **Información del dispositivo:** Lectura de versión de protocolo, firmware (v104), estado de enlace, batería (100%), perfiles (6 esquemas).
  - **Iluminación RGB:** Lectura del modo activo (`Tidal`, brillo 4/4, velocidad 2/4, paleta HSV).
  - **Mapa de teclas físico (Keymap):** Lectura de las 6 teclas físicas (configuradas de fábrica como `Ctrl + A` en `TYPE_STANDARD`) y los 3 estados del encoder rotatorio / perilla (Giro horario: `Volume Up`, Giro antihorario: `Volume Down`, Pulsación: `Mute`).
- **Monitor de entrada en tiempo real:** Captura no invasiva de eventos de teclado y perilla en Windows sin interferir con otros periféricos.
- **Seguridad estricta:** Capa de transporte con bloqueo por lista blanca (`read_only=True`) que prohíbe cualquier comando de escritura o flasheo en esta fase.

---

## Arquitectura

```text
MacroPad Studio/
├── app/
│   ├── main.py                     # Punto de entrada CLI / GUI
│   ├── hid/
│   │   ├── discovery.py            # Enumeración y filtrado de interfaces HID
│   │   ├── transport.py            # Transporte raw con framing de reporte 0 y modo seguro
│   │   └── protocol.py             # Decodificador del protocolo SDCX y keycodes
│   ├── ui/
│   │   └── diagnostic_window.py    # Interfaz gráfica moderna en PySide6 (Dark Theme)
│   └── diagnostics/
│       └── event_monitor.py        # Monitor de eventos de teclado y perilla en tiempo real
├── tests/
│   ├── test_discovery.py           # Pruebas unitarias de descubrimiento
│   ├── test_transport.py           # Pruebas unitarias de transporte y modo seguro
│   └── test_protocol.py            # Pruebas unitarias de decodificación de tramas
├── docs/
│   └── PHASE_1_REPORT.md           # Informe técnico detallado de la Fase 1
├── requirements.txt
├── pyproject.toml
└── README.md
```

---

## Requisitos e Instalación

### Requisitos:
- Windows 10 / 11 (64-bit)
- Python 3.12+ (Probado en Python 3.13)
- Macropad USB `6D80:DC81` conectado

### Instalación de dependencias:
```powershell
pip install -r requirements.txt
```

---

## Ejecución

### 1. Interfaz Gráfica (Recomendado):
```powershell
python -m app.main
```
Abre la ventana de diagnóstico con el macropad visual, estado de hardware, tabla de interfaces, configuración leída del firmware y monitor de eventos en tiempo real.

### 2. Modo Consola / Diagnóstico Rápido:
```powershell
python -m app.main --cli
```
Muestra en consola el volcado completo de hardware, firmware, iluminación, keymap y queda escuchando eventos de teclas y perilla hasta presionar `Ctrl + C`.

### 3. Ejecutar Pruebas Unitarias:
```powershell
python -m pytest -v
```
