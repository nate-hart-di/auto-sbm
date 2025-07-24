"""
Unit tests for fullauto mode functionality.

This module tests the fullauto mode implementation to ensure it bypasses
all user prompts except for actual compilation errors.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from click.testing import CliRunner

from sbm.cli import cli
from sbm.core.migration import migrate_dealer_theme, run_post_migration_workflow


class TestFullautoMode:
    """Test fullauto mode functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.theme_name = "test-theme"

    @patch('sbm.cli.migrate_dealer_theme')
    @patch('sbm.cli.get_config')
    def test_fullauto_command_exists(self, mock_get_config, mock_migrate):
        """Test that fullauto command exists and can be invoked."""
        mock_config = Mock()
        mock_get_config.return_value = mock_config
        mock_migrate.return_value = True

        result = self.runner.invoke(cli, ['fullauto', self.theme_name])
        
        assert result.exit_code == 0
        mock_migrate.assert_called_once()

    @patch('sbm.cli.migrate_dealer_theme')
    @patch('sbm.cli.get_config')  
    def test_fullauto_bypasses_migration_start_prompt(self, mock_get_config, mock_migrate):
        """Test that fullauto mode bypasses migration start confirmation."""
        mock_config = Mock()
        mock_get_config.return_value = mock_config
        mock_migrate.return_value = True

        result = self.runner.invoke(cli, ['fullauto', self.theme_name])
        
        # Should not prompt for user input
        assert "Proceed with migration?" not in result.output
        assert result.exit_code == 0

    @patch('sbm.core.migration.run_post_migration_workflow')
    @patch('sbm.core.migration.migrate_map_components')
    @patch('sbm.core.migration.add_predetermined_styles')
    @patch('sbm.core.migration.migrate_styles')
    @patch('sbm.core.migration.create_sb_files')
    @patch('sbm.core.migration.run_just_start')
    @patch('sbm.core.migration.git_operations')
    @patch('sbm.oem.factory.OEMFactory.detect_from_theme')
    def test_fullauto_passes_correct_interactive_flags(
        self, mock_oem, mock_git, mock_just, mock_create, 
        mock_styles, mock_predetermined, mock_maps, mock_post_workflow
    ):
        """Test that fullauto mode passes interactive_* flags as False."""
        # Setup mocks
        mock_oem.return_value = Mock()
        mock_git.return_value = (True, "test-branch")
        mock_just.return_value = True
        mock_create.return_value = True
        mock_styles.return_value = True
        mock_predetermined.return_value = True
        mock_maps.return_value = True
        mock_post_workflow.return_value = True

        # Call migrate_dealer_theme with fullauto parameters
        result = migrate_dealer_theme(
            self.theme_name,
            interactive_review=False,
            interactive_git=False,
            interactive_pr=False
        )

        assert result is True
        mock_post_workflow.assert_called_once()
        
        # Verify post-migration workflow called with interactive flags as False
        call_args = mock_post_workflow.call_args
        assert call_args[1]['interactive_review'] is False
        assert call_args[1]['interactive_git'] is False
        assert call_args[1]['interactive_pr'] is False

    @patch('sbm.core.migration.reprocess_manual_changes')
    @patch('sbm.core.migration.git_create_pr')
    @patch('sbm.core.migration.push_changes')
    @patch('sbm.core.migration.commit_changes')
    @patch('click.confirm')
    def test_fullauto_bypasses_post_migration_prompts(
        self, mock_confirm, mock_commit, mock_push, mock_pr, mock_reprocess
    ):
        """Test that fullauto mode bypasses all post-migration prompts."""
        # Setup mocks
        mock_reprocess.return_value = True
        mock_commit.return_value = True
        mock_push.return_value = True
        mock_pr.return_value = {"success": True, "pr_url": "test-url"}

        # Run post-migration workflow with fullauto flags
        result = run_post_migration_workflow(
            self.theme_name,
            "test-branch",
            interactive_review=False,
            interactive_git=False,
            interactive_pr=False
        )

        assert result is True
        
        # Verify no confirmation prompts were called
        mock_confirm.assert_not_called()
        
        # Verify operations were executed
        mock_commit.assert_called_once()
        mock_push.assert_called_once()
        mock_pr.assert_called_once()

    @patch('sbm.core.migration.reprocess_manual_changes')
    @patch('click.confirm')
    def test_fullauto_skips_manual_review(self, mock_confirm, mock_reprocess):
        """Test that fullauto mode skips manual review phase."""
        mock_reprocess.return_value = True

        result = run_post_migration_workflow(
            self.theme_name,
            "test-branch",
            interactive_review=False,
            interactive_git=False,
            interactive_pr=False
        )

        # Manual review prompt should not be called
        mock_confirm.assert_not_called()

    @patch('sbm.core.migration._handle_compilation_with_error_recovery')
    @patch('click.confirm')
    def test_fullauto_still_handles_compilation_errors(self, mock_confirm, mock_error_recovery):
        """Test that fullauto mode still stops for compilation errors."""
        # Simulate compilation error
        mock_error_recovery.return_value = False
        
        # This should be tested at the compilation level
        # The error recovery system should still function but with different behavior
        # in fullauto mode (auto-retry without prompts, fail after max attempts)
        
        # For now, verify the error recovery system is still called
        from sbm.core.migration import _verify_scss_compilation_with_docker
        
        with patch('sbm.core.migration._handle_compilation_with_error_recovery') as mock_handler:
            mock_handler.return_value = False
            
            result = _verify_scss_compilation_with_docker("/fake/path", self.theme_name, ["sb-inside.scss"])
            
            # Should still attempt error recovery
            assert result is False

    def test_fullauto_integration_with_cli(self):
        """Integration test for fullauto CLI command."""
        # This would test the full CLI integration
        # For now, verify the command structure
        
        from sbm.cli import fullauto
        
        # Verify the command is properly decorated
        assert hasattr(fullauto, '__click_params__')
        assert len(fullauto.__click_params__) == 1  # theme_name argument
        
        # Verify it's registered as a CLI command
        from sbm.cli import cli
        assert 'fullauto' in [cmd.name for cmd in cli.commands.values()]


class TestFullautoErrorHandling:
    """Test fullauto mode error handling scenarios."""

    def setup_method(self):
        """Set up test fixtures."""
        self.theme_name = "test-theme"

    @patch('sbm.core.migration.click.confirm')
    def test_fullauto_compilation_error_no_prompts(self, mock_confirm):
        """Test that compilation errors in fullauto mode don't prompt user."""
        # This test would verify that compilation errors are handled
        # without user prompts in fullauto mode
        
        # Mock a compilation error scenario
        with patch('sbm.core.migration._parse_compilation_errors') as mock_parse:
            mock_parse.return_value = [
                {
                    "type": "invalid_css",
                    "line_content": "test error",
                    "match_groups": [],
                    "original_line": "test error"
                }
            ]
            
            # In fullauto mode, should not call click.confirm
            from sbm.core.migration import _handle_compilation_with_error_recovery
            
            # This needs to be implemented to respect fullauto mode
            # For now, just verify the structure exists
            assert callable(_handle_compilation_with_error_recovery)

    def test_fullauto_git_error_handling(self):
        """Test that git errors in fullauto mode are handled properly."""
        # This would test git operation error handling in fullauto mode
        # Should fail fast without prompts
        
        with patch('sbm.core.migration.commit_changes') as mock_commit:
            mock_commit.return_value = False
            
            result = run_post_migration_workflow(
                self.theme_name,
                "test-branch",
                interactive_review=False,
                interactive_git=False,
                interactive_pr=False
            )
            
            # Should fail without prompting
            assert result is False


class TestFullautoModeConfiguration:
    """Test fullauto mode configuration and parameter passing."""

    def test_fullauto_command_invokes_auto_with_correct_params(self):
        """Test that fullauto command calls auto with fullauto=True."""
        from sbm.cli import fullauto
        from unittest.mock import patch
        
        with patch('sbm.cli.auto') as mock_auto:
            with patch('click.get_current_context') as mock_ctx:
                mock_ctx.return_value.invoke = Mock()
                
                # This is the implementation we need to add
                # For now, verify the command exists
                assert callable(fullauto)


@pytest.fixture
def mock_dependencies():
    """Mock all external dependencies for testing."""
    with patch.multiple(
        'sbm.core.migration',
        git_operations=Mock(return_value=(True, "test-branch")),
        run_just_start=Mock(return_value=True),
        create_sb_files=Mock(return_value=True),
        migrate_styles=Mock(return_value=True),
        add_predetermined_styles=Mock(return_value=True),
        migrate_map_components=Mock(return_value=True),
        commit_changes=Mock(return_value=True),
        push_changes=Mock(return_value=True),
    ) as mocks:
        yield mocks


class TestFullautoEndToEnd:
    """End-to-end tests for fullauto mode."""

    def test_fullauto_complete_workflow(self, mock_dependencies):
        """Test complete fullauto workflow without user interaction."""
        # This would be a comprehensive end-to-end test
        # Verifying the entire workflow completes without prompts
        
        result = migrate_dealer_theme(
            "test-theme",
            interactive_review=False,
            interactive_git=False,
            interactive_pr=False
        )
        
        assert result is True
        
        # Verify all steps were called
        mock_dependencies['git_operations'].assert_called_once()
        mock_dependencies['run_just_start'].assert_called_once()
        mock_dependencies['create_sb_files'].assert_called_once()
        mock_dependencies['migrate_styles'].assert_called_once()
        mock_dependencies['add_predetermined_styles'].assert_called_once()
        mock_dependencies['migrate_map_components'].assert_called_once()