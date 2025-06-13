"""
Tests for sbm.cli module.

Tests CLI commands, argument parsing, and command execution.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from click.testing import CliRunner

from sbm.cli import cli, migrate, validate, status, config_info, doctor
from sbm.utils.errors import ValidationError, ConfigurationError


class TestCLICommands:
    """Test CLI command functionality."""
    
    def test_cli_help(self, cli_runner):
        """Test CLI help output."""
        result = cli_runner.invoke(cli, ['--help'])
        assert result.exit_code == 0
        assert "Site Builder Migration Tool V2" in result.output
        assert "migrate" in result.output
        assert "validate" in result.output
        assert "status" in result.output
    
    def test_cli_version(self, cli_runner):
        """Test CLI version output."""
        result = cli_runner.invoke(cli, ['--version'])
        assert result.exit_code == 0
        assert "2.0.0" in result.output


class TestMigrateCommand:
    """Test the migrate command."""
    
    @patch('sbm.cli.MigrationWorkflow')
    @patch('sbm.cli.get_config')
    def test_migrate_basic(self, mock_get_config, mock_workflow_class, cli_runner):
        """Test basic migrate command."""
        mock_config = Mock()
        mock_get_config.return_value = mock_config
        
        mock_workflow = Mock()
        mock_workflow.run.return_value = {"success": True, "slug": "testtheme"}
        mock_workflow_class.return_value = mock_workflow
        
        result = cli_runner.invoke(migrate, ['testtheme'])
        
        assert result.exit_code == 0
        mock_workflow_class.assert_called_once_with(mock_config)
        mock_workflow.run.assert_called_once_with("testtheme", "prod", False, False)
    
    @patch('sbm.cli.MigrationWorkflow')
    @patch('sbm.cli.get_config')
    def test_migrate_with_options(self, mock_get_config, mock_workflow_class, cli_runner):
        """Test migrate command with all options."""
        mock_config = Mock()
        mock_get_config.return_value = mock_config
        
        mock_workflow = Mock()
        mock_workflow.run.return_value = {"success": True, "slug": "testtheme"}
        mock_workflow_class.return_value = mock_workflow
        
        result = cli_runner.invoke(migrate, [
            'testtheme',
            '--environment', 'staging',
            '--dry-run',
            '--force'
        ])
        
        assert result.exit_code == 0
        mock_workflow.run.assert_called_once_with("testtheme", "staging", True, True)
    
    @patch('sbm.cli.MigrationWorkflow')
    @patch('sbm.cli.get_config')
    def test_migrate_validation_error(self, mock_get_config, mock_workflow_class, cli_runner):
        """Test migrate command with validation error."""
        mock_config = Mock()
        mock_get_config.return_value = mock_config
        
        mock_workflow = Mock()
        mock_workflow.run.side_effect = ValidationError("Invalid theme")
        mock_workflow_class.return_value = mock_workflow
        
        result = cli_runner.invoke(migrate, ['invalidtheme'])
        
        assert result.exit_code == 1
        assert "ValidationError" in result.output
        assert "Invalid theme" in result.output
    
    @patch('sbm.cli.MigrationWorkflow')
    @patch('sbm.cli.get_config')
    def test_migrate_config_error(self, mock_get_config, mock_workflow_class, cli_runner):
        """Test migrate command with configuration error."""
        mock_get_config.side_effect = ConfigurationError("Missing config")
        
        result = cli_runner.invoke(migrate, ['testtheme'])
        
        assert result.exit_code == 1
        assert "ConfigurationError" in result.output
        assert "Missing config" in result.output
    
    @patch('sbm.cli.MigrationWorkflow')
    @patch('sbm.cli.get_config')
    def test_migrate_generic_error(self, mock_get_config, mock_workflow_class, cli_runner):
        """Test migrate command with generic error."""
        mock_config = Mock()
        mock_get_config.return_value = mock_config
        
        mock_workflow = Mock()
        mock_workflow.run.side_effect = Exception("Unexpected error")
        mock_workflow_class.return_value = mock_workflow
        
        result = cli_runner.invoke(migrate, ['testtheme'])
        
        assert result.exit_code == 1
        assert "Unexpected error occurred" in result.output
    
    def test_migrate_missing_slug(self, cli_runner):
        """Test migrate command without slug argument."""
        result = cli_runner.invoke(migrate, [])
        
        assert result.exit_code == 2
        assert "Missing argument" in result.output


class TestValidateCommand:
    """Test the validate command."""
    
    @patch('sbm.cli.ValidationEngine')
    @patch('sbm.cli.get_config')
    def test_validate_basic(self, mock_get_config, mock_validator_class, cli_runner):
        """Test basic validate command."""
        mock_config = Mock()
        mock_get_config.return_value = mock_config
        
        mock_validator = Mock()
        mock_validator.validate_theme.return_value = {
            "valid": True,
            "checks": {"structure": True, "files": True}
        }
        mock_validator_class.return_value = mock_validator
        
        result = cli_runner.invoke(validate, ['testtheme'])
        
        assert result.exit_code == 0
        assert "Validation completed" in result.output
        mock_validator.validate_theme.assert_called_once_with("testtheme")
    
    @patch('sbm.cli.ValidationEngine')
    @patch('sbm.cli.get_config')
    def test_validate_with_options(self, mock_get_config, mock_validator_class, cli_runner):
        """Test validate command with options."""
        mock_config = Mock()
        mock_get_config.return_value = mock_config
        
        mock_validator = Mock()
        mock_validator.validate_theme.return_value = {"valid": True}
        mock_validator_class.return_value = mock_validator
        
        result = cli_runner.invoke(validate, [
            'testtheme',
            '--check-scss',
            '--check-git',
            '--verbose'
        ])
        
        assert result.exit_code == 0
        call_args = mock_validator.validate_theme.call_args
        assert call_args[0][0] == "testtheme"
    
    @patch('sbm.cli.ValidationEngine')
    @patch('sbm.cli.get_config')
    def test_validate_failed(self, mock_get_config, mock_validator_class, cli_runner):
        """Test validate command with failed validation."""
        mock_config = Mock()
        mock_get_config.return_value = mock_config
        
        mock_validator = Mock()
        mock_validator.validate_theme.return_value = {
            "valid": False,
            "errors": ["Missing files", "Invalid structure"]
        }
        mock_validator_class.return_value = mock_validator
        
        result = cli_runner.invoke(validate, ['testtheme'])
        
        assert result.exit_code == 1
        assert "Validation failed" in result.output


class TestStatusCommand:
    """Test the status command."""
    
    @patch('sbm.cli.get_config')
    def test_status_basic(self, mock_get_config, cli_runner):
        """Test basic status command."""
        mock_config = Mock()
        mock_config.to_dict.return_value = {
            "di_platform_dir": "/path/to/platform",
            "context7": {"enabled": True, "server_url": "http://localhost:3001"},
            "git": {"user_name": "Test User"}
        }
        mock_get_config.return_value = mock_config
        
        result = cli_runner.invoke(status)
        
        assert result.exit_code == 0
        assert "SBM Tool Status" in result.output
        assert "Configuration" in result.output
    
    @patch('sbm.cli.get_config')
    def test_status_with_theme(self, mock_get_config, cli_runner):
        """Test status command with specific theme."""
        mock_config = Mock()
        mock_config.to_dict.return_value = {"test": "config"}
        mock_config.validate_theme_exists.return_value = True
        mock_config.get_theme_path.return_value = "/path/to/theme"
        mock_get_config.return_value = mock_config
        
        result = cli_runner.invoke(status, ['--theme', 'testtheme'])
        
        assert result.exit_code == 0
        assert "testtheme" in result.output
        mock_config.validate_theme_exists.assert_called_once_with("testtheme")
    
    @patch('sbm.cli.get_config')
    def test_status_theme_not_found(self, mock_get_config, cli_runner):
        """Test status command with non-existent theme."""
        mock_config = Mock()
        mock_config.validate_theme_exists.return_value = False
        mock_get_config.return_value = mock_config
        
        result = cli_runner.invoke(status, ['--theme', 'nonexistent'])
        
        assert result.exit_code == 1
        assert "Theme not found" in result.output


class TestConfigInfoCommand:
    """Test the config-info command."""
    
    @patch('sbm.cli.get_config')
    def test_config_info_basic(self, mock_get_config, cli_runner):
        """Test basic config-info command."""
        mock_config = Mock()
        mock_config.to_dict.return_value = {
            "di_platform_dir": "/path/to/platform",
            "context7": {
                "enabled": True,
                "server_url": "http://localhost:3001",
                "api_key_set": True
            },
            "git": {
                "user_name": "Test User",
                "user_email": "test@example.com"
            },
            "stellantis": {
                "enhanced_mode": True,
                "brand_detection": "auto"
            }
        }
        mock_get_config.return_value = mock_config
        
        result = cli_runner.invoke(config_info)
        
        assert result.exit_code == 0
        assert "Configuration Information" in result.output
        assert "Context7" in result.output
        assert "Git" in result.output
        assert "Stellantis" in result.output
    
    @patch('sbm.cli.get_config')
    def test_config_info_json_output(self, mock_get_config, cli_runner):
        """Test config-info command with JSON output."""
        mock_config = Mock()
        mock_config.to_dict.return_value = {"test": "config"}
        mock_get_config.return_value = mock_config
        
        result = cli_runner.invoke(config_info, ['--json'])
        
        assert result.exit_code == 0
        assert '"test": "config"' in result.output or '"test":"config"' in result.output


class TestDoctorCommand:
    """Test the doctor command."""
    
    @patch('sbm.cli.SystemDiagnostics')
    @patch('sbm.cli.get_config')
    def test_doctor_basic(self, mock_get_config, mock_diagnostics_class, cli_runner):
        """Test basic doctor command."""
        mock_config = Mock()
        mock_get_config.return_value = mock_config
        
        mock_diagnostics = Mock()
        mock_diagnostics.run_all_checks.return_value = {
            "overall_health": "healthy",
            "checks": {
                "config": {"status": "pass", "message": "Configuration valid"},
                "git": {"status": "pass", "message": "Git available"},
                "context7": {"status": "warning", "message": "Server not responding"}
            }
        }
        mock_diagnostics_class.return_value = mock_diagnostics
        
        result = cli_runner.invoke(doctor)
        
        assert result.exit_code == 0
        assert "System Diagnostics" in result.output
        assert "Configuration valid" in result.output
        mock_diagnostics.run_all_checks.assert_called_once()
    
    @patch('sbm.cli.SystemDiagnostics')
    @patch('sbm.cli.get_config')
    def test_doctor_with_fix(self, mock_get_config, mock_diagnostics_class, cli_runner):
        """Test doctor command with fix option."""
        mock_config = Mock()
        mock_get_config.return_value = mock_config
        
        mock_diagnostics = Mock()
        mock_diagnostics.run_all_checks.return_value = {"overall_health": "healthy"}
        mock_diagnostics.fix_issues.return_value = {"fixed": 2, "failed": 0}
        mock_diagnostics_class.return_value = mock_diagnostics
        
        result = cli_runner.invoke(doctor, ['--fix'])
        
        assert result.exit_code == 0
        mock_diagnostics.fix_issues.assert_called_once()
    
    @patch('sbm.cli.SystemDiagnostics')
    @patch('sbm.cli.get_config')
    def test_doctor_unhealthy_system(self, mock_get_config, mock_diagnostics_class, cli_runner):
        """Test doctor command with unhealthy system."""
        mock_config = Mock()
        mock_get_config.return_value = mock_config
        
        mock_diagnostics = Mock()
        mock_diagnostics.run_all_checks.return_value = {
            "overall_health": "critical",
            "checks": {
                "config": {"status": "fail", "message": "Missing configuration"}
            }
        }
        mock_diagnostics_class.return_value = mock_diagnostics
        
        result = cli_runner.invoke(doctor)
        
        assert result.exit_code == 1
        assert "critical" in result.output.lower()


class TestCLIIntegration:
    """Test CLI integration scenarios."""
    
    def test_cli_command_discovery(self, cli_runner):
        """Test that all commands are properly registered."""
        result = cli_runner.invoke(cli, ['--help'])
        
        expected_commands = ['migrate', 'validate', 'status', 'config-info', 'doctor']
        for command in expected_commands:
            assert command in result.output
    
    @patch('sbm.cli.get_config')
    def test_cli_global_options(self, mock_get_config, cli_runner):
        """Test CLI global options."""
        mock_config = Mock()
        mock_get_config.return_value = mock_config
        
        result = cli_runner.invoke(cli, ['--verbose', 'status'])
        assert result.exit_code == 0
        
        result = cli_runner.invoke(cli, ['--quiet', 'status'])
        assert result.exit_code == 0
    
    def test_cli_invalid_command(self, cli_runner):
        """Test CLI with invalid command."""
        result = cli_runner.invoke(cli, ['invalid-command'])
        
        assert result.exit_code == 2
        assert "No such command" in result.output
    
    @patch('sbm.cli.get_config')
    def test_cli_config_loading_error(self, mock_get_config, cli_runner):
        """Test CLI behavior when config loading fails."""
        mock_get_config.side_effect = ConfigurationError("Config error")
        
        result = cli_runner.invoke(migrate, ['testtheme'])
        
        assert result.exit_code == 1
        assert "ConfigurationError" in result.output


class TestCLIErrorHandling:
    """Test CLI error handling and edge cases."""
    
    def test_cli_keyboard_interrupt(self, cli_runner):
        """Test CLI behavior with keyboard interrupt."""
        with patch('sbm.cli.MigrationWorkflow') as mock_workflow_class:
            mock_workflow = Mock()
            mock_workflow.run.side_effect = KeyboardInterrupt()
            mock_workflow_class.return_value = mock_workflow
            
            with patch('sbm.cli.get_config'):
                result = cli_runner.invoke(migrate, ['testtheme'])
                
                assert result.exit_code == 1
                assert "interrupted" in result.output.lower()
    
    def test_cli_permission_error(self, cli_runner):
        """Test CLI behavior with permission errors."""
        with patch('sbm.cli.get_config', side_effect=PermissionError("Permission denied")):
            result = cli_runner.invoke(migrate, ['testtheme'])
            
            assert result.exit_code == 1
            assert "Permission denied" in result.output
    
    def test_cli_file_not_found_error(self, cli_runner):
        """Test CLI behavior with file not found errors."""
        with patch('sbm.cli.get_config', side_effect=FileNotFoundError("File not found")):
            result = cli_runner.invoke(migrate, ['testtheme'])
            
            assert result.exit_code == 1
            assert "File not found" in result.output
    
    def test_cli_empty_arguments(self, cli_runner):
        """Test CLI behavior with empty arguments."""
        commands_requiring_args = [
            (['migrate'], "Missing argument"),
            (['validate'], "Missing argument")
        ]
        
        for command_args, expected_error in commands_requiring_args:
            result = cli_runner.invoke(cli, command_args)
            assert result.exit_code == 2
            assert expected_error in result.output
    
    def test_cli_invalid_options(self, cli_runner):
        """Test CLI behavior with invalid options."""
        result = cli_runner.invoke(migrate, ['testtheme', '--environment', 'invalid'])
        assert result.exit_code == 2
        assert "Invalid value" in result.output
    
    @patch('sbm.cli.get_config')
    def test_cli_output_formatting(self, mock_get_config, cli_runner):
        mock_config = Mock()
        mock_config.to_dict.return_value = {"test": "config"}
        mock_get_config.return_value = mock_config
        
        result = cli_runner.invoke(status)
        
        assert result.exit_code == 0
        lines = result.output.split('\n')
        assert len([line for line in lines if line.strip()]) > 0 
