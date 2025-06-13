"""
Tests for sbm.utils.logger module.

Tests logging functionality, Rich console output, and progress tracking.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from io import StringIO

from sbm.utils.logger import SBMLogger, get_logger, setup_logging, reset_loggers


class TestSBMLogger:
    """Test the SBMLogger class."""
    
    def test_logger_initialization(self):
        """Test logger initialization."""
        logger = SBMLogger("test")
        assert logger.name == "test"
        assert logger.console is not None
        assert logger._progress is None
        assert logger._current_task is None
    
    def test_logger_setup(self):
        """Test logger setup with different configurations."""
        logger = SBMLogger("test")
        
        # Test basic setup
        logger.setup("INFO")
        assert logger._logger.level == 20  # INFO level
        
        # Test with file logging
        with patch('logging.FileHandler') as mock_file_handler:
            logger.setup("DEBUG", "test.log")
            mock_file_handler.assert_called_once_with("test.log")
    
    def test_basic_logging_methods(self):
        """Test basic logging methods."""
        logger = SBMLogger("test")
        logger.setup("DEBUG")
        
        with patch.object(logger._logger, 'info') as mock_info, \
             patch.object(logger._logger, 'error') as mock_error, \
             patch.object(logger._logger, 'warning') as mock_warning, \
             patch.object(logger._logger, 'debug') as mock_debug:
            
            logger.info("Test info message")
            logger.error("Test error message")
            logger.warning("Test warning message")
            logger.debug("Test debug message")
            
            mock_info.assert_called_once_with("Test info message")
            mock_error.assert_called_once_with("Test error message")
            mock_warning.assert_called_once_with("Test warning message")
            mock_debug.assert_called_once_with("Test debug message")
    
    def test_styled_logging_methods(self):
        """Test styled logging methods."""
        logger = SBMLogger("test")
        
        with patch.object(logger.console, 'print') as mock_print:
            logger.success("Success message")
            logger.failure("Failure message")
            logger.step("Step message")
            
            assert mock_print.call_count == 3
            
            # Check that styled messages were printed
            calls = mock_print.call_args_list
            assert "✅" in str(calls[0])
            assert "❌" in str(calls[1])
            assert "🔄" in str(calls[2])
    
    def test_migration_header(self):
        """Test migration header display."""
        logger = SBMLogger("test")
        
        with patch.object(logger.console, 'print') as mock_print:
            logger.migration_header("chryslerofportland", "Stellantis")
            
            # Should print empty lines and panel
            assert mock_print.call_count >= 3
            
            # Check that dealer and OEM info is included
            printed_content = str(mock_print.call_args_list)
            assert "chryslerofportland" in printed_content
            assert "Stellantis" in printed_content
    
    def test_migration_summary(self):
        """Test migration summary display."""
        logger = SBMLogger("test")
        
        with patch.object(logger.console, 'print') as mock_print:
            # Test successful migration
            logger.migration_summary("testtheme", True, 45.2, 4, 0)
            
            printed_content = str(mock_print.call_args_list)
            assert "SUCCESS" in printed_content
            assert "45.2" in printed_content
            assert "4" in printed_content
            
            mock_print.reset_mock()
            
            # Test failed migration
            logger.migration_summary("testtheme", False, 30.1, 2, 3)
            
            printed_content = str(mock_print.call_args_list)
            assert "FAILED" in printed_content
            assert "30.1" in printed_content
            assert "3" in printed_content
    
    def test_demo_banner(self):
        """Test demo mode banner."""
        logger = SBMLogger("test")
        
        with patch.object(logger.console, 'print') as mock_print:
            logger.demo_banner()
            
            printed_content = str(mock_print.call_args_list)
            assert "DEMO MODE ACTIVE" in printed_content
            assert "🎯" in printed_content
    
    def test_context7_status(self):
        """Test Context7 status display."""
        logger = SBMLogger("test")
        
        with patch.object(logger.console, 'print') as mock_print:
            # Test enabled status
            logger.context7_status(True, "http://localhost:3001")
            
            printed_content = str(mock_print.call_args_list)
            assert "CONNECTED" in printed_content
            assert "http://localhost:3001" in printed_content
            
            mock_print.reset_mock()
            
            # Test disabled status
            logger.context7_status(False, "http://localhost:3001")
            
            printed_content = str(mock_print.call_args_list)
            assert "DISABLED" in printed_content
    
    def test_progress_tracking(self):
        """Test progress tracking functionality."""
        logger = SBMLogger("test")
        
        with patch('sbm.utils.logger.Progress') as mock_progress_class:
            mock_progress = Mock()
            mock_progress_class.return_value = mock_progress
            
            # Start progress
            logger.start_progress("Testing progress")
            assert logger._progress is not None
            mock_progress.start.assert_called_once()
            mock_progress.add_task.assert_called_once_with("Testing progress", total=100)
            
            # Update progress
            logger.update_progress(25, "Updated description")
            mock_progress.update.assert_called()
            mock_progress.advance.assert_called()
            
            # Complete progress
            logger.complete_progress()
            mock_progress.stop.assert_called_once()
            assert logger._progress is None
    
    def test_validation_results(self):
        """Test validation results display."""
        logger = SBMLogger("test")
        
        results = {
            "SCSS Syntax": {"passed": True, "message": "All files valid"},
            "File Structure": {"passed": False, "message": "Missing files"},
            "Simple Check": True,
            "Failed Check": False
        }
        
        with patch.object(logger.console, 'print') as mock_print:
            logger.validation_results(results)
            
            # Should print table
            assert mock_print.call_count >= 1
            printed_content = str(mock_print.call_args_list)
            assert "Validation Results" in printed_content
    
    def test_error_with_suggestion(self):
        """Test error display with suggestion."""
        logger = SBMLogger("test")
        
        with patch.object(logger.console, 'print') as mock_print:
            logger.error_with_suggestion("Test error", "Try this fix")
            
            printed_content = str(mock_print.call_args_list)
            assert "Test error" in printed_content
            assert "Try this fix" in printed_content


class TestLoggerGlobal:
    """Test global logger functions."""
    
    def test_get_logger_singleton(self):
        """Test that get_logger returns the same instance for same name."""
        logger1 = get_logger("test")
        logger2 = get_logger("test")
        assert logger1 is logger2
        
        # Different names should return different instances
        logger3 = get_logger("different")
        assert logger1 is not logger3
    
    def test_get_logger_default_name(self):
        """Test get_logger with default name."""
        logger = get_logger()
        assert logger.name == "sbm"
    
    def test_setup_logging(self):
        """Test global logging setup."""
        with patch('sbm.utils.logger.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            setup_logging("DEBUG", "test.log")
            
            mock_get_logger.assert_called_once()
            mock_logger.setup.assert_called_once_with("DEBUG", "test.log")
    
    def test_reset_loggers(self):
        """Test logger reset functionality."""
        logger1 = get_logger("test")
        reset_loggers()
        logger2 = get_logger("test")
        
        assert logger1 is not logger2


class TestLoggerIntegration:
    """Test logger integration scenarios."""
    
    def test_logger_with_real_console_output(self):
        """Test logger with actual console output."""
        logger = SBMLogger("integration_test")
        logger.setup("INFO")
        
        # This should not raise any exceptions
        logger.info("Integration test message")
        logger.success("Integration test success")
        logger.step("Integration test step")
    
    def test_logger_progress_without_rich(self):
        """Test logger behavior when Rich components fail."""
        logger = SBMLogger("test")
        
        with patch('sbm.utils.logger.Progress', side_effect=ImportError("Rich not available")):
            # Should handle gracefully
            logger.start_progress("Test")
            logger.update_progress(50)
            logger.complete_progress()
    
    def test_logger_file_logging_error(self):
        """Test logger behavior when file logging fails."""
        logger = SBMLogger("test")
        
        with patch('logging.FileHandler', side_effect=PermissionError("Cannot write to file")):
            # Should handle gracefully and continue with console logging
            with pytest.raises(PermissionError):
                logger.setup("INFO", "/invalid/path/test.log")
    
    def test_logger_with_different_log_levels(self):
        """Test logger with different log levels."""
        logger = SBMLogger("test")
        
        # Test all valid log levels
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR"]
        
        for level in valid_levels:
            logger.setup(level)
            # Should not raise exceptions
            logger.info("Test message")
            logger.debug("Debug message")
            logger.warning("Warning message")
            logger.error("Error message")
    
    def test_logger_concurrent_progress_tracking(self):
        """Test logger behavior with concurrent progress operations."""
        logger = SBMLogger("test")
        
        with patch('sbm.utils.logger.Progress') as mock_progress_class:
            mock_progress = Mock()
            mock_progress_class.return_value = mock_progress
            
            # Start first progress
            logger.start_progress("First task")
            
            # Starting second progress should reuse existing
            logger.start_progress("Second task")
            
            # Should only create one Progress instance
            assert mock_progress_class.call_count == 1
    
    def test_logger_rich_formatting(self):
        """Test Rich formatting in logger output."""
        logger = SBMLogger("test")
        
        with patch.object(logger.console, 'print') as mock_print:
            # Test that Rich markup is preserved
            logger.success("Success with [bold]formatting[/bold]")
            
            # Should pass through Rich formatting
            call_args = mock_print.call_args_list[0]
            assert "[bold]" in str(call_args) or "formatting" in str(call_args)


class TestLoggerErrorHandling:
    """Test logger error handling and edge cases."""
    
    def test_logger_with_none_values(self):
        """Test logger behavior with None values."""
        logger = SBMLogger("test")
        logger.setup("INFO")
        
        # Should handle None values gracefully
        logger.info(None)
        logger.migration_header("test", None)
        logger.context7_status(True, None)
    
    def test_logger_with_empty_strings(self):
        """Test logger behavior with empty strings."""
        logger = SBMLogger("test")
        logger.setup("INFO")
        
        # Should handle empty strings gracefully
        logger.info("")
        logger.success("")
        logger.error_with_suggestion("", "")
    
    def test_logger_with_unicode_content(self):
        """Test logger behavior with Unicode content."""
        logger = SBMLogger("test")
        logger.setup("INFO")
        
        # Should handle Unicode content
        logger.info("Test with émojis 🚀 and ünïcödé")
        logger.success("Success with 中文 characters")
    
    def test_logger_memory_cleanup(self):
        """Test that logger properly cleans up resources."""
        logger = SBMLogger("test")
        
        with patch('sbm.utils.logger.Progress') as mock_progress_class:
            mock_progress = Mock()
            mock_progress_class.return_value = mock_progress
            
            # Start and complete progress multiple times
            for i in range(3):
                logger.start_progress(f"Task {i}")
                logger.complete_progress()
            
            # Should properly clean up each time
            assert mock_progress.stop.call_count == 3
            assert logger._progress is None
            assert logger._current_task is None 
