"""
Tests for SBM Rich status panels and displays.

This module tests the status panel creation functionality including migration
status, Docker status, error displays, and completion summaries.
"""

from unittest.mock import mock_open, patch

from rich.panel import Panel
from rich.table import Table

from sbm.ui.panels import StatusPanels


class TestStatusPanels:
    """Test suite for StatusPanels class."""

    def test_migration_status_panel_basic(self):
        """Test basic migration status panel creation."""
        panel = StatusPanels.create_migration_status_panel(
            "test-theme",
            "Step 1",
            "success"
        )

        assert isinstance(panel, Panel)
        # Test panel was created successfully
        assert panel is not None
        assert hasattr(panel, 'renderable')

    def test_migration_status_panel_with_additional_info(self):
        """Test migration status panel with additional information."""
        additional_info = {
            "Files": "4/4",
            "Duration": "2m 15s",
            "Warnings": "1"
        }

        panel = StatusPanels.create_migration_status_panel(
            "test-theme",
            "SCSS Migration",
            "warning",
            additional_info
        )

        assert isinstance(panel, Panel)
        # Test panel was created successfully
        assert panel is not None

    def test_migration_status_panel_long_theme_name(self):
        """Test migration status panel with long theme name truncation."""
        long_theme_name = "this-is-a-very-long-theme-name-that-should-be-truncated-for-display-purposes"

        panel = StatusPanels.create_migration_status_panel(
            long_theme_name,
            "Test Step",
            "in_progress"
        )

        assert isinstance(panel, Panel)
        # Should be truncated with ellipsis
        panel_str = str(panel)
        assert "..." in panel_str or len(long_theme_name) <= 40

    def test_migration_status_panel_all_statuses(self):
        """Test migration status panel with all possible statuses."""
        statuses = ["success", "warning", "error", "in_progress", "pending", "running"]
        expected_icons = ["✅", "⚠️", "❌", "⏳", "⏸️", "🔄"]

        for status, expected_icon in zip(statuses, expected_icons):
            panel = StatusPanels.create_migration_status_panel(
                "test-theme",
                "Test Step",
                status
            )

            assert isinstance(panel, Panel)
            assert expected_icon in str(panel)

    def test_docker_status_panel(self):
        """Test Docker status panel creation."""
        logs = [
            "2024-01-01 12:00:00 Container started",
            "2024-01-01 12:00:01 Compilation started",
            "2024-01-01 12:00:02 Compilation completed successfully"
        ]

        panel = StatusPanels.create_docker_status_panel("test-container", logs)

        assert isinstance(panel, Panel)
        assert panel is not None

    def test_docker_status_panel_with_status(self):
        """Test Docker status panel with different statuses."""
        logs = ["2024-01-01 12:00:00 Test log"]

        statuses = ["running", "stopped", "starting", "error"]
        expected_icons = ["🟢", "🔴", "🟡", "❌"]

        for status, expected_icon in zip(statuses, expected_icons):
            panel = StatusPanels.create_docker_status_panel(
                "test-container",
                logs,
                status
            )

            assert isinstance(panel, Panel)
            assert expected_icon in str(panel)

    def test_docker_status_panel_log_truncation(self):
        """Test Docker status panel truncates logs to recent entries."""
        # Create 15 log entries
        logs = [f"2024-01-01 12:00:{i:02d} Log entry {i}" for i in range(15)]

        panel = StatusPanels.create_docker_status_panel("test-container", logs)

        # Should only show last 8 logs
        panel_str = str(panel)
        assert "Log entry 14" in panel_str  # Last log should be present
        assert "Log entry 0" not in panel_str  # First log should be truncated

    def test_error_panel_basic(self):
        """Test basic error panel creation."""
        panel = StatusPanels.create_error_panel(
            "Syntax Error",
            "test.scss",
            42,
            "Undefined variable"
        )

        assert isinstance(panel, Panel)
        assert panel is not None

    def test_error_panel_with_code_snippet(self):
        """Test error panel with code snippet."""
        code_snippet = """$primary: #007bff;
.header {
  color: $undefined; // Error here
  margin: 10px;
}"""

        panel = StatusPanels.create_error_panel(
            "SCSS Error",
            "header.scss",
            3,
            "Undefined variable: $undefined",
            code_snippet
        )

        assert isinstance(panel, Panel)
        assert panel is not None

    def test_error_panel_with_suggested_fix(self):
        """Test error panel with suggested fix."""
        panel = StatusPanels.create_error_panel(
            "SCSS Error",
            "test.scss",
            10,
            "Missing semicolon",
            suggested_fix="Add semicolon at end of line"
        )

        assert isinstance(panel, Panel)
        assert panel is not None

    def test_error_panel_syntax_highlighting_fallback(self):
        """Test error panel handles syntax highlighting failures gracefully."""
        # Test with invalid code that might cause syntax highlighting to fail
        invalid_code = "<<< INVALID SCSS CODE >>>"

        panel = StatusPanels.create_error_panel(
            "Parse Error",
            "invalid.scss",
            1,
            "Invalid syntax",
            invalid_code
        )

        assert isinstance(panel, Panel)
        # Should still contain the code even if highlighting fails
        assert panel is not None

    @patch("sbm.utils.path.get_dealer_theme_dir")
    @patch("os.path.exists")
    @patch("os.stat")
    @patch("builtins.open", new_callable=mock_open, read_data="line1\nline2\nline3\n")
    def test_file_review_table_existing_files(self, mock_file, mock_stat, mock_exists, mock_get_dir):
        """Test file review table with existing files."""
        # Setup mocks
        mock_get_dir.return_value = "/fake/theme/dir"
        mock_exists.return_value = True

        # Mock file stats
        class MockStat:
            st_size = 1024
            st_mtime = 1640995200  # 2022-01-01 00:00:00

        mock_stat.return_value = MockStat()

        files = ["sb-inside.scss", "sb-vdp.scss"]
        table = StatusPanels.create_file_review_table("test-theme", files)

        assert isinstance(table, Table)
        table_str = str(table)
        assert "sb-inside.scss" in table_str
        assert "sb-vdp.scss" in table_str
        assert "✅ Ready" in table_str
        assert "3" in table_str  # Line count
        assert "1.0 KB" in table_str  # File size

    @patch("sbm.utils.path.get_dealer_theme_dir")
    @patch("os.path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data="")
    def test_file_review_table_empty_files(self, mock_file, mock_exists, mock_get_dir):
        """Test file review table with empty files."""
        mock_get_dir.return_value = "/fake/theme/dir"
        mock_exists.return_value = True

        files = ["empty.scss"]
        table = StatusPanels.create_file_review_table("test-theme", files)

        assert isinstance(table, Table)
        table_str = str(table)
        assert "⚠️ Empty" in table_str

    @patch("sbm.utils.path.get_dealer_theme_dir")
    @patch("os.path.exists")
    def test_file_review_table_missing_files(self, mock_exists, mock_get_dir):
        """Test file review table with missing files."""
        mock_get_dir.return_value = "/fake/theme/dir"
        mock_exists.return_value = False

        files = ["missing.scss"]
        table = StatusPanels.create_file_review_table("test-theme", files)

        assert isinstance(table, Table)
        table_str = str(table)
        assert "❌ Missing" in table_str
        assert "0 B" in table_str

    @patch("sbm.utils.path.get_dealer_theme_dir")
    @patch("os.path.exists")
    @patch("builtins.open", side_effect=OSError("Permission denied"))
    def test_file_review_table_file_error(self, mock_file, mock_exists, mock_get_dir):
        """Test file review table handles file access errors."""
        mock_get_dir.return_value = "/fake/theme/dir"
        mock_exists.return_value = True

        files = ["error.scss"]
        table = StatusPanels.create_file_review_table("test-theme", files)

        assert isinstance(table, Table)
        table_str = str(table)
        assert "❌ Error" in table_str
        assert "Permission denied" in table_str

    def test_git_status_panel(self):
        """Test Git status panel creation."""
        files_changed = ["sb-inside.scss", "sb-vdp.scss", "sb-home.scss"]
        commit_message = "SBM: Migrate test-theme to Site Builder format"

        panel = StatusPanels.create_git_status_panel(
            "test-theme",
            "test-theme-sbm20241218",
            files_changed,
            commit_message
        )

        assert isinstance(panel, Panel)
        panel_str = str(panel)
        assert "test-theme" in panel_str
        assert "test-theme-sbm20241218" in panel_str
        assert "sb-inside.scss" in panel_str
        assert "SBM: Migrate test-theme" in panel_str

    def test_git_status_panel_no_files(self):
        """Test Git status panel with no files changed."""
        panel = StatusPanels.create_git_status_panel(
            "test-theme",
            "test-branch",
            [],
            None
        )

        assert isinstance(panel, Panel)
        assert panel is not None

    def test_completion_summary_panel_basic(self):
        """Test basic completion summary panel."""
        panel = StatusPanels.create_completion_summary_panel(
            "test-theme",
            elapsed_time=125.5,
            files_processed=4
        )

        assert isinstance(panel, Panel)
        panel_str = str(panel)
        assert "Migration Complete!" in panel_str
        assert "🎉" in panel_str
        assert "test-theme" in panel_str
        assert "2m 5s" in panel_str  # 125.5 seconds formatted
        assert "4" in panel_str

    def test_completion_summary_panel_with_warnings_errors(self):
        """Test completion summary panel with warnings and errors."""
        panel = StatusPanels.create_completion_summary_panel(
            "test-theme",
            elapsed_time=45.0,
            files_processed=4,
            warnings=2,
            errors=1
        )

        assert isinstance(panel, Panel)
        panel_str = str(panel)
        assert "45.0s" in panel_str
        assert "2" in panel_str  # warnings
        assert "1" in panel_str  # errors

    def test_completion_summary_panel_with_pr_url(self):
        """Test completion summary panel with PR URL."""
        pr_url = "https://github.com/carsdotcom/platform/pull/12345"

        panel = StatusPanels.create_completion_summary_panel(
            "test-theme",
            elapsed_time=60.0,
            files_processed=4,
            pr_url=pr_url
        )

        assert isinstance(panel, Panel)
        assert pr_url in str(panel)

    def test_completion_summary_panel_time_formatting(self):
        """Test completion summary panel time formatting."""
        test_cases = [
            (30.5, "30.5s"),
            (90.0, "1m 30s"),
            (3665.0, "1h 1m")  # 1 hour, 1 minute, 5 seconds -> rounds to 1h 1m
        ]

        for elapsed_time, expected_format in test_cases:
            panel = StatusPanels.create_completion_summary_panel(
                "test-theme",
                elapsed_time=elapsed_time,
                files_processed=1
            )

            assert expected_format in str(panel)


class TestPanelIntegration:
    """Integration tests for panel functionality."""

    def test_all_panel_types_creation(self):
        """Test that all panel types can be created without errors."""
        # Migration status panel
        migration_panel = StatusPanels.create_migration_status_panel(
            "test-theme", "Test Step", "success"
        )
        assert isinstance(migration_panel, Panel)

        # Docker status panel
        docker_panel = StatusPanels.create_docker_status_panel(
            "test-container", ["Test log"]
        )
        assert isinstance(docker_panel, Panel)

        # Error panel
        error_panel = StatusPanels.create_error_panel(
            "Error", "test.scss", 1, "Test error"
        )
        assert isinstance(error_panel, Panel)

        # Git status panel
        git_panel = StatusPanels.create_git_status_panel(
            "test-theme", "test-branch", ["file.scss"]
        )
        assert isinstance(git_panel, Panel)

        # Completion summary panel
        completion_panel = StatusPanels.create_completion_summary_panel(
            "test-theme", 60.0, 4
        )
        assert isinstance(completion_panel, Panel)

    def test_panel_content_escaping(self):
        """Test that panel content handles special characters correctly."""
        # Test with special characters that might cause formatting issues
        special_theme = "test-theme-with-[brackets]-and-{braces}"

        panel = StatusPanels.create_migration_status_panel(
            special_theme,
            "Test Step",
            "success"
        )

        assert isinstance(panel, Panel)
        # Should not raise formatting errors
        panel_str = str(panel)
        assert len(panel_str) > 0
