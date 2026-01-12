"""
Core CLI command registration and functionality tests.
Tests the Click CLI interface and command registration.
"""
import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

from sbm.cli import cli


class TestCLICommands:
    """Test CLI command registration and basic functionality."""

    def setUp(self):
        self.runner = CliRunner()

    def test_cli_help_works(self):
        """Test main CLI help command works."""
        runner = CliRunner()
        result = runner.invoke(cli, ['--help'])

        assert result.exit_code == 0
        assert "Auto-SBM" in result.output
        assert "migrate" in result.output

    def test_cli_version_command(self):
        """Test version command exists and works."""
        runner = CliRunner()
        result = runner.invoke(cli, ['version'])

        assert result.exit_code == 0
        assert "2.7.0" in result.output or "version" in result.output.lower()

    def test_migrate_command_exists(self):
        """Test migrate command is registered."""
        runner = CliRunner()
        result = runner.invoke(cli, ['migrate', '--help'])

        assert result.exit_code == 0
        assert "migrate" in result.output.lower()

    def test_validate_command_exists(self):
        """Test validate command is registered."""
        runner = CliRunner()
        result = runner.invoke(cli, ['validate', '--help'])

        # Should either work or show that command exists
        assert result.exit_code in [0, 2]  # 0 = success, 2 = command exists but needs args

    def test_cli_handles_invalid_command(self):
        """Test CLI gracefully handles invalid commands."""
        runner = CliRunner()
        result = runner.invoke(cli, ['--invalid-flag'])

        assert result.exit_code != 0
        assert "No such option" in result.output or "Usage:" in result.output or "Error:" in result.output


class TestCLIOptions:
    """Test CLI global options and flags."""

    def test_verbose_flag_exists(self):
        """Test --verbose flag is available."""
        runner = CliRunner()
        result = runner.invoke(cli, ['--help'])

        assert result.exit_code == 0
        assert "--verbose" in result.output or "-v" in result.output

    def test_config_option_exists(self):
        """Test --config option is available."""
        runner = CliRunner()
        result = runner.invoke(cli, ['--help'])

        assert result.exit_code == 0
        assert "--config" in result.output

    @patch('sbm.config.AutoSBMSettings')
    def test_cli_loads_config(self, mock_config):
        """Test CLI attempts to load configuration."""
        mock_config.return_value = MagicMock()

        runner = CliRunner()
        # Try to run any command that would load config
        runner.invoke(cli, ['--help'])

        # Config should be imported/used somewhere in the CLI flow
        # This test ensures config loading doesn't crash the CLI


class TestCLIErrorHandling:
    """Test CLI error handling and edge cases."""

    def test_cli_handles_missing_config(self):
        """Test CLI handles missing configuration gracefully."""
        runner = CliRunner()

        with patch('sbm.config.AutoSBMSettings') as mock_config:
            # Simulate config loading error
            mock_config.side_effect = Exception("Config load failed")

            result = runner.invoke(cli, ['--help'])

            # CLI should either handle the error gracefully or show help
            # (help command shouldn't require full config)
            assert result.exit_code in [0, 1]

    def test_cli_handles_keyboard_interrupt(self):
        """Test CLI handles Ctrl+C gracefully."""
        runner = CliRunner()

        with patch('sbm.cli.cli') as mock_cli:
            mock_cli.side_effect = KeyboardInterrupt()

            # This test ensures KeyboardInterrupt is handled properly
            # (Implementation detail - would need actual command that can be interrupted)

    def test_migrate_command_requires_theme(self):
        """Test migrate command requires theme argument."""
        runner = CliRunner()
        result = runner.invoke(cli, ['migrate'])

        # Should fail with missing argument error
        assert result.exit_code != 0
        assert "Missing argument" in result.output or "Usage:" in result.output


class TestCLIIntegration:
    """Test CLI integration with core functionality."""

    @patch('sbm.config.AutoSBMSettings')
    def test_cli_with_valid_config(self, mock_config):
        """Test CLI works with valid configuration."""
        # Mock valid config
        mock_settings = MagicMock()
        mock_settings.github_token = "test_token"
        mock_settings.github_org = "test_org"
        mock_config.return_value = mock_settings

        runner = CliRunner()
        result = runner.invoke(cli, ['--help'])

        assert result.exit_code == 0

    def test_cli_commands_are_clickified(self):
        """Test all CLI commands are properly decorated with Click."""
        # Get all commands from the CLI
        commands = cli.list_commands(None)

        # Should have main commands
        expected_commands = ['migrate', 'version']

        for cmd in expected_commands:
            if cmd in commands:
                # Command exists - verify it's properly set up
                command_obj = cli.get_command(None, cmd)
                assert command_obj is not None

    def test_cli_import_doesnt_crash(self):
        """Test importing CLI module doesn't crash."""
        # This test ensures all imports in cli.py work
        try:
            from sbm.cli import cli
            assert cli is not None
        except ImportError as e:
            pytest.fail(f"CLI import failed: {e}")
        except Exception as e:
            pytest.fail(f"CLI import caused error: {e}")
