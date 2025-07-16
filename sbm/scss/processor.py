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
from ..utils.helpers import lighten_hex, darken_hex
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

    def validate_scss_syntax(self, content: str) -> (bool, Optional[str]):
        """
        Validates basic SCSS syntax by checking for balanced braces.
        """
        opening_braces = content.count('{')
        closing_braces = content.count('}')

        if opening_braces == closing_braces:
            return True, None
        else:
            return False, f"Mismatched braces: {opening_braces} opening, {closing_braces} closing"

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

    def _convert_scss_functions(self, content: str) -> str:
        """
        Convert SCSS functions to CSS-compatible equivalents.
        
        Handles two main cases:
        1. SCSS functions with CSS variables (e.g., lighten(var(--primary), 20%))
        2. SCSS functions with hardcoded colors (e.g., lighten(#252525, 2%))
        """
        logger.info("Converting SCSS functions to CSS-compatible equivalents...")
        
        # Case 1: SCSS functions with CSS variables - convert to CSS-compatible equivalents
        # These appear in raw SCSS content (not from mixins) and need to be handled
        
        # Convert SCSS variables to CSS variables
        # $primary -> var(--primary)
        content = re.sub(r'\$([a-zA-Z_][a-zA-Z0-9_-]*)', r'var(--\1)', content)
        
        
        # Case 2: SCSS functions with hardcoded hex colors - pre-calculate
        # lighten(#252525, 2%) -> #2a2a2a
        def replace_lighten(match):
            hex_color = match.group(2)
            percentage = int(match.group(3))
            lightened = lighten_hex(hex_color, percentage)
            return f"{match.group(1)}color: {lightened};"
        
        content = re.sub(
            r'(\s+)color:\s*lighten\((#[a-fA-F0-9]{3,6}),\s*(\d+)%\);',
            replace_lighten,
            content
        )
        
        # darken(#00ccfe, 10%) -> #00b8e6
        def replace_darken(match):
            hex_color = match.group(2)
            percentage = int(match.group(3))
            darkened = darken_hex(hex_color, percentage)
            return f"{match.group(1)}{match.group(4)}: {darkened};"
        
        content = re.sub(
            r'(\s+)(background|background-color):\s*darken\((#[a-fA-F0-9]{3,6}),\s*(\d+)%\);',
            lambda m: f"{m.group(1)}{m.group(2)}: {darken_hex(m.group(3), int(m.group(4)))};",
            content
        )
        
        # Handle background: lighten() cases
        content = re.sub(
            r'(\s+)background:\s*lighten\((#[a-fA-F0-9]{3,6}),\s*(\d+)%\);',
            lambda m: f"{m.group(1)}background: {lighten_hex(m.group(2), int(m.group(3)))};",
            content
        )
        
        # Fix malformed property declarations like "font-family: var(--weight): 300;"
        # This separates them into proper CSS declarations
        content = re.sub(
            r'(\s+)font-family:\s*var\(--([^)]+)\):\s*(\d+);',
            r'\1font-family: var(--\2);\n\1font-weight: \3;',
            content
        )
        
        # Remove any commented-out broken code patterns
        content = re.sub(
            r'//\s*background:\s*rgba\(var\(--[^)]+\),\s*[\d.]+\);',
            '',
            content
        )
        
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

            # Step 2.5: Convert SCSS functions to CSS-compatible equivalents
            content = self._convert_scss_functions(content)

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
