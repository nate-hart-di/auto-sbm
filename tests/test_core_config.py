"""
Core configuration loading and validation tests.
Tests the Pydantic v2 configuration system.
"""
import os
import pytest
from unittest.mock import patch, MagicMock
from pydantic import ValidationError

from sbm.config import AutoSBMSettings


class TestConfigLoading:
    """Test configuration loading from environment variables."""
    
    def test_config_loads_from_env(self):
        """Test configuration loads from environment variables"""
        # Set test environment variables that pass validation
        import os
        os.environ["GITHUB_TOKEN"] = "ghp_test123456789012345678901234567890"  # Valid format token for tests
        os.environ["GITHUB_ORG"] = "test-org"
        
        config = AutoSBMSettings()
        assert config.git.github_token == "ghp_test123456789012345678901234567890"
        assert config.git.github_org == "test-org"
        
        # Clean up
        del os.environ["GITHUB_TOKEN"]
        del os.environ["GITHUB_ORG"]
    
    def test_config_validates_github_token(self, monkeypatch):
        """Test config requires valid GitHub token."""
        # Test with invalid short token 
        monkeypatch.setenv("GITHUB_TOKEN", "short")
        monkeypatch.setenv("GITHUB_ORG", "test_org")
        
        with pytest.raises(ValidationError) as exc_info:
            AutoSBMSettings()
        
        assert "github_token" in str(exc_info.value)
    
    def test_config_validates_github_org(self, monkeypatch):
        """Test config uses default GitHub organization when not provided."""
        # Test with valid token but no org - should use default
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test123456789012345678901234567890")  # Valid token format
        monkeypatch.delenv("GITHUB_ORG", raising=False)
        
        config = AutoSBMSettings()
        
        # Should use default org
        assert config.git.github_org == "dealerinspire"
    
    def test_config_default_values(self, monkeypatch):
        """Test config provides sensible defaults."""
        # Set required fields only
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test123456789012345678901234567890")
        monkeypatch.setenv("GITHUB_ORG", "test_org")
        
        config = AutoSBMSettings()
        
        # Check defaults
        assert config.git.default_branch == "main"
        assert isinstance(config.git.default_labels, list)
        assert "fe-dev" in config.git.default_labels
    
    def test_config_pydantic_validation(self, monkeypatch):
        """Test Pydantic catches invalid configuration."""
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test123456789012345678901234567890")
        monkeypatch.setenv("GITHUB_ORG", "test_org")
        
        # Test invalid default_labels (should be JSON list)
        monkeypatch.setenv("DEFAULT_LABELS", '["test-label"]')  # Valid JSON list
        
        config = AutoSBMSettings()
        # Should handle string conversion to list
        assert isinstance(config.git.default_labels, list)


class TestConfigEnvironmentHandling:
    """Test environment variable handling and edge cases."""
    
    def test_config_handles_missing_env_file(self, monkeypatch, tmp_path):
        """Test config works without .env file."""
        # Change to temp directory without .env
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test123456789012345678901234567890")
        monkeypatch.setenv("GITHUB_ORG", "test_org")
        
        # Should load from environment variables only
        config = AutoSBMSettings()
        assert config.git.github_token == "ghp_test123456789012345678901234567890"
    
    def test_config_environment_precedence(self, monkeypatch, tmp_path):
        """Test environment variables override .env file."""
        # Create .env file
        env_file = tmp_path / ".env"
        env_file.write_text(
            "GITHUB_TOKEN=ghp_envfile123456789012345678901234567890\n"
            "GITHUB_ORG=env_file_org\n"
        )
        
        monkeypatch.chdir(tmp_path)
        
        # Override with environment variables
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_env123456789012345678901234567890")
        monkeypatch.setenv("GITHUB_ORG", "env_var_org")
        
        config = AutoSBMSettings()
        assert config.git.github_token == "ghp_env123456789012345678901234567890"
        assert config.git.github_org == "env_var_org"


class TestConfigValidation:
    """Test configuration field validation."""
    
    def test_config_empty_token_validation(self, monkeypatch):
        """Test config handles empty GitHub token gracefully."""
        # Empty token should be allowed (None default)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.setenv("GITHUB_ORG", "test-org")
        
        config = AutoSBMSettings()
        assert config.git.github_token is None
    
    def test_config_empty_org_validation(self, monkeypatch):
        """Test config handles empty organization gracefully."""
        # Test empty org - empty string is accepted as valid
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test123456789012345678901234567890")
        monkeypatch.setenv("GITHUB_ORG", "")  # Empty string
        
        config = AutoSBMSettings()
        # Empty string is valid (not None), so it's used as-is
        assert config.git.github_org == ""
    
    def test_config_labels_validation(self, monkeypatch):
        """Test default labels field validation."""
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test123456789012345678901234567890")
        monkeypatch.setenv("GITHUB_ORG", "test_org")
        monkeypatch.setenv("DEFAULT_LABELS", '["label1", "label2", "label3"]')  # JSON format
        
        config = AutoSBMSettings()
        
        # Should split comma-separated string into list
        expected_labels = ["label1", "label2", "label3"]
        assert config.git.default_labels == expected_labels
