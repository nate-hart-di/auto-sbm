"""
SCSS processor for the SBM tool.
This processor performs a targeted SCSS-to-SCSS transformation to produce
a clean, self-contained SCSS file with no external @import statements.
"""
import os
import re
from typing import Dict, List, Optional

from ..utils.logger import logger
from ..utils.path import get_dealer_theme_dir, get_common_theme_path
from .mixin_parser import CommonThemeMixinParser

class SCSSProcessor:
    """
    Transforms legacy SCSS to modern, Site-Builder-compatible SCSS
    by using an intelligent mixin parser and targeted transformations.
    """
    
    def __init__(self, slug: str):
        self.slug = slug
        self.theme_dir = get_dealer_theme_dir(slug)
        self.common_theme_path = get_common_theme_path()
        self.mixin_parser = CommonThemeMixinParser()

    def _convert_variables_to_css_vars(self, content: str) -> str:
        """
        Converts all SCSS variables to CSS custom properties (variables)
        for Site Builder compatibility using a generic pattern.
        """
        logger.info("Converting all SCSS variables to CSS custom properties...")
        
        # Convert all SCSS variables ($foo) to CSS variables (var(--foo))
        content = re.sub(r'\$([\w-]+)', r'var(--\1)', content)
        
        # Remove the now-unused SCSS variable declaration lines.
        content = re.sub(r'^\s*\$[\w-]+\s*:.*?;', '', content, flags=re.MULTILINE)

        return content

    def _convert_image_paths(self, content: str) -> str:
        """
        Converts relative image paths to absolute Site Builder paths.
        e.g., ../images/foo.jpg -> /wp-content/themes/DealerInspireDealerTheme/images/foo.jpg
        """
        logger.info("Converting relative image paths...")
        
        path_pattern = re.compile(r"url\((['\"]?)\.\.\/images\/(.*?)(['\"]?)\)")
        replacement = r"url(\1/wp-content/themes/DealerInspireDealerTheme/images/\2\3)"
        
        content = path_pattern.sub(replacement, content)
        
        return content

    def _remove_imports(self, content: str) -> str:
        """
        Removes all @import statements from the SCSS content.
        """
        # Logic to remove all @import lines
        content = re.sub(r'@import\s+.*?;', '', content)
        return content

    def transform_scss_content(self, content: str) -> str:
        """
        Performs transformations on SCSS content.
        """
        logger.info(f"Performing SCSS transformation for {self.slug}...")

        try:
            # Step 1: Convert SCSS variables to CSS variables (var(--...))
            content = self._convert_variables_to_css_vars(content)

            # Step 2: Convert relative image paths to absolute paths
            content = self._convert_image_paths(content)

            # Step 3: Convert all @include mixins using the intelligent parser
            logger.info("Converting mixins to CSS...")
            content, errors, unconverted = self.mixin_parser.parse_and_convert_mixins(content)
            if errors:
                logger.warning(f"Encountered {len(errors)} errors during mixin conversion.")
                for error in errors:
                    logger.debug(f"Mixin conversion error: {error}")
            if unconverted:
                logger.warning(f"Could not convert {len(unconverted)} mixins.")
                for mixin in unconverted:
                    logger.debug(f"Unconverted mixin: {mixin}")
            
            # Step 4: Remove imports
            processed_content = self._remove_imports(content)
            
            return processed_content
            
        except Exception as e:
            logger.error(f"An unexpected error occurred during SCSS processing for {self.slug}.", exc_info=True)
            return f"/* SBM: UNEXPECTED ERROR. CHECK LOGS. ERROR: {e} */\n{content}"

    def process_scss_file(self, file_path: str) -> str:
        """
        Reads an SCSS file and applies transformations.
        """
        if not os.path.exists(file_path):
            logger.warning(f"File not found, skipping: {file_path}")
            return ""
            
        with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        
        return self.transform_scss_content(content)
    
    def write_files_atomically(self, theme_dir: str, files: Dict[str, str]) -> bool:
        """
        Writes the transformed SCSS files to the theme directory.
        """
        try:
            for name, content in files.items():
                if not content:
                    logger.info(f"Skipping empty file: {name}")
                    continue
                
                final_path = os.path.join(theme_dir, name)
                with open(final_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                logger.info(f"Successfully wrote {final_path}")
            return True
        except Exception as e:
            logger.error(f"Error writing files atomically: {e}", exc_info=True)
            return False
