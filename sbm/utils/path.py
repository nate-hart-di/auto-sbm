"""
Path utilities for the SBM tool.

This module provides path handling functions for the SBM tool.
"""

import os
import re


def get_platform_dir():
    """
    Get the DI Websites Platform directory from environment variable.
    
    Returns:
        str: Path to the DI Websites Platform directory
    
    Raises:
        ValueError: If the environment variable is not set
    """
    platform_dir = os.environ.get('DI_WEBSITES_PLATFORM_DIR')
    if not platform_dir:
        raise ValueError("DI_WEBSITES_PLATFORM_DIR environment variable is not set.")
    
    return platform_dir


def get_dealer_theme_dir(slug):
    """
    Get the dealer theme directory for a given slug.
    
    Args:
        slug (str): Dealer theme slug
        
    Returns:
        str: Path to the dealer theme directory
        
    Raises:
        ValueError: If the platform directory is not set or the dealer theme directory doesn't exist
    """
    platform_dir = get_platform_dir()
    theme_dir = os.path.join(platform_dir, 'dealer-themes', slug)
    
    if not os.path.isdir(theme_dir):
        raise ValueError(f"Dealer theme directory not found: {theme_dir}")
    
    return theme_dir


def normalize_path(path):
    """
    Normalize a path to use forward slashes.
    
    Args:
        path (str): Path to normalize
        
    Returns:
        str: Normalized path
    """
    return path.replace('\\', '/')


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
    if path.startswith('../..'):
        # ../../DealerInspireCommonTheme/file.png → /wp-content/themes/DealerInspireCommonTheme/file.png
        path = re.sub(r'^../../', '/wp-content/themes/', path)
    elif path.startswith('..'):
        # ../images/background.jpg → /wp-content/themes/DealerInspireDealerTheme/images/background.jpg
        path = f"/wp-content/themes/DealerInspireDealerTheme/{path[3:]}"
    
    return path 
