"""MacroPad Studio - Application Entry Point."""
from __future__ import annotations

import argparse
import logging
import sys
import time

from app.hid.discovery import HidDiscovery
from app.hid.transport import HidTransport
from app.hid.protocol import SdcxProtocol


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] (%(name)s) %(message)s",
        datefmt="%H:%M:%S",
    )


def run_cli_diagnostic():
    """Execute Phase 1 diagnostic and inspection directly in the console."""
    print("=" * 65)
    print(" MacroPad Studio — Diagnóstico de Hardware HID (Fase 1)")
    print(" Modo: Solo Lectura / Inspección Segura")
    print("=" * 65)

    discovery = HidDiscovery()
    interfaces = discovery.enumerate_all()

    if not interfaces:
        print("\n[!] No se encontró ningún dispositivo USB con VID 0x6D80 y PID 0xDC81.")
        print("    Asegúrate de que el macropad esté conectado.")
        return 1

    print(f"\n[+] Se encontraron {len(interfaces)} colecciones/interfaces HID:")
    for iface in interfaces:
        role = " [CANAL DE CONFIGURACIÓN]" if iface.is_config_channel else ""
        print(f"    - MI_{iface.interface_number:02d}: {iface.interface_description}{role}")
        print(f"      UsagePage: 0x{iface.usage_page:04X}, Usage: 0x{iface.usage:02X}")
        print(f"      Fabricante: {iface.manufacturer}, Producto: {iface.product}")

    cfg_iface = discovery.find_config_interface()
    if not cfg_iface:
        print("\n[-] Error: No se encontró la interfaz de configuración (MI_02, UsagePage 0xFF00).")
        return 1

    print(f"\n[+] Conectando al canal de configuración seguro: {cfg_iface.product}...")
    transport = HidTransport(read_only=True)
    try:
        transport.open(cfg_iface.path)
        protocol = SdcxProtocol(transport)

        print("[+] Leyendo configuración de hardware y firmware...")
        dev_cfg = protocol.get_device_config()
        print(f"    - Versión de Protocolo: {dev_cfg.version}")
        print(f"    - PID Reportado: 0x{dev_cfg.pid:04X}")
        print(f"    - Versión de Firmware: v{dev_cfg.firmware_version}")
        print(f"    - Esquemas / Perfiles soportados: {dev_cfg.profile_count} (Activo: {dev_cfg.active_profile})")
        print(f"    - Capas soportadas: {dev_cfg.layer_count} (Activa: {dev_cfg.active_layer})")
        print(f"    - Batería: {dev_cfg.battery_level}% (Cargando: {dev_cfg.is_charging})")

        print("\n[+] Leyendo configuración de iluminación RGB...")
        light = protocol.get_light_config()
        print(f"    - Modo: {light.mode} ({light.mode_name})")
        print(f"    - Brillo: {light.brightness} / 4")
        print(f"    - Velocidad: {light.speed} / 4")
        print(f"    - Dirección: {light.direction}")
        print(f"    - Tipo de color: {'Color único' if light.color_type else 'Arcoíris / Paleta'}")
        print(f"    - HSV: ({light.hue_degrees}°, {light.sat_percent}%, {light.val_percent}%)")

        print("\n[+] Leyendo asignaciones físicas de fábrica (Keymap Capa 0)...")
        bindings = protocol.get_keymap(0)
        for b in bindings:
            print(f"    - {b.label:25s} -> {b.description} [{b.type_name}] (Raw: {b.type_id}, 0x{b.code1:02X}, 0x{b.code2:02X}, 0x{b.code3:02X})")

    except Exception as e:
        print(f"[-] Error durante la inspección HID: {e}")
        return 1
    finally:
        transport.close()

    print("\n" + "=" * 65)
    print(" Inspección completada exitosamente.")
    print(" Para usar la interfaz gráfica completa y el monitor interactivo:")
    print("     python -m app.main")
    print("=" * 65 + "\n")
    return 0


def main():
    parser = argparse.ArgumentParser(description="MacroPad Studio — Configurador HID")
    parser.add_argument("--cli", action="store_true", help="Ejecutar en modo diagnóstico por consola")
    parser.add_argument("-v", "--verbose", action="store_true", help="Activar logging detallado de depuración")
    args = parser.parse_args()

    setup_logging(args.verbose)

    if args.cli:
        sys.exit(run_cli_diagnostic())

    # GUI Mode
    from PySide6.QtWidgets import QApplication
    from app.ui.diagnostic_window import DiagnosticWindow

    app = QApplication(sys.argv)
    window = DiagnosticWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
