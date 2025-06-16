"""
Configuration management for SBM Tool V2.

Handles environment variables, validation, and configuration for all components
including Git operations and GitHub integration.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from dotenv import load_dotenv

from sbm.utils.errors import ConfigurationError


@dataclass
class GitConfig:
    """Git operation configuration."""
    
    user_name: str = ""
    user_email: str = ""
    default_branch: str = "main"
    default_reviewers: List[str] = field(default_factory=list)
    default_labels: List[str] = field(default_factory=lambda: ["sbm", "migration"])


@dataclass
class GitHubConfig:
    """GitHub integration configuration."""
    
    token: Optional[str] = None
    org: str = "carsdotcom"
    repo: str = "di-websites-platform"


@dataclass
class DemoConfig:
    """Demo/testing mode configuration."""
    
    enabled: bool = False
    skip_git: bool = False
    timeout: int = 300
    skip_startup: bool = False





class Config:
    """
    Central configuration manager for SBM Tool V2.
    
    Loads configuration from environment variables and provides
    validated access to all settings.
    """
    
    def __init__(self, env_file: Optional[str] = None, auto_load: bool = True):
        """
        Initialize configuration.
        
        Args:
            env_file: Optional path to .env file to load
            auto_load: Whether to auto-load from common env files
        """
        # Load environment variables
        if env_file:
            load_dotenv(env_file)
        elif auto_load:
            # Try to load from common locations
            for env_path in [".env", ".env.local", "env.example"]:
                if Path(env_path).exists():
                    load_dotenv(env_path)
                    break
        
        self._validate_required_settings()
        self._load_configurations()
    
    def _validate_required_settings(self) -> None:
        """Validate required environment settings."""
        # Auto-derive DI platform directory - it's always in the same place
        username = self._get_current_user()
        di_platform_path = Path(f"/Users/{username}/di-websites-platform")
        
        if not di_platform_path.exists():
            raise ConfigurationError(
                f"DI Platform directory not found at expected location: {di_platform_path}. "
                f"Please ensure the di-websites-platform repository is cloned to your home directory."
            )
    
    def _load_configurations(self) -> None:
        """Load all configuration sections."""
        # Core paths - always the same location
        username = self._get_current_user()
        self.di_platform_dir = Path(f"/Users/{username}/di-websites-platform")
        self.dealer_themes_dir = self.di_platform_dir / "dealer-themes"
        self.common_theme_dir = (
            self.di_platform_dir / 
            "app/dealer-inspire/wp-content/themes/DealerInspireCommonTheme"
        )
        

        
        # Git configuration
        self.git = GitConfig(
            user_name=os.getenv("GIT_USER_NAME", "SBM Tool"),
            user_email=os.getenv("GIT_USER_EMAIL", "sbm@dealerinspire.com"),
            default_branch=os.getenv("GIT_DEFAULT_BRANCH", "main"),
            default_reviewers=self._get_list("SBM_DEFAULT_REVIEWERS", ["carsdotcom/fe-dev"]),
            default_labels=self._get_list("SBM_DEFAULT_LABELS", ["fe-dev"])
        )
        
        # GitHub configuration
        self.github = GitHubConfig(
            token=self._get_github_token(),
            org=os.getenv("GITHUB_ORG", "carsdotcom"),
            repo=os.getenv("GITHUB_REPO", "di-websites-platform")
        )
        
        # Demo configuration
        self.demo = DemoConfig(
            enabled=self._get_bool("DEMO_MODE", False),
            skip_git=self._get_bool("DEMO_SKIP_GIT", False),
            timeout=int(os.getenv("DEMO_TIMEOUT", "300")),
            skip_startup=self._get_bool("DEMO_SKIP_STARTUP", False)
        )
        

        
        # General settings
        self.force_reset = self._get_bool("SBM_FORCE_RESET", False)
        self.skip_validation = self._get_bool("SBM_SKIP_VALIDATION", False)
        self.dev_mode = self._get_bool("DEV_MODE", False)
        self.verbose = self._get_bool("VERBOSE_OUTPUT", False)
        
        # Logging configuration
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.log_file = os.getenv("LOG_FILE", "sbm.log")
        self.log_format = os.getenv(
            "LOG_FORMAT", 
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
    
    def _get_bool(self, key: str, default: bool = False) -> bool:
        """Get boolean value from environment."""
        value = os.getenv(key)
        if value is None:
            return default
        
        value = value.lower()
        if value in ("true", "1", "yes", "on"):
            return True
        else:
            # Any other value (including empty string, "false", "invalid", etc.) is False
            return False
    
    def _get_list(self, key: str, default: Optional[List[str]] = None) -> List[str]:
        """Get list value from environment (comma-separated)."""
        if default is None:
            default = []
        
        value = os.getenv(key, "")
        if not value:
            return default
        
        return [item.strip() for item in value.split(",") if item.strip()]
    
    def get_theme_path(self, slug: str) -> Path:
        """
        Get the path to a dealer theme directory.
        
        Args:
            slug: Dealer theme slug
            
        Returns:
            Path to the theme directory
        """
        return self.dealer_themes_dir / slug
    
    def validate_theme_exists(self, slug: str) -> bool:
        """
        Check if a dealer theme exists.
        
        Args:
            slug: Dealer theme slug
            
        Returns:
            True if theme exists, False otherwise
        """
        theme_path = self.get_theme_path(slug)
        return theme_path.exists() and theme_path.is_dir()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary for debugging."""
        return {
            "di_platform_dir": str(self.di_platform_dir),
            "dealer_themes_dir": str(self.dealer_themes_dir),
            "common_theme_dir": str(self.common_theme_dir),

            "git": {
                "user_name": self.git.user_name,
                "user_email": self.git.user_email,
                "default_branch": self.git.default_branch,
                "default_reviewers": self.git.default_reviewers,
                "default_labels": self.git.default_labels
            },
            "github": {
                "org": self.github.org,
                "repo": self.github.repo,
                "token_set": bool(self.github.token)
            },
            "demo": {
                "enabled": self.demo.enabled,
                "skip_git": self.demo.skip_git,
                "timeout": self.demo.timeout,
                "skip_startup": self.demo.skip_startup
            },

            "general": {
                "force_reset": self.force_reset,
                "skip_validation": self.skip_validation,
                "dev_mode": self.dev_mode,
                "verbose": self.verbose,
                "log_level": self.log_level
            }
        }

    def _get_current_user(self) -> str:
        """Get current username."""
        try:
            import subprocess
            return subprocess.check_output(["id", "-un"]).decode().strip()
        except Exception:
            return os.getenv("USER", "nathanhart")  # fallback
    
    def _get_github_token(self) -> Optional[str]:
        """Get GitHub token from MCP config or environment."""
        # Try MCP config first
        try:
            mcp_config_path = Path.home() / ".cursor" / "mcp.json"
            if mcp_config_path.exists():
                import json
                with open(mcp_config_path) as f:
                    mcp_config = json.load(f)
                    github_env = mcp_config.get("mcpServers", {}).get("GitHub", {}).get("env", {})
                    if "GITHUB_PERSONAL_ACCESS_TOKEN" in github_env:
                        return github_env["GITHUB_PERSONAL_ACCESS_TOKEN"]
        except Exception:
            pass
        
        # Fallback to environment
        return os.getenv("GITHUB_TOKEN")
    



# Global configuration instance
_config: Optional[Config] = None


def get_config(env_file: Optional[str] = None) -> Config:
    """
    Get the global configuration instance.
    
    Args:
        env_file: Optional path to .env file to load
        
    Returns:
        Configuration instance
    """
    global _config
    if _config is None:
        _config = Config(env_file)
    return _config


def reset_config() -> None:
    """Reset the global configuration instance (for testing)."""
    global _config
    _config = None 
