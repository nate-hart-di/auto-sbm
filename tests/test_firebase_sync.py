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
    FirebaseSync,
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
    def test_initialization_success(self, mock_get_settings, mock_settings):
        """Test successful initialization."""
        mock_get_settings.return_value = mock_settings
        mock_firebase_admin = MagicMock()
        mock_creds = MagicMock()
        mock_creds.Certificate.return_value = "cert"
        mock_firebase_admin.credentials = mock_creds
        mock_firebase_admin._apps = []
        mock_firebase_admin.initialize_app.return_value = MagicMock()

        with patch.dict(
            "sys.modules",
            {"firebase_admin": mock_firebase_admin, "firebase_admin.credentials": mock_creds},
        ):
            assert _initialize_firebase() is True
            assert is_firebase_available() is True

        # Verify calls
        mock_creds.Certificate.assert_called_with(str(mock_settings.firebase.credentials_path))
        mock_firebase_admin.initialize_app.assert_called_once()

    @patch("sbm.utils.firebase_sync.get_settings")
    def test_idempotent_initialization(self, mock_get_settings, mock_settings):
        """Test that multiple calls don't re-initialize."""
        mock_get_settings.return_value = mock_settings
        mock_firebase_admin = MagicMock()
        mock_creds = MagicMock()
        mock_creds.Certificate.return_value = "cert"
        mock_firebase_admin.credentials = mock_creds
        mock_firebase_admin._apps = []
        mock_firebase_admin.initialize_app.return_value = MagicMock()

        with patch.dict(
            "sys.modules",
            {"firebase_admin": mock_firebase_admin, "firebase_admin.credentials": mock_creds},
        ):
            # First call
            assert _initialize_firebase() is True
            # Second call
            assert _initialize_firebase() is True

        # Should still be called only once
        mock_firebase_admin.initialize_app.assert_called_once()

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
    def test_invalid_credentials_file(self, mock_get_settings, mock_settings):
        """Test handling of invalid credentials file."""
        mock_get_settings.return_value = mock_settings
        mock_firebase_admin = MagicMock()
        mock_creds = MagicMock()
        mock_creds.Certificate.side_effect = ValueError("Invalid certificate")
        mock_firebase_admin.credentials = mock_creds
        mock_firebase_admin._apps = []

        with patch.dict(
            "sys.modules",
            {"firebase_admin": mock_firebase_admin, "firebase_admin.credentials": mock_creds},
        ):
            assert _initialize_firebase() is False


class TestFirebaseDBAccess:
    def test_get_db_not_initialized(self):
        """Test getting DB without initialization raises error."""
        with patch("sbm.utils.firebase_sync.is_firebase_available", return_value=False):
            with patch("sbm.utils.firebase_sync.get_settings") as mock_settings:
                # Mock unconfigured Firebase
                mock_settings.return_value.firebase.is_configured.return_value = False
                with pytest.raises(FirebaseInitializationError, match="Firebase not available"):
                    get_firebase_db()

    @patch("sbm.utils.firebase_sync.is_firebase_available")
    @patch("sbm.utils.firebase_sync.get_settings")
    def test_get_db_success(self, mock_get_settings, mock_available):
        """Test success when available."""
        mock_available.return_value = True
        settings = MagicMock()
        settings.firebase.is_admin_mode.return_value = True
        mock_get_settings.return_value = settings

        mock_db_module = MagicMock()
        mock_firebase = MagicMock()
        mock_firebase.db = mock_db_module

        # Patch sys.modules to mock firebase_admin and firebase_admin.db
        with patch.dict(
            "sys.modules", {"firebase_admin": mock_firebase, "firebase_admin.db": mock_db_module}
        ):
            db = get_firebase_db()
            assert db == mock_db_module


class TestFirebaseSync:
    """Tests for the FirebaseSync singleton class."""

    @patch("sbm.utils.firebase_sync.is_firebase_available", return_value=True)
    def test_singleton_pattern(self, mock_av):
        """Test that FirebaseSync is a singleton."""
        instance1 = FirebaseSync()
        instance2 = FirebaseSync()
        assert instance1 is instance2

    @patch("sbm.utils.firebase_sync.is_firebase_available", return_value=False)
    def test_init_fails_if_unavailable(self, mock_av):
        """Test that init raises error if Firebase is not available."""
        # Reset instance to allow re-init attempt
        FirebaseSync._instance = None
        with pytest.raises(FirebaseInitializationError):
            FirebaseSync()

    @patch("sbm.utils.firebase_sync.is_firebase_available", return_value=True)
    @patch("sbm.utils.firebase_sync.get_firebase_db")
    @patch("sbm.utils.firebase_sync.get_settings")
    def test_push_run_success(self, mock_get_settings, mock_get_db, mock_av):
        """Test successful push_run."""
        settings = MagicMock()
        settings.firebase.is_admin_mode.return_value = True
        mock_get_settings.return_value = settings
        # Mock DB reference
        mock_ref = MagicMock()
        mock_db = MagicMock()
        mock_db.reference.return_value = mock_ref
        mock_get_db.return_value = mock_db

        sync = FirebaseSync()

        run_data = {"slug": "test_slug", "status": "success", "sync_status": "pending"}
        result = sync.push_run("user1", run_data)

        assert result is True
        mock_db.reference.assert_called_with("users/user1/runs")

        # Verify sync_status was removed
        expected_push = {"slug": "test_slug", "status": "success"}
        mock_ref.push.assert_called_with(expected_push)

    @patch("sbm.utils.firebase_sync.is_firebase_available", return_value=True)
    @patch("sbm.utils.firebase_sync.get_firebase_db")
    @patch("sbm.utils.firebase_sync.get_settings")
    def test_fetch_team_stats(self, mock_get_settings, mock_get_db, mock_av):
        """Test successful fetch_team_stats."""
        settings = MagicMock()
        settings.firebase.is_admin_mode.return_value = True
        mock_get_settings.return_value = settings
        mock_ref = MagicMock()
        mock_db = MagicMock()
        mock_db.reference.return_value = mock_ref
        mock_get_db.return_value = mock_db

        # Mock data structure
        mock_ref.get.return_value = {
            "user1": {
                "migrations": ["slug1", "slugx"],
                "runs": {
                    "id1": {
                        "status": "success",
                        "slug": "slug1",
                        "lines_migrated": 800,
                        "automation_seconds": 3600,
                    }
                }
            },
            "user2": {
                "migrations": ["slug2", "slugx"],
                "runs": {
                    "id2": {
                        "status": "success",
                        "slug": "slug2",
                        "lines_migrated": 1600,
                        "automation_seconds": 7200,
                    }
                }
            },
        }

        sync = FirebaseSync()
        stats = sync.fetch_team_stats()

        assert stats is not None
        assert stats["total_users"] == 2
        assert stats["total_runs"] == 2
        assert stats["total_migrations"] == 4
        assert stats["total_time_saved_h"] == 3.0  # (800+1600)/800
        assert stats["total_automation_time_h"] == 3.0  # (3600+7200)/3600


class TestAnonymousAuth:
    """Tests for Story 2.7: Anonymous Auth / user_mode functionality."""

    def test_is_user_mode_without_credentials(self):
        """Test that is_user_mode returns True when only database_url is set."""
        settings = FirebaseSettings(
            credentials_path=None, database_url="https://test.firebaseio.com"
        )
        assert settings.is_configured() is True  # database_url is enough
        assert settings.is_admin_mode() is False  # no credentials
        assert settings.is_user_mode() is True  # configured but not admin

    def test_is_admin_mode_with_credentials(self, tmp_path):
        """Test that is_admin_mode returns True when credentials exist."""
        creds_file = tmp_path / "test-creds.json"
        creds_file.touch()

        settings = FirebaseSettings(
            credentials_path=creds_file, database_url="https://test.firebaseio.com"
        )
        assert settings.is_configured() is True
        assert settings.is_admin_mode() is True
        assert settings.is_user_mode() is False

    def test_not_configured_without_database_url(self):
        """Test that is_configured returns False without database_url."""
        settings = FirebaseSettings(credentials_path=None, database_url=None)
        assert settings.is_configured() is False
        assert settings.is_admin_mode() is False
        assert settings.is_user_mode() is False

    @patch("sbm.utils.firebase_sync.get_settings")
    def test_user_mode_initialization(self, mock_get_settings):
        """Test Firebase initialization in user mode (no credentials)."""
        # Create user-mode settings (database_url only, no credentials)
        settings = MagicMock(spec=AutoSBMSettings)
        settings.firebase = MagicMock()
        settings.firebase.is_configured.return_value = True
        settings.firebase.is_admin_mode.return_value = False
        settings.firebase.is_user_mode.return_value = True
        settings.firebase.database_url = "https://test.firebaseio.com"
        mock_get_settings.return_value = settings

        result = _initialize_firebase()

        assert result is True
