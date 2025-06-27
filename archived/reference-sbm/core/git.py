"""
Git operations for the SBM tool.

This module handles Git operations such as branch creation, commits, and pull requests.
"""

import os
from ..utils.command import execute_command
from ..utils.path import get_platform_dir
from ..utils.helpers import get_branch_name
from ..utils.logger import logger


def checkout_main_and_pull():
    """
    Checkout the main branch and pull the latest changes.
    
    Returns:
        bool: True if successful, False otherwise
    """
    logger.info("Checking out main branch and pulling latest changes")
    
    platform_dir = get_platform_dir()
    os.chdir(platform_dir)
    
    return execute_command("git checkout main && git pull", 
                          "Failed to checkout or pull main branch")


def create_branch(slug):
    """
    Create a new branch for the migration.
    
    Args:
        slug (str): Dealer theme slug
        
    Returns:
        tuple: (success, branch_name) - a tuple containing success status and branch name
    """
    branch_name = get_branch_name(slug)
    logger.info(f"Creating new branch: {branch_name}")
    
    platform_dir = get_platform_dir()
    os.chdir(platform_dir)
    
    success = execute_command(f"git checkout -b {branch_name}", 
                             f"Failed to create branch {branch_name}")
    
    return success, branch_name


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
    
    logger.info(f"Committing changes for {slug}")
    
    # Get the dealer theme directory
    platform_dir = get_platform_dir()
    dealer_dir = os.path.join(platform_dir, 'dealer-themes', slug)
    os.chdir(dealer_dir)
    
    # Add all changes
    if not execute_command("git add .", "Failed to add changes"):
        return False
    
    # Commit with the specified message
    if not execute_command(f'git commit -m "{message}"', "Failed to commit changes"):
        return False
    
    return True


def push_changes(branch_name):
    """
    Push changes to the remote repository.
    
    Args:
        branch_name (str): Branch name to push
        
    Returns:
        bool: True if successful, False otherwise
    """
    logger.info(f"Pushing changes to origin/{branch_name}")
    
    return execute_command(f"git push -u origin {branch_name}", 
                          f"Failed to push changes to origin/{branch_name}")


def git_operations(slug):
    """
    Perform all Git operations for a migration.
    
    Args:
        slug (str): Dealer theme slug
        
    Returns:
        tuple: (success, branch_name) - a tuple containing success status and branch name
    """
    logger.info(f"Performing Git operations for {slug}")
    
    # Checkout main and pull
    if not checkout_main_and_pull():
        return False, None
    
    # Create branch
    success, branch_name = create_branch(slug)
    
    return success, branch_name 
