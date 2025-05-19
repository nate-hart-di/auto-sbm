"""
Stellantis OEM handler for the SBM tool.

This module provides Stellantis-specific handling for Chrysler, Dodge, Jeep, Ram, and Fiat brands.
"""

from pathlib import Path
import re
import os
from .base import BaseOEMHandler
from ..utils.logger import logger


class StellantisHandler(BaseOEMHandler):
    """
    Stellantis/CDJR specific implementation.
    
    Handles Chrysler, Dodge, Jeep, Ram, and Fiat brands.
    """
    
    def get_map_styles(self):
        """
        Get Stellantis-specific map styles.
        
        Returns:
            str: CSS/SCSS content for map styles
        """
        return self._load_style_file('stellantis-map-styles.scss')
    
    def get_directions_styles(self):
        """
        Get Stellantis-specific direction box styles.
        
        Returns:
            str: CSS/SCSS content for directions box styles
        """
        return self._load_style_file('stellantis-directions-row-styles.scss')
    
    def get_map_partial_patterns(self):
        """
        Get Stellantis-specific patterns for identifying map partials.
        
        Returns:
            list: Regular expression patterns for finding map partials
        """
        # Stellantis-specific patterns
        stellantis_patterns = [
            r'dealer-groups/fca/map-row-\d+',
            r'dealer-groups/cdjr/map-row-\d+',
            r'dealer-groups/stellantis/map-row-\d+'
        ]
        return stellantis_patterns + super().get_map_partial_patterns()
    
    def get_brand_match_patterns(self):
        """
        Get patterns for identifying if a dealer belongs to Stellantis.
        
        Returns:
            list: Regular expression patterns for matching Stellantis brands
        """
        return [
            r'chrysler',
            r'dodge',
            r'jeep',
            r'ram',
            r'fiat',
            r'cdjr',
            r'fca'
        ]
