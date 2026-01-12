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
            "runs": {
                "push1": {
                    "status": "success",
                    "slug": "site-1",
                    "lines_migrated": 800,
                    "automation_seconds": 3600,
                },
                "push2": {
                    "status": "success",
                    "slug": "site-2",
                    "lines_migrated": 1600,
                    "automation_seconds": 3600,
                },
                "push3": {"status": "failed"},  # Should be ignored
            }
        },
        "user_b": {
            "runs": {
                "push4": {
                    "status": "success",
                    "slug": "site-3",
                    "lines_migrated": 800,
                    "automation_seconds": 3600,
                }
            }
        },
    }

    mock_firebase.reference.return_value.get.return_value = mock_data

    stats = fetch_team_stats()

    assert stats is not None
    assert stats["total_users"] == 2
    assert stats["total_migrations"] == 3  # site-1, site-2, site-3
    assert stats["total_runs"] == 3
    # 800 + 1600 + 800 = 3200 lines. 3200 / 800 = 4.0 hours
    assert stats["total_time_saved_h"] == 4.0
    # 3600*3 = 10800s = 3h
    assert stats["total_automation_time_h"] == 3.0

    # Check top contributors
    # user_a: 2 runs, user_b: 1 run
    top = stats["top_contributors"]
    assert top[0][0] == "user_a"
    assert top[0][1] == 2
    assert top[1][0] == "user_b"
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
