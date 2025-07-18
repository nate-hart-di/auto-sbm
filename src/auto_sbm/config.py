"""Secure configuration management with environment variables and Pydantic validation"""

from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from pathlib import Path
from typing import List, Optional
import os


class GitSettings(BaseSettings):
    """Git-specific configuration"""
    
    github_token: str = Field(..., description="GitHub personal access token")
    github_org: str = Field(default="dealerinspire", description="GitHub organization")
    default_branch: str = Field(default="main", description="Default git branch")
    default_labels: List[str] = Field(default=["fe-dev"], description="Default PR labels")
    default_reviewers: List[str] = Field(default=["carsdotcom/fe-dev"], description="Default PR reviewers")
    
    @field_validator('github_token')
    @classmethod
    def validate_github_token(cls, v: str) -> str:
        """Validate GitHub token format"""
        if not v or v == "your_github_personal_access_token_here":
            raise ValueError("GitHub token must be set and cannot be the placeholder value")
        
        if not (v.startswith('ghp_') or v.startswith('gho_') or v.startswith('ghu_') or v.startswith('ghs_')):
            raise ValueError("GitHub token format appears invalid")
        
        return v


class MigrationSettings(BaseSettings):
    """Migration-specific configuration"""
    
    cleanup_snapshots: bool = Field(default=True, description="Clean up migration snapshots")
    create_backups: bool = Field(default=True, description="Create backups before migration")
    max_concurrent_files: int = Field(default=10, ge=1, le=50, description="Maximum concurrent file processing")
    rich_ui_enabled: bool = Field(default=True, description="Enable Rich UI")


class AutoSBMSettings(BaseSettings):
    """Main application configuration with security and validation"""
    
    # Nested configuration objects
    git: GitSettings = Field(default_factory=GitSettings)
    migration: MigrationSettings = Field(default_factory=MigrationSettings)
    
    # File system paths
    themes_directory: Path = Field(default=Path("themes"), description="Themes directory")
    backup_directory: Path = Field(default=Path("backups"), description="Backup directory")
    
    @field_validator('themes_directory', 'backup_directory')
    @classmethod
    def validate_directories_exist(cls, v: Path) -> Path:
        """Ensure directories exist or can be created"""
        if not v.exists():
            try:
                v.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                raise ValueError(f"Cannot create directory {v}: {e}")
        return v
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "env_nested_delimiter": "__",
        "extra": "forbid"  # Reject unknown configuration keys
    }
    
    @classmethod
    def from_env(cls) -> "AutoSBMSettings":
        """Create settings instance from environment variables"""
        return cls()
    
    def is_ci_environment(self) -> bool:
        """Detect if running in CI/CD environment"""
        ci_indicators = [
            'CI', 'CONTINUOUS_INTEGRATION', 'BUILD_NUMBER', 
            'GITHUB_ACTIONS', 'JENKINS_URL', 'TRAVIS'
        ]
        return any(os.getenv(indicator) for indicator in ci_indicators)


# Global settings instance - lazy loaded
_settings: Optional[AutoSBMSettings] = None


def get_settings() -> AutoSBMSettings:
    """Get global settings instance (singleton pattern)"""
    global _settings
    if _settings is None:
        _settings = AutoSBMSettings.from_env()
    return _settings


def reset_settings() -> None:
    """Reset global settings (for testing)"""
    global _settings
    _settings = None