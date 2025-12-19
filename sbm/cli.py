"""
Command-line interface for the SBM tool with Rich UI enhancements.

This module provides the command-line interface for the SBM tool with
Rich-enhanced progress tracking, status displays, and interactive elements.
"""

from __future__ import annotations

import datetime
import sys
import os
import json
import time
import subprocess
import shutil
import platform
import webbrowser
import logging
import re
import datetime
from datetime import date
from typing import Any, Dict, List, Optional, Tuple, Union
from pathlib import Path

import click
from git import Repo

from .utils.timer import get_total_automation_time, get_total_duration
from .utils.version_utils import get_changelog, get_version
from sbm.utils.processes import run_background_task
from sbm.utils.tracker import (
    get_migration_stats,
    record_migration,
    record_run,
    sync_global_stats,
)

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
from .ui.prompts import InteractivePrompts
from .utils.logger import logger
from .utils.path import get_dealer_theme_dir, get_platform_dir

# --- Auto-run setup.sh if .sbm_setup_complete is missing or health check fails ---
# Use the predictable installation location as the primary root
REPO_ROOT = Path.home() / "auto-sbm"

# If not found at the legacy location, fallback to the current file's parent
if not REPO_ROOT.exists():
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

    # If we're running from a different venv (like di-websites-platform) or
    # if this is an external installation, skip detailed health checks
    import os
    import sys

    current_venv = getattr(sys, "prefix", None)
    expected_venv = str(REPO_ROOT / ".venv")
    current_dir = os.getcwd()

    # Skip health check if:
    # 1. Running from different venv
    # 2. Not running from within auto-sbm directory
    # 3. Auto-sbm installed as external package
    if (current_venv and expected_venv not in current_venv) or (str(REPO_ROOT) not in current_dir):
        logger.debug(f"External usage detected (venv: {current_venv}, dir: {current_dir})")
        logger.debug("Skipping detailed health check for external auto-sbm usage")
        # Just verify basic functionality - if sbm command works, we're good
        return True

    # Only do detailed health checks when running from auto-sbm development environment
    logger.debug("Running detailed health check for auto-sbm development environment")

    # Check Python venv and packages (only when running from auto-sbm venv)
    venv_path = REPO_ROOT / ".venv"
    pip_path = venv_path / "bin" / "pip"
    if not venv_path.is_dir() or not pip_path.is_file():
        logger.warning("Python virtual environment or pip not found")
        return False

    # Check if packages are importable instead of relying on pip freeze
    # This works better with editable installs where dependencies may not show individually
    python_path = venv_path / "bin" / "python"
    if not python_path.is_file():
        logger.warning("Python interpreter not found in virtual environment")
        return False

    # Map package names to import names (some differ)
    import_map = {
        "gitpython": "git",
        "pyyaml": "yaml",
        "pytest": "pytest",
        "click": "click",
        "rich": "rich",
        "jinja2": "jinja2",
        "requests": "requests",
        "colorama": "colorama",
    }

    try:
        for pkg, import_name in import_map.items():
            result = subprocess.run(
                [str(python_path), "-c", f"import {import_name}"],
                check=False,
                capture_output=True,
                timeout=5,
            )
            if result.returncode != 0:
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
# Only run setup when in auto-sbm development environment

current_dir = os.getcwd()
in_auto_sbm_repo = str(REPO_ROOT) in current_dir

need_setup = False
if in_auto_sbm_repo:  # Only check setup when running from auto-sbm repo
    if not SETUP_MARKER.exists():
        need_setup = True
    elif not is_env_healthy():
        logger.warning("Environment health check failed. Setup will be re-run to fix issues.")
        need_setup = True
else:
    logger.debug("Running auto-sbm from external environment - skipping setup checks")

if need_setup and in_auto_sbm_repo:
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

        # Check connectivity
        if (
            subprocess.run(
                ["git", "ls-remote", "--exit-code", "origin", "HEAD"],
                check=False,
                cwd=str(REPO_ROOT),
                capture_output=True,
                timeout=5,
            ).returncode
            != 0
        ):
            return

        # Check strictly for detached HEAD
        # git symbolic-ref -q HEAD returns 0 if on branch, 1 if detached
        if (
            subprocess.run(
                ["git", "symbolic-ref", "-q", "HEAD"],
                check=False,
                cwd=str(REPO_ROOT),
                capture_output=True,
            ).returncode
            != 0
        ):
            logger.debug("Detached HEAD detected; skipping auto-update.")
            return

        # Get current branch name
        branch_res = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            check=False,
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        if branch_res.returncode != 0:
            return

        current_branch = branch_res.stdout.strip()
        if current_branch not in ["main", "master"]:
            return

        # Check for uncommitted changes
        status_res = subprocess.run(
            ["git", "status", "--porcelain"],
            check=False,
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=5,
        )
        has_changes = bool(status_res.stdout.strip())
        stash_created = False

        if has_changes:
            stash_res = subprocess.run(
                ["git", "stash", "push", "-m", "SBM auto-update stash"],
                check=False,
                cwd=str(REPO_ROOT),
                capture_output=True,
                timeout=10,
            )
            stash_created = stash_res.returncode == 0

        try:
            # Perform pull with rebase to handle divergent branches seamlessly
            pull_res = subprocess.run(
                ["git", "pull", "--rebase", "--quiet", "origin", current_branch],
                check=False,
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                timeout=15,
            )

            if pull_res.returncode == 0:
                if pull_res.stdout.strip() and "Already up to date" not in pull_res.stdout:
                    logger.debug("Auto-updated to latest version.")
                _check_and_run_setup_if_needed()
            else:
                # Log error but don't block tool execution
                error_msg = pull_res.stderr.strip() if pull_res.stderr else "Unknown error"
                if "reconcile divergent branches" in error_msg:
                    logger.warning(
                        "⚠️ Auto-update failed: Divergent branches detected. "
                        "The tool will continue, but you may be on an outdated version. "
                        "Try running: 'git pull --rebase origin master' manually in ~/auto-sbm"
                    )
                else:
                    logger.debug(f"Auto-update pull failed: {error_msg}")
        finally:
            # ALWAYS attempt to restore stash if we created one
            if stash_created:
                restore_res = subprocess.run(
                    ["git", "stash", "pop"],
                    check=False,
                    cwd=str(REPO_ROOT),
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if restore_res.returncode != 0:
                    logger.warning(
                        "⚠️ Could not restore local changes due to conflicts. "
                        "Your changes are saved in stash. Run 'git stash list' and "
                        "'git stash pop' manually after resolving conflicts."
                    )

    except Exception as e:
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


def check_and_run_daily_update():
    """Check if sbm update needs to run (once per calendar day) and run it automatically."""
    try:
        # Get current date
        today = datetime.date.today().isoformat()

        # Search for .git in parent directories
        update_file = Path.cwd() / ".sbm_last_update"

        # Read last update date if file exists
        last_update = None
        if update_file.exists():
            try:
                last_update = update_file.read_text().strip()
            except Exception:
                pass

        # If we haven't updated today, run update
        if last_update != today:
            click.echo("🔄 Running daily auto-update...")

            # Run sbm update command
            result = subprocess.run(
                [sys.executable, "-m", "sbm.cli", "update"],
                check=False,
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent,
            )

            if result.returncode == 0:
                # Update successful - record today's date
                update_file.write_text(today)
                click.echo("✅ Auto-update completed successfully")
            else:
                # Update failed - continue anyway but warn
                click.echo(f"⚠️ Auto-update failed: {result.stderr.strip()}")

    except Exception as e:
        # Auto-update failure shouldn't break the main command
        click.echo(f"⚠️ Auto-update error (continuing): {e}")


@click.group(
    cls=SBMCommandGroup,
    default_command="auto",
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.option("--yes", "-y", is_flag=True, help="Auto-confirm all prompts (non-interactive mode)")
@click.option("--config", "config_path", default="config.json", help="Path to config file.")
@click.pass_context
def cli(ctx: click.Context, verbose: bool, yes: bool, config_path: str) -> None:
    """Auto-SBM: Automated Site Builder Migration Tool

    The main command for SBM migration with GitHub PR creation support.
    By default, prompts to create PRs with default reviewers (carsdotcom/fe-dev)
    and labels (fe-dev). Use 'sbm pr <theme-name>' for manual PR creation or
    --no-create-pr to skip.
    """
    from sbm.config import get_settings

    # Set logger level based on verbose flag
    if verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    # Set non-interactive mode if --yes is passed
    if yes:
        get_settings().non_interactive = True
        logger.info("Non-interactive mode enabled via --yes flag")

    # Run daily auto-update check (unless this is the update command itself)
    if ctx.invoked_subcommand != "update":
        check_and_run_daily_update()

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


def _expand_theme_names(theme_names: tuple[str, ...]) -> list[str]:
    """
    Expand theme names from arguments and optional file references.

    Args:
        theme_names: A tuple of theme names or file paths (prefixed with @)

    Returns:
        A list of expanded theme names (slugs)
    """
    expanded = []
    for name in theme_names:
        if name.startswith("@"):
            file_path_str = name[1:]
            file_path = Path(file_path_str)

            # 1. Try relative to CWD
            # 2. Try relative to REPO_ROOT (fallback for external execution)
            if not file_path.exists():
                fallback_path = REPO_ROOT / file_path_str
                if fallback_path.exists():
                    file_path = fallback_path
                else:
                    logger.error(
                        f"Theme list file not found: {file_path_str} (checked CWD and {REPO_ROOT})"
                    )
                    continue

            try:
                # Read slugs from file, supporting lines, spaces, or commas as delimiters
                with file_path.open("r") as f:
                    for line in f:
                        # Ignore comments (anything after #)
                        clean_line = line.split("#")[0].strip()
                        if not clean_line:
                            continue

                        # Treat commas as spaces, then split by whitespace
                        slugs = clean_line.replace(",", " ").split()
                        expanded.extend(slugs)
            except Exception as e:
                logger.error(f"Failed to read theme list file {file_path}: {e}")
        else:
            expanded.append(name)

    # Remove duplicates while preserving order
    unique_expanded = []
    seen = set()
    for item in expanded:
        if item not in seen:
            unique_expanded.append(item)
            seen.add(item)

    return unique_expanded


def _perform_migration_steps(theme_name: str, force_reset: bool, skip_maps: bool) -> bool:
    """Run the core migration steps, returning success status."""
    oem_handler = OEMFactory.detect_from_theme(theme_name)
    logger.info(f"Using {oem_handler} for {theme_name}")

    total_steps = 3 if skip_maps else 4
    from sbm.ui.console import get_console

    console = get_console()

    # Step 1: Create Site Builder files
    with console.status(f"Step 1/{total_steps}: Creating Site Builder files"):
        if not create_sb_files(theme_name, force_reset):
            logger.error(f"Failed to create Site Builder files for {theme_name}")
            return False
    console.print_success("Site Builder files created")

    # Step 2: Migrate styles
    with console.status(f"Step 2/{total_steps}: Migrating styles"):
        if not migrate_styles(theme_name):
            logger.error(f"Failed to migrate styles for {theme_name}")
            return False
    console.print_success("Styles migrated")

    # Step 3: Add predetermined styles
    with console.status(f"Step 3/{total_steps}: Adding predetermined styles"):
        if not add_predetermined_styles(theme_name):
            logger.error(f"Failed to add predetermined styles for {theme_name}")
            return False
    console.print_success("Predetermined styles added")

    # Step 4: Migrate map components if not skipped
    if not skip_maps:
        with console.status(f"Step 4/{total_steps}: Migrating map components"):
            if not migrate_map_components(theme_name, oem_handler):
                logger.error(f"Failed to migrate map components for {theme_name}")
                return False
        console.print_success("Map components migrated")
    else:
        logger.debug(f"Skipping map components migration for {theme_name}")

    return True


@cli.command()
@click.argument("theme_names", nargs=-1, required=True)
@click.option("--force-reset", is_flag=True, help="Force reset of existing Site Builder files.")
@click.option("--skip-maps", is_flag=True, help="Skip map components migration.")
@click.pass_context
def migrate(
    ctx: click.Context, theme_names: tuple[str, ...], force_reset: bool, skip_maps: bool
) -> None:
    """Migrate one or more dealer theme SCSS files to Site Builder format."""
    expanded_themes = _expand_theme_names(theme_names)
    if not expanded_themes:
        logger.error("No valid theme names provided.")
        sys.exit(1)

    config = ctx.obj.get("config", Config({}))
    from sbm.ui.console import get_console

    console = get_console(config)

    for theme_name in expanded_themes:
        console.print_migration_header(theme_name)

        if not _perform_migration_steps(theme_name, force_reset, skip_maps):
            logger.error(f"Migration failed for {theme_name}. Skipping...")
            continue

        _create_automation_snapshots(theme_name)
        console.print_manual_review_prompt(
            theme_name, ["sb-inside.scss", "sb-vdp.scss", "sb-vrp.scss", "sb-home.scss"]
        )

        if not click.confirm(f"Continue with migration of {theme_name}?"):
            continue

        if not reprocess_manual_changes(theme_name):
            continue

        _cleanup_snapshot_files(theme_name)

        try:
            record_migration(theme_name)
            record_run(
                slug=theme_name,
                command="migrate",
                status="success",
                duration=0,
                automation_time=0,
                lines_migrated=0,
            )
            sync_global_stats()
            # Show updated stats after each migration
            ctx.invoke(stats)
        except Exception as e:
            logger.warning(f"Could not update stats for {theme_name}: {e}")


@cli.command()
@click.argument("theme_names", nargs=-1, required=True)
@click.option("--yes", "-y", is_flag=True, help="Auto-confirm all prompts.")
@click.option("--skip-just", is_flag=True, help="Skip running the 'just start' command.")
@click.option("--force-reset", is_flag=True, help="Force reset of existing Site Builder files.")
@click.option("--create-pr/--no-create-pr", default=True, help="Create a GitHub PR.")
@click.option("--skip-post-migration", is_flag=True, help="Skip manual review/PR phase.")
@click.option("--verbose-docker", is_flag=True, help="Show verbose Docker output.")
@click.pass_context
def auto(
    ctx: click.Context,
    theme_names: tuple[str, ...],
    yes: bool,
    skip_just: bool,
    force_reset: bool,
    create_pr: bool,
    skip_post_migration: bool,
    verbose_docker: bool,
) -> None:
    """Run the full automated migration for one or more themes."""
    from sbm.config import get_settings

    expanded_themes = _expand_theme_names(theme_names)
    if not expanded_themes:
        sys.exit(1)

    if len(expanded_themes) > 1:
        yes = True
        skip_post_migration = True

    if yes:
        get_settings().non_interactive = True

    config = ctx.obj.get("config", Config({}))
    console = get_console(config)

    for theme_name in expanded_themes:
        config_dict = {
            "skip_just": skip_just,
            "force_reset": force_reset,
            "create_pr": create_pr,
            "skip_post_migration": skip_post_migration,
        }

        if not skip_post_migration:
            if not InteractivePrompts.confirm_migration_start(theme_name, config_dict):
                continue

        console.print_header("SBM Migration", f"Starting {theme_name}")
        from .utils.timer import (
            init_timing_summary,
            patch_click_confirm_for_timing,
            restore_click_confirm,
            print_timing_summary,
            clear_timing_summary,
        )

        init_timing_summary(theme_name)
        original_confirm = patch_click_confirm_for_timing()

        try:
            success, pr_url = migrate_dealer_theme(
                theme_name,
                skip_just=skip_just,
                force_reset=force_reset,
                create_pr=create_pr,
                interactive_review=not skip_post_migration,
                interactive_git=not skip_post_migration,
                interactive_pr=not skip_post_migration,
                verbose_docker=verbose_docker,
            )

            if success:
                record_migration(theme_name)
                record_run(
                    slug=theme_name,
                    command="auto",
                    status="success",
                    duration=get_total_duration(),
                    automation_time=get_total_automation_time(),
                    lines_migrated=0,
                )
                sync_global_stats()
                # Show updated stats after each migration
                ctx.invoke(stats)
                console.print_migration_complete(
                    theme_name, elapsed_time=get_total_duration(), files_processed=4, pr_url=pr_url
                )
            else:
                console.print_error(f"Migration failed for {theme_name}")

        except Exception as e:
            console.print_error(f"Error migrating {theme_name}: {e}")
        finally:
            if original_confirm:
                restore_click_confirm(original_confirm)
            print_timing_summary()
            clear_timing_summary()


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
@click.option(
    "--list",
    "show_list",
    is_flag=True,
    help="Show the list of migrated slugs in addition to the total count.",
)
@click.option(
    "--history",
    is_flag=True,
    help="Show the history of recent migration runs.",
)
@click.pass_context
def stats(ctx: click.Context, show_list: bool, history: bool) -> None:
    """Show migration tracker stats (total count and optional slug list)."""
    stats_data = get_migration_stats()
    config = ctx.obj.get("config", Config({}))
    console = get_console(config)
    rich_console = console.console

    # Imports for stats display
    from rich.columns import Columns
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    # Header Panel
    header = Panel(
        Text.from_markup(f"[bold cyan]Global Auto-SBM Stats[/bold cyan]"),
        border_style="bright_blue",
    )
    rich_console.print(header)

    # Personal Impact
    current_user = stats_data.get("user_id", "unknown")
    rich_console.print(
        Text.assemble(
            Text("Auto-SBM Stats: ", style="bold cyan"),
            Text(f"{current_user}", style="bold purple"),
        )
    )

    # Metrics Grid
    metrics_local = stats_data.get("metrics", {})

    def make_metric_panel(label: str, value: str, color: str) -> Panel:
        return Panel(
            Text.from_markup(f"[bold {color}]{value}[/bold {color}]\n[dim]{label}[/dim]"),
            expand=True,
            border_style=color,
        )

    metric_panels = [
        make_metric_panel("Sites Migrated", str(stats_data["count"]), "green"),
        make_metric_panel(
            "Lines Migrated",
            f"{metrics_local.get('total_lines_migrated', 0):,}",
            "cyan",
        ),
        make_metric_panel(
            "Time Saved",
            f"{metrics_local.get('total_time_saved_h', 0)}h",
            "yellow",
        ),
    ]

    rich_console.print(Columns(metric_panels, equal=True))

    # Global Team Impact
    global_metrics = stats_data.get("global_metrics", {})
    if global_metrics:
        rich_console.print("\n[bold cyan]Global Auto-SBM Stats[/bold cyan]")

        global_panels = [
            make_metric_panel("Total Users", str(global_metrics.get("total_users", 0)), "blue"),
            make_metric_panel(
                "Sites Migrated",
                str(global_metrics.get("total_migrations", 0)),
                "green",
            ),
            make_metric_panel(
                "Lines Migrated",
                f"{global_metrics.get('total_lines_migrated', 0):,}",
                "cyan",
            ),
            make_metric_panel(
                "Team Time Saved",
                f"{global_metrics.get('total_time_saved_h', 0)}h",
                "yellow",
            ),
        ]
        rich_console.print(Columns(global_panels, equal=True))

        # Top Contributors
        top_contributors = global_metrics.get("top_contributors", [])
        if top_contributors:
            rich_console.print("\n[bold cyan]Top Contributors:[/bold cyan]")
            contrib_table = Table(show_header=False, box=None, padding=(0, 2))
            contrib_table.add_column("Rank", style="dim", width=4)
            contrib_table.add_column("User", style="bold cyan")
            contrib_table.add_column("Migrations", style="green")

            for i, (user, count) in enumerate(top_contributors, 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"#{i}"
                contrib_table.add_row(f"  {medal}", f"{user}", f"{count} sites")
            rich_console.print(contrib_table)

    # User ID info
    current_user = stats_data.get("user_id", "unknown")

    last_updated_str = "Never"
    if stats_data.get("last_updated"):
        # Simple robust formatting for YYYY-MM-DD HH:MM:SS
        ts = stats_data["last_updated"]
        if len(ts) >= 19:
            last_updated_str = ts[:19].replace("T", " ")
        else:
            last_updated_str = ts

    rich_console.print(
        f"\n[dim]Contributing as: {current_user} | Last updated: {last_updated_str}[/dim]"
    )

    if history:
        runs = stats_data.get("runs", [])
        if runs:
            table = Table(
                title="Recent Migration Runs",
                title_style="bold cyan",
                show_header=True,
                header_style="bold magenta",
            )
            table.add_column("Timestamp", style="dim")
            table.add_column("Theme Slug", style="cyan")
            table.add_column("Command", style="green")
            table.add_column("Status", style="bold")
            table.add_column("Time", justify="right")

            for run in reversed(runs[-10:]):  # Show last 10
                status = run.get("status", "unknown")
                status_color = "green" if status == "success" else "red"

                table.add_row(
                    run.get("timestamp", "")[:19].replace("T", " "),
                    run.get("slug", "unknown"),
                    run.get("command", "unknown"),
                    f"[{status_color}]{status}[/{status_color}]",
                )
            rich_console.print(table)
        else:
            rich_console.print("[yellow]No run history found.[/yellow]")

    if show_list:
        migrations = stats_data.get("migrations", [])
        if migrations:
            table = Table(title="Migrated Theme Slugs", title_style="bold cyan")
            table.add_column("Slug", style="cyan")
            for slug in migrations:
                table.add_row(slug)
            rich_console.print(table)
        else:
            rich_console.print("[yellow]No migrations have been recorded yet.[/yellow]")


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
    skip_pr_prompt: bool,
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
    publish: bool,
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
            ["git", "stash", "push", "-m", "Manual SBM update stash"], cwd=REPO_ROOT, check=True
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
    subprocess.run(
        ["git", "stash", "pop"], cwd=REPO_ROOT, check=True, capture_output=True, text=True
    )


@cli.command()
def update() -> None:
    """Update auto-sbm to the latest version."""
    click.echo("🔄 Updating auto-sbm...")

    try:
        _validate_git_repository()
        current_branch = _get_current_branch()

        # Get current commit for comparison
        current_commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        ).stdout.strip()[:7]

        has_changes = _stash_changes_if_needed()

        # Perform git pull
        click.echo(f"📥 Pulling latest changes from origin/{current_branch}...")
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
                # Get new commit
                new_commit = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    check=True,
                    cwd=REPO_ROOT,
                    capture_output=True,
                    text=True,
                ).stdout.strip()[:7]

                # Show what changed
                click.echo(f"✅ Updated: {current_commit} → {new_commit}")

                # Show recent commits
                log_result = subprocess.run(
                    ["git", "log", f"{current_commit}..{new_commit}", "--oneline", "--no-decorate"],
                    check=True,
                    cwd=REPO_ROOT,
                    capture_output=True,
                    text=True,
                )
                if log_result.stdout.strip():
                    click.echo("\n📝 Changes:")
                    for line in log_result.stdout.strip().split("\n")[:5]:  # Show max 5 commits
                        click.echo(f"  • {line}")

                # Update dependencies
                click.echo("\n📦 Updating dependencies...")
                _update_dependencies()
                click.echo("✅ Dependencies updated")

            # Restore stashed changes
            if has_changes:
                _restore_stashed_changes()

            click.echo("\n✅ Update complete! Run 'sbm version' to verify.")
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
def test_compilation(theme_name: str, no_cleanup: bool, max_iterations: int, timeout: int) -> None:
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


def _report_test_results(theme_name: str, num_files: int, total_time: float, success: bool) -> None:
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

        success_count = sum((css_dir / f.replace(".scss", ".css")).exists() for f, _ in test_files)
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
        success_count = sum((css_dir / f.replace(".scss", ".css")).exists() for f, _ in test_files)
        if success_count == len(test_files):
            click.echo("✅ Compilation successful after commenting out problematic code")
            return True
    return False


def _comment_out_problematic_code_for_test(test_files: list[tuple[str, Path]]) -> None:
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
@click.option("--changelog", "-c", is_flag=True, help="Show recent changelog entries")
def version(changelog: bool) -> None:
    """Display version information."""
    console = get_console()
    current_version = get_version()

    console.print_header(
        title=f"auto-sbm v{current_version}", subtitle="Site Builder Migration Tool"
    )

    if changelog:
        console.console.print("\n[bold cyan]📝 Recent Changes:[/]")
        console.console.print("-" * 40)
        console.console.print(get_changelog())


@cli.command()
def doctor() -> None:
    """
    Validate auto-sbm installation and diagnose common issues.

    This command checks that all dependencies are available and the
    environment is properly configured for running migrations.
    """
    console = get_console()

    console.console.print("\n🔍 Auto-SBM Environment Diagnosis", style="bold blue")
    console.console.print("=" * 50)

    # Check critical modules
    required_modules = [
        ("pydantic", "Data validation"),
        ("pytest", "Testing framework"),
        ("click", "CLI framework"),
        ("rich", "Terminal UI"),
        ("git", "Git operations"),
        ("jinja2", "Template processing"),
        ("yaml", "YAML processing"),
        ("requests", "HTTP requests"),
        ("psutil", "System monitoring"),
    ]

    missing_modules = []
    for module, description in required_modules:
        try:
            __import__(module)
            console.console.print(f"✅ {module:<12} - {description}")
        except ImportError:
            console.console.print(f"❌ {module:<12} - {description} [red](MISSING)[/red]")
            missing_modules.append(module)

    # Check virtual environment
    console.console.print("\n📁 Environment Information:")
    console.console.print(f"   Python: {sys.executable}")
    console.console.print(
        f"   Version: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    )
    console.console.print(f"   Project root: {REPO_ROOT}")

    # Check setup marker
    if SETUP_MARKER.exists():
        console.console.print("✅ Setup completed successfully")
    else:
        console.console.print("⚠️  Setup marker missing - run setup.sh")

    # Check git configuration
    try:
        repo = Repo(REPO_ROOT)
        console.console.print(f"✅ Git repository: {repo.active_branch.name}")
    except Exception as e:
        console.console.print(f"❌ Git issue: {e}")

    # Check GitHub CLI
    if shutil.which("gh"):
        try:
            result = subprocess.run(
                ["gh", "auth", "status"], check=False, capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                console.console.print("✅ GitHub CLI authenticated")
            else:
                console.console.print("⚠️  GitHub CLI not authenticated")
        except Exception:
            console.console.print("⚠️  GitHub CLI auth check failed")
    else:
        console.console.print("❌ GitHub CLI not found")

    # Summary and recommendations
    console.console.print("\n📊 Summary:")
    if missing_modules:
        console.console.print(
            f"❌ {len(missing_modules)} missing dependencies: {', '.join(missing_modules)}"
        )
        console.console.print("\n🔧 Recommended fix:")
        console.console.print(f"   cd {REPO_ROOT}")
        console.console.print("   bash setup.sh")
        click.echo("\nEnvironment needs attention.")
        sys.exit(1)
    else:
        console.console.print("✅ All critical dependencies available!")
        console.console.print("✅ Environment looks healthy!")
        click.echo("\nEnvironment is ready for migrations.")


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


@cli.command(hidden=True)
def internal_refresh_stats() -> None:
    """
    Internal command used for background stats refresh.
    Runs the backfill script and then syncs global stats.
    """
    try:
        # Sync global stats (git push)
        from .utils.tracker import sync_global_stats

        sync_global_stats()
    except Exception as e:
        logger.debug(f"Internal stats refresh failed: {e}")


if __name__ == "__main__":
    cli()
