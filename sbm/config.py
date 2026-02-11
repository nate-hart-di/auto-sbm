"""
Unified Pydantic v2 configuration management for the SBM tool.

This module provides secure, type-safe configuration with environment variable support,
replacing the legacy JSON-based configuration system.
"""

from __future__ import annotations

import os
from typing import Any

from pathlib import Path
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ConfigurationError(Exception):
    """Custom exception for configuration-related errors."""


from sbm.utils.logger import logger


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
        default=["carsdotcom/fe-dev-sbm"], description="Default PR reviewers"
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

        # Check if it looks like a proper token (starts with known prefixes or reasonable length)
        if not (v.startswith(("ghp_", "gho_", "ghu_", "ghs_", "ghr_")) or len(v) >= 20):
            msg = "GitHub token format appears invalid"
            raise ValueError(msg)

        return v


class FirebaseSettings(BaseSettings):
    """Firebase Realtime Database configuration for team-wide stats sync.

    Story 2.7: Two authentication modes supported:
    - User Mode: database_url only → Anonymous Auth (read-only access)
    - Admin Mode: database_url + credentials_path → Full access

    Environment variables:
        FIREBASE__DATABASE_URL: Firebase Realtime Database URL (required for all)
        FIREBASE__CREDENTIALS_PATH: Path to Firebase service account JSON (admin only)
        FIREBASE__API_KEY: Firebase Web API Key (required for user mode/anonymous auth)
    """

    model_config = SettingsConfigDict(extra="ignore")

    credentials_path: Path | None = Field(
        default=None,
        description="Path to Firebase service account JSON file (admin only)",
    )
    database_url: str | None = Field(
        default="https://auto-sbm-default-rtdb.firebaseio.com",
        description="Firebase Realtime Database URL (e.g., https://project-id.firebaseio.com)",
    )
    api_key: str | None = Field(
        default=None,
        description="Firebase Web API Key (required for user mode/anonymous auth)",
    )

    @field_validator("credentials_path", mode="before")
    @classmethod
    def parse_credentials_path(cls, v: str | Path | None) -> Path | None:
        """Convert string path to Path object, handling None and empty strings."""
        if v is None or v == "":
            return None
        return Path(v) if isinstance(v, str) else v

    @field_validator("credentials_path", mode="after")
    @classmethod
    def validate_credentials_path(cls, v: Path | None) -> Path | None:
        """Validate that credentials file exists if path is provided."""
        if v is None:
            return v
        # Expand user home directory if needed
        expanded_path = v.expanduser()
        if not expanded_path.exists():
            # Log warning but don't fail - allows offline-first operation
            # Firebase operations will fail gracefully at runtime
            logger.warning(
                f"Firebase credentials file not found: {expanded_path}. "
                "Firebase admin mode will be disabled.",
            )
        return expanded_path

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str | None) -> str | None:
        """Validate Firebase database URL format."""
        if v is None or v == "":
            return None
        # Basic URL validation - must be HTTPS Firebase URL
        if not v.startswith("https://"):
            msg = "Firebase database URL must start with https://"
            raise ValueError(msg)
        if "firebaseio.com" not in v and "firebasedatabase.app" not in v:
            msg = (
                "Firebase database URL must be a valid Firebase Realtime Database URL "
                "(containing firebaseio.com or firebasedatabase.app)"
            )
            raise ValueError(msg)
        return v.rstrip("/")  # Normalize URL by removing trailing slash

    def is_configured(self) -> bool:
        """Check if Firebase is available (admin or user mode).

        Returns True if database_url is set and either credentials or api_key are available.
        Team members need api_key for anonymous auth.
        """
        return self.database_url is not None and (self.api_key is not None or self.is_admin_mode())

    def is_admin_mode(self) -> bool:
        """Check if running in admin mode with full credentials."""
        return (
            self.credentials_path is not None
            and self.credentials_path.exists()
            and self.database_url is not None
        )

    def is_user_mode(self) -> bool:
        """Check if running in user mode (anonymous auth)."""
        return self.database_url is not None and self.api_key is not None and not self.is_admin_mode()


class MigrationSettings(BaseSettings):
    """Migration-specific configuration."""


class AutoSBMSettings(BaseSettings):
    """Unified Pydantic v2 configuration replacing legacy JSON config."""

    model_config = SettingsConfigDict(
        env_file=[
            str(Path(__file__).resolve().parent.parent / ".env"),
            str(Path.home() / "auto-sbm" / ".env"),
        ],
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",  # CRITICAL: Allow extra inputs to prevent cross-env failures
    )

    # WordPress debug fields (ignored by auto-sbm)
    wp_debug: bool | None = Field(None, exclude=True, description="WP debug (ignored)")
    wp_debug_log: bool | None = Field(None, exclude=True, description="WP debug log (ignored)")
    wp_debug_display: bool | None = Field(
        None, exclude=True, description="WP debug display (ignored)"
    )

    # PATTERN: Nested models for complex configuration
    progress: ProgressSettings = Field(default_factory=lambda: ProgressSettings())
    logging: LoggingSettings = Field(default_factory=lambda: LoggingSettings())
    git: GitSettings = Field(default_factory=lambda: GitSettings())
    migration: MigrationSettings = Field(default_factory=lambda: MigrationSettings())
    firebase: FirebaseSettings = Field(default_factory=lambda: FirebaseSettings())

    # Global CLI behavior
    non_interactive: bool = Field(default=False, description="Disable interactive prompts")

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


def get_config(config_path: str = "config.json") -> Config:
    """
    Backward compatibility function for legacy code.

    Args:
        config_path: Legacy parameter, ignored in new implementation

    Returns:
        Config: Backward compatible config object
    """
    # Note: config_path is ignored in new implementation
    # All configuration now comes from environment variables and defaults
    return Config()
