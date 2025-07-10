"""
SCSS validation for the SBM tool.

This module provides functions for validating SCSS syntax and structure.
"""

import os
from pathlib import Path
import click # Import click for echo
from ..utils.logger import logger
from ..utils.path import get_dealer_theme_dir
from .processor import SCSSProcessor # Import SCSSProcessor for validate_scss_syntax

def validate_scss_files(slug: str) -> bool:
    """
    Validate theme SCSS files for syntax and structure.
    
    Args:
        slug (str): Dealer theme slug
        
    Returns:
        bool: True if all SCSS files are valid, False otherwise
    """
    logger.info(f"Validating SCSS files for {slug}...")
    
    try:
        theme_dir = Path(get_dealer_theme_dir(slug))
    except ValueError as e:
        logger.error(f"Error: {e}")
        return False

    processor = SCSSProcessor(slug)
    
    # Check for generated SCSS files
    sb_scss_files = [
        theme_dir / "sb-inside.scss",
        theme_dir / "sb-vdp.scss", 
        theme_dir / "sb-vrp.scss",
        theme_dir / "sb-home.scss"
    ]
    
    all_valid = True
    
    for scss_file in sb_scss_files:
        if scss_file.exists():
            try:
                with open(scss_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                is_valid, error = processor.validate_scss_syntax(content)
                if is_valid:
                    lines = len(content.splitlines())
                    click.echo(f"✓ {scss_file.name}: Valid SCSS syntax ({lines} lines)")
                else:
                    click.echo(f"✗ {scss_file.name}: Invalid SCSS syntax - {error}")
                    all_valid = False
            except Exception as e:
                click.echo(f"✗ {scss_file.name}: Error reading file - {str(e)}")
                all_valid = False
        else:
            click.echo(f"- {scss_file.name}: File not found")
    
    if all_valid:
        click.echo("\n✓ All SCSS files are valid!")
    else:
        click.echo("\n✗ Some SCSS files have validation errors")
    
    return all_valid
