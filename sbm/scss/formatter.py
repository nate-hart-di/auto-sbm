"""
Built-in SCSS formatter for the SBM tool.

Uses cssbeautifier (from jsbeautifier) to match VSCode's default CSS formatter behavior.
"""

from sbm.utils.logger import logger

try:
    from cssbeautifier import beautify as css_beautify

    BEAUTIFIER_AVAILABLE = True
except ImportError:
    BEAUTIFIER_AVAILABLE = False
    logger.warning("cssbeautifier not available, using basic formatting")


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
        Format SCSS content using cssbeautifier (matches VSCode default formatter).

        Args:
            content: Raw SCSS content

        Returns:
            Formatted SCSS content
        """
        if not content or not content.strip():
            return content

        try:
            if BEAUTIFIER_AVAILABLE:
                # Use cssbeautifier with settings matching VSCode defaults
                options = {
                    "indent_size": self.indent_size,
                    "indent_char": self.indent_char,
                    "selector_separator_newline": True,
                    "end_with_newline": True,
                    "newline_between_rules": True,
                    "space_around_combinator": True,
                }
                result = css_beautify(content, options)
                return result
            # Fallback to basic formatting
            return self._basic_format(content)

        except Exception as e:
            logger.warning(f"SCSS formatting failed, returning original: {e}")
            return content

    def _basic_format(self, content: str) -> str:
        """Basic fallback formatting if cssbeautifier unavailable."""
        # Normalize line endings
        content = content.replace("\r\n", "\n").replace("\r", "\n")

        # Remove trailing whitespace
        lines = [line.rstrip() for line in content.split("\n")]

        # Ensure single newline at end
        result = "\n".join(lines).rstrip() + "\n"

        return result

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
