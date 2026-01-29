"""
Tests for remigration functionality in tracker.py.

These tests ensure that mark_runs_for_remigration() correctly adds superseded
flags while preserving GitHub PR state truth.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from sbm.utils.tracker import mark_runs_for_remigration


# Mock Firebase data structure
MOCK_FIREBASE_DATA = {
    "user1": {
        "runs": {
            "lexusoffortmyers_2026-01-15_10-00-00": {
                "slug": "lexusoffortmyers",
                "status": "success",
                "pr_state": "MERGED",
                "merged_at": "2026-01-15T10:30:00Z",
                "pr_url": "https://github.com/dealerinspire/themes/pull/1234",
                "timestamp": "2026-01-15T10:00:00Z"
            },
            "toyotaoffortmyers_2026-01-16_11-00-00": {
                "slug": "toyotaoffortmyers",
                "status": "success",
                "pr_state": "MERGED",
                "merged_at": "2026-01-16T11:30:00Z",
                "pr_url": "https://github.com/dealerinspire/themes/pull/1235",
                "timestamp": "2026-01-16T11:00:00Z"
            },
            "hondaoffortmyers_2026-01-17_12-00-00": {
                "slug": "hondaoffortmyers",
                "status": "failed",
                "timestamp": "2026-01-17T12:00:00Z"
            },
            "nissanoffortmyers_2026-01-18_13-00-00": {
                "slug": "nissanoffortmyers",
                "status": "success",
                "pr_state": "OPEN",
                "created_at": "2026-01-18T13:00:00Z",
                "timestamp": "2026-01-18T13:00:00Z"
            }
        }
    },
    "user2": {
        "runs": {
            "lexusoffortmyers_2026-01-20_14-00-00": {
                "slug": "lexusoffortmyers",
                "status": "success",
                "pr_state": "MERGED",
                "merged_at": "2026-01-20T14:30:00Z",  # More recent than user1's
                "pr_url": "https://github.com/dealerinspire/themes/pull/1236",
                "timestamp": "2026-01-20T14:00:00Z"
            }
        }
    }
}


class TestMarkRunsForRemigration:
    """Test cases for mark_runs_for_remigration()."""

    @patch("sbm.utils.tracker.is_firebase_available")
    def test_mark_runs_without_firebase(self, mock_firebase_available):
        """Should return not_found counts when Firebase is unavailable."""
        mock_firebase_available.return_value = False

        result = mark_runs_for_remigration(["lexusoffortmyers", "toyotaoffortmyers"])

        assert result == {"updated": 0, "failed": 0, "not_found": 2}

    @patch("sbm.utils.tracker.is_firebase_available")
    @patch("sbm.utils.tracker.get_settings")
    @patch("sbm.utils.tracker.FirebaseSync")
    @patch("sbm.utils.firebase_sync.get_firebase_db")
    def test_mark_runs_adds_superseded_flag(
        self, mock_get_db, mock_firebase_sync_class, mock_get_settings, mock_firebase_available
    ):
        """Should add superseded flag without changing pr_state."""
        mock_firebase_available.return_value = True

        # Mock admin mode
        mock_settings = MagicMock()
        mock_settings.firebase.is_admin_mode.return_value = True
        mock_get_settings.return_value = mock_settings

        # Mock Firebase database
        mock_db = MagicMock()
        mock_ref = MagicMock()
        mock_ref.get.return_value = MOCK_FIREBASE_DATA
        mock_db.reference.return_value = mock_ref
        mock_get_db.return_value = mock_db

        # Mock FirebaseSync
        mock_sync = MagicMock()
        mock_sync.update_run.return_value = True
        mock_firebase_sync_class.return_value = mock_sync

        result = mark_runs_for_remigration(["lexusoffortmyers"])

        # Should have updated 1 run (the most recent one for this slug)
        assert result == {"updated": 1, "failed": 0, "not_found": 0}

        # Verify update_run was called with superseded fields
        mock_sync.update_run.assert_called_once()
        call_args = mock_sync.update_run.call_args
        updates = call_args.kwargs["updates"]

        assert "superseded" in updates
        assert updates["superseded"] is True
        assert "superseded_at" in updates
        assert "superseded_by" in updates

        # CRITICAL: pr_state should NOT be in updates
        assert "pr_state" not in updates

    @patch("sbm.utils.tracker.is_firebase_available")
    @patch("sbm.utils.tracker.get_settings")
    @patch("sbm.utils.tracker.FirebaseSync")
    @patch("sbm.utils.firebase_sync.get_firebase_db")
    def test_mark_runs_finds_most_recent(
        self, mock_get_db, mock_firebase_sync_class, mock_get_settings, mock_firebase_available
    ):
        """Should mark the most recent merged run for a slug."""
        mock_firebase_available.return_value = True

        mock_settings = MagicMock()
        mock_settings.firebase.is_admin_mode.return_value = True
        mock_get_settings.return_value = mock_settings

        mock_db = MagicMock()
        mock_ref = MagicMock()
        mock_ref.get.return_value = MOCK_FIREBASE_DATA
        mock_db.reference.return_value = mock_ref
        mock_get_db.return_value = mock_db

        mock_sync = MagicMock()
        mock_sync.update_run.return_value = True
        mock_firebase_sync_class.return_value = mock_sync

        result = mark_runs_for_remigration(["lexusoffortmyers"])

        assert result == {"updated": 1, "failed": 0, "not_found": 0}

        # Verify it updated user2's run (more recent than user1's)
        call_args = mock_sync.update_run.call_args
        assert call_args.kwargs["user_id"] == "user2"
        assert call_args.kwargs["run_key"] == "lexusoffortmyers_2026-01-20_14-00-00"

    @patch("sbm.utils.tracker.is_firebase_available")
    @patch("sbm.utils.tracker.get_settings")
    @patch("sbm.utils.tracker.FirebaseSync")
    @patch("sbm.utils.firebase_sync.get_firebase_db")
    def test_mark_runs_handles_not_found(
        self, mock_get_db, mock_firebase_sync_class, mock_get_settings, mock_firebase_available
    ):
        """Should return not_found count for slugs without completed runs."""
        mock_firebase_available.return_value = True

        mock_settings = MagicMock()
        mock_settings.firebase.is_admin_mode.return_value = True
        mock_get_settings.return_value = mock_settings

        mock_db = MagicMock()
        mock_ref = MagicMock()
        mock_ref.get.return_value = MOCK_FIREBASE_DATA
        mock_db.reference.return_value = mock_ref
        mock_get_db.return_value = mock_db

        mock_sync = MagicMock()
        mock_firebase_sync_class.return_value = mock_sync

        # hondaoffortmyers has a failed run (not completed)
        # nonexistent slug doesn't exist
        result = mark_runs_for_remigration(["hondaoffortmyers", "nonexistent"])

        assert result == {"updated": 0, "failed": 0, "not_found": 2}

    @patch("sbm.utils.tracker.is_firebase_available")
    @patch("sbm.utils.tracker.get_settings")
    @patch("sbm.utils.tracker.FirebaseSync")
    @patch("sbm.utils.firebase_sync.get_firebase_db")
    def test_mark_runs_ignores_open_prs(
        self, mock_get_db, mock_firebase_sync_class, mock_get_settings, mock_firebase_available
    ):
        """Should not mark runs with open PRs (not completed)."""
        mock_firebase_available.return_value = True

        mock_settings = MagicMock()
        mock_settings.firebase.is_admin_mode.return_value = True
        mock_get_settings.return_value = mock_settings

        mock_db = MagicMock()
        mock_ref = MagicMock()
        mock_ref.get.return_value = MOCK_FIREBASE_DATA
        mock_db.reference.return_value = mock_ref
        mock_get_db.return_value = mock_db

        mock_sync = MagicMock()
        mock_firebase_sync_class.return_value = mock_sync

        # nissanoffortmyers has an open PR (not merged)
        result = mark_runs_for_remigration(["nissanoffortmyers"])

        assert result == {"updated": 0, "failed": 0, "not_found": 1}

    @patch("sbm.utils.tracker.is_firebase_available")
    @patch("sbm.utils.tracker.get_settings")
    @patch("sbm.utils.tracker.FirebaseSync")
    @patch("sbm.utils.firebase_sync.get_firebase_db")
    def test_mark_runs_handles_firebase_failure(
        self, mock_get_db, mock_firebase_sync_class, mock_get_settings, mock_firebase_available
    ):
        """Should handle Firebase update failures gracefully."""
        mock_firebase_available.return_value = True

        mock_settings = MagicMock()
        mock_settings.firebase.is_admin_mode.return_value = True
        mock_get_settings.return_value = mock_settings

        mock_db = MagicMock()
        mock_ref = MagicMock()
        mock_ref.get.return_value = MOCK_FIREBASE_DATA
        mock_db.reference.return_value = mock_ref
        mock_get_db.return_value = mock_db

        # Mock update_run to fail
        mock_sync = MagicMock()
        mock_sync.update_run.return_value = False
        mock_firebase_sync_class.return_value = mock_sync

        result = mark_runs_for_remigration(["lexusoffortmyers"])

        assert result == {"updated": 0, "failed": 1, "not_found": 0}

    @patch("sbm.utils.tracker.is_firebase_available")
    @patch("sbm.utils.tracker.get_settings")
    @patch("sbm.utils.tracker.logger")
    def test_mark_runs_performance_warning(
        self, mock_logger, mock_get_settings, mock_firebase_available
    ):
        """Should log warning for large batches (>10 slugs)."""
        mock_firebase_available.return_value = True

        mock_settings = MagicMock()
        mock_settings.firebase.is_admin_mode.return_value = False
        mock_get_settings.return_value = mock_settings

        # Mock user mode authentication failure to exit early
        with patch("sbm.utils.tracker.get_user_mode_identity", return_value=None):
            large_batch = [f"slug{i}" for i in range(15)]
            result = mark_runs_for_remigration(large_batch)

            # Should have logged performance warning
            assert any("may be slow" in str(call) for call in mock_logger.warning.call_args_list)

    @patch("sbm.utils.tracker.is_firebase_available")
    @patch("sbm.utils.tracker.get_settings")
    @patch("sbm.utils.tracker.FirebaseSync")
    def test_mark_runs_user_mode_rest_api(
        self, mock_firebase_sync_class, mock_get_settings, mock_firebase_available
    ):
        """Should work in user mode with REST API."""
        mock_firebase_available.return_value = True

        # Mock user mode
        mock_settings = MagicMock()
        mock_settings.firebase.is_admin_mode.return_value = False
        mock_settings.firebase.database_url = "https://test.firebaseio.com"
        mock_get_settings.return_value = mock_settings

        mock_sync = MagicMock()
        mock_sync.update_run.return_value = True
        mock_firebase_sync_class.return_value = mock_sync

        with patch("sbm.utils.tracker.get_user_mode_identity") as mock_identity, \
             patch("requests.get") as mock_requests_get:

            mock_identity.return_value = ("user@example.com", "test_token")

            # Mock REST API response
            mock_response = MagicMock()
            mock_response.ok = True
            mock_response.json.return_value = MOCK_FIREBASE_DATA
            mock_requests_get.return_value = mock_response

            result = mark_runs_for_remigration(["toyotaoffortmyers"])

            assert result == {"updated": 1, "failed": 0, "not_found": 0}

            # Verify REST API was called
            mock_requests_get.assert_called_once()
