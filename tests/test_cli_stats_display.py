import pytest
from click.testing import CliRunner
from unittest.mock import MagicMock, patch
from sbm.cli import cli, stats


@pytest.fixture
def mock_get_migration_stats():
    with patch("sbm.cli.get_migration_stats") as mock:
        yield mock


@pytest.fixture
def runner():
    return CliRunner()


def test_stats_display_uses_display_name(mock_get_migration_stats, runner):
    """Verify that stats display uses the display_name from stats data."""
    mock_get_migration_stats.return_value = {
        "user_id": "auth-uid-123",
        "display_name": "Friendly User",
        "count": 5,
        "metrics": {"total_lines_migrated": 1000, "total_time_saved_h": 1.2},
        "last_updated": "2026-01-01T12:00:00",
    }

    # Mock config/console/logger setup in cli.py which can be complex
    with patch("sbm.cli.get_console"), patch("sbm.cli.get_settings"):
        # We need to capture the output printed to the rich console
        # Since sbm.cli creates its own console, we might need to mock it effectively
        # Or simpler: look for the string in the runner output if rich prints to stdout

        result = runner.invoke(cli, ["stats"])

        # Check output for the display name
        assert "Friendly User" in result.output
        assert (
            "auth-uid-123" not in result.output
        )  # Should prioritize display name in header/footer


def test_stats_display_fallback_to_uid(mock_get_migration_stats, runner):
    """Verify fallback to UID if display_name is missing."""
    mock_get_migration_stats.return_value = {
        "user_id": "auth-uid-123",
        # No display_name
        "count": 5,
        "metrics": {},
        "last_updated": "2026-01-01T12:00:00",
    }

    with patch("sbm.cli.get_console"), patch("sbm.cli.get_settings"):
        result = runner.invoke(cli, ["stats"])
        assert "auth-uid-123" in result.output
