"""
Unified Pydantic v2 configuration management for the SBM tool.

This module provides secure, type-safe configuration with environment variable support,
replacing the legacy JSON-based configuration system.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ConfigurationError(Exception):
    """Custom exception for configuration-related errors."""


class ProgressSettings(BaseSettings):
    """Progress tracking configuration."""

    model_config = SettingsConfigDict(extra="ignore")

    update_interval: float = Field(
        default=0.1, ge=0.01, le=1.0, description="Progress update interval in seconds"
    )
    thread_timeout: int = Field(default=30, ge=1, le=300, description="Thread timeout in seconds")
    max_concurrent_tasks: int = Field(
        default=10, ge=1, le=50, description="Maximum concurrent tasks"
    )


class LoggingSettings(BaseSettings):
    """Logging configuration."""

    model_config = SettingsConfigDict(extra="ignore")

    use_rich: bool = Field(default=True, description="Use Rich logging")
    log_level: str = Field(
        default="INFO", pattern=r"^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$", description="Log level"
    )
    mask_sensitive: bool = Field(default=True, description="Mask sensitive data in logs")


class GitSettings(BaseSettings):
    """Git-specific configuration."""

    model_config = SettingsConfigDict(extra="ignore")

    github_token: str | None = Field(default=None, description="GitHub personal access token")
    github_org: str = Field(default="dealerinspire", description="GitHub organization")
    default_branch: str = Field(default="main", description="Default git branch")
    default_labels: list[str] = Field(default=["fe-dev"], description="Default PR labels")
    default_reviewers: list[str] = Field(
        default=["carsdotcom/fe-dev"], description="Default PR reviewers"
    )

    @field_validator("github_token")
    @classmethod
    def validate_github_token(cls, v: str | None) -> str | None:
        """Validate GitHub token format and content."""
        # Allow None/empty for commands that don't require GitHub operations
        if v is None or v == "":
            return v

        # Check for placeholder value
        if v == "your_github_personal_access_token_here":
            msg = "GitHub token must be set and cannot be the placeholder value"
            raise ValueError(msg)

        # More relaxed validation - check basic format patterns
        if len(v) < 10:
            msg = "GitHub token appears too short to be valid"
            raise ValueError(msg)

        # Check if it looks like a proper token (starts with known prefixes
        # or has reasonable length)
        if not (v.startswith(("ghp_", "gho_", "ghu_", "ghs_", "ghr_")) or len(v) >= 20):
            msg = "GitHub token format appears invalid"
            raise ValueError(msg)

        return v


class MigrationSettings(BaseSettings):
    """Migration-specific configuration."""

    cleanup_snapshots: bool = Field(default=True, description="Clean up migration snapshots")
    create_backups: bool = Field(default=True, description="Create backups before migration")
    max_concurrent_files: int = Field(
        default=10, ge=1, le=50, description="Maximum concurrent file processing"
    )
    rich_ui_enabled: bool = Field(default=True, description="Enable Rich UI")


class AutoSBMSettings(BaseSettings):
    """Unified Pydantic v2 configuration replacing legacy JSON config."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",  # CRITICAL: Allow extra inputs to prevent cross-env failures
    )

    # PATTERN: Migrate all fields from legacy config.json
    themes_directory: str = Field(default="themes", description="Themes directory path")
    backup_directory: str = Field(default="backups", description="Backup directory path")
    backup_enabled: bool = Field(default=True, description="Enable backups")
    rich_ui_enabled: bool = Field(default=True, description="Enable Rich UI")

    # Add WordPress debug fields to handle di-websites-platform environment variables
    wp_debug: bool | None = Field(
        None, exclude=True, description="WordPress debug setting (ignored)"
    )
    wp_debug_log: bool | None = Field(
        None, exclude=True, description="WordPress debug log setting (ignored)"
    )
    wp_debug_display: bool | None = Field(
        None, exclude=True, description="WordPress debug display setting (ignored)"
    )

    # PATTERN: Nested models for complex configuration
    progress: ProgressSettings = Field(default_factory=lambda: ProgressSettings())
    logging: LoggingSettings = Field(default_factory=lambda: LoggingSettings())
    git: GitSettings = Field(default_factory=lambda: GitSettings())
    migration: MigrationSettings = Field(default_factory=lambda: MigrationSettings())

    @field_validator("themes_directory", "backup_directory")
    @classmethod
    def validate_directories(cls, v: str) -> str:
        """Validate directory paths."""
        path = Path(v)
        # Try to create directories, but be more resilient to failures
        if not path.exists():
            try:
                path.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                # In test/CI environments or when permissions don't allow, just warn
                if any(os.getenv(indicator) for indicator in [
                    "CI", "CONTINUOUS_INTEGRATION", "BUILD_NUMBER",
                    "GITHUB_ACTIONS", "JENKINS_URL", "TRAVIS", "PYTEST_CURRENT_TEST"
                ]):
                    # In test environments, allow it through
                    logging.getLogger(__name__).warning(
                        "Cannot create directory %s in test environment: %s", v, e
                    )
                    return v
                # In production, this is still an error
                msg = f"Cannot create directory {v}: {e}"
                raise ValueError(msg)
        return v

    def is_ci_environment(self) -> bool:
        """Detect if running in CI/CD environment."""
        ci_indicators = [
            "CI",
            "CONTINUOUS_INTEGRATION",
            "BUILD_NUMBER",
            "GITHUB_ACTIONS",
            "JENKINS_URL",
            "TRAVIS",
        ]
        return any(os.getenv(indicator) for indicator in ci_indicators)


# Global settings instance - lazy loaded
_settings: AutoSBMSettings | None = None


def get_settings() -> AutoSBMSettings:
    """Get global settings instance (singleton pattern)."""
    global _settings
    if _settings is None:
        _settings = AutoSBMSettings()
    return _settings


class Config:
    """
    Backward compatibility wrapper for legacy code.

    This maintains the same interface as the old Config class while
    delegating to the new Pydantic BaseSettings underneath.
    """

    def __init__(self, settings: dict[str, Any] | None = None) -> None:
        """Initialize with backward compatibility."""
        # Get the new Pydantic settings
        self._pydantic_settings = get_settings()

        # For backward compatibility, merge any provided dict settings
        if settings:
            # Convert dict settings to attributes for compatibility
            self._legacy_settings = settings
        else:
            self._legacy_settings = {}

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a configuration setting by key (backward compatible)."""
        # First check legacy settings
        if key in self._legacy_settings:
            return self._legacy_settings[key]

        # Then check Pydantic settings
        try:
            return getattr(self._pydantic_settings, key, default)
        except AttributeError:
            return default

    def __getattr__(self, name: str) -> Any:
        """Allow direct access to settings as attributes (backward compatible)."""
        # First check legacy settings
        if name in self._legacy_settings:
            return self._legacy_settings[name]

        # Then check Pydantic settings
        if hasattr(self._pydantic_settings, name):
            return getattr(self._pydantic_settings, name)

        msg = f"'{self.__class__.__name__}' object has no attribute '{name}'"
        raise AttributeError(msg)


def get_config(_config_path: str = "config.json") -> Config:
    """
    Backward compatibility function for legacy code.

    Args:
        _config_path: Legacy parameter, ignored in new implementation

    Returns:
        Config: Backward compatible config object
    """
    # Note: _config_path is ignored in new implementation
    # All configuration now comes from environment variables and defaults
    return Config()
