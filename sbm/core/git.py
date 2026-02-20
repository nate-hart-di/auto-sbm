"""
Git operations for the SBM tool.

This module handles Git operations such as branch creation, commits, and pull requests
using the GitPython library for safer and more robust interactions.
"""

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from git import GitCommandError, Repo

from sbm.config import Config
from sbm.utils.command import execute_command
from sbm.utils.helpers import get_branch_name
from sbm.utils.logger import logger
from sbm.utils.path import get_dealer_theme_dir, get_platform_dir


class CommentIntelligence:
    """Intelligent comment analysis to understand change intent."""

    def __init__(self) -> None:
        self.intent_keywords = {
            "testing": ["testing", "test", "experiment", "trying", "trial"],
            "integration": ["adding", "integrating", "including", "importing", "merging"],
            "fixing": ["fix", "fixing", "repair", "correct", "resolve", "bug"],
            "enhancement": ["improve", "enhance", "optimize", "better", "upgrade"],
            "temporary": ["temp", "temporary", "quick", "hotfix", "placeholder"],
            "migration": ["migrat", "mov", "transfer", "port", "convert"],
            "customization": ["custom", "dealer", "brand", "specific", "override"],
        }

        self.automotive_terms = {
            "vdp": "Vehicle Detail Page",
            "vrp": "Vehicle Results Page",
            "inventory": "Inventory Management",
            "ctabox": "Call-to-Action Component",
            "premium-features": "Premium Feature Display",
            "incentives": "Vehicle Incentives",
            "badge": "Vehicle Badge/Award",
            "results-page": "Search Results Page",
        }

    def analyze_comment(self, comment_text: str) -> Dict[str, Any]:
        """Analyze a comment to extract intent, action, and target."""
        comment_lower = comment_text.lower().strip()

        # Remove comment markers
        comment_clean = re.sub(r"^//\s*|^/\*\s*|\s*\*/$", "", comment_lower).strip()

        analysis: Dict[str, Any] = {
            "raw_text": comment_text,
            "clean_text": comment_clean,
            "intent": None,
            "action": None,
            "target": None,
            "automotive_context": [],
            "confidence": 0.0,
            "description": None,
        }

        # Extract intent
        for intent_type, keywords in self.intent_keywords.items():
            if any(keyword in comment_clean for keyword in keywords):
                analysis["intent"] = intent_type
                break

        # Extract action words
        action_patterns = [
            r"\b(adding|integrating|including|importing)\b",
            r"\b(fixing|correcting|resolving)\b",
            r"\b(improving|enhancing|optimizing)\b",
            r"\b(testing|experimenting)\b",
        ]

        for pattern in action_patterns:
            match = re.search(pattern, comment_clean)
            if match:
                analysis["action"] = match.group(1)
                break

        # Extract automotive context
        automotive_context = analysis["automotive_context"]
        if isinstance(automotive_context, list):
            for term, description in self.automotive_terms.items():
                if term in comment_clean:
                    automotive_context.append({"term": term, "description": description})

        # Extract target (what's being modified)
        target_patterns = [
            r"(vdp|vrp)\.css",
            r"(vdp|vrp)\s+styles",
            r"#([\w-]+)",  # CSS IDs
            r"\.([\w-]+)",  # CSS classes
        ]

        for pattern in target_patterns:
            match = re.search(pattern, comment_clean)
            if match:
                analysis["target"] = match.group(1) if match.group(1) else match.group(0)
                break

        # Calculate confidence and generate description
        confidence = self._calculate_confidence(analysis)
        analysis["confidence"] = confidence
        if isinstance(confidence, float) and confidence > 0.5:
            analysis["description"] = self._generate_description(analysis)

        return analysis

    def _calculate_confidence(self, analysis: Dict[str, Any]) -> float:
        """Calculate confidence score for the analysis."""
        confidence = 0.0

        # Base confidence from having intent
        if analysis["intent"]:
            confidence += 0.3

        # Boost for having action
        if analysis["action"]:
            confidence += 0.2

        # Boost for automotive context
        if analysis["automotive_context"]:
            confidence += 0.3

        # Boost for having target
        if analysis["target"]:
            confidence += 0.2

        return min(confidence, 1.0)

    def _generate_description(self, analysis: Dict[str, Any]) -> str:
        """Generate human-readable description from analysis."""
        parts = []

        # Start with action if available
        if analysis["action"]:
            parts.append(analysis["action"].capitalize())
        else:
            parts.append("Modified")

        # Add target context
        if analysis["target"]:
            if analysis["automotive_context"]:
                # Use automotive context for better description
                auto_desc = analysis["automotive_context"][0]["description"]
                parts.append(f"{auto_desc.lower()} ({analysis['target']})")
            else:
                parts.append(f"styles for {analysis['target']}")
        elif analysis["automotive_context"]:
            auto_desc = analysis["automotive_context"][0]["description"]
            parts.append(f"{auto_desc.lower()} styles")

        # Add intent context
        if analysis["intent"] and analysis["intent"] != "customization":
            if analysis["intent"] == "testing":
                parts.append("for testing purposes")
            elif analysis["intent"] == "integration":
                parts.append("integration")
            elif analysis["intent"] == "fixing":
                parts.append("to resolve issues")

        return " ".join(parts)


class CSSIntelligence:
    """Intelligent CSS analysis to understand what selectors and properties do."""

    def __init__(self) -> None:
        self.selector_types = {
            # Page-specific selectors
            "#results-page": "Vehicle Results Page (VRP)",
            "#lvrp-results-wrapper": "Live Vehicle Results Page",
            "#ctabox-premium-features": "Premium Features CTA Component",
            "#header": "Site Header",
            "#footer": "Site Footer",
            # Component selectors
            ".vehicle-description-text": "Vehicle Description Content",
            ".features-link": "Feature Link Component",
            ".list-group-item": "List Item Component",
            ".incentives": "Vehicle Incentives Display",
            ".badge-row": "Vehicle Badge/Award Row",
            ".cookie-banner": "Cookie Consent Banner",
            ".navbar": "Navigation Menu",
            ".fat-footer": "Footer Content Area",
        }

        self.property_purposes = {
            "display": "visibility control",
            "position": "element positioning",
            "z-index": "layering/stacking order",
            "background": "background styling",
            "color": "text color",
            "border": "border styling",
            "padding": "internal spacing",
            "margin": "external spacing",
            "max-width": "responsive width control",
            "max-height": "height constraint",
            "overflow": "content overflow handling",
            "overflow-y": "content overflow handling",
        }

    def analyze_css_block(self, css_lines: List[str]) -> Dict[str, Any]:
        """Analyze a block of CSS changes."""
        analysis: Dict[str, Any] = {
            "selectors": [],
            "properties": [],
            "purposes": [],
            "component_type": None,
            "business_context": None,
            "confidence": 0.0,
        }

        # Extract selectors and properties
        for line in css_lines:
            line_clean = line.strip().lstrip("+").strip()

            # Extract CSS selectors
            selector_match = re.match(r"^([#\.\w\-\s\[\]:,>+~]+)\s*\{?", line_clean)
            if selector_match:
                selector = selector_match.group(1).strip()
                selectors = analysis["selectors"]
                if isinstance(selectors, list):
                    selectors.append(selector)

                # Check if we know this selector
                for known_selector, description in self.selector_types.items():
                    if known_selector in selector:
                        analysis["component_type"] = description
                        break

            # Extract CSS properties
            property_match = re.match(r"^([\w-]+)\s*:", line_clean)
            if property_match:
                prop = property_match.group(1)
                properties = analysis["properties"]
                purposes = analysis["purposes"]
                if isinstance(properties, list):
                    properties.append(prop)

                # Add purpose if we know it
                if prop in self.property_purposes and isinstance(purposes, list):
                    purpose = self.property_purposes[prop]
                    if purpose not in purposes:
                        purposes.append(purpose)

        # Calculate confidence
        analysis["confidence"] = self._calculate_css_confidence(analysis)

        return analysis

    def _calculate_css_confidence(self, analysis: Dict[str, Any]) -> float:
        """Calculate confidence for CSS analysis."""
        confidence = 0.0

        if analysis["component_type"]:
            confidence += 0.5

        if analysis["purposes"]:
            confidence += 0.3

        if analysis["selectors"]:
            confidence += 0.2

        return min(confidence, 1.0)


class GitOperations:
    """Handles Git operations for SBM migrations."""

    def __init__(self, config: Config) -> None:
        """Initialize GitOperations with configuration."""
        self.config = config

    def _get_repo(self) -> Repo:
        """Initializes and returns a GitPython Repo object."""
        platform_dir = get_platform_dir()
        return Repo(platform_dir)

    def _is_git_repo(self) -> bool:
        """Check if we're in a Git repository."""
        try:
            self._get_repo()
            return True
        except Exception:
            return False

    def _check_gh_cli(self) -> bool:
        """Check if GitHub CLI is available and authenticated."""
        try:
            subprocess.run(["gh", "--version"], check=True, capture_output=True)
            subprocess.run(["gh", "auth", "status"], check=True, capture_output=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def _get_repo_info(self) -> Dict[str, str]:
        """Get current repository information."""
        try:
            repo = self._get_repo()
            return {
                "current_branch": repo.active_branch.name,
                "remote_url": repo.remotes.origin.url if repo.remotes else "",
            }
        except Exception as e:
            logger.warning(f"Could not get repo info: {e}")
            return {}

    def _is_sbm_dirty_state(self, repo: Repo) -> bool:
        """Check if dirty working tree looks like a previous SBM migration."""
        try:
            # Check current branch name for SBM pattern
            branch = repo.active_branch.name
            if re.match(r"pcon-\d+-.*-sbm\d{4}$", branch):
                return True

            # Check if dirty files are SBM migration artifacts
            changed = [item.a_path for item in repo.index.diff(None)]
            untracked = repo.untracked_files
            all_files = changed + untracked
            sbm_patterns = ("sb-inside.scss", "sb-vdp.scss", "sb-vrp.scss", "sb-home.scss")
            if any(f.endswith(p) for f in all_files for p in sbm_patterns):
                return True
        except Exception:
            pass
        return False

    def checkout_main_and_pull(self) -> bool:
        """
        Checkout the main branch and pull the latest changes.

        If the working tree is dirty from a previous SBM migration,
        auto-stashes changes before proceeding.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info("Setting up clean main branch")
            repo = self._get_repo()

            if repo.is_dirty(untracked_files=True):
                if self._is_sbm_dirty_state(repo):
                    logger.warning(
                        "Dirty working tree from previous SBM migration detected. "
                        "Auto-stashing changes to proceed."
                    )
                    repo.git.stash("save", "--include-untracked", "SBM auto-stash: dirty state from previous migration")
                else:
                    logger.error(
                        "Working tree has uncommitted changes that don't appear to be "
                        "from SBM. Commit or stash them, or rerun with --skip-git."
                    )
                    return False

            repo.heads.main.checkout()
            logger.debug("Pulling latest changes from origin/main")
            repo.remotes.origin.pull()
            return True
        except GitCommandError as e:
            logger.error(f"Failed to checkout or pull main branch: {e}")
            return False

    def create_branch(self, slug: str) -> tuple:
        """
        Create a new branch for the migration.

        Args:
            slug (str): Dealer theme slug

        Returns:
            tuple: (success, branch_name) - a tuple containing success status and branch name
        """
        branch_name = get_branch_name(slug)
        try:
            logger.info(f"Creating new branch: {branch_name}")
            repo = self._get_repo()

            # If branch already exists locally, delete it
            if branch_name in repo.heads:
                logger.warning(
                    f"Local branch '{branch_name}' already exists. Deleting and re-creating it to ensure a clean state."
                )
                repo.delete_head(branch_name, force=True)

            # Check if remote branch exists and delete it too (equivalent to git push origin --delete [branch_name])
            try:
                # Fetch latest refs to ensure we have up-to-date remote branch info
                repo.remotes.origin.fetch()

                # Check if remote branch exists
                remote_branch_exists = False
                try:
                    remote_refs = [ref.name for ref in repo.remotes.origin.refs]
                    if f"origin/{branch_name}" in remote_refs:
                        remote_branch_exists = True
                except Exception:
                    # If we can't list remote refs, try deletion anyway (safer)
                    remote_branch_exists = True

                if remote_branch_exists:
                    logger.warning(
                        f"Remote branch 'origin/{branch_name}' exists. Deleting it to ensure clean state."
                    )
                    # Delete the remote branch (equivalent to: git push origin --delete [branch_name])
                    repo.remotes.origin.push(refspec=f":{branch_name}")
                    logger.info(f"Successfully deleted remote branch 'origin/{branch_name}'")
                else:
                    logger.debug(
                        f"Remote branch 'origin/{branch_name}' does not exist, no cleanup needed"
                    )

            except Exception as e:
                # Remote branch deletion failure is not critical - continue with local branch creation
                logger.debug(f"Could not delete remote branch 'origin/{branch_name}': {e}")

            # Create and checkout the new branch
            new_branch = repo.create_head(branch_name)
            new_branch.checkout()

            return True, branch_name
        except GitCommandError as e:
            logger.error(f"Failed to create branch '{branch_name}': {e}")
            return False, None

    def commit_changes(self, slug: str, message: Optional[str] = None) -> bool:
        """
        Commit changes to the dealer theme.

        Args:
            slug (str): Dealer theme slug
            message (str, optional): Commit message. If None, a default message is used.

        Returns:
            bool: True if successful, False otherwise
        """
        if message is None:
            message = f"SBM: Migrate {slug} to Site Builder format"

        try:
            logger.info(f"Committing changes for {slug}")
            repo = self._get_repo()

            # Path to the dealer theme relative to the repo root
            theme_path = os.path.relpath(get_dealer_theme_dir(slug), get_platform_dir())

            # Clean up any snapshot files that might have been created after the initial cleanup
            snapshot_dir = os.path.join(get_dealer_theme_dir(slug), ".sbm-snapshots")
            if os.path.exists(snapshot_dir):
                import shutil

                shutil.rmtree(snapshot_dir)
                logger.info(f"Cleaned up snapshot directory before commit: {snapshot_dir}")

            # Add specific files in the theme directory, excluding snapshots
            logger.info(f"Adding changes in {theme_path}")

            # Add changes in the theme directory
            # We add the entire theme directory to ensure all migrated files (SCSS, PHP partials, etc.) are included.
            # Snapshots are cleaned up before this step.
            add_command = f"git add {theme_path}"
            add_success, _, _, _ = execute_command(
                add_command, f"Failed to add changes in {theme_path}", cwd=get_platform_dir()
            )

            if not add_success:
                logger.error("Failed to add files to git")
                return False

            # Commit if there are changes to commit
            if repo.is_dirty(index=True):
                logger.info(f'Committing with message: "{message}"')
                commit_command = f'git commit -m "{message}"'
                commit_success, _, _, _ = execute_command(
                    commit_command, "Failed to commit changes", cwd=get_platform_dir()
                )
                return commit_success
            logger.info("No changes to commit.")
            return True  # Nothing to do is a success

        except GitCommandError as e:
            logger.error(f"Failed to commit changes for {slug}: {e}")
            return False

    def push_changes(self, branch_name: str) -> bool:
        """
        Push changes to the remote repository.

        Args:
            branch_name (str): Branch name to push

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info(f"Pushing changes to origin/{branch_name}")
            repo = self._get_repo()

            # First, try a normal push with upstream tracking
            push_info = repo.remotes.origin.push(
                refspec=f"{branch_name}:{branch_name}", set_upstream=True
            )

            # Check push results for any failures
            for info in push_info:
                if info.flags & info.ERROR or info.flags & info.REJECTED:
                    error_msg = info.summary or "Unknown push error"

                    # If it's a non-fast-forward error, try force-with-lease
                    if "non-fast-forward" in error_msg.lower() or "rejected" in error_msg.lower():
                        logger.warning(
                            f"Push rejected (non-fast-forward). Retrying with force-with-lease..."
                        )
                        try:
                            # Retry with force-with-lease to safely overwrite remote branch
                            push_info_retry = repo.remotes.origin.push(
                                refspec=f"{branch_name}:{branch_name}",
                                set_upstream=True,
                                force_with_lease=True,
                            )

                            # Check if the retry succeeded
                            retry_failed = False
                            for retry_info in push_info_retry:
                                if retry_info.flags & (retry_info.ERROR | retry_info.REJECTED):
                                    retry_failed = True
                                    break

                            if not retry_failed:
                                logger.info(
                                    f"Successfully pushed with force-with-lease to origin/{branch_name}"
                                )
                                return True
                            else:
                                logger.error(
                                    f"Force-with-lease push also failed for origin/{branch_name}"
                                )
                                return False
                        except Exception as retry_e:
                            logger.error(f"Force-with-lease push failed: {retry_e}")
                            return False
                    else:
                        logger.error(f"Failed to push changes to origin/{branch_name}: {error_msg}")
                        return False
                if info.flags & info.UP_TO_DATE:
                    logger.debug(f"Branch {branch_name} already up to date")

            return True
        except Exception as e:
            # Catch all exceptions, including GitCommandError and others
            logger.error(f"Failed to push changes to origin/{branch_name}: {e}")
            return False

    def _execute_gh_pr_create(
        self,
        title: str,
        body: str,
        base: str,
        head: str,
        draft: bool,
        reviewers: List[str],
        labels: List[str],
    ) -> str:
        """
        Creates GitHub PR using gh CLI with advanced error handling
        """
        cmd = [
            "gh",
            "pr",
            "create",
            "--title",
            title,
            "--body",
            body,
            "--base",
            base,
            "--head",
            head,
        ]
        if draft:
            cmd.append("--draft")
        if reviewers:
            cmd.extend(["--reviewer", ",".join(reviewers)])
        if labels:
            cmd.extend(["--label", ",".join(labels)])

        try:
            env = self._get_gh_env()

            result = subprocess.run(
                cmd, check=True, capture_output=True, text=True, cwd=get_platform_dir(), env=env
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            error_output = e.stderr if e.stderr else str(e)
            if self._is_pr_exists_error(error_output):
                return self._handle_existing_pr(error_output, head)
            msg = f"GitHub CLI error: {error_output}"
            raise Exception(msg)

    def _is_pr_exists_error(self, error_output: str) -> bool:
        """Checks if the error output indicates that a PR already exists."""
        return (
            "already exists" in error_output.lower()
            or "pull request for branch" in error_output.lower()
        )

    def _get_gh_env(self) -> Dict[str, str]:
        """Get environment with GitHub token configured."""
        env = os.environ.copy()

        # Check for custom GitHub token in config
        if hasattr(self.config, "github_token") and self.config.github_token:
            env["GH_TOKEN"] = self.config.github_token
            logger.debug("Using custom GitHub token from config")
        elif hasattr(self.config, "git") and self.config.git:
            git_config = self.config.git
            if isinstance(git_config, dict) and "github_token" in git_config:
                env["GH_TOKEN"] = git_config["github_token"]
                logger.debug("Using custom GitHub token from git config")
            elif hasattr(git_config, "github_token") and git_config.github_token:
                env["GH_TOKEN"] = git_config.github_token
                logger.debug("Using custom GitHub token from git config")

        return env

    def _handle_existing_pr(self, error_output: str, head_branch: str) -> str:
        """Extracts the existing PR URL from the error output or by listing PRs."""
        # Try to extract PR URL from error message
        url_match = re.search(r"(https://github\.com/[^\s\n]+)", error_output)
        if url_match:
            return url_match.group(1)
        # Fallback to gh pr list
        try:
            env = self._get_gh_env()

            list_result = subprocess.run(
                ["gh", "pr", "list", "--head", head_branch, "--json", "url"],
                capture_output=True,
                text=True,
                check=True,
                cwd=get_platform_dir(),
                env=env,
            )
            pr_data = json.loads(list_result.stdout)
            if pr_data and len(pr_data) > 0:
                return pr_data[0]["url"]
        except Exception as list_e:
            logger.warning(f"Could not list existing PRs: {list_e}")
        msg = f"PR already exists but could not retrieve URL: {error_output}"
        raise Exception(msg)

    def _check_pr_merge_status(self, pr_url: str) -> Dict[str, Any]:
        """
        Check why a PR might not be auto-merging.

        Returns:
            dict with mergeable state, required checks, and blocking reasons
        """
        try:
            env = self._get_gh_env()

            result = subprocess.run(
                [
                    "gh",
                    "pr",
                    "view",
                    pr_url,
                    "--json",
                    "mergeable,mergeStateStatus,statusCheckRollup,reviewDecision",
                ],
                capture_output=True,
                text=True,
                check=True,
                cwd=get_platform_dir(),
                env=env,
            )

            data = json.loads(result.stdout)

            # Parse status checks
            status_checks = data.get("statusCheckRollup", [])
            failing_checks = [
                check["name"]
                for check in status_checks
                if check.get("conclusion") not in ["SUCCESS", "NEUTRAL", "SKIPPED", None]
            ]
            pending_checks = [
                check["name"] for check in status_checks if check.get("state") == "PENDING"
            ]

            return {
                "mergeable": data.get("mergeable"),
                "merge_state": data.get("mergeStateStatus"),
                "review_decision": data.get("reviewDecision"),
                "failing_checks": failing_checks,
                "pending_checks": pending_checks,
            }

        except Exception as e:
            logger.debug(f"Could not check PR merge status: {e}")
            return {}

    def _update_branch(self, pr_url: str) -> bool:
        """
        Update PR branch to be current with base branch.

        Returns:
            bool: True if branch was updated successfully
        """
        try:
            env = self._get_gh_env()

            # Check if branch needs updating first
            result = subprocess.run(
                ["gh", "pr", "view", pr_url, "--json", "mergeStateStatus"],
                capture_output=True,
                text=True,
                check=True,
                cwd=get_platform_dir(),
                env=env,
            )

            data = json.loads(result.stdout)
            merge_state = data.get("mergeStateStatus")

            # BEHIND means branch is behind base, DIRTY means behind and has conflicts
            if merge_state in ["BEHIND", "DIRTY"]:
                logger.info("🔄 Updating branch to be current with base...")

                # Update the branch using gh pr
                subprocess.run(
                    ["gh", "pr", "merge", pr_url, "--update-branch"],
                    check=True,
                    capture_output=True,
                    text=True,
                    cwd=get_platform_dir(),
                    env=env,
                    timeout=30,
                )

                logger.info("✓ Branch updated successfully")
                return True
            else:
                logger.debug(f"Branch already up-to-date (state: {merge_state})")
                return True

        except subprocess.TimeoutExpired:
            logger.warning("⚠ Branch update timed out - may complete in background")
            return False
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if e.stderr else str(e)
            # Don't fail on certain expected errors
            if "already up to date" in error_msg.lower():
                logger.debug("Branch already up-to-date")
                return True
            elif "cannot update" in error_msg.lower():
                logger.warning(f"⚠ Cannot update branch: {error_msg}")
                return False
            else:
                logger.warning(f"Could not update branch: {error_msg}")
                return False

    def _enable_auto_merge(self, pr_url: str) -> bool:
        """
        Enable auto-merge on a PR with squash strategy.
        Updates branch first if needed.

        Returns:
            bool: True if auto-merge was enabled successfully
        """
        try:
            env = self._get_gh_env()

            # First, try to update the branch if it's behind
            self._update_branch(pr_url)

            # Enable auto-merge with squash
            subprocess.run(
                ["gh", "pr", "merge", pr_url, "--auto", "--squash"],
                check=True,
                capture_output=True,
                text=True,
                cwd=get_platform_dir(),
                env=env,
            )

            logger.info("✓ Auto-merge enabled (squash strategy)")

            # Check merge status to diagnose potential blocking issues
            status = self._check_pr_merge_status(pr_url)
            if status:
                # Log diagnostics about why it might not merge immediately
                if status.get("mergeable") == "CONFLICTING":
                    logger.warning("⚠ PR has merge conflicts - auto-merge will wait for resolution")
                elif status.get("pending_checks"):
                    logger.info(
                        f"⏳ Auto-merge waiting for checks: {', '.join(status['pending_checks'])}"
                    )
                elif status.get("failing_checks"):
                    logger.warning(
                        f"⚠ Auto-merge blocked by failing checks: {', '.join(status['failing_checks'])}"
                    )
                elif status.get("review_decision") == "REVIEW_REQUIRED":
                    logger.info("⏳ Auto-merge waiting for required reviews")
                elif status.get("review_decision") == "CHANGES_REQUESTED":
                    logger.warning("⚠ Auto-merge blocked - changes requested in review")
                elif status.get("merge_state") == "BLOCKED":
                    logger.warning("⚠ Auto-merge blocked by branch protection rules")
                else:
                    logger.info("✓ PR ready to auto-merge when checks pass")

            return True

        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if e.stderr else str(e)
            logger.warning(f"Could not enable auto-merge: {error_msg}")
            return False

    def _analyze_migration_changes(self) -> List[str]:
        """Analyze Git changes to determine what was actually migrated."""
        what_items = []

        try:
            # Get the diff between current branch and main
            result = subprocess.run(
                ["git", "diff", "--name-status", "main...HEAD"],
                capture_output=True,
                text=True,
                check=True,
                cwd=get_platform_dir(),
            )

            changed_files = result.stdout.strip().split("\n") if result.stdout.strip() else []

            # Parse the git diff output (format: "A\tfilename" or "M\tfilename")
            added_files = []
            modified_files = []

            for line in changed_files:
                if not line.strip():
                    continue
                parts = line.split("\t", 1)
                if len(parts) == 2:
                    status, filepath = parts
                    if status == "A":
                        added_files.append(filepath)
                    elif status == "M":
                        modified_files.append(filepath)

            # Analyze what was actually migrated based on file changes
            # Filter for SCSS files and extract just the filename for easier matching
            css_files = []
            for f in added_files + modified_files:
                if f.endswith(".scss") and ("css/" in f or f.endswith(".scss")):
                    # Extract just the filename for easier matching
                    filename = os.path.basename(f)
                    css_files.append(filename)

            logger.debug(f"Found changed SCSS files: {css_files}")

            # Check for sb-inside.scss creation/modification
            if "sb-inside.scss" in css_files:
                # Check what source files exist to be more specific
                source_files = []
                current_dir = Path.cwd()
                if (current_dir / "css" / "style.scss").exists():
                    source_files.append("style.scss")
                if (current_dir / "css" / "inside.scss").exists():
                    source_files.append("inside.scss")
                if (current_dir / "css" / "_support-requests.scss").exists():
                    source_files.append("_support-requests.scss")

                if source_files:
                    source_text = " and ".join(source_files)
                    what_items.append(
                        f"- Migrated interior page styles from {source_text} to sb-inside.scss"
                    )
                else:
                    what_items.append("- Created sb-inside.scss for interior page styles")

            # Check for VDP migration (only from lvdp.scss)
            if "sb-vdp.scss" in css_files:
                if (Path.cwd() / "css" / "lvdp.scss").exists():
                    what_items.append("- Migrated VDP styles from lvdp.scss to sb-vdp.scss")
                else:
                    what_items.append("- Created sb-vdp.scss for VDP styles")

            # Check for VRP migration (only from lvrp.scss)
            if "sb-vrp.scss" in css_files:
                if (Path.cwd() / "css" / "lvrp.scss").exists():
                    what_items.append("- Migrated VRP styles from lvrp.scss to sb-vrp.scss")
                else:
                    what_items.append("- Created sb-vrp.scss for VRP styles")

            # Check for home page migration
            if "sb-home.scss" in css_files:
                what_items.append("- Created sb-home.scss for home page styles")

            logger.debug(
                f"Analyzed {len(css_files)} CSS file changes, generated {len(what_items)} what items"
            )

        except subprocess.CalledProcessError as e:
            logger.warning(f"Could not analyze Git changes: {e}")
        except Exception as e:
            logger.warning(f"Error analyzing migration changes: {e}")

        return what_items

    def _detect_manual_changes(self) -> Dict[str, Any]:
        """
        Detect manual changes by comparing current files with automation snapshots.
        """
        manual_changes = {
            "has_manual_changes": False,
            "change_descriptions": [],
            "files_modified": [],
            "estimated_manual_lines": 0,
            "added_lines": [],
            "file_line_counts": {},  # Track lines per file
        }

        try:
            # Get current working directory to find theme
            current_dir = Path.cwd()

            # Look for snapshots directory
            snapshot_dir = current_dir / ".sbm-snapshots"
            if not snapshot_dir.exists():
                logger.debug("No snapshot directory found, falling back to git diff method")
                return self._detect_manual_changes_fallback()

            # Check each snapshot file against current file
            migration_files = ["sb-inside.scss", "sb-vdp.scss", "sb-vrp.scss", "sb-home.scss"]

            for sb_file in migration_files:
                snapshot_file = snapshot_dir / f"{sb_file}.automated"
                current_file = current_dir / sb_file

                if snapshot_file.exists() and current_file.exists():
                    # Read both files
                    snapshot_content = snapshot_file.read_text()
                    current_content = current_file.read_text()

                    # Compare content
                    if snapshot_content != current_content:
                        # Calculate line differences
                        snapshot_lines = snapshot_content.splitlines()
                        current_lines = current_content.splitlines()

                        # Simple line count difference (could be more sophisticated)
                        line_diff = len(current_lines) - len(snapshot_lines)

                        if line_diff != 0:
                            manual_changes["has_manual_changes"] = True
                            file_line_counts = manual_changes.get("file_line_counts", {})
                            files_modified = manual_changes.get("files_modified", [])
                            change_descriptions = manual_changes.get("change_descriptions", [])

                            if isinstance(file_line_counts, dict):
                                file_line_counts[sb_file] = abs(line_diff)
                            if isinstance(files_modified, list):
                                files_modified.append(sb_file)

                            # Create description
                            if isinstance(change_descriptions, list):
                                if line_diff > 0:
                                    change_descriptions.append(
                                        f"Manual changes to {sb_file} ({line_diff} lines added) - please add details if needed"
                                    )
                                else:
                                    change_descriptions.append(
                                        f"Manual changes to {sb_file} ({abs(line_diff)} lines removed) - please add details if needed"
                                    )

            # Calculate total manual lines
            file_line_counts = manual_changes.get("file_line_counts", {})
            if isinstance(file_line_counts, dict):
                manual_changes["estimated_manual_lines"] = sum(file_line_counts.values())

            logger.debug(
                f"Snapshot comparison found {manual_changes['estimated_manual_lines']} manual lines"
            )

        except Exception as e:
            logger.debug(f"Error in snapshot-based manual change detection: {e}")
            return self._detect_manual_changes_fallback()

        return manual_changes

    def _detect_manual_changes_fallback(self) -> Dict[str, Any]:
        """
        Simple, honest detection of manual changes - just count lines and let user explain.
        """
        manual_changes = {
            "has_manual_changes": False,
            "change_descriptions": [],
            "files_modified": [],
            "estimated_manual_lines": 0,
            "added_lines": [],
            "file_line_counts": {},  # Track lines per file
        }

        try:
            # Get detailed diff content to analyze
            result = subprocess.run(
                ["git", "diff", "--unified=3", "main...HEAD"],
                capture_output=True,
                text=True,
                check=True,
                cwd=get_platform_dir(),
            )

            diff_content = result.stdout
            if not diff_content.strip():
                return manual_changes

            lines = diff_content.split("\n")
            added_lines = [
                line for line in lines if line.startswith("+") and not line.startswith("+++")
            ]
            manual_changes["added_lines"] = added_lines

            if not added_lines:
                return manual_changes

            # Get list of files that were changed
            file_result = subprocess.run(
                ["git", "diff", "--name-status", "main...HEAD"],
                capture_output=True,
                text=True,
                check=True,
                cwd=get_platform_dir(),
            )

            changed_files = (
                file_result.stdout.strip().split("\n") if file_result.stdout.strip() else []
            )

            # Check if files are newly created (A) vs modified (M)
            new_files = []
            modified_files = []

            for line in changed_files:
                if not line.strip():
                    continue
                parts = line.split("\t", 1)
                if len(parts) == 2:
                    status, filepath = parts
                    filename = os.path.basename(filepath)
                    if filename.endswith(".scss"):
                        if status == "A":
                            new_files.append(filename)
                        elif status == "M":
                            modified_files.append(filename)

            # Only count modifications to existing files as potential manual changes
            # New files created by migration (sb-*.scss) should not be counted as manual
            migration_files = {"sb-inside.scss", "sb-vdp.scss", "sb-vrp.scss", "sb-home.scss"}

            # Count manual lines per file - only for modified existing files or new non-migration files
            current_file = None
            for line in lines:
                # Track which file we're in
                if line.startswith("+++"):
                    file_match = re.search(r"\+\+\+ b/(.+)", line)
                    if file_match:
                        current_file = os.path.basename(file_match.group(1))
                        if current_file.endswith(".scss"):
                            # Only initialize count for files that aren't migration files
                            # Exclude ALL migration files regardless of git status (A or M)
                            if current_file not in migration_files:
                                file_line_counts = manual_changes.get("file_line_counts", {})
                                if isinstance(file_line_counts, dict):
                                    file_line_counts[current_file] = 0

                # Count added lines for current file (only if it's not a migration file)
                elif line.startswith("+") and current_file and current_file.endswith(".scss"):
                    file_line_counts = manual_changes.get("file_line_counts", {})
                    if isinstance(file_line_counts, dict) and current_file in file_line_counts:
                        file_line_counts[current_file] += 1

            # Calculate totals
            file_line_counts = manual_changes.get("file_line_counts", {})
            total_manual_lines = (
                sum(file_line_counts.values()) if isinstance(file_line_counts, dict) else 0
            )
            if total_manual_lines > 0:
                manual_changes["has_manual_changes"] = True
                manual_changes["estimated_manual_lines"] = total_manual_lines

                # Generate simple descriptions based on line counts
                change_descriptions = manual_changes.get("change_descriptions", [])
                if isinstance(file_line_counts, dict) and isinstance(change_descriptions, list):
                    for filename, line_count in file_line_counts.items():
                        if line_count > 0:
                            change_descriptions.append(
                                f"Manual changes to {filename} ({line_count} lines) - please add details if needed"
                            )

            # Only include modified files in the list, excluding ALL migration files
            manual_changes["files_modified"] = [
                filename
                for filename in modified_files
                if filename.endswith(".scss") and filename not in migration_files
            ]

        except subprocess.CalledProcessError as e:
            logger.debug(f"Could not analyze manual changes: {e}")
        except Exception as e:
            logger.debug(f"Error detecting manual changes: {e}")

        return manual_changes

    def _analyze_change_types(self, added_lines: List[str], manual_changes: Dict[str, Any]) -> None:
        """Analyze the types of changes made in the added lines."""
        change_patterns = {
            "custom_comments": r"\/\*.*(?:custom|manual|added|fix|tweak|adjust).*\*\/",
            "media_queries": r"@media.*\(",
            "pseudo_selectors": r":(?:hover|focus|active|before|after)",
            "custom_classes": r"\.(?:custom|manual|fix|temp|override)-",
            "brand_specific": r"(?:brand-specific|dealer-custom)",
            "important_overrides": r"!important",
            "z_index_adjustments": r"z-index:\s*\d+",
            "position_fixes": r"position:\s*(?:absolute|relative|fixed)",
            "color_customizations": r"(?:color|background).*#[0-9a-fA-F]{3,6}",
            "spacing_tweaks": r"(?:margin|padding).*(?:\d+px|\d+rem|\d+em)",
        }

        for line in added_lines:
            for change_type, pattern in change_patterns.items():
                if re.search(pattern, line, re.IGNORECASE):
                    if change_type not in manual_changes["change_types"]:
                        manual_changes["change_types"].append(change_type)

    def _generate_change_descriptions(self, manual_changes: Dict[str, Any]) -> List[str]:
        """Generate human-readable descriptions of the changes - ONLY for clear, specific changes."""
        type_descriptions = {
            "custom_comments": "Added explanatory comments for custom modifications",
            "custom_classes": "Created custom CSS classes for specific styling needs",
            "brand_specific": "Implemented brand-specific customizations",
            "important_overrides": "Added CSS !important overrides for specificity",
            "z_index_adjustments": "Fixed layering issues with z-index adjustments",
            "position_fixes": "Corrected element positioning",
            # REMOVED: Generic template descriptions that don't provide meaningful information:
            # - 'media_queries': 'Enhanced responsive design with custom media queries'
            # - 'pseudo_selectors': 'Improved interactive states (hover, focus, etc.)'
            # - 'color_customizations': 'Applied custom color schemes'
            # - 'spacing_tweaks': 'Fine-tuned spacing and layout'
        }

        descriptions = []
        for change_type in manual_changes["change_types"]:
            if change_type in type_descriptions:
                descriptions.append(type_descriptions[change_type])

        return descriptions

    def _build_stellantis_pr_content(
        self, slug: str, branch: str, repo_info: Dict[str, str]
    ) -> Dict[str, str]:
        """Build PR content using Stellantis template with dynamic What section based on actual Git changes."""
        # All Site Builder migrations use PCON-864
        title = f"PCON-864: {slug} SBM FE Audit"

        # Get automated migration changes
        automated_items = self._analyze_migration_changes()

        # Detect manual changes using git diff analysis
        manual_analysis = self._detect_manual_changes()

        # Build the what section
        what_items = []

        # Add automated changes
        if automated_items:
            what_items.extend(automated_items)
        else:
            # Fallback if no changes detected
            what_items.append(
                "- Migrated interior page styles from style.scss, inside.scss, and _support-requests.scss to sb-inside.scss"
            )

        # Add manual changes ONLY if they exist - with intelligent analysis
        if manual_analysis["has_manual_changes"]:
            if manual_analysis["change_descriptions"]:
                # We have clear, identifiable changes - add specific descriptions
                for description in manual_analysis["change_descriptions"]:
                    what_items.append(f"- {description}")
            else:
                # Manual changes detected but unclear what they are - prompt for details
                manual_lines = manual_analysis.get("estimated_manual_lines", 0)
                if manual_lines > 0:
                    what_items.append(
                        f"- Manual modifications added ({manual_lines} lines) - details need review"
                    )

        # Add OEM-specific items based on actual OEM handler (not just slug matching)
        try:
            from sbm.oem.factory import OEMFactory
            from sbm.oem.stellantis import StellantisHandler

            handler = OEMFactory.detect_from_theme(slug)

            if automated_items and isinstance(handler, StellantisHandler):
                what_items.append("- Added Stellantis Direction Row Styles")
                what_items.append("- Added Stellantis Cookie Banner styles")
        except Exception as e:
            logger.debug(f"Could not determine OEM for PR description: {e}")

        # Add map migration details if present
        try:
            from sbm.core.maps import get_map_report

            map_report = get_map_report(slug)
            if map_report:
                shortcodes = map_report.get("shortcodes_found")
                imports = map_report.get("imports_found")
                scss_targets = map_report.get("scss_targets") or []
                partials_copied = map_report.get("partials_copied") or []
                skipped_reason = map_report.get("skipped_reason")

                if not shortcodes:
                    if imports:
                        what_items.append(
                            "- Map components: CommonTheme map references present but no map shortcodes/template usage; migration skipped."
                        )
                    else:
                        what_items.append(
                            "- Map components: No map shortcodes detected; migration skipped."
                        )
                elif not scss_targets and not partials_copied and skipped_reason != "already_present":
                    what_items.append(
                        "- Map components: Map components detected but no CommonTheme map assets found; migration skipped."
                    )
                else:
                    # If strictly skipped because already present (complete success without changes), suppress note
                    if skipped_reason == "already_present":
                        pass
                    else:
                        parts = []
                        if scss_targets:
                            parts.append(f"SCSS appended to {', '.join(sorted(scss_targets))}")
                        if partials_copied:
                            # Verify if partials were actually added to git
                            repo_root = get_platform_dir()
                            theme_rel = os.path.relpath(get_dealer_theme_dir(slug), repo_root)

                            valid_partials = []
                            for p in sorted(set(partials_copied)):
                                # Partial path is like 'partials/map-row'
                                # Check if the corresponding .php file is in the git index
                                rel_file = os.path.join(theme_rel, f"{p}.php")
                                try:
                                    # Use git ls-files to verify the file is tracked and modified/added
                                    ls_result = subprocess.run(
                                        ["git", "ls-files", "--error-unmatch", rel_file],
                                        cwd=repo_root,
                                        capture_output=True,
                                        text=True,
                                    )
                                    if ls_result.returncode == 0:
                                        valid_partials.append(p)
                                    else:
                                        logger.debug(
                                            f"Partial {p} not found in git index, omitting from PR"
                                        )
                                except Exception:
                                    pass

                            if valid_partials:
                                parts.append(f"Partials copied {', '.join(valid_partials)}")
                        if parts:
                            detail = "; ".join(parts)
                            what_items.append(f"- Map components: {detail}")
                        elif skipped_reason == "migration_issue":
                            what_items.append(
                                "- Map components: Migration issue detected (check logs)"
                            )
                        # If everything was already present, we PASS and hide the line completely.
        except Exception as e:
            logger.debug(f"Could not add map migration details to PR: {e}")

        what_section = "\n".join(what_items)

        # Build the body using the original clean format
        body = f"""## What

{what_section}

## Why

Site Builder Migration

## Instructions for Reviewers

Within the di-websites-platform directory:

```bash
git checkout main
git pull
git checkout {branch}
just start {slug}
```

- Review all code found in "Files Changed"
- Open up a browser, go to localhost
- Verify that homepage and interior pages load properly
- Request changes as needed"""

        return {"title": title, "body": body, "what_section": what_section}

    def _open_pr_in_browser(self, pr_url: str) -> None:
        """Open PR URL in browser."""
        try:
            subprocess.run(["open", pr_url], check=True)
            logger.info(f"Opened PR in browser: {pr_url}")
        except subprocess.CalledProcessError:
            logger.warning(f"Could not open PR in browser. URL: {pr_url}")

    def _copy_salesforce_message_to_clipboard(self, what_section: str, pr_url: str) -> None:
        """Copy Salesforce message to clipboard."""
        try:
            salesforce_message = f"""FED Site Builder Migration Complete:

{what_section}

PR: {pr_url}"""

            # Use pbcopy on macOS
            subprocess.run(["pbcopy"], input=salesforce_message.encode(), check=True)
            logger.info("Copied Salesforce update to clipboard")
        except subprocess.CalledProcessError:
            logger.warning("Could not copy message to clipboard")

    def create_pr(
        self,
        slug: str,
        branch_name: Optional[str] = None,
        title: Optional[str] = None,
        body: Optional[str] = None,
        base: Optional[str] = None,
        head: Optional[str] = None,
        reviewers: Optional[List[str]] = None,
        labels: Optional[List[str]] = None,
        draft: bool = False,
    ) -> Dict[str, Any]:
        """
        Create a GitHub Pull Request for a given theme. This is the primary method for PR creation.

        Args:
            slug (str): Theme slug for the PR
            branch_name (str, optional): Branch name (fallback if head not provided)
            title (str, optional): PR title (auto-generated if not provided)
            body (str, optional): PR body (auto-generated if not provided)
            base (str, optional): Base branch (defaults to config default)
            head (str, optional): Head branch (defaults to current branch)
            reviewers (List[str], optional): List of reviewers (defaults to config)
            labels (List[str], optional): List of labels (defaults to config)
            draft (bool): Whether to create as draft PR

        Returns:
            Dict[str, Any]: Result dictionary with success status and PR details
        """
        try:
            # Check if we're in a Git repository
            if not self._is_git_repo():
                msg = "Not in a Git repository"
                raise Exception(msg)

            # Check GitHub CLI availability and auth
            if not self._check_gh_cli():
                msg = "GitHub CLI not available or not authenticated"
                raise Exception(msg)

            # Get repository info and determine current branch
            repo_info = self._get_repo_info()
            current_branch = head or repo_info.get("current_branch") or branch_name

            if not current_branch:
                msg = "Could not determine branch for PR"
                raise Exception(msg)

            # Use provided values or generate defaults using stellantis template
            pr_content = self._build_stellantis_pr_content(slug, current_branch, repo_info)
            pr_title = title or pr_content["title"]
            pr_body = body or pr_content["body"]
            what_section = pr_content["what_section"]

            # Get configuration values with fallbacks
            pr_base = base or getattr(self.config, "default_branch", "main")
            if hasattr(self.config, "git") and self.config.git:
                git_config = self.config.git
                if isinstance(git_config, dict):
                    pr_reviewers = reviewers or git_config.get(
                        "default_reviewers", ["carsdotcom/fe-dev-sbm"]
                    )
                    pr_labels = labels or git_config.get("default_labels", ["fe-dev"])
                else:
                    pr_reviewers = reviewers or getattr(
                        git_config, "default_reviewers", ["carsdotcom/fe-dev-sbm"]
                    )
                    pr_labels = labels or getattr(git_config, "default_labels", ["fe-dev"])
            else:
                pr_reviewers = reviewers or ["carsdotcom/fe-dev-sbm"]
                pr_labels = labels or ["fe-dev"]

            # Ensure non-None values for type safety
            safe_current_branch = current_branch or "main"
            safe_pr_base = pr_base or "main"

            # Create the PR
            pr_url = self._execute_gh_pr_create(
                title=pr_title,
                body=pr_body,
                base=safe_pr_base,
                head=safe_current_branch,
                draft=draft,
                reviewers=pr_reviewers,
                labels=pr_labels,
            )

            logger.debug(f"Successfully created PR: {pr_url}")

            # Enable auto-merge immediately after PR creation
            self._enable_auto_merge(pr_url)

            # Fetch PR metadata and additions immediately after creation
            from sbm.utils.github_pr import fetch_pr_additions, fetch_pr_metadata

            pr_metadata = fetch_pr_metadata(pr_url)
            github_additions = fetch_pr_additions(pr_url)

            # Open the PR in browser after creation
            self._open_pr_in_browser(pr_url)

            # Copy Salesforce message to clipboard
            self._copy_salesforce_message_to_clipboard(what_section, pr_url)

            # Build response with complete PR metadata
            result = {
                "success": True,
                "pr_url": pr_url,
                "branch": safe_current_branch,
                "title": pr_title,
                "body": pr_body,
                "salesforce_message": what_section,
                "github_additions": github_additions,
            }

            # Add PR metadata if successfully fetched
            if pr_metadata:
                result.update(
                    {
                        "pr_author": pr_metadata.get("author"),
                        "pr_state": pr_metadata.get("state"),
                        "created_at": pr_metadata.get("created_at"),
                        "merged_at": pr_metadata.get("merged_at"),
                        "closed_at": pr_metadata.get("closed_at"),
                    }
                )

            return result

        except Exception as e:
            error_str = str(e)
            logger.error(f"PR creation failed: {error_str}")

            # Handle existing PR gracefully
            if self._is_pr_exists_error(error_str):
                try:
                    safe_head_branch = head or branch_name or "main"
                    existing_pr_url = self._handle_existing_pr(error_str, safe_head_branch)
                    logger.info(f"PR already exists: {existing_pr_url}")

                    # Enable auto-merge for existing PR (in case it wasn't enabled)
                    self._enable_auto_merge(existing_pr_url)

                    # Fetch metadata and additions for existing PR
                    from sbm.utils.github_pr import fetch_pr_additions, fetch_pr_metadata

                    pr_metadata = fetch_pr_metadata(existing_pr_url)
                    existing_github_additions = fetch_pr_additions(existing_pr_url)

                    # Still copy Salesforce message since migration likely completed
                    pr_content = self._build_stellantis_pr_content(slug, safe_head_branch, {})
                    what_section = pr_content["what_section"]
                    self._copy_salesforce_message_to_clipboard(what_section, existing_pr_url)

                    result = {
                        "success": True,
                        "pr_url": existing_pr_url,
                        "branch": safe_head_branch,
                        "title": pr_content["title"],
                        "existing": True,
                        "salesforce_message": what_section,
                        "github_additions": existing_github_additions,
                    }

                    # Add PR metadata if successfully fetched
                    if pr_metadata:
                        result.update(
                            {
                                "pr_author": pr_metadata.get("author"),
                                "pr_state": pr_metadata.get("state"),
                                "created_at": pr_metadata.get("created_at"),
                                "merged_at": pr_metadata.get("merged_at"),
                                "closed_at": pr_metadata.get("closed_at"),
                            }
                        )

                    return result
                except Exception as handle_e:
                    logger.error(f"Failed to handle existing PR: {handle_e}")

            return {"success": False, "error": error_str}

    def git_operations(self, slug: str) -> tuple:
        """
        Perform all Git operations for a migration.

        Args:
            slug (str): Dealer theme slug

        Returns:
            tuple: (success, branch_name) - a tuple containing success status and branch name
        """
        logger.info(f"Performing Git operations for {slug}")

        if not self.checkout_main_and_pull():
            return False, None

        success, branch_name = self.create_branch(slug)

        return success, branch_name


# Legacy function wrappers for backward compatibility
def _get_repo() -> Repo:
    """Legacy wrapper - initializes and returns a GitPython Repo object."""
    platform_dir = get_platform_dir()
    return Repo(platform_dir)


def checkout_main_and_pull():
    """Legacy wrapper for checkout_main_and_pull."""
    git_ops = GitOperations(Config({}))
    return git_ops.checkout_main_and_pull()


def create_branch(slug):
    """Legacy wrapper for create_branch."""
    git_ops = GitOperations(Config({}))
    return git_ops.create_branch(slug)


def commit_changes(slug, message=None):
    """Legacy wrapper for commit_changes."""
    git_ops = GitOperations(Config({}))
    return git_ops.commit_changes(slug, message)


def push_changes(branch_name):
    """Legacy wrapper for push_changes."""
    git_ops = GitOperations(Config({}))
    return git_ops.push_changes(branch_name)


def git_operations(slug):
    """Legacy wrapper for git_operations."""
    git_ops = GitOperations(Config({}))
    return git_ops.git_operations(slug)


def create_pr(slug, branch_name=None, **kwargs):
    """Legacy wrapper for create_pr."""
    from sbm.config import Config

    # Initialize config with safe defaults
    config_dict = {
        "default_branch": "main",
        "git": {"default_reviewers": ["carsdotcom/fe-dev-sbm"], "default_labels": ["fe-dev"]},
    }
    git_ops = GitOperations(Config(config_dict))
    return git_ops.create_pr(slug=slug, branch_name=branch_name, **kwargs)
