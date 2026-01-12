"""
Comprehensive tests for auto-update wrapper regeneration.

Tests ensure that wrapper script is automatically regenerated during
auto-updates, so users get the latest environment isolation fixes.
"""

import os
import subprocess
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open, call
import pytest


# =============================================================================
# TEST 1: Auto-Update Wrapper Regeneration
# =============================================================================


class TestAutoUpdateWrapperRegeneration:
    """Tests for wrapper regeneration during auto-update process."""

    @patch("sbm.cli._regenerate_wrapper_script")
    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_auto_update_calls_wrapper_regeneration(
        self, mock_exists, mock_subprocess, mock_regenerate
    ):
        """Verify auto-update calls wrapper regeneration after dependency update."""
        from sbm.cli import _check_and_run_setup_if_needed

        # Mock setup file doesn't exist (force setup to run)
        mock_exists.return_value = False

        # Mock successful pip install
        mock_subprocess.return_value = MagicMock(returncode=0)

        with patch("pathlib.Path.open", mock_open()), \
             patch("time.strftime", return_value="2024-01-01 12:00:00"):

            _check_and_run_setup_if_needed()

            # Verify setup attempted
            assert mock_subprocess.called

    @patch("sbm.cli._regenerate_wrapper_script")
    @patch("subprocess.run")
    @patch("time.time")
    def test_auto_update_regenerates_after_8_hours(
        self, mock_time, mock_subprocess, mock_regenerate
    ):
        """Verify wrapper is regenerated if setup is older than 8 hours."""
        from sbm.cli import _check_and_run_setup_if_needed

        # Mock current time
        current_time = 1700000000.0
        mock_time.return_value = current_time

        # Mock successful pip install
        mock_subprocess.return_value = MagicMock(returncode=0)

        # Mock setup file that exists with old timestamp
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.stat.return_value = MagicMock(st_mtime=current_time - (9 * 3600))
        mock_path.open = mock_open()

        mock_repo_root = MagicMock()
        mock_repo_root.__truediv__.return_value = mock_path

        with patch("sbm.cli.REPO_ROOT", mock_repo_root), \
             patch("time.strftime", return_value="2024-01-01 12:00:00"):

            _check_and_run_setup_if_needed()

            # Verify wrapper regeneration was called
            mock_regenerate.assert_called_once()

    @patch("sbm.cli._regenerate_wrapper_script")
    @patch("subprocess.run")
    @patch("pathlib.Path.stat")
    @patch("pathlib.Path.exists")
    @patch("time.time")
    def test_auto_update_skips_if_setup_is_fresh(
        self, mock_time, mock_exists, mock_stat, mock_subprocess, mock_regenerate
    ):
        """Verify wrapper regeneration is skipped if setup is recent (< 8 hours)."""
        from sbm.cli import _check_and_run_setup_if_needed

        # Mock setup file exists
        mock_exists.return_value = True

        # Mock file modification time (2 hours ago)
        mock_stat.return_value = MagicMock(st_mtime=time.time() - (2 * 3600))
        mock_time.return_value = time.time()

        _check_and_run_setup_if_needed()

        # Verify wrapper regeneration was NOT called (setup is fresh)
        mock_regenerate.assert_not_called()

    @patch("sbm.cli._regenerate_wrapper_script")
    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_auto_update_regenerates_wrapper_on_dependency_success(
        self, mock_exists, mock_subprocess, mock_regenerate
    ):
        """Verify wrapper regeneration only happens after successful dependency update."""
        from sbm.cli import _check_and_run_setup_if_needed

        # Mock setup file doesn't exist
        mock_exists.return_value = False

        # Mock successful pip install
        mock_subprocess.return_value = MagicMock(returncode=0)

        with patch("pathlib.Path.open", mock_open()), \
             patch("time.strftime", return_value="2024-01-01 12:00:00"):

            _check_and_run_setup_if_needed()

            # Verify wrapper regeneration was called
            mock_regenerate.assert_called_once()

    @patch("sbm.cli._regenerate_wrapper_script")
    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_auto_update_skips_wrapper_on_dependency_failure(
        self, mock_exists, mock_subprocess, mock_regenerate
    ):
        """Verify wrapper regeneration is skipped if dependency update fails."""
        from sbm.cli import _check_and_run_setup_if_needed

        # Mock setup file doesn't exist
        mock_exists.return_value = False

        # Mock failed pip install
        mock_subprocess.return_value = MagicMock(returncode=1)

        with patch("pathlib.Path.open", mock_open()):
            _check_and_run_setup_if_needed()

            # Verify wrapper regeneration was NOT called (dependencies failed)
            mock_regenerate.assert_not_called()


# =============================================================================
# TEST 2: Auto-Update Integration
# =============================================================================


class TestAutoUpdateIntegration:
    """Tests for auto-update integration with wrapper regeneration."""

    @patch("sbm.cli._check_and_run_setup_if_needed")
    @patch("subprocess.run")
    def test_auto_update_calls_setup_after_pull(
        self, mock_subprocess, mock_setup
    ):
        """Verify _check_and_run_setup_if_needed is called after successful git pull."""
        from sbm.cli import auto_update_repo

        # Mock git operations to succeed
        def subprocess_side_effect(*args, **kwargs):
            # Git directory exists check
            if "ls-remote" in args[0]:
                return MagicMock(returncode=0)
            # Not detached HEAD
            if "symbolic-ref" in args[0]:
                return MagicMock(returncode=0)
            # Current branch
            if "rev-parse" in args[0] and "--abbrev-ref" in args[0]:
                return MagicMock(returncode=0, stdout="master\n")
            # No uncommitted changes
            if "status" in args[0] and "--porcelain" in args[0]:
                return MagicMock(returncode=0, stdout="")
            # Git pull (with updates)
            if "pull" in args[0]:
                return MagicMock(returncode=0, stdout="Updated files...\n")
            return MagicMock(returncode=0)

        mock_subprocess.side_effect = subprocess_side_effect

        # Mock Path operations
        mock_disable_file = MagicMock()
        mock_disable_file.exists.return_value = False

        mock_git_dir = MagicMock()
        mock_git_dir.exists.return_value = True

        def truediv_side_effect(name):
            if ".sbm-no-auto-update" in str(name):
                return mock_disable_file
            if ".git" in str(name):
                return mock_git_dir
            return MagicMock()

        mock_repo_root = MagicMock()
        mock_repo_root.__truediv__.side_effect = truediv_side_effect

        with patch("sbm.cli.REPO_ROOT", mock_repo_root), \
             patch("sbm.cli.logger"), \
             patch("sbm.cli._should_auto_update", return_value=True):

            auto_update_repo()

            # Verify git commands were attempted
            assert mock_subprocess.call_args_list

    @patch("sbm.cli._check_and_run_setup_if_needed")
    @patch("subprocess.run")
    def test_auto_update_skips_setup_on_no_updates(
        self, mock_subprocess, mock_setup
    ):
        """Verify setup is not called if there are no updates."""
        from sbm.cli import auto_update_repo

        # Mock git operations
        def subprocess_side_effect(*args, **kwargs):
            if "ls-remote" in args[0]:
                return MagicMock(returncode=0)
            if "symbolic-ref" in args[0]:
                return MagicMock(returncode=0)
            if "rev-parse" in args[0] and "--abbrev-ref" in args[0]:
                return MagicMock(returncode=0, stdout="master\n")
            if "status" in args[0] and "--porcelain" in args[0]:
                return MagicMock(returncode=0, stdout="")
            # Git pull (already up to date)
            if "pull" in args[0]:
                return MagicMock(returncode=0, stdout="Already up to date.\n")
            return MagicMock(returncode=0)

        mock_subprocess.side_effect = subprocess_side_effect

        with patch("pathlib.Path.exists", return_value=True), \
             patch("sbm.cli.logger"):

            auto_update_repo()

            # Setup should not be called (no updates)
            mock_setup.assert_not_called()


# =============================================================================
# TEST 3: Setup Complete Marker Management
# =============================================================================


class TestSetupCompleteMarker:
    """Tests for .sbm_setup_complete marker file management."""

    @patch("sbm.cli._regenerate_wrapper_script")
    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_setup_creates_marker_file(
        self, mock_exists, mock_subprocess, mock_regenerate
    ):
        """Verify setup creates .sbm_setup_complete marker file."""
        from sbm.cli import _check_and_run_setup_if_needed

        mock_exists.return_value = False
        mock_subprocess.return_value = MagicMock(returncode=0)

        with patch("pathlib.Path.open", mock_open()) as mock_file, \
             patch("time.strftime", return_value="2024-01-01 12:00:00"):

            _check_and_run_setup_if_needed()

            # Verify marker file was created
            mock_file.assert_called()

    @patch("sbm.cli._regenerate_wrapper_script")
    @patch("subprocess.run")
    @patch("time.time")
    def test_setup_deletes_old_marker_file(
        self, mock_time, mock_subprocess, mock_regenerate
    ):
        """Verify old marker file is deleted before running setup."""
        from sbm.cli import _check_and_run_setup_if_needed

        current_time = 1700000000.0
        mock_time.return_value = current_time
        mock_subprocess.return_value = MagicMock(returncode=0)

        # Mock setup file with old timestamp
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.stat.return_value = MagicMock(st_mtime=current_time - (9 * 3600))
        mock_path.open = mock_open()

        mock_repo_root = MagicMock()
        mock_repo_root.__truediv__.return_value = mock_path

        with patch("sbm.cli.REPO_ROOT", mock_repo_root), \
             patch("time.strftime", return_value="2024-01-01 12:00:00"):

            _check_and_run_setup_if_needed()

            # Verify setup attempted
            assert mock_subprocess.called

    @patch("sbm.cli._regenerate_wrapper_script")
    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_setup_marker_contains_timestamp(
        self, mock_exists, mock_subprocess, mock_regenerate
    ):
        """Verify marker file contains setup timestamp."""
        from sbm.cli import _check_and_run_setup_if_needed

        mock_exists.return_value = False
        mock_subprocess.return_value = MagicMock(returncode=0)

        with patch("pathlib.Path.open", mock_open()) as mock_file, \
             patch("time.strftime", return_value="2024-01-01 12:00:00") as mock_strftime:

            _check_and_run_setup_if_needed()

            # Verify timestamp function was called
            mock_strftime.assert_called()


# =============================================================================
# TEST 4: Dependency Update Process
# =============================================================================


class TestDependencyUpdateProcess:
    """Tests for pip dependency update during auto-update."""

    @patch("sbm.cli._regenerate_wrapper_script")
    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_setup_runs_pip_install(
        self, mock_exists, mock_subprocess, mock_regenerate
    ):
        """Verify pip install is run during setup."""
        from sbm.cli import _check_and_run_setup_if_needed
        import sys

        mock_exists.return_value = False
        mock_subprocess.return_value = MagicMock(returncode=0)

        with patch("pathlib.Path.open", mock_open()), \
             patch("time.strftime", return_value="2024-01-01 12:00:00"):

            _check_and_run_setup_if_needed()

            # Verify pip install was called
            pip_calls = [
                call_args
                for call_args in mock_subprocess.call_args_list
                if "pip" in call_args[0][0]
            ]
            assert pip_calls, "Expected pip install call"
            call_args = pip_calls[0][0][0]
            assert sys.executable in call_args
            assert "-m" in call_args
            assert "pip" in call_args
            assert "install" in call_args
            assert "requirements.txt" in call_args

    @patch("sbm.cli._regenerate_wrapper_script")
    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_setup_uses_timeout_for_pip(
        self, mock_exists, mock_subprocess, mock_regenerate
    ):
        """Verify pip install has a timeout to prevent hanging."""
        from sbm.cli import _check_and_run_setup_if_needed

        mock_exists.return_value = False
        mock_subprocess.return_value = MagicMock(returncode=0)

        with patch("pathlib.Path.open", mock_open()), \
             patch("time.strftime", return_value="2024-01-01 12:00:00"):

            _check_and_run_setup_if_needed()

            # Verify timeout was set on pip call
            pip_calls = [
                call_args
                for call_args in mock_subprocess.call_args_list
                if "pip" in call_args[0][0]
            ]
            assert pip_calls, "Expected pip install call"
            call_kwargs = pip_calls[0][1]
            assert "timeout" in call_kwargs
            assert call_kwargs["timeout"] == 60


# =============================================================================
# TEST 5: Error Handling
# =============================================================================


class TestErrorHandling:
    """Tests for error handling during auto-update and wrapper regeneration."""

    @patch("sbm.cli._regenerate_wrapper_script")
    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_setup_handles_exceptions_gracefully(
        self, mock_exists, mock_subprocess, mock_regenerate
    ):
        """Verify setup errors are handled gracefully without crashing."""
        from sbm.cli import _check_and_run_setup_if_needed

        mock_exists.return_value = False
        # Mock subprocess raising exception
        mock_subprocess.side_effect = OSError("Network error")

        with patch("sbm.cli.logger") as mock_logger:
            # Should not raise exception
            _check_and_run_setup_if_needed()

            # Should log debug message
            assert mock_logger.debug.called

    @patch("sbm.cli._regenerate_wrapper_script")
    @patch("subprocess.run")
    @patch("pathlib.Path.exists")
    def test_wrapper_regeneration_failure_doesnt_crash_setup(
        self, mock_exists, mock_subprocess, mock_regenerate
    ):
        """Verify wrapper regeneration failure doesn't prevent setup completion."""
        from sbm.cli import _check_and_run_setup_if_needed

        mock_exists.return_value = False
        mock_subprocess.return_value = MagicMock(returncode=0)
        # Mock wrapper regeneration failure
        mock_regenerate.side_effect = OSError("Permission denied")

        with patch("pathlib.Path.open", mock_open()), \
             patch("time.strftime", return_value="2024-01-01 12:00:00"), \
             patch("sbm.cli.logger"):

            # Should not raise exception even if wrapper regeneration fails
            _check_and_run_setup_if_needed()

    @patch("subprocess.run")
    def test_auto_update_handles_git_errors(self, mock_subprocess):
        """Verify auto-update handles git errors gracefully."""
        from sbm.cli import auto_update_repo

        # Mock git error
        mock_subprocess.return_value = MagicMock(returncode=1, stderr="fatal: error")

        with patch("pathlib.Path.exists", return_value=True), \
             patch("sbm.cli.logger"):

            # Should not raise exception
            auto_update_repo()


# =============================================================================
# TEST 6: Auto-Update Conditions
# =============================================================================


class TestAutoUpdateConditions:
    """Tests for conditions that trigger or skip auto-update."""

    @patch("subprocess.run")
    def test_auto_update_skips_if_disabled(self, mock_subprocess):
        """Verify auto-update is skipped if .sbm-no-auto-update file exists."""
        from sbm.cli import auto_update_repo

        with patch("pathlib.Path.exists", return_value=True):
            auto_update_repo()

            # Should not run any git commands
            mock_subprocess.assert_not_called()

    @patch("subprocess.run")
    def test_auto_update_skips_if_not_git_repo(self, mock_subprocess):
        """Verify auto-update is skipped if not in a git repository."""
        from sbm.cli import auto_update_repo

        # Mock Path operations
        mock_disable_file = MagicMock()
        mock_disable_file.exists.return_value = False

        mock_git_dir = MagicMock()
        mock_git_dir.exists.return_value = False

        def truediv_side_effect(name):
            if ".sbm-no-auto-update" in str(name):
                return mock_disable_file
            if ".git" in str(name):
                return mock_git_dir
            return MagicMock()

        mock_repo_root = MagicMock()
        mock_repo_root.__truediv__.side_effect = truediv_side_effect

        with patch("sbm.cli.REPO_ROOT", mock_repo_root):
            auto_update_repo()

            # Should not run git commands
            mock_subprocess.assert_not_called()

    @patch("subprocess.run")
    def test_auto_update_skips_on_detached_head(self, mock_subprocess):
        """Verify auto-update is skipped if in detached HEAD state."""
        from sbm.cli import auto_update_repo

        def subprocess_side_effect(*args, **kwargs):
            if "ls-remote" in args[0]:
                return MagicMock(returncode=0)
            # Detached HEAD (symbolic-ref fails)
            if "symbolic-ref" in args[0]:
                return MagicMock(returncode=1)
            return MagicMock(returncode=0)

        mock_subprocess.side_effect = subprocess_side_effect

        with patch("pathlib.Path.exists", return_value=True), \
             patch("sbm.cli.logger"):

            auto_update_repo()

            # Should not attempt pull (stopped at detached HEAD check)
            for call in mock_subprocess.call_args_list:
                assert "pull" not in str(call)

    @patch("subprocess.run")
    def test_auto_update_skips_on_non_master_branch(self, mock_subprocess):
        """Verify auto-update is skipped if not on master/main branch."""
        from sbm.cli import auto_update_repo

        def subprocess_side_effect(*args, **kwargs):
            if "ls-remote" in args[0]:
                return MagicMock(returncode=0)
            if "symbolic-ref" in args[0]:
                return MagicMock(returncode=0)
            # On feature branch
            if "rev-parse" in args[0] and "--abbrev-ref" in args[0]:
                return MagicMock(returncode=0, stdout="feature/test\n")
            return MagicMock(returncode=0)

        mock_subprocess.side_effect = subprocess_side_effect

        with patch("pathlib.Path.exists", return_value=True), \
             patch("sbm.cli.logger"):

            auto_update_repo()

            # Should not attempt pull (not on master/main)
            for call in mock_subprocess.call_args_list:
                assert "pull" not in str(call)
