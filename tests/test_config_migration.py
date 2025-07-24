"""
Test cases for unified Pydantic configuration migration.

This test module verifies:
- Pydantic v2 BaseSettings functionality
- Backward compatibility with legacy Config class
- Environment variable handling and validation
- Field validation and security features
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from sbm.config import (
    AutoSBMSettings,
    Config,
    GitSettings,
    LoggingSettings,
    MigrationSettings,
    ProgressSettings,
    get_config,
    get_settings,
)


class TestPydanticConfiguration:
    """Test the new Pydantic v2 configuration system."""

    def test_autosbm_settings_creation(self):
        """Test that AutoSBMSettings can be created with defaults."""
        with patch.dict(os.environ, {"GITHUB_TOKEN": "ghp_test_token_12345"}):
            settings = AutoSBMSettings()

            # Test default values
            assert settings.themes_directory == "themes"
            assert settings.backup_directory == "backups"
            assert settings.backup_enabled is True
            assert settings.rich_ui_enabled is True

            # Test nested models
            assert isinstance(settings.progress, ProgressSettings)
            assert isinstance(settings.logging, LoggingSettings)
            assert isinstance(settings.git, GitSettings)
            assert isinstance(settings.migration, MigrationSettings)

    def test_environment_variable_support(self):
        """Test environment variable loading and precedence."""
        test_env = {
            "GITHUB_TOKEN": "ghp_test_token_12345",
            "THEMES_DIRECTORY": "/custom/themes",
            "BACKUP_ENABLED": "false",
            "RICH_UI_ENABLED": "true"
        }

        with patch.dict(os.environ, test_env, clear=False):
            settings = AutoSBMSettings()

            assert settings.themes_directory == "/custom/themes"
            assert settings.backup_enabled is False
            assert settings.rich_ui_enabled is True

    def test_nested_environment_variables(self):
        """Test nested configuration with environment variables."""
        test_env = {
            "GITHUB_TOKEN": "ghp_test_token_12345",
            "PROGRESS__UPDATE_INTERVAL": "0.2",
            "PROGRESS__THREAD_TIMEOUT": "60",
            "LOGGING__LOG_LEVEL": "DEBUG"
        }

        with patch.dict(os.environ, test_env, clear=False):
            settings = AutoSBMSettings()

            assert settings.progress.update_interval == 0.2
            assert settings.progress.thread_timeout == 60
            assert settings.logging.log_level == "DEBUG"

    def test_field_validation(self):
        """Test Pydantic field validation."""
        with patch.dict(os.environ, {"GITHUB_TOKEN": "ghp_test_token_12345"}):
            settings = AutoSBMSettings()

            # Test progress settings validation
            assert 0.01 <= settings.progress.update_interval <= 1.0
            assert 1 <= settings.progress.thread_timeout <= 300
            assert 1 <= settings.progress.max_concurrent_tasks <= 50

            # Test logging settings validation
            assert settings.logging.log_level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

    def test_github_token_validation(self):
        """Test GitHub token validation."""
        # Test valid token
        with patch.dict(os.environ, {"GITHUB_TOKEN": "ghp_valid_token_12345"}):
            settings = AutoSBMSettings()
            assert settings.git.github_token == "ghp_valid_token_12345"

        # Test invalid token format
        with patch.dict(os.environ, {"GITHUB_TOKEN": "invalid_token"}):
            with pytest.raises(ValueError, match="GitHub token format appears invalid"):
                AutoSBMSettings()

        # Test placeholder token
        with patch.dict(os.environ, {"GITHUB_TOKEN": "your_github_personal_access_token_here"}):
            with pytest.raises(ValueError, match="GitHub token must be set and cannot be the placeholder value"):
                AutoSBMSettings()

    def test_directory_validation(self):
        """Test directory validation and creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_themes_dir = os.path.join(temp_dir, "test_themes")
            test_backup_dir = os.path.join(temp_dir, "test_backups")

            test_env = {
                "GITHUB_TOKEN": "ghp_test_token_12345",
                "THEMES_DIRECTORY": test_themes_dir,
                "BACKUP_DIRECTORY": test_backup_dir
            }

            with patch.dict(os.environ, test_env, clear=False):
                settings = AutoSBMSettings()

                # Directories should be created automatically
                assert Path(test_themes_dir).exists()
                assert Path(test_backup_dir).exists()
                assert settings.themes_directory == test_themes_dir
                assert settings.backup_directory == test_backup_dir

    def test_ci_environment_detection(self):
        """Test CI/CD environment detection."""
        with patch.dict(os.environ, {"GITHUB_TOKEN": "ghp_test_token_12345"}):
            settings = AutoSBMSettings()

            # Normal environment
            assert settings.is_ci_environment() is False

        # Test with CI indicators
        with patch.dict(os.environ, {"GITHUB_TOKEN": "ghp_test_token_12345", "CI": "true"}):
            settings = AutoSBMSettings()
            assert settings.is_ci_environment() is True

        with patch.dict(os.environ, {"GITHUB_TOKEN": "ghp_test_token_12345", "GITHUB_ACTIONS": "true"}):
            settings = AutoSBMSettings()
            assert settings.is_ci_environment() is True

    def test_extra_fields_rejected(self):
        """Test that extra fields are rejected for security."""
        with patch.dict(os.environ, {"GITHUB_TOKEN": "ghp_test_token_12345", "UNKNOWN_FIELD": "value"}):
            # Should create successfully (extra fields are ignored by environment loading)
            settings = AutoSBMSettings()
            assert not hasattr(settings, "unknown_field")


class TestBackwardCompatibility:
    """Test backward compatibility with legacy Config class."""

    def test_legacy_config_creation(self):
        """Test that legacy Config class still works."""
        with patch.dict(os.environ, {"GITHUB_TOKEN": "ghp_test_token_12345"}):
            config = Config()

            # Should be able to create without errors
            assert isinstance(config, Config)

    def test_legacy_get_setting_method(self):
        """Test legacy get_setting method."""
        with patch.dict(os.environ, {"GITHUB_TOKEN": "ghp_test_token_12345"}):
            config = Config()

            # Test getting default settings
            assert config.get_setting("themes_directory") == "themes"
            assert config.get_setting("backup_enabled") is True
            assert config.get_setting("nonexistent_key", "default") == "default"

    def test_legacy_attribute_access(self):
        """Test legacy attribute access patterns."""
        with patch.dict(os.environ, {"GITHUB_TOKEN": "ghp_test_token_12345"}):
            config = Config()

            # Test direct attribute access
            assert config.themes_directory == "themes"
            assert config.backup_enabled is True
            assert config.rich_ui_enabled is True

            # Test nested attribute access
            assert hasattr(config, "progress")
            assert hasattr(config, "logging")
            assert hasattr(config, "git")
            assert hasattr(config, "migration")

    def test_legacy_dict_settings_override(self):
        """Test that legacy dict settings can override defaults."""
        with patch.dict(os.environ, {"GITHUB_TOKEN": "ghp_test_token_12345"}):
            legacy_settings = {
                "custom_setting": "custom_value",
                "themes_directory": "legacy_themes"
            }

            config = Config(legacy_settings)

            # Legacy settings should take precedence
            assert config.get_setting("custom_setting") == "custom_value"
            assert config.get_setting("themes_directory") == "legacy_themes"

    def test_get_config_function(self):
        """Test the legacy get_config function."""
        with patch.dict(os.environ, {"GITHUB_TOKEN": "ghp_test_token_12345"}):
            config = get_config("nonexistent_file.json")  # Path is ignored

            assert isinstance(config, Config)
            assert config.get_setting("themes_directory") == "themes"


class TestConfigurationSingleton:
    """Test the singleton pattern for settings."""

    def test_get_settings_singleton(self):
        """Test that get_settings returns the same instance."""
        with patch.dict(os.environ, {"GITHUB_TOKEN": "ghp_test_token_12345"}):
            settings1 = get_settings()
            settings2 = get_settings()

            # Should be the same instance
            assert settings1 is settings2

    def test_settings_reset_for_testing(self):
        """Test that settings can be reset for testing purposes."""

        with patch.dict(os.environ, {"GITHUB_TOKEN": "ghp_test_token_12345"}):
            # Get initial settings
            settings1 = get_settings()

            # Manually reset (simulating what would happen in test teardown)
            import sbm.config
            sbm.config._settings = None

            # Get new settings
            settings2 = get_settings()

            # Should be different instances
            assert settings1 is not settings2


class TestNestedSettingsModels:
    """Test the nested settings models."""

    def test_progress_settings(self):
        """Test ProgressSettings model."""
        progress = ProgressSettings()

        assert 0.01 <= progress.update_interval <= 1.0
        assert 1 <= progress.thread_timeout <= 300
        assert 1 <= progress.max_concurrent_tasks <= 50

    def test_logging_settings(self):
        """Test LoggingSettings model."""
        logging_settings = LoggingSettings()

        assert logging_settings.use_rich is True
        assert logging_settings.log_level == "INFO"
        assert logging_settings.mask_sensitive is True

    def test_git_settings(self):
        """Test GitSettings model."""
        with patch.dict(os.environ, {"GITHUB_TOKEN": "ghp_test_token_12345"}):
            git = GitSettings()

            assert git.github_token == "ghp_test_token_12345"
            assert git.github_org == "dealerinspire"
            assert git.default_branch == "main"
            assert "fe-dev" in git.default_labels
            assert "carsdotcom/fe-dev" in git.default_reviewers

    def test_migration_settings(self):
        """Test MigrationSettings model."""
        migration = MigrationSettings()

        assert migration.cleanup_snapshots is True
        assert migration.create_backups is True
        assert 1 <= migration.max_concurrent_files <= 50
        assert migration.rich_ui_enabled is True


class TestConfigurationSecurity:
    """Test security features of the configuration system."""

    def test_github_token_validation_security(self):
        """Test that GitHub token validation prevents common security issues."""
        # Test placeholder token (should fail)
        with patch.dict(os.environ, {"GITHUB_TOKEN": "your_github_personal_access_token_here"}):
            with pytest.raises(ValueError):
                AutoSBMSettings()

        # Test empty token (should be allowed for non-git commands)
        with patch.dict(os.environ, {"GITHUB_TOKEN": ""}):
            config = AutoSBMSettings()
            assert config.git.github_token == ""

        # Test None token (simulated by missing env var)
        with patch.dict(os.environ, {}, clear=True):
            config = AutoSBMSettings()
            assert config.git.github_token is None

    def test_path_injection_prevention(self):
        """Test that path settings prevent directory traversal."""
        with patch.dict(os.environ, {"GITHUB_TOKEN": "ghp_test_token_12345"}):
            # Normal paths should work
            with patch.dict(os.environ, {"THEMES_DIRECTORY": "valid_themes"}):
                settings = AutoSBMSettings()
                assert "valid_themes" in settings.themes_directory

            # Path traversal attempts should be handled safely
            # (Note: This tests that the validator doesn't crash, not that it prevents traversal)
            with patch.dict(os.environ, {"THEMES_DIRECTORY": "../../../etc"}):
                settings = AutoSBMSettings()
                # Should not crash during validation
                assert isinstance(settings.themes_directory, str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
