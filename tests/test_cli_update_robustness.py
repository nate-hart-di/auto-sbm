import subprocess
from unittest.mock import MagicMock, patch, call
import pytest
from click.testing import CliRunner
from sbm.cli import cli, update


@pytest.fixture
def mock_subprocess():
    with patch("sbm.cli.subprocess.run") as mock:
        yield mock


@pytest.fixture
def mock_legacy_sync():
    with patch("sbm.cli.sync_legacy_stats") as mock:
        yield mock


@pytest.fixture
def runner():
    return CliRunner()


def test_update_aborts_rebase(mock_subprocess, mock_legacy_sync, runner):
    """Verify that update attempts to abort a rebase if detected."""
    # Mock existence of rebase-merge directory
    with patch("pathlib.Path.exists") as mock_exists:
        # Sequence of exists calls: .git -> True, rebase-merge -> True
        def side_effect(self):
            if str(self).endswith(".git"):
                return True
            if str(self).endswith("rebase-merge"):
                return True
            return False

        mock_exists.side_effect = side_effect  # Note: this might be tricky to mock exact path logic

        # Simplified approach: Mock the specific check in the function if possible,
        # but since it uses REPO_ROOT / .git ... let's try to patch Path.exists globally carefully
        # or just trust the logic if we can mock the values it checks.

        # Actually, let's just patch the method in sbm.cli that does the check if we extracted it,
        # but we didn't.

        # Better: Mock Path objects logic directly in the module import context if possible,
        # or just rely on subprocess calls if we can trigger that path.

        # Let's try mocking the specific interaction.
        # The code checks: (git_dir / "rebase-merge").exists()

        with patch(
            "sbm.cli.Path.exists", side_effect=[True, True, True, True]
        ):  # git exists, rebase-merge exists
            result = runner.invoke(cli, ["update"])

        # Verify rebase --abort was called
        mock_subprocess.assert_any_call(
            ["git", "rebase", "--abort"], check=False, cwd=pytest.any, capture_output=True
        )


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
            ["git", "checkout", "stats/archive/"], check=False, cwd=pytest.any, capture_output=True
        )
