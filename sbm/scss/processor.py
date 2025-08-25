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

from sbm.utils.helpers import darken_hex, lighten_hex
from sbm.utils.logger import logger
from sbm.utils.path import get_common_theme_path, get_dealer_theme_dir

from .classifiers import ProfessionalStyleClassifier, StyleClassifier, robust_css_processing
from .mixin_parser import CommonThemeMixinParser


class SCSSProcessor:
    """
    Transforms legacy SCSS to modern, Site-Builder-compatible SCSS
    by using an intelligent mixin parser and targeted transformations.
    """

    def __init__(self, slug: str, exclude_nav_styles: bool = True) -> None:
        self.slug = slug
        self.theme_dir = get_dealer_theme_dir(slug)
        self.common_theme_path = get_common_theme_path()
        self.exclude_nav_styles = exclude_nav_styles
        logger.info(f"SCSS Processor initialized for dealer: {self.slug}")
        self.mixin_parser = CommonThemeMixinParser()

        # Initialize style classifier for header/footer/nav exclusion
        if self.exclude_nav_styles:
            try:
                # Use professional parser for better accuracy with comma-separated selectors
                self.style_classifier = ProfessionalStyleClassifier(strict_mode=True)
                logger.info("Professional style exclusion enabled for header/footer/navigation components")
            except Exception as e:
                # Fallback to original classifier if professional parser not available
                self.style_classifier = StyleClassifier(strict_mode=True)
                logger.warning(f"Using fallback style classifier (professional parser failed: {e})")
                logger.info("Style exclusion enabled for header/footer/navigation components")

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
                # CRITICAL FIX: Don't convert SCSS functions to CSS custom properties
                # Skip variables that contain SCSS functions like map_keys(), map-get()
                if any(func in var_value for func in ['map_keys', 'map-get', 'map-']):
                    logger.warning(f"Skipping variable with SCSS function: {var_name}")
                    continue
                
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
        return self._convert_scss_variables_intelligently(content)

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

            # CRITICAL FIX: Handle @each loops properly
            if "@each" in stripped and "$types" in stripped:
                # Fix undefined variable reference
                lines[i] = line.replace("$types", "map-keys($font-types)")
                continue

            # Skip conversion for SCSS internal logic BUT allow variable conversion inside maps
            if (
                inside_mixin or stripped.startswith(("@each", "@for", "@if", "@else", "%#")) or "map-get(" in stripped or "map-keys(" in stripped
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

    def _clean_comment_blocks(self, content: str) -> str:
        """
        Remove large comment blocks and section dividers that clutter PR diffs.
        """
        logger.info("Cleaning up large comment blocks and section dividers...")

        # Remove large asterisk comment blocks like:
        # // *************************************************************************************************
        # //    HEADER
        # // *************************************************************************************************
        content = re.sub(r"// \*{20,}\n//.*?\n// \*{20,}\n", "", content, flags=re.MULTILINE)

        # Remove unicode box drawing comment blocks like:
        # //▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀
        # // _MapRow
        # //▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄
        content = re.sub(r"//[▀▄]{20,}\n.*?\n//[▀▄]{20,}\n", "", content, flags=re.MULTILINE)

        # Remove standalone comment lines that are just section markers
        content = re.sub(r"^//\s*$\n", "", content, flags=re.MULTILINE)

        # Remove excessive blank lines (more than 2 consecutive)
        content = re.sub(r"\n\s*\n\s*\n+", "\n\n", content)

        return content

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
        return unquoted_pattern.sub(r'url("\1")', content)


    def _remove_imports(self, content: str) -> str:
        """
        Removes all @import statements from the SCSS content.
        """
        # Logic to remove all @import lines
        return re.sub(r"@import\s+.*?;", "", content)

    def _convert_scss_functions(self, content: str) -> str:
        """
        Convert SCSS functions to CSS-compatible equivalents.

        Handles two main cases:
        1. SCSS functions with CSS variables (e.g., lighten(var(--primary), 20%))
        2. SCSS functions with hardcoded colors (e.g., lighten(#252525, 2%))
        """
        logger.info("Converting SCSS functions to CSS-compatible equivalents...")

        # CRITICAL FIX: Handle color keywords in SCSS functions
        # Replace color keywords with variables before processing
        color_mappings = {
            'green': '#008000',
            'red': '#ff0000', 
            'blue': '#0000ff',
            'black': '#000000',
            'white': '#ffffff'
        }

        for color_name, hex_value in color_mappings.items():
            # Fix darken(green,10%) -> darken(#008000,10%)
            content = content.replace(f'darken({color_name}', f'darken({hex_value}')
            content = content.replace(f'lighten({color_name}', f'lighten({hex_value}')

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
        def replace_lighten(match) -> str:
            hex_color = match.group(2)
            percentage = int(match.group(3))
            lightened = lighten_hex(hex_color, percentage)
            return f"{match.group(1)}color: {lightened};"

        content = re.sub(
            r"(\s+)color:\s*lighten\((#[a-fA-F0-9]{3,6}),\s*(\d+)%\);", replace_lighten, content
        )

        # darken(#00ccfe, 10%) -> #00b8e6
        def replace_darken(match) -> str:
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
        return re.sub(r"//\s*background:\s*rgba\(var\(--[^)]+\),\s*[\d.]+\);", "", content)


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
            # Step 0: Inject required utility functions at the start
            utility_functions = """
// Auto-generated utility functions
@function em($pixels, $context: 16) {
  @return #{$pixels/$context}em;
}

@function rem($pixels, $context: 16) {
  @return #{$pixels/$context}rem;
}

"""
            content = utility_functions + content
            # Step 0: Filter out header/footer/navigation styles (CRITICAL for Site Builder)
            if self.exclude_nav_styles:
                logger.info("Filtering header/footer/navigation styles for Site Builder compatibility...")

                try:
                    # Try the configured classifier first
                    content, exclusion_result = self.style_classifier.filter_scss_content(content)
                except Exception as e:
                    logger.warning(f"Style classifier failed: {e}, using robust processing")
                    # Use robust processing as ultimate fallback
                    content, exclusion_result = robust_css_processing(content)

                if exclusion_result.excluded_count > 0:
                    logger.info(f"Excluded {exclusion_result.excluded_count} header/footer/nav rules from migration")
                    for category, count in exclusion_result.patterns_matched.items():
                        logger.info(f"  - {category}: {count} rules")
                else:
                    logger.info("No header/footer/navigation styles found to exclude")

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

            # Step 5: Clean up large comment blocks and section dividers
            processed_content = self._clean_comment_blocks(processed_content)

            # Step 6: Trim whitespace for a clean final output
            return self._trim_whitespace(processed_content)


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

    def light_cleanup_scss_content(self, content: str) -> str:
        """
        Apply minimal cleanup to manually-edited SCSS content without reprocessing from source.
        This preserves manual fixes while ensuring consistent formatting.
        
        Args:
            content: The manually-edited SCSS content
            
        Returns:
            str: Lightly cleaned SCSS content
        """
        if not content.strip():
            return content

        try:
            # Only apply minimal transformations that don't break manual fixes
            processed_content = content

            # 1. Normalize line endings
            processed_content = processed_content.replace("\r\n", "\n").replace("\r", "\n")

            # 2. Remove excessive whitespace (but preserve intentional spacing)
            processed_content = re.sub(r"\n\s*\n\s*\n", "\n\n", processed_content)  # Max 2 consecutive newlines

            # 3. Ensure proper spacing around braces (but preserve SCSS interpolation #{...})
            # First protect SCSS interpolation completely by temporarily replacing it
            interpolation_matches = re.findall(r"#\{[^}]*\}", processed_content)
            protected_content = processed_content
            for i, match in enumerate(interpolation_matches):
                protected_content = protected_content.replace(match, f"SCSS_INTERPOLATION_{i}", 1)
            
            # Apply spacing rules to protected content
            protected_content = re.sub(r"(\S)\{", r"\1 {", protected_content)  # Space before {
            protected_content = re.sub(r"\}(\S)", r"} \1", protected_content)   # Space after }
            
            # Restore SCSS interpolation
            for i, match in enumerate(interpolation_matches):
                protected_content = protected_content.replace(f"SCSS_INTERPOLATION_{i}", match)
            processed_content = protected_content

            # 4. Convert SCSS variables to CSS custom properties
            # This ensures any remaining SCSS variables get converted during light cleanup
            processed_content = self._convert_scss_variables_intelligently(processed_content)

            # 5. Basic variable cleanup (only if they look malformed)
            # Convert any obvious SCSS variable syntax errors
            processed_content = re.sub(r"\$([a-zA-Z-_]+)\s*=\s*", r"$\1: ", processed_content)  # Fix = to :

            # 7. Remove trailing whitespace from lines
            lines = processed_content.split("\n")
            cleaned_lines = [line.rstrip() for line in lines]
            processed_content = "\n".join(cleaned_lines)

            # 8. Ensure file ends with single newline
            processed_content = processed_content.rstrip() + "\n"

            logger.debug(f"Light cleanup applied to SCSS content ({len(content)} → {len(processed_content)} chars)")
            return processed_content

        except Exception as e:
            logger.warning(f"Light cleanup failed, returning original content: {e}")
            return content

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

    def reprocess_scss_content(self, content: str) -> str:
        """
        Apply comprehensive transformations to existing Site Builder SCSS content
        without resetting from source. This is specifically for the reprocess workflow.
        """
        logger.debug("Applying reprocess transformations to existing SB content...")
        
        try:
            # Skip utility function injection if already present
            if "@function em(" not in content:
                utility_functions = """// Auto-generated utility functions
@function em($pixels, $context: 16) {
  @return #{$pixels/$context}em;
}

@function rem($pixels, $context: 16) {
  @return #{$pixels/$context}rem;
}

"""
                content = utility_functions + content
            
            # Apply the same transformations as migration but on existing content
            # Step 1: Process SCSS variables into CSS custom properties
            content = self._process_scss_variables(content)
            
            # Step 2: Convert relative image paths to absolute paths  
            content = self._convert_image_paths(content)
            
            # Step 3: Convert SCSS functions to CSS-compatible equivalents
            content = self._convert_scss_functions(content)
            
            # Step 4: Convert mixins using the intelligent parser
            logger.debug("Converting mixins to CSS for reprocess...")
            content, errors, unconverted = self.mixin_parser.parse_and_convert_mixins(content)
            if errors:
                logger.debug(f"Mixin conversion errors during reprocess: {len(errors)}")
            if unconverted:
                logger.debug(f"Unconverted mixins during reprocess: {len(unconverted)}")
            
            # Step 5: Final cleanup of any remaining SCSS variable references
            content = self._final_reprocess_cleanup(content)
            
            # Step 6: Basic formatting cleanup
            content = self._trim_whitespace(content)
            
            return content
            
        except Exception as e:
            logger.warning(f"Reprocess transformations failed, using light cleanup: {e}")
            # Fallback to light cleanup if reprocess fails
            return self.light_cleanup_scss_content(content)
    
    def _final_reprocess_cleanup(self, content: str) -> str:
        """
        Final cleanup specifically for reprocessing to catch any remaining SCSS variables.
        """
        lines = content.split('\n')
        processed_lines = []
        
        for line in lines:
            # Skip SCSS internal logic
            if ('#{' in line or line.strip().startswith('@mixin') or 
                line.strip().startswith('@function') or line.strip().startswith('@each')):
                processed_lines.append(line)
                continue
            
            # Convert remaining SCSS variables in CSS property contexts
            if ':' in line and '$' in line and not line.strip().startswith('$'):
                # Convert $variable to var(--variable) in CSS values
                line = re.sub(r'\$([a-zA-Z][\w-]*)', r'var(--\1)', line)
            
            processed_lines.append(line)
        
        return '\n'.join(processed_lines)
