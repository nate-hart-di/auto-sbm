import pytest
from unittest.mock import MagicMock, patch, ANY
from sbm.utils.tracker import process_pending_syncs, record_run, _write_tracker, _read_tracker


@pytest.fixture
def mock_tracker_file(tmp_path):
    tracker_file = tmp_path / ".sbm_migrations.json"
    return tracker_file


@pytest.fixture
def mock_firebase(mocker):
    # Mock firebase availability
    mocker.patch("sbm.utils.tracker.is_firebase_available", return_value=True)
    mocker.patch("sbm.utils.firebase_sync.is_firebase_available", return_value=True)
    # Mock slug validation to allow test slugs
    mocker.patch("sbm.utils.tracker.is_official_slug", return_value=True)
    settings = MagicMock()
    settings.firebase.is_admin_mode.return_value = True
    settings.firebase.database_url = "https://test.firebaseio.com"
    mocker.patch("sbm.utils.firebase_sync.get_settings", return_value=settings)
    mock_db = MagicMock()
    mocker.patch("sbm.utils.firebase_sync.get_firebase_db", return_value=mock_db)
    return mock_db


def test_record_run_offline_sets_pending(mocker, mock_tracker_file):
    """Test that if Firebase is offline, run is saved with 'pending_sync' status."""
    mocker.patch("sbm.utils.tracker.TRACKER_FILE", mock_tracker_file)

    # Simulate Firebase offline
    mocker.patch("sbm.utils.tracker.is_firebase_available", return_value=False)

    # Run record_run
    record_run(
        slug="test-offline-slug",
        command="migrate",
        status="success",
        duration=10.0,
        automation_time=5.0,
    )

    # Check local file
    data = _read_tracker()
    runs = data.get("runs", [])
    assert len(runs) == 1
    assert runs[0]["sync_status"] == "pending_sync"
    assert runs[0]["slug"] == "test-offline-slug"


def test_process_pending_syncs_success(mocker, mock_tracker_file, mock_firebase):
    """Test that process_pending_syncs uploads pending items and updates status."""
    mocker.patch("sbm.utils.tracker.TRACKER_FILE", mock_tracker_file)

    # Setup initial state with one pending run
    initial_data = {
        "runs": [
            {
                "slug": "pending-slug",
                "status": "success",
                "sync_status": "pending_sync",
                "lines_migrated": 100,
                "timestamp": "2024-01-01T00:00:00Z",
            }
        ]
    }
    _write_tracker(initial_data)

    # Verify mock firebase setup
    ref_mock = mock_firebase.reference.return_value

    # Run process
    process_pending_syncs()

    # Verify push was called
    ref_mock.push.assert_called_once()
    call_args = ref_mock.push.call_args[0][0]
    assert call_args["slug"] == "pending-slug"
    assert "sync_status" not in call_args  # Should not push sync_status field

    # Verify local file updated
    data = _read_tracker()
    assert data["runs"][0]["sync_status"] == "synced"


def test_process_pending_syncs_failure_remains_pending(mocker, mock_tracker_file, mock_firebase):
    """Test that if upload fails, status remains pending."""
    mocker.patch("sbm.utils.tracker.TRACKER_FILE", mock_tracker_file)

    initial_data = {
        "runs": [{"slug": "fail-slug", "status": "success", "sync_status": "pending_sync"}]
    }
    _write_tracker(initial_data)

    # Mock push raising exception
    ref_mock = mock_firebase.reference.return_value
    ref_mock.push.side_effect = Exception("Connection error")

    process_pending_syncs()

    data = _read_tracker()
    assert data["runs"][0]["sync_status"] == "pending_sync"
