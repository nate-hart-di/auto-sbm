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
        logger.info(f"SCSS Processor initialized for dealer: {self.slug}")
        self.mixin_parser = CommonThemeMixinParser()

    def _process_scss_variables(self, content: str) -> str:
        """
        Processes SCSS variables by moving them to a :root block as CSS custom properties.
        """
        logger.info("Processing SCSS variables into CSS custom properties...")

        # Find all root-level SCSS variable declarations (e.g., "$primary: #000;")
        declarations = re.findall(r'^\s*(\$[\w-]+)\s*:\s*(.*?);', content, flags=re.MULTILINE)

        # Remove the original SCSS variable declaration lines from the main content
        content = re.sub(r'^\s*\$[\w-]+\s*:.*?;', '', content, flags=re.MULTILINE)

        root_properties = []
        if declarations:
            for var_name, var_value in declarations:
                # Convert to CSS custom property format (e.g., --primary: #000;)
                prop_name = var_name.replace('$', '--')
                # Important: Convert any variables used in the value of another variable
                var_value = re.sub(r'\$([\w-]+)', r'var(--\1)', var_value)
                root_properties.append(f"  {prop_name}: {var_value};")

            # Assemble the final :root block
            root_block = ":root {\n" + "\n".join(root_properties) + "\n}\n\n"
            # Prepend the new :root block to the content
            content = root_block + content.lstrip()

        # Finally, convert all remaining SCSS variable usages throughout the file
        content = re.sub(r'\$([\w-]+)', r'var(--\1)', content)
        return content

    def _trim_whitespace(self, content: str) -> str:
        """
        Removes excess whitespace and blank lines from the final output.
        """
        logger.info("Trimming whitespace from final output...")
        # Replace multiple blank lines with a single one
        content = re.sub(r'\n\s*\n', '\n\n', content)
        # Remove leading/trailing whitespace
        return content.strip()

    def _convert_image_paths(self, content: str) -> str:
        """
        Converts relative image paths to absolute Site Builder paths and ensures
        all URLs are consistently double-quoted.
        """
        logger.info("Converting relative image paths and enforcing quotes...")

        # Convert relative `../images/` paths to absolute, quoted paths
        content = re.sub(
            r"url\((['\"]?)\.\.\/images\/(.*?)(['\"]?)\)",
            r'url("/wp-content/themes/DealerInspireDealerTheme/images/\2")',
            content
        )

        # A second pass to catch any unquoted, already-absolute paths that were missed
        unquoted_pattern = re.compile(r'url\((/wp-content/themes/DealerInspireDealerTheme/images/[^)]+)\)')
        content = unquoted_pattern.sub(r'url("\1")', content)

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
            # Step 1: Process SCSS variables into a :root block and convert usage
            content = self._process_scss_variables(content)

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

            # Step 5: Trim whitespace for a clean final output
            processed_content = self._trim_whitespace(processed_content)
            
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
