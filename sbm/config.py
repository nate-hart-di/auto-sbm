"""
Configuration management for the SBM tool.

This module handles loading and accessing configuration settings.
"""

import json
from pathlib import Path

class ConfigurationError(Exception):
    """Custom exception for configuration-related errors."""
    pass

class Config:
    """
    Represents the configuration settings for the SBM tool.
    """
    def __init__(self, settings: dict):
        self._settings = settings

    def get_setting(self, key: str, default=None):
        """Get a configuration setting by key."""
        return self._settings.get(key, default)

    def __getattr__(self, name):
        """Allow direct access to settings as attributes."""
        if name in self._settings:
            return self._settings[name]
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

def get_config(config_path: str = 'config.json') -> Config:
    """
    Loads configuration from a JSON file.

    Args:
        config_path (str): Path to the configuration file.

    Returns:
        Config: A Config object containing the loaded settings.

    Raises:
        ConfigurationError: If the config file is not found or is invalid.
    """
    config_file = Path(config_path)
    if not config_file.exists():
        raise ConfigurationError(f"Configuration file not found: {config_path}")

    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            settings = json.load(f)
        return Config(settings)
    except json.JSONDecodeError as e:
        raise ConfigurationError(f"Invalid JSON in config file {config_path}: {e}")
    except Exception as e:
        raise ConfigurationError(f"Error loading config file {config_path}: {e}")
