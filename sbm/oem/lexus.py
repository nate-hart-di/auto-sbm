"""
Lexus OEM handler for the SBM tool.
"""

from .base import BaseOEMHandler


class LexusHandler(BaseOEMHandler):
    """
    Handler for Lexus dealers.
    """

    def get_map_styles(self) -> str:
        """
        Get Lexus-specific map styles.
        """
        return ""

    def get_directions_styles(self) -> str:
        """
        Get Lexus-specific direction box styles.
        """
        return ""

    def should_force_map_migration(self) -> bool:
        """
        Force Lexus map styles to migrate to sb-inside.scss.
        """
        return True

    def get_map_partial_patterns(self):
        """
        Get Lexus-specific patterns for identifying map partials/imports.
        """
        return [
            r"dealer-groups/lexus/lexusoem\d+/_?section-map",
            r"dealer-groups/lexus/lexusoem\d+/mapsection\d*",
            r"dealer-groups/([^/]+)/map-row-\d+",
            r"dealer-groups/([^/]+)/directions",
            r"dealer-groups/([^/]+)/location",
        ]

    def get_brand_match_patterns(self):
        """
        Get patterns for identifying if a dealer is Lexus.
        """
        return [
            r"lexus",
        ]
