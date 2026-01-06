"""
Core migration functionality for the SBM tool.

This module handles the main migration logic for dealer themes.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Dict, Any

import click
from rich.prompt import Confirm

from sbm.oem.factory import OEMFactory
from sbm.oem.stellantis import StellantisHandler
from sbm.scss.processor import SCSSProcessor
from sbm.ui.console import get_console
from sbm.utils.command import execute_command, execute_interactive_command
from sbm.utils.logger import logger
from sbm.utils.path import get_dealer_theme_dir, get_platform_dir
from sbm.utils.timer import timer_segment

from .git import commit_changes, git_operations, push_changes
from .git import create_pr as git_create_pr
from .maps import migrate_map_components

if TYPE_CHECKING:
    from sbm.ui.console import SBMConsole


def _cleanup_exclusion_comments(slug: str) -> None:
    """
    Remove any existing EXCLUDED RULE comments from SCSS files to prevent compilation errors.
    Args:
        slug: Dealer theme slug
    """
    try:
        theme_dir = Path(get_dealer_theme_dir(slug))
        scss_files = ["sb-inside.scss", "sb-vdp.scss", "sb-vrp.scss", "sb-home.scss"]

        total_cleaned = 0
        for scss_file in scss_files:
            file_path = theme_dir / scss_file
            if file_path.exists():
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                if "/* EXCLUDED RULE" in content:
                    new_content = re.sub(r"/\* EXCLUDED RULE.*?\*/", "", content, flags=re.DOTALL)
                    file_path.write_text(new_content, encoding="utf-8")
                    total_cleaned += 1

        if total_cleaned > 0:
            logger.info(f"Cleaned {total_cleaned} exclusion comments from {slug}")
    except Exception as e:
        logger.error(f"Error cleaning up exclusion comments for {slug}: {e}")


def _cleanup_snapshot_files(slug: str) -> None:
    """
    Remove any .sbm-snapshots directories and files before committing.

    Args:
        slug (str): Dealer theme slug
    """
    try:
        theme_dir = Path(get_dealer_theme_dir(slug))
        snapshot_dir = theme_dir / ".sbm-snapshots"

        if snapshot_dir.exists():
            shutil.rmtree(snapshot_dir)
            logger.debug(f"Cleaned up snapshot directory: {snapshot_dir}")
        else:
            logger.debug(f"No snapshot directory found at: {snapshot_dir}")

        # Also clean up any individual .automated files that might exist
        automated_files = list(theme_dir.rglob("*.automated"))
        for file_path in automated_files:
            try:
                file_path.unlink()
                logger.info(f"Removed automated file: {file_path}")
            except Exception as e:
                logger.warning(f"Could not remove automated file {file_path}: {e}")

    except Exception as e:
        logger.warning(f"Could not clean up snapshot files: {e}")


def _create_automation_snapshots(slug: str) -> None:
    """
    Create snapshots of the automated migration output for comparison with manual changes.

    Args:
        slug (str): Dealer theme slug
    """
    try:
        theme_dir = Path(get_dealer_theme_dir(slug))
        snapshot_dir = theme_dir / ".sbm-snapshots"

        # Create snapshot directory
        snapshot_dir.mkdir(parents=True, exist_ok=True)

        # List of Site Builder files to snapshot
        sb_files = ["sb-inside.scss", "sb-vdp.scss", "sb-vrp.scss", "sb-home.scss"]

        snapshots_created = 0
        for sb_file in sb_files:
            source_path = theme_dir / sb_file
            if source_path.exists():
                snapshot_path = snapshot_dir / f"{sb_file}.automated"

                # Copy the automated output to snapshot
                snapshot_path.write_text(
                    source_path.read_text(encoding="utf-8", errors="ignore"),
                    encoding="utf-8",
                )

                snapshots_created += 1
                logger.debug(f"Created snapshot: {snapshot_path}")

        if snapshots_created > 0:
            logger.debug(f"Created automation snapshot for {slug}")
        else:
            logger.debug(f"No Site Builder files found to snapshot for {slug}")

    except Exception as e:
        logger.warning(f"Could not create automation snapshots: {e}")


def _process_aws_output(output_line: str, console: SBMConsole) -> None:
    """
    Process AWS authentication output and provide meaningful status updates.

    Args:
        output_line: Single line of AWS output
        console: SBMConsole instance for styled output
    """
    line = output_line.strip().lower()

    # Map AWS SAML output patterns to user-friendly messages
    if "please authenticate" in line:
        console.print_aws_status("Opening browser for SAML authentication...")

    elif "authentication successful" in line or "login successful" in line:
        console.print_aws_status("SAML authentication successful")

    elif "retrieving" in line and "token" in line:
        console.print_aws_status("Retrieving AWS session tokens...")

    elif "assuming role" in line:
        console.print_aws_status("Assuming AWS role...")

    elif "credentials saved" in line or "profile updated" in line:
        console.print_aws_status("AWS credentials configured")

    elif "error" in line or "failed" in line:
        logger.warning(f"⚠️ AWS warning: {output_line.strip()}")

    elif "timeout" in line or "expired" in line:
        console.print_aws_status("Authentication timeout - please retry")

    elif output_line.strip() and not any(
        skip in line for skip in ["debug", "verbose", "url:", "http"]
    ):
        # Log other significant AWS output
        logger.debug(f"AWS: {output_line.strip()}")


def _process_docker_output(output_line: str) -> None:
    """
    Process Docker output lines and provide meaningful progress updates.

    Args:
        output_line: Single line of Docker output
        progress_tracker: MigrationProgress instance for status updates
    """
    line = output_line.strip().lower()

    # Map common Docker output patterns to user-friendly messages
    if "pulling" in line and "image" in line:
        # Docker image pulling
        if "download" in line:
            return  # Skip individual download progress
        if "complete" in line or "pull complete" in line:
            return  # Skip completion messages for individual layers
        # Extract image name from pulling message
        parts = output_line.split()
        if len(parts) > 1:
            image = parts[1].replace(":", "")
            logger.info(f"📦 Pulling Docker image: {image}")

    elif "creating" in line and ("container" in line or "network" in line):
        logger.info("🐳 Creating Docker resources...")

    elif "starting" in line and ("container" in line or "service" in line):
        logger.info("🚀 Starting Docker containers...")

    elif "waiting" in line and ("healthy" in line or "ready" in line):
        logger.info("⏳ Waiting for services to become ready...")

    elif "ready" in line or "started" in line or "running" in line:
        logger.info("✅ Docker services are running")

    elif "error" in line or "failed" in line:
        logger.warning(f"⚠️ Docker warning: {output_line.strip()}")

    elif "listening on" in line or "server started" in line:
        logger.info("🌐 Web server is ready")

    elif output_line.strip() and not any(
        skip in line
        for skip in ["step", "sha256", "digest", "already exists", "layer already exists"]
    ):
        # Log other significant output
        logger.debug(f"Docker: {output_line.strip()}")


def run_just_start(
    slug: str, suppress_output: bool = False, console: SBMConsole | None = None
) -> bool:
    """
    Run the 'just start' command for the given slug (automatically chooses dev/prod database).
    Uses interactive execution to allow password prompts and user input.

    Args:
        slug: Dealer theme slug
        suppress_output: Whether to suppress verbose Docker output (default: False)
        console: Optional console instance for unified UI.

    Returns:
        bool: True if successful, False otherwise
    """
    logger.info(f"Starting site build for {slug}")

    # Verify the 'just' command is available
    success, _, _, _ = execute_command("which just", "'just' command not found")
    if not success:
        logger.error("Please install 'just' or ensure it's in your PATH.")
        return False

    platform_dir = get_platform_dir()

    # AWS authentication (simplified to avoid subprocess tracking issues)
    if console:
        console.print_warning("Ensuring AWS authentication before Docker startup...")
    else:
        logger.info("Ensuring AWS authentication before Docker startup...")

    aws_login_success = execute_interactive_command(
        "saml2aws login -a inventory-non-prod-423154430651-developer",
        "AWS login failed",
        cwd=platform_dir,
        suppress_output=False,  # Always show AWS login prompts
    )

    if not aws_login_success:
        if console:
            console.print_warning("AWS login failed - continuing anyway (Docker may fail)")
        else:
            logger.warning("AWS login failed - continuing anyway (Docker may fail)")
    elif console:
        console.print_info("AWS authentication completed")
    else:
        logger.info("AWS authentication completed")

    # Run the 'just start' command (let it choose dev/prod automatically)
    if suppress_output:
        logger.info(f"Running 'just start {slug}' with suppressed output...")
    else:
        logger.info(f"Running 'just start {slug}' interactively...")

    success = execute_interactive_command(
        f"just start {slug}",
        f"Failed to run 'just start {slug}'",
        cwd=platform_dir,
        suppress_output=suppress_output,
    )

    if success:
        logger.debug("'just start' command completed successfully.")
        return True

    if console:
        console.print_error("Docker startup failed!")
    else:
        logger.error("Docker startup failed!")

    logger.error("'just start' command failed.")
    logger.error("Common causes:")
    logger.error("  - AWS authentication expired")
    logger.error("  - Docker daemon not running")
    logger.error("  - Network connectivity issues")
    logger.error("  - Theme configuration problems")
    logger.error("Try running with --verbose-docker flag to see detailed output")
    return False


def _wait_for_gulp_idle(timeout: int = 20) -> None:
    """Wait for the Docker Gulp watcher to finish its current cycle."""
    try:
        cleanup_start = time.time()
        cleanup_sass_done = False
        cleanup_process_done = False

        while (time.time() - cleanup_start) < timeout:
            result = subprocess.run(
                ["docker", "logs", "--tail", "10", "dealerinspire_legacy_assets"],
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0 and result.stdout:
                recent_logs = result.stdout.lower()
                if "finished 'sass'" in recent_logs:
                    cleanup_sass_done = True
                if "finished 'processcss'" in recent_logs:
                    cleanup_process_done = True

                if cleanup_sass_done and cleanup_process_done:
                    logger.debug("Docker Gulp watcher is idle")
                    return

            time.sleep(1)

        logger.warning(f"Gulp idle wait timed out after {timeout} seconds")

    except Exception as e:
        logger.warning(f"Error waiting for Gulp idle: {e}")


def create_sb_files(slug: str, force_reset: bool = False) -> bool:
    """
    Create necessary Site Builder SCSS files if they don't exist.

    Args:
        slug: Dealer theme slug
        force_reset: Whether to reset existing files

    Returns:
        bool: True if successful, False otherwise
    """
    logger.info(f"Creating Site Builder files for {slug}")

    try:
        theme_dir = Path(get_dealer_theme_dir(slug))

        # List of Site Builder files to create
        sb_files = ["sb-inside.scss", "sb-vdp.scss", "sb-vrp.scss", "sb-home.scss"]

        for file in sb_files:
            file_path = theme_dir / file

            # Skip if file exists and we're not forcing reset
            if file_path.exists() and not force_reset:
                logger.info(f"File {file} already exists, skipping creation")
                continue

            # Create or reset the file
            file_path.write_text("", encoding="utf-8")

            logger.info(f"Created {file}")

        return True

    except Exception as e:
        logger.error(f"Error creating Site Builder files: {e}")
        return False


def migrate_styles(slug: str, processor: Optional[SCSSProcessor] = None) -> tuple[bool, int]:
    # 3. Processes main SCSS files (style.scss, inside.scss, etc.)
    # 4. Writes transformed files to target directory.
    logger.debug(f"Migrating styles for {slug} using new SASS-based SCSSProcessor")
    try:
        theme_dir = Path(get_dealer_theme_dir(slug))
        source_scss_dir = theme_dir / "css"

        if not source_scss_dir.is_dir():
            logger.error(f"Source SCSS directory not found: {source_scss_dir}")
            return False, 0

        if processor is None:
            processor = SCSSProcessor(slug, exclude_nav_styles=True)

        # Define source files for sb-inside
        inside_sources = [
            source_scss_dir / "style.scss",
            source_scss_dir / "inside.scss",
            source_scss_dir / "_support-requests.scss",
        ]
        # Only use lvdp.scss and lvrp.scss, not vdp.scss and vrp.scss
        vdp_sources = [source_scss_dir / "lvdp.scss"]
        vrp_sources = [source_scss_dir / "lvrp.scss"]

        # Process each category
        inside_content = "\n".join(
            [processor.process_scss_file(str(f)) for f in inside_sources if f.exists()]
        )
        vdp_content = "\n".join(
            [processor.process_scss_file(str(f)) for f in vdp_sources if f.exists()]
        )
        vrp_content = "\n".join(
            [processor.process_scss_file(str(f)) for f in vrp_sources if f.exists()]
        )

        # Combine results
        results = {
            "sb-inside.scss": inside_content,
            "sb-vdp.scss": vdp_content,
            "sb-vrp.scss": vrp_content,
        }

        # Write the resulting SCSS to files
        success = processor.write_files_atomically(str(theme_dir), results)

        if success:
            generated_files = []
            total_lines_processed = 0
            for filename, content in results.items():
                if content:
                    lines = len(content.splitlines())
                    total_lines_processed += lines
                    generated_files.append(f"{filename} ({lines} lines)")
            if generated_files:
                msg = (
                    f"Successfully reprocessed {total_lines_processed} lines. "
                    "SCSS files should compile now. Please start Docker for verification."
                )
                logger.info(msg)
            # Note: SCSS formatting is applied at the end of the full migration
            # after all content (predetermined styles, map components) is added
            return True, total_lines_processed
        else:
            logger.error("SCSS migration failed during file writing.")
            return False, 0

    except Exception as e:
        logger.error(f"Error migrating styles: {e}", exc_info=True)
        return False, 0


def _add_cookie_disclaimer_styles(theme_path: Path, oem_handler: object | None, slug: str) -> bool:
    """Add cookie disclaimer styles for Stellantis dealers."""
    if not isinstance(oem_handler, StellantisHandler):
        return True

    auto_sbm_dir = Path(__file__).parent.parent.parent
    source = auto_sbm_dir / "stellantis/add-to-sb-inside/stellantis-cookie-banner-styles.scss"
    if not source.exists():
        logger.warning(f"Cookie banner source not found: {source}")
        return False

    styles = source.read_text(encoding="utf-8", errors="ignore")

    # Process styles to remove imports and standardize variables
    try:
        from sbm.scss.processor import SCSSProcessor

        processor = SCSSProcessor(slug)
        styles = processor.transform_scss_content(styles)
    except Exception as e:
        logger.warning(f"Failed to process cookie banner styles: {e}")

    for sb_file in ["sb-inside.scss", "sb-home.scss"]:
        file_path = theme_path / sb_file
        if not file_path.exists():
            continue
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        if ".cookie-banner" not in content:
            with file_path.open("a", encoding="utf-8") as f:
                f.write("\n\n/* Cookie Banner Styles */\n" + styles)
            logger.info(f"Added cookie banner styles to {sb_file}")
    return True


def _add_directions_row_styles(theme_path: Path, oem_handler: object | None, slug: str) -> bool:
    """Add directions row styles from OEM handler."""
    if not oem_handler:
        return True

    # Get styles from handler
    try:
        styles = oem_handler.get_directions_styles()
    except (NotImplementedError, AttributeError):
        return True

    if not styles:
        return True

    # Process styles to remove imports and standardize variables
    try:
        from sbm.scss.processor import SCSSProcessor

        processor = SCSSProcessor(slug)
        styles = processor.transform_scss_content(styles)
    except Exception as e:
        logger.warning(f"Failed to process directions row styles: {e}")

    inside_path = theme_path / "sb-inside.scss"
    if inside_path.exists():
        content = inside_path.read_text(encoding="utf-8", errors="ignore")
        # Check for marker or class name to avoid duplicates
        if "/* Directions Row Styles */" not in content and ".directions-row" not in content:
            with inside_path.open("a", encoding="utf-8") as f:
                f.write("\n\n/* Directions Row Styles */\n" + styles)
            logger.info("Added directions row styles to sb-inside.scss")
    return True


def _add_map_styles(theme_path: Path, oem_handler: object | None, slug: str) -> bool:
    """Add map styles from OEM handler."""
    if not oem_handler:
        return True

    # Get styles from handler
    try:
        styles = oem_handler.get_map_styles()
    except (NotImplementedError, AttributeError):
        return True

    if not styles:
        return True

    # Process styles to remove imports and standardize variables
    try:
        from sbm.scss.processor import SCSSProcessor

        processor = SCSSProcessor(slug)
        styles = processor.transform_scss_content(styles)
    except Exception as e:
        logger.warning(f"Failed to process map styles: {e}")

    inside_path = theme_path / "sb-inside.scss"
    if inside_path.exists():
        content = inside_path.read_text(encoding="utf-8", errors="ignore")
        if "/* Map Styles */" not in content and "#mapRow" not in content:
            with inside_path.open("a", encoding="utf-8") as f:
                f.write("\n\n/* Map Styles */\n" + styles)
            logger.info("Added map styles to sb-inside.scss")
    return True


def add_predetermined_styles(slug: str, oem_handler: dict | object | None = None) -> bool:
    """
    Add predetermined styles for cookie disclaimer and directions row.

    Args:
        slug: Dealer theme slug
        oem_handler: OEM handler for the dealer
    """
    logger.info(f"Adding predetermined styles for {slug}")
    theme_path = Path(get_dealer_theme_dir(slug))

    # Use OEM factory to get handler if not provided
    if oem_handler is None:
        oem_handler = OEMFactory.detect_from_theme(slug)

    success = True
    if not _add_cookie_disclaimer_styles(theme_path, oem_handler, slug):
        success = False
    if not _add_directions_row_styles(theme_path, oem_handler, slug):
        success = False
    if not _add_map_styles(theme_path, oem_handler, slug):
        success = False
    return success


def test_compilation_recovery(slug: str) -> bool:
    """
    Test compilation error handling on an existing theme without doing migration.

    This function copies existing SCSS files to the CSS directory, monitors
    compilation, and tests the error recovery system without modifying
    the original theme files.

    Args:
        slug: Dealer theme slug

    Returns:
        bool: True if compilation succeeds or errors are handled, False otherwise
    """
    logger.info(f"Testing compilation error recovery for {slug}")

    try:
        theme_dir = Path(get_dealer_theme_dir(slug))
        css_dir = theme_dir / "css"

        if not css_dir.exists():
            logger.error(f"CSS directory not found: {css_dir}")
            return False

        # List of Site Builder files to test
        sb_files = ["sb-inside.scss", "sb-vdp.scss", "sb-vrp.scss", "sb-home.scss"]
        test_files = []

        # Copy existing SCSS files to CSS directory for testing
        for sb_file in sb_files:
            scss_path = theme_dir / sb_file
            if scss_path.exists():
                test_filename = f"test-{sb_file}"
                test_path = css_dir / test_filename

                # Copy file for testing
                shutil.copy2(scss_path, test_path)
                test_files.append((test_filename, str(scss_path)))
                logger.info(f"Copied {sb_file} to {test_filename} for testing")

        if not test_files:
            logger.warning("No SCSS files found to test")
            return False

        click.echo(f"\n🧪 Testing compilation error recovery on {len(test_files)} files")
        click.echo("Files will be copied to CSS directory to trigger Docker Gulp compilation...")

        # Test compilation with error recovery
        success, _, _ = _handle_compilation_with_error_recovery(
            str(css_dir), test_files, str(theme_dir), slug
        )

        # Clean up test files
        click.echo("\n🧹 Cleaning up test files...")
        _cleanup_compilation_test_files(str(css_dir), test_files)

        if success:
            click.echo("✅ Compilation test completed successfully")
            logger.info("Compilation error recovery test passed")
        else:
            click.echo("❌ Compilation test failed")
            logger.error("Compilation error recovery test failed")

        return success

    except Exception as e:
        logger.error(f"Error during compilation test: {e}")
        click.echo(f"❌ Test failed with error: {e}")
        return False


def reprocess_manual_changes(slug: str) -> bool:
    """
    Reprocess Site Builder SCSS files after manual review to ensure consistency.

    This function applies the same transformations as the initial migration
    to any manual changes made by the user, ensuring variables, mixins,
    and other SCSS patterns are properly processed.

    Args:
        slug: Dealer theme slug

    Returns:
        bool: True if reprocessing was successful, False otherwise
    """
    logger.debug(f"Reprocessing manual changes for {slug}")

    try:
        theme_dir = Path(get_dealer_theme_dir(slug))
        processor = SCSSProcessor(slug, exclude_nav_styles=True)

        # List of Site Builder files to reprocess
        sb_files = ["sb-inside.scss", "sb-vdp.scss", "sb-vrp.scss", "sb-home.scss"]

        changes_made = False
        processed_files = []

        for sb_file in sb_files:
            file_path = theme_dir / sb_file

            if file_path.exists():
                # Read the current manually-edited content
                original_content = file_path.read_text(encoding="utf-8", errors="ignore")

                # Skip if file is empty
                if not original_content.strip():
                    continue

                # Apply reprocess-specific transformation logic to existing content
                # This ensures all conversions (variables, paths, mixins, functions) are applied
                # while preserving manual edits and avoiding duplicate utility functions
                processed_content = processor.reprocess_scss_content(original_content)

                # Check if any changes were made
                if processed_content != original_content:
                    # Write the processed content back
                    file_path.write_text(processed_content, encoding="utf-8")

                    changes_made = True
                    processed_files.append(sb_file)

                    # Count lines for feedback
                    original_lines = len(original_content.splitlines())
                    processed_lines = len(processed_content.splitlines())
                    logger.info(
                        f"Light cleanup applied to {sb_file}: {original_lines} → {processed_lines} lines"
                    )
                else:
                    logger.info(f"No cleanup needed for {sb_file} - manual edits preserved")

        if changes_made:
            logger.info(
                f"Reprocessing completed for {slug}. Files updated: {', '.join(processed_files)}"
            )
        else:
            logger.info(f"No reprocessing needed for {slug} - all files already properly formatted")

        # Format all SCSS files with built-in formatter
        from sbm.scss.formatter import format_all_scss_files

        if format_all_scss_files(str(theme_dir)):
            logger.info("Applied SCSS formatting to all Site Builder files")
        else:
            logger.warning("SCSS formatting encountered issues")

        # Note: SCSS compilation verification moved to separate timer segment
        # to avoid including long sleep/user interaction time in reprocessing timer
        return True

    except Exception as e:
        logger.error(f"Error reprocessing manual changes for {slug}: {e}")
        return False


def run_post_migration_workflow(
    slug: str,
    branch_name: str | None,
    skip_git: bool = False,
    create_pr: bool = True,
    interactive_review: bool = True,
    interactive_git: bool = True,
    interactive_pr: bool = True,
    skip_reprocessing: bool = False,
    console: SBMConsole | None = None,
) -> tuple[bool, Optional[str]]:
    """
    Run the post-migration workflow including git operations and PR creation.

    Args:
        slug: Dealer theme slug
        branch_name: Git branch name
        skip_git: Whether to skip git operations
        create_pr: Whether to create a pull request
        _interactive_review: DEPRECATED
        _interactive_git: DEPRECATED
        _interactive_pr: DEPRECATED
        skip_reprocessing: Whether to skip reprocessing manual changes
        console: Optional console instance for unified UI

    Returns:
        bool: True if all steps are successful, False otherwise.
    """
    if console is None:
        console = get_console()

    logger.debug(f"Starting post-migration workflow for {slug} on branch {branch_name}")

    if not skip_reprocessing:
        with timer_segment("Reprocessing Manual Changes"):
            if not reprocess_manual_changes(slug):
                return False, None

        with timer_segment("SCSS Compilation Verification"):
            theme_dir = Path(get_dealer_theme_dir(slug))
            sb_files = ["sb-inside.scss", "sb-vdp.scss", "sb-vrp.scss", "sb-home.scss"]
            if not _verify_scss_compilation_with_docker(theme_dir, slug, sb_files, console=console):
                return False, None

    _cleanup_snapshot_files(slug)

    # Automated Git operations
    if not skip_git:
        with timer_segment("Git Operations"):
            if not commit_changes(slug):
                return False, None
            if not push_changes(branch_name):
                return False, None

    # Automated PR creation
    pr_url = None
    salesforce_message = None
    if create_pr:
        logger.info(f"Creating PR for {slug}...")
        pr_result = git_create_pr(slug, branch_name)

        # Handle dict return (new) or tuple return (legacy safety)
        if isinstance(pr_result, dict):
            success = pr_result.get("success", False)
            pr_url = pr_result.get("pr_url")
            salesforce_message = pr_result.get("salesforce_message")
        else:
            success, pr_url = pr_result

        if success:
            logger.debug(f"PR created: {pr_url}")
        else:
            logger.error(f"Failed to create PR for {slug}")
            return {"success": False, "pr_url": None, "salesforce_message": None}

    logger.info(f"Migration completed successfully for {slug}")

    return {"success": True, "pr_url": pr_url, "salesforce_message": salesforce_message}


def _perform_core_migration(
    slug: str, force_reset: bool, oem_handler: object | None, skip_maps: bool, console: SBMConsole
) -> tuple[bool, int]:
    """Run core transformation steps."""
    console.print_step("Creating Site Builder SCSS files")
    with timer_segment("Site Builder File Creation"):
        if not create_sb_files(slug, force_reset):
            return False, 0

    console.print_step("Migrating SCSS styles and transforming syntax")
    processor = SCSSProcessor(slug, exclude_nav_styles=True)
    lines_migrated = 0
    with timer_segment("SCSS Migration"):
        success, lines = migrate_styles(slug, processor=processor)
        if not success:
            return False, 0
        lines_migrated = lines

    _cleanup_exclusion_comments(slug)
    console.print_step("Adding predetermined OEM-specific styles")
    add_predetermined_styles(slug, oem_handler)

    if not skip_maps:
        console.print_step("Migrating map components")
        # Pass the same processor to map components migration to ensure consistent variable transformation
        if not migrate_map_components(
            slug, oem_handler, interactive=False, console=console, processor=processor
        ):
            return False, 0

    # Final formatting pass - format all SCSS files after all content has been added
    console.print_step("Formatting SCSS files")
    from sbm.scss.formatter import format_all_scss_files

    theme_dir = get_dealer_theme_dir(slug)
    if format_all_scss_files(theme_dir):
        logger.info("Applied SCSS formatting to all Site Builder files")
    else:
        logger.warning("SCSS formatting encountered issues")

    return True, lines_migrated


def migrate_dealer_theme(
    slug: str,
    skip_just: bool = False,
    force_reset: bool = False,
    skip_git: bool = False,
    skip_maps: bool = False,
    oem_handler: object | None = None,
    create_pr: bool = True,
    interactive_review: bool = True,
    interactive_git: bool = True,
    interactive_pr: bool = True,
    verbose_docker: bool = False,
    console: SBMConsole | None = None,
) -> Dict[str, Any]:
    """
    Migrate a dealer theme to the Site Builder platform.

    Args:
        slug: Dealer theme slug
        skip_just: Whether to skip the 'just start' command
        force_reset: Whether to reset existing Site Builder files
        skip_git: Whether to skip Git operations
        skip_maps: Whether to skip map components migration
        oem_handler: Manually specified OEM handler
        create_pr: Whether to create a GitHub Pull Request
        _interactive_review: DEPRECATED
        interactive_git: Whether to prompt for Git operations
        interactive_pr: Whether to prompt for PR creation
        _verbose_docker: Whether to show verbose Docker output
        console: Optional console instance for unified UI

    Returns:
        Dict[str, Any]: Dictionary with keys 'success' (bool), 'pr_url' (str), and 'salesforce_message' (str)
    """
    if console is None:
        console = get_console()

    logger.info(f"Starting migration for {slug}")

    if oem_handler is None:
        oem_handler = OEMFactory.detect_from_theme(slug)

    branch_name = None
    if not skip_git:
        console.print_step("Setting up Git branch and repository")
        with timer_segment("Git Operations"):
            success, branch_name = git_operations(slug)
        if not success:
            return {"success": False, "pr_url": None, "salesforce_message": None}

    if not skip_just:
        console.print_step("Starting Docker environment (just start)")
        with timer_segment("Docker Startup"):
            if not run_just_start(slug, suppress_output=False):
                return {"success": False, "pr_url": None, "salesforce_message": None}

    success, lines_migrated = _perform_core_migration(
        slug, force_reset, oem_handler, skip_maps, console
    )
    if not success:
        return {"success": False, "pr_url": None, "salesforce_message": None, "lines_migrated": 0}

    _create_automation_snapshots(slug)

    result = run_post_migration_workflow(
        slug,
        branch_name,
        skip_git=skip_git,
        create_pr=create_pr,
        interactive_review=interactive_review,
        interactive_git=interactive_git,
        interactive_pr=interactive_pr,
        console=console,
    )

    # Add lines_migrated to the result
    if isinstance(result, dict):
        result["lines_migrated"] = lines_migrated

    return result


def _prepare_test_scaffolding(
    theme_path: Path, css_dir: Path, sb_files: list[str]
) -> list[tuple[str, str]]:
    """Copy original source files to test files in the monitoring directory."""
    test_files = []
    for sb_file in sb_files:
        src_path = theme_path / sb_file
        if src_path.exists():
            test_filename = f"test-{sb_file}"
            dst_path = css_dir / test_filename
            try:
                shutil.copy2(src_path, dst_path)
                test_files.append((test_filename, str(dst_path)))
                logger.debug(f"Created test file: {test_filename}")
            except Exception as e:
                logger.warning(f"Could not create test file for {sb_file}: {e}")
    return test_files


def _cleanup_verification_artifacts(
    css_dir: Path, _test_files: list[tuple[str, str]], skip_git_checkout: bool, theme_path: Path
) -> None:
    """Remove test files and generated CSS, optionally resetting git state."""
    logger.debug("Cleaning up verification artifacts...")
    for test_filename, _ in _test_files:
        try:
            (css_dir / test_filename).unlink(missing_ok=True)
            css_filename = test_filename.replace(".scss", ".css")
            (css_dir / css_filename).unlink(missing_ok=True)
        except Exception as e:
            logger.warning(f"Error removing test file {test_filename}: {e}")

    time.sleep(1)
    _wait_for_gulp_idle(timeout=10)

    if not skip_git_checkout:
        try:
            subprocess.run(
                ["git", "checkout", "HEAD", "css/"],
                cwd=str(theme_path),
                check=False,
                capture_output=True,
            )
        except Exception as e:
            logger.warning(f"Failed to reset CSS directory: {e}")


def _verify_scss_compilation_with_docker(
    theme_dir: str | Path,
    slug: str,
    sb_files: list[str],
    skip_git_checkout: bool = False,
    console: SBMConsole | None = None,
) -> bool:
    """
    Verify SCSS compilation by copying files to CSS directory and monitoring Docker logs.

    Args:
        theme_dir: Path to dealer theme directory
        slug: Dealer theme slug
        sb_files: List of Site Builder SCSS files to verify
        skip_git_checkout: Whether to skip resetting git state
        console: Optional console instance for unified UI

    Returns:
        bool: True if all files compile successfully, False otherwise
    """
    theme_path = Path(theme_dir)
    css_dir = theme_path / "css"
    manual_fix_attempted = False

    while True:
        logger.info(f"Testing SCSS compilation for {slug}...")
        test_files = _prepare_test_scaffolding(theme_path, css_dir, sb_files)

        if not test_files:
            logger.warning("No Site Builder files found to test")
            return True

        # Wait for compilation to trigger
        _wait_for_gulp_idle(timeout=20)

        # Handle compilation and interactive recovery
        success, recovery_manual, rerun_requested = _handle_compilation_with_error_recovery(
            css_dir, test_files, theme_path, slug, console=console
        )

        manual_fix_attempted = manual_fix_attempted or recovery_manual

        if rerun_requested:
            logger.info("Manual fixes applied. Restarting verification cycle...")
            _cleanup_verification_artifacts(css_dir, test_files, True, theme_path)
            continue

        _cleanup_verification_artifacts(
            css_dir, test_files, skip_git_checkout or manual_fix_attempted, theme_path
        )
        return success


def _extract_error_details_from_logs(logs: str) -> tuple[str | None, int | None, str | None]:
    """
    Extract error file, line, and message from Docker logs.

    Args:
        logs: Docker log output

    Returns:
        tuple: (error_file, error_line, error_message)
    """
    error_file = None
    error_line = None
    error_message = None

    for line in logs.split("\n"):
        # Look for error message lines
        if "Error:" in line and any(
            keyword in line.lower() for keyword in ["invalid", "undefined", "expected", "syntax"]
        ):
            error_message = line.strip()
        # Look for "on line X of file" patterns
        elif "on line" in line and "test-sb-" in line:
            # Parse: "on line 40 of ../DealerInspireDealerTheme/css/test-sb-inside.scss"
            match = re.search(r"on line (\d+) of [^/]*/(test-sb-[^/]+\.scss)", line)
            if match:
                error_line = int(match.group(1))
                test_file = match.group(2)
                # Convert test-sb-inside.scss -> sb-inside.scss
                error_file = test_file.replace("test-", "")
                break

    return error_file, error_line, error_message


def _prompt_user_for_manual_fix(
    logs: str,
    theme_path: Path,
    test_files: list[tuple[str, str]],
    console: SBMConsole | None = None,
) -> bool:
    """
    Prompt the user to manually fix compilation errors.

    Args:
        logs: Docker log output
        theme_path: Path to theme directory
        test_files: List of test files
        console: Optional console instance
    Returns:
        bool: True if user wants to continue after fixing
    """
    error_file, error_line, error_message = _extract_error_details_from_logs(logs)

    if console:
        console.print_error("❌ SCSS Compilation Error")
    else:
        click.echo("\n❌ SCSS Compilation Error")
        click.echo("=" * 50)

    if error_file and error_line:
        if console:
            console.print_error(f"Error: {error_message}")
            console.print_error(f"File: {error_file}")
            console.print_error(f"Line: {error_line}")
            console.print_info(f"Opening {error_file} for editing...")
        else:
            click.echo(f"Error: {error_message}")
            click.echo(f"File: {error_file}")
            click.echo(f"Line: {error_line}")
            click.echo()
            click.echo(f"Opening {error_file} for editing...")

        try:
            subprocess.run(["open", str(theme_path / error_file)], check=False)
        except Exception as e:
            logger.warning(f"Could not open file: {e}")
            if console:
                console.print_warning(f"Please manually open: {theme_path / error_file}")
            else:
                click.echo(f"Please manually open: {theme_path / error_file}")
    else:
        # Fallback to raw error display
        if error_message:
            if console:
                console.print_error(f"Error: {error_message}")
            else:
                click.echo(f"Error: {error_message}")
        else:
            # Show generic error info
            error_lines = [
                line for line in logs.split("\n") if "error" in line.lower() and line.strip()
            ]
            if error_lines:
                if console:
                    console.print_error("Recent errors from Gulp:")
                    for line in error_lines[-3:]:
                        console.print_info(f"  {line.strip()}")
                else:
                    click.echo("Recent errors from Gulp:")
                    for line in error_lines[-3:]:
                        click.echo(f"  {line.strip()}")

        if console:
            console.print_info(f"Please check these files in: {theme_path}")
            for test_filename, _ in test_files:
                original_file = test_filename.replace("test-", "")
                console.print_info(f"  - {original_file}")
        else:
            click.echo(f"Please check these files in: {theme_path}")
            for test_filename, _ in test_files:
                original_file = test_filename.replace("test-", "")
                click.echo(f"  - {original_file}")

    return Confirm.ask("Continue after fixing the errors?", default=True)


def _handle_migration_restart(
    slug: str,
    css_path_dir: Path,
    theme_path: Path,
    test_files: list[tuple[str, str]],
) -> bool:
    """
    Clean up and restart the migration pipeline after manual fixes.

    Args:
        slug: Dealer theme slug
        css_path_dir: CSS directory path
        theme_path: Theme directory path
        test_files: List of test files

    Returns:
        bool: True if restart was successful
    """
    # Clean up existing test files and CSS outputs
    # Identical cleaning of existing test files to ensure clean state
    for test_filename, _ in test_files:
        test_file_path = css_path_dir / test_filename
        if test_file_path.exists():
            test_file_path.unlink()

        css_filename = test_filename.replace(".scss", ".css")
        css_path = css_path_dir / css_filename
        if css_path.exists():
            css_path.unlink()

    logger.debug("Waiting for Gulp and Docker to settle...")
    time.sleep(2)
    _wait_for_gulp_idle(timeout=20)

    # Note: We purposefully do NOT reset the site builder files here.
    # The user has just manually edited them to fix errors.
    # Wiping them now would lose the user's changes.

    add_predetermined_styles(slug)
    reprocess_manual_changes(slug)
    _create_automation_snapshots(slug)

    return True


def _handle_compilation_with_error_recovery(
    css_dir: str | Path,
    test_files: list[tuple[str, str]],
    theme_dir: str | Path,
    slug: str,
    console: SBMConsole | None = None,
) -> tuple[bool, bool, bool]:
    """
    Handle SCSS compilation with comprehensive error recovery and iterative fixing.

    Args:
        css_dir: Path to CSS directory
        test_files: List of (test_filename, scss_path) tuples
        theme_dir: Path to dealer theme directory
        slug: Dealer theme slug
        console: Optional console instance for unified UI

    Returns:
        tuple[bool, bool, bool]: (compilation_success, manual_fix_attempted, rerun_requested)
    """
    max_iterations = 5
    iteration = 0
    manual_fix_attempted = False
    css_path_dir = Path(css_dir)
    theme_path = Path(theme_dir)

    # Capture start time for log filtering - REMOVED, using marker-based filtering instead
    # start_time = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    while iteration < max_iterations:
        iteration += 1
        logger.debug(f"🔄 Compilation attempt {iteration}/{max_iterations}")
        time.sleep(1)

        try:
            # Get substantial tail of logs to ensure we capture the start of the process
            result = subprocess.run(
                ["docker", "logs", "--tail", "200", "dealerinspire_legacy_assets"],
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0 and result.stdout:
                logs = result.stdout
                lower_logs = logs.lower()

                # Filter logs to only include the current compilation cycle
                # We look for the LAST occurrence of "starting 'sass'" to assume that's the current run
                start_marker = "starting 'sass'..."
                last_start_idx = lower_logs.rfind(start_marker)

                if last_start_idx != -1:
                    # Keep logs from the start of the compilation, plus a bit of context if needed
                    # effectively slicing the string
                    relevant_logs = logs[last_start_idx:]
                    relevant_lower_logs = lower_logs[last_start_idx:]
                else:
                    # Fallback: use all logs if we can't find the start marker (might have scrolled off)
                    relevant_logs = logs
                    relevant_lower_logs = lower_logs

                if (
                    "finished 'sass'" in relevant_lower_logs
                    and "finished 'processcss'" in relevant_lower_logs
                ):
                    # Robust error detection (case-insensitive)
                    if not any(
                        err in relevant_lower_logs
                        for err in ["error:", "gulp-notify: [error running gulp]"]
                    ):
                        logger.info("✅ Compilation completed successfully")
                        return True, manual_fix_attempted, False

                errors_found = _parse_compilation_errors(relevant_logs)
                if errors_found:
                    fixes_applied = 0
                    for error_info in errors_found:
                        if _attempt_error_fix(error_info, str(css_path_dir), str(theme_path)):
                            fixes_applied += 1

                    if fixes_applied > 0:
                        msg = f"🔧 Applied {fixes_applied} automated SCSS fixes"
                        if console:
                            console.print_info(msg)
                            console.print_info("Retrying compilation...")
                        else:
                            click.echo(f"\n{msg}\nRetrying compilation...")
                        continue
                    break
        except Exception as e:
            logger.warning(f"Error checking logs: {e}")

        success_count = sum(
            1 for f, _ in test_files if (css_path_dir / f.replace(".scss", ".css")).exists()
        )
        if success_count == len(test_files):
            return True, manual_fix_attempted, False

    # Handle final failure and manual fix
    try:
        result = subprocess.run(
            ["docker", "logs", "--tail", "100", "dealerinspire_legacy_assets"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        logs = result.stdout if result.returncode == 0 else ""

        # Apply same filtering logic for manual fix prompt
        lower_logs = logs.lower()
        start_marker = "starting 'sass'..."
        last_start_idx = lower_logs.rfind(start_marker)
        if last_start_idx != -1:
            logs = logs[last_start_idx:]

        if _prompt_user_for_manual_fix(logs, theme_path, test_files, console):
            manual_fix_attempted = True
            if _handle_migration_restart(slug, css_path_dir, theme_path, test_files):
                return False, manual_fix_attempted, True

    except Exception as e:
        logger.warning(f"Error in failure recovery: {e}")

    return False, manual_fix_attempted, False


def _parse_compilation_errors(logs: str) -> list[dict]:
    """
    Parse Docker Gulp logs to extract specific compilation error information.

    Args:
        logs: Docker Gulp log output

    Returns:
        list: List of error dictionaries with file, line, and error details
    """
    errors = []

    # Common SCSS error patterns
    error_patterns = [
        {"pattern": r"error.*?([^/\s]+\.s?css):(\d+):(\d+):?\s*(.+)", "type": "syntax_error"},
        {
            "pattern": r"undefined variable.*?\$([a-zA-Z_][a-zA-Z0-9_-]*)",
            "type": "undefined_variable",
        },
        {"pattern": r"undefined mixin.*?([a-zA-Z_][a-zA-Z0-9_-]*)", "type": "undefined_mixin"},
        {"pattern": r'invalid css.*?after.*?"([^"]*)"', "type": "invalid_css"},
    ]

    lines = logs.split("\n")

    for line in lines:
        for pattern_info in error_patterns:
            match = re.search(pattern_info["pattern"], line, re.IGNORECASE)
            if match:
                error = {
                    "type": pattern_info["type"],
                    "line_content": line.strip(),
                    "match_groups": match.groups(),
                    "original_line": line,
                }

                # Extract file information if available
                if len(match.groups()) >= 3 and match.group(1) and match.group(2):
                    error["file"] = match.group(1)
                    error["line_number"] = int(match.group(2))
                    if len(match.groups()) >= 4:
                        error["error_message"] = match.group(4)

                errors.append(error)
                logger.info(f"Detected {error['type']}: {error['line_content']}")

    return errors


def _attempt_error_fix(error_info: dict, css_dir: str | Path, _theme_dir: str | Path) -> bool:
    """
    Attempt to automatically fix a specific compilation error.

    Args:
        error_info: Error information dictionary
        css_dir: CSS directory path
        _theme_dir: Theme directory path (unused)

    Returns:
        bool: True if fix was applied, False otherwise
    """
    error_type = error_info.get("type")
    css_path = Path(css_dir)

    try:
        if error_type == "undefined_variable":
            return _fix_undefined_variable(error_info, css_path)

        if error_type == "undefined_mixin":
            return _fix_undefined_mixin(error_info, css_path)

        if error_type == "syntax_error":
            return _fix_syntax_error(error_info, css_path)

        if error_type == "invalid_css":
            return _fix_invalid_css(error_info, css_path)

        logger.info(f"No automated fix available for error type: {error_type}")
        return False

    except Exception as e:
        logger.warning(f"Error applying fix for {error_type}: {e}")
        return False


def _fix_undefined_variable(error_info: dict, css_dir: Path) -> bool:
    """Fix undefined SCSS variables by uncommenting or replacing with CSS variables."""
    variable_name = error_info["match_groups"][0] if error_info["match_groups"] else None

    if not variable_name:
        return False

    logger.info(f"Attempting to fix undefined variable: ${variable_name}")

    # First, try to uncomment the variable in _variables.scss
    variables_file = css_dir / "_variables.scss"
    if variables_file.exists():
        try:
            content = variables_file.read_text()
            lines = content.splitlines()
            modified = False

            for i, line in enumerate(lines):
                # Look for commented variable definition
                if (
                    f"${variable_name}:" in line
                    and line.strip().startswith("//")
                    and not line.strip().startswith("// SCSS CONVERTED:")
                ):
                    # Uncomment the line
                    _uncommented_line = line.lstrip("/ ").strip()
                    if _uncommented_line.startswith("$"):
                        lines[i] = _uncommented_line
                        modified = True
                        logger.info(f"Uncommented variable definition: ${variable_name}")
                        break

            if modified:
                variables_file.write_text("\n".join(lines) + "\n")
                return True

        except Exception as e:
            logger.warning(f"Error fixing variable in _variables.scss: {e}")

    # Fallback: Replace undefined variable with CSS variable equivalent in test files
    for file_path in css_dir.iterdir():
        if file_path.name.startswith("test-") and file_path.suffix == ".scss":
            try:
                content = file_path.read_text()

                # Replace undefined variable with CSS variable equivalent
                original_content = content
                content = content.replace(f"${variable_name}", f"var(--{variable_name})")

                if content != original_content:
                    file_path.write_text(content)
                    logger.info(f"Fixed undefined variable ${variable_name} in {file_path.name}")
                    return True

            except Exception as e:
                logger.warning(f"Error fixing variable in {file_path.name}: {e}")

    return False


def _fix_undefined_mixin(error_info: dict, css_dir: Path) -> bool:
    """Fix undefined mixins by commenting them out."""
    if "match_groups" not in error_info or not error_info["match_groups"]:
        return False

    mixin_name = error_info["match_groups"][0]
    logger.info(f"Attempting to fix undefined mixin: {mixin_name}")

    # Find and comment out mixin usage
    for file_path in css_dir.iterdir():
        if file_path.name.startswith("test-") and file_path.suffix == ".scss":
            try:
                content = file_path.read_text()
                lines = content.splitlines(keepends=True)

                modified = False
                for i, line in enumerate(lines):
                    if f"@include {mixin_name}" in line:
                        lines[i] = f"// COMMENTED OUT: {line.strip()}\n"
                        modified = True
                        logger.info(f"Commented out mixin usage: {mixin_name}")

                if modified:
                    file_path.write_text("".join(lines))
                    return True

            except Exception as e:
                logger.warning(f"Error fixing mixin in {file_path.name}: {e}")

    return False


def _fix_syntax_error(_error_info: dict, scss_content: str) -> str | None:
    """Comment out lines with syntax errors."""
    return _comment_out_error_line(_error_info, scss_content)


def _fix_invalid_css(error_info: dict, css_dir: Path) -> bool:
    """Fix invalid CSS syntax errors."""
    error_message = error_info.get("message", "")

    # Handle dangling comma selectors (like .navbar .navbar-inner ul.nav li a,)
    if "expected 1 selector or at-rule" in error_message and (
        ".navbar" in error_message or "navbar-inn" in error_message
    ):
        return _fix_dangling_comma_selector(error_info, css_dir)

    # Handle specific mixin parameter syntax errors
    if "fade-transition(" in error_message and "var(--element))" in error_message:
        return _fix_mixin_parameter_syntax(error_info, css_dir)

    # Handle other invalid CSS patterns
    if 'expected ")"' in error_message or 'expected "{"' in error_message:
        return _fix_parenthesis_mismatch(error_info, css_dir)

    # Fall back to commenting out the line
    return _comment_out_error_line(error_info, css_dir)


def _fix_dangling_comma_selector(_error_info: dict, css_dir: Path) -> bool:
    """Fix dangling comma selectors followed by comments that break SCSS compilation."""
    for file_path in css_dir.iterdir():
        if file_path.name.startswith("test-") and file_path.suffix == ".scss":
            try:
                content = file_path.read_text()
                lines = content.splitlines(keepends=True)

                modified = False
                for i, line in enumerate(lines):
                    # Look for lines ending with comma followed by EXCLUDED comments
                    if (
                        line.strip().endswith(",")
                        and i + 1 < len(lines)
                        and "EXCLUDED" in lines[i + 1]
                        and "RULE:" in lines[i + 1]
                    ):
                        # Remove the comma and comment out the problematic line
                        lines[i] = f"// FIXED DANGLING COMMA: {line.strip().rstrip(',')}"
                        # Also comment out the EXCLUDED comment line
                        lines[i + 1] = f"// REMOVED EXCLUSION COMMENT: {lines[i + 1].strip()}\n"
                        modified = True
                        logger.info(
                            f"Fixed dangling comma selector in {file_path.name} at line {i + 1}"
                        )

                if modified:
                    file_path.write_text("".join(lines))
                    return True

            except Exception as e:
                logger.warning(f"Error fixing dangling comma in {file_path.name}: {e}")

    return False


def _fix_mixin_parameter_syntax(_error_info: dict, css_dir: Path) -> bool:
    """Fix mixin parameter syntax errors like fade-transition(var(--element))."""
    for file_path in css_dir.iterdir():
        if file_path.name.startswith("test-") and file_path.suffix == ".scss":
            try:
                content = file_path.read_text()

                # Fix fade-transition mixin with double closing parentheses
                fixed_content = re.sub(
                    r"fade-transition\(var\(--([^)]+)\)\)", r"fade-transition(var(--\1))", content
                )

                if fixed_content != content:
                    file_path.write_text(fixed_content)
                    logger.info(f"Fixed mixin parameter syntax in {file_path.name}")
                    return True

            except Exception as e:
                logger.warning(f"Error fixing mixin parameters in {file_path.name}: {e}")

    return False


def _fix_parenthesis_mismatch(_error_info: dict, css_dir: Path) -> bool:
    """Fix parenthesis mismatch errors."""
    for file_path in css_dir.iterdir():
        if file_path.name.startswith("test-") and file_path.suffix == ".scss":
            try:
                content = file_path.read_text()
                lines = content.splitlines(keepends=True)

                modified = False
                for i, _line in enumerate(lines):
                    # Fix common parenthesis issues
                    if ")" in _line and "(" in _line:
                        # Count parentheses
                        open_count = _line.count("(")
                        close_count = _line.count(")")

                        if close_count > open_count:
                            # Remove extra closing parentheses
                            while close_count > open_count and ")" in _line:
                                _line = _line.replace(")", "", 1)
                                close_count -= 1

                            lines[i] = _line
                            modified = True
                            logger.info(
                                f"Fixed parenthesis mismatch in {file_path.name} line {i + 1}"
                            )

                if modified:
                    file_path.write_text("".join(lines))
                    return True

            except Exception as e:
                logger.warning(f"Error fixing parentheses in {file_path.name}: {e}")

    return False


def _comment_out_error_line(error_info: dict, css_dir: Path) -> bool:
    """Comment out a problematic line of code."""
    if "file" not in error_info or "line_number" not in error_info:
        return False

    file_name = error_info["file"]
    line_number = error_info["line_number"]

    # Find the test file
    test_file_path = None
    for file_path in css_dir.iterdir():
        if file_path.name.startswith("test-") and file_name in file_path.name:
            test_file_path = file_path
            break

    if not test_file_path or not test_file_path.exists():
        return False

    try:
        content = test_file_path.read_text()
        lines = content.splitlines(keepends=True)

        if line_number <= len(lines):
            original_line = lines[line_number - 1]
            stripped_line = original_line.strip()

            # CRITICAL FIX: Don't comment out lines that only contain a closing brace
            # or preserve the brace if it's part of the line.
            if stripped_line == "}":
                logger.info(
                    f"Skipping commenting out line {line_number} in {file_name} because it is just a closing brace."
                )
                return False

            if "}" in stripped_line and not any(c.isalnum() for c in stripped_line.split("}")[0]):
                # If the line looks like "  }" or similar, don't comment it out
                logger.info(
                    f"Skipping commenting out line {line_number} in {file_name} to preserve block structure."
                )
                return False

            # If there's a brace at the end of the line, try to preserve it
            if stripped_line.endswith("}") and not stripped_line.startswith("}"):
                lines[line_number - 1] = (
                    f"// ERROR COMMENTED OUT: {stripped_line.rstrip('}')}\n}}\n"
                )
            else:
                lines[line_number - 1] = f"// ERROR COMMENTED OUT: {stripped_line}\n"

            test_file_path.write_text("".join(lines))

            logger.info(f"Commented out problematic line {line_number} in {file_name}")
            return True

    except Exception as e:
        logger.warning(f"Error commenting out line: {e}")

    return False


def _cleanup_compilation_test_files(css_dir: str | Path, test_files: list[tuple[str, str]]) -> None:
    """
    Clean up test files created during compilation testing.

    Args:
        css_dir: Path to CSS directory
        test_files: List of (test_filename, scss_path) tuples
    """
    css_path_dir = Path(css_dir)
    for test_filename, _ in test_files:
        test_path = css_path_dir / test_filename
        css_filename = test_filename.replace(".scss", ".css")
        css_path = css_path_dir / css_filename

        # Remove test SCSS file
        if test_path.exists():
            test_path.unlink()
            logger.info(f"Removed test file: {test_filename}")

        # Remove generated CSS file
        if css_path.exists():
            css_path.unlink()
            logger.info(f"Removed generated CSS: {css_filename}")

    # Wait for cleanup cycle to complete
    time.sleep(1)

    # Reset any tracked changes
    try:
        subprocess.run(
            ["git", "reset", "--hard"],
            check=False,
            cwd=str(css_path_dir.parent),
            capture_output=True,
            timeout=10,
        )
        logger.info("Reset git working directory after test cleanup")
    except Exception as e:
        logger.warning(f"Could not reset git directory: {e}")


def _comment_out_problematic_code(
    test_files: list[tuple[str, str]], css_dir: str | Path
) -> list[dict]:
    """
    Systematically comment out problematic SCSS code based on actual compilation errors.

    Args:
        test_files: List of test files
        css_dir: CSS directory path

    Returns:
        list: List of commented out lines with file info
    """
    logger.warning("Systematically commenting out problematic SCSS code...")

    commented_lines = []
    css_path = Path(css_dir)

    # Get current Docker logs to identify specific errors
    docker_errors = _get_current_compilation_errors()

    if docker_errors:
        # Comment out lines based on actual errors
        for error in docker_errors:
            if "fade-transition" in error.get("message", ""):
                lines_commented = _comment_lines_containing(
                    test_files, css_path, "fade-transition", "fade-transition mixin"
                )
                commented_lines.extend(lines_commented)
            elif "undefined mixin" in error.get("message", "").lower():
                mixin_name = _extract_mixin_name_from_error(error)
                if mixin_name:
                    lines_commented = _comment_lines_containing(
                        test_files,
                        css_path,
                        f"@include {mixin_name}",
                        f"undefined mixin: {mixin_name}",
                    )
                    commented_lines.extend(lines_commented)
            elif "lighten(" in error.get("message", "") or "darken(" in error.get("message", ""):
                lines_commented = _comment_lines_containing(
                    test_files, css_path, ["lighten(", "darken("], "SCSS color functions"
                )
                commented_lines.extend(lines_commented)
    else:
        # Fallback: comment common problematic patterns
        logger.warning("No specific errors found, using fallback pattern commenting")
        fallback_patterns = [
            ("fade-transition", "fade-transition mixin"),
            ("lighten(", "lighten function"),
            ("darken(", "darken function"),
            ("@include", "mixin calls"),
        ]

        for pattern, description in fallback_patterns:
            lines_commented = _comment_lines_containing(test_files, css_path, pattern, description)
            commented_lines.extend(lines_commented)
            if lines_commented:  # Stop after first successful comment
                break
    return commented_lines


def _get_current_compilation_errors() -> list[dict]:
    """Get current compilation errors from Docker logs."""
    try:
        result = subprocess.run(
            ["docker", "logs", "--tail", "30", "dealerinspire_legacy_assets"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0 and result.stdout:
            logs = result.stdout
            errors = []

            # Parse different error patterns
            for line in logs.split("\n"):
                if "error:" in line.lower():
                    errors.append({"message": line, "type": "error"})
                elif "undefined" in line.lower():
                    errors.append({"message": line, "type": "undefined"})

            return errors
    except Exception as e:
        logger.warning(f"Error getting Docker logs: {e}")

    return []


def _extract_mixin_name_from_error(error: dict) -> str | None:
    """Extract mixin name from error message."""
    message = error.get("message", "")
    # Look for patterns like "Undefined mixin 'fade-transition'"
    match = re.search(r"mixin['\s]+([a-zA-Z_-]+)", message)
    return match.group(1) if match else None


def _comment_lines_containing(
    test_files: list[tuple[str, str]],
    css_dir: Path,
    patterns: str | list[str],
    description: str,
) -> list[dict]:
    """Comment out lines containing specific patterns."""
    if isinstance(patterns, str):
        patterns = [patterns]

    commented_lines = []

    for test_filename, _ in test_files:
        test_file_path = css_dir / test_filename

        if not test_file_path.exists():
            continue

        try:
            content = test_file_path.read_text()
            lines = content.split("\n")
            modified = False

            for i, line in enumerate(lines):
                if line.strip().startswith("//"):
                    continue  # Skip already commented lines

                # Check if line contains any of the patterns
                for pattern in patterns:
                    if pattern in line:
                        original_line = line.strip()
                        lines[i] = f"// COMMENTED OUT: {line}"
                        modified = True

                        # Track what was commented out
                        commented_lines.append(
                            {
                                "file": test_filename.replace("test-", ""),
                                "line": original_line,
                                "reason": description,
                            }
                        )

                        logger.info(
                            f"Commented out {description} in {test_filename}: {original_line}"
                        )
                        break

            if modified:
                test_file_path.write_text("\n".join(lines))
                logger.info(f"Commented out {description} in {test_filename}")

        except Exception as e:
            logger.warning(f"Error processing {test_filename}: {e}")

    return commented_lines


def _copy_successful_test_files_to_originals(
    test_files: list[tuple[str, str]], css_dir: str | Path, theme_dir: str | Path
) -> None:
    """
    Copy successful test files back to original locations.

    Args:
        test_files: List of (test_filename, original_path) tuples
        css_dir: CSS directory path
        theme_dir: Theme directory path
    """
    logger.info("Copying successful test files back to original locations...")
    css_path_dir = Path(css_dir)
    theme_path = Path(theme_dir)

    for test_filename, _ in test_files:
        test_file_path = css_path_dir / test_filename
        original_filename = test_filename.replace("test-", "")
        original_path = theme_path / original_filename

        if test_file_path.exists():
            try:
                shutil.copy2(test_file_path, original_path)
                logger.info(f"Copied {test_filename} back to {original_filename}")
            except Exception as e:
                logger.warning(f"Error copying {test_filename} to {original_filename}: {e}")


def _report_commented_code(commented_lines: list[dict], slug: str) -> None:
    """
    Report what code was commented out to the user.

    Args:
        commented_lines: List of commented line info
        slug: Theme slug
    """
    if not commented_lines:
        click.echo("✅ No code needed to be commented out")
        return

    click.echo(f"\n📋 Compilation Success Report for {slug}")
    click.echo("=" * 60)
    click.echo("✅ SCSS files now compile successfully!")
    click.echo(
        f"🔧 {len(commented_lines)} lines of code were automatically commented out to fix "
        "compilation errors:"
    )
    click.echo()

    # Group by file
    by_file = {}
    for item in commented_lines:
        if item["file"] not in by_file:
            by_file[item["file"]] = []
        by_file[item["file"]].append(item)

    for filename, items in by_file.items():
        click.echo(f"📄 {filename}:")
        for item in items:
            click.echo(f"   • {item['reason']}: {item['line']}")
        click.echo()

    click.echo("💡 Next steps:")
    click.echo("   • Review the commented code above")
    click.echo("   • Consider implementing CSS equivalents where possible")
    click.echo("   • Update your SCSS to avoid these patterns in the future")
    click.echo("=" * 60)
