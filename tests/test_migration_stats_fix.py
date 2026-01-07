import pytest
from unittest.mock import MagicMock, patch
from sbm.core.migration import migrate_dealer_theme, run_post_migration_workflow


@patch("sbm.core.migration.git_operations")
@patch("sbm.core.migration.run_just_start")
@patch("sbm.core.migration._perform_core_migration")
@patch("sbm.core.migration._create_automation_snapshots")
@patch("sbm.core.migration.run_post_migration_workflow")
@patch("sbm.core.migration.get_console")
def test_migrate_dealer_theme_propagates_lines_migrated(
    mock_console,
    mock_run_post_migration,
    mock_create_snapshots,
    mock_perform_core,
    mock_run_just,
    mock_git_ops,
):
    """Test that migrate_dealer_theme returns lines_migrated from core migration."""
    # Setup mocks
    mock_git_ops.return_value = (True, "test-branch")
    mock_run_just.return_value = True

    # Core migration returns success and 100 lines migrated
    mock_perform_core.return_value = (True, 100)

    # Post migration returns a dict success
    mock_run_post_migration.return_value = {
        "success": True,
        "pr_url": "http://github.com/pr/1",
        "salesforce_message": "Done",
    }

    # Execute
    result = migrate_dealer_theme(
        slug="test-slug", skip_just=False, force_reset=True, create_pr=False, skip_git=False
    )

    # Verify
    assert isinstance(result, dict)
    assert result["success"] is True
    assert result["lines_migrated"] == 100
    assert result["pr_url"] == "http://github.com/pr/1"


@patch("sbm.core.migration.reprocess_manual_changes")
@patch("sbm.core.migration._verify_scss_compilation_with_docker")
@patch("sbm.core.migration._cleanup_snapshot_files")
@patch("sbm.core.migration.commit_changes")
@patch("sbm.core.migration.push_changes")
@patch("sbm.core.migration.git_create_pr")
def test_run_post_migration_workflow_returns_dict(
    mock_create_pr,
    mock_push,
    mock_commit,
    mock_cleanup,
    mock_verify,
    mock_reprocess,
):
    """Test standard success path returns expected dict structure."""
    # Setup success path
    mock_reprocess.return_value = True
    mock_verify.return_value = True
    mock_commit.return_value = True
    mock_push.return_value = True

    # Mock create_pr returning dict (new behavior)
    mock_create_pr.return_value = {
        "success": True,
        "pr_url": "http://test.url",
        "salesforce_message": "msg",
    }

    result = run_post_migration_workflow(
        slug="test-slug", branch_name="test-branch", create_pr=True
    )

    assert isinstance(result, dict)
    assert result["success"] is True
    assert result["pr_url"] == "http://test.url"


def test_run_post_migration_workflow_failure_returns_dict():
    """Test failure path returns dict with success=False."""
    with patch("sbm.core.migration.reprocess_manual_changes") as mock_reprocess:
        mock_reprocess.return_value = False

        result = run_post_migration_workflow(slug="test-slug", branch_name="test-branch")

        assert isinstance(result, dict)
        assert result["success"] is False
