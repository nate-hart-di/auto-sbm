"""
Tests for configuration management and environment variable loading.
"""

import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
from pydantic import ValidationError

from sbm.config import (
    AutoSBMSettings,
    FirebaseSettings,
    get_settings,
    _settings,
)


@pytest.fixture
def clean_settings():
    """Reset the global settings singleton before and after tests."""
    # Reset global singleton
    import sbm.config

    sbm.config._settings = None
    yield
    sbm.config._settings = None


class TestFirebaseSettings:
    """Test usage of FirebaseSettings validation."""

    @patch.dict(os.environ, {}, clear=True)
    def test_default_values(self, clean_settings):
        """Test that default values are None."""
        # Try empty string to disable env file reading
        settings = FirebaseSettings(_env_file="")
        print(f"DEBUG: settings.database_url={settings.database_url}")
        assert settings.credentials_path is None
        # Default value is set in config.py
        assert settings.database_url == "https://auto-sbm-default-rtdb.firebaseio.com"
        # Since default URL and API key are set, it IS configured for user mode
        assert settings.is_configured()

    def test_valid_configuration(self, tmp_path):
        """Test valid configuration with existing file and valid URL."""
        # Create dummy credentials file
        creds_file = tmp_path / "firebase-creds.json"
        creds_file.touch()

        settings = FirebaseSettings(
            credentials_path=creds_file,
            database_url="https://my-project-default-rtdb.firebaseio.com",
        )

        assert settings.credentials_path == creds_file
        assert settings.database_url == "https://my-project-default-rtdb.firebaseio.com"
        assert settings.is_configured()

    def test_parse_credentials_path_string(self, tmp_path):
        """Test that string path is converted to Path object."""
        creds_file = tmp_path / "creds.json"
        creds_file.touch()

        settings = FirebaseSettings(credentials_path=str(creds_file))
        assert isinstance(settings.credentials_path, Path)
        assert settings.credentials_path == creds_file

    @patch("sbm.config.logger")
    def test_missing_credentials_file_warning(self, mock_logger):
        """Test that a missing file triggers a logger warning."""
        settings = FirebaseSettings(credentials_path="/path/to/nonexistent/file.json")

        # Should still set the path
        assert str(settings.credentials_path) == "/path/to/nonexistent/file.json"

        # Should verify warning was logged
        mock_logger.warning.assert_called_once()
        assert "Firebase credentials file not found" in mock_logger.warning.call_args[0][0]

    def test_invalid_database_url_scheme(self):
        """Test validation of invalid URL scheme."""
        with pytest.raises(ValidationError) as excinfo:
            FirebaseSettings(database_url="http://insecure-url.com")

        assert "Firebase database URL must start with https://" in str(excinfo.value)

    def test_invalid_database_url_domain(self):
        """Test validation of invalid Firebase domain."""
        with pytest.raises(ValidationError) as excinfo:
            FirebaseSettings(database_url="https://google.com")

        assert "must be a valid Firebase Realtime Database URL" in str(excinfo.value)

    def test_valid_firebasedatabase_app_domain(self):
        """Test validation of firebasedatabase.app domain (new format)."""
        settings = FirebaseSettings(database_url="https://project.firebasedatabase.app")
        assert settings.database_url == "https://project.firebasedatabase.app"

    def test_url_trailing_slash_stripped(self):
        """Test that trailing slashes are removed."""
        settings = FirebaseSettings(database_url="https://project.firebaseio.com/")
        assert settings.database_url == "https://project.firebaseio.com"


class TestAutoSBMSettingsIntegration:
    """Test integration of Firebase settings into main config."""

    def test_firebase_settings_default(self, clean_settings):
        """Test that firebase settings are initialized by default when no env vars set."""
        # Clear Firebase env vars to test true defaults
        env_override = {
            "FIREBASE__CREDENTIALS_PATH": "",
            "FIREBASE__DATABASE_URL": "",
        }
        with patch.dict(os.environ, env_override, clear=False):
            settings = AutoSBMSettings()
            assert isinstance(settings.firebase, FirebaseSettings)
            # With no env vars, is_configured should be False (no database_url)
            assert not settings.firebase.is_configured()

    def test_env_var_loading(self, tmp_path, clean_settings):
        """Test loading from environment variables."""
        # Mock environment variables
        creds_file = tmp_path / "env-creds.json"
        creds_file.touch()

        env_vars = {
            "FIREBASE__CREDENTIALS_PATH": str(creds_file),
            "FIREBASE__DATABASE_URL": "https://env-test.firebaseio.com",
        }

        with patch.dict(os.environ, env_vars):
            settings = AutoSBMSettings()

            assert settings.firebase.credentials_path == creds_file
            assert settings.firebase.database_url == "https://env-test.firebaseio.com"
            assert settings.firebase.is_configured()
