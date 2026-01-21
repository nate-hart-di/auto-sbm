import pytest
from unittest.mock import patch, MagicMock
from sbm.utils.tracker import record_run, _read_tracker, _sync_to_firebase


@pytest.fixture
def mock_tracker_file(tmp_path):
    tracker_file = tmp_path / ".sbm_migrations.json"
    with patch("sbm.utils.tracker.TRACKER_FILE", tracker_file):
        yield tracker_file


@patch("sbm.utils.tracker._get_user_id", return_value="test-user")
@patch("sbm.utils.tracker._get_github_login", return_value="test-user")
@patch("sbm.utils.firebase_sync.FirebaseSync.push_run", return_value=True)
@patch("sbm.utils.tracker.is_firebase_available")
@patch("sbm.utils.tracker.is_official_slug", return_value=True)
def test_record_run_with_metrics_and_firebase(
    mock_is_official,
    mock_is_available,
    mock_push_run,
    mock_github_login,
    mock_user_id,
    mock_tracker_file,
):
    # Setup mocks
    mock_is_available.return_value = True

    # Execute
    record_run(
        slug="test-theme",
        command="auto",
        status="success",
        duration=10.0,
        automation_time=5.0,
        lines_migrated=100,
        files_created_count=4,
        scss_line_count=500,
        report_path="/tmp/report.md",
    )

    # Verify local tracker storage
    data = _read_tracker()
    last_run = data["runs"][-1]

    assert last_run["slug"] == "test-theme"
    assert last_run["lines_migrated"] == 100
    assert last_run["files_created_count"] == 4
    assert last_run["scss_line_count"] == 500
    assert last_run["report_path"] == "/tmp/report.md"

    # Verify Firebase interactions
    mock_push_run.assert_called_once()
    pushed_data = mock_push_run.call_args[0][1]
    assert pushed_data["slug"] == "test-theme"
    assert pushed_data["files_created_count"] == 4
