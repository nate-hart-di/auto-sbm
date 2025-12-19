"""
Built-in SCSS formatter for the SBM tool.

This module provides a reliable, zero-dependency SCSS formatter that works
regardless of the user's environment or installed tools.

The formatter handles:
- Consistent indentation (configurable, default 2 spaces)
- Proper spacing around braces
- Normalized whitespace
- Preserved comments
- SCSS-specific syntax (nesting, variables, mixins, etc.)
"""

import re
from typing import Optional

from sbm.utils.logger import logger


class SCSSFormatter:
    """
    A reliable SCSS formatter that produces consistent output.

    Works by tracking brace depth and applying proper indentation
    while preserving SCSS-specific syntax.
    """

    def __init__(self, indent_size: int = 2, indent_char: str = " ") -> None:
        """
        Initialize the formatter.

        Args:
            indent_size: Number of indent characters per level (default: 2)
            indent_char: Character to use for indentation (default: space)
        """
        self.indent_size = indent_size
        self.indent_char = indent_char
        self.indent_unit = indent_char * indent_size

    def format(self, content: str) -> str:
        """
        Format SCSS content with consistent indentation and spacing.

        Args:
            content: Raw SCSS content

        Returns:
            Formatted SCSS content
        """
        if not content or not content.strip():
            return content

        try:
            # Normalize line endings
            content = content.replace("\r\n", "\n").replace("\r", "\n")

            # Process the content
            lines = content.split("\n")
            formatted_lines = []
            depth = 0
            in_multiline_comment = False
            in_multiline_value = False

            for i, line in enumerate(lines):
                original_line = line
                stripped = line.strip()

                # Skip empty lines but preserve them
                if not stripped:
                    # Don't add multiple consecutive blank lines
                    if formatted_lines and formatted_lines[-1].strip() == "":
                        continue
                    formatted_lines.append("")
                    continue

                # Handle multiline comments
                if "/*" in stripped and "*/" not in stripped:
                    in_multiline_comment = True
                if "*/" in stripped:
                    in_multiline_comment = False

                # Handle multiline values (e.g., long background gradients)
                if in_multiline_value:
                    if stripped.endswith(";"):
                        in_multiline_value = False
                    formatted_lines.append(self.indent_unit * (depth + 1) + stripped)
                    continue

                # Check for opening/closing braces to adjust depth
                open_braces = stripped.count("{") - stripped.count("#{")  # Exclude interpolation
                close_braces = stripped.count("}")

                # Adjust depth for closing braces BEFORE indenting this line
                if stripped.startswith("}") or stripped == "}":
                    depth = max(0, depth - 1)

                # Apply indentation
                if in_multiline_comment and not stripped.startswith("/*"):
                    # Preserve comment indentation style
                    formatted_line = self.indent_unit * depth + " " + stripped
                else:
                    formatted_line = self.indent_unit * depth + stripped

                # Ensure space before opening brace (but not for interpolation)
                formatted_line = re.sub(r'(\S)\{(?!\{)', r'\1 {', formatted_line)

                # Ensure space after closing brace if followed by content (except semicolon)
                formatted_line = re.sub(r'\}([^\s\};,])', r'} \1', formatted_line)

                formatted_lines.append(formatted_line)

                # Adjust depth for opening braces AFTER processing this line
                depth += open_braces
                # Handle closing braces that aren't at the start of line
                if close_braces > 0 and not stripped.startswith("}"):
                    depth = max(0, depth - close_braces)

                # Check if this starts a multiline value
                if ":" in stripped and not stripped.endswith(";") and not stripped.endswith("{") and not stripped.endswith(","):
                    # Could be multiline, but only if next line continues it
                    pass

            # Join and clean up
            result = "\n".join(formatted_lines)

            # Final cleanup
            result = self._final_cleanup(result)

            return result

        except Exception as e:
            logger.warning(f"SCSS formatting failed, returning original: {e}")
            return content

    def _final_cleanup(self, content: str) -> str:
        """Apply final cleanup passes to the formatted content."""
        # Remove trailing whitespace from lines
        lines = content.split("\n")
        lines = [line.rstrip() for line in lines]

        # Remove excessive blank lines (max 1 consecutive)
        cleaned_lines = []
        prev_blank = False
        for line in lines:
            is_blank = line.strip() == ""
            if is_blank and prev_blank:
                continue
            cleaned_lines.append(line)
            prev_blank = is_blank

        # Ensure single newline at end
        result = "\n".join(cleaned_lines)
        result = result.rstrip() + "\n"

        return result


def format_scss_file(file_path: str, indent_size: int = 2) -> bool:
    """
    Format an SCSS file in place.

    Args:
        file_path: Path to the SCSS file
        indent_size: Number of spaces per indent level

    Returns:
        True if formatting succeeded, False otherwise
    """
    try:
        from pathlib import Path

        path = Path(file_path)
        if not path.exists():
            logger.warning(f"File not found for formatting: {file_path}")
            return False

        content = path.read_text(encoding="utf-8", errors="ignore")

        formatter = SCSSFormatter(indent_size=indent_size)
        formatted = formatter.format(content)

        # Only write if content changed
        if formatted != content:
            path.write_text(formatted, encoding="utf-8")
            logger.debug(f"Formatted: {path.name}")
        else:
            logger.debug(f"No changes needed: {path.name}")

        return True

    except Exception as e:
        logger.warning(f"Failed to format {file_path}: {e}")
        return False


def format_scss_content(content: str, indent_size: int = 2) -> str:
    """
    Format SCSS content string.

    Args:
        content: SCSS content to format
        indent_size: Number of spaces per indent level

    Returns:
        Formatted SCSS content
    """
    formatter = SCSSFormatter(indent_size=indent_size)
    return formatter.format(content)


def format_all_scss_files(theme_dir: str, indent_size: int = 2) -> bool:
    """
    Format all sb-*.scss files in a theme directory.

    Args:
        theme_dir: Path to the theme directory
        indent_size: Number of spaces per indent level

    Returns:
        True if all files formatted successfully
    """
    try:
        from pathlib import Path

        theme_path = Path(theme_dir)
        if not theme_path.exists():
            logger.warning(f"Theme directory not found: {theme_dir}")
            return False

        scss_files = list(theme_path.glob("sb-*.scss"))
        if not scss_files:
            logger.info("No sb-*.scss files found to format")
            return True

        logger.info(f"Formatting {len(scss_files)} SCSS files...")

        success = True
        for scss_file in scss_files:
            if not format_scss_file(str(scss_file), indent_size):
                success = False

        if success:
            logger.info(f"Successfully formatted {len(scss_files)} SCSS files")

        return success

    except Exception as e:
        logger.error(f"Failed to format SCSS files: {e}")
        return False
