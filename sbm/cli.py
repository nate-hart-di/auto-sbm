"""
Command-line interface for the SBM tool.

This module provides the command-line interface for the SBM tool.
"""

import click
import logging # Re-add the logging import
import sys
import os
import subprocess
import shutil
from pathlib import Path
from .scss.processor import SCSSProcessor
from .scss.validator import validate_scss_files # Import the new validation function
from .utils.logger import logger # Import the pre-configured logger
from .utils.path import get_dealer_theme_dir
from .core.migration import migrate_dealer_theme, run_post_migration_workflow # Import both migration functions
from .config import get_config, ConfigurationError, Config
from git import Repo # Import Repo for post_migrate command

# --- Auto-run setup.sh if .sbm_setup_complete is missing or health check fails ---
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SETUP_MARKER = os.path.join(REPO_ROOT, '.sbm_setup_complete')
SETUP_SCRIPT = os.path.join(REPO_ROOT, 'setup.sh')

REQUIRED_CLI_TOOLS = ['git', 'gh', 'just', 'python3', 'pip']
REQUIRED_PYTHON_PACKAGES = ['click', 'rich', 'gitpython', 'pyyaml', 'jinja2', 'pytest', 'requests', 'colorama']


def is_env_healthy():
    # Check CLI tools
    for cmd in REQUIRED_CLI_TOOLS:
        if not shutil.which(cmd):
            print(f"[SBM] Required CLI tool missing: {cmd}")
            return False
    # Check Python venv and packages
    venv_path = os.path.join(REPO_ROOT, '.venv')
    pip_path = os.path.join(venv_path, 'bin', 'pip')
    if not os.path.isdir(venv_path) or not os.path.isfile(pip_path):
        print("[SBM] Python virtual environment or pip not found.")
        return False
    try:
        result = subprocess.run([pip_path, 'freeze'], capture_output=True, text=True, timeout=10)
        installed = [line.split('==')[0].lower() for line in result.stdout.splitlines() if '==' in line]
        for pkg in REQUIRED_PYTHON_PACKAGES:
            if pkg.lower() not in installed:
                print(f"[SBM] Required Python package missing: {pkg}")
                return False
    except Exception as e:
        print(f"[SBM] Error checking Python packages: {e}")
        return False
    return True

# --- Setup logic ---
need_setup = False
if not os.path.exists(SETUP_MARKER):
    need_setup = True
elif not is_env_healthy():
    print("[SBM] Environment health check failed. Setup will be re-run to fix issues.")
    need_setup = True

if need_setup:
    print("[SBM] Running setup.sh...")
    try:
        result = subprocess.run(['bash', SETUP_SCRIPT], cwd=REPO_ROOT)
        if result.returncode != 0:
            print("[SBM] setup.sh failed. Please review the output above and fix any issues before retrying.")
            sys.exit(1)
        else:
            print("[SBM] Setup complete. Continuing with SBM command...")
    except Exception as e:
        print(f"[SBM] Failed to run setup.sh: {e}")
        sys.exit(1)

# --- Auto-update: Enhanced git pull with better error handling ---
def auto_update_repo():
    """
    Automatically pull the latest changes from the auto-sbm repository.
    Runs at the start of every sbm command to ensure users have the latest features.
    """
    # Check if auto-update is disabled
    disable_file = os.path.join(REPO_ROOT, '.sbm-no-auto-update')
    if os.path.exists(disable_file):
        return  # Auto-update disabled by user
    
    try:
        # Check if we're in a git repository
        git_dir = os.path.join(REPO_ROOT, '.git')
        if not os.path.exists(git_dir):
            return  # Not a git repo, skip update
        
        # Check if we have network connectivity by testing git remote
        connectivity_check = subprocess.run(
            ['git', 'ls-remote', '--exit-code', 'origin', 'HEAD'],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if connectivity_check.returncode != 0:
            # No network or remote access, skip silently
            return
        
        # Check current branch and stash any local changes
        current_branch_result = subprocess.run(
            ['git', 'branch', '--show-current'],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if current_branch_result.returncode != 0:
            return  # Can't determine branch, skip
        
        current_branch = current_branch_result.stdout.strip()
        
        # Only auto-update if we're on main/master branch
        if current_branch not in ['main', 'master']:
            return  # Don't auto-update on feature branches
        
        # Check if there are uncommitted changes
        status_result = subprocess.run(
            ['git', 'status', '--porcelain'],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=5
        )
        
        has_changes = bool(status_result.stdout.strip())
        stash_created = False
        
        if has_changes:
            # Stash local changes
            stash_result = subprocess.run(
                ['git', 'stash', 'push', '-m', 'SBM auto-update stash'],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                timeout=10
            )
            stash_created = stash_result.returncode == 0
        
        # Perform git pull
        pull_result = subprocess.run(
            ['git', 'pull', '--quiet', 'origin', current_branch],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=15
        )
        
        if pull_result.returncode == 0:
            # Check if there were actual updates
            if pull_result.stdout.strip() and "Already up to date" not in pull_result.stdout:
                print("[SBM] ✅ Auto-updated to latest version.")
            
            # Restore stashed changes if we created a stash
            if stash_created:
                restore_result = subprocess.run(
                    ['git', 'stash', 'pop'],
                    cwd=REPO_ROOT,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if restore_result.returncode != 0:
                    print("[SBM] ⚠️  Warning: Could not restore local changes. Check 'git stash list'.")
        else:
            # Pull failed, restore stash if we created one
            if stash_created:
                subprocess.run(
                    ['git', 'stash', 'pop'],
                    cwd=REPO_ROOT,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
        
    except subprocess.TimeoutExpired:
        # Network timeout, skip silently
        pass
    except Exception:
        # Any other error, fail silently to not interrupt user workflow
        pass

# Run auto-update at CLI initialization
auto_update_repo()

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
    By default, prompts to create PRs with default reviewers (carsdotcom/fe-dev) and labels (fe-dev).
    Use 'sbm pr <theme-name>' for manual PR creation or --no-create-pr to skip.
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

@cli.command()
@click.argument('theme_name')
@click.option('--force-reset', is_flag=True, help="Force reset of existing Site Builder files.")
@click.option('--skip-maps', is_flag=True, help="Skip map components migration.")
def migrate(theme_name, force_reset, skip_maps):
    """
    Migrate a dealer theme SCSS files to Site Builder format.
    
    This command runs the core migration steps (create files, migrate styles, add predetermined styles,
    migrate maps) followed by manual review and post-migration validation/formatting.
    
    This does NOT include Git operations, Docker container management, or PR creation.
    Use 'sbm auto' for the full automated workflow including Git and PR operations.
    """
    from sbm.core.migration import (
        create_sb_files, 
        migrate_styles, 
        add_predetermined_styles,
        migrate_map_components,
        reprocess_manual_changes,
        _create_automation_snapshots,
        _cleanup_snapshot_files
    )
    from sbm.oem.factory import OEMFactory
    
    click.echo(f"Starting SCSS migration for {theme_name}...")
    
    # Create the appropriate OEM handler for this slug
    oem_handler = OEMFactory.detect_from_theme(theme_name)
    logger.info(f"Using {oem_handler} for {theme_name}")
    
    # Step 1: Create Site Builder files
    logger.info(f"Step 1/4: Creating Site Builder files for {theme_name}...")
    if not create_sb_files(theme_name, force_reset):
        logger.error(f"Failed to create Site Builder files for {theme_name}")
        click.echo(f"❌ Failed to create Site Builder files for {theme_name}.", err=True)
        sys.exit(1)
    
    # Step 2: Migrate styles
    logger.info(f"Step 2/4: Migrating styles for {theme_name}...")
    if not migrate_styles(theme_name):
        logger.error(f"Failed to migrate styles for {theme_name}")
        click.echo(f"❌ Failed to migrate styles for {theme_name}.", err=True)
        sys.exit(1)
    
    # Step 3: Add predetermined styles
    logger.info(f"Step 3/4: Adding predetermined styles for {theme_name}...")
    if not add_predetermined_styles(theme_name):
        logger.error(f"Failed to add predetermined styles for {theme_name}")
        click.echo(f"❌ Failed to add predetermined styles for {theme_name}.", err=True)
        sys.exit(1)
    
    # Step 4: Migrate map components if not skipped
    if not skip_maps:
        logger.info(f"Step 4/4: Migrating map components for {theme_name}...")
        if not migrate_map_components(theme_name, oem_handler):
            logger.error(f"Failed to migrate map components for {theme_name}")
            click.echo(f"❌ Failed to migrate map components for {theme_name}.", err=True)
            sys.exit(1)
        logger.info(f"Map components migrated successfully for {theme_name}")
    else:
        logger.info(f"Step 4/4: Skipping map components migration for {theme_name}")
    
    logger.info(f"Migration completed successfully for {theme_name}")
    
    # Create snapshots of the automated migration output for comparison
    _create_automation_snapshots(theme_name)
    logger.info("Created automation snapshot before manual review")
    
    # Manual review phase
    click.echo("\n" + "="*80)
    click.echo(f"Manual Review Required for {theme_name}")
    click.echo("Please review the migrated SCSS files in your theme directory:")
    click.echo(f"  - {get_dealer_theme_dir(theme_name)}/sb-inside.scss")
    click.echo(f"  - {get_dealer_theme_dir(theme_name)}/sb-vdp.scss")
    click.echo(f"  - {get_dealer_theme_dir(theme_name)}/sb-vrp.scss")
    click.echo(f"  - {get_dealer_theme_dir(theme_name)}/sb-home.scss")
    click.echo("\nVerify the content and make any necessary manual adjustments.")
    click.echo("Once you are satisfied, proceed to the next step.")
    click.echo("="*80 + "\n")
    
    if not click.confirm("Continue with the migration after manual review?"):
        logger.info("Migration stopped by user after manual review.")
        click.echo("Migration stopped by user.")
        return
    
    # Reprocess manual changes to ensure consistency (includes validation, fixing issues, prettier formatting)
    logger.info(f"Reprocessing manual changes for {theme_name} to ensure consistency...")
    if not reprocess_manual_changes(theme_name):
        logger.error("Failed to reprocess manual changes.")
        click.echo("❌ Failed to reprocess manual changes.", err=True)
        sys.exit(1)
    
    # Clean up snapshot files after manual review phase
    logger.info("Cleaning up automation snapshots after manual review")
    _cleanup_snapshot_files(theme_name)
    
    click.echo(f"✅ SCSS migration completed successfully for {theme_name}!")
    click.echo("Files have been validated, issues fixed, and formatted with prettier.")
    click.echo("You can now review the final files and commit them when ready.")

@cli.command()
@click.argument('theme_name')
@click.option('--skip-just', is_flag=True, help="Skip running the 'just start' command.")
@click.option('--force-reset', is_flag=True, help="Force reset of existing Site Builder files.")
@click.option('--create-pr/--no-create-pr', default=True, help="Create a GitHub Pull Request after successful migration (default: True, with defaults: reviewers=carsdotcom/fe-dev, labels=fe-dev).")
@click.option('--skip-post-migration', is_flag=True, help="Skip interactive manual review, re-validation, Git operations, and PR creation.")
def auto(theme_name, skip_just, force_reset, create_pr, skip_post_migration):
    """
    Run the full, automated migration for a given theme.
    This is the recommended command for most migrations.
    
    By default, prompts to create a published PR with default reviewers (carsdotcom/fe-dev) 
    and labels (fe-dev). Use --no-create-pr to skip. For more control over PR creation, 
    use 'sbm pr <theme-name>' separately.
    
    Use --skip-just to skip running the 'just start' command (if the site is already started).
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
def reprocess(theme_name):
    """
    Reprocess Site Builder SCSS files to ensure consistency.
    
    This command applies the same transformations as the initial migration
    to existing Site Builder files, ensuring variables, mixins, and other
    SCSS patterns are properly processed after manual changes.
    """
    click.echo(f"Reprocessing Site Builder files for {theme_name}...")
    
    from .core.migration import reprocess_manual_changes
    
    success = reprocess_manual_changes(theme_name)
    
    if success:
        click.echo(f"✅ Reprocessing completed successfully for {theme_name}!")
    else:
        click.echo(f"❌ Reprocessing failed for {theme_name}.", err=True)
        sys.exit(1)

@cli.command()
@click.argument('theme_name')
def validate(theme_name):
    """Validate theme structure and SCSS syntax."""
    validate_scss_files(theme_name)

@cli.command()
@click.argument('theme_name')
@click.option('--skip-git', is_flag=True, help="Skip Git operations (add, commit, push).")
@click.option('--create-pr/--no-create-pr', default=True, help="Create a GitHub Pull Request after successful post-migration steps (default: True, with defaults: reviewers=carsdotcom/fe-dev, labels=fe-dev).")
@click.option('--skip-review', is_flag=True, help="Skip interactive manual review and re-validation.")
@click.option('--skip-git-prompt', is_flag=True, help="Skip prompt for Git operations.")
@click.option('--skip-pr-prompt', is_flag=True, help="Skip prompt for PR creation.")
def post_migrate(theme_name, skip_git, create_pr, skip_review, skip_git_prompt, skip_pr_prompt):
    """
    Run post-migration steps for a given theme, including manual review, re-validation, Git operations, and PR creation.
    This command assumes the initial migration (up to map components) has already been completed.
    
    By default, prompts to create a published PR with default reviewers (carsdotcom/fe-dev) 
    and labels (fe-dev). Use --no-create-pr to skip. For more control over PR creation, 
    use 'sbm pr <theme-name>' separately.
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

@cli.command()
def update():
    """
    Manually update auto-sbm to the latest version.
    """
    click.echo("Manually updating auto-sbm...")
    
    try:
        # Force update regardless of disable file
        git_dir = os.path.join(REPO_ROOT, '.git')
        if not os.path.exists(git_dir):
            click.echo("❌ Not in a git repository. Cannot update.", err=True)
            sys.exit(1)
        
        # Check current branch
        current_branch_result = subprocess.run(
            ['git', 'branch', '--show-current'],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if current_branch_result.returncode != 0:
            click.echo("❌ Could not determine current branch.", err=True)
            sys.exit(1)
        
        current_branch = current_branch_result.stdout.strip()
        
        # Stash changes if any
        status_result = subprocess.run(
            ['git', 'status', '--porcelain'],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True
        )
        
        has_changes = bool(status_result.stdout.strip())
        if has_changes:
            click.echo("Stashing local changes...")
            subprocess.run(
                ['git', 'stash', 'push', '-m', 'Manual SBM update stash'],
                cwd=REPO_ROOT,
                check=True
            )
        
        # Perform git pull
        click.echo(f"Pulling latest changes from origin/{current_branch}...")
        pull_result = subprocess.run(
            ['git', 'pull', 'origin', current_branch],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True
        )
        
        if pull_result.returncode == 0:
            if "Already up to date" in pull_result.stdout:
                click.echo("✅ Already up to date.")
            else:
                click.echo("✅ Successfully updated to latest version.")
            
            # Restore stashed changes
            if has_changes:
                click.echo("Restoring local changes...")
                subprocess.run(['git', 'stash', 'pop'], cwd=REPO_ROOT, check=True)
        else:
            click.echo(f"❌ Update failed: {pull_result.stderr}", err=True)
            if has_changes:
                subprocess.run(['git', 'stash', 'pop'], cwd=REPO_ROOT)
            sys.exit(1)
            
    except subprocess.CalledProcessError as e:
        click.echo(f"❌ Update failed: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}", err=True)
        sys.exit(1)

@cli.command()
@click.argument('action', type=click.Choice(['enable', 'disable', 'status']))
def auto_update(action):
    """
    Manage auto-update settings for auto-sbm.
    
    Actions:
    - enable: Enable automatic updates (default behavior)
    - disable: Disable automatic updates 
    - status: Show current auto-update status
    """
    disable_file = os.path.join(REPO_ROOT, '.sbm-no-auto-update')
    
    if action == 'enable':
        if os.path.exists(disable_file):
            os.remove(disable_file)
            click.echo("✅ Auto-updates enabled. SBM will automatically update at startup.")
        else:
            click.echo("✅ Auto-updates are already enabled.")
    
    elif action == 'disable':
        if not os.path.exists(disable_file):
            with open(disable_file, 'w') as f:
                f.write("# This file disables auto-updates for auto-sbm\n")
                f.write("# Delete this file or run 'sbm auto-update enable' to re-enable\n")
            click.echo("✅ Auto-updates disabled. Run 'sbm auto-update enable' to re-enable.")
        else:
            click.echo("✅ Auto-updates are already disabled.")
    
    elif action == 'status':
        if os.path.exists(disable_file):
            click.echo("❌ Auto-updates are DISABLED")
            click.echo("   Run 'sbm auto-update enable' to enable automatic updates")
        else:
            click.echo("✅ Auto-updates are ENABLED")
            click.echo("   SBM will automatically update to the latest version at startup")
            click.echo("   Run 'sbm auto-update disable' to disable automatic updates")

if __name__ == '__main__':
    cli()
