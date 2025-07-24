"""
Command-line interface for the SBM tool with Rich UI enhancements.

This module provides the command-line interface for the SBM tool with
Rich-enhanced progress tracking, status displays, and interactive elements.
"""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import click
from git import Repo

from .config import Config, ConfigurationError, get_config
from .core.git import GitOperations
from .core.migration import (
    _attempt_error_fix,
    _cleanup_snapshot_files,
    _create_automation_snapshots,
    _parse_compilation_errors,
    add_predetermined_styles,
    create_sb_files,
    migrate_dealer_theme,
    migrate_map_components,
    migrate_styles,
    reprocess_manual_changes,
    run_post_migration_workflow,
)
from .oem.factory import OEMFactory
from .scss.classifiers import StyleClassifier
from .scss.validator import validate_scss_files

# Rich UI imports
from .ui.console import get_console
from .ui.panels import StatusPanels
from .ui.progress import MigrationProgress
from .ui.prompts import InteractivePrompts
from .utils.helpers import get_branch_name
from .utils.logger import logger
from .utils.path import get_dealer_theme_dir, get_platform_dir

# --- Auto-run setup.sh if .sbm_setup_complete is missing or health check fails ---
REPO_ROOT = Path(__file__).parent.parent.resolve()
SETUP_MARKER = REPO_ROOT / ".sbm_setup_complete"
SETUP_SCRIPT = REPO_ROOT / "setup.sh"

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

    # If we're running from a different venv (like di-websites-platform), 
    # skip the venv health check since dependencies may be installed elsewhere
    import sys
    current_venv = getattr(sys, 'prefix', None)
    expected_venv = str(REPO_ROOT / ".venv")
    
    if current_venv and expected_venv not in current_venv:
        logger.debug(f"Running from different venv ({current_venv}), skipping auto-sbm venv health check")
        # Just check if the current environment has the required packages
        try:
            import click, rich, git, yaml, jinja2, pytest, requests, colorama
            # Also check for gitpython specifically since 'git' might be confusing
            import git as gitpython
            return True
        except ImportError as e:
            logger.warning(f"Required package not available in current environment: {e}")
            return False
    
    # Check Python venv and packages (only when running from auto-sbm venv)
    venv_path = REPO_ROOT / ".venv"
    pip_path = venv_path / "bin" / "pip"
    if not venv_path.is_dir() or not pip_path.is_file():
        logger.warning("Python virtual environment or pip not found")
        return False

    try:
        result = subprocess.run(
            [str(pip_path), "freeze"], check=False, capture_output=True, text=True, timeout=10
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
if not SETUP_MARKER.exists():
    need_setup = True
elif not is_env_healthy():
    logger.warning("Environment health check failed. Setup will be re-run to fix issues.")
    need_setup = True

if need_setup:
    logger.info("Running setup.sh...")
    try:
        result = subprocess.run(["bash", str(SETUP_SCRIPT)], check=False, cwd=str(REPO_ROOT))
        if result.returncode != 0:
            logger.error(
                "Setup.sh failed. Please review the output above and fix any issues "
                "before retrying."
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
    disable_file = REPO_ROOT / ".sbm-no-auto-update"
    if disable_file.exists():
        return  # Auto-update disabled by user

    try:
        # Check if we're in a git repository
        git_dir = REPO_ROOT / ".git"
        if not git_dir.exists():
            return  # Not a git repo, skip update

        # Check if we have network connectivity by testing git remote
        connectivity_check = subprocess.run(
            ["git", "ls-remote", "--exit-code", "origin", "HEAD"],
            check=False,
            cwd=str(REPO_ROOT),
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
            cwd=str(REPO_ROOT),
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
            cwd=str(REPO_ROOT),
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
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                timeout=10,
            )
            stash_created = stash_result.returncode == 0

        # Perform git pull
        pull_result = subprocess.run(
            ["git", "pull", "--quiet", "origin", current_branch],
            check=False,
            cwd=str(REPO_ROOT),
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
                    cwd=str(REPO_ROOT),
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
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                timeout=10,
            )

    except subprocess.TimeoutExpired:
        # Network timeout, skip silently
        pass
    except Exception as e:
        # Any other error, fail silently to not interrupt user workflow
        logger.debug(f"Auto-update failed silently: {e}")


def _check_and_run_setup_if_needed() -> None:
    """
    Check if setup needs to be run (if >8 hours since last setup) and run it silently.
    """
    setup_complete_file = REPO_ROOT / ".sbm_setup_complete"

    try:
        # Check if setup file exists and when it was last modified
        if setup_complete_file.exists():
            file_mtime = setup_complete_file.stat().st_mtime
            current_time = time.time()
            hours_since_setup = (current_time - file_mtime) / 3600

            if hours_since_setup <= 8:
                return  # Setup is still fresh, no need to run

        # Setup is needed - delete old marker and run setup
        if setup_complete_file.exists():
            setup_complete_file.unlink()

        # Run pip install requirements silently
        pip_result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
            check=False,
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=60,
        )

        if pip_result.returncode == 0:
            # Create the setup complete marker
            with setup_complete_file.open("w") as f:
                f.write(f"Setup completed at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")

    except Exception as e:
        # Silently ignore setup errors during auto-update
        logger.debug(f"Silent setup check failed: {e}")


# Run auto-update at CLI initialization
auto_update_repo()


class SBMCommandGroup(click.Group):
    """A custom command group that allows running a default command."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        self.default_command = kwargs.pop("default_command", None)
        super().__init__(*args, **kwargs)

    def resolve_command(
        self, ctx: click.Context, args: list[str]
    ) -> tuple[str, click.Command, list[str]]:
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
    By default, prompts to create PRs with default reviewers (carsdotcom/fe-dev)
    and labels (fe-dev). Use 'sbm pr <theme-name>' for manual PR creation or
    --no-create-pr to skip.
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
    if Path(config_path).exists():
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


def _perform_migration_steps(theme_name: str, force_reset: bool, skip_maps: bool) -> bool:
    """Run the core migration steps, returning success status."""
    oem_handler = OEMFactory.detect_from_theme(theme_name)
    logger.info(f"Using {oem_handler} for {theme_name}")

    # Step 1: Create Site Builder files
    logger.info(f"Step 1/4: Creating Site Builder files for {theme_name}...")
    if not create_sb_files(theme_name, force_reset):
        logger.error(f"Failed to create Site Builder files for {theme_name}")
        click.echo(f"❌ Failed to create Site Builder files for {theme_name}.", err=True)
        return False

    # Step 2: Migrate styles
    logger.info(f"Step 2/4: Migrating styles for {theme_name}...")
    if not migrate_styles(theme_name):
        logger.error(f"Failed to migrate styles for {theme_name}")
        click.echo(f"❌ Failed to migrate styles for {theme_name}.", err=True)
        return False

    # Step 3: Add predetermined styles
    logger.info(f"Step 3/4: Adding predetermined styles for {theme_name}...")
    if not add_predetermined_styles(theme_name):
        logger.error(f"Failed to add predetermined styles for {theme_name}")
        click.echo(f"❌ Failed to add predetermined styles for {theme_name}.", err=True)
        return False

    # Step 4: Migrate map components if not skipped
    if not skip_maps:
        logger.info(f"Step 4/4: Migrating map components for {theme_name}...")
        if not migrate_map_components(theme_name, oem_handler):
            logger.error(f"Failed to migrate map components for {theme_name}")
            click.echo(f"❌ Failed to migrate map components for {theme_name}.", err=True)
            return False
        logger.info(f"Map components migrated successfully for {theme_name}")
    else:
        logger.info(f"Step 4/4: Skipping map components migration for {theme_name}")

    return True


@cli.command()
@click.argument("theme_name")
@click.option("--force-reset", is_flag=True, help="Force reset of existing Site Builder files.")
@click.option("--skip-maps", is_flag=True, help="Skip map components migration.")
def migrate(theme_name: str, force_reset: bool, skip_maps: bool) -> None:
    """
    Migrate a dealer theme SCSS files to Site Builder format.

    This command runs the core migration steps (create files, migrate styles, add
    predetermined styles, migrate maps) followed by manual review and post-migration
    validation/formatting.

    This does NOT include Git operations, Docker container management, or PR creation.
    Use 'sbm auto' for the full automated workflow including Git and PR operations.
    """
    click.echo(f"Starting SCSS migration for {theme_name}...")

    if not _perform_migration_steps(theme_name, force_reset, skip_maps):
        sys.exit(1)

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

    # Reprocess manual changes to ensure consistency (includes validation, fixing issues,
    # prettier formatting)
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
    help="Create a GitHub Pull Request after successful migration (default: True, with "
         "defaults: reviewers=carsdotcom/fe-dev, labels=fe-dev).",
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

    # Check if we're in fullauto mode
    from .features.fullauto_mode import is_fullauto_active
    fullauto_active = is_fullauto_active()
    
    # Confirm migration start if not in non-interactive mode and not in fullauto mode
    if not skip_post_migration and not fullauto_active:
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
    
    if fullauto_active:
        logger.info("Fullauto mode detected - disabling all interactive prompts")
        interactive_review = False
        interactive_git = False
        interactive_pr = False
    else:
        interactive_review = not skip_post_migration
        interactive_git = not skip_post_migration
        interactive_pr = not skip_post_migration

    # Start migration timer and patch click.confirm for timing 
    from .utils.timer import start_migration_timer, timer_segment, patch_click_confirm_for_timing
    migration_timer = start_migration_timer(theme_name)
    
    # Patch click.confirm to pause timer during user interactions (unless in fullauto mode)
    original_confirm = None
    if not fullauto_active:
        original_confirm = patch_click_confirm_for_timing()
    
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
                with timer_segment("Complete Migration Process"):
                    success = migrate_dealer_theme(
                        theme_name,
                        skip_just=skip_just,
                        force_reset=force_reset,
                        create_pr=create_pr,
                        interactive_review=interactive_review,
                        interactive_git=interactive_git,
                        interactive_pr=interactive_pr,
                        progress_tracker=progress_tracker,  # Enhanced progress tracking enabled!
                        verbose_docker=verbose_docker,
                    )

            # Handle interactive prompts AFTER progress context ends
            if success and (interactive_review or interactive_git or interactive_pr):
                # Get branch name - use centralized helper function
                branch_name = get_branch_name(theme_name)

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
            # Enhanced completion with elapsed time tracking and timing breakdown
            elapsed_time = progress_tracker.get_elapsed_time() if progress_tracker else 0.0
            timing_summary = progress_tracker.get_timing_summary() if progress_tracker else None
            console.print_migration_complete(theme_name, elapsed_time, timing_summary)
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
    finally:
        # Restore original click.confirm if we patched it
        if original_confirm and not fullauto_active:
            from .utils.timer import restore_click_confirm
            restore_click_confirm(original_confirm)
        
        # Always finish the timer
        from .utils.timer import finish_migration_timer
        finish_migration_timer()


@cli.command()
@click.argument("theme_name")
def fullauto(theme_name: str) -> None:
    """
    Run full automated migration with zero user prompts (except errors).
    
    This command runs the complete migration workflow from start to PR creation
    without any user interaction, except for compilation errors that require 
    manual intervention.
    
    Equivalent to: sbm auto <theme-name> with all interactive flags disabled.
    """
    from .features.fullauto_mode import create_fullauto_context
    
    # Use fullauto context to manage prompt bypassing
    with create_fullauto_context(enabled=True):
        ctx = click.get_current_context()
        ctx.invoke(
            auto, 
            theme_name=theme_name, 
            skip_just=False, 
            force_reset=False,
            create_pr=True, 
            skip_post_migration=False, 
            verbose_docker=False
        )


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

    success = reprocess_manual_changes(theme_name)

    if success:
        click.echo(f"✅ Reprocessing completed successfully for {theme_name}!")
    else:
        click.echo(f"❌ Reprocessing failed for {theme_name}.", err=True)
        sys.exit(1)


@cli.command()
@click.argument("theme_name")
@click.option(
    "--check-exclusions",
    is_flag=True,
    help="Check for header/footer/navigation styles that should be excluded.",
)
@click.option(
    "--show-excluded",
    is_flag=True,
    help="Show excluded rules (use with --check-exclusions).",
)
def validate(theme_name: str, check_exclusions: bool, show_excluded: bool) -> None:
    """
    Validate theme structure and SCSS syntax.

    Args:
        theme_name: Name of the dealer theme to validate
        check_exclusions: Whether to check for header/footer/navigation styles
        show_excluded: Whether to display excluded rules (requires check_exclusions)
    """
    validate_scss_files(theme_name)

    # Style exclusion validation
    if check_exclusions:

        theme_dir = get_dealer_theme_dir(theme_name)
        classifier = StyleClassifier(strict_mode=True)

        sb_files = ["sb-inside.scss", "sb-vdp.scss", "sb-vrp.scss", "sb-home.scss"]
        total_excluded = 0
        total_checked = 0

        click.echo(f"\n🔍 Checking style exclusions for {theme_name}...")
        click.echo("=" * 60)

        for sb_file in sb_files:
            file_path = Path(theme_dir) / sb_file
            if file_path.exists():
                result = classifier.analyze_file(file_path)
                total_excluded += result.excluded_count
                total_checked += 1

                if result.excluded_count > 0:
                    click.echo(f"📄 {sb_file}:")
                    click.echo(f"  ⚠️  Found {result.excluded_count} excluded rules")
                    for category, count in result.patterns_matched.items():
                        click.echo(f"    - {category}: {count} rules")

                    if show_excluded and result.excluded_rules:
                        click.echo("  📝 Excluded rules:")
                        for i, rule in enumerate(result.excluded_rules[:3], 1):  # Show first 3
                            rule_preview = rule.split("\n")[0][:50]
                            click.echo(f"    {i}. {rule_preview}...")
                        if len(result.excluded_rules) > 3:
                            click.echo(f"    ... and {len(result.excluded_rules) - 3} more")
                else:
                    click.echo(f"✅ {sb_file}: No excluded styles found")
            else:
                click.echo(f"⚪ {sb_file}: File not found")

        click.echo("=" * 60)
        if total_excluded > 0:
            click.echo(
                f"⚠️  SUMMARY: Found {total_excluded} header/footer/nav rules "
                "that should be excluded"
            )
            click.echo("💡 These styles may conflict with Site Builder components")
            if not show_excluded:
                click.echo("   Use --show-excluded to see the specific rules")
        else:
            click.echo("✅ SUMMARY: No problematic header/footer/navigation styles found")

        click.echo(f"📊 Checked {total_checked} Site Builder files")


@cli.command()
@click.argument("theme_name")
@click.option("--skip-git", is_flag=True, help="Skip Git operations (add, commit, push).")
@click.option(
    "--create-pr/--no-create-pr",
    default=True,
    help="Create a GitHub Pull Request after successful post-migration steps "
         "(default: True, with defaults: reviewers=carsdotcom/fe-dev, labels=fe-dev).",
)
@click.option(
    "--skip-review", is_flag=True, help="Skip interactive manual review and re-validation."
)
@click.option("--skip-git-prompt", is_flag=True, help="Skip prompt for Git operations.")
@click.option("--skip-pr-prompt", is_flag=True, help="Skip prompt for PR creation.")
def post_migrate(
    theme_name: str,
    skip_git: bool,
    create_pr: bool,
    skip_review: bool,
    skip_git_prompt: bool,
    skip_pr_prompt: bool
) -> None:
    """
    Run post-migration steps for a given theme, including manual review, re-validation,
    Git operations, and PR creation.
    This command assumes the initial migration (up to map components) has already been completed.

    By default, prompts to create a published PR with default reviewers (carsdotcom/fe-dev)
    and labels (fe-dev). Use --no-create-pr to skip. For more control over PR creation,
    use 'sbm pr <theme-name>' separately.
    """
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
def pr(
    ctx: click.Context,
    theme_name: str,
    title: str | None,
    body: str | None,
    base: str,
    head: str | None,
    reviewers: str | None,
    labels: str | None,
    draft: bool,
    publish: bool
) -> None:
    """
    Create a GitHub Pull Request for a given theme.

    By default, creates a published PR with:
    - Reviewers: carsdotcom/fe-dev
    - Labels: fe-dev
    - Content: Auto-generated based on Git changes (Stellantis template)
    """
    config = ctx.obj["config"]
    logger = ctx.obj["logger"]

    git_ops = GitOperations(config)

    # Determine draft status
    is_draft = draft if draft else not publish

    # Parse reviewers and labels if provided
    parsed_reviewers = None
    parsed_labels = None
    if reviewers:
        parsed_reviewers = [r.strip() for r in reviewers.split(",")]
    if labels:
        parsed_labels = [label.strip() for label in labels.split(",")]

    try:
        # The create_pr method in GitOperations will handle branch detection
        # and PR content generation.
        logger.info("Creating GitHub PR for %s...", theme_name)
        pr_result = git_ops.create_pr(
            slug=theme_name,
            branch_name=head,
            # Pass head directly, GitOperations will handle current branch if head is None
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
                click.echo("ℹ️  PR already existed - retrieved existing PR URL")  # noqa: RUF001
        else:
            click.echo(f"❌ PR creation failed: {pr_result['error']}", err=True)
            sys.exit(1)

    except Exception:
        logger.exception("Unexpected error occurred")
        sys.exit(1)


def _validate_git_repository() -> None:
    """Validate we're in a git repository."""
    git_dir = REPO_ROOT / ".git"
    if not git_dir.exists():
        click.echo("❌ Not in a git repository. Cannot update.", err=True)
        sys.exit(1)


def _get_current_branch() -> str:
    """Get the current git branch name."""
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        check=False,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=5,
    )

    if result.returncode != 0:
        click.echo("❌ Could not determine current branch.", err=True)
        sys.exit(1)

    return result.stdout.strip()


def _stash_changes_if_needed() -> bool:
    """Stash local changes if any exist. Returns True if changes were stashed."""
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
            ["git", "stash", "push", "-m", "Manual SBM update stash"],
            cwd=REPO_ROOT,
            check=True
        )

    return has_changes


def _update_dependencies() -> None:
    """Update requirements and reinstall package."""
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

    # Reinstall auto-sbm package to reflect code changes
    click.echo("Reinstalling auto-sbm package...")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-e", "."],
            cwd=REPO_ROOT,
            check=True,
        )
        click.echo("✅ Auto-sbm package reinstalled successfully.")
    except subprocess.CalledProcessError as e:
        click.echo(f"⚠️  Warning: Failed to reinstall auto-sbm package: {e}")


def _restore_stashed_changes() -> None:
    """Restore previously stashed changes."""
    click.echo("Restoring local changes...")
    subprocess.run(["git", "stash", "pop"], cwd=REPO_ROOT, check=True)


@cli.command()
def update() -> None:
    """Manually update auto-sbm to the latest version."""
    click.echo("Manually updating auto-sbm...")

    try:
        _validate_git_repository()
        current_branch = _get_current_branch()
        has_changes = _stash_changes_if_needed()

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
                _update_dependencies()

            # Restore stashed changes
            if has_changes:
                _restore_stashed_changes()
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
def test_compilation(
    theme_name: str, no_cleanup: bool, max_iterations: int, timeout: int
) -> None:
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
    click.echo(f"🧪 Testing SCSS compilation error handling for {theme_name}...")
    click.echo(f"Max iterations: {max_iterations}, Timeout: {timeout}s")

    theme_dir = Path(get_dealer_theme_dir(theme_name))
    css_dir = theme_dir / "css"
    test_files: list[tuple[str, Path]] = []
    success = False

    try:
        _validate_test_compilation_dirs(theme_dir, css_dir)
        existing_files = _find_existing_scss_files(theme_dir)
        test_files = _prepare_test_files(existing_files, theme_dir, css_dir)

        click.echo("🔄 Starting compilation monitoring with error recovery...")
        click.echo(f"📊 Monitoring up to {max_iterations} recovery iterations...")

        start_time = time.time()
        success = _test_compilation_with_monitoring(
            css_dir, test_files, theme_dir, max_iterations, timeout
        )
        total_time = time.time() - start_time

        _report_test_results(theme_name, len(test_files), total_time, success)

    except (ValueError, FileNotFoundError) as e:
        click.echo(f"❌ Test setup failed: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Test failed with error: {e}", err=True)
        logger.error(f"Compilation test error: {e}")
    finally:
        if not no_cleanup and test_files:
            click.echo("\n🧹 Cleaning up test files...")
            _cleanup_test_files(css_dir, test_files)
        elif no_cleanup:
            click.echo(f"\n🔍 Test files preserved for debugging in: {css_dir}")
            if test_files:
                click.echo("Test files:")
                for test_filename, _ in test_files:
                    click.echo(f"  - {test_filename}")


def _validate_test_compilation_dirs(theme_dir: Path, css_dir: Path) -> None:
    """Check if theme and css directories exist for test compilation."""
    if not theme_dir.exists():
        msg = f"Theme directory not found: {theme_dir}"
        raise FileNotFoundError(msg)
    if not css_dir.exists():
        msg = f"CSS directory not found: {css_dir}"
        raise FileNotFoundError(msg)


def _find_existing_scss_files(theme_dir: Path) -> list[str]:
    """Find existing, non-empty SCSS files in the theme directory."""
    sb_files = ["sb-inside.scss", "sb-vdp.scss", "sb-vrp.scss", "sb-home.scss"]
    existing_files = []
    for sb_file in sb_files:
        file_path = theme_dir / sb_file
        if file_path.exists() and file_path.read_text().strip():
            existing_files.append(sb_file)

    if not existing_files:
        missing_files_info = []
        for sb_file in sb_files:
            file_path = theme_dir / sb_file
            status = "empty" if file_path.exists() else "missing"
            missing_files_info.append(f"  - {sb_file} ({status})")
        raise ValueError(
            "No Site Builder SCSS files with content found.\n"
            "Available files to test:\n" + "\n".join(missing_files_info)
        )
    return existing_files


def _prepare_test_files(
    existing_files: list[str], theme_dir: Path, css_dir: Path
) -> list[tuple[str, Path]]:
    """Copy SCSS files to a test location for compilation."""
    click.echo(f"📁 Found {len(existing_files)} SCSS files to test: {', '.join(existing_files)}")
    test_files = []
    click.echo("📋 Copying SCSS files for compilation testing...")
    for sb_file in existing_files:
        src_path = theme_dir / sb_file
        test_filename = f"test-compilation-{sb_file}"
        dst_path = css_dir / test_filename
        shutil.copy2(src_path, dst_path)
        test_files.append((test_filename, dst_path))
        click.echo(f"  ✅ {sb_file} → {test_filename}")
    return test_files


def _report_test_results(
    theme_name: str, num_files: int, total_time: float, success: bool
) -> None:
    """Report the final results of the compilation test."""
    click.echo(f"\n📈 Compilation Test Results for {theme_name}")
    click.echo("=" * 60)
    click.echo(f"Files tested: {num_files}")
    click.echo(f"Total time: {total_time:.1f}s")
    click.echo(f"Result: {'✅ SUCCESS' if success else '❌ FAILED'}")

    if success:
        click.echo("\n🎉 All SCSS files compiled successfully!")
        click.echo("The error handling system is working correctly for this theme.")
    else:
        click.echo("\n⚠️  Compilation failed after all recovery attempts.")
        click.echo("This theme may have complex errors requiring manual fixes.")
        click.echo("\n🔧 Debugging tips:")
        click.echo("- Check Docker logs: docker logs dealerinspire_legacy_assets")
        click.echo("- Use --no-cleanup to examine test files")
        click.echo("- Try increasing --max-iterations or --timeout")


def _test_compilation_with_monitoring(
    css_dir: Path,
    test_files: list[tuple[str, Path]],
    theme_dir: Path,
    max_iterations: int,
    timeout: int,
) -> bool:
    """
    Enhanced compilation monitoring specifically for testing error handling.
    """
    iteration = 0
    start_time = time.time()
    click.echo("🔄 Starting compilation monitoring...")

    while iteration < max_iterations and (time.time() - start_time) < timeout:
        iteration += 1
        click.echo(f"📍 Attempt {iteration}/{max_iterations}")
        time.sleep(3)

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
                if (
                    "finished 'sass'" in logs
                    and "finished 'processcss'" in logs
                    and not any(
                        error_indicator in logs
                        for error_indicator in [
                            "error:",
                            "failed",
                            "scss compilation error",
                            "syntax error",
                        ]
                    )
                ):
                    click.echo("✅ Compilation completed successfully")
                    return True

                errors_found = _parse_compilation_errors(logs, test_files)
                if errors_found:
                    click.echo(f"🔍 Found {len(errors_found)} compilation errors")
                    for i, error_info in enumerate(errors_found, 1):
                        error_type = error_info.get("type", "unknown")
                        error_msg = error_info.get("line_content", "No details")
                        click.echo(f"  {i}. {error_type}: {error_msg}")

                    fixes_applied = sum(
                        _attempt_error_fix(error, css_dir, theme_dir) for error in errors_found
                    )
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

        success_count = sum(
            (css_dir / f.replace(".scss", ".css")).exists() for f, _ in test_files
        )
        if success_count == len(test_files):
            click.echo("✅ All CSS files generated successfully")
            return True
        click.echo(f"📊 Compilation status: {success_count}/{len(test_files)} files compiled")

        if (time.time() - start_time) >= timeout:
            click.echo(f"⏱️  Timeout reached ({timeout}s)")
            break

    click.echo(f"❌ Compilation failed after {iteration} attempts")
    if click.confirm("🔧 Comment out problematic SCSS code to allow compilation?", default=False):
        _comment_out_problematic_code_for_test(test_files)
        time.sleep(3)
        success_count = sum(
            (css_dir / f.replace(".scss", ".css")).exists() for f, _ in test_files
        )
        if success_count == len(test_files):
            click.echo("✅ Compilation successful after commenting out problematic code")
            return True
    return False


def _comment_out_problematic_code_for_test(
    test_files: list[tuple[str, Path]]
) -> None:
    """Comment out potentially problematic SCSS code in test files."""
    click.echo("🔧 Commenting out potentially problematic SCSS code...")
    problematic_patterns = [
        r"@include\s+[^;]+;",
        r"lighten\([^)]+\)",
        r"darken\([^)]+\)",
        r"\$[a-zA-Z_][a-zA-Z0-9_-]*",
    ]
    for test_filename, scss_path in test_files:
        try:
            content = scss_path.read_text()
            lines = content.split("\n")
            modified = False
            for i, line in enumerate(lines):
                if not line.strip().startswith("//") and any(
                    re.search(p, line) for p in problematic_patterns
                ):
                    lines[i] = f"// TEST COMMENTED: {line}"
                    modified = True
            if modified:
                scss_path.write_text("\n".join(lines))
                click.echo(f"  ✅ Commented problematic code in {test_filename}")
        except Exception as e:
            click.echo(f"  ⚠️  Error processing {test_filename}: {e}")


def _cleanup_test_files(css_dir: Path, test_files: list[tuple[str, Path]]) -> None:
    """Clean up test files and wait for Docker Gulp to process the cleanup."""
    try:
        for test_filename, scss_path in test_files:
            try:
                if scss_path.exists():
                    scss_path.unlink()
                css_path = css_dir / test_filename.replace(".scss", ".css")
                if css_path.exists():
                    css_path.unlink()
            except Exception as e:
                click.echo(f"  ⚠️  Error removing {test_filename}: {e}")
        time.sleep(3)
        click.echo("✅ Test files cleaned up successfully")
    except Exception as e:
        click.echo(f"⚠️  Error during cleanup: {e}")





@cli.command()
def version() -> None:
    """Display version information."""
    click.echo("auto-sbm version 2.0.0")
    click.echo("Site Builder Migration Tool")


@cli.command()
@click.argument("action", type=click.Choice(["enable", "disable", "status"]))
def auto_update(action: str) -> None:
    """
    Manage auto-update settings for auto-sbm.

    Actions:
    - enable: Enable automatic updates (default behavior)
    - disable: Disable automatic updates
    - status: Show current auto-update status
    """
    disable_file = REPO_ROOT / ".sbm-no-auto-update"

    if action == "enable":
        if disable_file.exists():
            disable_file.unlink()
            click.echo("✅ Auto-updates enabled. SBM will automatically update at startup.")
        else:
            click.echo("✅ Auto-updates are already enabled.")

    elif action == "disable":
        if not disable_file.exists():
            with disable_file.open("w") as f:
                f.write("# This file disables auto-updates for auto-sbm\n")
                f.write("# Delete this file or run 'sbm auto-update enable' to re-enable\n")
            click.echo("✅ Auto-updates disabled. Run 'sbm auto-update enable' to re-enable.")
        else:
            click.echo("✅ Auto-updates are already disabled.")

    elif action == "status":
        if disable_file.exists():
            click.echo("❌ Auto-updates are DISABLED")
            click.echo("   Run 'sbm auto-update enable' to enable automatic updates")
        else:
            click.echo("✅ Auto-updates are ENABLED")
            click.echo("   SBM will automatically update to the latest version at startup")
            click.echo("   Run 'sbm auto-update disable' to disable automatic updates")


if __name__ == "__main__":
    cli()
