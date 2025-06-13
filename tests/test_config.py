"""
Tests for sbm.config module.

Tests configuration loading, validation, and environment handling.
"""

import os
import pytest
from unittest.mock import patch
from pathlib import Path

from sbm.config import Config, get_config, reset_config
from sbm.utils.errors import ConfigurationError


class TestConfig:
    """Test the Config class."""
    
    def test_config_initialization_with_valid_env(self, test_config):
        """Test config initialization with valid environment."""
        assert test_config.di_platform_dir.exists()
        assert test_config.dealer_themes_dir.exists()
        assert test_config.context7.server_url == "http://localhost:3001"
        assert test_config.context7.api_key == "test_api_key"
        assert test_config.git.user_name == "Test User"
        assert test_config.stellantis.enhanced_mode is True
    
    def test_config_missing_required_env_var(self, temp_dir):
        """Test config fails with missing required environment variable."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ConfigurationError) as exc_info:
                Config(auto_load=False)
            assert "Missing required environment variables" in str(exc_info.value)
            assert "DI_PLATFORM_DIR" in str(exc_info.value)
    
    def test_config_invalid_platform_dir(self, temp_dir):
        """Test config fails with invalid platform directory."""
        invalid_path = temp_dir / "nonexistent"
        with patch.dict(os.environ, {"DI_PLATFORM_DIR": str(invalid_path)}):
            with pytest.raises(ConfigurationError) as exc_info:
                Config()
            assert "DI Platform directory does not exist" in str(exc_info.value)
    
    def test_context7_config(self, test_config):
        """Test Context7 configuration."""
        assert test_config.context7.server_url == "http://localhost:3001"
        assert test_config.context7.api_key == "test_api_key"
        assert test_config.context7.timeout == 30
        assert test_config.context7.enabled is True
    
    def test_git_config(self, test_config):
        """Test Git configuration."""
        assert test_config.git.user_name == "Test User"
        assert test_config.git.user_email == "test@example.com"
        assert test_config.git.default_branch == "main"
        assert "reviewer1" in test_config.git.default_reviewers
        assert "reviewer2" in test_config.git.default_reviewers
    
    def test_stellantis_config(self, test_config):
        """Test Stellantis configuration."""
        assert test_config.stellantis.enhanced_mode is True
        assert test_config.stellantis.brand_detection == "auto"
        assert test_config.stellantis.map_processing is True
        
        # Test brand patterns
        assert "chrysler" in test_config.stellantis.brand_patterns
        assert "dodge" in test_config.stellantis.brand_patterns
        assert "jeep" in test_config.stellantis.brand_patterns
        assert "ram" in test_config.stellantis.brand_patterns
    
    def test_demo_config_disabled(self, test_config):
        """Test demo configuration when disabled."""
        assert test_config.demo.enabled is False
        assert test_config.demo.timeout == 300
        assert test_config.demo.skip_git is False
    
    def test_demo_config_enabled(self, mock_di_platform):
        """Test demo configuration when enabled."""
        with patch.dict(os.environ, {
            "DI_PLATFORM_DIR": str(mock_di_platform),
            "DEMO_MODE": "true",
            "DEMO_TIMEOUT": "180",
            "DEMO_SKIP_GIT": "true",
            "DEMO_SKIP_STARTUP": "true"
        }):
            config = Config()
            assert config.demo.enabled is True
            assert config.demo.timeout == 180
            assert config.demo.skip_git is True
            assert config.demo.skip_startup is True
    
    def test_get_theme_path(self, test_config):
        """Test getting theme path."""
        theme_path = test_config.get_theme_path("chryslerofportland")
        expected_path = test_config.dealer_themes_dir / "chryslerofportland"
        assert theme_path == expected_path
    
    def test_validate_theme_exists(self, test_config):
        """Test theme existence validation."""
        # Existing theme
        assert test_config.validate_theme_exists("chryslerofportland") is True
        
        # Non-existing theme
        assert test_config.validate_theme_exists("nonexistenttheme") is False
    
    def test_boolean_parsing(self, mock_di_platform):
        """Test boolean value parsing from environment."""
        test_cases = [
            ("true", True),
            ("True", True),
            ("1", True),
            ("yes", True),
            ("on", True),
            ("false", False),
            ("False", False),
            ("0", False),
            ("no", False),
            ("off", False),
            ("", False),
            ("invalid", False)
        ]
        
        for env_value, expected in test_cases:
            with patch.dict(os.environ, {
                "DI_PLATFORM_DIR": str(mock_di_platform),
                "STELLANTIS_ENHANCED_MODE": env_value
            }):
                config = Config()
                assert config.stellantis.enhanced_mode == expected
    
    def test_list_parsing(self, mock_di_platform):
        """Test list value parsing from environment."""
        with patch.dict(os.environ, {
            "DI_PLATFORM_DIR": str(mock_di_platform),
            "SBM_DEFAULT_REVIEWERS": "user1,user2,user3",
            "SBM_DEFAULT_LABELS": "label1, label2 , label3"
        }):
            config = Config()
            assert config.git.default_reviewers == ["user1", "user2", "user3"]
            assert config.git.default_labels == ["label1", "label2", "label3"]
    
    def test_to_dict(self, test_config):
        """Test configuration serialization to dictionary."""
        config_dict = test_config.to_dict()
        
        assert "di_platform_dir" in config_dict
        assert "context7" in config_dict
        assert "git" in config_dict
        assert "stellantis" in config_dict
        assert "demo" in config_dict
        
        # Check Context7 section
        assert config_dict["context7"]["enabled"] is True
        assert config_dict["context7"]["server_url"] == "http://localhost:3001"
        assert config_dict["context7"]["api_key_set"] is True
        
        # Check Git section
        assert config_dict["git"]["user_name"] == "Test User"
        assert config_dict["git"]["default_branch"] == "main"


class TestConfigGlobal:
    """Test global configuration functions."""
    
    def test_get_config_singleton(self, mock_env_vars):
        """Test that get_config returns the same instance."""
        config1 = get_config()
        config2 = get_config()
        assert config1 is config2
    
    def test_reset_config(self, mock_env_vars):
        """Test configuration reset."""
        config1 = get_config()
        reset_config()
        config2 = get_config()
        assert config1 is not config2
    
    def test_get_config_with_env_file(self, temp_dir, mock_di_platform):
        """Test loading config from specific env file."""
        env_file = temp_dir / "test.env"
        env_file.write_text(f"""
DI_PLATFORM_DIR={mock_di_platform}
CONTEXT7_SERVER_URL=http://test:3002
GIT_USER_NAME=Test From File
""")
        
        reset_config()
        config = get_config(str(env_file))
        assert config.context7.server_url == "http://test:3002"
        assert config.git.user_name == "Test From File"


class TestConfigEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_config_with_minimal_env(self, mock_di_platform):
        """Test config with only required environment variables."""
        with patch.dict(os.environ, {
            "DI_PLATFORM_DIR": str(mock_di_platform)
        }, clear=True):
            config = Config()
            
            # Should use defaults
            assert config.context7.server_url == "http://localhost:3001"
            assert config.git.default_branch == "main"
            assert config.stellantis.enhanced_mode is True
    
    def test_config_with_empty_lists(self, mock_di_platform):
        """Test config with empty list values."""
        with patch.dict(os.environ, {
            "DI_PLATFORM_DIR": str(mock_di_platform),
            "SBM_DEFAULT_REVIEWERS": "",
            "SBM_DEFAULT_LABELS": ""
        }):
            config = Config()
            assert config.git.default_reviewers == []
            assert config.git.default_labels == ["sbm", "migration"]  # Should use default
    
    def test_config_with_invalid_numbers(self, mock_di_platform):
        """Test config with invalid numeric values."""
        with patch.dict(os.environ, {
            "DI_PLATFORM_DIR": str(mock_di_platform),
            "CONTEXT7_TIMEOUT": "invalid",
            "DEMO_TIMEOUT": "not_a_number"
        }):
            # Should not raise exception, should use defaults or handle gracefully
            with pytest.raises(ValueError):
                Config()
    
    def test_config_paths_creation(self, test_config):
        """Test that all expected paths are created correctly."""
        assert test_config.di_platform_dir.is_dir()
        assert test_config.dealer_themes_dir.is_dir()
        assert test_config.common_theme_dir.is_dir()
        
        # Test path relationships
        assert test_config.dealer_themes_dir.parent == test_config.di_platform_dir
        assert "DealerInspireCommonTheme" in str(test_config.common_theme_dir) 
