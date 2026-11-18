mod hotkeys;
mod profiles;
mod protocol;

use hotkeys::{HotkeyManager, HOTKEY_F24};
use profiles::ProfileManager;
use protocol::SdcxDevice;
use std::sync::{Arc, Mutex};

fn print_banner() {
    println!("============================================================");
    println!(" MacroPad Studio Service (Rust Edition)");
    println!(" Daemon en segundo plano para Macropad SDCX (6D80:DC81)");
    println!("============================================================");
}

fn main() {
    print_banner();

    // 1. Initialize SDCX Macropad HID
    println!("[+] Buscando macropad USB HID 6D80:DC81...");
    let device = match SdcxDevice::open_first() {
        Ok(dev) => {
            println!("[✓] Macropad SDCX detectado y canal MI_02 abierto.");
            Arc::new(Mutex::new(Some(dev)))
        }
        Err(e) => {
            eprintln!("[-] Advertencia: {e}");
            eprintln!("    El servicio continuará y reintentará la conexión al detectar eventos.");
            Arc::new(Mutex::new(None))
        }
    };

    // 2. Load Profiles
    println!("[+] Cargando configuración de perfiles desde profiles.json...");
    let profile_mgr = Arc::new(Mutex::new(ProfileManager::load_from_paths()));
    {
        let mgr = profile_mgr.lock().unwrap();
        println!(
            "[✓] {} perfil(es) cargado(s). Perfil inicial: '{}' (Tema RGB: {:?})",
            mgr.profiles.len(),
            mgr.active_profile().name,
            mgr.active_profile().theme_color
        );

        if let Ok(guard) = device.lock() {
            if let Some(ref dev) = *guard {
                let _ = mgr.apply_to_hardware(dev);
            }
        }
    }

    // 3. Register Global System-Wide Hotkey (F24) for Profile Switching
    println!("[+] Registrando interceptor global para Tecla 6 (F24 - Cambio de Perfil)...");
    if HotkeyManager::register_profile_switcher() {
        println!("[✓] Interceptor global F24 activo en Windows.");
    } else {
        println!("[!] Nota: F24 ya estaba en uso o no se pudo registrar.");
    }

    println!("\n------------------------------------------------------------");
    println!(" SERVICIO EN SEGUNDO PLANO ACTIVO (Consumo de CPU: 0%)");
    println!(" - Tecla 6 (F24): Alterna perfiles y cambia LEDs físicamente.");
    println!(" - Teclas 1..5 (F13..F17): Pasan limpiamente a Windows/OBS.");
    println!(" - Funciona minimizado, en juegos o sin ventana abierta.");
    println!("");
    println!(" NOTA PARA OBS STUDIO:");
    println!(" En OBS -> Ajustes -> Avanzado -> Atajos:");
    println!(" Configura 'Comportamiento del foco de teclas rápidas':");
    println!(" -> 'No desactivar nunca las teclas de acceso rápido'");
    println!("------------------------------------------------------------\n");

    let device_clone = Arc::clone(&device);
    let profile_mgr_clone = Arc::clone(&profile_mgr);

    HotkeyManager::run_loop(move |hotkey_id| {
        if hotkey_id == HOTKEY_F24 {
            let mut mgr = profile_mgr_clone.lock().unwrap();
            let next_p = mgr.next_profile().clone();
            println!(
                "\n[⚡] CAMBIO DE PERFIL ACTIVADO (Tecla 6): '{}' (Color RGB: {:?})",
                next_p.name, next_p.theme_color
            );

            if let Ok(mut guard) = device_clone.lock() {
                if guard.is_none() {
                    *guard = SdcxDevice::open_first().ok();
                }
                if let Some(ref dev) = *guard {
                    if let Err(e) = mgr.apply_to_hardware(dev) {
                        eprintln!("[-] Error sincronizando con hardware: {e}");
                    } else {
                        println!("[✓] Hardware y LEDs actualizados físicamente al nuevo perfil.");
                    }
                }
            }
        }
    });

    HotkeyManager::unregister_all();
}
