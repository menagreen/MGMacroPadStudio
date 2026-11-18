use windows_sys::Win32::UI::Input::KeyboardAndMouse::{RegisterHotKey, UnregisterHotKey, MOD_NOREPEAT};
use windows_sys::Win32::UI::WindowsAndMessaging::{GetMessageW, MSG, WM_HOTKEY};

pub const HOTKEY_F24: i32 = 1024;
pub const VK_F24: u32 = 0x87;

pub struct HotkeyManager;

impl HotkeyManager {
    /// Registers only the profile switcher hotkey (F24) so that action keys
    /// (F13..F18, multimedia, Ctrl shortcuts) pass through freely to Windows,
    /// OBS Studio, and games without being swallowed by the OS.
    pub fn register_profile_switcher() -> bool {
        unsafe {
            let ok = RegisterHotKey(std::ptr::null_mut(), HOTKEY_F24, MOD_NOREPEAT, VK_F24);
            if ok == 0 {
                eprintln!("[-] Advertencia: No se pudo registrar la hotkey F24 (posible conflicto o permisos).");
                false
            } else {
                true
            }
        }
    }

    pub fn unregister_all() {
        unsafe {
            UnregisterHotKey(std::ptr::null_mut(), HOTKEY_F24);
        }
    }

    pub fn run_loop<F: FnMut(i32)>(mut callback: F) {
        unsafe {
            let mut msg: MSG = std::mem::zeroed();
            loop {
                let res = GetMessageW(&mut msg, std::ptr::null_mut(), 0, 0);
                if res <= 0 {
                    // res == 0 means WM_QUIT; res == -1 means error
                    let err = windows_sys::Win32::Foundation::GetLastError();
                    let _ = std::fs::write("service_exit.log", format!("GetMessageW returned {res}, GetLastError={err}\n"));
                    break;
                }
                if msg.message == WM_HOTKEY {
                    let hotkey_id = msg.wParam as i32;
                    callback(hotkey_id);
                }
            }
        }
    }
}
