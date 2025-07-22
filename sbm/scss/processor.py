"""
SCSS processor for the SBM tool.
This processor performs a targeted SCSS-to-SCSS transformation to produce
a clean, self-contained SCSS file with no external @import statements.
"""

import os
import re
import subprocess
import tempfile
from typing import Dict, Optional

from ..utils.helpers import darken_hex, lighten_hex
from ..utils.logger import logger
from ..utils.path import get_common_theme_path, get_dealer_theme_dir
from .mixin_parser import CommonThemeMixinParser
from .classifiers import StyleClassifier


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
        self.style_classifier = StyleClassifier()

    def _process_scss_variables(self, content: str) -> str:
        """
        Processes SCSS variables by moving them to a :root block as CSS custom properties.
        """
        logger.info("Processing SCSS variables into CSS custom properties...")

        # Find all root-level SCSS variable declarations (e.g., "$primary: #000;")
        declarations = re.findall(r"^\s*(\$[\w-]+)\s*:\s*(.*?);", content, flags=re.MULTILINE)

        # Remove the original SCSS variable declaration lines from the main content
        content = re.sub(r"^\s*\$[\w-]+\s*:.*?;", "", content, flags=re.MULTILINE)

        root_properties = []
        if declarations:
            for var_name, var_value in declarations:
                # Convert to CSS custom property format (e.g., --primary: #000;)
                prop_name = var_name.replace("$", "--")
                # Important: Convert any variables used in the value of another variable
                var_value = re.sub(r"\$([\w-]+)", r"var(--\1)", var_value)
                root_properties.append(f"  {prop_name}: {var_value};")

            # Assemble the final :root block
            root_block = ":root {\n" + "\n".join(root_properties) + "\n}\n\n"
            # Prepend the new :root block to the content
            content = root_block + content.lstrip()

        # Finally, convert SCSS variable usages to CSS custom properties
        # BUT exclude SCSS internal logic (mixins, maps, loops, functions)
        content = self._convert_scss_variables_intelligently(content)
        return content

    def _convert_scss_variables_intelligently(self, content: str) -> str:
        """
        Convert SCSS variables to CSS custom properties, but only in appropriate contexts.
        Excludes SCSS internal logic like mixin parameters, maps, loops, and functions.
        """
        lines = content.split("\n")
        inside_mixin = False
        inside_map = False
        brace_depth = 0

        for i, line in enumerate(lines):
            stripped = line.strip()
            original_line = line

            # Track brace depth for nested structures
            brace_depth += line.count("{") - line.count("}")

            # Check if we're entering a mixin definition
            if stripped.startswith("@mixin"):
                inside_mixin = True
                continue

            # Check if we're exiting a mixin definition
            if inside_mixin and stripped == "}" and brace_depth == 0:
                inside_mixin = False
                continue

            # Check if we're in a map definition
            if ":" in stripped and "(" in stripped and not inside_mixin:
                if re.match(r"^\s*\$[\w-]+\s*:\s*\(", stripped):
                    inside_map = True
                    continue

            # Check if we're exiting a map definition
            elif inside_map and stripped.endswith(");"):
                inside_map = False
                continue

            # Skip conversion for SCSS internal logic BUT allow variable conversion inside maps
            if (
                inside_mixin
                or stripped.startswith("@each")
                or stripped.startswith("@for")
                or stripped.startswith("@if")
                or stripped.startswith("@else")
                or "map-get(" in stripped
                or "map-keys(" in stripped
                or stripped.startswith("%#")
            ):
                continue

            # Convert variables inside maps
            if inside_map:
                lines[i] = re.sub(r"\$([a-zA-Z][\w-]*)", r"var(--\1)", line)
                continue

            # Convert variables in CSS property contexts only
            # Look for patterns like "property: $variable" but exclude SCSS variable assignments and interpolation
            if (
                ":" in stripped
                and not stripped.startswith("@")
                and not re.match(r"^\s*\$[\w-]+\s*:", stripped)
            ):
                # Don't convert variables inside interpolation #{...}
                if "#{" in line:
                    # Split line into parts, only convert variables outside interpolation
                    parts = re.split(r"(#\{[^}]*\})", line)
                    for j, part in enumerate(parts):
                        if not part.startswith("#{"):
                            parts[j] = re.sub(r"\$([\w-]+)", r"var(--\1)", part)
                    lines[i] = "".join(parts)
                else:
                    lines[i] = re.sub(r"\$([\w-]+)", r"var(--\1)", line)

        return "\n".join(lines)

    def _trim_whitespace(self, content: str) -> str:
        """
        Removes excess whitespace and blank lines from the final output.
        """
        logger.info("Trimming whitespace from final output...")
        # Replace multiple blank lines with a single one
        content = re.sub(r"\n\s*\n", "\n\n", content)
        # Remove leading/trailing whitespace
        return content.strip()

    def validate_scss_syntax(self, content: str) -> (bool, Optional[str]):
        """
        Validates basic SCSS syntax by checking for balanced braces.
        """
        opening_braces = content.count("{")
        closing_braces = content.count("}")

        if opening_braces == closing_braces:
            return True, None
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
            content,
        )

        # A second pass to catch any unquoted, already-absolute paths that were missed
        unquoted_pattern = re.compile(
            r"url\((/wp-content/themes/DealerInspireDealerTheme/images/[^)]+)\)"
        )
        content = unquoted_pattern.sub(r'url("\1")', content)

        return content

    def _remove_imports(self, content: str) -> str:
        """
        Removes all @import statements from the SCSS content.
        """
        # Logic to remove all @import lines
        content = re.sub(r"@import\s+.*?;", "", content)
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

        # Convert SCSS variables to CSS variables using intelligent conversion
        content = self._convert_scss_variables_intelligently(content)

        # Handle SCSS functions that can't work with CSS variables
        # lighten(var(--primary), 20%) -> var(--primary) (remove the function)
        content = re.sub(r"lighten\(var\(--([^)]+)\),\s*\d+%\)", r"var(--\1)", content)
        content = re.sub(r"darken\(var\(--([^)]+)\),\s*\d+%\)", r"var(--\1)", content)

        # Case 2: SCSS functions with hardcoded hex colors - pre-calculate
        # lighten(#252525, 2%) -> #2a2a2a
        def replace_lighten(match):
            hex_color = match.group(2)
            percentage = int(match.group(3))
            lightened = lighten_hex(hex_color, percentage)
            return f"{match.group(1)}color: {lightened};"

        content = re.sub(
            r"(\s+)color:\s*lighten\((#[a-fA-F0-9]{3,6}),\s*(\d+)%\);", replace_lighten, content
        )

        # darken(#00ccfe, 10%) -> #00b8e6
        def replace_darken(match):
            hex_color = match.group(2)
            percentage = int(match.group(3))
            darkened = darken_hex(hex_color, percentage)
            return f"{match.group(1)}{match.group(4)}: {darkened};"

        content = re.sub(
            r"(\s+)(background|background-color):\s*darken\((#[a-fA-F0-9]{3,6}),\s*(\d+)%\);",
            lambda m: f"{m.group(1)}{m.group(2)}: {darken_hex(m.group(3), int(m.group(4)))};",
            content,
        )

        # Handle background: lighten() cases
        content = re.sub(
            r"(\s+)background:\s*lighten\((#[a-fA-F0-9]{3,6}),\s*(\d+)%\);",
            lambda m: f"{m.group(1)}background: {lighten_hex(m.group(2), int(m.group(3)))};",
            content,
        )

        # Fix malformed property declarations like "font-family: var(--weight): 300;"
        # This separates them into proper CSS declarations
        content = re.sub(
            r"(\s+)font-family:\s*var\(--([^)]+)\):\s*(\d+);",
            r"\1font-family: var(--\2);\n\1font-weight: \3;",
            content,
        )

        # Remove any commented-out broken code patterns
        content = re.sub(r"//\s*background:\s*rgba\(var\(--[^)]+\),\s*[\d.]+\);", "", content)

        return content

    def _verify_scss_compilation(self, content: str) -> bool:
        """
        Verify that SCSS content compiles successfully using Dart Sass.
        Returns True if compilation succeeds, False otherwise.
        """
        try:
            # Create a temporary file with the SCSS content
            with tempfile.NamedTemporaryFile(mode="w", suffix=".scss", delete=False) as temp_file:
                temp_file.write(content)
                temp_file_path = temp_file.name

            # Try to compile with Dart Sass to a temporary output file
            with tempfile.NamedTemporaryFile(mode="w", suffix=".css", delete=False) as output_file:
                output_file_path = output_file.name

            result = subprocess.run(
                ["sass", "--no-source-map", temp_file_path, output_file_path],
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )

            # Clean up output file
            if os.path.exists(output_file_path):
                os.unlink(output_file_path)

            # Clean up temporary file
            os.unlink(temp_file_path)

            if result.returncode != 0:
                logger.error(f"SCSS compilation failed: {result.stderr}")
                return False

            logger.info("SCSS compilation verified successfully")
            return True

        except subprocess.TimeoutExpired:
            logger.error("SCSS compilation verification timed out")
            return False
        except FileNotFoundError:
            # Fallback: Sass not installed, do basic regex validation
            logger.warning("Sass compiler not found, using fallback validation")
            return self._fallback_validation(content)
        except Exception as e:
            logger.error(f"SCSS compilation verification failed: {e}")
            return False

    def _fallback_validation(self, content: str) -> bool:
        """
        Fallback validation using regex patterns when Sass compiler is unavailable.
        """
        issues = []

        # Check for remaining SCSS syntax that would cause compilation failures
        if re.search(r"@include\s+", content):
            issues.append("@include statements found")
        if re.search(r"\$[a-zA-Z]", content):
            issues.append("SCSS variables found")
        if re.search(r"(lighten|darken|mix)\(", content):
            issues.append("SCSS functions found")
        if re.search(r"@mixin\s+", content):
            issues.append("@mixin definitions found")

        if issues:
            logger.error(f"Fallback validation failed: {', '.join(issues)}")
            return False

        logger.info("Fallback validation passed")
        return True

    def transform_scss_content(self, content: str) -> str:
        """
        Performs transformations on SCSS content.
        """
        logger.info(f"Performing SCSS transformation for {self.slug}...")

        try:
            # Step 0: CRITICAL - Filter excluded header/footer/nav styles FIRST
            content, exclusions = self.style_classifier.filter_scss_content(content, self.slug)
            
            if exclusions:
                logger.info(f"Excluded {len(exclusions)} header/footer/nav styles from migration")
                logger.info(f"Exclusion summary: {self.style_classifier.get_exclusion_summary()}")
                for exclusion in exclusions[:5]:  # Log first 5 for verification
                    logger.debug(f"Excluded: {exclusion.selector} - {exclusion.pattern}")
            
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
            logger.error(
                f"An unexpected error occurred during SCSS processing for {self.slug}.",
                exc_info=True,
            )
            return f"/* SBM: UNEXPECTED ERROR. CHECK LOGS. ERROR: {e} */\n{content}"

    def process_scss_file(self, file_path: str) -> str:
        """
        Reads an SCSS file and applies transformations.
        """
        if not os.path.exists(file_path):
            logger.warning(f"File not found, skipping: {file_path}")
            return ""

        with open(file_path, encoding="utf-8") as f:
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
                with open(final_path, "w", encoding="utf-8") as f:
                    f.write(content)
                logger.info(f"Successfully wrote {final_path}")
            return True
        except Exception as e:
            logger.error(f"Error writing files atomically: {e}", exc_info=True)
            return False
