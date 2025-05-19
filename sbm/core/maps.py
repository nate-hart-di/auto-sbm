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
from ..oem.factory import OEMFactory


def find_map_shortcodes(slug, shortcode_patterns=None):
    """
    Find map-related shortcodes in dealer theme PHP files.
    
    Args:
        slug (str): Dealer theme slug
        shortcode_patterns (list, optional): List of shortcode patterns to search for
        
    Returns:
        list: List of map shortcodes found
    """
    logger.info(f"Searching for map shortcodes in {slug}")
    
    try:
        theme_dir = get_dealer_theme_dir(slug)
        shortcodes = []
        
        # If patterns are not provided, use default patterns
        if shortcode_patterns is None:
            shortcode_patterns = [
                r'add_shortcode\s*\(\s*[\'"]full-map[\'"]',
                r'add_shortcode\s*\(\s*[\'"]map[\'"]',
                r'add_shortcode\s*\(\s*[\'"]google-?map[\'"]',
                r'add_shortcode\s*\(\s*[\'"].*?map.*?[\'"]',
            ]
        
        # Look for PHP files
        php_files = glob(os.path.join(theme_dir, "**/*.php"), recursive=True)
        
        for php_file in php_files:
            with open(php_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
                # Look for map-related shortcodes
                for pattern in shortcode_patterns:
                    map_shortcodes = re.findall(pattern, content)
                    if map_shortcodes:
                        shortcodes.extend(map_shortcodes)
                        logger.info(f"Found map shortcodes in {os.path.relpath(php_file, theme_dir)}: {map_shortcodes}")
        
        return shortcodes
        
    except Exception as e:
        logger.error(f"Error finding map shortcodes: {e}")
        return []


def identify_map_partials(slug, oem_handler=None, partial_patterns=None):
    """
    Identify map partials used by map shortcodes.
    
    Args:
        slug (str): Dealer theme slug
        oem_handler (BaseOEMHandler, optional): OEM handler for the dealer
        partial_patterns (list, optional): List of partial patterns to search for
        
    Returns:
        list: List of map partial paths
    """
    logger.info(f"Identifying map partials for {slug}")
    
    try:
        # Use OEM factory to get handler if not provided
        if oem_handler is None:
            oem_handler = OEMFactory.detect_from_theme(slug)
            logger.info(f"Using {oem_handler} for identifying map partials")
            
        # Use OEM-specific patterns if none are provided
        if partial_patterns is None:
            partial_patterns = oem_handler.get_map_partial_patterns()
            
        theme_dir = get_dealer_theme_dir(slug)
        partials = []
        
        # Look for PHP files
        php_files = glob(os.path.join(theme_dir, "**/*.php"), recursive=True)
        
        for php_file in php_files:
            with open(php_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
                # Look for map partial patterns
                for pattern in partial_patterns:
                    matches = re.findall(pattern, content)
                    if matches:
                        partials.extend(matches)
                        logger.info(f"Found map partials in {os.path.relpath(php_file, theme_dir)}: {matches}")
        
        return partials
    
    except Exception as e:
        logger.error(f"Error identifying map partials: {e}")
        return []


def copy_map_partials(slug, partials, oem_handler=None):
    """
    Copy map partials from CommonTheme to DealerTheme preserving the directory structure.
    
    Args:
        slug (str): Dealer theme slug
        partials (list): List of map partial paths
        oem_handler (BaseOEMHandler, optional): OEM handler for the dealer
        
    Returns:
        bool: True if successful, False otherwise
    """
    logger.info(f"Copying map partials for {slug}")
    
    try:
        # Use OEM factory to get handler if not provided
        if oem_handler is None:
            oem_handler = OEMFactory.detect_from_theme(slug)
            logger.info(f"Using {oem_handler} for copying map partials")
        
        theme_dir = get_dealer_theme_dir(slug)
        platform_dir = get_platform_dir()
        common_theme_dir = os.path.join(platform_dir, "wp-content", "themes", "DealerInspireCommonTheme")
        
        # Ensure CommonTheme directory exists
        if not os.path.exists(common_theme_dir):
            common_theme_dir = os.path.join("/Users/nathanhart/code/dealerinspire/dealerinspire-core/dealer-inspire/wp-content/themes/DealerInspireCommonTheme")
            if not os.path.exists(common_theme_dir):
                logger.error(f"CommonTheme directory not found at: {common_theme_dir}")
                return False
        
        # Process each partial
        for partial in partials:
            # Normalize path
            if not partial.endswith('.php'):
                partial += '.php'
            
            # Source path in CommonTheme
            source_path = os.path.join(common_theme_dir, partial)
            
            # Target path in DealerTheme
            target_path = os.path.join(theme_dir, partial)
            
            # Create target directory if it doesn't exist
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            
            # Copy the file
            if os.path.exists(source_path):
                shutil.copy2(source_path, target_path)
                logger.info(f"Copied map partial from {source_path} to {target_path}")
            else:
                logger.warning(f"Source map partial not found: {source_path}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error copying map partials: {e}")
        return False


def migrate_map_styles(slug, partials, oem_handler=None):
    """
    Migrate map styles to sb-inside.scss.
    
    Args:
        slug (str): Dealer theme slug
        partials (list): List of map partial paths
        oem_handler (BaseOEMHandler, optional): OEM handler for the dealer
        
    Returns:
        bool: True if successful, False otherwise
    """
    logger.info(f"Migrating map styles for {slug}")
    
    try:
        # Use OEM factory to get handler if not provided
        if oem_handler is None:
            oem_handler = OEMFactory.detect_from_theme(slug)
            logger.info(f"Using {oem_handler} for map styles migration")
        
        theme_dir = get_dealer_theme_dir(slug)
        sb_inside_path = os.path.join(theme_dir, "sb-inside.scss")
        
        # Check if map styles already exist
        with open(sb_inside_path, 'r') as f:
            content = f.read()
            
        if '#mapRow' in content or '#directionsBox' in content or 'map-canvas' in content:
            logger.info(f"Map styles already exist in sb-inside.scss for {slug}")
            return True
        
        # Get map styles from OEM handler
        map_styles = oem_handler.get_map_styles()
        
        # Add map styles to sb-inside.scss
        with open(sb_inside_path, 'a') as f:
            f.write(f"\n\n// Map styles for {slug} - {oem_handler.name} OEM\n")
            f.write(map_styles)
        
        logger.info(f"Added {oem_handler.name} map styles to sb-inside.scss for {slug}")
        return True
        
    except Exception as e:
        logger.error(f"Error migrating map styles: {e}")
        return False


def migrate_map_components(slug, oem_handler=None):
    """
    Migrate map components from CommonTheme to DealerTheme.
    
    Args:
        slug (str): Dealer theme slug
        oem_handler (BaseOEMHandler, optional): OEM handler for the dealer
        
    Returns:
        bool: True if successful, False otherwise
    """
    logger.info(f"Starting map components migration for {slug}")
    
    try:
        # Use OEM factory to get handler if not provided
        if oem_handler is None:
            oem_handler = OEMFactory.detect_from_theme(slug)
            logger.info(f"Using {oem_handler} for map components migration")
        
        # Find map shortcodes using OEM-specific patterns
        shortcode_patterns = oem_handler.get_shortcode_patterns()
        shortcodes = find_map_shortcodes(slug, shortcode_patterns)
        
        if not shortcodes:
            logger.info(f"No map shortcodes found for {slug}, skipping map migration")
            return True
        
        # Identify map partials using OEM-specific patterns
        partials = identify_map_partials(slug, oem_handler)
        
        if not partials:
            logger.info(f"No map partials identified for {slug}, skipping map migration")
            return True
        
        # Copy map partials
        if not copy_map_partials(slug, partials, oem_handler):
            logger.error(f"Failed to copy map partials for {slug}")
            return False
        
        # Migrate map styles
        if not migrate_map_styles(slug, partials, oem_handler):
            logger.error(f"Failed to migrate map styles for {slug}")
            return False
        
        logger.info(f"Map components migration completed successfully for {slug}")
        return True
        
    except Exception as e:
        logger.error(f"Error migrating map components: {e}")
        return False
