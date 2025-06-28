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
        
        # Stash any local changes before switching branches
        if repo.is_dirty(untracked_files=True):
            logger.info("Stashing dirty working directory before checkout.")
            repo.git.stash()

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
        
        # Create and checkout the new branch
        new_branch = repo.create_head(branch_name)
        new_branch.checkout()
        
        return True, branch_name
    except GitCommandError as e:
        # If branch already exists, check it out
        if f"a branch named '{branch_name}' already exists" in str(e).lower():
            logger.warning(f"Branch '{branch_name}' already exists. Checking it out.")
            try:
                repo.heads[branch_name].checkout()
                return True, branch_name
            except GitCommandError as checkout_e:
                logger.error(f"Failed to checkout existing branch '{branch_name}': {checkout_e}")
                return False, None
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
        
        # Add all changes in the specific theme directory
        logger.info(f"Adding changes in {theme_path}")
        repo.index.add([theme_path])
        
        # Commit if there are changes to commit
        if repo.is_dirty(index=True):
            logger.info(f'Committing with message: "{message}"')
            repo.index.commit(message)
            return True
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

    # Build the gh pr create command
    gh_cmd = [
        "gh", "pr", "create",
        "--title", title,
        "--body", body,
        "--base", base_branch,
        "--head", head_branch,
        "--draft" # Always create as draft initially
    ]

    if reviewers:
        gh_cmd.extend(["--reviewer", reviewers])
    if labels:
        gh_cmd.extend(["--label", labels])

    # Execute the command
    # We need to capture stdout to get the PR URL
    success, stdout_lines, stderr_lines, _ = execute_command(
        " ".join(gh_cmd),
        error_message="Failed to create GitHub PR",
        wait_for_completion=True # This command should complete and return output
    )

    if success:
        pr_url = "".join(stdout_lines).strip()
        logger.info(f"Successfully created PR: {pr_url}")
        return pr_url
    else:
        logger.error(f"Error creating PR. Stderr: {'\n'.join(stderr_lines)}")
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
