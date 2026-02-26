"""
Integration tests for Firebase connectivity.

These tests attempt to actually connect to Firebase if credentials are available.
They are marked to be skipped if no credentials are found.
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sbm.config import AutoSBMSettings, FirebaseSettings
from sbm.utils.firebase_sync import get_firebase_db, is_firebase_available, reset_firebase


# Check for credentials in common locations
def get_credentials_path() -> Path | None:
    # 1. Env var
    env_path = os.getenv("FIREBASE__CREDENTIALS_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    # 2. Default location in repo (if ignored)
    default_path = Path("firebase-service-account.json")
    if default_path.exists():
        return default_path

    return None


def get_database_url() -> str | None:
    return os.getenv("FIREBASE__DATABASE_URL")


CREDENTIALS_PATH = get_credentials_path()
DATABASE_URL = get_database_url()
HAS_CREDENTIALS = CREDENTIALS_PATH is not None and DATABASE_URL is not None


@pytest.mark.integration
@pytest.mark.skipif(not HAS_CREDENTIALS, reason="No Firebase credentials found")
class TestFirebaseIntegration:
    """Integration tests focusing on actual connection."""

    @pytest.fixture(autouse=True)
    def setup_integration(self):
        """Setup real configuration for integration tests."""
        reset_firebase()

        # Override settings to use real credentials
        with patch("sbm.utils.firebase_sync.get_settings") as mock_settings:
            real_settings = MagicMock(spec=AutoSBMSettings)
            real_settings.firebase = FirebaseSettings(
                credentials_path=CREDENTIALS_PATH, database_url=DATABASE_URL
            )
            mock_settings.return_value = real_settings
            yield

        reset_firebase()

    def test_connection_and_basic_ops(self):
        """Test authentication and basic read/write."""
        # 1. Initialize
        assert is_firebase_available()

        # 2. Get DB reference
        db = get_firebase_db()
        assert db is not None

        # 3. Perform a test write (to a test path)
        try:
            ref = db.reference("integration_test/ping")
            ref.set({"status": "ok", "timestamp": {".sv": "timestamp"}})

            # 4. Perform a read
            data = ref.get()
            assert data is not None
            assert data.get("status") == "ok"

            # Cleanup
            ref.delete()
        except Exception as e:
            pytest.fail(f"Firebase integration operation failed: {e}")
