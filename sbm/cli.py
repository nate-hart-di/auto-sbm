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
from .scss.validator import validate_scss_files # Import the new validation function
from .utils.logger import logger # Import the pre-configured logger
from .utils.path import get_dealer_theme_dir
from .core.migration import migrate_dealer_theme, run_post_migration_workflow # Import both migration functions
from .config import get_config, ConfigurationError, Config
from git import Repo # Import Repo for post_migrate command

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
@click.option('--skip-post-migration', is_flag=True, help="Skip interactive manual review, re-validation, Git operations, and PR creation.")
def auto(theme_name, skip_just, force_reset, create_pr, skip_post_migration):
    """
    Run the full, automated migration for a given theme.
    This is the recommended command for most migrations.
    """
    click.echo(f"Starting automated migration for {theme_name}...")
    
    interactive_review = not skip_post_migration
    interactive_git = not skip_post_migration
    interactive_pr = not skip_post_migration

    success = migrate_dealer_theme(
        theme_name,
        skip_just=skip_just,
        force_reset=force_reset,
        create_pr=create_pr,
        interactive_review=interactive_review,
        interactive_git=interactive_git,
        interactive_pr=interactive_pr
    )
    if success:
        click.echo(f"Automated migration completed successfully for {theme_name}!")
    else:
        click.echo(f"Automated migration failed for {theme_name}.", err=True)
        sys.exit(1)

@cli.command()
@click.argument('theme_name')
def validate(theme_name):
    """Validate theme structure and SCSS syntax."""
    validate_scss_files(theme_name)

@cli.command()
@click.argument('theme_name')
@click.option('--skip-git', is_flag=True, help="Skip Git operations (add, commit, push).")
@click.option('--create-pr', is_flag=True, help="Create a GitHub Pull Request after successful post-migration steps.")
@click.option('--skip-review', is_flag=True, help="Skip interactive manual review and re-validation.")
@click.option('--skip-git-prompt', is_flag=True, help="Skip prompt for Git operations.")
@click.option('--skip-pr-prompt', is_flag=True, help="Skip prompt for PR creation.")
def post_migrate(theme_name, skip_git, create_pr, skip_review, skip_git_prompt, skip_pr_prompt):
    """
    Run post-migration steps for a given theme, including manual review, re-validation, Git operations, and PR creation.
    This command assumes the initial migration (up to map components) has already been completed.
    """
    from .core.migration import run_post_migration_workflow # Import the new function
    from git import Repo # Import Repo for post_migrate command
    from sbm.utils.path import get_platform_dir # Import get_platform_dir

    click.echo(f"Starting post-migration workflow for {theme_name}...")

    # Attempt to get the current branch name for post-migration context
    try:
        repo = Repo(get_platform_dir()) # Use the platform root for the repo
        branch_name = repo.active_branch.name
    except Exception as e:
        click.echo(f"Error: Could not determine current Git branch for post-migration: {e}", err=True)
        click.echo("Please ensure you are in a Git repository and on the correct branch.", err=True)
        sys.exit(1)

    interactive_review = not skip_review
    interactive_git = not skip_git_prompt
    interactive_pr = not skip_pr_prompt

    success = run_post_migration_workflow(
        theme_name,
        branch_name,
        skip_git=skip_git,
        create_pr=create_pr,
        interactive_review=interactive_review,
        interactive_git=interactive_git,
        interactive_pr=interactive_pr
    )

    if success:
        click.echo(f"Post-migration workflow completed successfully for {theme_name}!")
    else:
        click.echo(f"Post-migration workflow failed for {theme_name}.", err=True)
        sys.exit(1)

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
        from sbm.utils.path import get_platform_dir
        repo = Repo(get_platform_dir())
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