from datetime import datetime
from unittest.mock import patch

import pytest
from scripts.stats.report_slack import calculate_metrics, filter_runs_by_previous_calendar_day

from sbm.core.migration import MigrationResult
from sbm.utils.tracker import record_run


@pytest.fixture
def clean_migration_result():
    return MigrationResult(
        slug="test-slug", files_created_count=5, scss_line_count=1000, report_path="/tmp/report.md"
    )


def test_migration_result_pr_fields(clean_migration_result):
    """Verify MigrationResult correctly stores new PR fields."""
    result = clean_migration_result

    # Initial state
    assert result.pr_author is None
    assert result.pr_state is None

    # Mark success with new fields
    result.mark_success(
        pr_url="https://github.com/org/repo/pull/123",
        salesforce_message="Done",
        pr_author="test-user",
        pr_state="MERGED",
    )

    # Verify updates
    assert result.pr_url == "https://github.com/org/repo/pull/123"
    assert result.pr_author == "test-user"
    assert result.pr_state == "MERGED"
    assert result.status == "success"


@patch("sbm.utils.tracker._read_tracker")
@patch("sbm.utils.tracker._write_tracker")
@patch("sbm.utils.tracker._get_github_login", return_value="author-name")
def test_record_run_stores_pr_fields(mock_github_login, mock_write, mock_read):
    """Verify record_run accepts and stores updated PR context."""
    # Setup mock data
    mock_read.return_value = {"runs": []}

    # Call record_run with new arguments
    record_run(
        slug="test-slug",
        command="auto",
        duration=60,
        automation_time=60,
        status="success",
        files_created_count=5,
        scss_line_count=500,
        report_path="/tmp/report.md",
        pr_url="https://github.com/org/repo/pull/456",
        pr_author="author-name",
        pr_state="OPEN",
    )

    # Verify write was called with correct data
    assert mock_write.called
    written_data = mock_write.call_args[0][0]
    last_run = written_data["runs"][-1]

    assert last_run["slug"] == "test-slug"
    assert last_run["pr_url"] == "https://github.com/org/repo/pull/456"
    assert last_run["pr_author"] == "author-name"
    assert last_run["pr_state"] == "OPEN"


@patch("sbm.utils.tracker._read_tracker")
@patch("sbm.utils.tracker._write_tracker")
@patch("sbm.utils.tracker._get_github_login", return_value="user-b")
def test_record_run_mismatch_author_warns(mock_github_login, mock_write, mock_read, caplog):
    """Verify mismatch between pr_author and GH login logs a warning."""
    mock_read.return_value = {"runs": []}

    record_run(
        slug="test-slug",
        command="auto",
        duration=60,
        automation_time=60,
        status="success",
        files_created_count=5,
        scss_line_count=500,
        report_path="/tmp/report.md",
        pr_url="https://github.com/org/repo/pull/456",
        pr_author="user-a",
        pr_state="OPEN",
    )

    warnings = [r for r in caplog.records if r.levelname == "WARNING"]
    assert any("PR author mismatch" in r.message for r in warnings)


def test_slack_calendar_day_filtering():
    """Verify strict previous calendar day filtering logic."""
    from zoneinfo import ZoneInfo

    tz = ZoneInfo("America/Chicago")

    # Mock "now" as Jan 15th 2026 10AM CST
    mock_now = datetime(2026, 1, 15, 10, 0, 0, tzinfo=tz)

    class FakeDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return mock_now

        @classmethod
        def fromisoformat(cls, date_string):
            return datetime.fromisoformat(date_string)

    with patch("scripts.stats.report_slack.datetime", FakeDatetime):
        # Create runs with various timestamps

        # 1. Previous Day (Jan 14th) 12:01 AM CST
        ts_valid_start = datetime(2026, 1, 14, 0, 1, 0, tzinfo=tz).isoformat()

        # 2. Previous Day (Jan 14th) 11:59 PM CST
        ts_valid_end = datetime(2026, 1, 14, 23, 59, 0, tzinfo=tz).isoformat()

        # 3. Today (Jan 15th) 00:01 AM CST (Too new)
        ts_too_new = datetime(2026, 1, 15, 0, 1, 0, tzinfo=tz).isoformat()

        # 4. Two Days Ago (Jan 13th) 11:59 PM CST (Too old)
        ts_too_old = datetime(2026, 1, 13, 23, 59, 0, tzinfo=tz).isoformat()

        runs = [
            {"slug": "valid-start", "timestamp": ts_valid_start},
            {"slug": "valid-end", "timestamp": ts_valid_end},
            {"slug": "too-new", "timestamp": ts_too_new},
            {"slug": "too-old", "timestamp": ts_too_old},
        ]

        filtered = filter_runs_by_previous_calendar_day(runs, "America/Chicago")

        slugs = [r["slug"] for r in filtered]
        assert "valid-start" in slugs
        assert "valid-end" in slugs
        assert "too-new" not in slugs
        assert "too-old" not in slugs
        assert len(filtered) == 2


def test_calculate_metrics_counts_pr_states():
    runs = [
        {
            "status": "success",
            "slug": "merged",
            "merged_at": "2026-01-10T10:00:00+00:00",
            "lines_migrated": 800,
            "automation_seconds": 3600,
        },
        {
            "status": "success",
            "slug": "open",
            "created_at": "2026-01-11T10:00:00+00:00",
            "pr_state": "OPEN",
        },
        {
            "status": "success",
            "slug": "closed",
            "pr_state": "CLOSED",
        },
    ]
    metrics = calculate_metrics(runs, {}, is_all_time=False)
    assert metrics["success_count"] == 1
    assert metrics["in_review_count"] == 1
    assert metrics["closed_count"] == 1
