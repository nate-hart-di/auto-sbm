"""
Tests for sbm.utils.errors module.

Tests all error classes, suggestions, and error formatting.
"""

import pytest

from sbm.utils.errors import (
    SBMError,
    ConfigurationError,
    ValidationError,
    GitError,
    SCSSError,
    Context7Error,
    OEMError,
    FileOperationError,
    ThemeError,
    MigrationError,
    format_error_for_display
)


class TestSBMError:
    """Test the base SBMError class."""
    
    def test_basic_error(self):
        """Test basic error creation."""
        error = SBMError("Test error message")
        assert str(error) == "Test error message"
        assert error.message == "Test error message"
        assert error.suggestion is None
        assert error.details == {}
    
    def test_error_with_suggestion(self):
        """Test error with suggestion."""
        error = SBMError("Test error", suggestion="Try this fix")
        assert "Test error" in str(error)
        assert "Try this fix" in str(error)
        assert error.suggestion == "Try this fix"
    
    def test_error_with_details(self):
        """Test error with details."""
        details = {"file": "test.scss", "line": 42}
        error = SBMError("Test error", details=details)
        assert error.details == details


class TestConfigurationError:
    """Test ConfigurationError class."""
    
    def test_configuration_error_basic(self):
        """Test basic configuration error."""
        error = ConfigurationError("Config missing")
        assert "Config missing" in str(error)
        assert "environment configuration" in error.suggestion
    
    def test_configuration_error_with_missing_vars(self):
        """Test configuration error with missing variables."""
        missing_vars = ["VAR1", "VAR2"]
        error = ConfigurationError("Missing vars", missing_vars=missing_vars)
        assert "VAR1" in error.suggestion
        assert "VAR2" in error.suggestion
        assert "env.example" in error.suggestion
        assert error.details["missing_vars"] == missing_vars


class TestValidationError:
    """Test ValidationError class."""
    
    def test_validation_error_basic(self):
        """Test basic validation error."""
        error = ValidationError("Validation failed")
        assert "Validation failed" in str(error)
        assert "check the input values" in error.suggestion
    
    def test_validation_error_with_field(self):
        """Test validation error with field information."""
        error = ValidationError(
            "Invalid value",
            field="theme_slug",
            expected="string",
            actual="number"
        )
        assert "Expected theme_slug to be string" in error.suggestion
        assert "but got number" in error.suggestion
        assert error.details["field"] == "theme_slug"


class TestGitError:
    """Test GitError class."""
    
    def test_git_error_basic(self):
        """Test basic git error."""
        error = GitError("Git command failed")
        assert "Git command failed" in str(error)
        assert "Git status" in error.suggestion
    
    def test_git_error_patterns(self):
        """Test git error pattern matching."""
        test_cases = [
            ("not a git repository", "correct DI Websites Platform directory"),
            ("branch already exists", "git branch -D"),
            ("nothing to commit", "No changes detected"),
            ("permission denied", "Git credentials"),
            ("merge conflict", "Resolve merge conflicts")
        ]
        
        for message, expected_suggestion in test_cases:
            error = GitError(message)
            assert expected_suggestion in error.suggestion
    
    def test_git_error_with_command(self):
        """Test git error with command details."""
        error = GitError(
            "Command failed",
            command="git commit",
            exit_code=1,
            output="error output"
        )
        assert error.details["command"] == "git commit"
        assert error.details["exit_code"] == 1
        assert error.details["output"] == "error output"


class TestSCSSError:
    """Test SCSSError class."""
    
    def test_scss_error_basic(self):
        """Test basic SCSS error."""
        error = SCSSError("SCSS compilation failed")
        assert "SCSS compilation failed" in str(error)
        assert "SCSS standards" in error.suggestion
    
    def test_scss_error_patterns(self):
        """Test SCSS error pattern matching."""
        test_cases = [
            ("syntax error", "missing semicolons"),
            ("variable not found", "properly defined and imported"),
            ("mixin undefined", "properly included"),
            ("import failed", "referenced files exist")
        ]
        
        for message, expected_suggestion in test_cases:
            error = SCSSError(message)
            assert expected_suggestion in error.suggestion
    
    def test_scss_error_with_details(self):
        """Test SCSS error with file details."""
        error = SCSSError(
            "Syntax error",
            file_path="/path/to/file.scss",
            line_number=42,
            syntax_error="missing semicolon"
        )
        assert error.details["file_path"] == "/path/to/file.scss"
        assert error.details["line_number"] == 42
        assert error.details["syntax_error"] == "missing semicolon"


class TestContext7Error:
    """Test Context7Error class."""
    
    def test_context7_error_basic(self):
        """Test basic Context7 error."""
        error = Context7Error("Connection failed")
        assert "Connection failed" in str(error)
        assert "Context7 server status" in error.suggestion
        assert "SKIP_CONTEXT7=true" in error.suggestion
    
    def test_context7_error_patterns(self):
        """Test Context7 error pattern matching."""
        test_cases = [
            ("connection refused", "server is running"),
            ("timeout", "network connectivity"),
            ("unauthorized", "API key is correct"),
            ("not found", "server URL"),
            ("server error", "server logs")
        ]
        
        for message, expected_suggestion in test_cases:
            error = Context7Error(message)
            assert expected_suggestion in error.suggestion
    
    def test_context7_error_with_details(self):
        """Test Context7 error with server details."""
        error = Context7Error(
            "Server error",
            server_url="http://localhost:3001",
            status_code=500,
            response="Internal server error"
        )
        assert error.details["server_url"] == "http://localhost:3001"
        assert error.details["status_code"] == 500
        assert error.details["response"] == "Internal server error"


class TestOEMError:
    """Test OEMError class."""
    
    def test_oem_error_basic(self):
        """Test basic OEM error."""
        error = OEMError("OEM handler failed")
        assert "OEM handler failed" in str(error)
        assert "OEM configuration" in error.suggestion
    
    def test_oem_error_patterns(self):
        """Test OEM error pattern matching."""
        test_cases = [
            ("handler not found", "properly implemented"),
            ("brand detection failed", "brand detection patterns"),
            ("stellantis error", "enhanced mode is enabled")
        ]
        
        for message, expected_suggestion in test_cases:
            error = OEMError(message)
            assert expected_suggestion in error.suggestion
    
    def test_oem_error_with_details(self):
        """Test OEM error with details."""
        error = OEMError(
            "Brand detection failed",
            oem="Stellantis",
            slug="chryslerofportland",
            brand="Chrysler"
        )
        assert error.details["oem"] == "Stellantis"
        assert error.details["slug"] == "chryslerofportland"
        assert error.details["brand"] == "Chrysler"


class TestFileOperationError:
    """Test FileOperationError class."""
    
    def test_file_operation_error_basic(self):
        """Test basic file operation error."""
        error = FileOperationError("File operation failed")
        assert "File operation failed" in str(error)
        assert "file path, permissions" in error.suggestion
    
    def test_file_operation_error_patterns(self):
        """Test file operation error pattern matching."""
        test_cases = [
            ("not found", "file or directory exists"),
            ("permission denied", "write access"),
            ("already exists", "force mode"),
            ("disk full", "disk space"),
            ("read-only", "file permissions")
        ]
        
        for message, expected_suggestion in test_cases:
            error = FileOperationError(message)
            assert expected_suggestion in error.suggestion
    
    def test_file_operation_error_with_details(self):
        """Test file operation error with details."""
        error = FileOperationError(
            "Permission denied",
            file_path="/path/to/file",
            operation="write",
            permissions=False
        )
        assert error.details["file_path"] == "/path/to/file"
        assert error.details["operation"] == "write"
        assert error.details["permissions"] is False


class TestThemeError:
    """Test ThemeError class."""
    
    def test_theme_error_basic(self):
        """Test basic theme error."""
        error = ThemeError("Theme not found")
        assert "Theme not found" in str(error)
        assert "theme configuration" in error.suggestion
    
    def test_theme_error_not_found(self):
        """Test theme not found error."""
        error = ThemeError("Theme not found", slug="testtheme")
        assert "testtheme" in error.suggestion
        assert "dealer-themes directory" in error.suggestion
        assert error.details["slug"] == "testtheme"
    
    def test_theme_error_invalid(self):
        """Test invalid theme error."""
        error = ThemeError("Invalid theme structure")
        assert "theme structure" in error.suggestion
        assert "required files" in error.suggestion


class TestMigrationError:
    """Test MigrationError class."""
    
    def test_migration_error_basic(self):
        """Test basic migration error."""
        error = MigrationError("Migration failed")
        assert "Migration failed" in str(error)
        assert "migration logs" in error.suggestion
    
    def test_migration_error_with_step(self):
        """Test migration error with step information."""
        step_suggestions = {
            "initialization": "just start",
            "file_creation": "Site Builder file templates",
            "style_migration": "SCSS processing",
            "validation": "validation rules",
            "git_operations": "Git repository state"
        }
        
        for step, expected_suggestion in step_suggestions.items():
            error = MigrationError("Step failed", step=step)
            assert expected_suggestion in error.suggestion
    
    def test_migration_error_partial_success(self):
        """Test migration error with partial success."""
        error = MigrationError(
            "Migration failed",
            step="validation",
            slug="testtheme",
            partial_success=True
        )
        assert "Some steps completed successfully" in error.suggestion
        assert error.details["partial_success"] is True
        assert error.details["slug"] == "testtheme"


class TestErrorFormatting:
    """Test error formatting functions."""
    
    def test_format_sbm_error(self):
        """Test formatting SBM error for display."""
        error = ValidationError(
            "Test validation error",
            field="test_field",
            expected="string"
        )
        formatted = format_error_for_display(error)
        
        assert formatted["type"] == "ValidationError"
        assert formatted["message"] == "Test validation error"
        assert "Expected test_field" in formatted["suggestion"]
        assert "field" in formatted["details"]
    
    def test_format_generic_error(self):
        """Test formatting generic error for display."""
        error = ValueError("Generic error message")
        formatted = format_error_for_display(error)
        
        assert formatted["type"] == "ValueError"
        assert formatted["message"] == "Generic error message"
        assert formatted["suggestion"] == "Check the error message and try again."
        assert formatted["details"] == {}
    
    def test_format_error_with_all_fields(self):
        """Test formatting error with all fields populated."""
        error = GitError(
            "Git operation failed",
            command="git commit",
            exit_code=1,
            output="error output"
        )
        formatted = format_error_for_display(error)
        
        assert formatted["type"] == "GitError"
        assert formatted["message"] == "Git operation failed"
        assert formatted["suggestion"] is not None
        assert "command" in formatted["details"]
        assert "exit_code" in formatted["details"]
        assert "output" in formatted["details"]


class TestErrorInheritance:
    """Test error class inheritance and behavior."""
    
    def test_all_errors_inherit_from_sbm_error(self):
        """Test that all custom errors inherit from SBMError."""
        error_classes = [
            ConfigurationError,
            ValidationError,
            GitError,
            SCSSError,
            Context7Error,
            OEMError,
            FileOperationError,
            ThemeError,
            MigrationError
        ]
        
        for error_class in error_classes:
            error = error_class("Test message")
            assert isinstance(error, SBMError)
            assert isinstance(error, Exception)
    
    def test_error_string_representation(self):
        """Test string representation of errors."""
        error_with_suggestion = SBMError("Error message", suggestion="Fix suggestion")
        error_without_suggestion = SBMError("Error message")
        
        assert "Error message" in str(error_with_suggestion)
        assert "Fix suggestion" in str(error_with_suggestion)
        assert str(error_without_suggestion) == "Error message"
    
    def test_error_exception_behavior(self):
        """Test that errors can be raised and caught properly."""
        with pytest.raises(SBMError) as exc_info:
            raise ValidationError("Test validation error")
        
        assert isinstance(exc_info.value, ValidationError)
        assert isinstance(exc_info.value, SBMError)
        assert "Test validation error" in str(exc_info.value) 
