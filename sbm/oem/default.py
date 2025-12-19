"""
Default OEM handler for the SBM tool.

This module provides a fallback handler for dealers that don't match any specific OEM.
"""

from .base import BaseOEMHandler


class DefaultHandler(BaseOEMHandler):
    """
    Default handler for dealers that don't match any specific OEM.

    Provides generic styles and patterns that work across most dealers.
    Does NOT add OEM-specific map/directions styles - those come from the OEM handlers.
    """

    def get_map_styles(self) -> str:
        """
        Get generic map styles.

        Returns:
            str: Empty string - default handler doesn't add map styles.
                 Map styles are OEM-specific (e.g., Stellantis has specific directions box).
        """
        # Default handler returns nothing - map styles are OEM-specific
        # The actual map SCSS content is migrated from CommonTheme via maps.py
        return ""

    def get_directions_styles(self):
        """
        Get generic direction box styles.

        Returns:
            str: Empty string - default handler doesn't add directions styles.
                 Directions styles are OEM-specific (e.g., Stellantis).
        """
        # Default handler returns nothing - directions styles are OEM-specific
        return ""

    def get_brand_match_patterns(self):
        """
        Get patterns for identifying if a dealer belongs to this handler.

        Returns:
            list: Regular expression patterns for matching dealer brands
        """
        # This is a fallback handler, so it doesn't have specific patterns
        return []
