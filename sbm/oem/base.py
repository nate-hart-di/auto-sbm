"""
Base OEM handler for the SBM tool.

This module defines the BaseOEMHandler class that provides a common interface
for all OEM-specific implementations.
"""

from pathlib import Path
import os
from ..utils.logger import logger


class BaseOEMHandler:
    """
    Base class for OEM-specific handling.
    
    All OEM handlers should inherit from this class and implement
    the required methods.
    """
    
    def __init__(self, slug):
        """
        Initialize the OEM handler.
        
        Args:
            slug (str): Dealer theme slug
        """
        self.slug = slug
        self.name = self.__class__.__name__.replace('Handler', '')
    
    def get_map_styles(self):
        """
        Get OEM-specific map styles.
        
        Returns:
            str: CSS/SCSS content for map styles
        """
        raise NotImplementedError(f"{self.name} handler must implement get_map_styles()")
    
    def get_directions_styles(self):
        """
        Get OEM-specific direction box styles.
        
        Returns:
            str: CSS/SCSS content for directions box styles
        """
        raise NotImplementedError(f"{self.name} handler must implement get_directions_styles()")
    
    def get_map_partial_patterns(self):
        """
        Get OEM-specific patterns for identifying map partials.
        
        Returns:
            list: Regular expression patterns for finding map partials
        """
        # Default patterns that work for most OEMs
        return [
            r'dealer-groups/([^/]+)/map-row-\d+',
            r'dealer-groups/([^/]+)/directions',
            r'dealer-groups/([^/]+)/location'
        ]
    
    def get_shortcode_patterns(self):
        """
        Get OEM-specific patterns for identifying map shortcodes.
        
        Returns:
            list: Regular expression patterns for finding map shortcodes
        """
        # Default patterns that work for most OEMs
        return [
            r'add_shortcode\s*\(\s*[\'"]full-map[\'"]',
            r'add_shortcode\s*\(\s*[\'"]map[\'"]',
            r'add_shortcode\s*\(\s*[\'"]google-?map[\'"]',
            r'add_shortcode\s*\(\s*[\'"].*?map.*?[\'"]'
        ]
    
    def get_brand_match_patterns(self):
        """
        Get patterns for identifying if a dealer belongs to this OEM.
        
        Returns:
            list: Regular expression patterns for matching dealer brands
        """
        raise NotImplementedError(f"{self.name} handler must implement get_brand_match_patterns()")
    
    def _load_style_file(self, filename):
        """
        Helper method to load style content from a file.
        
        Args:
            filename (str): Name of the style file
            
        Returns:
            str: Content of the style file or empty string if not found
        """
        # Try to locate the style file in multiple locations
        possible_paths = [
            # In the general styles directory (for Stellantis)
            Path(__file__).parent.parent.parent / 'stellantis' / 'add-to-sb-inside' / filename,
        ]
        
        for path in possible_paths:
            if path.exists():
                logger.info(f"Loading style file: {path}")
                with open(path, 'r') as f:
                    return f.read()
        
        logger.warning(f"Style file {filename} not found for {self.name}")
        return ""
    
    def __str__(self):
        return f"{self.name}Handler({self.slug})"
