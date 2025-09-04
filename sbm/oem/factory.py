"""
Factory for creating OEM handlers.

This module provides a factory for creating the appropriate OEM handler
based on dealer information.
"""

import os
import re
from pathlib import Path

from sbm.utils.logger import logger

from .default import DefaultHandler
from .stellantis import StellantisHandler
from .kia import KiaHandler


class OEMFactory:
    """
    Factory for creating OEM handlers based on dealer information.
    """

    # List of all available handlers
    _handlers = [
        StellantisHandler,
        KiaHandler,
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
        Detect the OEM from the dealer slug first, then fallback to theme content analysis.
        
        Priority order:
        1. Slug-based detection (most reliable)
        2. Theme content analysis (fallback for ambiguous cases)

        Args:
            slug (str): Dealer theme slug
            platform_dir (str, optional): Path to the platform directory

        Returns:
            BaseOEMHandler: An instance of the appropriate OEM handler
        """
        
        # PRIORITY 1: Try slug-based detection first (most reliable)
        slug_based_handler = cls.create_handler(slug)
        if slug_based_handler.__class__.__name__ != "DefaultHandler":
            logger.info(f"Detected OEM for {slug} based on slug: {slug_based_handler.__class__.__name__}")
            return slug_based_handler
        
        # PRIORITY 2: Slug didn't match known patterns, try theme content analysis as fallback
        logger.debug(f"Slug '{slug}' didn't match known patterns, analyzing theme content...")
        
        if not platform_dir:
            platform_dir = os.environ.get("DI_WEBSITES_PLATFORM_DIR", "")
            if not platform_dir:
                logger.warning("Platform directory not set, unable to detect OEM from theme")
                return cls.create_handler(slug)

        theme_dir = Path(platform_dir) / "dealer-themes" / slug

        # Check if the theme directory exists (skip warning since git checkout happens later)
        if not theme_dir.exists():
            logger.debug(
                f"Theme directory not found at {theme_dir} (will be available after git checkout)"
            )
            return cls.create_handler(slug)

        # Look for OEM-specific indicators in files
        indicators = {}

        # Check functions.php for OEM-specific code (excluding migration-added content)
        functions_file = theme_dir / "functions.php"
        if functions_file.exists():
            with open(functions_file, encoding="utf-8", errors="ignore") as f:
                content = f.read().lower()
                
                # Filter out migration-generated content to avoid false positives
                content = cls._filter_migration_content(content)

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

        # Also check other theme files (excluding sb-* migration files)
        theme_files = [
            "style.scss",
            "inside.scss", 
            "_support-requests.scss",
            "lvdp.scss",
            "lvrp.scss"
        ]
        
        css_dir = theme_dir / "css"
        for filename in theme_files:
            file_path = css_dir / filename
            if file_path.exists():
                try:
                    with open(file_path, encoding="utf-8", errors="ignore") as f:
                        content = f.read().lower()
                        original_content_preview = content[:200].replace('\n', ' ')
                        content = cls._filter_migration_content(content)
                        filtered_content_preview = content[:200].replace('\n', ' ')
                        
                        logger.debug(f"OEM Detection for {filename}: Original='{original_content_preview}...' Filtered='{filtered_content_preview}...'")
                        
                        for handler_class in cls._handlers:
                            handler = handler_class(slug)
                            patterns = handler.get_brand_match_patterns()
                            
                            matches = 0
                            matched_patterns = []
                            for pattern in patterns:
                                pattern_matches = re.findall(pattern, content, re.IGNORECASE)
                                matches += len(pattern_matches)
                                if pattern_matches:
                                    matched_patterns.append(f"{pattern}: {pattern_matches}")

                            if matches > 0:
                                logger.debug(f"OEM Detection: {handler_class.__name__} found {matches} matches in {filename}: {matched_patterns}")
                                indicators[handler_class.__name__] = (
                                    indicators.get(handler_class.__name__, 0) + matches
                                )
                except Exception as e:
                    logger.debug(f"Could not read {filename}: {e}")
        
        # Re-evaluate best match after checking all files (fallback only)
        if indicators:
            best_match = max(indicators.items(), key=lambda x: x[1])
            logger.info(f"Detected OEM for {slug} based on theme content: {best_match[0]}")

            # Create the appropriate handler
            for handler_class in cls._handlers:
                if handler_class.__name__ == best_match[0]:
                    return handler_class(slug)

        # If no indicators were found, fall back to the create_handler method
        return cls.create_handler(slug)

    @classmethod
    def _filter_migration_content(cls, content: str) -> str:
        """
        Filter out migration-generated content that could cause false OEM detection.
        
        Args:
            content: File content to filter
            
        Returns:
            Filtered content with migration artifacts removed
        """
        # Remove git commit messages and references that contain FCA/Stellantis keywords
        content = re.sub(r'(?i)added fca[^\n]*', '', content)
        content = re.sub(r'(?i)fca direction row styles[^\n]*', '', content)  
        content = re.sub(r'(?i)fca cookie banner[^\n]*', '', content)
        
        # Remove Site Builder file references
        content = re.sub(r'sb-[a-z]+\.scss', '', content)
        
        # Remove migration tool comments and artifacts
        content = re.sub(r'(?i)auto-generated[^\n]*', '', content)
        
        # Remove SCSS import statements that contain Stellantis/FCA paths (major contamination source)
        content = re.sub(r'@import[^;]*dealer-groups/fca[^;]*;', '', content, flags=re.IGNORECASE)
        content = re.sub(r'@import[^;]*dealer-groups/cdjr[^;]*;', '', content, flags=re.IGNORECASE)
        content = re.sub(r'@import[^;]*dealer-groups/stellantis[^;]*;', '', content, flags=re.IGNORECASE)
        
        # Remove any remaining references to stellantis, fca, cdjr patterns that are migration artifacts
        content = re.sub(r'(?i)\bstellantis\b[^\n]*migration[^\n]*', '', content)
        content = re.sub(r'(?i)\bfca\b[^\n]*migration[^\n]*', '', content)
        content = re.sub(r'(?i)\bcdjr\b[^\n]*migration[^\n]*', '', content)
        content = re.sub(r'(?i)migration tool[^\n]*', '', content)
        content = re.sub(r'(?i)site builder[^\n]*', '', content)
        
        return content
