from unittest.mock import patch

import pytest
from click.testing import CliRunner

from sbm.cli import cli
from sbm.config import Config
from sbm.ui.console import SBMConsole


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

    # Use real SBMConsole so output goes to stdout (captured by runner)
    real_sbm_console = SBMConsole(config=Config({}))

    with patch("sbm.cli.get_console", return_value=real_sbm_console), patch("sbm.cli.get_settings"):
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

    real_sbm_console = SBMConsole(config=Config({}))

    with patch("sbm.cli.get_console", return_value=real_sbm_console), patch("sbm.cli.get_settings"):
        result = runner.invoke(cli, ["stats"])
        assert "auth-uid-123" in result.output
