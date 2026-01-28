"""
Factory for creating OEM handlers.

This module provides a factory for creating the appropriate OEM handler
based on dealer information.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, ClassVar

from sbm.utils.logger import logger

from .default import DefaultHandler
from .kia import KiaHandler
from .lexus import LexusHandler
from .stellantis import StellantisHandler

if TYPE_CHECKING:
    from .base import BaseOEMHandler


class OEMFactory:
    """
    Factory for creating OEM handlers based on dealer information.
    """

    # List of all available handlers
    _handlers: ClassVar[list[type[BaseOEMHandler]]] = [
        StellantisHandler,
        KiaHandler,
        LexusHandler,
        # Add more handlers here as they are needed
    ]

    @classmethod
    def create_handler(cls, slug: str, dealer_info: dict[str, str] | None = None) -> BaseOEMHandler:
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
                        handler_name = handler.__class__.__name__
                        logger.info(f"Matched {slug} to {handler_name} based on brand: {brand}")
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
    def detect_from_theme(cls, slug: str, platform_dir: str | None = None) -> BaseOEMHandler:
        """
        Detect the OEM from the dealer slug.

        Args:
            slug: Dealer theme slug
            platform_dir: Deprecated, kept for compatibility (unused).

        Returns:
            An instance of the appropriate OEM handler
        """
        _ = platform_dir  # Mark as intentionally unused

        # PRIORITY 1: Try slug-based detection first (most reliable)
        slug_based_handler = cls.create_handler(slug)
        if slug_based_handler.__class__.__name__ != "DefaultHandler":
            logger.info(
                f"Detected OEM for {slug} based on slug: {slug_based_handler.__class__.__name__}"
            )
            return slug_based_handler

        # PRIORITY 2: Theme content analysis REMOVED to avoid false positives
        # We now strictly rely on slug matching or explicit dealer info.
        return slug_based_handler
