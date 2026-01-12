import json
import sys
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

# Add scripts directory to path to allow importing the script module
PROJECT_ROOT = Path(__file__).parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts" / "stats"
sys.path.append(str(SCRIPTS_DIR))

# Import the module under test
# We use a try-except block here because tests might run before the script exists
try:
    import migrate_to_firebase
except ImportError:
    migrate_to_firebase = None


@pytest.fixture
def mock_settings():
    with patch("migrate_to_firebase.AutoSBMSettings") as MockSettings:
        settings = MockSettings.return_value
        settings.firebase.is_configured.return_value = True
        yield settings


def test_module_import():
    """Fail if module cannot be imported (meaning it hasn't been created yet)."""
    assert migrate_to_firebase is not None, "migrate_to_firebase module not found"


@patch("migrate_to_firebase.Path.exists")
@patch("migrate_to_firebase.Path.home")
@patch("builtins.open", new_callable=mock_open)
def test_load_local_history(mock_file, mock_home, mock_exists):
    """Test loading history from JSON file."""
    mock_home.return_value = Path("/mock/home")
    mock_exists.return_value = True

    data = {"runs": [{"timestamp": "t1", "slug": "s1"}, {"timestamp": "t2", "slug": "s2"}]}
    mock_file.return_value.read.return_value = json.dumps(data)

    history = migrate_to_firebase.load_local_history()

    assert len(history) == 2, f"Expected 2 items, got {len(history)}"
    assert history[0]["slug"] == "s1"
    # Note: Path joining in the script will result in specific path behavior,
    # relying on the mocked home path.
    mock_file.assert_called_with(Path("/mock/home/.sbm_migrations.json"), "r")


@patch("migrate_to_firebase.is_firebase_available")
@patch("migrate_to_firebase.push_run_to_firebase")
@patch("migrate_to_firebase.get_existing_signatures")
@patch("migrate_to_firebase.load_local_history")
@patch("migrate_to_firebase.track_progress")
def test_migrate_main_logic(
    mock_track, mock_load, mock_existing, mock_push, mock_firebase_avail
):
    """Test the main migration loop logic."""
    # Setup track_progress to just return the sequence
    mock_track.side_effect = lambda x, **kwargs: x

    # Setup data
    mock_load.return_value = [
        {"timestamp": "t1", "slug": "slug1"},
        {"timestamp": "t2", "slug": "slug2"},
    ]
    mock_firebase_avail.return_value = True
    mock_existing.return_value = {"t1_slug1"}

    # Run migration
    stats = migrate_to_firebase.perform_migration("user1")

    # Verify
    assert stats["total"] == 2
    assert stats["skipped"] == 1
    assert stats["migrated"] == 1

    mock_push.assert_called_once()
    args = mock_push.call_args[0]
    assert args[0] == "user1"
    assert args[1]["slug"] == "slug2"
