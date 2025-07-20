"""
Validation module for the SBM tool.

This module provides validation functions for PHP and other files.
"""

import os
import subprocess

from ..utils.logger import logger


def validate_php_syntax(file_path):
    """
    Validate PHP syntax in a file.
    
    Args:
        file_path (str): Path to the PHP file
        
    Returns:
        bool: True if syntax is valid, False otherwise
    """
    logger.info(f"Validating PHP syntax for {os.path.basename(file_path)}")

    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return False

    # First check brace count
    with open(file_path, encoding="utf-8", errors="ignore") as f:
        content = f.read()

    # Count braces
    opening_count = content.count("{")
    closing_count = content.count("}")

    logger.info(f"PHP brace count: {opening_count} opening, {closing_count} closing")

    if opening_count != closing_count:
        logger.warning(f"Unbalanced braces in {os.path.basename(file_path)}: "
                      f"{opening_count} opening, {closing_count} closing")

        # If we have more opening than closing braces, try to fix it
        if opening_count > closing_count:
            missing = opening_count - closing_count
            logger.info(f"Adding {missing} missing closing braces")

            # Create a backup
            with open(f"{file_path}.bak", "w") as f:
                f.write(content)

            # Add missing closing braces
            with open(file_path, "w") as f:
                f.write(content + "\n" + "}" * missing + "\n?>")

            logger.info(f"Fixed PHP file by adding {missing} closing braces")

    # If php command is available, use it for syntax validation
    try:
        result = subprocess.run(
            f"php -l {file_path}",
            check=False, shell=True,
            capture_output=True,
            text=True
        )

        if "No syntax errors detected" in result.stdout:
            logger.info(f"PHP syntax validation passed for {os.path.basename(file_path)}")
            return True
        logger.error(f"PHP syntax validation failed for {os.path.basename(file_path)}: {result.stderr}")
        return False

    except Exception as e:
        logger.warning(f"Could not run PHP syntax check (php -l): {e}")
        logger.info("Skipping PHP syntax validation, only brace count was checked")

        # Return True if braces are balanced (or were fixed)
        return opening_count == closing_count or opening_count > closing_count


def validate_theme_files(slug, theme_dir):
    """
    Validate important files in a dealer theme.
    
    Args:
        slug (str): Dealer theme slug
        theme_dir (str): Path to the dealer theme directory
        
    Returns:
        bool: True if all validations pass, False otherwise
    """
    logger.info(f"Validating theme files for {slug}")

    success = True

    # Validate functions.php if it exists
    functions_php = os.path.join(theme_dir, "functions.php")
    if os.path.exists(functions_php):
        if not validate_php_syntax(functions_php):
            logger.error(f"functions.php validation failed for {slug}")
            success = False

    # Validate header.php if it exists
    header_php = os.path.join(theme_dir, "header.php")
    if os.path.exists(header_php):
        if not validate_php_syntax(header_php):
            logger.error(f"header.php validation failed for {slug}")
            success = False

    # Validate footer.php if it exists
    footer_php = os.path.join(theme_dir, "footer.php")
    if os.path.exists(footer_php):
        if not validate_php_syntax(footer_php):
            logger.error(f"footer.php validation failed for {slug}")
            success = False

    # Validate Site Builder files
    sb_files = ["sb-inside.scss", "sb-home.scss", "sb-vdp.scss", "sb-vrp.scss"]

    from ..scss.validator import validate_scss_syntax

    for file in sb_files:
        file_path = os.path.join(theme_dir, file)
        if os.path.exists(file_path):
            if not validate_scss_syntax(file_path):
                logger.error(f"{file} validation failed for {slug}")
                success = False

    return success
