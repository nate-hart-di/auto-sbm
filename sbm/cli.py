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

@click.group(cls=SBMCommandGroup, default_command='auto', context_settings={'help_option_names': ['-h', '--help']})
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.option('--config', 'config_path', default='config.json', help='Path to config file.')
@click.pass_context
def cli(ctx, verbose, config_path):
    """Auto-SBM: Automated Site Builder Migration Tool
    
    The main command for SBM migration with GitHub PR creation support.
    Use 'sbm pr <theme-name>' to create PRs with default reviewers (carsdotcom/fe-dev) and labels (fe-dev).
    """
    # Set logger level based on verbose flag
    if verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
    
    # Initialize context object
    ctx.ensure_object(dict)
    
    # Try to load config if it exists
    config = None
    if os.path.exists(config_path):
        try:
            config = get_config(config_path)
        except ConfigurationError as e:
            logger.warning(f"Configuration warning: {e}")
            config = Config({})  # Use empty config as fallback
    else:
        config = Config({})  # Use empty config as fallback
    
    # Store config and logger in context
    ctx.obj['config'] = config
    ctx.obj['logger'] = logger

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
@click.option('--create-pr', is_flag=True, help="Create a GitHub Pull Request after successful migration (with defaults: reviewers=carsdotcom/fe-dev, labels=fe-dev).")
@click.option('--skip-post-migration', is_flag=True, help="Skip interactive manual review, re-validation, Git operations, and PR creation.")
def auto(theme_name, skip_just, force_reset, create_pr, skip_post_migration):
    """
    Run the full, automated migration for a given theme.
    This is the recommended command for most migrations.
    
    When --create-pr is used, creates a published PR with default reviewers (carsdotcom/fe-dev) 
    and labels (fe-dev). For more control over PR creation, use 'sbm pr <theme-name>' separately.
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
@click.option('--create-pr', is_flag=True, help="Create a GitHub Pull Request after successful post-migration steps (with defaults: reviewers=carsdotcom/fe-dev, labels=fe-dev).")
@click.option('--skip-review', is_flag=True, help="Skip interactive manual review and re-validation.")
@click.option('--skip-git-prompt', is_flag=True, help="Skip prompt for Git operations.")
@click.option('--skip-pr-prompt', is_flag=True, help="Skip prompt for PR creation.")
def post_migrate(theme_name, skip_git, create_pr, skip_review, skip_git_prompt, skip_pr_prompt):
    """
    Run post-migration steps for a given theme, including manual review, re-validation, Git operations, and PR creation.
    This command assumes the initial migration (up to map components) has already been completed.
    
    When --create-pr is used, creates a published PR with default reviewers (carsdotcom/fe-dev) 
    and labels (fe-dev). For more control over PR creation, use 'sbm pr <theme-name>' separately.
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
@click.option('--title', '-t', help='Title for the Pull Request. (Optional: auto-generated if not provided)')
@click.option('--body', '-b', help='Body/description for the Pull Request. (Optional: auto-generated if not provided)')
@click.option('--base', default='main', help='Base branch for the Pull Request (default: main).')
@click.option('--head', help='Head branch for the Pull Request (default: current branch).')
@click.option('--reviewers', '-r', help='Comma-separated list of reviewers (default: carsdotcom/fe-dev).')
@click.option('--labels', '-l', help='Comma-separated list of labels (default: fe-dev).')
@click.option('--draft', '-d', is_flag=True, default=False, help='Create as draft PR.')
@click.option('--publish', '-p', is_flag=True, default=True, help='Create as published PR (default: true).')
@click.pass_context
def pr(ctx, theme_name, title, body, base, head, reviewers, labels, draft, publish):
    """
    Create a GitHub Pull Request for a given theme.
    
    By default, creates a published PR with:
    - Reviewers: carsdotcom/fe-dev
    - Labels: fe-dev
    - Content: Auto-generated based on Git changes (Stellantis template)
    """
    config = ctx.obj['config']
    logger = ctx.obj['logger']

    from sbm.core.git import GitOperations
    git_ops = GitOperations(config)

    # Determine draft status
    is_draft = draft if draft else not publish

    # Parse reviewers and labels if provided
    parsed_reviewers = None
    parsed_labels = None
    if reviewers:
        parsed_reviewers = [r.strip() for r in reviewers.split(',')]
    if labels:
        parsed_labels = [l.strip() for l in labels.split(',')]

    try:
        # The create_pr method in GitOperations will handle branch detection
        # and PR content generation.
        logger.info(f"Creating GitHub PR for {theme_name}...")
        pr_result = git_ops.create_pr(
            slug=theme_name,
            branch_name=head,  # Pass head directly, GitOperations will handle current branch if head is None
            title=title,
            body=body,
            base=base,
            head=head,
            reviewers=parsed_reviewers,
            labels=parsed_labels,
            draft=is_draft
        )

        if pr_result['success']:
            click.echo(f"✅ Pull request created: {pr_result['pr_url']}")
            click.echo(f"Title: {pr_result['title']}")
            click.echo(f"Branch: {pr_result['branch']}")
            if is_draft:
                click.echo("📝 Created as draft - remember to publish when ready")
            if pr_result.get('existing'):
                click.echo("ℹ️  PR already existed - retrieved existing PR URL")
        else:
            click.echo(f"❌ PR creation failed: {pr_result['error']}", err=True)
            sys.exit(1)

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    cli()
