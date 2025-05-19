"""
Map components migration for the SBM tool.

This module handles the migration of map components from CommonTheme to DealerTheme.
"""

import os
import re
import shutil
from glob import glob
from ..utils.logger import logger
from ..utils.path import get_dealer_theme_dir, get_platform_dir, normalize_path


def find_map_shortcodes(slug):
    """
    Find map-related shortcodes in dealer theme PHP files.
    
    Args:
        slug (str): Dealer theme slug
        
    Returns:
        list: List of map shortcodes found
    """
    logger.info(f"Searching for map shortcodes in {slug}")
    
    try:
        theme_dir = get_dealer_theme_dir(slug)
        shortcodes = []
        
        # Look for PHP files
        php_files = glob(os.path.join(theme_dir, "**/*.php"), recursive=True)
        
        for php_file in php_files:
            with open(php_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
                # Look for map-related shortcodes
                map_shortcodes = re.findall(r"add_shortcode\(\s*['\"]((?:full-)?map)['\"]", content)
                
                if map_shortcodes:
                    shortcodes.extend(map_shortcodes)
                    logger.info(f"Found map shortcodes in {os.path.relpath(php_file, theme_dir)}: {map_shortcodes}")
        
        return shortcodes
        
    except Exception as e:
        logger.error(f"Error finding map shortcodes: {e}")
        return []


def identify_map_partials(slug):
    """
    Identify map partials used by map shortcodes.
    
    Args:
        slug (str): Dealer theme slug
        
    Returns:
        list: List of map partial paths
    """
    logger.info(f"Identifying map partials for {slug}")
    
    # This is a placeholder for the actual implementation
    # For now, we'll return an empty list
    return []


def copy_map_partials(slug, partials):
    """
    Copy map partials from CommonTheme to DealerTheme preserving the directory structure.
    
    Args:
        slug (str): Dealer theme slug
        partials (list): List of map partial paths
        
    Returns:
        bool: True if successful, False otherwise
    """
    logger.info(f"Copying map partials for {slug}")
    
    # This is a placeholder for the actual implementation
    # For now, we'll return True
    return True


def migrate_map_styles(slug, partials):
    """
    Migrate map styles to sb-inside.scss.
    
    Args:
        slug (str): Dealer theme slug
        partials (list): List of map partial paths
        
    Returns:
        bool: True if successful, False otherwise
    """
    logger.info(f"Migrating map styles for {slug}")
    
    # This is a placeholder for the actual implementation
    # For now, we'll return True
    return True


def migrate_map_components(slug):
    """
    Migrate map components from CommonTheme to DealerTheme.
    
    Args:
        slug (str): Dealer theme slug
        
    Returns:
        bool: True if successful, False otherwise
    """
    logger.info(f"Starting map components migration for {slug}")
    
    try:
        # Find map shortcodes
        shortcodes = find_map_shortcodes(slug)
        
        if not shortcodes:
            logger.info(f"No map shortcodes found for {slug}, skipping map migration")
            return True
        
        # Identify map partials
        partials = identify_map_partials(slug)
        
        if not partials:
            logger.info(f"No map partials identified for {slug}, skipping map migration")
            return True
        
        # Copy map partials
        if not copy_map_partials(slug, partials):
            logger.error(f"Failed to copy map partials for {slug}")
            return False
        
        # Migrate map styles
        if not migrate_map_styles(slug, partials):
            logger.error(f"Failed to migrate map styles for {slug}")
            return False
        
        logger.info(f"Map components migration completed successfully for {slug}")
        return True
        
    except Exception as e:
        logger.error(f"Error migrating map components: {e}")
        return False 
