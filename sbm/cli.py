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

def setup_logging(verbose=False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
def cli(verbose):
    """Auto-SBM: Automated Site Builder Migration Tool"""
    setup_logging(verbose)

@cli.command()
@click.argument('theme_name')
@click.option('--dry-run', is_flag=True, help='Show what would be done without making changes')
@click.option('--scss-only', is_flag=True, help='Only process SCSS files')
def migrate(theme_name, dry_run, scss_only):
    """Migrate a theme from Site Builder to custom theme structure."""
    
    if scss_only:
        # SCSS-only migration using the existing processor
        processor = SCSSProcessor(theme_name)
        # Look for theme in dealer-themes directory
        dealer_themes_dir = Path("/Users/nathanhart/di-websites-platform/dealer-themes")
        theme_dir = dealer_themes_dir / theme_name
        
        if not theme_dir.exists():
            click.echo(f"Error: Theme directory '{theme_name}' not found at {theme_dir}", err=True)
            return
        
        style_scss = theme_dir / "css" / "style.scss"
        if not style_scss.exists():
            click.echo(f"Error: style.scss not found in {theme_dir}/css/", err=True)
            return
        
        try:
            if dry_run:
                click.echo("DRY RUN: Would process the following:")
                click.echo(f"  Input: {style_scss}")
                click.echo("  Output files:")
                click.echo(f"    - {theme_dir}/sb-inside.scss")
                click.echo(f"    - {theme_dir}/sb-vrp.scss")
                click.echo(f"    - {theme_dir}/sb-vdp.scss")
            else:
                click.echo(f"Processing SCSS migration for {theme_name}...")
                
                # Process the SCSS file
                results = processor.process_style_scss(str(theme_dir))
                
                if not results:
                    click.echo("No SCSS content was generated", err=True)
                    return
                
                # Prepare files for writing (results already have proper filenames)
                files_to_write = results
                
                if not files_to_write:
                    click.echo("No valid SCSS content to write", err=True)
                    return
                
                # Write files atomically
                success = processor.write_files_atomically(str(theme_dir), files_to_write)
                
                if success:
                    # Report results
                    for filename, content in files_to_write.items():
                        lines = len(content.splitlines())
                        click.echo(f"Generated {filename}: {lines} lines")
                    
                    click.echo("SCSS migration completed successfully!")
                else:
                    click.echo("SCSS migration failed during file writing", err=True)
                    return
                
        except Exception as e:
            click.echo(f"Error during SCSS migration: {str(e)}", err=True)
            return
    else:
        # Full migration would go here
        click.echo("Full migration not implemented yet. Use --scss-only for SCSS migration.")

@cli.command()
@click.argument('theme_name')
def validate(theme_name):
    """Validate theme structure and SCSS syntax."""
    processor = SCSSProcessor(theme_name)
    dealer_themes_dir = Path("/Users/nathanhart/di-websites-platform/dealer-themes")
    theme_dir = dealer_themes_dir / theme_name
    
    if not theme_dir.exists():
        click.echo(f"Error: Theme directory '{theme_name}' not found at {theme_dir}", err=True)
        return
    
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
    cli()
