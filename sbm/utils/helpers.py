"""
Helper utilities for the SBM tool.

This module provides miscellaneous helper functions for the SBM tool.
"""

import re
from datetime import datetime


def validate_slug(slug):
    """
    Validate that the slug contains only allowed characters.
    
    Args:
        slug (str): Dealer theme slug to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    if not slug:
        return False
    
    if re.search(r'[^a-zA-Z0-9/_-]', slug):
        return False
    
    return True


def get_branch_name(slug):
    """
    Generate a standardized branch name for a migration.
    
    Args:
        slug (str): Dealer theme slug
        
    Returns:
        str: Branch name in the format {slug}-sbm{MMYY}
    """
    current_date = datetime.now().strftime("%m%y")
    return f"{slug}-sbm{current_date}"


def extract_content_between_comments(content, start_marker, end_marker):
    """
    Extract content between specified comment markers.
    
    Args:
        content (str): Content to search in
        start_marker (str): Start marker comment
        end_marker (str): End marker comment
        
    Returns:
        str: Extracted content or empty string if not found
    """
    pattern = re.compile(f"{re.escape(start_marker)}(.*?){re.escape(end_marker)}", 
                         re.DOTALL)
    match = pattern.search(content)
    
    if match:
        return match.group(1).strip()
    
    return ""


def extract_nested_rule(content, selector):
    """
    Extract a CSS rule including all nested rules.
    
    Args:
        content (str): CSS content to search in
        selector (str): CSS selector to find
        
    Returns:
        str: Extracted rule content or empty string if not found
    """
    # Escape special characters in the selector for regex
    escaped_selector = re.escape(selector)
    
    # Pattern to match the selector and its content block
    pattern = re.compile(f"{escaped_selector}\\s*{{([^}}]*(?:{{[^}}]*}}[^}}]*)*)}}", re.DOTALL)
    match = pattern.search(content)
    
    if match:
        # Return the full match including selector and braces
        return match.group(0)
    
    return "" 
