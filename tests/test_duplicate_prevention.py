import pytest
import os
import sbm.config  # Import module to access _settings
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from sbm.cli import cli, _expand_theme_names
from sbm.utils.tracker import get_all_migrated_slugs

# Mock data
MOCK_FIREBASE_USERS = {
    "user1": {
        "runs": {
            "run1": {"slug": "site-a", "status": "success", "merged_at": "2026-01-10T10:00:00Z"},
            "run2": {"slug": "site-b", "status": "failed"},  # Should not be counted
        }
    },
    "user2": {
        "runs": {"run3": {"slug": "site-c", "status": "success", "pr_state": "MERGED"}}
    },
}


@patch("sbm.utils.tracker.is_firebase_available", return_value=True)
@patch("sbm.utils.firebase_sync.is_firebase_available", return_value=True)
@patch("sbm.utils.firebase_sync.get_firebase_db")
def test_get_all_migrated_slugs_success(mock_get_db, mock_sync_avail, mock_is_avail):
    mock_db = MagicMock()
    mock_ref = MagicMock()
    mock_ref.get.return_value = MOCK_FIREBASE_USERS
    mock_db.reference.return_value = mock_ref
    mock_get_db.return_value = mock_db

    slugs = get_all_migrated_slugs()

    assert slugs["site-a"] == "user1"
    assert slugs["site-c"] == "user2"
    assert "site-b" not in slugs  # Failed run
    assert len(slugs) == 2


@patch("sbm.utils.tracker.is_firebase_available", return_value=False)
def test_get_all_migrated_slugs_offline(mock_is_avail):
    slugs = get_all_migrated_slugs()
    assert slugs == {}


@patch("sbm.cli._expand_theme_names", return_value=["site-a", "site-new"])
@patch("sbm.utils.tracker.get_all_migrated_slugs")
@patch("sbm.cli.migrate_dealer_theme")
@patch("sbm.cli.get_console")
@patch("sbm.cli.InteractivePrompts")
def test_auto_duplicate_warn_skip(
    mock_prompts_class, mock_console, mock_migrate, mock_get_slugs, mock_expand
):
    """Test that CLI warns and skips validation when user confirms skip."""
    # Reset settings singleton
    sbm.config._settings = None

    # Configure mocks
    mock_get_slugs.return_value = {"site-a": "user1"}

    # Configure prompts
    mock_prompts_class.confirm_migration_start.return_value = True
    mock_prompts_class.confirm_duplicate_migration.return_value = True

    runner = CliRunner()
    # Ensure NON_INTERACTIVE is false
    result = runner.invoke(
        cli, ["auto", "site-a", "site-new"], env={"NON_INTERACTIVE": "false", "CI": ""}
    )

    # Verify duplicates removed means call count 1
    args, _ = mock_migrate.call_args
    assert args[0] == "site-new"
    assert mock_migrate.call_count == 1

    assert mock_prompts_class.confirm_duplicate_migration.called


@patch("sbm.cli._expand_theme_names", return_value=["site-a", "site-new"])
@patch("sbm.utils.tracker.get_all_migrated_slugs")
@patch("sbm.cli.migrate_dealer_theme")
@patch("sbm.cli.get_console")
@patch("sbm.cli.InteractivePrompts")
def test_auto_duplicate_warn_force(
    mock_prompts_class, mock_console, mock_migrate, mock_get_slugs, mock_expand
):
    """Test that CLI proceeds with duplicates when user says No to skip."""
    # Reset settings singleton
    sbm.config._settings = None

    mock_get_slugs.return_value = {"site-a": "user1"}

    # Configure prompts
    mock_prompts_class.confirm_migration_start.return_value = True
    mock_prompts_class.confirm_duplicate_migration.return_value = False  # No, do NOT skip

    runner = CliRunner()
    # Ensure NON_INTERACTIVE is false
    result = runner.invoke(
        cli, ["auto", "site-a", "site-new"], env={"NON_INTERACTIVE": "false", "CI": ""}
    )

    assert result.exit_code == 0
    # Verify call count 2 (both ran)
    assert mock_migrate.call_count == 2
    assert mock_prompts_class.confirm_duplicate_migration.called
