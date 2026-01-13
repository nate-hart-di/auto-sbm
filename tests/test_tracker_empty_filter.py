import pytest
from unittest.mock import MagicMock, patch
from sbm.utils import tracker


@pytest.fixture
def mock_firebase_settings():
    with patch("sbm.utils.tracker.get_settings") as mock_settings:
        mock_settings.return_value.firebase.is_user_mode.return_value = False
        mock_settings.return_value.firebase.is_configured.return_value = True
        yield mock_settings


@pytest.fixture
def mock_is_firebase_available():
    with patch("sbm.utils.tracker.is_firebase_available", return_value=True) as mock:
        yield mock


@pytest.fixture
def mock_tracker_io(tmp_path):
    # Mock read/write tracker to use a temp file
    tracker_file = tmp_path / ".sbm_migrations_test.json"
    with patch("sbm.utils.tracker.TRACKER_FILE", tracker_file):
        yield tracker_file


def test_record_run_skips_empty_migration_sync(
    mock_firebase_settings, mock_is_firebase_available, mock_tracker_io
):
    """Verify that a run with 0 lines migrated is skipped and marked as skipped_empty."""

    # Mock FirebaseSync to ensure push_run is NOT called
    with patch("sbm.utils.tracker.FirebaseSync") as MockFirebaseSync:
        mock_sync_instance = MockFirebaseSync.return_value

        # Record a run with 0 lines
        tracker.record_run(
            slug="test-empty-slug",
            command="migrate",
            status="success",
            duration=10.0,
            automation_time=5.0,
            lines_migrated=0,  # CRITICAL: 0 lines
            files_created_count=4,
            scss_line_count=100,
        )

        # Verify sync.push_run was NOT called
        mock_sync_instance.push_run.assert_not_called()

        # Verify the local file content
        data = tracker._read_tracker()
        last_run = data["runs"][-1]

        assert last_run["slug"] == "test-empty-slug"
        assert last_run["lines_migrated"] == 0
        assert last_run["sync_status"] == "skipped_empty"


def test_record_run_syncs_valid_migration(
    mock_firebase_settings, mock_is_firebase_available, mock_tracker_io
):
    """Verify that a run with >0 lines migrated is synced."""

    with patch("sbm.utils.tracker.FirebaseSync") as MockFirebaseSync:
        mock_sync_instance = MockFirebaseSync.return_value
        mock_sync_instance.push_run.return_value = True

        # Record a run with 100 lines
        tracker.record_run(
            slug="test-valid-slug",
            command="migrate",
            status="success",
            duration=10.0,
            automation_time=5.0,
            lines_migrated=100,  # CRITICAL: > 0 lines
            files_created_count=4,
            scss_line_count=100,
        )

        # Verify sync.push_run WAS called
        mock_sync_instance.push_run.assert_called_once()

        # Verify status is synced
        data = tracker._read_tracker()
        last_run = data["runs"][-1]
        assert last_run["sync_status"] == "synced"
