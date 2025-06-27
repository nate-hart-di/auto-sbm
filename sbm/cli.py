"""
Command-line interface for the SBM tool.

This module provides the command-line interface for the SBM tool.
"""

import click
import logging
import sys
from pathlib import Path
from .scss.processor import SCSSProcessor
from .utils.logger import setup_logger
from .utils.path import get_dealer_theme_dir

def setup_logging(verbose=False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
def main(verbose):
    """Auto-SBM: Automated Site Builder Migration Tool"""
    setup_logging(verbose)

@main.command()
@click.argument('theme_name')
@click.option('--dry-run', is_flag=True, help='Show what would be done without making changes')
@click.option('--scss-only', is_flag=True, help='Only process SCSS files')
def migrate(theme_name, dry_run, scss_only):
    """Migrate a theme from Site Builder to custom theme structure."""
    if dry_run:
        click.echo("DRY RUN: SCSS migration would be performed for theme: " + theme_name)
        return

    if scss_only:
        click.echo(f"Processing SCSS migration for {theme_name}...")
        from sbm.core.migration import migrate_styles
        if not migrate_styles(theme_name):
            click.echo("SCSS migration failed.", err=True)
            sys.exit(1)
    else:
        # This can be expanded for full migration
        click.echo("Full migration not implemented yet. Use --scss-only for SCSS migration.")

@main.command()
@click.argument('theme_name')
def validate(theme_name):
    """Validate theme structure and SCSS syntax."""
    try:
        theme_dir = Path(get_dealer_theme_dir(theme_name))
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        return

    processor = SCSSProcessor(theme_name)
    
    # Check for generated SCSS files
    scss_files = [
        theme_dir / "sb-inside.scss",
        theme_dir / "sb-vrp.scss", 
        theme_dir / "sb-vdp.scss"
    ]
    
    all_valid = True
    
    for scss_file in scss_files:
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

if __name__ == '__main__':
    main()
