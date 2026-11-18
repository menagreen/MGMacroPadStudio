//! MacroPad Studio GUI — Native eframe/egui interface by MenaGreen
//! Features glassmorphic dark theme, glowing pads, rotary knob, per-key RGB picker,
//! profile management, and live USB HID synchronization.

use crate::autostart::AutostartManager;
use crate::profiles::{KeyConfig, ProfileManager};
use crate::protocol::SdcxDevice;
use eframe::egui::{self, Color32, Rect, Rounding, Stroke, Vec2};

const COLOR_MENA_GREEN: Color32 = Color32::from_rgb(0, 255, 136);
const COLOR_CYAN: Color32 = Color32::from_rgb(0, 229, 255);
const COLOR_BG_OBSIDIAN: Color32 = Color32::from_rgb(12, 16, 23);
const COLOR_PANEL_BG: Color32 = Color32::from_rgb(18, 23, 33);
const COLOR_CARD_BG: Color32 = Color32::from_rgb(24, 30, 43);

pub struct MacroPadApp {
    profile_mgr: ProfileManager,
    device: Option<SdcxDevice>,
    device_status: String,
    device_connected: bool,

    // UI state
    selected_key_idx: u8,
    selected_color: [f32; 3], // RGB 0..1 for picker
    autostart_enabled: bool,
    status_message: String,
    status_success: bool,

    // Dialog state for new profile
    show_new_profile_dialog: bool,
    new_profile_name: String,
}

impl MacroPadApp {
    pub fn new(_cc: &eframe::CreationContext<'_>) -> Self {
        // Try opening device
        let (device, connected, status) = match SdcxDevice::open_first() {
            Ok(dev) => (Some(dev), true, "Conectado (SDCX 6D80:DC81 MI_02)".to_string()),
            Err(e) => (None, false, format!("Desconectado ({e})")),
        };

        let profile_mgr = ProfileManager::load_from_paths();
        let autostart_enabled = AutostartManager::is_enabled();

        // Initial color from key 0
        let initial_rgb = if let Some(rgb) = profile_mgr.active_profile().key_colors.get("0") {
            [rgb.0 as f32 / 255.0, rgb.1 as f32 / 255.0, rgb.2 as f32 / 255.0]
        } else {
            [0.0, 1.0, 0.53] // MenaGreen
        };

        Self {
            profile_mgr,
            device,
            device_status: status,
            device_connected: connected,
            selected_key_idx: 0,
            selected_color: initial_rgb,
            autostart_enabled,
            status_message: "Listo.".to_string(),
            status_success: true,
            show_new_profile_dialog: false,
            new_profile_name: String::new(),
        }
    }

    fn apply_theme(&self, ctx: &egui::Context) {
        let mut visuals = egui::Visuals::dark();
        visuals.override_text_color = Some(Color32::from_rgb(235, 240, 248));
        visuals.window_fill = COLOR_BG_OBSIDIAN;
        visuals.panel_fill = COLOR_PANEL_BG;
        visuals.extreme_bg_color = Color32::from_rgb(8, 11, 16);
        visuals.widgets.noninteractive.bg_fill = COLOR_PANEL_BG;
        visuals.widgets.noninteractive.rounding = Rounding::same(8.0);
        visuals.widgets.inactive.bg_fill = COLOR_CARD_BG;
        visuals.widgets.inactive.rounding = Rounding::same(6.0);
        visuals.widgets.hovered.bg_fill = Color32::from_rgb(36, 45, 62);
        visuals.widgets.hovered.rounding = Rounding::same(6.0);
        visuals.widgets.active.bg_fill = Color32::from_rgb(0, 255, 136);
        visuals.widgets.active.fg_stroke.color = Color32::BLACK;
        ctx.set_visuals(visuals);
    }

    fn sync_to_hardware(&mut self) {
        if self.device.is_none() {
            self.device = SdcxDevice::open_first().ok();
        }

        if let Some(ref dev) = self.device {
            match self.profile_mgr.apply_to_hardware(dev) {
                Ok(_) => {
                    self.device_connected = true;
                    self.device_status = "Conectado (SDCX 6D80:DC81 MI_02)".to_string();
                    self.status_message = format!("¡Perfil '{}' sincronizado con el hardware físico!", self.profile_mgr.active_profile().name);
                    self.status_success = true;
                }
                Err(e) => {
                    self.status_message = format!("Error al escribir en dispositivo: {e}");
                    self.status_success = false;
                }
            }
        } else {
            self.device_connected = false;
            self.device_status = "Dispositivo no conectado".to_string();
            self.status_message = "Perfil guardado localmente (conecta el dispositivo para sincronizar)".to_string();
            self.status_success = true;
        }
    }
}

impl eframe::App for MacroPadApp {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        self.apply_theme(ctx);

        // TOP HEADER
        egui::TopBottomPanel::top("header_panel")
            .frame(egui::Frame::none().fill(COLOR_PANEL_BG).inner_margin(egui::Margin::symmetric(16.0, 12.0)))
            .show(ctx, |ui| {
                ui.horizontal(|ui| {
                    // Logo and Title
                    ui.heading(
                        egui::RichText::new("⚡ MacroPad Studio")
                            .color(COLOR_MENA_GREEN)
                            .strong()
                            .size(19.0),
                    );
                    ui.label(
                        egui::RichText::new("by MenaGreen")
                            .color(COLOR_CYAN)
                            .italics()
                            .size(13.0),
                    );

                    ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                        // Autostart toggle
                        let mut auto = self.autostart_enabled;
                        if ui.checkbox(&mut auto, egui::RichText::new("Iniciar con Windows").size(12.0)).changed() {
                            self.autostart_enabled = auto;
                            if auto {
                                let _ = AutostartManager::enable();
                            } else {
                                let _ = AutostartManager::disable();
                            }
                        }

                        ui.separator();

                        // Device Badge
                        if self.device_connected {
                            ui.label(
                                egui::RichText::new("● Conectado")
                                    .color(COLOR_MENA_GREEN)
                                    .strong()
                                    .size(12.0),
                            );
                        } else {
                            ui.label(
                                egui::RichText::new("○ Desconectado")
                                    .color(Color32::from_rgb(255, 87, 34))
                                    .size(12.0),
                            );
                        }
                    });
                });
            });

        // BOTTOM STATUS BAR
        egui::TopBottomPanel::bottom("status_bar")
            .frame(egui::Frame::none().fill(COLOR_BG_OBSIDIAN).inner_margin(egui::Margin::symmetric(14.0, 8.0)))
            .show(ctx, |ui| {
                ui.horizontal(|ui| {
                    let col = if self.status_success { COLOR_MENA_GREEN } else { Color32::from_rgb(255, 87, 34) };
                    ui.label(egui::RichText::new(&self.status_message).color(col).size(12.0));

                    ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                        ui.label(egui::RichText::new("SDCX Macropad | VID: 0x6D80 PID: 0xDC81").color(Color32::from_rgb(120, 135, 160)).size(11.0));
                    });
                });
            });

        // MAIN CENTRAL VIEW
        egui::CentralPanel::default()
            .frame(egui::Frame::none().fill(COLOR_BG_OBSIDIAN).inner_margin(egui::Margin::same(16.0)))
            .show(ctx, |ui| {
                ui.columns(2, |columns| {
                    // LEFT COLUMN: Visual Macropad (6 Keys + 1 Knob)
                    columns[0].vertical(|ui| {
                        ui.label(egui::RichText::new("PAD FÍSICO (Haz clic para seleccionar tecla)").color(Color32::from_rgb(180, 195, 215)).strong().size(13.0));
                        ui.add_space(8.0);

                        // Pad Container Card
                        egui::Frame::none()
                            .fill(COLOR_PANEL_BG)
                            .rounding(Rounding::same(12.0))
                            .stroke(Stroke::new(1.0_f32, Color32::from_rgb(34, 44, 62)))
                            .inner_margin(egui::Margin::same(18.0))
                            .show(ui, |ui| {
                                ui.vertical_centered(|ui| {
                                    // Row 1: Keys 1, 2, 3
                                    ui.horizontal(|ui| {
                                        ui.add_space(10.0);
                                        for idx in 0..3 {
                                            self.render_key_button(ui, idx);
                                            ui.add_space(12.0);
                                        }
                                    });

                                    ui.add_space(12.0);

                                    // Row 2: Keys 4, 5, 6
                                    ui.horizontal(|ui| {
                                        ui.add_space(10.0);
                                        for idx in 3..6 {
                                            self.render_key_button(ui, idx);
                                            ui.add_space(12.0);
                                        }
                                    });

                                    ui.add_space(20.0);
                                    ui.separator();
                                    ui.add_space(10.0);

                                    // Rotary Knob
                                    ui.horizontal(|ui| {
                                        ui.add_space(20.0);
                                        self.render_knob_button(ui, 16);
                                        ui.add_space(15.0);
                                        ui.vertical(|ui| {
                                            ui.label(egui::RichText::new("Perilla Rotativa").strong().size(13.0));
                                            ui.label(egui::RichText::new("• Giro Horario: Volumen +").color(Color32::from_rgb(160, 175, 195)).size(11.0));
                                            ui.label(egui::RichText::new("• Giro Antihorario: Volumen -").color(Color32::from_rgb(160, 175, 195)).size(11.0));
                                            ui.label(egui::RichText::new("• Pulsación: Silenciar Mic/Audio").color(COLOR_CYAN).size(11.0));
                                        });
                                    });
                                });
                            });

                        ui.add_space(12.0);

                        // Quick Flood Fill button
                        if ui.add(egui::Button::new(egui::RichText::new("✨ Pintar Todo el Pad con este Color").strong().color(Color32::BLACK)).fill(COLOR_MENA_GREEN)).clicked() {
                            let r = (self.selected_color[0] * 255.0) as u8;
                            let g = (self.selected_color[1] * 255.0) as u8;
                            let b = (self.selected_color[2] * 255.0) as u8;
                            let active_p = &mut self.profile_mgr.profiles[self.profile_mgr.active_index];
                            for k in 0..6 {
                                active_p.key_colors.insert(k.to_string(), (r, g, b));
                            }
                            for k in 16..19 {
                                active_p.key_colors.insert(k.to_string(), (r, g, b));
                            }
                            self.profile_mgr.save();
                            self.sync_to_hardware();
                        }
                    });

                    // RIGHT COLUMN: Configurator, Profiles, OBS & Color Picker
                    columns[1].vertical(|ui| {
                        // Profile Selector Header
                        ui.horizontal(|ui| {
                            ui.label(egui::RichText::new("Perfil Activo:").strong().size(14.0));

                            let active_name = self.profile_mgr.active_profile().name.clone();
                            egui::ComboBox::from_id_salt("profile_combo")
                                .selected_text(egui::RichText::new(&active_name).color(COLOR_MENA_GREEN).strong())
                                .show_ui(ui, |ui| {
                                    for i in 0..self.profile_mgr.profiles.len() {
                                        let name = self.profile_mgr.profiles[i].name.clone();
                                        if ui.selectable_label(self.profile_mgr.active_index == i, name).clicked() {
                                            self.profile_mgr.active_index = i;
                                            self.profile_mgr.save();
                                            self.sync_to_hardware();
                                        }
                                    }
                                });

                            if ui.button("+ Nuevo").clicked() {
                                self.show_new_profile_dialog = true;
                                self.new_profile_name = "Nuevo Perfil".to_string();
                            }

                            if self.profile_mgr.profiles.len() > 1 {
                                if ui.button(egui::RichText::new("🗑 Eliminar").color(Color32::from_rgb(255, 87, 87))).clicked() {
                                    self.profile_mgr.delete_active_profile();
                                    self.sync_to_hardware();
                                }
                            }
                        });

                        ui.add_space(8.0);

                        // Key Editor Box
                        let key_label = if self.selected_key_idx < 6 {
                            format!("TECLA FÍSICA {}", self.selected_key_idx + 1)
                        } else {
                            "PULSACIÓN DE PERILLA".to_string()
                        };

                        egui::Frame::none()
                            .fill(COLOR_PANEL_BG)
                            .rounding(Rounding::same(10.0))
                            .stroke(Stroke::new(1.0_f32, Color32::from_rgb(38, 48, 68)))
                            .inner_margin(egui::Margin::same(14.0))
                            .show(ui, |ui| {
                                ui.label(egui::RichText::new(&key_label).color(COLOR_CYAN).strong().size(13.0));
                                ui.add_space(6.0);

                                // Action selection
                                ui.label(egui::RichText::new("Asignar Acción:").size(12.0));
                                let current_binding = self.profile_mgr.active_profile().key_bindings.get(&self.selected_key_idx.to_string()).cloned();
                                let current_desc = current_binding.as_ref().map(|b| b.label.as_str()).unwrap_or("Sin asignar");

                                ui.label(egui::RichText::new(format!("Actual: {current_desc}")).color(Color32::WHITE).strong());
                                ui.add_space(4.0);

                                ui.horizontal_wrapped(|ui| {
                                    if ui.button("F13 (Mute OBS)").clicked() {
                                        self.set_key_action(self.selected_key_idx, 32, 0, 104, 0, "F13 (Mute OBS)", false);
                                    }
                                    if ui.button("F14 (Escena 1)").clicked() {
                                        self.set_key_action(self.selected_key_idx, 32, 0, 105, 0, "F14 (Escena 1)", false);
                                    }
                                    if ui.button("F15 (Escena 2)").clicked() {
                                        self.set_key_action(self.selected_key_idx, 32, 0, 106, 0, "F15 (Escena 2)", false);
                                    }
                                    if ui.button("F16 (Escena 3)").clicked() {
                                        self.set_key_action(self.selected_key_idx, 32, 0, 107, 0, "F16 (Escena 3)", false);
                                    }
                                    if ui.button("F17 (Rec)").clicked() {
                                        self.set_key_action(self.selected_key_idx, 32, 0, 108, 0, "F17 (Rec)", false);
                                    }
                                    if ui.button("Ctrl + C").clicked() {
                                        self.set_key_action(self.selected_key_idx, 32, 1, 6, 0, "Ctrl + C (Copiar)", false);
                                    }
                                    if ui.button("Ctrl + V").clicked() {
                                        self.set_key_action(self.selected_key_idx, 32, 1, 25, 0, "Ctrl + V (Pegar)", false);
                                    }
                                    if ui.button("Ctrl + Z").clicked() {
                                        self.set_key_action(self.selected_key_idx, 32, 1, 29, 0, "Ctrl + Z (Deshacer)", false);
                                    }
                                    if ui.button(egui::RichText::new("🔄 Cambio Perfil (F24)").color(COLOR_MENA_GREEN)).clicked() {
                                        self.set_key_action(self.selected_key_idx, 32, 0, 115, 0, "Cambio de Perfil (F24)", true);
                                    }
                                });

                                ui.add_space(10.0);
                                ui.separator();
                                ui.add_space(6.0);

                                // RGB Color Picker for this key
                                ui.label(egui::RichText::new("Color RGB de esta Tecla:").size(12.0));
                                ui.horizontal(|ui| {
                                    if ui.color_edit_button_rgb(&mut self.selected_color).changed() {
                                        let r = (self.selected_color[0] * 255.0) as u8;
                                        let g = (self.selected_color[1] * 255.0) as u8;
                                        let b = (self.selected_color[2] * 255.0) as u8;
                                        let p = &mut self.profile_mgr.profiles[self.profile_mgr.active_index];
                                        p.key_colors.insert(self.selected_key_idx.to_string(), (r, g, b));
                                        self.profile_mgr.save();
                                    }

                                    // Quick Color Swatches
                                    let swatches = [
                                        ("MenaGreen", (0, 255, 136)),
                                        ("Cyan", (0, 229, 255)),
                                        ("OBS Violet", (155, 93, 229)),
                                        ("Orange", (255, 87, 34)),
                                        ("Red", (255, 0, 85)),
                                        ("Blue", (0, 112, 243)),
                                        ("White", (255, 255, 255)),
                                    ];

                                    for (_name, (r, g, b)) in swatches {
                                        let c = Color32::from_rgb(r, g, b);
                                        if ui.add(egui::Button::new(" ").fill(c).min_size(Vec2::splat(18.0))).clicked() {
                                            self.selected_color = [r as f32 / 255.0, g as f32 / 255.0, b as f32 / 255.0];
                                            let p = &mut self.profile_mgr.profiles[self.profile_mgr.active_index];
                                            p.key_colors.insert(self.selected_key_idx.to_string(), (r, g, b));
                                            self.profile_mgr.save();
                                        }
                                    }
                                });
                            });

                        ui.add_space(14.0);

                        // Save & Hardware Sync Button
                        let save_btn = egui::Button::new(
                            egui::RichText::new("💾 GUARDAR Y APLICAR AL HARDWARE")
                                .color(Color32::BLACK)
                                .strong()
                                .size(14.0),
                        )
                        .fill(COLOR_MENA_GREEN)
                        .min_size(Vec2::new(ui.available_width(), 42.0));

                        if ui.add(save_btn).clicked() {
                            self.sync_to_hardware();
                        }
                    });
                });

                // New Profile Modal Dialog
                if self.show_new_profile_dialog {
                    egui::Window::new("Crear Nuevo Perfil")
                        .collapsible(false)
                        .resizable(false)
                        .anchor(egui::Align2::CENTER_CENTER, Vec2::ZERO)
                        .show(ctx, |ui| {
                            ui.label("Nombre del Perfil:");
                            ui.text_edit_singleline(&mut self.new_profile_name);
                            ui.add_space(8.0);
                            ui.horizontal(|ui| {
                                if ui.button("Crear").clicked() {
                                    if !self.new_profile_name.trim().is_empty() {
                                        self.profile_mgr.create_profile(&self.new_profile_name, (0, 255, 136));
                                        self.show_new_profile_dialog = false;
                                        self.sync_to_hardware();
                                    }
                                }
                                if ui.button("Cancelar").clicked() {
                                    self.show_new_profile_dialog = false;
                                }
                            });
                        });
                }
            });
    }
}

impl MacroPadApp {
    fn render_key_button(&mut self, ui: &mut egui::Ui, idx: u8) {
        let is_selected = self.selected_key_idx == idx;
        let p = self.profile_mgr.active_profile();
        let (r, g, b) = p.key_colors.get(&idx.to_string()).cloned().unwrap_or(p.theme_color);
        let key_color = Color32::from_rgb(r, g, b);

        let binding_label = p.key_bindings.get(&idx.to_string())
            .map(|k| k.label.as_str())
            .unwrap_or("Sin asignar");

        let size = Vec2::new(95.0, 72.0);
        let (rect, response) = ui.allocate_exact_size(size, egui::Sense::click());

        if response.clicked() {
            self.selected_key_idx = idx;
            self.selected_color = [r as f32 / 255.0, g as f32 / 255.0, b as f32 / 255.0];
        }

        let painter = ui.painter();

        // Keycap background
        let bg = if is_selected { Color32::from_rgb(32, 42, 60) } else { COLOR_CARD_BG };
        painter.rect_filled(rect, Rounding::same(8.0), bg);

        // Glowing Border matching assigned RGB
        let border_color = if is_selected { COLOR_MENA_GREEN } else { key_color };
        let border_width = if is_selected { 2.5_f32 } else { 1.5_f32 };
        painter.rect_stroke(rect, Rounding::same(8.0), Stroke::new(border_width, border_color));

        // Key Header
        painter.text(
            rect.center_top() + Vec2::new(0.0, 10.0),
            egui::Align2::CENTER_CENTER,
            format!("KEY {}", idx + 1),
            egui::FontId::proportional(12.0),
            Color32::WHITE,
        );

        // Binding text (truncated)
        let short_label = if binding_label.len() > 14 {
            format!("{}...", &binding_label[..12])
        } else {
            binding_label.to_string()
        };

        painter.text(
            rect.center() + Vec2::new(0.0, 5.0),
            egui::Align2::CENTER_CENTER,
            short_label,
            egui::FontId::proportional(10.0),
            Color32::from_rgb(170, 185, 205),
        );

        // Color indicator pill at bottom
        let pill_rect = Rect::from_center_size(rect.center_bottom() - Vec2::new(0.0, 8.0), Vec2::new(32.0, 4.0));
        painter.rect_filled(pill_rect, Rounding::same(2.0), key_color);
    }

    fn render_knob_button(&mut self, ui: &mut egui::Ui, idx: u8) {
        let is_selected = self.selected_key_idx == idx;
        let p = self.profile_mgr.active_profile();
        let (r, g, b) = p.key_colors.get(&idx.to_string()).cloned().unwrap_or(p.theme_color);
        let knob_color = Color32::from_rgb(r, g, b);

        let size = Vec2::new(65.0, 65.0);
        let (rect, response) = ui.allocate_exact_size(size, egui::Sense::click());

        if response.clicked() {
            self.selected_key_idx = idx;
            self.selected_color = [r as f32 / 255.0, g as f32 / 255.0, b as f32 / 255.0];
        }

        let painter = ui.painter();
        let center = rect.center();
        let radius = 28.0;

        // Outer glow
        painter.circle_filled(center, radius, Color32::from_rgb(28, 36, 50));
        let border_col = if is_selected { COLOR_MENA_GREEN } else { knob_color };
        painter.circle_stroke(center, radius, Stroke::new(if is_selected { 2.5_f32 } else { 1.5_f32 }, border_col));

        // Inner circle
        painter.circle_filled(center, radius * 0.65, Color32::from_rgb(18, 24, 34));

        // Center notch indicator
        painter.text(center, egui::Align2::CENTER_CENTER, "◉", egui::FontId::proportional(14.0), border_col);
    }

    fn set_key_action(&mut self, idx: u8, type_id: u8, code1: u8, code2: u8, code3: u8, label: &str, is_profile_switch: bool) {
        let p = &mut self.profile_mgr.profiles[self.profile_mgr.active_index];
        p.key_bindings.insert(idx.to_string(), KeyConfig {
            type_id,
            code1,
            code2,
            code3,
            label: label.to_string(),
            is_profile_switch,
        });
        self.profile_mgr.save();
        self.status_message = format!("Acción asignada a Tecla {}: {label}", idx + 1);
        self.status_success = true;
    }
}
