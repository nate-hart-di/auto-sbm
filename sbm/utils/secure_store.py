"""Secure storage helpers for sensitive configuration values."""

from __future__ import annotations

from typing import Optional

from sbm.utils.logger import logger

SERVICE_NAME = "auto-sbm"


def _get_keyring():
    try:
        import keyring

        return keyring
    except Exception:
        return None


def is_secure_store_available() -> bool:
    """Return True if a system keyring backend is available."""
    keyring = _get_keyring()
    if keyring is None:
        return False
    try:
        keyring.get_keyring()
        return True
    except Exception:
        return False


def get_secret(key: str) -> Optional[str]:
    """Fetch a secret from the keyring."""
    keyring = _get_keyring()
    if keyring is None:
        return None
    try:
        return keyring.get_password(SERVICE_NAME, key)
    except Exception as e:
        logger.debug(f"Failed to read keyring secret {key}: {e}")
        return None


def set_secret(key: str, value: str) -> bool:
    """Store a secret in the keyring."""
    keyring = _get_keyring()
    if keyring is None:
        return False
    try:
        keyring.set_password(SERVICE_NAME, key, value)
        return True
    except Exception as e:
        logger.debug(f"Failed to write keyring secret {key}: {e}")
        return False
