"""
Land Rover OEM handler for the SBM tool.
"""

from .base import BaseOEMHandler


class LandRoverHandler(BaseOEMHandler):
    """
    Handler for Land Rover dealers.
    """

    def get_map_styles(self) -> str:
        """
        Get Land Rover-specific map styles.
        """
        return ""

    def get_directions_styles(self) -> str:
        """
        Get Land Rover-specific direction box styles.
        """
        return ""

    def should_force_map_migration(self) -> bool:
        """
        Land Rover styles use CommonTheme directly, no forced migration to sb-inside.scss needed.
        """
        return False

    def get_map_partial_patterns(self) -> list[str]:
        """
        Get Land Rover-specific patterns for identifying map partials/imports.
        """
        return [
            r"dealer-groups/landrover/map-row",
            r"dealer-groups/landrover/directions-row",
            r"dealer-groups/landrover/location",
        ]

    def get_brand_match_patterns(self) -> list[str]:
        """
        Get patterns for identifying if a dealer is Land Rover.
        """
        return [
            r"landrover",
            r"land-rover",
            r"land_rover",
            r"land rover",
        ]
