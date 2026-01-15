"""
Kia OEM handler for the SBM tool.

This module provides Kia-specific handling for the Kia brand.
Currently acts as a placeholder that delegates to DefaultHandler functionality.
"""

from .base import BaseOEMHandler


class KiaHandler(BaseOEMHandler):
    """
    Kia-specific implementation.

    Currently a placeholder that uses default behavior.
    Future: May include Kia-specific styles, components, or processing.
    """

    def get_brand_match_patterns(self):
        """
        Get patterns for identifying if a dealer belongs to Kia.

        Returns:
            list: Regular expression patterns for matching Kia brands
        """
        return [r"kia"]

    def get_map_styles(self):
        """
        Get Kia-specific map styles.
        Currently returns default map styles.

        Returns:
            str: CSS/SCSS content for map styles
        """
        # For now, use default map styles
        # Future: Could return Kia-specific map styling
        return super().get_map_styles()

    def get_directions_styles(self):
        """
        Get Kia-specific direction box styles.
        Currently returns default direction styles.

        Returns:
            str: CSS/SCSS content for directions box styles
        """
        # For now, use default direction styles
        # Future: Could return Kia-specific direction styling
        return super().get_directions_styles()
