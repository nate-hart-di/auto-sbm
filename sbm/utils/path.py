"""
Path utilities for the SBM tool.

This module provides path handling functions for the SBM tool.
"""

import logging
import os
import re
from os.path import expanduser

logger = logging.getLogger(__name__)


def get_platform_dir():
    """
    Get the DI Websites Platform directory.
    
    Returns:
        str: Path to the DI Websites Platform directory
    
    Raises:
        ValueError: If the directory is not found.
    """
    home_dir = expanduser("~")
    # This path is based on the user's explicit request.
    platform_dir = os.path.join(home_dir, "di-websites-platform")

    if not os.path.isdir(platform_dir):
        raise ValueError(f"DI Websites Platform directory not found at: {platform_dir}")

    return platform_dir


def get_dealer_theme_dir(slug):
    """
    Get the dealer theme directory for a given slug.
    
    Args:
        slug (str): Dealer theme slug
        
    Returns:
        str: Path to the dealer theme directory
        
    Raises:
        ValueError: If the platform directory is not set
    """
    platform_dir = get_platform_dir()
    theme_dir = os.path.join(platform_dir, "dealer-themes", slug)

    return theme_dir


def normalize_path(path):
    """
    Normalize a path to use forward slashes.
    
    Args:
        path (str): Path to normalize
        
    Returns:
        str: Normalized path
    """
    return path.replace("\\", "/")


def convert_to_absolute_theme_path(path, slug):
    """
    Convert a relative path to an absolute theme path.
    
    Args:
        path (str): Relative path to convert
        slug (str): Dealer theme slug
        
    Returns:
        str: Absolute path with /wp-content/themes/ format
    """
    # First normalize the path to use forward slashes
    path = normalize_path(path)

    # Convert relative paths to absolute paths
    if path.startswith("../.."):
        # ../../DealerInspireCommonTheme/file.png → /wp-content/themes/DealerInspireCommonTheme/file.png
        path = re.sub(r"^../../", "/wp-content/themes/", path)
    elif path.startswith(".."):
        # ../images/background.jpg → /wp-content/themes/DealerInspireDealerTheme/images/background.jpg
        path = f"/wp-content/themes/DealerInspireDealerTheme/{path[3:]}"

    return path


def get_common_theme_path() -> str:
    """
    Returns the absolute path to the DealerInspireCommonTheme directory.
    
    This function assumes the script is running within the auto-sbm project
    and can traverse up to the parent directory containing di-websites-platform.
    """
    # Construct the path starting from the user's home directory
    home_dir = expanduser("~")
    platform_root = os.path.join(home_dir, "di-websites-platform")

    common_theme_path = os.path.join(
        platform_root,
        "app",
        "dealer-inspire",
        "wp-content",
        "themes",
        "DealerInspireCommonTheme"
    )

    if not os.path.isdir(common_theme_path):
        # Fallback for different structures, can be adjusted
        logger.warning(f"DealerInspireCommonTheme not found at expected path: {common_theme_path}")
        # A more robust solution might search or use a config setting
        return ""

    return common_theme_path
