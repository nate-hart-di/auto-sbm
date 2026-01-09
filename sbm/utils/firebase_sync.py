"""
Firebase Realtime Database synchronization module for SBM.

Provides initialization and utility functions for Firebase Admin SDK.
Part of Epic 2: Robust Team-Wide Synchronization.

Usage:
    from sbm.utils.firebase_sync import get_firebase_db, is_firebase_available

    if is_firebase_available():
        db = get_firebase_db()
        # Use db.reference() for database operations
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

from sbm.config import get_settings
from sbm.utils.logger import logger

if TYPE_CHECKING:
    from firebase_admin import db as firebase_db

# Module-level state for lazy initialization
_firebase_app: object | None = None
_firebase_initialized: bool = False
_initialization_lock = threading.Lock()


class FirebaseInitializationError(Exception):
    """Raised when Firebase initialization fails."""


def _initialize_firebase() -> bool:
    """
    Initialize Firebase Admin SDK with credentials from configuration.

    Returns:
        True if initialization successful, False otherwise.

    This function is thread-safe and idempotent - multiple calls are safe.
    """
    global _firebase_app, _firebase_initialized

    # Quick check without lock
    if _firebase_initialized:
        return _firebase_app is not None

    with _initialization_lock:
        # Double-check after acquiring lock
        if _firebase_initialized:
            return _firebase_app is not None

        try:
            settings = get_settings()

            # Check if Firebase is configured
            if not settings.firebase.is_configured():
                logger.debug("Firebase not configured - credentials_path or database_url missing")
                _firebase_initialized = True
                return False

            # Import firebase_admin only when needed (lazy import)
            try:
                import firebase_admin
                from firebase_admin import credentials
            except ImportError as e:
                logger.warning(
                    "firebase-admin package not installed. Install with: pip install firebase-admin"
                )
                _firebase_initialized = True
                raise FirebaseInitializationError("firebase-admin package not installed") from e

            # Check if already initialized (happens during testing or reload)
            if firebase_admin._apps:
                _firebase_app = firebase_admin.get_app()
                _firebase_initialized = True
                logger.debug("Firebase already initialized, reusing existing app")
                return True

            # Initialize with service account credentials
            cred = credentials.Certificate(str(settings.firebase.credentials_path))
            _firebase_app = firebase_admin.initialize_app(
                cred,
                {
                    "databaseURL": settings.firebase.database_url,
                },
            )

            logger.info("Firebase initialized successfully")
            _firebase_initialized = True
            return True

        except FirebaseInitializationError:
            # Re-raise initialization errors (e.g. missing package)
            raise
        except FileNotFoundError as e:
            logger.warning(f"Firebase credentials file not found: {e}")
            _firebase_initialized = True
            return False
        except ValueError as e:
            logger.warning(f"Invalid Firebase credentials: {e}")
            _firebase_initialized = True
            return False
        except Exception as e:
            logger.warning(f"Firebase initialization failed: {e}")
            _firebase_initialized = True
            return False


def is_firebase_available() -> bool:
    """
    Check if Firebase is available and properly configured.

    Returns:
        True if Firebase can be used for sync operations, False otherwise.

    This function will attempt to initialize Firebase if not already done.
    It's safe to call repeatedly - initialization only happens once.
    """
    try:
        return _initialize_firebase()
    except FirebaseInitializationError:
        return False


def get_firebase_db() -> "firebase_db":
    """
    Get the Firebase Realtime Database reference module.

    Returns:
        The firebase_admin.db module for database operations.

    Raises:
        FirebaseInitializationError: If Firebase is not available or initialization failed.

    Example:
        db = get_firebase_db()
        ref = db.reference('/users')
        data = ref.get()
    """
    if not is_firebase_available():
        msg = "Firebase is not available - check configuration and credentials"
        raise FirebaseInitializationError(msg)

    # Import db module (guaranteed to work if initialization succeeded)
    from firebase_admin import db

    return db


def get_firebase_app() -> object | None:
    """
    Get the initialized Firebase app instance.

    Returns:
        The Firebase app instance if initialized, None otherwise.
    """
    if not _firebase_initialized:
        _initialize_firebase()
    return _firebase_app


def reset_firebase() -> None:
    """
    Reset Firebase state for testing or reconfiguration.

    WARNING: This deletes the Firebase app instance. Only use in tests
    or when reconfiguration is explicitly required.
    """
    global _firebase_app, _firebase_initialized

    with _initialization_lock:
        if _firebase_app is not None:
            try:
                import firebase_admin

                firebase_admin.delete_app(_firebase_app)
            except Exception as e:
                logger.debug(f"Error deleting Firebase app: {e}")

        _firebase_app = None
        _firebase_initialized = False
