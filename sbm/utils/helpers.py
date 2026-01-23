"""
Helper utilities for the SBM tool.

This module provides miscellaneous helper functions for the SBM tool.
"""

import re
from datetime import datetime


def validate_slug(slug: str) -> bool:
    """
    Validate that the slug contains only allowed characters.

    Args:
        slug (str): Dealer theme slug to validate

    Returns:
        bool: True if valid, False otherwise
    """
    if not slug:
        return False

    return not re.search(r"[^a-zA-Z0-9/_-]", slug)


def get_branch_name(slug: str) -> str:
    """
    Generate a standardized branch name for a migration.

    All Site Builder migrations use PCON-864 for Jira tracking.

    Args:
        slug (str): Dealer theme slug

    Returns:
        str: Branch name in the format pcon-864-{slug}-sbm{MMYY}

    Example:
        get_branch_name("centralmainechrysler") -> "pcon-864-centralmainechrysler-sbm1025"
    """
    current_date = datetime.now().strftime("%m%y")
    return f"pcon-864-{slug}-sbm{current_date}"


def extract_content_between_comments(content: str, start_marker: str, end_marker: str) -> str:
    """
    Extract content between specified comment markers.

    Args:
        content (str): Content to search in
        start_marker (str): Start marker comment
        end_marker (str): End marker comment

    Returns:
        str: Extracted content or empty string if not found
    """
    pattern = re.compile(f"{re.escape(start_marker)}(.*?){re.escape(end_marker)}", re.DOTALL)
    match = pattern.search(content)

    if match:
        return match.group(1).strip()

    return ""


def extract_nested_rule(content: str, selector: str) -> str:
    """
    Extract a CSS rule including all nested rules.

    Args:
        content (str): CSS content to search in
        selector (str): CSS selector to find

    Returns:
        str: Extracted rule content or empty string if not found
    """
    # Escape special characters in the selector for regex
    escaped_selector = re.escape(selector)

    # Pattern to match the selector and its content block
    pattern = re.compile(f"{escaped_selector}\\s*{{([^}}]*(?:{{[^}}]*}}[^}}]*)*)}}", re.DOTALL)
    match = pattern.search(content)

    if match:
        # Return the full match including selector and braces
        return match.group(0)

    return ""


def hex_to_rgb(hex_color: str) -> tuple[int, int, int] | None:
    """
    Convert hex color to RGB tuple.

    Args:
        hex_color (str): Hex color string (e.g., "#ff0000" or "ff0000")

    Returns:
        tuple: RGB tuple (r, g, b) or None if invalid
    """
    hex_color = hex_color.lstrip("#")

    if len(hex_color) == 3:
        # Expand shorthand (e.g., "f0f" -> "ff00ff")
        hex_color = "".join([c * 2 for c in hex_color])

    if len(hex_color) != 6:
        return None

    try:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return (r, g, b)
    except ValueError:
        return None


def rgb_to_hex(r, g, b) -> str:
    """
    Convert RGB tuple to hex color string.

    Args:
        r (int): Red component (0-255)
        g (int): Green component (0-255)
        b (int): Blue component (0-255)

    Returns:
        str: Hex color string (e.g., "#ff0000")
    """
    return f"#{r:02x}{g:02x}{b:02x}"


def lighten_hex(hex_color: str, percentage: int) -> str:
    """
    Lighten a hex color by a given percentage.

    Args:
        hex_color (str): Hex color string (e.g., "#252525")
        percentage (int): Percentage to lighten (0-100)

    Returns:
        str: Lightened hex color string or original if invalid
    """
    rgb = hex_to_rgb(hex_color)
    if not rgb:
        return hex_color

    r, g, b = rgb
    factor = percentage / 100.0

    # Lighten by moving closer to white (255)
    r = min(255, int(r + (255 - r) * factor))
    g = min(255, int(g + (255 - g) * factor))
    b = min(255, int(b + (255 - b) * factor))

    return rgb_to_hex(r, g, b)


def darken_hex(hex_color: str, percentage: int) -> str:
    """
    Darken a hex color by a given percentage.

    Args:
        hex_color (str): Hex color string (e.g., "#00ccfe")
        percentage (int): Percentage to darken (0-100)

    Returns:
        str: Darkened hex color string or original if invalid
    """
    rgb = hex_to_rgb(hex_color)
    if not rgb:
        return hex_color

    r, g, b = rgb
    factor = percentage / 100.0

    # Darken by moving closer to black (0)
    r = max(0, int(r * (1 - factor)))
    g = max(0, int(g * (1 - factor)))
    b = max(0, int(b * (1 - factor)))

    return rgb_to_hex(r, g, b)
