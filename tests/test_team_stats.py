import pytest
from unittest.mock import MagicMock
from sbm.utils.tracker import fetch_team_stats, get_migration_stats


@pytest.fixture
def mock_firebase(mocker):
    mocker.patch("sbm.utils.firebase_sync.is_firebase_available", return_value=True)
    mocker.patch("sbm.utils.tracker.is_firebase_available", return_value=True)
    settings = MagicMock()
    settings.firebase.is_admin_mode.return_value = True
    settings.firebase.database_url = "https://test.firebaseio.com"
    mocker.patch("sbm.utils.firebase_sync.get_settings", return_value=settings)
    mock_db = MagicMock()
    mocker.patch("sbm.utils.firebase_sync.get_firebase_db", return_value=mock_db)
    return mock_db


def test_fetch_team_stats_success(mocker, mock_firebase):
    """Test aggregation of team stats from mock Firebase data."""
    # Mock data structure: users/{user_id}/runs/{push_id}/...
    mock_data = {
        "user_a": {
            "migrations": ["site-1", "site-4"],
            "runs": {
                "push1": {
                    "status": "success",
                    "slug": "site-1",
                    "lines_migrated": 800,
                    "automation_seconds": 3600,
                    "merged_at": "2024-01-01T10:00:00+00:00",
                },
                "push2": {
                    "status": "success",
                    "slug": "site-2",
                    "lines_migrated": 1600,
                    "automation_seconds": 3600,
                    "pr_state": "OPEN",
                },
                "push3": {"status": "failed"},  # Should be ignored
            }
        },
        "user_b": {
            "migrations": ["site-3"],
            "runs": {
                "push4": {
                    "status": "success",
                    "slug": "site-3",
                    "lines_migrated": 800,
                    "automation_seconds": 3600,
                    "merged_at": "2024-01-02T10:00:00+00:00",
                }
            }
        },
    }

    mock_firebase.reference.return_value.get.return_value = mock_data

    stats = fetch_team_stats()

    assert stats is not None
    assert stats["total_users"] == 2
    assert stats["total_migrations"] == 2  # merged only: site-1, site-3
    assert stats["total_runs"] == 2
    # 800 + 800 = 1600 lines. 1600 / 800 = 2.0 hours
    assert stats["total_time_saved_h"] == 2.0
    # 3600*2 = 7200s = 2h
    assert stats["total_automation_time_h"] == 2.0

    # Check top contributors
    # user_a: 1 migration, user_b: 1 migration
    top = stats["top_contributors"]
    assert top[0][1] == 1
    assert top[1][1] == 1


def test_fetch_team_stats_offline_returns_none(mocker):
    """Test offline behavior."""
    mocker.patch("sbm.utils.tracker.is_firebase_available", return_value=False)
    assert fetch_team_stats() is None


def test_get_migration_stats_with_team_flag(mocker, mock_firebase):
    """Test get_migration_stats calls fetch_team_stats when team=True."""
    # Mock fetch_team_stats to return a dummy dict
    mocker.patch("sbm.utils.tracker.fetch_team_stats", return_value={"mock": "data"})
    mocker.patch("sbm.utils.tracker._get_user_id", return_value="test_user")

    result = get_migration_stats(team=True)

    assert result["source"] == "firebase"
    assert result["team_stats"] == {"mock": "data"}


def test_get_migration_stats_fallback(mocker):
    """Test fallback when team stats fetch fails."""
    mocker.patch("sbm.utils.tracker.fetch_team_stats", return_value=None)
    mocker.patch("sbm.utils.tracker.is_firebase_available", return_value=False)

    result = get_migration_stats(team=True)

    assert "error" in result


def test_get_migration_stats_team_since_filters(mocker):
    """Ensure team stats with since filter uses run data instead of cached team stats."""
    mocker.patch("sbm.utils.tracker.fetch_team_stats", side_effect=AssertionError("should not call"))
    mocker.patch("sbm.utils.tracker._get_user_id", return_value="test_user")

    run_recent = {
        "status": "success",
        "slug": "site-1",
        "lines_migrated": 800,
        "merged_at": "2026-01-16T10:00:00+00:00",
        "pr_state": "MERGED",
        "pr_author": "user_a",
    }
    run_old = {
        "status": "success",
        "slug": "site-2",
        "lines_migrated": 1200,
        "merged_at": "2025-12-01T10:00:00+00:00",
        "pr_state": "MERGED",
        "pr_author": "user_b",
    }

    mocker.patch("sbm.utils.tracker.get_global_reporting_data", return_value=([run_recent, run_old], {}))
    mocker.patch("sbm.utils.tracker.filter_runs", return_value=[run_recent])

    result = get_migration_stats(team=True, since="7")

    assert result["source"] == "firebase"
    assert result["team_stats"]["total_migrations"] == 1
