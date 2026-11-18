#[cfg(windows)]
fn main() {
    if std::path::Path::new("assets/icon.ico").exists() {
        let mut res = winres::WindowsResource::new();
        res.set_icon("assets/icon.ico");
        res.set("ProductName", "MacroPad Studio by MenaGreen");
        res.set("FileDescription", "MacroPad Studio — USB HID Configurator & Daemon");
        res.set("LegalCopyright", "Copyright (C) 2026 MenaGreen");
        let _ = res.compile();
    }
}

#[cfg(not(windows))]
fn main() {}
