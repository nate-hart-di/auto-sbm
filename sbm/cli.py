"""
Command-line interface for the SBM tool.

This module provides the command-line interface for the SBM tool.
"""

import click
import logging # Re-add the logging import
import sys
import os
from pathlib import Path
from .scss.processor import SCSSProcessor
from .utils.logger import logger # Import the pre-configured logger
from .utils.path import get_dealer_theme_dir
from .core.migration import migrate_dealer_theme
from .config import get_config, ConfigurationError, Config

class SBMCommandGroup(click.Group):
    """A custom command group that allows running a default command."""
    def __init__(self, *args, **kwargs):
        self.default_command = kwargs.pop('default_command', None)
        super().__init__(*args, **kwargs)

    def resolve_command(self, ctx, args):
        try:
            # Try to resolve the command as usual
            return super().resolve_command(ctx, args)
        except click.UsageError:
            # If it fails, assume it's an argument for the default command
            if self.default_command is None:
                raise
            # Prepend the default command name to the arguments
            args.insert(0, self.default_command)
            return super().resolve_command(ctx, args)

@click.group(cls=SBMCommandGroup, default_command='auto')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
def cli(verbose):
    """Auto-SBM: Automated Site Builder Migration Tool"""
    # Set logger level based on verbose flag
    if verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

@cli.command(hidden=True)
@click.argument('theme_name', required=False)
@click.option('--config', 'config_path', default='config.json', help='Path to config file.')
@click.option('--dry-run', is_flag=True, help='Show what would be done without making changes')
@click.option('--scss-only', is_flag=True, help='Only process SCSS files')
def migrate(theme_name, config_path, dry_run, scss_only):
    """Migrate a theme from Site Builder to custom theme structure."""
    config = None
    
    if os.path.exists(config_path):
        try:
            config = get_config(config_path)
            theme_name = config.get_setting('dealer_id')
        except ConfigurationError as e:
            click.echo(f"Configuration error: {e}", err=True)
            sys.exit(1)
    
    if not theme_name:
        click.echo("Error: A theme name must be provided either as an argument or in a config file.", err=True)
        sys.exit(1)
        
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
            click.echo(f"SCSS migration completed successfully for {theme_name}.")
    else:
        click.echo(f"Starting full migration for {theme_name}...")
        success = migrate_dealer_theme(theme_name)
        if success:
            click.echo(f"Full migration completed successfully for {theme_name}!")
        else:
            click.echo(f"Full migration failed for {theme_name}.", err=True)
            sys.exit(1)

@cli.command()
@click.argument('theme_name')
@click.option('--skip-just', is_flag=True, help="Skip running the 'just start' command.")
@click.option('--force-reset', is_flag=True, help="Force reset of existing Site Builder files.")
@click.option('--create-pr', is_flag=True, help="Create a GitHub Pull Request after successful migration.")
def auto(theme_name, skip_just, force_reset, create_pr):
    """
    Run the full, automated migration for a given theme.
    This is the recommended command for most migrations.
    """
    click.echo(f"Starting automated migration for {theme_name}...")
    success = migrate_dealer_theme(theme_name, skip_just=skip_just, force_reset=force_reset, create_pr=create_pr)
    if success:
        click.echo(f"Automated migration completed successfully for {theme_name}!")
    else:
        click.echo(f"Automated migration failed for {theme_name}.", err=True)
        sys.exit(1)

@cli.command()
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

@cli.command()
@click.argument('theme_name')
@click.option('--title', '-t', help='Title for the Pull Request.')
@click.option('--body', '-b', help='Body/description for the Pull Request.')
@click.option('--base', default='main', help='Base branch for the Pull Request (default: main).')
@click.option('--head', help='Head branch for the Pull Request (default: current branch).')
@click.option('--reviewers', '-r', default='carsdotcom/fe-dev', help='Comma-separated list of reviewers (default: carsdotcom/fe-dev).')
@click.option('--labels', '-l', default='fe-dev', help='Comma-separated list of labels (default: fe-dev).')
def pr(theme_name, title, body, base, head, reviewers, labels):
    """
    Create a GitHub Pull Request for a given theme.
    """
    from sbm.core.git import create_pull_request
    from git import Repo, GitCommandError
    from sbm.utils.helpers import get_branch_name

    # Generate default title and body if not provided
    if not title:
        title = f"SBM: Migrate {theme_name} to Site Builder format"
    
    if not body:
        body = f"This PR migrates the {theme_name} theme to the Site Builder format.\n\n" \
               f"**What:**\n- Converted SCSS to Site Builder compatible format.\n- Added predetermined styles for cookie banner and directions row.\n\n" \
               f"**Why:**\n- To enable the theme to be used with the new Site Builder platform.\n\n" \
               f"**Review Instructions:**\n- Review the changes in the Files Changed tab.\n- Verify the site loads correctly on the new platform."

    try:
        repo = Repo(os.getcwd()) # Use current working directory to get repo
        current_branch = repo.active_branch.name
        head_branch = head if head else current_branch
    except GitCommandError as e:
        click.echo(f"Error getting Git branch information: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: Could not determine current Git branch. Ensure you are in a Git repository: {e}", err=True)
        sys.exit(1)

    click.echo(f"Creating Pull Request for {theme_name}...")
    pr_url = create_pull_request(title, body, base, head_branch, reviewers, labels)

    if pr_url:
        click.echo(f"Pull Request created successfully: {pr_url}")
    else:
        click.echo(f"Failed to create Pull Request for {theme_name}.", err=True)
        sys.exit(1)

if __name__ == '__main__':
    cli()

