"""
Factory for creating OEM handlers.

This module provides a factory for creating the appropriate OEM handler
based on dealer information.
"""

import os
import re
from pathlib import Path

from ..utils.logger import logger
from .default import DefaultHandler
from .stellantis import StellantisHandler


class OEMFactory:
    """
    Factory for creating OEM handlers based on dealer information.
    """

    # List of all available handlers
    _handlers = [
        StellantisHandler,
        # Add more handlers here as they are needed
    ]

    @classmethod
    def create_handler(cls, slug, dealer_info=None):
        """
        Create the appropriate OEM handler based on dealer information.

        Args:
            slug (str): Dealer theme slug
            dealer_info (dict, optional): Additional dealer information

        Returns:
            BaseOEMHandler: An instance of the appropriate OEM handler
        """
        # If dealer_info is provided and has a 'brand' key, use it for matching
        if dealer_info and "brand" in dealer_info:
            brand = dealer_info["brand"].lower()

            # Try to match the brand to a handler
            for handler_class in cls._handlers:
                handler = handler_class(slug)
                patterns = handler.get_brand_match_patterns()

                for pattern in patterns:
                    if re.search(pattern, brand, re.IGNORECASE):
                        logger.info(
                            f"Matched {slug} to {handler.__class__.__name__} based on brand: {brand}"
                        )
                        return handler

        # If no dealer_info is provided or no match was found, try to infer from the slug
        for handler_class in cls._handlers:
            handler = handler_class(slug)
            patterns = handler.get_brand_match_patterns()

            for pattern in patterns:
                if re.search(pattern, slug, re.IGNORECASE):
                    logger.info(f"Matched {slug} to {handler.__class__.__name__} based on slug")
                    return handler

        # If no match is found, use the default handler
        logger.info(f"No OEM match found for {slug}, using DefaultHandler")
        return DefaultHandler(slug)

    @classmethod
    def detect_from_theme(cls, slug, platform_dir=None):
        """
        Detect the OEM from the theme directory structure and content.

        Args:
            slug (str): Dealer theme slug
            platform_dir (str, optional): Path to the platform directory

        Returns:
            BaseOEMHandler: An instance of the appropriate OEM handler
        """
        if not platform_dir:
            platform_dir = os.environ.get("DI_WEBSITES_PLATFORM_DIR", "")
            if not platform_dir:
                logger.warning("Platform directory not set, unable to detect OEM from theme")
                return cls.create_handler(slug)

        theme_dir = Path(platform_dir) / "dealer-themes" / slug

        # Check if the theme directory exists
        if not theme_dir.exists():
            logger.warning(
                f"Theme directory not found at {theme_dir}, unable to detect OEM from theme"
            )
            return cls.create_handler(slug)

        # Look for OEM-specific indicators in files
        indicators = {}

        # Check functions.php for OEM-specific code
        functions_file = theme_dir / "functions.php"
        if functions_file.exists():
            with open(functions_file, encoding="utf-8", errors="ignore") as f:
                content = f.read().lower()

                # Check for each handler's patterns
                for handler_class in cls._handlers:
                    handler = handler_class(slug)
                    patterns = handler.get_brand_match_patterns()

                    matches = 0
                    for pattern in patterns:
                        matches += len(re.findall(pattern, content, re.IGNORECASE))

                    if matches > 0:
                        indicators[handler_class.__name__] = (
                            indicators.get(handler_class.__name__, 0) + matches
                        )

        # If any indicators were found, use the handler with the most matches
        if indicators:
            best_match = max(indicators.items(), key=lambda x: x[1])
            logger.info(f"Detected OEM for {slug} based on theme content: {best_match[0]}")

            # Create the appropriate handler
            for handler_class in cls._handlers:
                if handler_class.__name__ == best_match[0]:
                    return handler_class(slug)

        # If no indicators were found, fall back to the create_handler method
        return cls.create_handler(slug)
