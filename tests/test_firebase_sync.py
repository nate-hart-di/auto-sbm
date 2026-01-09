"""
Tests for the Firebase synchronization module.
"""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from sbm.utils.firebase_sync import (
    is_firebase_available,
    get_firebase_db,
    reset_firebase,
    FirebaseInitializationError,
    _initialize_firebase,
)
from sbm.config import AutoSBMSettings, FirebaseSettings


@pytest.fixture(autouse=True)
def clean_firebase_state():
    """Reset firebase state before each test."""
    reset_firebase()
    yield
    reset_firebase()


@pytest.fixture
def mock_settings(tmp_path):
    """Create mock settings with configured firebase."""
    creds_file = tmp_path / "test-creds.json"
    creds_file.touch()

    firebase_settings = FirebaseSettings(
        credentials_path=creds_file, database_url="https://test.firebaseio.com"
    )

    settings = MagicMock(spec=AutoSBMSettings)
    settings.firebase = firebase_settings
    return settings


class TestFirebaseInitialization:
    @patch("sbm.utils.firebase_sync.get_settings")
    def test_initialization_not_configured(self, mock_get_settings):
        """Test initialization when not configured returns False."""
        # Create unconfigured settings
        settings = MagicMock(spec=AutoSBMSettings)
        settings.firebase = MagicMock()
        settings.firebase.is_configured.return_value = False
        mock_get_settings.return_value = settings

        assert is_firebase_available() is False
        assert _initialize_firebase() is False

    @patch("sbm.utils.firebase_sync.get_settings")
    @patch("firebase_admin.credentials.Certificate")
    @patch("firebase_admin.initialize_app")
    def test_initialization_success(
        self, mock_init_app, mock_cert, mock_get_settings, mock_settings
    ):
        """Test successful initialization."""
        mock_get_settings.return_value = mock_settings

        assert _initialize_firebase() is True
        assert is_firebase_available() is True

        # Verify calls
        mock_cert.assert_called_with(str(mock_settings.firebase.credentials_path))
        mock_init_app.assert_called_once()

    @patch("sbm.utils.firebase_sync.get_settings")
    @patch("firebase_admin.credentials.Certificate")
    @patch("firebase_admin.initialize_app")
    def test_idempotent_initialization(
        self, mock_init_app, mock_cert, mock_get_settings, mock_settings
    ):
        """Test that multiple calls don't re-initialize."""
        mock_get_settings.return_value = mock_settings

        # First call
        assert _initialize_firebase() is True

        # Second call
        assert _initialize_firebase() is True

        # Should still be called only once
        mock_init_app.assert_called_once()

    @patch("sbm.utils.firebase_sync.get_settings")
    def test_missing_firebase_admin_package(self, mock_get_settings, mock_settings):
        """Test behavior when firebase-admin is not installed."""
        mock_get_settings.return_value = mock_settings

        # Simulate import error by ensuring sys.modules['firebase_admin'] is None
        with patch.dict("sys.modules", {"firebase_admin": None}):
            # We must also clear it if it exists to force re-import check
            # but usually patching to None triggers ImportError on import
            with pytest.raises(FirebaseInitializationError, match="not installed"):
                _initialize_firebase()

    @patch("sbm.utils.firebase_sync.get_settings")
    @patch("firebase_admin.credentials.Certificate")
    def test_invalid_credentials_file(self, mock_cert, mock_get_settings, mock_settings):
        """Test handling of invalid credentials file."""
        mock_get_settings.return_value = mock_settings
        mock_cert.side_effect = ValueError("Invalid certificate")

        assert _initialize_firebase() is False


class TestFirebaseDBAccess:
    def test_get_db_not_initialized(self):
        """Test getting DB without initialization raises error."""
        with patch("sbm.utils.firebase_sync.is_firebase_available", return_value=False):
            with pytest.raises(FirebaseInitializationError, match="not available"):
                get_firebase_db()

    @patch("sbm.utils.firebase_sync.is_firebase_available")
    def test_get_db_success(self, mock_available):
        """Test success when available."""
        mock_available.return_value = True

        mock_db_module = MagicMock()
        mock_firebase = MagicMock()
        mock_firebase.db = mock_db_module

        # Patch sys.modules to mock firebase_admin and firebase_admin.db
        with patch.dict(
            "sys.modules", {"firebase_admin": mock_firebase, "firebase_admin.db": mock_db_module}
        ):
            db = get_firebase_db()
            assert db == mock_db_module
