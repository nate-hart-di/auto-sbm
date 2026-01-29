"""
Tests for shared run helper functions.

These tests ensure that the shared `is_complete_run()` helper correctly
identifies completed runs across all use cases.
"""

import pytest

from sbm.utils.run_helpers import is_complete_run


class TestIsCompleteRun:
    """Test cases for the is_complete_run() helper function."""

    def test_is_complete_run_with_merged_at(self):
        """A successful run with merged_at should be complete."""
        run = {
            "status": "success",
            "merged_at": "2026-01-15T10:30:00Z",
            "slug": "lexusoffortmyers"
        }
        assert is_complete_run(run) is True

    def test_is_complete_run_with_pr_state_merged(self):
        """A successful run with pr_state=MERGED should be complete."""
        run = {
            "status": "success",
            "pr_state": "MERGED",
            "slug": "lexusoffortmyers"
        }
        assert is_complete_run(run) is True

    def test_is_complete_run_superseded(self):
        """A superseded run should NOT be complete."""
        run = {
            "status": "success",
            "merged_at": "2026-01-15T10:30:00Z",
            "superseded": True,
            "slug": "lexusoffortmyers"
        }
        assert is_complete_run(run) is False

    def test_is_complete_run_failed_status(self):
        """A failed run should NOT be complete."""
        run = {
            "status": "failed",
            "merged_at": "2026-01-15T10:30:00Z",
            "slug": "lexusoffortmyers"
        }
        assert is_complete_run(run) is False

    def test_is_complete_run_open_pr(self):
        """An open PR should NOT be complete."""
        run = {
            "status": "success",
            "pr_state": "OPEN",
            "created_at": "2026-01-15T10:00:00Z",
            "slug": "lexusoffortmyers"
        }
        assert is_complete_run(run) is False

    def test_is_complete_run_closed_pr(self):
        """A closed PR (not merged) should NOT be complete."""
        run = {
            "status": "success",
            "pr_state": "CLOSED",
            "closed_at": "2026-01-15T10:30:00Z",
            "slug": "lexusoffortmyers"
        }
        assert is_complete_run(run) is False

    def test_is_complete_run_no_pr_info(self):
        """A run without PR info should NOT be complete."""
        run = {
            "status": "success",
            "slug": "lexusoffortmyers"
        }
        assert is_complete_run(run) is False

    def test_is_complete_run_case_insensitive_pr_state(self):
        """pr_state should be case-insensitive."""
        run = {
            "status": "success",
            "pr_state": "merged",  # lowercase
            "slug": "lexusoffortmyers"
        }
        assert is_complete_run(run) is True

    def test_is_complete_run_invalid_status(self):
        """A run with invalid status should NOT be complete."""
        run = {
            "status": "invalid",
            "merged_at": "2026-01-15T10:30:00Z",
            "slug": "lexusoffortmyers"
        }
        assert is_complete_run(run) is False

    def test_is_complete_run_empty_dict(self):
        """An empty run dict should NOT be complete."""
        run = {}
        assert is_complete_run(run) is False
