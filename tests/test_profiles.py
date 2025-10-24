"""
Tests for the ProfileManager class
"""
import pytest
import json
from pathlib import Path
from neozen.core.profiles import ProfileManager


class TestProfileManager:
    """Test suite for ProfileManager"""

    def test_profile_manager_initialization(self, tmp_path):
        """Test that ProfileManager initializes with correct path"""
        # Create a temporary profile manager with custom path
        manager = ProfileManager("test_profiles.json")
        assert manager.profile_path is not None
        assert isinstance(manager.profile_path, Path)

    def test_load_profiles_nonexistent_file(self, tmp_path, monkeypatch):
        """Test loading profiles when file doesn't exist"""
        # Change to temp directory
        monkeypatch.chdir(tmp_path)
        manager = ProfileManager("nonexistent.json")
        profiles = manager.load_profiles()
        assert profiles == {}

    def test_save_and_load_profiles(self, tmp_path, monkeypatch):
        """Test saving and loading profiles"""
        # Use temp directory
        test_file = tmp_path / "test_profiles.json"

        # Create manager with test path
        manager = ProfileManager()
        manager.profile_path = test_file

        # Save test profiles
        test_profiles = {
            "Test Scan": {
                "target": "192.168.1.1",
                "arguments": "-sV -T4"
            },
            "Quick Scan": {
                "target": "localhost",
                "arguments": "-F"
            }
        }

        result = manager.save_profiles(test_profiles)
        assert result is True
        assert test_file.exists()

        # Load profiles back
        loaded_profiles = manager.load_profiles()
        assert loaded_profiles == test_profiles

    def test_save_profiles_invalid_data(self, tmp_path):
        """Test saving profiles with invalid data"""
        test_file = tmp_path / "test_profiles.json"
        manager = ProfileManager()
        manager.profile_path = test_file

        # Try to save non-serializable data
        invalid_profiles = {
            "test": {"func": lambda x: x}  # Functions are not JSON serializable
        }

        result = manager.save_profiles(invalid_profiles)
        assert result is False

    def test_load_profiles_invalid_json(self, tmp_path):
        """Test loading profiles from file with invalid JSON"""
        test_file = tmp_path / "invalid.json"
        test_file.write_text("not valid json {{{")

        manager = ProfileManager()
        manager.profile_path = test_file

        profiles = manager.load_profiles()
        assert profiles == {}

    def test_get_profile_path_creates_directory(self, tmp_path, monkeypatch):
        """Test that _get_profile_path creates necessary directories"""
        # This test verifies the directory creation logic
        manager = ProfileManager("test.json")

        # The path should exist or be created
        assert manager.profile_path.parent.exists() or manager.profile_path.parent == Path(".")
