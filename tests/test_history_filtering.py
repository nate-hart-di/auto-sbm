"""
Unit tests for sbm.utils.tracker filter_runs function.

Tests cover:
- Period-based date filtering (day, week, month, N days)
- User filtering
- Limit/pagination
- PR state-aware date preference (merged_at/created_at/closed_at)
- Edge cases and error handling
"""

import pytest
from datetime import datetime, timedelta, timezone
from sbm.utils.tracker import filter_runs
from sbm.utils.tracker import _dedupe_runs_for_display


class TestFilterRunsByPeriod:
    """Test period-based date filtering."""

    @pytest.fixture
    def sample_runs(self):
        """Generate runs spanning the last 45 days."""
        now = datetime.now(timezone.utc)
        runs = []
        for i in range(45):
            ts = (now - timedelta(days=i)).isoformat()
            runs.append(
                {
                    "timestamp": ts,
                    "slug": f"dealer-{i}",
                    "status": "success",
                    "_user": "test-user" if i % 2 == 0 else "other-user",
                }
            )
        return runs

    def test_filter_last_day(self, sample_runs):
        """Filter runs from the last 24 hours."""
        result = filter_runs(sample_runs, since="1")
        # Should only include today's run (index 0)
        assert len(result) == 1
        assert result[0]["slug"] == "dealer-0"

    def test_filter_last_week(self, sample_runs):
        """Filter runs from the last 7 days."""
        result = filter_runs(sample_runs, since="7")
        # Should include runs 0-6 (7 days)
        assert len(result) == 7

    def test_filter_last_month(self, sample_runs):
        """Filter runs from the last 30 days."""
        result = filter_runs(sample_runs, since="30")
        assert len(result) == 30

    def test_filter_custom_days(self, sample_runs):
        """Filter runs from last N days."""
        result = filter_runs(sample_runs, since="14")
        assert len(result) == 14


class TestFilterRunsByDate:
    """Test ISO date string filtering (YYYY-MM-DD)."""

    def test_since_date_iso(self):
        """Filter runs since a specific ISO date."""
        runs = [
            {"timestamp": "2024-01-01T10:00:00+00:00", "slug": "a"},
            {"timestamp": "2024-01-15T10:00:00+00:00", "slug": "b"},
            {"timestamp": "2024-01-20T10:00:00+00:00", "slug": "c"},
        ]
        result = filter_runs(runs, since="2024-01-15")
        assert len(result) == 2
        slugs = {r["slug"] for r in result}
        assert slugs == {"b", "c"}

    def test_until_date_iso(self):
        """Filter runs until a specific ISO date."""
        runs = [
            {"timestamp": "2024-01-01T10:00:00+00:00", "slug": "a"},
            {"timestamp": "2024-01-15T10:00:00+00:00", "slug": "b"},
            {"timestamp": "2024-01-20T10:00:00+00:00", "slug": "c"},
        ]
        result = filter_runs(runs, until="2024-01-15")
        assert len(result) == 2
        slugs = {r["slug"] for r in result}
        assert slugs == {"a", "b"}

    def test_date_range(self):
        """Filter runs within a date range."""
        runs = [
            {"timestamp": "2024-01-01T10:00:00+00:00", "slug": "a"},
            {"timestamp": "2024-01-15T10:00:00+00:00", "slug": "b"},
            {"timestamp": "2024-01-20T10:00:00+00:00", "slug": "c"},
        ]
        result = filter_runs(runs, since="2024-01-10", until="2024-01-18")
        assert len(result) == 1
        assert result[0]["slug"] == "b"


class TestDatePreferenceByState:
    """Test that PR state-aware dates are preferred over timestamp for filtering."""

    def test_merged_at_used_for_filtering(self):
        """merged_at should be used for date filtering when available."""
        runs = [
            {
                "timestamp": "2024-01-01T10:00:00+00:00",  # Recorded date
                "merged_at": "2024-01-15T10:00:00+00:00",  # Actual merge date
                "slug": "backfill-run",
            },
        ]
        # Filter since Jan 10 - should include because merged_at is Jan 15
        result = filter_runs(runs, since="2024-01-10")
        assert len(result) == 1

        # Filter since Jan 20 - should exclude because merged_at is Jan 15
        result = filter_runs(runs, since="2024-01-20")
        assert len(result) == 0

    def test_fallback_to_timestamp(self):
        """Falls back to timestamp when merged_at is missing."""
        runs = [
            {"timestamp": "2024-01-15T10:00:00+00:00", "slug": "normal-run"},
        ]
        result = filter_runs(runs, since="2024-01-10")
        assert len(result) == 1

    def test_created_at_used_for_in_review(self):
        """created_at should be used for filtering open PRs."""
        runs = [
            {
                "timestamp": "2024-01-01T10:00:00+00:00",
                "created_at": "2024-01-12T10:00:00+00:00",
                "pr_state": "OPEN",
                "slug": "open-run",
            },
        ]
        result = filter_runs(runs, since="2024-01-10")
        assert len(result) == 1

    def test_closed_at_used_for_closed(self):
        """closed_at should be used for filtering closed PRs."""
        runs = [
            {
                "timestamp": "2024-01-01T10:00:00+00:00",
                "created_at": "2024-01-10T10:00:00+00:00",
                "closed_at": "2024-01-18T10:00:00+00:00",
                "pr_state": "CLOSED",
                "slug": "closed-run",
            },
        ]
        result = filter_runs(runs, since="2024-01-15")
        assert len(result) == 1

    def test_closed_state_without_closed_at(self):
        """PRs marked CLOSED without closed_at should still be closed."""
        runs = [
            {
                "timestamp": "2024-01-18T10:00:00+00:00",
                "created_at": "2024-01-10T10:00:00+00:00",
                "pr_state": "CLOSED",
                "slug": "legacy-closed",
            },
        ]
        result = filter_runs(runs, since="2024-01-15")
        assert len(result) == 1

    def test_sorting_uses_merged_at(self):
        """Runs should be sorted by state-aware dates (most recent first)."""
        runs = [
            {
                "timestamp": "2024-01-01T10:00:00+00:00",
                "merged_at": "2024-01-20T10:00:00+00:00",
                "slug": "a",
            },
            {
                "timestamp": "2024-01-15T10:00:00+00:00",
                "merged_at": "2024-01-10T10:00:00+00:00",
                "slug": "b",
            },
            {
                "timestamp": "2024-01-10T10:00:00+00:00",
                "created_at": "2024-01-19T10:00:00+00:00",
                "pr_state": "OPEN",
                "slug": "c",
            },
        ]
        result = filter_runs(runs)
        # Order should be: a (Jan 20), c (Jan 19), b (Jan 10)
        assert result[0]["slug"] == "a"


class TestFilterRunsByUser:
    """Test user filtering."""

    def test_filter_by_user(self):
        """Filter runs by _user field."""
        runs = [
            {"_user": "alice", "slug": "a"},
            {"_user": "bob", "slug": "b"},
            {"_user": "alice", "slug": "c"},
        ]
        result = filter_runs(runs, user="alice")
        assert len(result) == 2
        assert all(r["_user"] == "alice" for r in result)

    def test_filter_by_pr_author(self):
        """Filter runs by pr_author when _user is different or missing."""
        runs = [
            {"_user": "firebase-alice", "pr_author": "alice", "slug": "a"},
            {"_user": "firebase-bob", "pr_author": "bob", "slug": "b"},
            {"pr_author": "alice", "slug": "c"},
        ]
        result = filter_runs(runs, user="alice")
        assert len(result) == 2
        assert all(r.get("pr_author") == "alice" for r in result)

    def test_filter_by_user_case_insensitive(self):
        """User filter should be case insensitive."""
        runs = [
            {"_user": "Alice", "slug": "a"},
            {"_user": "BOB", "slug": "b"},
        ]
        result = filter_runs(runs, user="alice")
        assert len(result) == 1
        assert result[0]["slug"] == "a"

    def test_filter_by_partial_user(self):
        """User filter supports partial matching."""
        runs = [
            {"_user": "nate-hart-di", "slug": "a"},
            {"_user": "other-user", "slug": "b"},
        ]
        result = filter_runs(runs, user="nate")
        assert len(result) == 1


class TestFilterRunsLimit:
    """Test limit/pagination."""

    def test_limit_returns_most_recent(self):
        """Limit should return the N most recent runs."""
        runs = [
            {"timestamp": "2024-01-01T10:00:00+00:00", "slug": "oldest"},
            {"timestamp": "2024-01-02T10:00:00+00:00", "slug": "middle"},
            {"timestamp": "2024-01-03T10:00:00+00:00", "slug": "newest"},
        ]
        result = filter_runs(runs, limit=2)
        assert len(result) == 2
        assert result[0]["slug"] == "newest"
        assert result[1]["slug"] == "middle"

    def test_limit_with_filters(self):
        """Limit should be applied after other filters."""
        runs = [
            {"timestamp": "2024-01-01T10:00:00+00:00", "_user": "alice", "slug": "a1"},
            {"timestamp": "2024-01-02T10:00:00+00:00", "_user": "bob", "slug": "b1"},
            {"timestamp": "2024-01-03T10:00:00+00:00", "_user": "alice", "slug": "a2"},
            {"timestamp": "2024-01-04T10:00:00+00:00", "_user": "alice", "slug": "a3"},
        ]
        result = filter_runs(runs, user="alice", limit=2)
        assert len(result) == 2
        assert result[0]["slug"] == "a3"
        assert result[1]["slug"] == "a2"


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_runs(self):
        """Handle empty runs list."""
        result = filter_runs([], since="2024-01-01")
        assert result == []

    def test_invalid_date_format(self):
        """Invalid date format should be handled gracefully."""
        runs = [{"timestamp": "2024-01-01T10:00:00+00:00", "slug": "a"}]
        # Should log warning and ignore the filter
        result = filter_runs(runs, since="not-a-date")
        assert len(result) == 1

    def test_missing_timestamp(self):
        """Runs without timestamp should be skipped in date filtering."""
        runs = [
            {"timestamp": "2024-01-15T10:00:00+00:00", "slug": "a"},
            {"slug": "b"},  # No timestamp
        ]
        result = filter_runs(runs, since="2024-01-01")
        assert len(result) == 1
        assert result[0]["slug"] == "a"

    def test_malformed_timestamp(self):
        """Malformed timestamps should be skipped."""
        runs = [
            {"timestamp": "2024-01-15T10:00:00+00:00", "slug": "a"},
            {"timestamp": "not-a-timestamp", "slug": "b"},
        ]
        result = filter_runs(runs, since="2024-01-01")
        assert len(result) == 1

    def test_z_suffix_timestamps(self):
        """Handle timestamps with Z suffix."""
        runs = [
            {"timestamp": "2024-01-15T10:00:00Z", "slug": "a"},
        ]
        result = filter_runs(runs, since="2024-01-01")
        assert len(result) == 1

    def test_double_offset_timestamps(self):
        """Handle malformed double-offset timestamps like '...+00:00Z'."""
        runs = [
            {"timestamp": "2024-01-15T10:00:00+00:00Z", "slug": "a"},
        ]
        result = filter_runs(runs, since="2024-01-01")
        # Should handle gracefully (either include or skip, not crash)
        assert isinstance(result, list)

    def test_no_filters_returns_all(self):
        """No filters should return all runs."""
        runs = [{"slug": "a"}, {"slug": "b"}]
        result = filter_runs(runs)
        assert len(result) == 2


class TestDedupeRunsForDisplay:
    def test_dedupe_keeps_most_recent_per_slug(self):
        runs = [
            {
                "slug": "dup-slug",
                "status": "success",
                "merged_at": "2026-01-01T10:00:00+00:00",
            },
            {
                "slug": "dup-slug",
                "status": "success",
                "merged_at": "2026-01-03T10:00:00+00:00",
            },
            {
                "slug": "unique",
                "status": "success",
                "merged_at": "2026-01-02T10:00:00+00:00",
            },
        ]
        result = _dedupe_runs_for_display(runs)
        slugs = [r["slug"] for r in result if r.get("slug")]
        assert slugs.count("dup-slug") == 1
        assert "unique" in slugs
