import pytest
from unittest.mock import MagicMock, patch
from sbm.core.migration import (
    migrate_dealer_theme,
    run_post_migration_workflow,
    MigrationResult,
    MigrationStep,
)


@patch("sbm.core.migration.git_operations")
@patch("sbm.core.migration.run_just_start")
@patch("sbm.core.migration._perform_core_migration")
@patch("sbm.core.migration._create_automation_snapshots")
@patch("sbm.core.migration.run_post_migration_workflow")
@patch("sbm.core.migration.get_console")
def test_migrate_dealer_theme_returns_migration_result(
    mock_console,
    mock_run_post_migration,
    mock_create_snapshots,
    mock_perform_core,
    mock_run_just,
    mock_git_ops,
):
    """Test that migrate_dealer_theme returns MigrationResult dataclass."""
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

    # Verify MigrationResult object structure
    assert isinstance(result, MigrationResult)
    assert result.status == "success"
    assert result.slug == "test-slug"
    assert result.pr_url == "http://github.com/pr/1"
    assert result.salesforce_message == "Done"
    assert result.branch_name == "test-branch"
    assert result.elapsed_time > 0


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
    # _verify_scss_compilation_with_docker returns (success, errors) when capture_errors=True
    mock_verify.return_value = (True, [])
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


@patch("sbm.core.migration.git_operations")
@patch("sbm.core.migration.run_just_start")
@patch("sbm.core.migration._perform_core_migration")
@patch("sbm.core.migration._create_automation_snapshots")
@patch("sbm.core.migration.run_post_migration_workflow")
@patch("sbm.core.migration.get_console")
def test_migrate_dealer_theme_git_failure_tracking(
    mock_console,
    mock_run_post_migration,
    mock_create_snapshots,
    mock_perform_core,
    mock_run_just,
    mock_git_ops,
):
    """Test that Git setup failure is tracked in MigrationResult."""
    # Git operations fail
    mock_git_ops.return_value = (False, None)

    # Execute
    result = migrate_dealer_theme(slug="test-slug", skip_just=False, force_reset=True)

    # Verify failure tracking
    assert isinstance(result, MigrationResult)
    assert result.status == "failed"
    assert result.step_failed == MigrationStep.GIT_SETUP
    assert "Git branch creation or checkout failed" in result.error_message
    assert "test-slug" in result.error_message
    assert result.slug == "test-slug"


@patch("sbm.core.migration.git_operations")
@patch("sbm.core.migration.run_just_start")
@patch("sbm.core.migration._perform_core_migration")
@patch("sbm.core.migration._create_automation_snapshots")
@patch("sbm.core.migration.run_post_migration_workflow")
@patch("sbm.core.migration.get_console")
def test_migrate_dealer_theme_docker_failure_tracking(
    mock_console,
    mock_run_post_migration,
    mock_create_snapshots,
    mock_perform_core,
    mock_run_just,
    mock_git_ops,
):
    """Test that Docker startup failure is tracked in MigrationResult."""
    # Git succeeds but Docker fails
    mock_git_ops.return_value = (True, "test-branch")
    mock_run_just.return_value = False

    # Execute
    result = migrate_dealer_theme(slug="test-slug", skip_just=False, force_reset=True)

    # Verify failure tracking
    assert isinstance(result, MigrationResult)
    assert result.status == "failed"
    assert result.step_failed == MigrationStep.DOCKER_STARTUP
    assert "Docker container startup failed" in result.error_message
    assert "test-slug" in result.error_message
    assert result.branch_name == "test-branch"


@patch("sbm.core.migration.git_operations")
@patch("sbm.core.migration.run_just_start")
@patch("sbm.core.migration._perform_core_migration")
@patch("sbm.core.migration._create_automation_snapshots")
@patch("sbm.core.migration.run_post_migration_workflow")
@patch("sbm.core.migration.get_console")
def test_migrate_dealer_theme_core_migration_failure_tracking(
    mock_console,
    mock_run_post_migration,
    mock_create_snapshots,
    mock_perform_core,
    mock_run_just,
    mock_git_ops,
):
    """Test that core migration failure is tracked in MigrationResult."""
    # Git and Docker succeed but core migration fails
    mock_git_ops.return_value = (True, "test-branch")
    mock_run_just.return_value = True
    mock_perform_core.return_value = (False, 0)

    # Execute
    result = migrate_dealer_theme(slug="test-slug", skip_just=False, force_reset=True)

    # Verify failure tracking
    assert isinstance(result, MigrationResult)
    assert result.status == "failed"
    assert result.step_failed == MigrationStep.CORE_MIGRATION
    assert "Core migration failed" in result.error_message
    assert "test-slug" in result.error_message


@patch("sbm.core.migration.git_operations")
@patch("sbm.core.migration.run_just_start")
@patch("sbm.core.migration._perform_core_migration")
@patch("sbm.core.migration._create_automation_snapshots")
@patch("sbm.core.migration.run_post_migration_workflow")
@patch("sbm.core.migration.get_console")
def test_migrate_dealer_theme_exception_tracking(
    mock_console,
    mock_run_post_migration,
    mock_create_snapshots,
    mock_perform_core,
    mock_run_just,
    mock_git_ops,
):
    """Test that exceptions are tracked with stack traces."""
    # Git operations raise an exception
    mock_git_ops.side_effect = ValueError("Test exception")

    # Execute
    result = migrate_dealer_theme(slug="test-slug", skip_just=False, force_reset=True)

    # Verify exception tracking
    assert isinstance(result, MigrationResult)
    assert result.status == "failed"
    assert result.step_failed == MigrationStep.GIT_SETUP
    assert "Test exception" in result.error_message
    assert result.stack_trace is not None
    assert "ValueError" in result.stack_trace


@patch("sbm.core.migration.reprocess_manual_changes")
@patch("sbm.core.migration._verify_scss_compilation_with_docker")
@patch("sbm.core.migration._cleanup_snapshot_files")
@patch("sbm.core.migration.commit_changes")
@patch("sbm.core.migration.push_changes")
@patch("sbm.core.migration.git_create_pr")
def test_scss_error_capture(
    mock_create_pr,
    mock_push,
    mock_commit,
    mock_cleanup,
    mock_verify,
    mock_reprocess,
):
    """Test that SCSS compilation errors are captured in MigrationResult."""
    # Setup: SCSS verification fails with errors
    mock_reprocess.return_value = True
    mock_verify.return_value = (False, ["Error: Invalid variable $test", "Error: Missing semicolon"])

    # Create a MigrationResult to pass to the function
    result = MigrationResult(slug="test-slug")

    # Execute
    output = run_post_migration_workflow(
        slug="test-slug", branch_name="test-branch", create_pr=True, result=result
    )

    # Verify SCSS errors were captured
    assert result.status == "failed"
    assert result.step_failed == MigrationStep.SCSS_VERIFICATION
    assert len(result.scss_errors) == 2
    assert "Invalid variable $test" in result.scss_errors[0]
    assert "Missing semicolon" in result.scss_errors[1]


@patch("sbm.core.migration.git_operations")
@patch("sbm.core.migration.run_just_start")
@patch("sbm.core.migration._perform_core_migration")
@patch("sbm.core.migration._create_automation_snapshots")
@patch("sbm.core.migration.run_post_migration_workflow")
@patch("sbm.core.migration.get_console")
def test_migrate_dealer_theme_tracks_lines_migrated(
    mock_console,
    mock_run_post_migration,
    mock_create_snapshots,
    mock_perform_core,
    mock_run_just,
    mock_git_ops,
):
    """Test that lines_migrated is properly tracked in MigrationResult."""
    # Setup mocks
    mock_git_ops.return_value = (True, "test-branch")
    mock_run_just.return_value = True

    # Core migration returns success and 850 lines migrated
    mock_perform_core.return_value = (True, 850)

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

    # Verify MigrationResult has lines_migrated properly set
    assert isinstance(result, MigrationResult)
    assert result.status == "success"
    assert result.lines_migrated == 850, f"Expected 850 lines migrated, got {result.lines_migrated}"

    # Verify _perform_core_migration was called (proves integration path exists)
    mock_perform_core.assert_called_once()


def test_lines_migrated_assignment_on_failure():
    """Test that lines_migrated is set even on migration failure (for debugging)."""
    with patch("sbm.core.migration.git_operations") as mock_git_ops, \
         patch("sbm.core.migration.run_just_start") as mock_run_just, \
         patch("sbm.core.migration._perform_core_migration") as mock_perform_core, \
         patch("sbm.core.migration.get_console"):

        # Setup: Git and Docker succeed
        mock_git_ops.return_value = (True, "test-branch")
        mock_run_just.return_value = True

        # Core migration fails but returns 450 lines processed
        mock_perform_core.return_value = (False, 450)

        # Execute
        result = migrate_dealer_theme(slug="test-slug", skip_just=False, force_reset=True)

        # Verify: Failed migration still has lines_migrated for debugging
        assert result.status == "failed"
        assert result.step_failed == MigrationStep.CORE_MIGRATION
        assert result.lines_migrated == 450, "Failed migrations should track partial progress for debugging"


@patch("sbm.cli.REPO_ROOT", new_callable=lambda: MagicMock())
def test_migration_report_generation(mock_repo_root):
    """Test that migration report is generated with correct format."""
    from sbm.cli import _generate_migration_report
    from pathlib import Path
    import tempfile

    # Create temp directory for reports
    with tempfile.TemporaryDirectory() as tmpdir:
        mock_repo_root.__truediv__ = lambda self, other: Path(tmpdir) / other

        # Create test results
        results = [
            MigrationResult(
                slug="success-slug",
                status="success",
                pr_url="https://github.com/pr/123",
                salesforce_message="Migration completed successfully",
                branch_name="feat/success",
                elapsed_time=45.5,
            ),
            MigrationResult(
                slug="failed-slug",
                status="failed",
                step_failed=MigrationStep.SCSS_VERIFICATION,
                error_message="SCSS compilation failed",
                branch_name="feat/failed",
                elapsed_time=30.2,
            ),
        ]

        # Generate report
        _generate_migration_report(results)

        # Verify report file exists and has correct content
        reports_dir = Path(tmpdir) / "reports"
        assert reports_dir.exists()

        report_files = list(reports_dir.glob("migration_report_*.txt"))
        assert len(report_files) == 1

        report_content = report_files[0].read_text()

        # Verify summary section
        assert "SUMMARY" in report_content
        assert "Total Slugs Processed: 2" in report_content
        assert "Successful: 1" in report_content
        assert "Failed: 1" in report_content

        # Verify Salesforce messages section
        assert "SALESFORCE MESSAGES" in report_content
        assert "success-slug" in report_content
        assert "https://github.com/pr/123" in report_content
        assert "Migration completed successfully" in report_content

        # Verify detailed results
        assert "DETAILED RESULTS" in report_content
        assert "failed-slug" in report_content
        assert "Failed At Step: scss_verification" in report_content
        assert "SCSS compilation failed" in report_content
