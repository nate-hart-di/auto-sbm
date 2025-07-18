"""
Tests for SBM Rich console components.

This module tests the console management, theming, and output functionality
of the Rich UI console system.
"""

import pytest
from io import StringIO
from rich.console import Console
from sbm.ui.console import SBMConsole, get_console
from sbm.config import Config


class TestSBMConsole:
    """Test suite for SBMConsole class."""
    
    def test_console_initialization(self):
        """Test console initializes with correct theme."""
        console = SBMConsole()
        assert console.console is not None
        assert console.console.theme is not None
        assert hasattr(console, 'config')
    
    def test_console_with_config(self):
        """Test console respects configuration."""
        config = Config({'ui': {'theme': 'high-contrast'}})
        console = SBMConsole(config)
        assert console.config.get_setting('ui', {}).get('theme') == 'high-contrast'
    
    def test_theme_creation_default(self):
        """Test default theme creation."""
        console = SBMConsole()
        theme = console._create_theme()
        
        # Verify required styles exist
        assert "info" in theme.styles
        assert "error" in theme.styles
        assert "success" in theme.styles
        assert "warning" in theme.styles
        assert "progress" in theme.styles
        assert "step" in theme.styles
    
    def test_theme_creation_high_contrast(self):
        """Test high contrast theme creation."""
        config = Config({'ui': {'theme': 'high-contrast'}})
        console = SBMConsole(config)
        theme = console._create_theme()
        
        # Verify high contrast colors
        assert "bright_cyan" in str(theme.styles.get("info", ""))
        assert "bright_red" in str(theme.styles.get("error", ""))
    
    def test_step_printing(self):
        """Test step printing formats correctly."""
        # Redirect output to StringIO for testing
        output = StringIO()
        console = SBMConsole()
        console.console = Console(file=output, force_terminal=False, width=80)
        
        console.print_step(1, 6, "Test step")
        output_text = output.getvalue()
        
        assert "Step 1/6:" in output_text
        assert "Test step" in output_text
    
    def test_status_printing(self):
        """Test status message printing."""
        output = StringIO()
        console = SBMConsole()
        console.console = Console(file=output, force_terminal=False, width=80)
        
        console.print_status("Test message", "info")
        output_text = output.getvalue()
        
        assert "Test message" in output_text
    
    def test_success_message(self):
        """Test success message printing."""
        output = StringIO()
        console = SBMConsole()
        console.console = Console(file=output, force_terminal=False, width=80)
        
        console.print_success("Operation completed")
        output_text = output.getvalue()
        
        assert "✅" in output_text
        assert "Operation completed" in output_text
    
    def test_error_message(self):
        """Test error message printing."""
        output = StringIO()
        console = SBMConsole()
        console.console = Console(file=output, force_terminal=False, width=80)
        
        console.print_error("Something went wrong")
        output_text = output.getvalue()
        
        assert "❌" in output_text
        assert "Something went wrong" in output_text
    
    def test_warning_message(self):
        """Test warning message printing."""
        output = StringIO()
        console = SBMConsole()
        console.console = Console(file=output, force_terminal=False, width=80)
        
        console.print_warning("This is a warning")
        output_text = output.getvalue()
        
        assert "⚠️" in output_text
        assert "This is a warning" in output_text
    
    def test_info_message(self):
        """Test info message printing."""
        output = StringIO()
        console = SBMConsole()
        console.console = Console(file=output, force_terminal=False, width=80)
        
        console.print_info("Information message")
        output_text = output.getvalue()
        
        assert "ℹ️" in output_text
        assert "Information message" in output_text
    
    def test_header_printing(self):
        """Test header printing with subtitle."""
        output = StringIO()
        console = SBMConsole()
        console.console = Console(file=output, force_terminal=False, width=80)
        
        console.print_header("Main Title", "Subtitle text")
        output_text = output.getvalue()
        
        assert "Main Title" in output_text
        assert "Subtitle text" in output_text
    
    def test_ci_environment_detection(self):
        """Test CI environment detection."""
        console = SBMConsole()
        
        # Test with no CI environment
        is_ci = console._is_ci_environment()
        assert isinstance(is_ci, bool)
    
    def test_global_console_instance(self):
        """Test global console instance functionality."""
        config = Config({})
        console1 = get_console(config)
        console2 = get_console(config)
        
        # Should return the same instance
        assert console1 is console2
        assert isinstance(console1, SBMConsole)


class TestConsoleIntegration:
    """Integration tests for console functionality."""
    
    def test_console_output_capture(self):
        """Test that console output can be captured for testing."""
        output = StringIO()
        console = SBMConsole()
        console.console = Console(file=output, force_terminal=False, width=80)
        
        # Test various output types
        console.print_success("Success test")
        console.print_error("Error test")
        console.print_warning("Warning test")
        console.print_info("Info test")
        
        output_text = output.getvalue()
        
        assert "Success test" in output_text
        assert "Error test" in output_text
        assert "Warning test" in output_text
        assert "Info test" in output_text
    
    def test_console_theming_consistency(self):
        """Test that theming is consistent across different message types."""
        output = StringIO()
        console = SBMConsole()
        console.console = Console(file=output, force_terminal=False, width=80)
        
        # Print messages with different styles
        console.print_status("Info message", "info")
        console.print_status("Warning message", "warning")
        console.print_status("Error message", "error")
        console.print_status("Success message", "success")
        
        output_text = output.getvalue()
        
        # Verify all messages are present
        assert "Info message" in output_text
        assert "Warning message" in output_text
        assert "Error message" in output_text
        assert "Success message" in output_text