"""
Tests for stats accuracy (GitHub PR additions) and git retry resilience.

Covers:
- GitHub PR additions fetch replaces local SCSS line count
- commit_changes() returns False when git add fails
- checkout_main_and_pull() auto-stashes SBM dirty state
- post-migrate command records runs in stats
"""

import json
import subprocess
from unittest.mock import MagicMock, patch


class TestFetchPRAdditions:
    """Test fetching GitHub PR additions for accurate stats."""

    @patch("subprocess.run")
    def test_fetch_pr_additions_success(self, mock_run):
        """Verify fetch_pr_additions returns the additions count."""
        from sbm.utils.github_pr import fetch_pr_additions

        mock_run.return_value = MagicMock(
            stdout=json.dumps({"additions": 1234}),
            returncode=0,
        )

        result = fetch_pr_additions("https://github.com/org/repo/pull/42")
        assert result == 1234
        mock_run.assert_called_once()
        # Verify it called gh pr view with --json additions
        call_args = mock_run.call_args
        assert "gh" in call_args[0][0]
        assert "additions" in call_args[0][0]

    @patch("subprocess.run")
    def test_fetch_pr_additions_returns_none_on_failure(self, mock_run):
        """Verify fetch_pr_additions returns None when gh CLI fails."""
        from sbm.utils.github_pr import fetch_pr_additions

        mock_run.side_effect = subprocess.CalledProcessError(1, "gh")

        result = fetch_pr_additions("https://github.com/org/repo/pull/42")
        assert result is None

    @patch("subprocess.run")
    def test_fetch_pr_additions_returns_none_on_missing_field(self, mock_run):
        """Verify fetch_pr_additions returns None when additions field is missing."""
        from sbm.utils.github_pr import fetch_pr_additions

        mock_run.return_value = MagicMock(
            stdout=json.dumps({}),
            returncode=0,
        )

        result = fetch_pr_additions("https://github.com/org/repo/pull/42")
        assert result is None


class TestCreatePRIncludesAdditions:
    """Test that create_pr includes github_additions in its result."""

    @patch("sbm.core.git.GitOperations._open_pr_in_browser")
    @patch("sbm.core.git.GitOperations._copy_salesforce_message_to_clipboard")
    @patch("sbm.core.git.GitOperations._enable_auto_merge")
    @patch("sbm.utils.github_pr.GitHubPRManager.fetch_pr_additions", return_value=567)
    @patch(
        "sbm.utils.github_pr.GitHubPRManager.fetch_pr_metadata",
        return_value={
            "author": "testuser",
            "state": "OPEN",
            "created_at": "2026-01-01T00:00:00Z",
            "merged_at": None,
            "closed_at": None,
        },
    )
    @patch(
        "sbm.core.git.GitOperations._execute_gh_pr_create",
        return_value="https://github.com/org/repo/pull/99",
    )
    @patch("sbm.core.git.GitOperations._build_stellantis_pr_content")
    @patch("sbm.core.git.GitOperations._check_gh_cli", return_value=True)
    @patch("sbm.core.git.GitOperations._is_git_repo", return_value=True)
    @patch(
        "sbm.core.git.GitOperations._get_repo_info", return_value={"current_branch": "test-branch"}
    )
    def test_create_pr_result_includes_github_additions(
        self,
        mock_repo_info,
        mock_is_git,
        mock_check_gh,
        mock_build_content,
        mock_execute,
        mock_metadata,
        mock_additions,
        mock_auto_merge,
        mock_clipboard,
        mock_browser,
    ):
        """Verify create_pr result dict contains github_additions."""
        from sbm.config import Config
        from sbm.core.git import GitOperations

        mock_build_content.return_value = {
            "title": "test",
            "body": "test body",
            "what_section": "test what",
        }

        config = Config(
            {"default_branch": "main", "git": {"default_reviewers": [], "default_labels": []}}
        )
        git_ops = GitOperations(config)
        result = git_ops.create_pr(slug="test-theme")

        assert result["success"] is True
        assert result["github_additions"] == 567


class TestCommitChangesErrorHandling:
    """Test that commit_changes returns False when git add fails."""

    @patch("sbm.core.git.get_platform_dir", return_value="/fake/platform")
    @patch("sbm.core.git.get_dealer_theme_dir", return_value="/fake/platform/themes/test")
    @patch("sbm.core.git.execute_command")
    @patch("sbm.core.git.GitOperations._get_repo")
    def test_commit_changes_returns_false_on_add_failure(
        self,
        mock_get_repo,
        mock_execute,
        mock_theme_dir,
        mock_platform_dir,
    ):
        """Verify commit_changes returns False when git add fails."""
        from sbm.config import Config
        from sbm.core.git import GitOperations

        mock_repo = MagicMock()
        mock_get_repo.return_value = mock_repo

        # Simulate git add failure
        mock_execute.return_value = (False, "", "error adding files", 1)

        config = Config({})
        git_ops = GitOperations(config)
        result = git_ops.commit_changes("test-theme")

        assert result is False


class TestCheckoutMainAutoStash:
    """Test auto-stash behavior in checkout_main_and_pull."""

    @patch("sbm.core.git.GitOperations._get_repo")
    def test_auto_stash_on_sbm_branch(self, mock_get_repo):
        """Verify auto-stash when on an SBM branch with dirty state."""
        from sbm.config import Config
        from sbm.core.git import GitOperations

        mock_repo = MagicMock()
        mock_get_repo.return_value = mock_repo
        mock_repo.is_dirty.return_value = True
        mock_repo.active_branch.name = "pcon-999-testdealer-sbm0226"
        mock_repo.heads.main.checkout.return_value = None
        mock_repo.remotes.origin.pull.return_value = None

        config = Config({})
        git_ops = GitOperations(config)
        result = git_ops.checkout_main_and_pull()

        assert result is True
        mock_repo.git.stash.assert_called_once_with(
            "save", "--include-untracked", "SBM auto-stash: dirty state from previous migration"
        )

    @patch("sbm.core.git.GitOperations._get_repo")
    def test_auto_stash_on_sbm_files(self, mock_get_repo):
        """Verify auto-stash when dirty files are SBM artifacts."""
        from sbm.config import Config
        from sbm.core.git import GitOperations

        mock_repo = MagicMock()
        mock_get_repo.return_value = mock_repo
        mock_repo.is_dirty.return_value = True
        mock_repo.active_branch.name = "some-other-branch"

        # Simulate SBM files in diff
        mock_diff_item = MagicMock()
        mock_diff_item.a_path = "themes/dealer/sb-inside.scss"
        mock_repo.index.diff.return_value = [mock_diff_item]
        mock_repo.untracked_files = []
        mock_repo.heads.main.checkout.return_value = None
        mock_repo.remotes.origin.pull.return_value = None

        config = Config({})
        git_ops = GitOperations(config)
        result = git_ops.checkout_main_and_pull()

        assert result is True
        mock_repo.git.stash.assert_called_once_with(
            "save", "--include-untracked", "SBM auto-stash: dirty state from previous migration"
        )

    @patch("sbm.core.git.GitOperations._get_repo")
    def test_no_auto_stash_on_non_sbm_dirty(self, mock_get_repo):
        """Verify no auto-stash for non-SBM dirty state."""
        from sbm.config import Config
        from sbm.core.git import GitOperations

        mock_repo = MagicMock()
        mock_get_repo.return_value = mock_repo
        mock_repo.is_dirty.return_value = True
        mock_repo.active_branch.name = "feature/unrelated"

        # Non-SBM files
        mock_diff_item = MagicMock()
        mock_diff_item.a_path = "src/app.ts"
        mock_repo.index.diff.return_value = [mock_diff_item]
        mock_repo.untracked_files = []

        config = Config({})
        git_ops = GitOperations(config)
        result = git_ops.checkout_main_and_pull()

        assert result is False
        mock_repo.git.stash.assert_not_called()

    @patch("sbm.core.git.GitOperations._get_repo")
    def test_clean_working_tree_passes(self, mock_get_repo):
        """Verify clean working tree proceeds without stashing."""
        from sbm.config import Config
        from sbm.core.git import GitOperations

        mock_repo = MagicMock()
        mock_get_repo.return_value = mock_repo
        mock_repo.is_dirty.return_value = False
        mock_repo.heads.main.checkout.return_value = None
        mock_repo.remotes.origin.pull.return_value = None

        config = Config({})
        git_ops = GitOperations(config)
        result = git_ops.checkout_main_and_pull()

        assert result is True
        mock_repo.git.stash.assert_not_called()


class TestPostMigrateRecordsRun:
    """Test that post-migrate CLI command records runs."""

    @patch("sbm.cli.record_run")
    @patch("sbm.cli.record_migration")
    @patch("sbm.cli.run_post_migration_workflow")
    @patch("sbm.cli.Repo")
    @patch("sbm.cli.get_platform_dir", return_value="/fake/platform")
    def test_post_migrate_records_successful_run(
        self,
        mock_platform,
        mock_repo_cls,
        mock_workflow,
        mock_record_migration,
        mock_record_run,
    ):
        """Verify post_migrate calls record_run on success."""
        from click.testing import CliRunner

        from sbm.cli import cli

        mock_repo_cls.return_value.active_branch.name = "test-branch"
        mock_workflow.return_value = {
            "success": True,
            "pr_url": "https://github.com/org/repo/pull/1",
            "github_additions": 300,
            "pr_author": "testuser",
            "pr_state": "OPEN",
            "created_at": "2026-01-01T00:00:00Z",
            "merged_at": None,
            "closed_at": None,
        }

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "post-migrate",
                "test-theme",
                "--skip-review",
                "--skip-git-prompt",
                "--skip-pr-prompt",
            ],
        )

        # Should have called record_run
        mock_record_run.assert_called_once()
        call_kwargs = mock_record_run.call_args[1]
        assert call_kwargs["slug"] == "test-theme"
        assert call_kwargs["command"] == "post-migrate"
        assert call_kwargs["status"] == "success"
        assert call_kwargs["lines_migrated"] == 300
        assert call_kwargs["pr_url"] == "https://github.com/org/repo/pull/1"

        # Should have called record_migration
        mock_record_migration.assert_called_once_with("test-theme")
