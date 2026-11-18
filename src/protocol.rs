#![allow(dead_code)]
use hidapi::{HidApi, HidDevice};
use std::collections::HashMap;

pub const DEFAULT_VID: u16 = 0x6D80;
pub const DEFAULT_PID: u16 = 0xDC81;
pub const CONFIG_USAGE_PAGE: u16 = 0xFF00;
pub const CONFIG_USAGE: u16 = 0x02;

#[derive(Debug, Clone)]
pub struct DeviceModel {
    pub vid: u16,
    pub pid: u16,
    pub name: &'static str,
    pub default_layout: &'static str,
}

pub const KNOWN_DEVICES: &[DeviceModel] = &[
    DeviceModel { vid: 0x6D80, pid: 0xDC81, name: "SDCX 6-Teclas + 1 Perilla", default_layout: "2x3" },
    DeviceModel { vid: 0x6D80, pid: 0xDC80, name: "SDCX 3-Teclas + 1 Perilla", default_layout: "1x3" },
    DeviceModel { vid: 0x6D80, pid: 0xDC82, name: "SDCX 9-Teclas + 2 Perillas", default_layout: "3x3" },
    DeviceModel { vid: 0x6D80, pid: 0xDC83, name: "SDCX 12-Teclas + 2 Perillas", default_layout: "3x4" },
    DeviceModel { vid: 0x6D80, pid: 0xDC84, name: "SDCX 16-Teclas (4x4)", default_layout: "4x4" },
    DeviceModel { vid: 0x1189, pid: 0x8890, name: "Chant Macropad Genérico", default_layout: "2x3" },
    DeviceModel { vid: 0x0483, pid: 0x5750, name: "STM32 HID Macropad Clon", default_layout: "2x3" },
    DeviceModel { vid: 0x3554, pid: 0xF509, name: "PCsensor USB Keypad", default_layout: "1x3" },
];

pub struct SdcxDevice {
    device: HidDevice,
    pub matched_name: String,
    pub vid: u16,
    pub pid: u16,
}

impl SdcxDevice {
    /// Opens the first detected compatible macropad.
    /// Checks known models first, then falls back to any vendor-defined HID interface (0xFF00).
    pub fn open_first() -> Result<Self, String> {
        Self::open_with_filter(None, None)
    }

    /// Opens device with optional custom VID / PID filter.
    pub fn open_with_filter(custom_vid: Option<u16>, custom_pid: Option<u16>) -> Result<Self, String> {
        let api = HidApi::new().map_err(|e| format!("Error al iniciar hidapi: {e}"))?;

        // 1. If custom filter provided, search specifically for that
        if let (Some(v), Some(p)) = (custom_vid, custom_pid) {
            for dev in api.device_list() {
                if dev.vendor_id() == v && dev.product_id() == p {
                    let is_config = (dev.usage_page() == CONFIG_USAGE_PAGE && dev.usage() == CONFIG_USAGE)
                        || dev.interface_number() == 2
                        || dev.interface_number() == 0;

                    if is_config {
                        let device = dev.open_device(&api).map_err(|e| format!("Error abriendo dispositivo: {e}"))?;
                        return Ok(Self {
                            device,
                            matched_name: format!("Personalizado (0x{v:04X}:0x{p:04X})"),
                            vid: v,
                            pid: p,
                        });
                    }
                }
            }
        }

        // 2. Search against known compatible models table
        for known in KNOWN_DEVICES {
            for dev in api.device_list() {
                if dev.vendor_id() == known.vid && dev.product_id() == known.pid {
                    let is_config = (dev.usage_page() == CONFIG_USAGE_PAGE && dev.usage() == CONFIG_USAGE)
                        || dev.interface_number() == 2;

                    if is_config {
                        let device = dev.open_device(&api).map_err(|e| format!("Error abriendo {}: {e}", known.name))?;
                        return Ok(Self {
                            device,
                            matched_name: known.name.to_string(),
                            vid: known.vid,
                            pid: known.pid,
                        });
                    }
                }
            }
        }

        // 3. Fallback Heuristic: Any vendor-defined HID collection (UsagePage 0xFF00, Usage 0x02)
        for dev in api.device_list() {
            if dev.usage_page() == CONFIG_USAGE_PAGE && dev.usage() == CONFIG_USAGE && dev.vendor_id() != 0 {
                let v = dev.vendor_id();
                let p = dev.product_id();
                if let Ok(device) = dev.open_device(&api) {
                    return Ok(Self {
                        device,
                        matched_name: format!("Genérico 0xFF00:0x02 (0x{v:04X}:0x{p:04X})"),
                        vid: v,
                        pid: p,
                    });
                }
            }
        }

        Err("No se detectó ningún macropad compatible en el sistema.".to_string())
    }

    pub fn transfer(&self, group: u8, sub: u8, payload: &[u8]) -> Result<[u8; 64], String> {
        let mut wire = [0u8; 65]; // report_id 0 + 64 data bytes
        wire[0] = 0x00; // report ID 0
        wire[1] = group;
        wire[2] = sub;

        for (i, &b) in payload.iter().enumerate() {
            if 3 + i < wire.len() {
                wire[3 + i] = b;
            }
        }

        self.device.write(&wire).map_err(|e| format!("HID write failed: {e}"))?;

        let mut resp = [0u8; 64];
        let bytes_read = self.device.read_timeout(&mut resp, 1000).map_err(|e| format!("HID read failed: {e}"))?;
        if bytes_read == 0 {
            return Err("HID read timeout: device did not respond".to_string());
        }

        Ok(resp)
    }

    pub fn set_key_binding(&self, key_idx: u8, type_id: u8, c1: u8, c2: u8, c3: u8) -> Result<(), String> {
        let offset = (key_idx as u16) * 4;
        let payload = [
            7,
            (offset & 0xFF) as u8,
            ((offset >> 8) & 0xFF) as u8,
            0,
            0, // layer
            0,
            type_id,
            c1,
            c2,
            c3,
        ];

        let resp = self.transfer(0x06, 16, &payload)?;
        if resp[0] == 0xAA {
            Ok(())
        } else {
            Err(format!("Device returned unexpected response: 0x{:02X}", resp[0]))
        }
    }

    pub fn set_light_config(&self, mode: u8, brightness: u8, speed: u8) -> Result<(), String> {
        let bri = brightness.clamp(0, 4);
        let spd = speed.clamp(0, 4);
        let m = mode.clamp(0, 5);

        let cfg = [1, 0, m, bri, spd, 0, 0, 0, 0, 255, 255];
        let mut payload = vec![11, 0, 0];
        payload.extend_from_slice(&cfg);

        let resp = self.transfer(0x06, 11, &payload)?;
        if resp[0] == 0xAA {
            Ok(())
        } else {
            Err("Device failed to confirm light config".to_string())
        }
    }

    pub fn set_key_color(&self, key_idx: u8, r: u8, g: u8, b: u8) -> Result<(), String> {
        let offset = (key_idx as u16) * 3;
        let payload = [
            3,
            (offset & 0xFF) as u8,
            ((offset >> 8) & 0xFF) as u8,
            0,
            0,
            0,
            r,
            g,
            b,
        ];

        let resp = self.transfer(0x06, 20, &payload)?;
        if resp[0] == 0xAA {
            Ok(())
        } else {
            Err("Device failed to confirm key color".to_string())
        }
    }

    pub fn set_all_key_colors(&self, colors: &HashMap<u8, (u8, u8, u8)>) -> Result<(), String> {
        // Ensure Light Mode 5 (Custom Per-Key RGB) is active with full brightness
        let _ = self.set_light_config(5, 4, 2);
        std::thread::sleep(std::time::Duration::from_millis(15));

        for (&idx, &(r, g, b)) in colors {
            let _ = self.set_key_color(idx, r, g, b);
            std::thread::sleep(std::time::Duration::from_millis(8));
        }
        Ok(())
    }
}
