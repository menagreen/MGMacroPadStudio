"""Unit tests for profile manager and hardware synchronization."""
from unittest.mock import MagicMock
from pathlib import Path
import tempfile
import json

from app.profiles.profile_manager import ProfileManager, Profile, KeyConfig
from app.hid.protocol import TYPE_STANDARD, TYPE_CONSUMER


def test_profile_defaults():
    with tempfile.TemporaryDirectory() as tmp_dir:
        test_file = Path(tmp_dir) / "test_profiles.json"
        mgr = ProfileManager(storage_path=test_file)

        assert len(mgr.profiles) == 3
        assert mgr.active_profile.id == "general"
        assert test_file.exists()


def test_profile_cycle_next():
    with tempfile.TemporaryDirectory() as tmp_dir:
        test_file = Path(tmp_dir) / "test_profiles.json"
        mgr = ProfileManager(storage_path=test_file)

        p1 = mgr.active_profile.id
        p2 = mgr.next_profile().id
        p3 = mgr.next_profile().id
        p4 = mgr.next_profile().id

        assert p1 == "general"
        assert p2 == "obs_stream"
        assert p3 == "multimedia"
        assert p4 == "general"  # Round-robin cycle


def test_apply_profile_to_hardware():
    with tempfile.TemporaryDirectory() as tmp_dir:
        test_file = Path(tmp_dir) / "test_profiles.json"
        mgr = ProfileManager(storage_path=test_file)

        proto = MagicMock()
        proto.set_key_binding.return_value = True
        proto.set_all_key_colors.return_value = True

        ok = mgr.apply_to_hardware(proto)
        assert ok
        assert proto.set_key_binding.called
        assert proto.set_all_key_colors.called


def test_create_and_delete_profile():
    with tempfile.TemporaryDirectory() as tmp_dir:
        test_file = Path(tmp_dir) / "test_profiles.json"
        mgr = ProfileManager(storage_path=test_file)

        created = mgr.create_profile("Valorant", "Profile for FPS", (255, 0, 0))
        assert created.name == "Valorant"
        assert len(mgr.profiles) == 4
        assert mgr.active_profile.id == created.id
        assert mgr.active_profile.theme_color == (255, 0, 0)

        # Delete it
        ok = mgr.delete_profile(created.id)
        assert ok
        assert len(mgr.profiles) == 3


def test_set_profile_theme_color():
    with tempfile.TemporaryDirectory() as tmp_dir:
        test_file = Path(tmp_dir) / "test_profiles.json"
        mgr = ProfileManager(storage_path=test_file)

        mgr.set_profile_theme_color("general", (100, 200, 50))
        assert mgr.profiles[0].theme_color == (100, 200, 50)
        assert mgr.profiles[0].key_colors[0] == (100, 200, 50)

