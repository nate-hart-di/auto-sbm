import pytest
from unittest.mock import patch, MagicMock
from sbm.utils.tracker import record_run, _read_tracker


class TestTrackerReports:
    @pytest.fixture
    def mock_tracker_file(self, tmp_path):
        tracker_file = tmp_path / ".sbm_migrations.json"
        with patch("sbm.utils.tracker.TRACKER_FILE", tracker_file):
            yield tracker_file

    @patch("sbm.utils.tracker.is_firebase_available")
    def test_record_run_with_report_path(self, mock_is_available, mock_tracker_file):
        # Setup
        mock_is_available.return_value = False

        # Execute
        record_run(
            slug="report-test",
            command="auto",
            status="success",
            duration=10.0,
            automation_time=5.0,
            report_path="/path/to/report.md",
        )

        # Verify
        data = _read_tracker()
        last_run = data["runs"][-1]
        assert last_run["report_path"] == "/path/to/report.md"

    @patch("sbm.utils.tracker.is_firebase_available")
    def test_record_run_backward_compatibility(self, mock_is_available, mock_tracker_file):
        # Setup
        mock_is_available.return_value = False

        # Execute without report_path
        record_run(
            slug="compat-test", command="auto", status="success", duration=10.0, automation_time=5.0
        )

        # Verify
        data = _read_tracker()
        last_run = data["runs"][-1]
        # Should be None or not present, depending on implementation
        # The current implementation sets it to None in the dict definition if passed as None,
        # but let's verify it handles the absence in signature (it has default=None)
        assert last_run["report_path"] is None
