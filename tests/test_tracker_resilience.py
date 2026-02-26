from unittest.mock import MagicMock

import pytest

from sbm.utils.tracker import _read_tracker, _write_tracker, process_pending_syncs, record_run


@pytest.fixture
def mock_tracker_file(tmp_path):
    tracker_file = tmp_path / ".sbm_migrations.json"
    return tracker_file


@pytest.fixture
def mock_firebase(mocker):
    # Mock firebase availability
    mocker.patch("sbm.utils.tracker.is_firebase_available", return_value=True)
    mocker.patch("sbm.utils.firebase_sync.is_firebase_available", return_value=True)
    mocker.patch("sbm.utils.tracker._get_github_login", return_value="test-user")
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
    mocker.patch("sbm.utils.tracker._get_github_login", return_value="test-user")

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
    mocker.patch("sbm.utils.tracker._get_github_login", return_value="test-user")

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

    # Verify set was called on a child ref
    ref_mock.child.assert_called_once()
    ref_mock.child.return_value.set.assert_called_once()
    call_args = ref_mock.child.return_value.set.call_args[0][0]
    assert call_args["slug"] == "pending-slug"
    assert "sync_status" not in call_args  # Should not push sync_status field

    # Verify local file updated
    data = _read_tracker()
    assert data["runs"][0]["sync_status"] == "synced"


def test_process_pending_syncs_failure_remains_pending(mocker, mock_tracker_file, mock_firebase):
    """Test that if upload fails, status remains pending."""
    mocker.patch("sbm.utils.tracker.TRACKER_FILE", mock_tracker_file)
    mocker.patch("sbm.utils.tracker._get_github_login", return_value="test-user")

    initial_data = {
        "runs": [{"slug": "fail-slug", "status": "success", "sync_status": "pending_sync"}]
    }
    _write_tracker(initial_data)

    # Mock set raising exception
    ref_mock = mock_firebase.reference.return_value
    ref_mock.child.return_value.set.side_effect = Exception("Connection error")

    process_pending_syncs()

    data = _read_tracker()
    assert data["runs"][0]["sync_status"] == "pending_sync"
