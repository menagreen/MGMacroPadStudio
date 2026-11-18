use hidapi::{HidApi, HidDevice};
use std::collections::HashMap;

pub const DEFAULT_VID: u16 = 0x6D80;
pub const DEFAULT_PID: u16 = 0xDC81;
pub const CONFIG_USAGE_PAGE: u16 = 0xFF00;
pub const CONFIG_USAGE: u16 = 0x02;

pub struct SdcxDevice {
    device: HidDevice,
}

impl SdcxDevice {
    pub fn open_first() -> Result<Self, String> {
        let api = HidApi::new().map_err(|e| format!("Failed to init hidapi: {e}"))?;

        for dev in api.device_list() {
            if dev.vendor_id() == DEFAULT_VID && dev.product_id() == DEFAULT_PID {
                let is_config = (dev.usage_page() == CONFIG_USAGE_PAGE && dev.usage() == CONFIG_USAGE)
                    || dev.interface_number() == 2;

                if is_config {
                    let device = dev.open_device(&api).map_err(|e| format!("Failed to open device: {e}"))?;
                    return Ok(Self { device });
                }
            }
        }

        Err("No SDCX Macropad config interface (MI_02) found.".to_string())
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
        self.set_light_config(5, 4, 2)?;
        for (&idx, &(r, g, b)) in colors {
            let _ = self.set_key_color(idx, r, g, b);
        }
        Ok(())
    }
}
