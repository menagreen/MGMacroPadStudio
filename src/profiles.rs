use crate::protocol::SdcxDevice;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KeyConfig {
    pub type_id: u8,
    pub code1: u8,
    pub code2: u8,
    pub code3: u8,
    #[serde(default)]
    pub label: String,
    #[serde(default)]
    pub is_profile_switch: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Profile {
    pub id: String,
    pub name: String,
    #[serde(default)]
    pub description: String,
    pub theme_color: (u8, u8, u8),
    #[serde(default = "default_mode")]
    pub light_mode: u8,
    #[serde(default = "default_bri")]
    pub light_brightness: u8,
    #[serde(default = "default_spd")]
    pub light_speed: u8,
    #[serde(default)]
    pub key_colors: HashMap<String, (u8, u8, u8)>,
    #[serde(default)]
    pub key_bindings: HashMap<String, KeyConfig>,
}

fn default_mode() -> u8 { 5 }
fn default_bri() -> u8 { 4 }
fn default_spd() -> u8 { 2 }

#[derive(Debug, Serialize, Deserialize)]
pub struct ProfilesDocument {
    pub active_index: usize,
    pub profiles: Vec<Profile>,
}

pub struct ProfileManager {
    file_path: PathBuf,
    pub profiles: Vec<Profile>,
    pub active_index: usize,
}

impl ProfileManager {
    pub fn load_from_paths() -> Self {
        let mut candidates = vec![
            PathBuf::from("data/profiles.json"),
            PathBuf::from("../data/profiles.json"),
            PathBuf::from("profiles.json"),
        ];

        if let Ok(exe) = std::env::current_exe() {
            if let Some(dir) = exe.parent() {
                candidates.push(dir.join("data/profiles.json"));
                candidates.push(dir.join("profiles.json"));
                if let Some(p2) = dir.parent() {
                    candidates.push(p2.join("data/profiles.json"));
                    if let Some(p3) = p2.parent() {
                        candidates.push(p3.join("data/profiles.json"));
                    }
                }
            }
        }

        for path in &candidates {
            if path.exists() {
                if let Ok(content) = fs::read_to_string(path) {
                    if let Ok(doc) = serde_json::from_str::<ProfilesDocument>(&content) {
                        if !doc.profiles.is_empty() {
                            return Self {
                                file_path: path.clone(),
                                profiles: doc.profiles,
                                active_index: doc.active_index,
                            };
                        }
                    }
                }
            }
        }

        // Fallback default profiles if no file found
        let (p1, p2, p3) = Self::defaults();
        Self {
            file_path: PathBuf::from("data/profiles.json"),
            profiles: vec![p1, p2, p3],
            active_index: 0,
        }
    }

    fn defaults() -> (Profile, Profile, Profile) {
        let mut p1_colors = HashMap::new();
        let mut p1_keys = HashMap::new();
        for i in 0..6 {
            p1_colors.insert(i.to_string(), (0, 173, 181));
        }
        p1_keys.insert("5".to_string(), KeyConfig {
            type_id: 32,
            code1: 0,
            code2: 0x73, // F24
            code3: 0,
            label: "Cambio de Perfil (F24)".to_string(),
            is_profile_switch: true,
        });

        let p1 = Profile {
            id: "general".to_string(),
            name: "General / Productividad".to_string(),
            description: "Perfil General".to_string(),
            theme_color: (0, 173, 181),
            light_mode: 5,
            light_brightness: 4,
            light_speed: 2,
            key_colors: p1_colors,
            key_bindings: p1_keys,
        };

        let mut p2_colors = HashMap::new();
        let mut p2_keys = HashMap::new();
        for i in 0..6 {
            p2_colors.insert(i.to_string(), (155, 93, 229));
            p2_keys.insert(i.to_string(), KeyConfig {
                type_id: 32,
                code1: 0,
                code2: 0x68 + i, // F13..F18
                code3: 0,
                label: format!("F{}", 13 + i),
                is_profile_switch: i == 5,
            });
        }
        let p2 = Profile {
            id: "obs_stream".to_string(),
            name: "Streaming / OBS".to_string(),
            description: "Perfil OBS F13-F18".to_string(),
            theme_color: (155, 93, 229),
            light_mode: 5,
            light_brightness: 4,
            light_speed: 2,
            key_colors: p2_colors,
            key_bindings: p2_keys,
        };

        let mut p3_colors = HashMap::new();
        for i in 0..6 {
            p3_colors.insert(i.to_string(), (255, 87, 34));
        }
        let p3 = Profile {
            id: "multimedia".to_string(),
            name: "Multimedia".to_string(),
            description: "Perfil Multimedia".to_string(),
            theme_color: (255, 87, 34),
            light_mode: 5,
            light_brightness: 4,
            light_speed: 2,
            key_colors: p3_colors,
            key_bindings: HashMap::new(),
        };

        (p1, p2, p3)
    }

    pub fn reload(&mut self) {
        if self.file_path.exists() {
            if let Ok(content) = fs::read_to_string(&self.file_path) {
                if let Ok(doc) = serde_json::from_str::<ProfilesDocument>(&content) {
                    if !doc.profiles.is_empty() {
                        self.profiles = doc.profiles;
                        if self.active_index >= self.profiles.len() {
                            self.active_index = doc.active_index.min(self.profiles.len() - 1);
                        }
                    }
                }
            }
        }
    }

    pub fn active_profile(&self) -> &Profile {
        if self.active_index < self.profiles.len() {
            &self.profiles[self.active_index]
        } else {
            &self.profiles[0]
        }
    }

    pub fn next_profile(&mut self) -> &Profile {
        self.reload();
        if !self.profiles.is_empty() {
            self.active_index = (self.active_index + 1) % self.profiles.len();
            self.save();
        }
        self.active_profile()
    }

    pub fn save(&self) {
        let doc = ProfilesDocument {
            active_index: self.active_index,
            profiles: self.profiles.clone(),
        };
        if let Ok(json_str) = serde_json::to_string_pretty(&doc) {
            let _ = fs::write(&self.file_path, json_str);
        }
    }

    pub fn create_profile(&mut self, name: &str, theme_color: (u8, u8, u8)) {
        let id = format!("profile_{}", self.profiles.len() + 1);
        let mut key_colors = HashMap::new();
        for i in 0..6 {
            key_colors.insert(i.to_string(), theme_color);
        }
        for i in 16..19 {
            key_colors.insert(i.to_string(), theme_color);
        }

        let mut key_bindings = HashMap::new();
        // Default Key 6 as profile switcher
        key_bindings.insert("5".to_string(), KeyConfig {
            type_id: 32,
            code1: 0,
            code2: 115, // F24
            code3: 0,
            label: "Cambio de Perfil (F24)".to_string(),
            is_profile_switch: true,
        });

        let new_p = Profile {
            id,
            name: name.to_string(),
            description: format!("Perfil {}", name),
            theme_color,
            light_mode: 5,
            light_brightness: 4,
            light_speed: 2,
            key_colors,
            key_bindings,
        };

        self.profiles.push(new_p);
        self.active_index = self.profiles.len() - 1;
        self.save();
    }

    pub fn delete_active_profile(&mut self) -> bool {
        if self.profiles.len() > 1 {
            self.profiles.remove(self.active_index);
            if self.active_index >= self.profiles.len() {
                self.active_index = self.profiles.len() - 1;
            }
            self.save();
            true
        } else {
            false
        }
    }

    pub fn apply_to_hardware(&self, dev: &SdcxDevice) -> Result<(), String> {
        let p = self.active_profile();
        println!("[+] Aplicando perfil '{}' al hardware...", p.name);

        // 1. Write key bindings
        for (k_str, cfg) in &p.key_bindings {
            if let Ok(idx) = k_str.parse::<u8>() {
                dev.set_key_binding(idx, cfg.type_id, cfg.code1, cfg.code2, cfg.code3)?;
            }
        }

        // 2. Write RGB colors
        if p.light_mode == 5 {
            let mut colors = HashMap::new();
            for (k_str, &rgb) in &p.key_colors {
                if let Ok(idx) = k_str.parse::<u8>() {
                    colors.insert(idx, rgb);
                }
            }
            dev.set_all_key_colors(&colors)?;
        } else {
            dev.set_light_config(p.light_mode, p.light_brightness, p.light_speed)?;
        }

        println!("[+] Perfil '{}' aplicado exitosamente al hardware.", p.name);
        Ok(())
    }
}
