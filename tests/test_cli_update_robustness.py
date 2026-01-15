import subprocess
from unittest.mock import MagicMock, patch, call, ANY
import pytest
from click.testing import CliRunner
from sbm.cli import cli, update


@pytest.fixture
def mock_subprocess():
    with patch("sbm.cli.subprocess.run") as mock:
        yield mock


@pytest.fixture
def mock_legacy_sync():
    with patch("sbm.utils.legacy_sync.sync_legacy_stats") as mock:
        yield mock


@pytest.fixture
def runner():
    return CliRunner()


def test_update_aborts_rebase(mock_subprocess, mock_legacy_sync, runner):
    """Verify that update attempts to abort a rebase if detected."""

    # Mock Path.exists to Simulate .git and rebase-merge existing
    # We patch sbm.cli.Path.exists because sbm.cli imports Path from pathlib
    # autospec=True ensures the mock receives 'self' when called on an instance
    with patch("sbm.cli.Path.exists", autospec=True) as mock_exists:

        def side_effect(self):
            s = str(self)
            print(f"DEBUG: Checking sbm.cli.Path.exists for {s}")
            if s.endswith(".git"):
                return True
            if s.endswith("rebase-merge") or s.endswith("rebase-apply"):
                return True
            return False

        mock_exists.side_effect = side_effect

        try:
            # We use catch_exceptions=False to let exceptions bubble up for debugging
            # But normally we might want to assert exit code.
            # If it crashes, we want to see why.
            result = runner.invoke(cli, ["update"], catch_exceptions=False)
        except Exception as e:
            print(f"DEBUG: Exception during invoke: {e}")
            import traceback

            traceback.print_exc()
            # If we catch it, result isn't created.
            # We should probably fail the test with the traceback.
            raise e

    print(f"DEBUG: Result exit code: {result.exit_code}")
    print(f"DEBUG: Output: {result.output}")
    print(f"DEBUG: Mock Subprocess calls: {mock_subprocess.call_args_list}")

    # Verify rebase --abort was called
    rebase_aborted = False
    for call_args in mock_subprocess.call_args_list:
        args, kwargs = call_args
        if args[0] == ["git", "rebase", "--abort"]:
            rebase_aborted = True
            assert kwargs.get("check") is False

    assert rebase_aborted, "git rebase --abort was not called"


def test_update_syncs_and_resets(mock_subprocess, mock_legacy_sync, runner):
    """Verify that update syncs legacy stats and checkouts archives."""
    # Setup mocks to bypass rebase check and git validation
    with patch("sbm.cli._validate_git_repository"), patch(
        "sbm.cli._get_current_branch", return_value="main"
    ), patch("sbm.cli.Path.exists", return_value=False), patch(
        "sbm.cli._stash_changes_if_needed", return_value=False
    ):
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = "new_hash"

        result = runner.invoke(cli, ["update"])

        # 1. Verify sync called
        mock_legacy_sync.assert_called_once()

        # 2. Verify checkout of stats/archive
        mock_subprocess.assert_any_call(
            ["git", "checkout", "stats/archive/"], check=False, cwd=ANY, capture_output=ANY
        )
