#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod autostart;
mod daemon;
mod hotkeys;
mod profiles;
mod protocol;
mod ui;

use hotkeys::HotkeyManager;
use profiles::ProfileManager;
use protocol::SdcxDevice;
use std::sync::{Arc, Mutex};
use ui::MacroPadApp;

fn main() -> Result<(), eframe::Error> {
    let args: Vec<String> = std::env::args().collect();
    let is_service = args.iter().any(|a| a == "--service" || a == "-s");

    if is_service {
        run_headless_service();
        Ok(())
    } else {
        run_gui()
    }
}

fn run_headless_service() {
    let device = match SdcxDevice::open_first() {
        Ok(dev) => Arc::new(Mutex::new(Some(dev))),
        Err(_) => Arc::new(Mutex::new(None)),
    };

    let profile_mgr = Arc::new(Mutex::new(ProfileManager::load_from_paths()));
    {
        let mgr = profile_mgr.lock().unwrap();
        if let Ok(guard) = device.lock() {
            if let Some(ref dev) = *guard {
                let _ = mgr.apply_to_hardware(dev);
            }
        }
    }

    let (hw_tx, hw_rx) = std::sync::mpsc::channel();
    let device_clone = Arc::clone(&device);
    let profile_mgr_clone = Arc::clone(&profile_mgr);

    // Dedicated hardware worker thread: runs independently from Windows hook path
    // Preventing Windows LowLevelHooksTimeout from ever killing the hook!
    std::thread::spawn(move || {
        while let Ok(()) = hw_rx.recv() {
            let mut mgr = profile_mgr_clone.lock().unwrap();
            let _ = mgr.next_profile();

            if let Ok(mut guard) = device_clone.lock() {
                if guard.is_none() {
                    *guard = SdcxDevice::open_first().ok();
                }
                if let Some(ref dev) = *guard {
                    let _ = mgr.apply_to_hardware(dev);
                }
            }
        }
    });

    HotkeyManager::run_loop(move || {
        let _ = hw_tx.send(());
    });
}

fn run_gui() -> Result<(), eframe::Error> {
    // Gracefully stop any running background service instance so GUI has exclusive hardware control
    crate::daemon::DaemonManager::stop_background_service();

    let mut viewport = eframe::egui::ViewportBuilder::default()
        .with_inner_size([880.0, 530.0])
        .with_min_inner_size([820.0, 480.0])
        .with_title("MacroPad Studio by MenaGreen");

    // Load MG Icon
    if let Ok(img) = image::load_from_memory(include_bytes!("../assets/icon.png")) {
        let rgba = img.to_rgba8();
        let (width, height) = rgba.dimensions();
        viewport = viewport.with_icon(eframe::egui::IconData {
            rgba: rgba.into_raw(),
            width,
            height,
        });
    }

    let native_options = eframe::NativeOptions {
        viewport,
        ..Default::default()
    };

    let result = eframe::run_native(
        "MacroPad Studio by MenaGreen",
        native_options,
        Box::new(|cc| Ok(Box::new(MacroPadApp::new(cc)))),
    );

    // When the GUI window closes, keep everything active by spawning the background service!
    crate::daemon::DaemonManager::spawn_background_service();

    result
}
