"""
Command-line interface for the SBM tool with Rich UI enhancements.

This module provides the command-line interface for the SBM tool with
Rich-enhanced progress tracking, status displays, and interactive elements.
"""

from __future__ import annotations  # CRITICAL: Must be first import for forward references

import logging  # Re-add the logging import
import os
import shutil
import subprocess
import sys
from typing import Any, List, Tuple  # Add typing imports for Click functions

import click
from git import Repo  # Import Repo for post_migrate command

from .config import Config, ConfigurationError, get_config
from .core.migration import (  # Import migration functions
    migrate_dealer_theme,
    run_post_migration_workflow,
    test_compilation_recovery,
)
from .scss.validator import validate_scss_files  # Import the new validation function

# Rich UI imports
from .ui.console import get_console
from .ui.panels import StatusPanels
from .ui.progress import MigrationProgress
from .ui.prompts import InteractivePrompts
from .utils.logger import logger  # Import the pre-configured logger
from .utils.path import get_dealer_theme_dir

# --- Auto-run setup.sh if .sbm_setup_complete is missing or health check fails ---
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SETUP_MARKER = os.path.join(REPO_ROOT, ".sbm_setup_complete")
SETUP_SCRIPT = os.path.join(REPO_ROOT, "setup.sh")

REQUIRED_CLI_TOOLS = ["git", "gh", "just", "python3", "pip"]
REQUIRED_PYTHON_PACKAGES = [
    "click",
    "rich",
    "gitpython",
    "pyyaml",
    "jinja2",
    "pytest",
    "requests",
    "colorama",
]


def is_env_healthy() -> bool:
    """
    Check if the environment has all required tools and packages.

    Returns:
        True if environment is healthy, False otherwise
    """
    # Check CLI tools
    for cmd in REQUIRED_CLI_TOOLS:
        if not shutil.which(cmd):
            logger.warning(f"Required CLI tool missing: {cmd}")
            return False

    # Check Python venv and packages
    venv_path = os.path.join(REPO_ROOT, ".venv")
    pip_path = os.path.join(venv_path, "bin", "pip")
    if not os.path.isdir(venv_path) or not os.path.isfile(pip_path):
        logger.warning("Python virtual environment or pip not found")
        return False

    try:
        result = subprocess.run(
            [pip_path, "freeze"], check=False, capture_output=True, text=True, timeout=10
        )
        installed = [
            line.split("==")[0].lower() for line in result.stdout.splitlines() if "==" in line
        ]
        for pkg in REQUIRED_PYTHON_PACKAGES:
            if pkg.lower() not in installed:
                logger.warning(f"Required Python package missing: {pkg}")
                return False
    except subprocess.TimeoutExpired:
        logger.error("Timeout while checking Python packages")
        return False
    except Exception as e:
        logger.error(f"Error checking Python packages: {type(e).__name__}")
        return False

    return True


# --- Setup logic ---
need_setup = False
if not os.path.exists(SETUP_MARKER):
    need_setup = True
elif not is_env_healthy():
    logger.warning("Environment health check failed. Setup will be re-run to fix issues.")
    need_setup = True

if need_setup:
    logger.info("Running setup.sh...")
    try:
        result = subprocess.run(["bash", SETUP_SCRIPT], check=False, cwd=REPO_ROOT)
        if result.returncode != 0:
            logger.error(
                "Setup.sh failed. Please review the output above and fix any issues before retrying."
            )
            sys.exit(1)
        else:
            logger.info("Setup complete. Continuing with SBM command...")
    except Exception as e:
        logger.error(f"Failed to run setup.sh: {type(e).__name__}")
        sys.exit(1)


# --- Auto-update: Enhanced git pull with better error handling ---
def auto_update_repo() -> None:
    """
    Automatically pull the latest changes from the auto-sbm repository.
    Runs at the start of every sbm command to ensure users have the latest features.
    """
    # Check if auto-update is disabled
    disable_file = os.path.join(REPO_ROOT, ".sbm-no-auto-update")
    if os.path.exists(disable_file):
        return  # Auto-update disabled by user

    try:
        # Check if we're in a git repository
        git_dir = os.path.join(REPO_ROOT, ".git")
        if not os.path.exists(git_dir):
            return  # Not a git repo, skip update

        # Check if we have network connectivity by testing git remote
        connectivity_check = subprocess.run(
            ["git", "ls-remote", "--exit-code", "origin", "HEAD"],
            check=False,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=5,
        )

        if connectivity_check.returncode != 0:
            # No network or remote access, skip silently
            return

        # Check current branch and stash any local changes
        current_branch_result = subprocess.run(
            ["git", "branch", "--show-current"],
            check=False,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=5,
        )

        if current_branch_result.returncode != 0:
            return  # Can't determine branch, skip

        current_branch = current_branch_result.stdout.strip()

        # Only auto-update if we're on main/master branch
        if current_branch not in ["main", "master"]:
            return  # Don't auto-update on feature branches

        # Check if there are uncommitted changes
        status_result = subprocess.run(
            ["git", "status", "--porcelain"],
            check=False,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=5,
        )

        has_changes = bool(status_result.stdout.strip())
        stash_created = False

        if has_changes:
            # Stash local changes
            stash_result = subprocess.run(
                ["git", "stash", "push", "-m", "SBM auto-update stash"],
                check=False,
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                timeout=10,
            )
            stash_created = stash_result.returncode == 0

        # Perform git pull
        pull_result = subprocess.run(
            ["git", "pull", "--quiet", "origin", current_branch],
            check=False,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=15,
        )

        if pull_result.returncode == 0:
            # Check if there were actual updates
            if pull_result.stdout.strip() and "Already up to date" not in pull_result.stdout:
                logger.info("Auto-updated to latest version.")

            # Check if we need to run full setup (if >8 hours since last setup)
            _check_and_run_setup_if_needed()

            # Restore stashed changes if we created a stash
            if stash_created:
                restore_result = subprocess.run(
                    ["git", "stash", "pop"],
                    check=False,
                    cwd=REPO_ROOT,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if restore_result.returncode != 0:
                    logger.warning("Could not restore local changes. Check 'git stash list'.")
        # Pull failed, restore stash if we created one
        elif stash_created:
            subprocess.run(
                ["git", "stash", "pop"],
                check=False,
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                timeout=10,
            )

    except subprocess.TimeoutExpired:
        # Network timeout, skip silently
        pass
    except Exception:
        # Any other error, fail silently to not interrupt user workflow
        pass


def _check_and_run_setup_if_needed() -> None:
    """
    Check if setup needs to be run (if >8 hours since last setup) and run it silently.
    """
    setup_complete_file = os.path.join(REPO_ROOT, ".sbm_setup_complete")

    try:
        # Check if setup file exists and when it was last modified
        if os.path.exists(setup_complete_file):
            import time

            file_mtime = os.path.getmtime(setup_complete_file)
            current_time = time.time()
            hours_since_setup = (current_time - file_mtime) / 3600

            if hours_since_setup <= 8:
                return  # Setup is still fresh, no need to run

        # Setup is needed - delete old marker and run setup
        if os.path.exists(setup_complete_file):
            os.remove(setup_complete_file)

        # Run pip install requirements silently
        pip_result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
            check=False,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=60,
        )

        if pip_result.returncode == 0:
            # Create the setup complete marker
            import time

            with open(setup_complete_file, "w") as f:
                f.write(f"Setup completed at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")

    except Exception:
        # Silently ignore setup errors during auto-update
        pass


# Run auto-update at CLI initialization
auto_update_repo()


class SBMCommandGroup(click.Group):
    """A custom command group that allows running a default command."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.default_command = kwargs.pop("default_command", None)
        super().__init__(*args, **kwargs)

    def resolve_command(
        self, ctx: click.Context, args: List[str]
    ) -> Tuple[str, click.Command, List[str]]:
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


@click.group(
    cls=SBMCommandGroup,
    default_command="auto",
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.option("--config", "config_path", default="config.json", help="Path to config file.")
@click.pass_context
def cli(ctx: click.Context, verbose: bool, config_path: str) -> None:
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
    ctx.obj["config"] = config
    ctx.obj["logger"] = logger


@cli.command()
@click.argument("theme_name")
@click.option("--force-reset", is_flag=True, help="Force reset of existing Site Builder files.")
@click.option("--skip-maps", is_flag=True, help="Skip map components migration.")
def migrate(theme_name: str, force_reset: bool, skip_maps: bool) -> None:
    """
    Migrate a dealer theme SCSS files to Site Builder format.

    This command runs the core migration steps (create files, migrate styles, add predetermined styles,
    migrate maps) followed by manual review and post-migration validation/formatting.

    This does NOT include Git operations, Docker container management, or PR creation.
    Use 'sbm auto' for the full automated workflow including Git and PR operations.
    """
    from sbm.core.migration import (
        _cleanup_snapshot_files,
        _create_automation_snapshots,
        add_predetermined_styles,
        create_sb_files,
        migrate_map_components,
        migrate_styles,
        reprocess_manual_changes,
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
    click.echo("\n" + "=" * 80)
    click.echo(f"Manual Review Required for {theme_name}")
    click.echo("Please review the migrated SCSS files in your theme directory:")
    click.echo(f"  - {get_dealer_theme_dir(theme_name)}/sb-inside.scss")
    click.echo(f"  - {get_dealer_theme_dir(theme_name)}/sb-vdp.scss")
    click.echo(f"  - {get_dealer_theme_dir(theme_name)}/sb-vrp.scss")
    click.echo(f"  - {get_dealer_theme_dir(theme_name)}/sb-home.scss")
    click.echo("\nVerify the content and make any necessary manual adjustments.")
    click.echo("Once you are satisfied, proceed to the next step.")
    click.echo("=" * 80 + "\n")

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
@click.argument("theme_name")
@click.option("--skip-just", is_flag=True, help="Skip running the 'just start' command.")
@click.option("--force-reset", is_flag=True, help="Force reset of existing Site Builder files.")
@click.option(
    "--create-pr/--no-create-pr",
    default=True,
    help="Create a GitHub Pull Request after successful migration (default: True, with defaults: reviewers=carsdotcom/fe-dev, labels=fe-dev).",
)
@click.option(
    "--skip-post-migration",
    is_flag=True,
    help="Skip interactive manual review, re-validation, Git operations, and PR creation.",
)
@click.option(
    "--verbose-docker",
    is_flag=True,
    help="Show verbose Docker output during startup (for debugging).",
)
@click.pass_context
def auto(
    ctx: click.Context,
    theme_name: str,
    skip_just: bool,
    force_reset: bool,
    create_pr: bool,
    skip_post_migration: bool,
    verbose_docker: bool,
) -> None:
    """
    Run the full, automated migration for a given theme.
    This is the recommended command for most migrations.

    By default, prompts to create a published PR with default reviewers (carsdotcom/fe-dev)
    and labels (fe-dev). Use --no-create-pr to skip. For more control over PR creation,
    use 'sbm pr <theme-name>' separately.

    Use --skip-just to skip running the 'just start' command (if the site is already started).
    """
    # Get configuration and initialize Rich console
    config = ctx.obj.get("config", Config({}))
    console = get_console(config)

    # Show Rich migration start panel
    config_info = {
        "Skip Just": skip_just,
        "Force Reset": force_reset,
        "Create PR": create_pr,
        "Skip Post-Migration": skip_post_migration,
    }

    start_panel = StatusPanels.create_migration_status_panel(
        theme_name, "Initialization", "in_progress", config_info
    )
    console.console.print(start_panel)

    # Confirm migration start if not in non-interactive mode
    if not skip_post_migration:
        config_dict = {
            "skip_just": skip_just,
            "force_reset": force_reset,
            "create_pr": create_pr,
            "skip_post_migration": skip_post_migration,
        }

        if not InteractivePrompts.confirm_migration_start(theme_name, config_dict):
            console.print_info("Migration cancelled by user")
            return

    console.print_header("SBM Migration", f"Starting automated migration for {theme_name}")

    interactive_review = not skip_post_migration
    interactive_git = not skip_post_migration
    interactive_pr = not skip_post_migration

    # Create migration progress tracker
    progress = MigrationProgress()

    # Use Rich UI for beautiful output WITHOUT progress bars
    try:
        # Beautiful startup panel
        # Enhanced migration header with SBM branding
        console.print_migration_header(theme_name)

        # Initialize enhanced progress tracker (no more hanging issues!)
        progress_tracker = MigrationProgress(show_speed=False)

        # Run migration with enhanced progress tracking
        try:
            with progress_tracker.progress_context():
                # Add overall migration tracking
                migration_task_id = progress_tracker.add_migration_task(theme_name, 6)

                success = migrate_dealer_theme(
                    theme_name,
                    skip_just=skip_just,
                    force_reset=force_reset,
                    create_pr=create_pr,
                    interactive_review=False,  # Handle interactivity outside progress context
                    interactive_git=False,  # Handle interactivity outside progress context
                    interactive_pr=False,  # Handle interactivity outside progress context
                    progress_tracker=progress_tracker,  # Enhanced progress tracking enabled!
                    verbose_docker=verbose_docker,
                )

            # Handle interactive prompts AFTER progress context ends
            if success and (interactive_review or interactive_git or interactive_pr):
                # Import required for post-migration workflow
                # Get branch name - use theme-sbm date format
                from datetime import datetime

                from .core.migration import run_post_migration_workflow

                date_suffix = datetime.now().strftime("%m%d")
                branch_name = f"{theme_name}-sbm{date_suffix}"

                success = run_post_migration_workflow(
                    theme_name,
                    branch_name,
                    skip_git=skip_just,  # Use skip_just for skip_git logic
                    create_pr=create_pr,
                    interactive_review=interactive_review,
                    interactive_git=interactive_git,
                    interactive_pr=interactive_pr,
                )

        except KeyboardInterrupt:
            # Handle user interruption specifically
            console.print_warning("Migration interrupted by user")
            logger.info("Migration interrupted by user")
            sys.exit(1)
        except Exception as e:
            console.print_error(f"Migration failed: {e!s}")
            logger.error(f"Migration error: {e}", exc_info=True)
            success = False

        if success:
            # Enhanced completion with elapsed time tracking
            elapsed_time = progress_tracker.get_elapsed_time() if progress_tracker else 0.0
            console.print_migration_complete(theme_name, elapsed_time)
        else:
            console.print_error(f"❌ Migration failed for {theme_name}")
            sys.exit(1)

    except KeyboardInterrupt:
        # Handle outer-level user interruption
        console.print_warning("Migration interrupted by user")
        logger.info("Migration interrupted by user")
        sys.exit(1)
    except Exception as migration_error:
        # Handle any unexpected errors at the top level
        console.print_error(f"Unexpected migration error: {migration_error!s}")
        logger.exception("Unexpected migration error")
        sys.exit(1)


@cli.command()
@click.argument("theme_name")
def reprocess(theme_name: str) -> None:
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
@click.argument("theme_name")
def validate(theme_name: str) -> None:
    """Validate theme structure and SCSS syntax."""
    validate_scss_files(theme_name)


@cli.command()
@click.argument("theme_name")
def test_compilation(theme_name):
    """
    Test compilation error handling on an existing theme without doing migration.

    This command copies existing SCSS files to the CSS directory, monitors
    Docker Gulp compilation, and tests the error recovery system without
    modifying the original theme files.
    """
    click.echo(f"Testing compilation error recovery for {theme_name}...")

    if test_compilation_recovery(theme_name):
        click.echo("✅ Compilation test passed")
    else:
        click.echo("❌ Compilation test failed")
        sys.exit(1)


@cli.command()
@click.argument("theme_name")
@click.option("--skip-git", is_flag=True, help="Skip Git operations (add, commit, push).")
@click.option(
    "--create-pr/--no-create-pr",
    default=True,
    help="Create a GitHub Pull Request after successful post-migration steps (default: True, with defaults: reviewers=carsdotcom/fe-dev, labels=fe-dev).",
)
@click.option(
    "--skip-review", is_flag=True, help="Skip interactive manual review and re-validation."
)
@click.option("--skip-git-prompt", is_flag=True, help="Skip prompt for Git operations.")
@click.option("--skip-pr-prompt", is_flag=True, help="Skip prompt for PR creation.")
def post_migrate(theme_name, skip_git, create_pr, skip_review, skip_git_prompt, skip_pr_prompt):
    """
    Run post-migration steps for a given theme, including manual review, re-validation, Git operations, and PR creation.
    This command assumes the initial migration (up to map components) has already been completed.

    By default, prompts to create a published PR with default reviewers (carsdotcom/fe-dev)
    and labels (fe-dev). Use --no-create-pr to skip. For more control over PR creation,
    use 'sbm pr <theme-name>' separately.
    """
    from sbm.utils.path import get_platform_dir  # Import get_platform_dir

    click.echo(f"Starting post-migration workflow for {theme_name}...")

    # Attempt to get the current branch name for post-migration context
    try:
        repo = Repo(get_platform_dir())  # Use the platform root for the repo
        branch_name = repo.active_branch.name
    except Exception as e:
        click.echo(
            f"Error: Could not determine current Git branch for post-migration: {e}", err=True
        )
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
        interactive_pr=interactive_pr,
    )

    if success:
        click.echo(f"Post-migration workflow completed successfully for {theme_name}!")
    else:
        click.echo(f"Post-migration workflow failed for {theme_name}.", err=True)
        sys.exit(1)


@cli.command()
@click.argument("theme_name")
@click.option(
    "--title", "-t", help="Title for the Pull Request. (Optional: auto-generated if not provided)"
)
@click.option(
    "--body",
    "-b",
    help="Body/description for the Pull Request. (Optional: auto-generated if not provided)",
)
@click.option("--base", default="main", help="Base branch for the Pull Request (default: main).")
@click.option("--head", help="Head branch for the Pull Request (default: current branch).")
@click.option(
    "--reviewers", "-r", help="Comma-separated list of reviewers (default: carsdotcom/fe-dev)."
)
@click.option("--labels", "-l", help="Comma-separated list of labels (default: fe-dev).")
@click.option("--draft", "-d", is_flag=True, default=False, help="Create as draft PR.")
@click.option(
    "--publish", "-p", is_flag=True, default=True, help="Create as published PR (default: true)."
)
@click.pass_context
def pr(ctx, theme_name, title, body, base, head, reviewers, labels, draft, publish):
    """
    Create a GitHub Pull Request for a given theme.

    By default, creates a published PR with:
    - Reviewers: carsdotcom/fe-dev
    - Labels: fe-dev
    - Content: Auto-generated based on Git changes (Stellantis template)
    """
    config = ctx.obj["config"]
    logger = ctx.obj["logger"]

    from sbm.core.git import GitOperations

    git_ops = GitOperations(config)

    # Determine draft status
    is_draft = draft if draft else not publish

    # Parse reviewers and labels if provided
    parsed_reviewers = None
    parsed_labels = None
    if reviewers:
        parsed_reviewers = [r.strip() for r in reviewers.split(",")]
    if labels:
        parsed_labels = [l.strip() for l in labels.split(",")]

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
            draft=is_draft,
        )

        if pr_result["success"]:
            click.echo(f"✅ Pull request created: {pr_result['pr_url']}")
            click.echo(f"Title: {pr_result['title']}")
            click.echo(f"Branch: {pr_result['branch']}")
            if is_draft:
                click.echo("📝 Created as draft - remember to publish when ready")
            if pr_result.get("existing"):
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
        git_dir = os.path.join(REPO_ROOT, ".git")
        if not os.path.exists(git_dir):
            click.echo("❌ Not in a git repository. Cannot update.", err=True)
            sys.exit(1)

        # Check current branch
        current_branch_result = subprocess.run(
            ["git", "branch", "--show-current"],
            check=False,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=5,
        )

        if current_branch_result.returncode != 0:
            click.echo("❌ Could not determine current branch.", err=True)
            sys.exit(1)

        current_branch = current_branch_result.stdout.strip()

        # Stash changes if any
        status_result = subprocess.run(
            ["git", "status", "--porcelain"],
            check=False,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )

        has_changes = bool(status_result.stdout.strip())
        if has_changes:
            click.echo("Stashing local changes...")
            subprocess.run(
                ["git", "stash", "push", "-m", "Manual SBM update stash"], cwd=REPO_ROOT, check=True
            )

        # Perform git pull
        click.echo(f"Pulling latest changes from origin/{current_branch}...")
        pull_result = subprocess.run(
            ["git", "pull", "origin", current_branch],
            check=False,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )

        if pull_result.returncode == 0:
            if "Already up to date" in pull_result.stdout:
                click.echo("✅ Already up to date.")
            else:
                click.echo("✅ Successfully updated to latest version.")

                # Install/update requirements after git pull
                click.echo("Installing updated requirements...")
                try:
                    subprocess.run(
                        [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
                        cwd=REPO_ROOT,
                        check=True,
                    )
                    click.echo("✅ Requirements updated successfully.")
                except subprocess.CalledProcessError as e:
                    click.echo(f"⚠️  Warning: Failed to update requirements: {e}")

            # Restore stashed changes
            if has_changes:
                click.echo("Restoring local changes...")
                subprocess.run(["git", "stash", "pop"], cwd=REPO_ROOT, check=True)
        else:
            click.echo(f"❌ Update failed: {pull_result.stderr}", err=True)
            if has_changes:
                subprocess.run(["git", "stash", "pop"], check=False, cwd=REPO_ROOT)
            sys.exit(1)

    except subprocess.CalledProcessError as e:
        click.echo(f"❌ Update failed: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("theme_name")
@click.option("--no-cleanup", is_flag=True, help="Skip cleanup of test files (for debugging).")
@click.option("--max-iterations", default=3, help="Maximum error recovery iterations (default: 3).")
@click.option(
    "--timeout", default=45, help="Maximum wait time for compilation in seconds (default: 45)."
)
def test_compilation(theme_name, no_cleanup, max_iterations, timeout):
    """
    Test SCSS compilation error handling system without running a full migration.

    This command:
    1. Copies existing SCSS files from the theme to CSS directory for compilation testing
    2. Monitors Docker Gulp logs for compilation errors
    3. Applies the full error recovery pipeline with automated fixes
    4. Reports results and cleans up afterward (unless --no-cleanup is used)

    This allows testing the error handling capabilities on themes with known
    compilation issues without modifying the original files or running a full migration.
    """
    import time

    click.echo(f"🧪 Testing SCSS compilation error handling for {theme_name}...")
    click.echo(f"Max iterations: {max_iterations}, Timeout: {timeout}s")

    try:
        theme_dir = get_dealer_theme_dir(theme_name)
        css_dir = os.path.join(theme_dir, "css")

        # Check if theme directory exists
        if not os.path.exists(theme_dir):
            click.echo(f"❌ Theme directory not found: {theme_dir}", err=True)
            sys.exit(1)

        if not os.path.exists(css_dir):
            click.echo(f"❌ CSS directory not found: {css_dir}", err=True)
            sys.exit(1)

        # Find existing Site Builder SCSS files to test
        sb_files = ["sb-inside.scss", "sb-vdp.scss", "sb-vrp.scss", "sb-home.scss"]
        existing_files = []

        for sb_file in sb_files:
            file_path = os.path.join(theme_dir, sb_file)
            if os.path.exists(file_path):
                # Check if file has content
                with open(file_path) as f:
                    content = f.read().strip()
                if content:
                    existing_files.append(sb_file)

        if not existing_files:
            click.echo(f"❌ No Site Builder SCSS files with content found in {theme_name}")
            click.echo("Available files to test:")
            for sb_file in sb_files:
                file_path = os.path.join(theme_dir, sb_file)
                if os.path.exists(file_path):
                    click.echo(f"  - {sb_file} (empty)")
                else:
                    click.echo(f"  - {sb_file} (missing)")
            sys.exit(1)

        click.echo(
            f"📁 Found {len(existing_files)} SCSS files to test: {', '.join(existing_files)}"
        )

        # Copy files to CSS directory with test prefix
        test_files = []
        click.echo("📋 Copying SCSS files for compilation testing...")

        for sb_file in existing_files:
            src_path = os.path.join(theme_dir, sb_file)
            test_filename = f"test-compilation-{sb_file}"
            dst_path = os.path.join(css_dir, test_filename)

            shutil.copy2(src_path, dst_path)
            test_files.append((test_filename, dst_path))
            click.echo(f"  ✅ {sb_file} → {test_filename}")

        # Monitor compilation with enhanced error recovery
        click.echo("🔄 Starting compilation monitoring with error recovery...")
        click.echo(f"📊 Monitoring up to {max_iterations} recovery iterations...")

        start_time = time.time()
        success = _test_compilation_with_monitoring(
            css_dir, test_files, theme_dir, theme_name, max_iterations, timeout
        )
        total_time = time.time() - start_time

        # Report results
        click.echo(f"\n📈 Compilation Test Results for {theme_name}")
        click.echo("=" * 60)
        click.echo(f"Files tested: {len(test_files)}")
        click.echo(f"Total time: {total_time:.1f}s")
        click.echo(f"Result: {'✅ SUCCESS' if success else '❌ FAILED'}")

        if success:
            click.echo("\n🎉 All SCSS files compiled successfully!")
            click.echo("The error handling system is working correctly for this theme.")
        else:
            click.echo("\n⚠️  Compilation failed after all recovery attempts.")
            click.echo("This theme may have complex errors requiring manual fixes.")

            # Provide helpful debugging info
            click.echo("\n🔧 Debugging tips:")
            click.echo("- Check Docker logs: docker logs dealerinspire_legacy_assets")
            click.echo("- Use --no-cleanup to examine test files")
            click.echo("- Try increasing --max-iterations or --timeout")

        return success

    except Exception as e:
        click.echo(f"❌ Test failed with error: {e}", err=True)
        logger.error(f"Compilation test error: {e}")
        return False

    finally:
        # Cleanup unless disabled
        if not no_cleanup and "test_files" in locals():
            click.echo("\n🧹 Cleaning up test files...")
            _cleanup_test_files(css_dir, test_files)
        elif no_cleanup:
            click.echo(f"\n🔍 Test files preserved for debugging in: {css_dir}")
            if "test_files" in locals():
                click.echo("Test files:")
                for test_filename, _ in test_files:
                    click.echo(f"  - {test_filename}")


def _test_compilation_with_monitoring(
    css_dir, test_files, theme_dir, slug, max_iterations, timeout
):
    """
    Enhanced compilation monitoring specifically for testing error handling.

    Args:
        css_dir: CSS directory path
        test_files: List of (test_filename, scss_path) tuples
        theme_dir: Theme directory path
        slug: Theme slug
        max_iterations: Maximum recovery iterations
        timeout: Maximum wait time in seconds

    Returns:
        bool: True if compilation succeeds, False if all recovery attempts fail
    """
    import subprocess
    import time

    iteration = 0
    start_time = time.time()

    click.echo("🔄 Starting compilation monitoring...")

    while iteration < max_iterations and (time.time() - start_time) < timeout:
        iteration += 1
        click.echo(f"📍 Attempt {iteration}/{max_iterations}")

        # Wait for compilation cycle
        time.sleep(3)

        # Check Docker Gulp logs for errors
        try:
            result = subprocess.run(
                ["docker", "logs", "--tail", "50", "dealerinspire_legacy_assets"],
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0 and result.stdout:
                logs = result.stdout.lower()

                # Look for compilation success indicators
                if "finished 'sass'" in logs and "finished 'processcss'" in logs:
                    # Check if any errors in recent logs
                    if not any(
                        error_indicator in logs
                        for error_indicator in [
                            "error:",
                            "failed",
                            "scss compilation error",
                            "syntax error",
                        ]
                    ):
                        click.echo("✅ Compilation completed successfully")
                        return True

                # Parse and handle specific errors
                from .core.migration import _attempt_error_fix, _parse_compilation_errors

                errors_found = _parse_compilation_errors(logs, test_files)

                if errors_found:
                    click.echo(f"🔍 Found {len(errors_found)} compilation errors")

                    # Display errors for testing visibility
                    for i, error_info in enumerate(errors_found, 1):
                        error_type = error_info.get("type", "unknown")
                        error_msg = error_info.get("line_content", "No details")
                        click.echo(f"  {i}. {error_type}: {error_msg}")

                    # Attempt to fix each error
                    fixes_applied = 0
                    for error_info in errors_found:
                        if _attempt_error_fix(error_info, css_dir, theme_dir):
                            fixes_applied += 1

                    if fixes_applied > 0:
                        click.echo(f"🔧 Applied {fixes_applied} automated fixes, retrying...")
                        continue
                    click.echo("⚠️  No automated fixes available for detected errors")
                    break
                click.echo("⏳ No specific errors detected, waiting for compilation...")

        except subprocess.TimeoutExpired:
            click.echo("⏱️  Docker logs command timed out")
        except Exception as e:
            click.echo(f"⚠️  Error checking Docker logs: {e}")

        # Check for successful CSS file generation
        success_count = 0
        for test_filename, _ in test_files:
            css_filename = test_filename.replace(".scss", ".css")
            css_path = os.path.join(css_dir, css_filename)
            if os.path.exists(css_path):
                success_count += 1

        if success_count == len(test_files):
            click.echo("✅ All CSS files generated successfully")
            return True

        click.echo(f"📊 Compilation status: {success_count}/{len(test_files)} files compiled")

        # Check timeout
        elapsed = time.time() - start_time
        if elapsed >= timeout:
            click.echo(f"⏱️  Timeout reached ({timeout}s)")
            break

    # Final check and user option for manual intervention
    click.echo(f"❌ Compilation failed after {iteration} attempts")

    if click.confirm("🔧 Comment out problematic SCSS code to allow compilation?", default=False):
        _comment_out_problematic_code_for_test(test_files, css_dir)

        # Give one more chance after commenting out
        time.sleep(3)
        success_count = 0
        for test_filename, _ in test_files:
            css_filename = test_filename.replace(".scss", ".css")
            css_path = os.path.join(css_dir, css_filename)
            if os.path.exists(css_path):
                success_count += 1

        if success_count == len(test_files):
            click.echo("✅ Compilation successful after commenting out problematic code")
            return True

    return False


def _comment_out_problematic_code_for_test(test_files, css_dir):
    """
    Comment out potentially problematic SCSS code in test files.

    Args:
        test_files: List of test files
        css_dir: CSS directory path
    """
    click.echo("🔧 Commenting out potentially problematic SCSS code...")

    problematic_patterns = [
        r"@include\s+[^;]+;",  # All mixin includes
        r"lighten\([^)]+\)",  # lighten functions
        r"darken\([^)]+\)",  # darken functions
        r"\$[a-zA-Z_][a-zA-Z0-9_-]*",  # All SCSS variables
    ]

    for test_filename, scss_path in test_files:
        try:
            with open(scss_path) as f:
                content = f.read()

            lines = content.split("\n")
            modified = False

            for i, line in enumerate(lines):
                for pattern in problematic_patterns:
                    import re

                    if re.search(pattern, line):
                        if not line.strip().startswith("//"):
                            lines[i] = f"// TEST COMMENTED: {line}"
                            modified = True
                            break

            if modified:
                with open(scss_path, "w") as f:
                    f.write("\n".join(lines))

                click.echo(f"  ✅ Commented problematic code in {test_filename}")

        except Exception as e:
            click.echo(f"  ⚠️  Error processing {test_filename}: {e}")


def _cleanup_test_files(css_dir, test_files):
    """
    Clean up test files and wait for Docker Gulp to process the cleanup.

    Args:
        css_dir: CSS directory path
        test_files: List of (test_filename, scss_path) tuples
    """
    import time

    try:
        # Remove test files
        for test_filename, scss_path in test_files:
            try:
                # Remove test SCSS file
                if os.path.exists(scss_path):
                    os.remove(scss_path)

                # Remove generated CSS file
                css_filename = test_filename.replace(".scss", ".css")
                css_path = os.path.join(css_dir, css_filename)
                if os.path.exists(css_path):
                    os.remove(css_path)

            except Exception as e:
                click.echo(f"  ⚠️  Error removing {test_filename}: {e}")

        # Wait for Gulp cleanup cycle
        time.sleep(3)
        click.echo("✅ Test files cleaned up successfully")

    except Exception as e:
        click.echo(f"⚠️  Error during cleanup: {e}")


@cli.command()
@click.argument("action", type=click.Choice(["enable", "disable", "status"]))
def auto_update(action):
    """
    Manage auto-update settings for auto-sbm.

    Actions:
    - enable: Enable automatic updates (default behavior)
    - disable: Disable automatic updates
    - status: Show current auto-update status
    """
    disable_file = os.path.join(REPO_ROOT, ".sbm-no-auto-update")

    if action == "enable":
        if os.path.exists(disable_file):
            os.remove(disable_file)
            click.echo("✅ Auto-updates enabled. SBM will automatically update at startup.")
        else:
            click.echo("✅ Auto-updates are already enabled.")

    elif action == "disable":
        if not os.path.exists(disable_file):
            with open(disable_file, "w") as f:
                f.write("# This file disables auto-updates for auto-sbm\n")
                f.write("# Delete this file or run 'sbm auto-update enable' to re-enable\n")
            click.echo("✅ Auto-updates disabled. Run 'sbm auto-update enable' to re-enable.")
        else:
            click.echo("✅ Auto-updates are already disabled.")

    elif action == "status":
        if os.path.exists(disable_file):
            click.echo("❌ Auto-updates are DISABLED")
            click.echo("   Run 'sbm auto-update enable' to enable automatic updates")
        else:
            click.echo("✅ Auto-updates are ENABLED")
            click.echo("   SBM will automatically update to the latest version at startup")
            click.echo("   Run 'sbm auto-update disable' to disable automatic updates")


if __name__ == "__main__":
    cli()
