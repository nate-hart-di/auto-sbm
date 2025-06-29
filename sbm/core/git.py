"""
Git operations for the SBM tool.

This module handles Git operations such as branch creation, commits, and pull requests
using the GitPython library for safer and more robust interactions.
"""

import os
from git import Repo, GitCommandError
from ..utils.path import get_platform_dir, get_dealer_theme_dir
from ..utils.helpers import get_branch_name
from ..utils.logger import logger
from ..utils.command import execute_command


def _get_repo() -> Repo:
    """Initializes and returns a GitPython Repo object."""
    platform_dir = get_platform_dir()
    return Repo(platform_dir)

def checkout_main_and_pull():
    """
    Checkout the main branch and pull the latest changes.
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        logger.info("Checking out main branch and pulling latest changes")
        repo = _get_repo()
        
        # Stash or discard any local changes before switching branches
        if repo.is_dirty(untracked_files=True):
            logger.info("Discarding dirty working directory before checkout.")
            repo.git.reset('--hard')
            repo.git.clean('-fd')

        repo.heads.main.checkout()
        logger.info("Pulling latest changes from origin/main")
        repo.remotes.origin.pull()
        return True
    except GitCommandError as e:
        logger.error(f"Failed to checkout or pull main branch: {e}")
        return False

def create_branch(slug):
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
        repo = _get_repo()
        
        # If branch already exists, delete it
        if branch_name in repo.heads:
            logger.warning(f"Branch '{branch_name}' already exists. Deleting it.")
            repo.delete_head(branch_name, force=True)

        # Create and checkout the new branch
        new_branch = repo.create_head(branch_name)
        new_branch.checkout()
        
        return True, branch_name
    except GitCommandError as e:
        logger.error(f"Failed to create branch '{branch_name}': {e}")
        return False, None

def commit_changes(slug, message=None):
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
        repo = _get_repo()
        
        # Path to the dealer theme relative to the repo root
        theme_path = os.path.relpath(get_dealer_theme_dir(slug), get_platform_dir())
        
        # Add all changes in the specific theme directory using subprocess
        logger.info(f"Adding changes in {theme_path}")
        add_command = f"git add {theme_path}"
        add_success, _, _, _ = execute_command(add_command, "Failed to add changes", cwd=get_platform_dir())
        if not add_success:
            return False
            
        # Commit if there are changes to commit
        if repo.is_dirty(index=True):
            logger.info(f'Committing with message: "{message}"')
            commit_command = f'git commit -m "{message}"'
            commit_success, _, _, _ = execute_command(commit_command, "Failed to commit changes", cwd=get_platform_dir())
            return commit_success
        else:
            logger.info("No changes to commit.")
            return True # Nothing to do is a success
            
    except GitCommandError as e:
        logger.error(f"Failed to commit changes for {slug}: {e}")
        return False

def push_changes(branch_name):
    """
    Push changes to the remote repository.
    
    Args:
        branch_name (str): Branch name to push
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        logger.info(f"Pushing changes to origin/{branch_name}")
        repo = _get_repo()
        repo.remotes.origin.push(refspec=f"{branch_name}:{branch_name}", set_upstream=True)
        return True
    except GitCommandError as e:
        logger.error(f"Failed to push changes to origin/{branch_name}: {e}")
        return False

def create_pull_request(
    title: str,
    body: str,
    base_branch: str,
    head_branch: str,
    reviewers: str = "",
    labels: str = "",
) -> str | None:
    """
    Creates a GitHub Pull Request using the GitHub CLI (gh).

    Args:
        title (str): The title of the pull request.
        body (str): The body/description of the pull request.
        base_branch (str): The base branch for the PR (e.g., 'main').
        head_branch (str): The head branch for the PR (e.g., 'feature/my-feature').
        reviewers (str, optional): Comma-separated list of reviewers. Defaults to "".
        labels (str, optional): Comma-separated list of labels. Defaults to "".

    Returns:
        str | None: The URL of the created PR if successful, None otherwise.
    """
    logger.info(f"Attempting to create a Pull Request from {head_branch} to {base_branch}")

    # Add a git status check to debug uncommitted changes
    status_command = "git status"
    execute_command(status_command, "Failed to get git status", cwd=get_platform_dir())

    # Build the gh pr create command as a single string with proper quoting
    gh_cmd = (
        f'gh pr create --repo "carsdotcom/di-websites-platform" --title "{title}" --body "{body}" '
        f'--base "{base_branch}" --head "{head_branch}" --draft'
    )

    # Execute the command
    success, stdout_lines, stderr_lines, _ = execute_command(
        gh_cmd,
        error_message="Failed to create GitHub PR",
        wait_for_completion=True
    )

    if success:
        pr_url = "".join(stdout_lines).strip()
        logger.info(f"Successfully created PR: {pr_url}")
        return pr_url
    else:
        logger.error(f"Error creating PR. Stderr: {''.join(stderr_lines)}")
        return None

def git_operations(slug):
    """
    Perform all Git operations for a migration.
    
    Args:
        slug (str): Dealer theme slug
        
    Returns:
        tuple: (success, branch_name) - a tuple containing success status and branch name
    """
    logger.info(f"Performing Git operations for {slug}")
    
    if not checkout_main_and_pull():
        return False, None
    
    success, branch_name = create_branch(slug)
    
    return success, branch_name 
