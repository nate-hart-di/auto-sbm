"""
Comprehensive tests for wrapper script environment isolation.

Tests ensure that the sbm wrapper script properly isolates itself from
other active virtual environments (e.g., di-websites-platform venv).
"""

import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open, call
import pytest


# =============================================================================
# TEST 1: Wrapper Script Environment Isolation
# =============================================================================


class TestWrapperEnvironmentIsolation:
    """Tests for wrapper script environment variable isolation."""

    def test_wrapper_unsets_virtual_env(self):
        """Verify wrapper script unsets VIRTUAL_ENV to prevent conflicts."""
        from sbm.cli import _regenerate_wrapper_script

        with patch("pathlib.Path.open", mock_open()) as mock_file, \
             patch("os.chmod"), \
             patch("pathlib.Path.mkdir"):

            _regenerate_wrapper_script()

            # Get the written content
            written_content = mock_file().write.call_args[0][0]

            # Verify VIRTUAL_ENV is unset
            assert "unset VIRTUAL_ENV" in written_content

    def test_wrapper_unsets_pythonpath(self):
        """Verify wrapper script unsets PYTHONPATH to prevent import conflicts."""
        from sbm.cli import _regenerate_wrapper_script

        with patch("pathlib.Path.open", mock_open()) as mock_file, \
             patch("os.chmod"), \
             patch("pathlib.Path.mkdir"):

            _regenerate_wrapper_script()

            written_content = mock_file().write.call_args[0][0]
            assert "unset PYTHONPATH" in written_content

    def test_wrapper_unsets_pythonhome(self):
        """Verify wrapper script unsets PYTHONHOME to prevent home directory conflicts."""
        from sbm.cli import _regenerate_wrapper_script

        with patch("pathlib.Path.open", mock_open()) as mock_file, \
             patch("os.chmod"), \
             patch("pathlib.Path.mkdir"):

            _regenerate_wrapper_script()

            written_content = mock_file().write.call_args[0][0]
            assert "unset PYTHONHOME" in written_content

    def test_wrapper_cleans_path(self):
        """Verify wrapper script removes other venv bin directories from PATH."""
        from sbm.cli import _regenerate_wrapper_script

        with patch("pathlib.Path.open", mock_open()) as mock_file, \
             patch("os.chmod"), \
             patch("pathlib.Path.mkdir"):

            _regenerate_wrapper_script()

            written_content = mock_file().write.call_args[0][0]
            # Should filter out .venv/bin directories and add auto-sbm's venv first
            assert "grep -v '/\\.venv/bin'" in written_content
            assert "export PATH=" in written_content

    def test_wrapper_uses_absolute_python_path(self):
        """Verify wrapper uses absolute path to auto-sbm's Python interpreter."""
        from sbm.cli import _regenerate_wrapper_script

        with patch("pathlib.Path.open", mock_open()) as mock_file, \
             patch("os.chmod"), \
             patch("pathlib.Path.mkdir"):

            _regenerate_wrapper_script()

            written_content = mock_file().write.call_args[0][0]
            # Should use full path to venv python, not rely on PATH
            assert "VENV_PYTHON=" in written_content
            assert ".venv/bin/python" in written_content
            assert '"$VENV_PYTHON" -m' in written_content


# =============================================================================
# TEST 2: Wrapper Script Generation
# =============================================================================


class TestWrapperScriptGeneration:
    """Tests for wrapper script generation and validation."""

    def test_regenerate_wrapper_creates_file(self):
        """Verify wrapper regeneration creates the wrapper file."""
        from sbm.cli import _regenerate_wrapper_script

        with patch("pathlib.Path.open", mock_open()) as mock_file, \
             patch("os.chmod") as mock_chmod, \
             patch("pathlib.Path.mkdir"):

            _regenerate_wrapper_script()

            # Verify file was opened for writing
            mock_file.assert_called_once()
            assert mock_file().write.called

    def test_regenerate_wrapper_sets_executable(self):
        """Verify wrapper script is made executable (chmod 755)."""
        from sbm.cli import _regenerate_wrapper_script

        with patch("pathlib.Path.open", mock_open()), \
             patch("os.chmod") as mock_chmod, \
             patch("pathlib.Path.mkdir"):

            _regenerate_wrapper_script()

            # Verify chmod was called with executable permissions (0o755)
            mock_chmod.assert_called_once()
            assert mock_chmod.call_args[0][1] == 0o755

    def test_regenerate_wrapper_creates_local_bin_dir(self):
        """Verify ~/.local/bin directory is created if it doesn't exist."""
        from sbm.cli import _regenerate_wrapper_script

        with patch("pathlib.Path.open", mock_open()), \
             patch("os.chmod"), \
             patch("pathlib.Path.mkdir") as mock_mkdir:

            _regenerate_wrapper_script()

            # Verify mkdir was called with parents=True and exist_ok=True
            mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    def test_regenerate_wrapper_uses_repo_root(self):
        """Verify wrapper uses REPO_ROOT for project path."""
        from sbm.cli import _regenerate_wrapper_script, REPO_ROOT

        with patch("pathlib.Path.open", mock_open()) as mock_file, \
             patch("os.chmod"), \
             patch("pathlib.Path.mkdir"):

            _regenerate_wrapper_script()

            written_content = mock_file().write.call_args[0][0]
            assert str(REPO_ROOT) in written_content

    def test_regenerate_wrapper_includes_health_check(self):
        """Verify wrapper includes import health check for critical modules."""
        from sbm.cli import _regenerate_wrapper_script

        with patch("pathlib.Path.open", mock_open()) as mock_file, \
             patch("os.chmod"), \
             patch("pathlib.Path.mkdir"):

            _regenerate_wrapper_script()

            written_content = mock_file().write.call_args[0][0]
            # Should check for critical imports
            assert "import pydantic, click, rich, colorama, sbm.cli" in written_content

    def test_regenerate_wrapper_handles_exceptions_gracefully(self):
        """Verify wrapper regeneration doesn't crash on errors."""
        from sbm.cli import _regenerate_wrapper_script

        with patch("pathlib.Path.open", side_effect=OSError("Permission denied")), \
             patch("sbm.cli.logger") as mock_logger:

            # Should not raise exception
            _regenerate_wrapper_script()

            # Should log debug message about failure
            assert mock_logger.debug.called


# =============================================================================
# TEST 3: Multi-Venv Compatibility
# =============================================================================


class TestMultiVenvCompatibility:
    """Tests for wrapper behavior when called from different virtual environments."""

    def test_wrapper_works_with_active_venv(self):
        """Verify wrapper can be called while another venv is active."""
        from sbm.cli import _regenerate_wrapper_script

        with patch("pathlib.Path.open", mock_open()) as mock_file, \
             patch("os.chmod"), \
             patch("pathlib.Path.mkdir"):

            _regenerate_wrapper_script()

            written_content = mock_file().write.call_args[0][0]

            # Wrapper should clean environment before executing
            # This ensures it works regardless of active venv
            assert "unset VIRTUAL_ENV" in written_content
            assert "unset PYTHONPATH" in written_content

    def test_wrapper_prioritizes_auto_sbm_venv_in_path(self):
        """Verify wrapper puts auto-sbm venv first in PATH."""
        from sbm.cli import _regenerate_wrapper_script

        with patch("pathlib.Path.open", mock_open()) as mock_file, \
             patch("os.chmod"), \
             patch("pathlib.Path.mkdir"):

            _regenerate_wrapper_script()

            written_content = mock_file().write.call_args[0][0]

            # Should export PATH with auto-sbm venv first
            assert "export PATH=" in written_content
            assert ".venv/bin:" in written_content

    def test_wrapper_filters_other_venv_from_path(self):
        """Verify wrapper removes other .venv/bin directories from PATH."""
        from sbm.cli import _regenerate_wrapper_script

        with patch("pathlib.Path.open", mock_open()) as mock_file, \
             patch("os.chmod"), \
             patch("pathlib.Path.mkdir"):

            _regenerate_wrapper_script()

            written_content = mock_file().write.call_args[0][0]

            # Should use grep to filter out .venv/bin paths
            assert "grep -v '/\\.venv/bin'" in written_content


# =============================================================================
# TEST 4: Wrapper Script Validation
# =============================================================================


class TestWrapperScriptValidation:
    """Tests for wrapper script validation and error handling."""

    def test_wrapper_validates_venv_python_exists(self):
        """Verify wrapper checks if venv Python interpreter exists."""
        from sbm.cli import _regenerate_wrapper_script

        with patch("pathlib.Path.open", mock_open()) as mock_file, \
             patch("os.chmod"), \
             patch("pathlib.Path.mkdir"):

            _regenerate_wrapper_script()

            written_content = mock_file().write.call_args[0][0]

            # Should check if VENV_PYTHON file exists
            assert '[ ! -f "$VENV_PYTHON" ]' in written_content

    def test_wrapper_validates_project_root_exists(self):
        """Verify wrapper checks if project root directory exists."""
        from sbm.cli import _regenerate_wrapper_script

        with patch("pathlib.Path.open", mock_open()) as mock_file, \
             patch("os.chmod"), \
             patch("pathlib.Path.mkdir"):

            _regenerate_wrapper_script()

            written_content = mock_file().write.call_args[0][0]

            # Should check if PROJECT_ROOT directory exists
            assert '[ ! -d "$PROJECT_ROOT" ]' in written_content

    def test_wrapper_changes_to_project_directory(self):
        """Verify wrapper changes to project directory before execution."""
        from sbm.cli import _regenerate_wrapper_script

        with patch("pathlib.Path.open", mock_open()) as mock_file, \
             patch("os.chmod"), \
             patch("pathlib.Path.mkdir"):

            _regenerate_wrapper_script()

            written_content = mock_file().write.call_args[0][0]

            # Should cd to PROJECT_ROOT
            assert 'cd "$PROJECT_ROOT"' in written_content

    def test_wrapper_provides_helpful_error_messages(self):
        """Verify wrapper provides clear error messages for common issues."""
        from sbm.cli import _regenerate_wrapper_script

        with patch("pathlib.Path.open", mock_open()) as mock_file, \
             patch("os.chmod"), \
             patch("pathlib.Path.mkdir"):

            _regenerate_wrapper_script()

            written_content = mock_file().write.call_args[0][0]

            # Should have user-friendly error messages
            assert "❌" in written_content  # Error indicator
            assert "🔧" in written_content  # Fix suggestion
            assert "bash setup.sh" in written_content  # Recovery instructions


# =============================================================================
# TEST 5: Wrapper Script Content Validation
# =============================================================================


class TestWrapperScriptContent:
    """Tests for specific content requirements in the wrapper script."""

    def test_wrapper_includes_shebang(self):
        """Verify wrapper script starts with proper shebang."""
        from sbm.cli import _regenerate_wrapper_script

        with patch("pathlib.Path.open", mock_open()) as mock_file, \
             patch("os.chmod"), \
             patch("pathlib.Path.mkdir"):

            _regenerate_wrapper_script()

            written_content = mock_file().write.call_args[0][0]
            assert written_content.startswith("#!/bin/bash")

    def test_wrapper_includes_version_comment(self):
        """Verify wrapper includes version information in comments."""
        from sbm.cli import _regenerate_wrapper_script

        with patch("pathlib.Path.open", mock_open()) as mock_file, \
             patch("os.chmod"), \
             patch("pathlib.Path.mkdir"):

            _regenerate_wrapper_script()

            written_content = mock_file().write.call_args[0][0]
            assert "auto-sbm v2.7.0" in written_content

    def test_wrapper_passes_all_arguments(self):
        """Verify wrapper passes all CLI arguments to sbm.cli module."""
        from sbm.cli import _regenerate_wrapper_script

        with patch("pathlib.Path.open", mock_open()) as mock_file, \
             patch("os.chmod"), \
             patch("pathlib.Path.mkdir"):

            _regenerate_wrapper_script()

            written_content = mock_file().write.call_args[0][0]
            # Should pass all arguments with "$@"
            assert '"$@"' in written_content

    def test_wrapper_uses_python_module_execution(self):
        """Verify wrapper executes sbm as a Python module (-m flag)."""
        from sbm.cli import _regenerate_wrapper_script

        with patch("pathlib.Path.open", mock_open()) as mock_file, \
             patch("os.chmod"), \
             patch("pathlib.Path.mkdir"):

            _regenerate_wrapper_script()

            written_content = mock_file().write.call_args[0][0]
            # Should use -m to execute as module
            assert '-m "$PROJECT_CLI_MODULE"' in written_content
            assert 'PROJECT_CLI_MODULE="sbm.cli"' in written_content
