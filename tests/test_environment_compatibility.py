"""
Test Environment Compatibility for Migration System

This test suite validates that the migration system works correctly across
different environment configurations, including clean venvs and global command isolation.
"""
import os
import tempfile
from pathlib import Path

import pytest

from sbm.config import AutoSBMSettings, get_config
from sbm.core.validation import CompilationStatus, CompilationValidator


class TestEnvironmentCompatibility:
    """Test cross-environment compatibility."""

    def test_clean_environment_initialization(self):
        """Test that the system initializes in a clean environment."""
        # Clear environment variables that could interfere
        env_backup = {}
        test_vars = [
            "AUTOSBM_THEMES_DIRECTORY",
            "AUTOSBM_BACKUP_ENABLED",
            "AUTOSBM_RICH_UI_ENABLED",
            "WP_DEBUG",
            "WP_DEBUG_LOG",
        ]

        for var in test_vars:
            if var in os.environ:
                env_backup[var] = os.environ[var]
                del os.environ[var]

        try:
            # Test clean initialization
            settings = AutoSBMSettings()
            assert settings.themes_directory == "themes"
            assert settings.backup_enabled is True
            assert settings.rich_ui_enabled is True

            # Test that WordPress variables are ignored
            os.environ["WP_DEBUG"] = "true"
            os.environ["WP_DEBUG_LOG"] = "true"
            settings_with_wp = AutoSBMSettings()
            # Should still work without being affected by WP vars
            assert settings_with_wp.themes_directory == "themes"

        finally:
            # Restore environment
            for var, value in env_backup.items():
                os.environ[var] = value
            for var in ["WP_DEBUG", "WP_DEBUG_LOG"]:
                os.environ.pop(var, None)

    def test_di_websites_platform_compatibility(self):
        """Test compatibility with di-websites-platform environment."""
        # Simulate di-websites-platform environment variables
        env_vars = {
            "WP_DEBUG": "true",
            "WP_DEBUG_LOG": "true",
            "WP_DEBUG_DISPLAY": "false",
            "DATABASE_URL": "mysql://localhost/test",
            "PHP_VERSION": "8.1",
        }

        env_backup = {}
        for key, value in env_vars.items():
            if key in os.environ:
                env_backup[key] = os.environ[key]
            os.environ[key] = value

        try:
            # Should initialize without errors
            settings = AutoSBMSettings()
            config = get_config()

            # Core functionality should work
            assert settings.themes_directory == "themes"
            assert config.get_setting("backup_enabled", True) is True

        finally:
            # Restore environment
            for key in env_vars:
                os.environ.pop(key, None)
            for key, value in env_backup.items():
                os.environ[key] = value

    def test_compilation_validator_environment_isolation(self):
        """Test that compilation validation works in isolated environments."""
        validator = CompilationValidator()

        # Test with temporary directory to simulate clean environment
        with tempfile.TemporaryDirectory() as temp_dir:
            test_path = Path(temp_dir) / "test.scss"
            test_path.write_text(".test { color: blue; }")

            # Start tracking and record compilation attempt
            validator.start_compilation_tracking()
            validator.track_compilation_attempt(1, CompilationStatus.SUCCESS, [], [])

            status = validator.get_final_status()
            assert status == CompilationStatus.SUCCESS

    def test_cli_command_isolation(self):
        """Test that CLI commands work in isolated environments."""
        # Test basic CLI import and functionality
        try:
            from click.testing import CliRunner

            from sbm.cli import cli

            runner = CliRunner()

            # Test help command (should work in any environment)
            result = runner.invoke(cli, ["--help"])
            assert result.exit_code == 0
            assert "Auto SBM" in result.output or "Commands:" in result.output

        except ImportError as e:
            pytest.skip(f"CLI testing skipped due to import error: {e}")

    def test_progress_tracking_isolation(self):
        """Test that progress tracking works in isolated environments."""
        from sbm.ui.progress import MigrationProgress

        # Test that progress tracking doesn't depend on external state
        progress = MigrationProgress()

        # Start and complete a step
        progress.start_step_timing("test_step")
        progress.complete_step_timing("test_step")

        # Get timing summary
        summary = progress.get_timing_summary()
        assert isinstance(summary, dict)
        assert "test_step" in summary["steps"] or "total_time" in summary

    def test_backup_system_environment_resilience(self):
        """Test that backup system handles environment variations."""
        from sbm.config import AutoSBMSettings

        # Test with non-existent backup directory in CI environment
        os.environ["CI"] = "true"

        try:
            # Should not raise an error in CI environment
            settings = AutoSBMSettings()
            # Should have default backup directory
            assert settings.backup_directory == "backups"

        finally:
            os.environ.pop("CI", None)

    def test_logging_configuration_isolation(self):
        """Test that logging configuration works in isolated environments."""
        from sbm.config import LoggingSettings

        settings = LoggingSettings()
        assert settings.log_level in ["DEBUG", "INFO", "WARNING", "ERROR"]
        assert isinstance(settings.use_rich, bool)
        assert isinstance(settings.mask_sensitive, bool)

    def test_git_operations_environment_safety(self):
        """Test that git operations are safe in different environments."""
        from sbm.config import GitSettings

        settings = GitSettings()

        # Should have safe defaults
        assert isinstance(settings.default_branch, str)
        assert isinstance(settings.github_org, str)
        assert isinstance(settings.default_labels, list)

    def test_scss_processing_environment_independence(self):
        """Test that SCSS processing works independently of environment."""
        from sbm.scss.classifiers import StyleClassifier

        classifier = StyleClassifier()

        # Test basic functionality
        test_scss = ".header { background: blue; }"
        filtered_content, result = classifier.filter_scss_content(test_scss)

        assert hasattr(result, "excluded_count")
        assert hasattr(result, "included_count")
        assert isinstance(filtered_content, str)

    def test_migration_settings_environment_defaults(self):
        """Test that migration settings have appropriate environment defaults."""
        from sbm.config import MigrationSettings

        settings = MigrationSettings()

        # Should have sensible defaults
        assert isinstance(settings.cleanup_snapshots, bool)
        assert isinstance(settings.create_backups, bool)
        assert isinstance(settings.max_concurrent_files, int)
        assert isinstance(settings.rich_ui_enabled, bool)


@pytest.mark.integration
class TestFullEnvironmentWorkflow:
    """Integration tests for full workflow in different environments."""

    def test_complete_workflow_simulation(self):
        """Simulate a complete workflow in a clean environment."""
        # This test simulates the full migration workflow
        # without actually modifying files

        from sbm.config import get_settings
        from sbm.core.validation import CompilationValidator
        from sbm.ui.progress import MigrationProgress

        # Initialize components
        get_settings()
        progress = MigrationProgress()
        validator = CompilationValidator()

        # Simulate migration steps
        steps = ["initialize", "analyze", "backup", "process", "validate", "complete"]

        for step in steps:
            progress.start_step_timing(step)
            # Simulate work
            import time
            time.sleep(0.01)  # Minimal delay for timing
            progress.complete_step_timing(step)

        # Verify results
        timing_summary = progress.get_timing_summary()
        assert isinstance(timing_summary, dict)

        # Test final status
        validator.start_compilation_tracking()
        validator.track_compilation_attempt(1, CompilationStatus.SUCCESS, [], [])
        final_status = validator.get_final_status()
        assert final_status == CompilationStatus.SUCCESS
