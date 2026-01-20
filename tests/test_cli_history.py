"""Tests for enhanced CLI history display (Story 1-3)."""

import pytest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

from sbm.cli import _format_duration, _calculate_time_saved, cli


class TestFormatDuration:
    """Test the _format_duration helper function."""

    def test_format_duration_seconds_only(self):
        """Test formatting for durations under 1 minute."""
        assert _format_duration(45.5) == "45s"
        assert _format_duration(5.0) == "5s"
        assert _format_duration(59.9) == "59s"

    def test_format_duration_sub_second(self):
        """Test formatting for sub-second durations."""
        assert _format_duration(0.5) == "< 1s"
        assert _format_duration(0.0) == "< 1s"
        assert _format_duration(0.99) == "< 1s"

    def test_format_duration_minutes_and_seconds(self):
        """Test formatting for durations with minutes and seconds."""
        assert _format_duration(90) == "1m 30s"
        assert _format_duration(125.7) == "2m 5s"
        assert _format_duration(60) == "1m 0s"
        assert _format_duration(120) == "2m 0s"

    def test_format_duration_large_values(self):
        """Test formatting for large durations."""
        assert _format_duration(3600) == "60m 0s"
        assert _format_duration(7200) == "120m 0s"
        assert _format_duration(3661) == "61m 1s"


class TestCalculateTimeSaved:
    """Test the _calculate_time_saved helper function."""

    def test_calculate_time_saved_standard(self):
        """Test time saved calculation for standard values."""
        assert _calculate_time_saved(800) == "1.0h"
        assert _calculate_time_saved(1600) == "2.0h"
        assert _calculate_time_saved(400) == "0.5h"
        assert _calculate_time_saved(2400) == "3.0h"

    def test_calculate_time_saved_zero(self):
        """Test time saved calculation for zero lines."""
        assert _calculate_time_saved(0) == "-"

    def test_calculate_time_saved_small_values(self):
        """Test time saved calculation for small values."""
        assert _calculate_time_saved(50) == "< 0.1h"
        assert _calculate_time_saved(79) == "< 0.1h"

    def test_calculate_time_saved_decimal(self):
        """Test time saved calculation for values that result in decimals."""
        assert _calculate_time_saved(850) == "1.1h"
        assert _calculate_time_saved(1234) == "1.5h"


class TestStatsHistoryCommand:
    """Test the stats --history command."""

    @patch("sbm.cli.get_migration_stats")
    @patch("sbm.cli.get_console")
    def test_stats_history_runs_without_error(self, mock_console, mock_stats):
        """Test that stats --history command runs without error."""
        mock_stats.return_value = {
            "count": 5,
            "migrations": [],
            "runs": [],
            "metrics": {},
            "global_metrics": {},
            "last_updated": None,
            "path": "/tmp/test",
            "user_id": "test-user",
        }
        mock_console.return_value = MagicMock()

        runner = CliRunner()
        result = runner.invoke(cli, ["stats", "--history"])
        # Should not crash even with empty runs
        assert result.exit_code == 0

    @patch("sbm.cli.get_migration_stats")
    @patch("sbm.cli.get_console")
    def test_stats_history_with_limit(self, mock_console, mock_stats):
        """Test stats --history --limit option."""
        mock_stats.return_value = {
            "count": 0,
            "migrations": [],
            "runs": [],
            "metrics": {},
            "global_metrics": {},
            "last_updated": None,
            "path": "/tmp/test",
            "user_id": "test-user",
        }
        mock_console.return_value = MagicMock()

        runner = CliRunner()
        result = runner.invoke(cli, ["stats", "--history", "--limit", "25"])
        assert result.exit_code == 0

    @patch("sbm.cli.get_migration_stats")
    @patch("sbm.cli.get_console")
    def test_stats_history_with_since_filter(self, mock_console, mock_stats):
        """Test stats --history with --since days filter."""
        mock_stats.return_value = {
            "count": 0,
            "migrations": [],
            "runs": [
                {
                    "timestamp": "2026-01-09T10:00:00Z",
                    "slug": "test-theme",
                    "command": "auto",
                    "status": "success",
                    "duration_seconds": 45.5,
                    "lines_migrated": 850,
                }
            ],
            "metrics": {},
            "global_metrics": {},
            "last_updated": None,
            "path": "/tmp/test",
            "user_id": "test-user",
        }
        mock_console.return_value = MagicMock()

        runner = CliRunner()
        result = runner.invoke(cli, ["stats", "--history", "--since", "7"])
        assert result.exit_code == 0

    @patch("sbm.cli.get_migration_stats")
    @patch("sbm.cli.get_console")
    def test_stats_history_invalid_date_format(self, mock_console, mock_stats):
        """Test stats --history with invalid since value."""
        mock_stats.return_value = {
            "count": 0,
            "migrations": [],
            "runs": [],
            "metrics": {},
            "global_metrics": {},
            "last_updated": None,
            "path": "/tmp/test",
            "user_id": "test-user",
        }
        # Create a mock console with a mock rich_console
        mock_rich_console = MagicMock()
        mock_console_obj = MagicMock()
        mock_console_obj.console = mock_rich_console
        mock_console.return_value = mock_console_obj

        runner = CliRunner()
        result = runner.invoke(cli, ["stats", "--history", "--since", "invalid-date"])
        # Click should reject non-integer --since values
        assert result.exit_code != 0


class TestStatsHistoryBackwardCompatibility:
    """Test backward compatibility with old run data."""

    @patch("sbm.cli.get_migration_stats")
    @patch("sbm.cli.get_console")
    def test_old_run_data_without_new_fields(self, mock_console, mock_stats):
        """Test that old runs without new fields display gracefully."""
        # Simulate old run data without lines_migrated, duration_seconds, report_path
        mock_stats.return_value = {
            "count": 1,
            "migrations": ["old-theme"],
            "runs": [
                {
                    "timestamp": "2025-12-01T10:00:00Z",
                    "slug": "old-theme",
                    "command": "auto",
                    "status": "success",
                    # Missing: duration_seconds, lines_migrated, report_path
                }
            ],
            "metrics": {},
            "global_metrics": {},
            "last_updated": "2025-12-01T10:00:00Z",
            "path": "/tmp/test",
            "user_id": "test-user",
        }
        mock_console.return_value = MagicMock()

        runner = CliRunner()
        result = runner.invoke(cli, ["stats", "--history"])
        # Should not crash with missing fields
        assert result.exit_code == 0

    @patch("sbm.cli.get_migration_stats")
    @patch("sbm.cli.get_console")
    def test_partial_run_data(self, mock_console, mock_stats):
        """Test runs with some but not all new fields."""
        mock_stats.return_value = {
            "count": 1,
            "migrations": ["partial-theme"],
            "runs": [
                {
                    "timestamp": "2026-01-05T10:00:00Z",
                    "slug": "partial-theme",
                    "command": "auto",
                    "status": "success",
                    "duration_seconds": 90.5,
                    "lines_migrated": 500,
                    # Missing: report_path
                }
            ],
            "metrics": {},
            "global_metrics": {},
            "last_updated": "2026-01-05T10:00:00Z",
            "path": "/tmp/test",
            "user_id": "test-user",
        }
        mock_console.return_value = MagicMock()

        runner = CliRunner()
        result = runner.invoke(cli, ["stats", "--history"])
        assert result.exit_code == 0
