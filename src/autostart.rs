//! Manages Windows user startup via HKCU\Software\Microsoft\Windows\CurrentVersion\Run

use std::ptr;
use windows_sys::Win32::Foundation::ERROR_SUCCESS;
use windows_sys::Win32::System::Registry::{
    RegCloseKey, RegDeleteValueW, RegOpenKeyExW, RegQueryValueExW, RegSetValueExW, HKEY,
    HKEY_CURRENT_USER, KEY_READ, KEY_WRITE, REG_SZ,
};

const RUN_SUBKEY: &str = "Software\\Microsoft\\Windows\\CurrentVersion\\Run\0";
const APP_NAME: &str = "MacroPadStudioService\0";

fn to_wide_chars(s: &str) -> Vec<u16> {
    s.encode_utf16().collect()
}

pub struct AutostartManager;

impl AutostartManager {
    /// Returns true if the service is currently registered to start with Windows.
    pub fn is_enabled() -> bool {
        unsafe {
            let subkey_w = to_wide_chars(RUN_SUBKEY);
            let name_w = to_wide_chars(APP_NAME);
            let mut hkey: HKEY = ptr::null_mut();

            if RegOpenKeyExW(HKEY_CURRENT_USER, subkey_w.as_ptr(), 0, KEY_READ, &mut hkey) == ERROR_SUCCESS {
                let mut data_type: u32 = 0;
                let mut data_len: u32 = 0;
                let status = RegQueryValueExW(
                    hkey,
                    name_w.as_ptr(),
                    ptr::null_mut(),
                    &mut data_type,
                    ptr::null_mut(),
                    &mut data_len,
                );
                RegCloseKey(hkey);
                status == ERROR_SUCCESS
            } else {
                false
            }
        }
    }

    /// Registers the executable with `--service` argument to run silently on user logon.
    pub fn enable() -> Result<(), String> {
        let exe_path = std::env::current_exe().map_err(|e| e.to_string())?;
        let cmd = format!("\"{}\" --service\0", exe_path.display());
        let cmd_w = to_wide_chars(&cmd);

        unsafe {
            let subkey_w = to_wide_chars(RUN_SUBKEY);
            let name_w = to_wide_chars(APP_NAME);
            let mut hkey: HKEY = ptr::null_mut();

            if RegOpenKeyExW(HKEY_CURRENT_USER, subkey_w.as_ptr(), 0, KEY_WRITE, &mut hkey) != ERROR_SUCCESS {
                return Err("No se pudo abrir la clave de registro HKCU Run para escritura.".into());
            }

            let status = RegSetValueExW(
                hkey,
                name_w.as_ptr(),
                0,
                REG_SZ,
                cmd_w.as_ptr() as *const u8,
                (cmd_w.len() * 2) as u32,
            );
            RegCloseKey(hkey);

            if status == ERROR_SUCCESS {
                Ok(())
            } else {
                Err(format!("Error en RegSetValueExW: código {status}"))
            }
        }
    }

    /// Removes the application from Windows startup.
    pub fn disable() -> Result<(), String> {
        unsafe {
            let subkey_w = to_wide_chars(RUN_SUBKEY);
            let name_w = to_wide_chars(APP_NAME);
            let mut hkey: HKEY = ptr::null_mut();

            if RegOpenKeyExW(HKEY_CURRENT_USER, subkey_w.as_ptr(), 0, KEY_WRITE, &mut hkey) != ERROR_SUCCESS {
                return Err("No se pudo abrir la clave de registro HKCU Run para eliminación.".into());
            }

            let status = RegDeleteValueW(hkey, name_w.as_ptr());
            RegCloseKey(hkey);

            if status == ERROR_SUCCESS {
                Ok(())
            } else {
                Err(format!("Error en RegDeleteValueW: código {status}"))
            }
        }
    }
}
