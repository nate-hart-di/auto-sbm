"""
Configuration management for SBM Tool V2.

Handles environment variables, validation, and configuration for all components
including Context7 integration, Git operations, and Stellantis-specific settings.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from dotenv import load_dotenv

from sbm.utils.errors import ConfigurationError


@dataclass
class Context7Config:
    """Context7 MCP server configuration."""
    
    server_url: str = "http://localhost:3001"
    api_key: Optional[str] = None
    timeout: int = 30
    enabled: bool = True


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
class StellantisConfig:
    """Stellantis-specific processing configuration."""
    
    enhanced_mode: bool = True
    brand_detection: str = "auto"
    map_processing: bool = True
    
    # Brand patterns for detection
    brand_patterns: Dict[str, List[str]] = field(default_factory=lambda: {
        'chrysler': ['chrysler', 'chryslerof', 'chrysler-'],
        'dodge': ['dodge', 'dodgeof', 'dodge-'],
        'jeep': ['jeep', 'jeepof', 'jeep-'],
        'ram': ['ram', 'ramof', 'ram-', 'ramtrucks'],
        'fiat': ['fiat', 'fiatof', 'fiat-'],
        'cdjr': ['cdjr', 'cdjrof', 'chryslerdodgejeepram'],
        'fca': ['fca', 'fcaof', 'fiat-chrysler']
    })


@dataclass
class DemoConfig:
    """Demo mode configuration for live presentations."""
    
    enabled: bool = False
    timeout: int = 300
    skip_git: bool = False
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
        
        # Context7 configuration
        self.context7 = Context7Config(
            server_url=os.getenv("CONTEXT7_SERVER_URL", "http://localhost:3001"),
            api_key=self._get_context7_key(),
            timeout=int(os.getenv("CONTEXT7_TIMEOUT", "30")),
            enabled=not self._get_bool("SKIP_CONTEXT7", False)
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
        
        # Stellantis configuration
        self.stellantis = StellantisConfig(
            enhanced_mode=self._get_bool("STELLANTIS_ENHANCED_MODE", True),
            brand_detection=os.getenv("STELLANTIS_BRAND_DETECTION", "auto"),
            map_processing=self._get_bool("STELLANTIS_MAP_PROCESSING", True)
        )
        
        # Demo configuration
        self.demo = DemoConfig(
            enabled=self._get_bool("DEMO_MODE", False),
            timeout=int(os.getenv("DEMO_TIMEOUT", "300")),
            skip_git=self._get_bool("DEMO_SKIP_GIT", False),
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
            "context7": {
                "server_url": self.context7.server_url,
                "timeout": self.context7.timeout,
                "enabled": self.context7.enabled,
                "api_key_set": bool(self.context7.api_key)
            },
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
            "stellantis": {
                "enhanced_mode": self.stellantis.enhanced_mode,
                "brand_detection": self.stellantis.brand_detection,
                "map_processing": self.stellantis.map_processing
            },
            "demo": {
                "enabled": self.demo.enabled,
                "timeout": self.demo.timeout,
                "skip_git": self.demo.skip_git,
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
    
    def _get_context7_key(self) -> Optional[str]:
        """Get Context7 API key from MCP config or environment."""
        # Try MCP config first
        try:
            mcp_config_path = Path.home() / ".cursor" / "mcp.json"
            if mcp_config_path.exists():
                import json
                with open(mcp_config_path) as f:
                    mcp_config = json.load(f)
                    context7_env = mcp_config.get("mcpServers", {}).get("context7-mcp", {}).get("args", [])
                    # Look for --key argument
                    for i, arg in enumerate(context7_env):
                        if arg == "--key" and i + 1 < len(context7_env):
                            return context7_env[i + 1]
        except Exception:
            pass
        
        # Fallback to environment
        return os.getenv("CONTEXT7_API_KEY")


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
