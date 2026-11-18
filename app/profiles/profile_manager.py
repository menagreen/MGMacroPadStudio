"""Profile storage and active profile management."""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.hid.protocol import (
    PHYSICAL_KEYS,
    SdcxProtocol,
    TYPE_CONSUMER,
    TYPE_STANDARD,
)

logger = logging.getLogger(__name__)

PROFILES_FILE = Path("data/profiles.json")


@dataclass
class KeyConfig:
    type_id: int
    code1: int
    code2: int
    code3: int
    label: str = ""
    is_profile_switch: bool = False


@dataclass
class Profile:
    id: str
    name: str
    description: str
    theme_color: Tuple[int, int, int]  # (R, G, B)
    light_mode: int  # 5 for Custom per-key, 1 Steady, 2 Breath, 4 Tidal
    light_brightness: int  # 0..4
    light_speed: int  # 0..4
    key_colors: Dict[int, Tuple[int, int, int]] = field(default_factory=dict)
    key_bindings: Dict[int, KeyConfig] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "theme_color": list(self.theme_color),
            "light_mode": self.light_mode,
            "light_brightness": self.light_brightness,
            "light_speed": self.light_speed,
            "key_colors": {str(k): list(v) for k, v in self.key_colors.items()},
            "key_bindings": {
                str(k): asdict(v) for k, v in self.key_bindings.items()
            },
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Profile:
        key_colors = {
            int(k): tuple(v) for k, v in data.get("key_colors", {}).items()
        }
        key_bindings = {
            int(k): KeyConfig(**v) for k, v in data.get("key_bindings", {}).items()
        }
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            theme_color=tuple(data.get("theme_color", [0, 173, 181])),
            light_mode=data.get("light_mode", 5),
            light_brightness=data.get("light_brightness", 4),
            light_speed=data.get("light_speed", 2),
            key_colors=key_colors,
            key_bindings=key_bindings,
        )


def generate_default_profiles() -> List[Profile]:
    """Create initial default profiles: General, OBS/Stream, Multimedia."""
    # 1. Profile: General / Productividad (Cyan)
    cyan = (0, 173, 181)
    p1_colors = {i: cyan for i in range(6)}
    p1_colors[16] = cyan
    p1_colors[17] = cyan
    p1_colors[18] = cyan
    p1_keys = {
        0: KeyConfig(TYPE_STANDARD, 1, 0x06, 0, "Ctrl + C (Copiar)"),
        1: KeyConfig(TYPE_STANDARD, 1, 0x19, 0, "Ctrl + V (Pegar)"),
        2: KeyConfig(TYPE_STANDARD, 1, 0x1D, 0, "Ctrl + Z (Deshacer)"),
        3: KeyConfig(TYPE_STANDARD, 0, 0x28, 0, "Enter"),
        4: KeyConfig(TYPE_STANDARD, 0, 0x2C, 0, "Espacio"),
        # Key 6 switches profile: bound to F24
        5: KeyConfig(TYPE_STANDARD, 0, 0x73, 0, "Cambio de Perfil (F24)", is_profile_switch=True),
        16: KeyConfig(TYPE_CONSUMER, 0xE2, 0, 0, "Silencio / Mute"),
        17: KeyConfig(TYPE_CONSUMER, 0xE9, 0, 0, "Subir Volumen"),
        18: KeyConfig(TYPE_CONSUMER, 0xEA, 0, 0, "Bajar Volumen"),
    }
    p1 = Profile(
        id="general",
        name="General / Productividad",
        description="Atajos diarios de oficina y edición.",
        theme_color=cyan,
        light_mode=5,
        light_brightness=4,
        light_speed=2,
        key_colors=p1_colors,
        key_bindings=p1_keys,
    )

    # 2. Profile: Streaming / OBS (Púrpura / Magenta)
    purple = (155, 93, 229)
    p2_colors = {i: purple for i in range(6)}
    p2_colors[16] = purple
    p2_colors[17] = purple
    p2_colors[18] = purple
    p2_keys = {
        0: KeyConfig(TYPE_STANDARD, 0, 0x68, 0, "F13 (Mute Mic OBS)"),
        1: KeyConfig(TYPE_STANDARD, 0, 0x69, 0, "F14 (Escena 1)"),
        2: KeyConfig(TYPE_STANDARD, 0, 0x6A, 0, "F15 (Escena 2)"),
        3: KeyConfig(TYPE_STANDARD, 0, 0x6B, 0, "F16 (Grabar)"),
        4: KeyConfig(TYPE_STANDARD, 0, 0x6C, 0, "F17 (Replay Buffer)"),
        5: KeyConfig(TYPE_STANDARD, 0, 0x73, 0, "Cambio de Perfil (F24)", is_profile_switch=True),
        16: KeyConfig(TYPE_CONSUMER, 0xE2, 0, 0, "Silencio / Mute"),
        17: KeyConfig(TYPE_CONSUMER, 0xE9, 0, 0, "Subir Volumen"),
        18: KeyConfig(TYPE_CONSUMER, 0xEA, 0, 0, "Bajar Volumen"),
    }
    p2 = Profile(
        id="obs_stream",
        name="Streaming / OBS",
        description="Teclas F13 a F17 dedicadas a transmisiones.",
        theme_color=purple,
        light_mode=5,
        light_brightness=4,
        light_speed=2,
        key_colors=p2_colors,
        key_bindings=p2_keys,
    )

    # 3. Profile: Multimedia / Música (Naranja / Fuego)
    orange = (255, 87, 34)
    p3_colors = {i: orange for i in range(6)}
    p3_colors[16] = orange
    p3_colors[17] = orange
    p3_colors[18] = orange
    p3_keys = {
        0: KeyConfig(TYPE_CONSUMER, 0xCD, 0, 0, "Play / Pause"),
        1: KeyConfig(TYPE_CONSUMER, 0xB6, 0, 0, "Pista Anterior"),
        2: KeyConfig(TYPE_CONSUMER, 0xB5, 0, 0, "Siguiente Pista"),
        3: KeyConfig(TYPE_CONSUMER, 0x24, 2, 0, "Navegador Atrás"),
        4: KeyConfig(TYPE_CONSUMER, 0x25, 2, 0, "Navegador Adelante"),
        5: KeyConfig(TYPE_STANDARD, 0, 0x73, 0, "Cambio de Perfil (F24)", is_profile_switch=True),
        16: KeyConfig(TYPE_CONSUMER, 0xE2, 0, 0, "Silencio / Mute"),
        17: KeyConfig(TYPE_CONSUMER, 0xE9, 0, 0, "Subir Volumen"),
        18: KeyConfig(TYPE_CONSUMER, 0xEA, 0, 0, "Bajar Volumen"),
    }
    p3 = Profile(
        id="multimedia",
        name="Multimedia & Música",
        description="Controles rápidos para Spotify, YouTube y navegador.",
        theme_color=orange,
        light_mode=5,
        light_brightness=4,
        light_speed=2,
        key_colors=p3_colors,
        key_bindings=p3_keys,
    )

    return [p1, p2, p3]


class ProfileManager:
    """Manages collection of profiles and synchronizes with hardware."""

    def __init__(self, storage_path: Path = PROFILES_FILE):
        self.storage_path = storage_path
        self.profiles: List[Profile] = []
        self.active_profile_index: int = 0
        self.load()

    def load(self) -> None:
        """Load profiles from JSON file or generate defaults."""
        if self.storage_path.exists():
            try:
                data = json.loads(self.storage_path.read_text(encoding="utf-8"))
                self.profiles = [Profile.from_dict(p) for p in data.get("profiles", [])]
                self.active_profile_index = data.get("active_index", 0)
                if not self.profiles:
                    self.profiles = generate_default_profiles()
            except Exception as e:
                logger.error(f"Error loading profiles: {e}")
                self.profiles = generate_default_profiles()
        else:
            self.profiles = generate_default_profiles()
            self.save()

    def save(self) -> None:
        """Persist profiles to disk."""
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "active_index": self.active_profile_index,
                "profiles": [p.to_dict() for p in self.profiles],
            }
            self.storage_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to save profiles: {e}")

    @property
    def active_profile(self) -> Profile:
        if 0 <= self.active_profile_index < len(self.profiles):
            return self.profiles[self.active_profile_index]
        return self.profiles[0]

    def set_active_profile_by_id(self, profile_id: str) -> Optional[Profile]:
        for i, p in enumerate(self.profiles):
            if p.id == profile_id:
                self.active_profile_index = i
                self.save()
                return p
        return None

    def next_profile(self) -> Profile:
        """Advance to next profile in round-robin order."""
        self.active_profile_index = (self.active_profile_index + 1) % len(self.profiles)
        self.save()
        return self.active_profile

    def create_profile(
        self,
        name: str,
        description: str = "",
        theme_color: Tuple[int, int, int] = (0, 173, 181),
    ) -> Profile:
        """Create a new profile initialized with standard keys and switch on Key 6."""
        import uuid
        profile_id = f"custom_{uuid.uuid4().hex[:8]}"
        colors = {i: theme_color for i in range(6)}
        colors[16] = theme_color
        colors[17] = theme_color
        colors[18] = theme_color

        keys = {
            0: KeyConfig(TYPE_STANDARD, 0, 0x1E, 0, "Número 1"),
            1: KeyConfig(TYPE_STANDARD, 0, 0x1F, 0, "Número 2"),
            2: KeyConfig(TYPE_STANDARD, 0, 0x20, 0, "Número 3"),
            3: KeyConfig(TYPE_STANDARD, 0, 0x21, 0, "Número 4"),
            4: KeyConfig(TYPE_STANDARD, 0, 0x22, 0, "Número 5"),
            5: KeyConfig(TYPE_STANDARD, 0, 0x73, 0, "Cambio de Perfil (F24)", is_profile_switch=True),
            16: KeyConfig(TYPE_CONSUMER, 0xE2, 0, 0, "Silencio / Mute"),
            17: KeyConfig(TYPE_CONSUMER, 0xE9, 0, 0, "Subir Volumen"),
            18: KeyConfig(TYPE_CONSUMER, 0xEA, 0, 0, "Bajar Volumen"),
        }

        new_profile = Profile(
            id=profile_id,
            name=name,
            description=description,
            theme_color=theme_color,
            light_mode=5,
            light_brightness=4,
            light_speed=2,
            key_colors=colors,
            key_bindings=keys,
        )
        self.profiles.append(new_profile)
        self.active_profile_index = len(self.profiles) - 1
        self.save()
        return new_profile

    def delete_profile(self, profile_id: str) -> bool:
        """Delete profile by ID, ensuring at least one profile remains."""
        if len(self.profiles) <= 1:
            return False
        for i, p in enumerate(self.profiles):
            if p.id == profile_id:
                del self.profiles[i]
                if self.active_profile_index >= len(self.profiles):
                    self.active_profile_index = len(self.profiles) - 1
                self.save()
                return True
        return False

    def set_profile_theme_color(self, profile_id: str, color: Tuple[int, int, int]) -> None:
        """Update profile theme color and apply to all keys."""
        for p in self.profiles:
            if p.id == profile_id:
                p.theme_color = color
                for k in range(6):
                    p.key_colors[k] = color
                p.key_colors[16] = color
                p.key_colors[17] = color
                p.key_colors[18] = color
                self.save()
                break

    def apply_to_hardware(self, protocol: SdcxProtocol, profile: Optional[Profile] = None) -> bool:
        """Write key assignments and per-key RGB colors of the profile into hardware flash."""
        target = profile or self.active_profile
        logger.info(f"Synchronizing profile '{target.name}' to macropad hardware...")

        # 1. Write Key Bindings
        for idx, cfg in target.key_bindings.items():
            protocol.set_key_binding(idx, cfg.type_id, cfg.code1, cfg.code2, cfg.code3)

        # 2. Write Per-Key RGB colors
        if target.light_mode == 5 and target.key_colors:
            protocol.set_all_key_colors(target.key_colors)
        else:
            # Apply global light effect
            protocol.set_light_config(
                target.light_mode,
                target.light_brightness,
                target.light_speed,
            )

        logger.info(f"Hardware synchronization for '{target.name}' complete.")
        return True
