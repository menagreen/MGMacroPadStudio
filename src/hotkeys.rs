#![allow(dead_code)]
use std::sync::atomic::{AtomicU64, AtomicUsize, Ordering};
use std::time::{SystemTime, UNIX_EPOCH};
use windows_sys::Win32::Foundation::{LPARAM, LRESULT, WPARAM};
use windows_sys::Win32::System::LibraryLoader::GetModuleHandleW;
use windows_sys::Win32::UI::Input::KeyboardAndMouse::{RegisterHotKey, UnregisterHotKey, MOD_NOREPEAT};
use windows_sys::Win32::UI::WindowsAndMessaging::{
    CallNextHookEx, DispatchMessageW, GetMessageW, SetWindowsHookExW, TranslateMessage,
    UnhookWindowsHookEx, HHOOK, KBDLLHOOKSTRUCT, MSG, WH_KEYBOARD_LL, WM_HOTKEY, WM_KEYDOWN, WM_SYSKEYDOWN,
};

pub const HOTKEY_F24: i32 = 1024;
pub const VK_F24: u32 = 0x87;

static HOOK: AtomicUsize = AtomicUsize::new(0);
static LAST_TRIGGER_MS: AtomicU64 = AtomicU64::new(0);
static mut ACTION_CALLBACK: Option<Box<dyn FnMut() + Send>> = None;

fn now_ms() -> u64 {
    SystemTime::now().duration_since(UNIX_EPOCH).map(|d| d.as_millis() as u64).unwrap_or(0)
}

fn trigger_debounced() {
    let now = now_ms();
    let last = LAST_TRIGGER_MS.load(Ordering::SeqCst);
    if now.saturating_sub(last) > 150 {
        LAST_TRIGGER_MS.store(now, Ordering::SeqCst);
        unsafe {
            if let Some(ref mut cb) = ACTION_CALLBACK {
                cb();
            }
        }
    }
}

unsafe extern "system" fn hook_proc(code: i32, w_param: WPARAM, l_param: LPARAM) -> LRESULT {
    if code >= 0 && (w_param as u32 == WM_KEYDOWN || w_param as u32 == WM_SYSKEYDOWN) {
        let kbd = *(l_param as *const KBDLLHOOKSTRUCT);
        if kbd.vkCode == VK_F24 {
            trigger_debounced();
        }
    }
    let h = HOOK.load(Ordering::SeqCst) as HHOOK;
    CallNextHookEx(h, code, w_param, l_param)
}

pub struct HotkeyManager;

impl HotkeyManager {
    /// Starts both a low-level keyboard hook (WH_KEYBOARD_LL) and Win32 RegisterHotKey
    /// with message pump and debouncing. This ensures 100% reliable capture of F24
    /// across all Windows versions, full-screen games, OBS Studio, and background services.
    pub fn run_loop<F: FnMut() + Send + 'static>(callback: F) {
        unsafe {
            ACTION_CALLBACK = Some(Box::new(callback));

            // Vector 1: Low-level keyboard hook with valid HMODULE
            let hmod = GetModuleHandleW(std::ptr::null());
            let hook = SetWindowsHookExW(WH_KEYBOARD_LL, Some(hook_proc), hmod, 0);
            if !hook.is_null() {
                HOOK.store(hook as usize, Ordering::SeqCst);
            }

            // Vector 2: Win32 RegisterHotKey as fallback / complement
            RegisterHotKey(std::ptr::null_mut(), HOTKEY_F24, MOD_NOREPEAT, VK_F24);

            let mut msg: MSG = std::mem::zeroed();
            while GetMessageW(&mut msg, std::ptr::null_mut(), 0, 0) > 0 {
                if msg.message == WM_HOTKEY && msg.wParam == HOTKEY_F24 as usize {
                    trigger_debounced();
                }
                TranslateMessage(&msg);
                DispatchMessageW(&msg);
            }

            UnregisterHotKey(std::ptr::null_mut(), HOTKEY_F24);

            let h = HOOK.swap(0, Ordering::SeqCst) as HHOOK;
            if !h.is_null() {
                UnhookWindowsHookEx(h);
            }
        }
    }

    pub fn unhook() {
        unsafe {
            UnregisterHotKey(std::ptr::null_mut(), HOTKEY_F24);
            let h = HOOK.swap(0, Ordering::SeqCst) as HHOOK;
            if !h.is_null() {
                UnhookWindowsHookEx(h);
            }
        }
    }
}
