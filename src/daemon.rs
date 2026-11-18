#![allow(dead_code)]
//! Daemon process management for background execution
//! Controls starting, stopping, and detecting the headless background service.

use std::os::windows::process::CommandExt;

const DETACHED_PROCESS: u32 = 0x00000008;
const CREATE_NO_WINDOW: u32 = 0x08000000;

pub struct DaemonManager;

impl DaemonManager {
    /// Spawns the current executable with `--service` in a detached, invisible background process.
    pub fn spawn_background_service() {
        if let Ok(exe) = std::env::current_exe() {
            let _ = std::process::Command::new(exe)
                .arg("--service")
                .creation_flags(DETACHED_PROCESS | CREATE_NO_WINDOW)
                .spawn();
        }
    }

    /// Stops any running background service instance so GUI mode can claim exclusive access to hardware.
    pub fn stop_background_service() {
        let my_pid = std::process::id();
        let cmd = format!(
            "Get-CimInstance Win32_Process -Filter \"Name = 'macropad-studio.exe'\" | Where-Object {{ $_.ProcessId -ne {} -and $_.CommandLine -like '*--service*' }} | ForEach-Object {{ Stop-Process -Id $_.ProcessId -Force }}",
            my_pid
        );
        let _ = std::process::Command::new("powershell")
            .args(["-NoProfile", "-NonInteractive", "-Command", &cmd])
            .creation_flags(CREATE_NO_WINDOW)
            .status();
    }

    /// Checks if a background service instance is currently running.
    pub fn is_service_running() -> bool {
        let my_pid = std::process::id();
        let cmd = format!(
            "(Get-CimInstance Win32_Process -Filter \"Name = 'macropad-studio.exe'\" | Where-Object {{ $_.ProcessId -ne {} -and $_.CommandLine -like '*--service*' }}).Count",
            my_pid
        );
        let output = std::process::Command::new("powershell")
            .args(["-NoProfile", "-NonInteractive", "-Command", &cmd])
            .creation_flags(CREATE_NO_WINDOW)
            .output();

        if let Ok(out) = output {
            let text = String::from_utf8_lossy(&out.stdout).trim().to_string();
            if let Ok(count) = text.parse::<u32>() {
                return count > 0;
            }
        }
        false
    }
}
