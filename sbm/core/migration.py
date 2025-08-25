"""
Core migration functionality for the SBM tool.

This module handles the main migration logic for dealer themes.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from typing import TYPE_CHECKING

import click  # Import click for interactive prompts

from sbm.oem.factory import OEMFactory
from sbm.scss.processor import SCSSProcessor
from sbm.utils.command import execute_command, execute_interactive_command
from sbm.utils.logger import logger
from sbm.utils.path import get_dealer_theme_dir

from .git import commit_changes, git_operations, push_changes  # Import git functions
from .git import create_pr as git_create_pr  # Import with alias to avoid naming conflicts
from .maps import migrate_map_components

if TYPE_CHECKING:
    from sbm.ui.console import SBMConsole


def _cleanup_exclusion_comments(slug: str) -> None:
    """
    Remove any existing EXCLUDED RULE comments from SCSS files to prevent compilation errors.
    
    Args:
        slug (str): Dealer theme slug
    """
    try:
        theme_dir = get_dealer_theme_dir(slug)
        scss_files = ["sb-inside.scss", "sb-vdp.scss", "sb-vrp.scss", "sb-home.scss"]

        total_cleaned = 0
        for scss_file in scss_files:
            file_path = os.path.join(theme_dir, scss_file)
            if os.path.exists(file_path):
                with open(file_path) as f:
                    content = f.read()

                # Remove EXCLUDED RULE comments and fix dangling commas
                lines = content.split("\n")
                cleaned_lines = []
                i = 0
                while i < len(lines):
                    line = lines[i]

                    # Check for dangling comma followed by EXCLUDED comment
                    if (
                        line.strip().endswith(",") and
                        i + 1 < len(lines) and
                        "EXCLUDED" in lines[i + 1] and
                        "RULE:" in lines[i + 1]
                    ):
                        # Remove comma and add cleaned line
                        cleaned_line = line.strip().rstrip(",")
                        if cleaned_line:  # Only add if not empty
                            cleaned_lines.append(f"// CLEANED: {cleaned_line}")
                        # Skip the EXCLUDED comment line
                        i += 2
                        total_cleaned += 1
                        continue

                    # Remove standalone EXCLUDED comments
                    if "EXCLUDED" in line and "RULE:" in line:
                        # Skip this line entirely
                        i += 1
                        total_cleaned += 1
                        continue

                    # Keep regular lines
                    cleaned_lines.append(line)
                    i += 1

                # Write back if changes were made
                if total_cleaned > 0:
                    with open(file_path, "w") as f:
                        f.write("\n".join(cleaned_lines))
                    logger.info(f"Cleaned {total_cleaned} exclusion comments from {scss_file}")

        if total_cleaned > 0:
            logger.info(f"Total cleaned exclusion comments from {slug}: {total_cleaned}")

    except Exception as e:
        logger.warning(f"Error cleaning exclusion comments for {slug}: {e}")


def _cleanup_snapshot_files(slug: str) -> None:
    """
    Remove any .sbm-snapshots directories and files before committing.

    Args:
        slug (str): Dealer theme slug
    """
    try:
        theme_dir = get_dealer_theme_dir(slug)
        snapshot_dir = os.path.join(theme_dir, ".sbm-snapshots")

        if os.path.exists(snapshot_dir):
            import shutil

            shutil.rmtree(snapshot_dir)
            logger.info(f"Cleaned up snapshot directory: {snapshot_dir}")
        else:
            logger.debug(f"No snapshot directory found at: {snapshot_dir}")

        # Also clean up any individual .automated files that might exist
        import glob

        automated_files = glob.glob(os.path.join(theme_dir, "**", "*.automated"), recursive=True)
        for file_path in automated_files:
            try:
                os.remove(file_path)
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
        theme_dir = get_dealer_theme_dir(slug)
        snapshot_dir = os.path.join(theme_dir, ".sbm-snapshots")

        # Create snapshot directory
        os.makedirs(snapshot_dir, exist_ok=True)

        # List of Site Builder files to snapshot
        sb_files = ["sb-inside.scss", "sb-vdp.scss", "sb-vrp.scss", "sb-home.scss"]

        snapshots_created = 0
        for sb_file in sb_files:
            source_path = os.path.join(theme_dir, sb_file)
            if os.path.exists(source_path):
                snapshot_path = os.path.join(snapshot_dir, f"{sb_file}.automated")

                # Copy the automated output to snapshot
                with open(source_path) as source:
                    content = source.read()

                with open(snapshot_path, "w") as snapshot:
                    snapshot.write(content)

                snapshots_created += 1
                logger.debug(f"Created snapshot: {snapshot_path}")

        if snapshots_created > 0:
            logger.info(f"Created automation snapshot for {slug}")
            logger.info("Created automation snapshot before manual review")
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


def run_just_start(slug, suppress_output=False) -> bool:
    """
    Run the 'just start' command for the given slug (automatically chooses dev/prod database).
    Uses interactive execution to allow password prompts and user input.

    Args:
        slug (str): Dealer theme slug
        suppress_output (bool): Whether to suppress verbose Docker output (default: False)

    Returns:
        bool: True if successful, False otherwise
    """
    logger.info(f"Starting site build for {slug}")

    # Verify the 'just' command is available
    success, _, _, _ = execute_command("which just", "'just' command not found")
    if not success:
        logger.error("Please install 'just' or ensure it's in your PATH.")
        return False

    # Get the platform directory for running the command
    from sbm.utils.path import get_platform_dir

    platform_dir = get_platform_dir()

    # AWS authentication (simplified to avoid subprocess tracking issues)
    from sbm.ui.simple_rich import print_step_success, print_step_warning

    print_step_warning("Ensuring AWS authentication before Docker startup...")

    aws_login_success = execute_interactive_command(
        "saml2aws login -a inventory-non-prod-423154430651-developer",
        "AWS login failed",
        cwd=platform_dir,
        suppress_output=False,  # Always show AWS login prompts
    )

    if not aws_login_success:
        print_step_warning("AWS login failed - continuing anyway (Docker may fail)")
    else:
        print_step_success("AWS authentication completed")

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
        logger.info("'just start' command completed successfully.")
        return True
    from sbm.ui.simple_rich import print_step_error

    print_step_error("Docker startup failed!")
    logger.error("'just start' command failed.")
    logger.error("Common causes:")
    logger.error("  - AWS authentication expired")
    logger.error("  - Docker daemon not running")
    logger.error("  - Network connectivity issues")
    logger.error("  - Theme configuration problems")
    logger.error("Try running with --verbose-docker flag to see detailed output")
    return False


def create_sb_files(slug, force_reset=False) -> bool | None:
    """
    Create necessary Site Builder SCSS files if they don't exist.

    Args:
        slug (str): Dealer theme slug
        force_reset (bool): Whether to reset existing files

    Returns:
        bool: True if successful, False otherwise
    """
    logger.info(f"Creating Site Builder files for {slug}")

    try:
        theme_dir = get_dealer_theme_dir(slug)

        # List of Site Builder files to create
        sb_files = ["sb-inside.scss", "sb-vdp.scss", "sb-vrp.scss", "sb-home.scss"]

        for file in sb_files:
            file_path = os.path.join(theme_dir, file)

            # Skip if file exists and we're not forcing reset
            if os.path.exists(file_path) and not force_reset:
                logger.info(f"File {file} already exists, skipping creation")
                continue

            # Create or reset the file
            with open(file_path, "w") as f:
                f.write("")

            logger.info(f"Created {file}")

        return True

    except Exception as e:
        logger.error(f"Error creating Site Builder files: {e}")
        return False


def migrate_styles(slug: str) -> bool:
    """
    Orchestrates the SCSS migration for a given theme.
    1. Finds the theme directory.
    2. Initializes the SCSS processor.
    3. Processes the main SCSS files (style.scss, inside.scss, _support-requests.scss, lvdp.scss, lvrp.scss).
    4. Writes the transformed files to the target directory.
    """
    logger.info(f"Migrating styles for {slug} using new SASS-based SCSSProcessor")
    try:
        theme_dir = get_dealer_theme_dir(slug)
        source_scss_dir = os.path.join(theme_dir, "css")

        if not os.path.isdir(source_scss_dir):
            logger.error(f"Source SCSS directory not found: {source_scss_dir}")
            return False

        processor = SCSSProcessor(slug, exclude_nav_styles=True)

        # Define source files - include style.scss, inside.scss, and _support-requests.scss for sb-inside
        inside_sources = [
            os.path.join(source_scss_dir, "style.scss"),
            os.path.join(source_scss_dir, "inside.scss"),
            os.path.join(source_scss_dir, "_support-requests.scss"),
        ]
        # Only use lvdp.scss and lvrp.scss, not vdp.scss and vrp.scss
        vdp_sources = [os.path.join(source_scss_dir, "lvdp.scss")]
        vrp_sources = [os.path.join(source_scss_dir, "lvrp.scss")]

        # Process each category
        inside_content = "\n".join(
            [processor.process_scss_file(f) for f in inside_sources if os.path.exists(f)]
        )
        vdp_content = "\n".join(
            [processor.process_scss_file(f) for f in vdp_sources if os.path.exists(f)]
        )
        vrp_content = "\n".join(
            [processor.process_scss_file(f) for f in vrp_sources if os.path.exists(f)]
        )

        # Combine results
        results = {
            "sb-inside.scss": inside_content,
            "sb-vdp.scss": vdp_content,
            "sb-vrp.scss": vrp_content,
        }

        # Write the resulting CSS to files
        success = processor.write_files_atomically(theme_dir, results)

        if success:
            for filename, content in results.items():
                if content:
                    lines = len(content.splitlines())
                    logger.info(f"Generated {filename}: {lines} lines")
            logger.info("SCSS migration completed successfully!")
        else:
            logger.error("SCSS migration failed during file writing.")

        return success

    except Exception as e:
        logger.error(f"Error migrating styles: {e}", exc_info=True)
        return False


def add_predetermined_styles(slug, oem_handler=None) -> bool | None:
    """
    Add predetermined styles for cookie disclaimer and directions row.

    Args:
        slug (str): Dealer theme slug
        oem_handler (BaseOEMHandler, optional): OEM handler for the dealer

    Returns:
        bool: True if successful, False otherwise
    """
    logger.info(f"Adding predetermined styles for {slug}")

    try:
        theme_dir = get_dealer_theme_dir(slug)

        # Paths to the SCSS files
        sb_inside_path = os.path.join(theme_dir, "sb-inside.scss")
        sb_home_path = os.path.join(theme_dir, "sb-home.scss")

        if not os.path.exists(sb_inside_path):
            logger.warning(f"sb-inside.scss not found for {slug}")
            return False

        if not os.path.exists(sb_home_path):
            logger.warning(f"sb-home.scss not found for {slug}")
            return False

        # Use OEM factory to get handler if not provided
        if oem_handler is None:
            oem_handler = OEMFactory.detect_from_theme(slug)
            logger.info(f"Using {oem_handler} for {slug}")

        # Only add Stellantis styles for Stellantis dealers
        from sbm.oem.stellantis import StellantisHandler

        if not isinstance(oem_handler, StellantisHandler):
            logger.info(f"Skipping Stellantis-specific styles for non-Stellantis dealer: {slug}")
            return True

        # 1. Add cookie banner styles to both sb-inside.scss and sb-home.scss (directly from source file)
        # Get the auto-sbm directory path
        auto_sbm_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        cookie_banner_source = os.path.join(
            auto_sbm_dir, "stellantis", "add-to-sb-inside", "stellantis-cookie-banner-styles.scss"
        )
        if os.path.exists(cookie_banner_source):
            with open(cookie_banner_source) as f:
                cookie_styles = f.read()

            # Add to sb-inside.scss
            with open(sb_inside_path) as f:
                inside_content = f.read()

            if ".cookie-banner" not in inside_content:
                with open(sb_inside_path, "a") as f:
                    f.write("\n\n/* Cookie Banner Styles */\n")
                    f.write(cookie_styles)
                logger.info("Added cookie banner styles to sb-inside.scss")
            else:
                logger.info("Cookie banner styles already exist in sb-inside.scss")

            # Add to sb-home.scss
            with open(sb_home_path) as f:
                home_content = f.read()

            if ".cookie-banner" not in home_content:
                with open(sb_home_path, "a") as f:
                    f.write("\n\n/* Cookie Banner Styles */\n")
                    f.write(cookie_styles)
                logger.info("Added cookie banner styles to sb-home.scss")
            else:
                logger.info("Cookie banner styles already exist in sb-home.scss")
        else:
            logger.warning(f"Cookie banner source file not found: {cookie_banner_source}")

        # 2. Add directions row styles (directly from source file)
        directions_row_source = os.path.join(
            auto_sbm_dir, "stellantis", "add-to-sb-inside", "stellantis-directions-row-styles.scss"
        )
        if os.path.exists(directions_row_source):
            with open(directions_row_source) as f:
                directions_styles = f.read()

            # Check if directions row styles already exist
            with open(sb_inside_path) as f:
                content = f.read()

            if ".directions-row" not in content:
                # Append the directions styles
                with open(sb_inside_path, "a") as f:
                    f.write("\n\n/* Directions Row Styles */\n")
                    f.write(directions_styles)
                logger.info("Added directions row styles")
            else:
                logger.info("Directions row styles already exist")
        else:
            logger.warning(f"Directions row source file not found: {directions_row_source}")

        return True

    except Exception as e:
        logger.error(f"Error adding predetermined styles: {e}")
        return False


def _check_prettier_available() -> bool | None:
    """
    Check if prettier is available on the system.

    Returns:
        bool: True if prettier is available, False otherwise
    """
    try:
        # Try different ways to find prettier with extended PATH
        import os
        
        # Common paths where npm global packages are installed
        extended_paths = [
            "/usr/local/bin",
            "/opt/homebrew/bin", 
            os.path.expanduser("~/.nvm/versions/node/*/bin"),
            os.path.expanduser("~/.npm-global/bin")
        ]
        
        current_path = os.environ.get("PATH", "")
        extended_path = ":".join(extended_paths) + ":" + current_path
        
        # Set environment with extended PATH
        env = os.environ.copy()
        env["PATH"] = extended_path
        
        # First check if prettier command exists
        success, stdout, stderr, _ = execute_command(
            "prettier --version", 
            "Checking prettier availability", 
            wait_for_completion=True,
            env=env
        )

        if success and stdout:
            # Parse version to ensure it's actually prettier
            version_output = "".join(stdout).strip()
            if version_output and any(char.isdigit() for char in version_output):
                logger.debug(f"Prettier version detected: {version_output}")
                return True

        # If that fails, try which command to find prettier
        success, stdout, stderr, _ = execute_command(
            "which prettier", 
            "Finding prettier location", 
            wait_for_completion=True,
            env=env
        )
        
        if success and stdout:
            prettier_path = "".join(stdout).strip()
            if prettier_path and os.path.isfile(prettier_path):
                logger.debug(f"Prettier found at: {prettier_path}")
                return True

        return False
    except Exception as e:
        logger.debug(f"Prettier not available: {e}")
        return False


def _format_scss_with_prettier(file_path) -> bool | None:
    """
    Format an SCSS file with prettier if available.

    Args:
        file_path (str): Path to the SCSS file to format

    Returns:
        bool: True if formatting succeeded, False otherwise
    """
    try:
        # Setup extended PATH for prettier
        import os
        
        # Common paths where npm global packages are installed
        extended_paths = [
            "/usr/local/bin",
            "/opt/homebrew/bin", 
            os.path.expanduser("~/.nvm/versions/node/*/bin"),
            os.path.expanduser("~/.npm-global/bin")
        ]
        
        current_path = os.environ.get("PATH", "")
        extended_path = ":".join(extended_paths) + ":" + current_path
        
        # Set environment with extended PATH
        env = os.environ.copy()
        env["PATH"] = extended_path
        
        # Use prettier to format the file in place
        success, stdout, stderr, _ = execute_command(
            f"prettier --write '{file_path}'",
            f"Failed to format {os.path.basename(file_path)} with prettier",
            wait_for_completion=True,
            env=env
        )

        if success:
            return True
        # Log stderr for debugging if formatting failed
        if stderr:
            error_msg = "".join(stderr).strip()
            logger.debug(
                f"Prettier formatting error for {os.path.basename(file_path)}: {error_msg}"
            )
        return False

    except Exception as e:
        logger.warning(f"Could not format {os.path.basename(file_path)} with prettier: {e}")
        return False


def _format_all_scss_with_prettier(slug) -> bool | None:
    """
    Format all SCSS files in the theme directory with prettier using glob pattern.

    Args:
        slug (str): Dealer theme slug

    Returns:
        bool: True if formatting succeeded, False otherwise
    """
    try:
        import glob

        home_dir = os.path.expanduser("~")
        pattern = f"{home_dir}/di-websites-platform/dealer-themes/{slug}/sb-*.scss"
        logger.info(f"Prettier: Looking for files with pattern: {pattern}")

        files = glob.glob(pattern, recursive=True)
        logger.info(f"Prettier: Found {len(files)} files:")
        for file in files:
            logger.info(f"  - {file}")

        if not files:
            logger.warning("No sb-*.scss files found")
            return False

        # Use prettier from auto-sbm venv to ensure it's always available
        auto_sbm_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        prettier_path = os.path.join(auto_sbm_dir, ".venv", "bin", "prettier")

        # Fallback to system prettier if venv prettier doesn't exist
        if not os.path.exists(prettier_path):
            prettier_path = "prettier"
            logger.info("Prettier: Using system prettier (venv prettier not found)")
        else:
            logger.info(f"Prettier: Using venv prettier at {prettier_path}")

        command = [prettier_path, "--write", *files]
        logger.info(f"Prettier: Running command: {' '.join(command)}")

        result = subprocess.run(
            command, check=False, capture_output=True, text=True, env=os.environ
        )

        logger.info(f"Prettier: Exit code: {result.returncode}")
        if result.stdout:
            logger.info(f"Prettier stdout: {result.stdout}")
        if result.stderr:
            logger.info(f"Prettier stderr: {result.stderr}")

        # Prettier returns 0 on success even with warnings in stderr
        if result.returncode == 0:
            logger.info("Prettier: Formatting completed successfully")
            return True
        logger.error(f"Prettier: Failed with exit code {result.returncode}")
        return False

    except Exception as e:
        logger.error(f"Prettier: Exception occurred: {e}")
        import traceback

        logger.error(f"Prettier: Traceback: {traceback.format_exc()}")
        return False


def test_compilation_recovery(slug):
    """
    Test compilation error handling on an existing theme without doing migration.

    This function copies existing SCSS files to the CSS directory, monitors
    compilation, and tests the error recovery system without modifying
    the original theme files.

    Args:
        slug (str): Dealer theme slug

    Returns:
        bool: True if compilation succeeds or errors are handled, False otherwise
    """
    logger.info(f"Testing compilation error recovery for {slug}")

    try:
        theme_dir = get_dealer_theme_dir(slug)
        css_dir = os.path.join(theme_dir, "css")

        if not os.path.exists(css_dir):
            logger.error(f"CSS directory not found: {css_dir}")
            return False

        # List of Site Builder files to test
        sb_files = ["sb-inside.scss", "sb-vdp.scss", "sb-vrp.scss", "sb-home.scss"]
        test_files = []

        # Copy existing SCSS files to CSS directory for testing
        for sb_file in sb_files:
            scss_path = os.path.join(theme_dir, sb_file)
            if os.path.exists(scss_path):
                test_filename = f"test-{sb_file}"
                test_path = os.path.join(css_dir, test_filename)

                # Copy file for testing
                shutil.copy2(scss_path, test_path)
                test_files.append((test_filename, scss_path))
                logger.info(f"Copied {sb_file} to {test_filename} for testing")

        if not test_files:
            logger.warning("No SCSS files found to test")
            return False

        click.echo(f"\n🧪 Testing compilation error recovery on {len(test_files)} files")
        click.echo("Files will be copied to CSS directory to trigger Docker Gulp compilation...")

        # Test compilation with error recovery
        success = _handle_compilation_with_error_recovery(css_dir, test_files, theme_dir, slug)

        # Clean up test files
        click.echo("\n🧹 Cleaning up test files...")
        _cleanup_compilation_test_files(css_dir, test_files)

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


def reprocess_manual_changes(slug) -> bool | None:
    """
    Reprocess Site Builder SCSS files after manual review to ensure consistency.

    This function applies the same transformations as the initial migration
    to any manual changes made by the user, ensuring variables, mixins,
    and other SCSS patterns are properly processed.

    Args:
        slug (str): Dealer theme slug

    Returns:
        bool: True if reprocessing was successful, False otherwise
    """
    logger.info(f"Reprocessing manual changes for {slug}")

    try:
        theme_dir = get_dealer_theme_dir(slug)
        processor = SCSSProcessor(slug, exclude_nav_styles=True)

        # List of Site Builder files to reprocess
        sb_files = ["sb-inside.scss", "sb-vdp.scss", "sb-vrp.scss", "sb-home.scss"]

        changes_made = False
        processed_files = []

        # Check if prettier is available for formatting
        prettier_available = _check_prettier_available()
        if prettier_available:
            logger.info("Prettier detected - will format SCSS files after processing")
        else:
            logger.info("Prettier not available - using default formatting")

        for sb_file in sb_files:
            file_path = os.path.join(theme_dir, sb_file)

            if os.path.exists(file_path):
                # Read the current manually-edited content
                with open(file_path, encoding="utf-8") as f:
                    original_content = f.read()

                # Skip if file is empty
                if not original_content.strip():
                    continue

                # Apply reprocess-specific transformation logic to existing content
                # This ensures all conversions (variables, paths, mixins, functions) are applied
                # while preserving manual edits and avoiding duplicate utility functions
                processed_content = processor.reprocess_scss_content(original_content)

                # Check if any changes were made
                if processed_content != original_content:
                    # Write the processed content back with explicit flushing
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(processed_content)
                        f.flush()  # Ensure content is written to disk
                        os.fsync(f.fileno())  # Force write to disk

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

        # Format all SCSS files at once with prettier if available
        if prettier_available:
            if _format_all_scss_with_prettier(slug):
                logger.info("Applied prettier formatting to all SCSS files")
            else:
                logger.warning("Prettier formatting failed, using default formatting")

        # Note: SCSS compilation verification moved to separate timer segment 
        # to avoid including long sleep/user interaction time in reprocessing timer
        return True

    except Exception as e:
        logger.error(f"Error reprocessing manual changes for {slug}: {e}")
        return False


def run_post_migration_workflow(
    slug,
    branch_name,
    skip_git=False,
    create_pr=True,
    interactive_review=True,
    interactive_git=True,
    interactive_pr=True,
    skip_reprocessing=False,
) -> bool:
    """
    Run the post-migration workflow including manual review, git operations, and PR creation.

    Args:
        slug (str): Dealer theme slug
        branch_name (str): Git branch name
        skip_git (bool): Whether to skip git operations
        create_pr (bool): Whether to create a pull request
        interactive_review (bool): DEPRECATED - manual review step removed
        interactive_git (bool): Whether to prompt for git operations
        interactive_pr (bool): Whether to prompt for PR creation

    Returns:
        bool: True if all steps are successful, False otherwise.
    """
    logger.info(f"Starting post-migration workflow for {slug} on branch {branch_name}")

    # Skip manual review - go directly to processing
    if False:  # interactive_review disabled
        # Clear the terminal to ensure clean display
        import os
        import sys
        import time

        # Force close any active Rich contexts
        try:
            from rich.console import Console
            console = Console()
            console.clear()
        except (ImportError, AttributeError):
            # Console clearing failed, not critical for functionality
            pass

        # Clear terminal using system command
        os.system("clear" if os.name == "posix" else "cls")

        # Brief pause to ensure terminal is clear
        time.sleep(0.1)

        # Force flush any remaining Rich output
        sys.stdout.flush()
        sys.stderr.flush()

        # Use direct sys.stdout.write to bypass any Rich interference
        message = f"""🎉 MIGRATION COMPLETED SUCCESSFULLY! 🎉

================================================================================
Manual Review Required for {slug}
Please review the migrated SCSS files in your theme directory:
  - {get_dealer_theme_dir(slug)}/sb-inside.scss
  - {get_dealer_theme_dir(slug)}/sb-vdp.scss
  - {get_dealer_theme_dir(slug)}/sb-vrp.scss
  - {get_dealer_theme_dir(slug)}/sb-home.scss

Verify the content and make any necessary manual adjustments.
Once you are satisfied, proceed to the next step.
================================================================================

"""
        sys.stdout.write(message)
        sys.stdout.flush()

        # Use basic input() for maximum compatibility - no Rich, no Click interference
        from sbm.utils.timer import timer_pause
        while True:
            try:
                with timer_pause("Manual review confirmation"):
                    sys.stdout.write("Continue with the migration after manual review? [Y/n]: ")
                    sys.stdout.flush()
                    response = input().strip().lower()
                if response in ("", "y", "yes"):
                    break
                if response in ("n", "no"):
                    logger.info("Post-migration workflow stopped by user after manual review.")
                    return False
                with timer_pause("Invalid input clarification"):
                    sys.stdout.write("Please enter 'y' or 'n': ")
                    sys.stdout.flush()
            except (EOFError, KeyboardInterrupt):
                logger.info("Post-migration workflow stopped by user after manual review.")
                return False

        # Reprocess manual changes to ensure consistency (skip if already verified)
        if not skip_reprocessing:
            logger.info(f"Reprocessing manual changes for {slug} to ensure consistency...")
            from sbm.utils.timer import timer_segment
            with timer_segment("Reprocessing Manual Changes"):
                if not reprocess_manual_changes(slug):
                    logger.error("Failed to reprocess manual changes.")
                    return False
            
            # Verify SCSS compilation in separate timer to avoid including long sleep/user interaction time
            with timer_segment("SCSS Compilation Verification"):
                theme_dir = get_dealer_theme_dir(slug)
                sb_files = ["sb-inside.scss", "sb-vdp.scss", "sb-vrp.scss", "sb-home.scss"]
                compilation_result = _verify_scss_compilation_with_docker(theme_dir, slug, sb_files)
                if not compilation_result:
                    logger.error("SCSS compilation verification failed - files do not compile with Docker Gulp")
                    logger.error("This may indicate syntax errors in the generated SCSS files.")
                    logger.error("You may need to manually review and fix the Site Builder files.")
                    # Don't throw exception - let the process continue and user can fix manually
                    return False
                logger.info("✅ All SCSS files verified to compile successfully with Docker Gulp")
        else:
            logger.info("Skipping reprocessing - files were already manually fixed and verified")

        # Clean up snapshot files after manual review phase
        logger.info("Cleaning up automation snapshots after manual review")
        _cleanup_snapshot_files(slug)
    else:
        # If no interactive review, still do cleanup and reprocessing
        if not skip_reprocessing:
            logger.info(f"Reprocessing manual changes for {slug} to ensure consistency...")
            from sbm.utils.timer import timer_segment
            with timer_segment("Reprocessing Manual Changes"):
                if not reprocess_manual_changes(slug):
                    logger.error("Failed to reprocess manual changes.")
                    return False
            
            # Verify SCSS compilation in separate timer to avoid including long sleep/user interaction time
            with timer_segment("SCSS Compilation Verification"):
                theme_dir = get_dealer_theme_dir(slug)
                sb_files = ["sb-inside.scss", "sb-vdp.scss", "sb-vrp.scss", "sb-home.scss"]
                compilation_result = _verify_scss_compilation_with_docker(theme_dir, slug, sb_files)
                if not compilation_result:
                    logger.error("SCSS compilation verification failed - files do not compile with Docker Gulp")
                    logger.error("This may indicate syntax errors in the generated SCSS files.")
                    logger.error("You may need to manually review and fix the Site Builder files.")
                    # Don't throw exception - let the process continue and user can fix manually
                    return False
                logger.info("✅ All SCSS files verified to compile successfully with Docker Gulp")
        logger.info("Cleaning up automation snapshots")
        _cleanup_snapshot_files(slug)

    # Git commit prompt with consistent input handling
    commit_response = "y"  # Default to yes
    if interactive_git:
        import sys
        sys.stdout.write(f"Commit all changes for {slug}? [Y/n]: ")
        sys.stdout.flush()
        commit_response = input().strip().lower()
        if commit_response in ("n", "no"):
            logger.info("Skipping commit.")
            return True

    if not interactive_git or commit_response in ("", "y", "yes"):
        # Clean up any snapshot files before committing - do this right before git operations
        _cleanup_snapshot_files(slug)

        from sbm.utils.timer import timer_segment
        with timer_segment("Git Commit Operations"):
            if not commit_changes(slug):
                logger.error("Failed to commit changes.")
                return False

        # Clean up snapshots again after commit in case they were recreated
        _cleanup_snapshot_files(slug)
    else:
        logger.info("Skipping commit.")
        return True  # End workflow if user skips commit

    # Git push prompt with consistent input handling
    push_response = "y"  # Default to yes
    if interactive_git:
        sys.stdout.write(f"Push changes to origin/{branch_name}? [Y/n]: ")
        sys.stdout.flush()
        push_response = input().strip().lower()
        if push_response in ("n", "no"):
            logger.info("Skipping push.")
            return True

    if not interactive_git or push_response in ("", "y", "yes"):
        from sbm.utils.timer import timer_segment
        with timer_segment("Git Push Operations"):
            if not push_changes(branch_name):
                logger.error("Failed to push changes.")
                return False
    else:
        logger.info("Skipping push.")
        return True  # End workflow if user skips push

    if create_pr:
        # PR creation prompt with consistent input handling
        pr_response = "y"  # Default to yes
        if interactive_pr:
            sys.stdout.write("Create a pull request? [Y/n]: ")
            sys.stdout.flush()
            pr_response = input().strip().lower()
            if pr_response in ("n", "no"):
                logger.info("Skipping pull request creation.")
                return True

        if not interactive_pr or pr_response in ("", "y", "yes"):
            logger.info("Creating pull request...")
            try:
                from sbm.utils.timer import timer_segment
                with timer_segment("GitHub PR Creation"):
                    pr_result = git_create_pr(slug=slug, branch_name=branch_name)

                if pr_result and pr_result.get("success"):
                    pr_url = pr_result.get("pr_url")
                    logger.info(f"Successfully created PR: {pr_url}")

                    # PR created successfully
                else:
                    error_message = pr_result.get("error", "Unknown error")
                    logger.error(f"Failed to create PR: {error_message}")
                    return False

            except Exception as e:
                logger.error(f"An exception occurred while creating PR: {e}")
                return False
        else:
            logger.info("Skipping pull request creation.")

    return True


def migrate_dealer_theme(
    slug,
    skip_just=False,
    force_reset=False,
    skip_git=False,
    skip_maps=False,
    oem_handler=None,
    create_pr=True,
    interactive_review=True,
    interactive_git=True,
    interactive_pr=True,
    verbose_docker=False,
):
    """
    Migrate a dealer theme to the Site Builder platform.

    Args:
        slug (str): Dealer theme slug
        skip_just (bool): Whether to skip the 'just start' command
        force_reset (bool): Whether to reset existing Site Builder files
        skip_git (bool): Whether to skip Git operations
        skip_maps (bool): Whether to skip map components migration
        oem_handler (BaseOEMHandler, optional): Manually specified OEM handler
        create_pr (bool): Whether to create a GitHub Pull Request after successful migration (default: True).
        interactive_review (bool): DEPRECATED - manual review step removed and re-validation.
        interactive_git (bool): Whether to prompt for Git add, commit, push.
        interactive_pr (bool): Whether to prompt for PR creation.

    Returns:
        bool: True if all steps are successful, False otherwise.
    """
    # Use simple Rich UI for beautiful output
    from sbm.ui.simple_rich import (
        print_migration_complete,
        print_migration_header,
        print_step,
        print_step_success,
    )

    print_migration_header(slug)
    logger.info(f"Starting migration for {slug}")

    # Create the appropriate OEM handler for this slug if not provided
    if oem_handler is None:
        oem_handler = OEMFactory.detect_from_theme(slug)

    logger.info(f"Using {oem_handler} for {slug}")

    branch_name = None  # Initialize branch_name

    # Perform Git operations if not skipped
    if not skip_git:
        print_step(1, 6, "Setting up Git branch and repository", slug)

        from sbm.utils.timer import timer_segment
        with timer_segment("Git Operations"):
            success, branch_name = git_operations(slug)
        if not success:
            logger.error(f"Git operations failed for {slug}")
            return False

        print_step_success(f"Git operations completed: branch {branch_name}")
        logger.info(f"Git operations completed successfully, branch: {branch_name}")

    # Run 'just start' if not skipped
    if not skip_just:
        print_step(2, 6, "Starting Docker environment (just start)", slug)

        # Temporarily pause progress tracking during Docker startup to avoid output interference
        from sbm.utils.timer import timer_segment
        with timer_segment("Docker Startup"):
            just_start_success = run_just_start(
                slug,
                suppress_output=False,  # Never suppress Docker output - user needs to see what's happening
            )

        logger.info(f"'just start' returned: {just_start_success}")
        if not just_start_success:
            logger.error(f"Failed to start site for {slug}")
            return False

        print_step_success("Docker environment started successfully")
        logger.info(f"Site started successfully for {slug}")

    # Create Site Builder files
    print_step(3, 6, "Creating Site Builder SCSS files", slug)

    from sbm.utils.timer import timer_segment
    with timer_segment("Site Builder File Creation"):
        if not create_sb_files(slug, force_reset):
            logger.error(f"Failed to create Site Builder files for {slug}")
            return False

    print_step_success("Site Builder files created successfully")

    # Migrate styles
    print_step(4, 6, "Migrating SCSS styles and transforming syntax", slug)

    from sbm.utils.timer import timer_segment
    with timer_segment("SCSS Migration"):
        if not migrate_styles(slug):
            logger.error(f"Failed to migrate styles for {slug}")
            return False

    print_step_success("SCSS styles migrated and transformed successfully")

    # Clean up any existing EXCLUDED RULE comments that could break compilation
    logger.info(f"Cleaning up exclusion comments for {slug}...")
    _cleanup_exclusion_comments(slug)

    # Add cookie banner and directions row styles as a separate step (after style migration)
    # This ensures these predetermined styles are not affected by the validators and parsers
    print_step(5, 6, "Adding predetermined OEM-specific styles", slug)
    if not add_predetermined_styles(slug, oem_handler):
        logger.warning(f"Could not add all predetermined styles for {slug}")

    print_step_success("Predetermined styles added successfully")

    # Migrate map components if not skipped
    if not skip_maps:
        print_step(6, 6, "Migrating map components and PHP partials", slug)
        if not migrate_map_components(slug, oem_handler, interactive=False):
            logger.error(f"Failed to migrate map components for {slug}")
            return False

        print_step_success("Map components migrated successfully")
        logger.info(f"Map components migrated successfully for {slug}")
    else:
        print_step(6, 6, "Skipping map components migration", slug)
        print_step_success("Map components skipped")

    logger.info(f"Migration completed successfully for {slug}")

    # Show beautiful completion message
    print_migration_complete(slug)

    # Create snapshots of the automated migration output for comparison
    _create_automation_snapshots(slug)

    # Always run post-migration workflow (git operations, PR creation)
    # Interactive flags control prompting behavior, not whether operations run
    return run_post_migration_workflow(
        slug,
        branch_name,
        skip_git=skip_git,
        create_pr=create_pr,
        interactive_review=interactive_review,
        interactive_git=interactive_git,
        interactive_pr=interactive_pr,
    )


def _verify_scss_compilation_with_docker(theme_dir: str, slug: str, sb_files: list) -> bool:
    """
    Verify SCSS compilation by copying files to CSS directory and monitoring Docker Gulp compilation.

    Args:
        theme_dir: Path to dealer theme directory
        slug: Dealer theme slug
        sb_files: List of Site Builder SCSS files to verify

    Returns:
        bool: True if all files compile successfully, False otherwise
    """
    css_dir = os.path.join(theme_dir, "css")
    test_files = []

    try:
        logger.info("Verifying SCSS compilation using Docker Gulp...")

        # Step 1: Copy sb-*.scss files to CSS directory with test prefix
        for sb_file in sb_files:
            src_path = os.path.join(theme_dir, sb_file)
            if os.path.exists(src_path):
                # Create test filename (sb-inside.scss -> test-sb-inside.scss)
                test_filename = f"test-{sb_file}"
                dst_path = os.path.join(css_dir, test_filename)

                shutil.copy2(src_path, dst_path)
                test_files.append((test_filename, dst_path))
                logger.info(f"Copied {sb_file} to {test_filename} for compilation test")

        if not test_files:
            logger.warning("No Site Builder files found to test")
            return True

        # Step 2: Wait for Docker Gulp to process the files
        logger.info("Monitoring Docker Gulp compilation...")
        time.sleep(1)  # Give Gulp time to detect and process files

        # Step 3: Check for corresponding CSS files
        max_wait = 5  # 5 seconds max wait time total
        start_time = time.time()
        compiled_files = []

        # If any file compiles, wait max 2 more seconds for others
        first_compile_time = None

        while (time.time() - start_time) < max_wait and len(compiled_files) < len(test_files):
            for test_filename, scss_path in test_files:
                if test_filename in compiled_files:
                    continue

                # Check for corresponding CSS file
                css_filename = test_filename.replace(".scss", ".css")
                css_path = os.path.join(css_dir, css_filename)

                if os.path.exists(css_path):
                    compiled_files.append(test_filename)
                    logger.info(f"✅ {test_filename} compiled successfully to {css_filename}")

                    # Start 2-second countdown after first compile
                    if first_compile_time is None:
                        first_compile_time = time.time()

            # If we have at least one compile and it's been 2+ seconds, stop waiting
            if first_compile_time and (time.time() - first_compile_time) >= 2:
                break

            if len(compiled_files) < len(test_files):
                time.sleep(0.2)  # Check every 200ms

        # Step 4: Monitor compilation with iterative error handling
        compilation_success = False
        try:
            # Attempt compilation with error handling loop
            if not _handle_compilation_with_error_recovery(css_dir, test_files, theme_dir, slug):
                logger.error("❌ SCSS compilation failed after error recovery attempts")
                return False

            # Step 5: Re-verify compilation success after error recovery
            # Check again for CSS files after error recovery completed - MUST be done BEFORE cleanup
            final_compiled_files = []
            for test_filename, scss_path in test_files:
                css_filename = test_filename.replace(".scss", ".css")
                css_path = os.path.join(css_dir, css_filename)
                if os.path.exists(css_path):
                    final_compiled_files.append(test_filename)

            compilation_success = len(final_compiled_files) == len(test_files)

            if compilation_success:
                logger.info(
                    f"✅ All {len(test_files)} SCSS files compiled successfully with Docker Gulp"
                )
            else:
                failed_files = [f for f, _ in test_files if f not in final_compiled_files]
                logger.error(f"❌ Docker Gulp compilation failed for: {', '.join(failed_files)}")

        except Exception as e:
            logger.error(f"Critical error during compilation monitoring: {e}")
            return False

        return compilation_success

    except Exception as e:
        logger.error(f"Error during Docker Gulp compilation verification: {e}")
        return False

    finally:
        # Step 6: Cleanup sequence to avoid triggering additional compilations
        try:
            # First: Remove untracked test files (this will trigger Gulp to compile again)
            logger.info("Removing test files...")
            for test_filename, scss_path in test_files:
                try:
                    # Remove test SCSS file
                    if os.path.exists(scss_path):
                        os.remove(scss_path)
                        logger.info(f"Removed test SCSS file: {test_filename}")

                    # Remove generated CSS file
                    css_filename = test_filename.replace(".scss", ".css")
                    css_path = os.path.join(css_dir, css_filename)
                    if os.path.exists(css_path):
                        os.remove(css_path)
                        logger.info(f"Removed generated CSS file: {css_filename}")

                except Exception as e:
                    logger.warning(f"Error removing test file {test_filename}: {e}")

            # Second: Wait for Gulp to finish the cleanup compilation cycle
            logger.info("Waiting for Gulp cleanup cycle to complete...")
            time.sleep(2)  # Give Gulp time to process file removals

            try:
                cleanup_wait = 10
                cleanup_start = time.time()
                cleanup_sass_done = False
                cleanup_process_done = False

                while (time.time() - cleanup_start) < cleanup_wait:
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
                            logger.info("✅ Gulp cleanup cycle completed")
                            break

                    time.sleep(1)

            except Exception as e:
                logger.warning(f"Could not monitor cleanup cycle: {e}")

            # Third: Reset CSS directory to undo any changes to tracked files
            result = subprocess.run(
                ["git", "checkout", "HEAD", "css/"],
                check=False,
                cwd=theme_dir,
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                logger.info("✅ CSS directory reset to original state using git checkout")
            else:
                logger.warning(f"Git checkout of CSS directory failed: {result.stderr}")

        except Exception as e:
            logger.warning(f"Error during CSS directory cleanup: {e}")


def _handle_compilation_with_error_recovery(
    css_dir: str, test_files: list, theme_dir: str, slug: str
) -> bool:
    """
    Handle SCSS compilation with comprehensive error recovery and iterative fixing.

    Args:
        css_dir: Path to CSS directory
        test_files: List of (test_filename, scss_path) tuples
        theme_dir: Path to dealer theme directory
        slug: Dealer theme slug

    Returns:
        bool: True if compilation succeeds, False if all recovery attempts fail
    """
    max_iterations = 5
    iteration = 0

    logger.info("Starting compilation monitoring with error recovery...")

    while iteration < max_iterations:
        iteration += 1
        logger.info(f"🔄 Compilation attempt {iteration}/{max_iterations}")

        # Wait for compilation cycle
        time.sleep(1)

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
                    # Check if any errors in recent logs (check original case-sensitive logs)
                    original_logs = result.stdout
                    if not any(
                        error_indicator in original_logs
                        for error_indicator in ["Error:", "gulp-notify: [Error running Gulp]"]
                    ):
                        logger.info("✅ Compilation completed successfully")
                        return True

                # Parse and handle specific errors
                errors_found = _parse_compilation_errors(logs, test_files)

                if errors_found:
                    logger.warning(f"Found {len(errors_found)} compilation errors")

                    # Attempt to fix each error
                    fixes_applied = 0
                    for error_info in errors_found:
                        if _attempt_error_fix(error_info, css_dir, theme_dir):
                            fixes_applied += 1

                    if fixes_applied > 0:
                        logger.info(
                            f"Applied {fixes_applied} automated fixes, retrying compilation..."
                        )
                        # Prompt user about changes
                        click.echo(f"\n🔧 Applied {fixes_applied} automated SCSS fixes")
                        click.echo(
                            "Files have been automatically repaired. Retrying compilation..."
                        )
                        continue
                    logger.warning("No automated fixes available for detected errors")
                    break
                # No specific errors found, but compilation may still be in progress
                logger.info("No specific errors detected, waiting for compilation...")

        except subprocess.TimeoutExpired:
            logger.warning("Docker logs command timed out")
        except Exception as e:
            logger.warning(f"Error checking Docker logs: {e}")

        # Check for successful CSS file generation
        success_count = 0
        for test_filename, _ in test_files:
            css_filename = test_filename.replace(".scss", ".css")
            css_path = os.path.join(css_dir, css_filename)
            if os.path.exists(css_path):
                success_count += 1

        if success_count == len(test_files):
            logger.info("✅ All CSS files generated successfully")
            return True

        logger.info(f"Compilation status: {success_count}/{len(test_files)} files compiled")

    # Final attempt - show user the exact error and let them fix it
    logger.error(f"❌ Compilation failed after {max_iterations} attempts")

    # Get the exact error details
    try:
        result = subprocess.run(
            ["docker", "logs", "--tail", "20", "dealerinspire_legacy_assets"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0 and result.stdout:
            logs = result.stdout
            _parse_compilation_errors(logs, test_files)

            click.echo("\n❌ SCSS Compilation Error")
            click.echo("=" * 50)

            # Parse the specific error from logs
            error_file = None
            error_line = None
            error_message = None

            # Extract error details from Docker logs
            for line in logs.split("\n"):
                # Look for error message lines
                if "Error:" in line and any(
                    keyword in line.lower()
                    for keyword in ["invalid", "undefined", "expected", "syntax"]
                ):
                    error_message = line.strip()
                # Look for "on line X of file" patterns
                elif "on line" in line and "test-sb-" in line:
                    # Parse: "on line 40 of ../DealerInspireDealerTheme/css/test-sb-inside.scss"
                    import re

                    match = re.search(r"on line (\d+) of [^/]*/(test-sb-[^/]+\.scss)", line)
                    if match:
                        error_line = int(match.group(1))
                        test_file = match.group(2)
                        # Convert test-sb-inside.scss -> sb-inside.scss
                        error_file = test_file.replace("test-", "")
                        break

            if error_file and error_line:
                click.echo(f"Error: {error_message}")
                click.echo(f"File: {error_file}")
                click.echo(f"Line: {error_line}")
                click.echo()

                # Open the file in default editor
                file_path = os.path.join(theme_dir, error_file)
                click.echo(f"Opening {error_file} for editing...")

                try:
                    subprocess.run(["open", file_path], check=False)
                except Exception as e:
                    logger.warning(f"Could not open file: {e}")
                    click.echo(f"Please manually open: {file_path}")
            else:
                # Fallback to raw error display
                if error_message:
                    click.echo(f"Error: {error_message}")
                else:
                    # Show more comprehensive error information
                    error_lines = [
                        line
                        for line in logs.split("\n")
                        if "error" in line.lower() and line.strip()
                    ]
                    if error_lines:
                        click.echo("Recent errors from Gulp:")
                        for line in error_lines[-3:]:  # Show last 3 error lines
                            click.echo(f"  {line.strip()}")
                    else:
                        # Show last few lines of logs for context
                        recent_lines = [line for line in logs.split("\n")[-10:] if line.strip()]
                        if recent_lines:
                            click.echo("Recent Gulp output:")
                            for line in recent_lines:
                                click.echo(f"  {line.strip()}")

                click.echo(f"Please check these files in: {theme_dir}")
                for test_filename, _ in test_files:
                    original_file = test_filename.replace("test-", "")
                    click.echo(f"  - {original_file}")

            click.echo("=" * 50)

            # CRITICAL FIX: Use Rich Prompt instead of click.confirm for visible input
            from rich.prompt import Confirm

            user_wants_to_continue = Confirm.ask("Continue after fixing the errors?", default=True)

            if user_wants_to_continue:
                # User fixed the errors manually, reprocess the files and test compilation
                logger.info("User confirmed manual fixes, reprocessing files...")

                # Clean up existing test files and CSS outputs
                for test_filename, _ in test_files:
                    test_file_path = os.path.join(css_dir, test_filename)
                    if os.path.exists(test_file_path):
                        os.remove(test_file_path)

                    # Also clean up any CSS output files
                    css_filename = test_filename.replace(".scss", ".css")
                    css_file_path = os.path.join(css_dir, css_filename)
                    if os.path.exists(css_file_path):
                        os.remove(css_file_path)

                # CRITICAL FIX: Do NOT reprocess manual changes - this causes infinite loop!
                # Just verify the manually fixed files compile correctly
                logger.info("Verifying manually fixed files compile correctly...")

                # Recopy the manually fixed files to test again
                for test_filename, _ in test_files:
                    original_file = test_filename.replace("test-", "")
                    src_path = os.path.join(theme_dir, original_file)
                    if os.path.exists(src_path):
                        dst_path = os.path.join(css_dir, test_filename)
                        shutil.copy2(src_path, dst_path)

                # Give Gulp time to compile
                time.sleep(2)

                # Check if compilation succeeded
                success_count = 0
                for test_filename, _ in test_files:
                    css_filename = test_filename.replace(".scss", ".css")
                    css_path = os.path.join(css_dir, css_filename)
                    if os.path.exists(css_path):
                        success_count += 1

                if success_count == len(test_files):
                    logger.info("✅ Manual fixes successful - all files now compile!")
                    return True
                logger.warning(f"Manual fixes incomplete: {success_count}/{len(test_files)} files compile")
                return False
            return False

    except Exception as e:
        logger.warning(f"Error getting compilation details: {e}")
        click.echo("\n❌ SCSS Compilation failed")
        click.echo("Check Docker logs: docker logs dealerinspire_legacy_assets")
        click.echo(f"Theme directory: {theme_dir}")

        # CRITICAL FIX: Use Rich Prompt instead of click.confirm for visible input
        from rich.prompt import Confirm

        if Confirm.ask("Continue anyway?", default=False):
            return True

    return False


def _parse_compilation_errors(logs: str, test_files: list) -> list:
    """
    Parse Docker Gulp logs to extract specific compilation error information.

    Args:
        logs: Docker Gulp log output
        test_files: List of test files being compiled

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
            import re

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


def _attempt_error_fix(error_info: dict, css_dir: str, theme_dir: str) -> bool:
    """
    Attempt to automatically fix a specific compilation error.

    Args:
        error_info: Error information dictionary
        css_dir: CSS directory path
        theme_dir: Theme directory path

    Returns:
        bool: True if fix was applied, False otherwise
    """
    error_type = error_info.get("type")

    try:
        if error_type == "undefined_variable":
            return _fix_undefined_variable(error_info, css_dir)

        if error_type == "undefined_mixin":
            return _fix_undefined_mixin(error_info, css_dir)

        if error_type == "syntax_error":
            return _fix_syntax_error(error_info, css_dir)

        if error_type == "invalid_css":
            return _fix_invalid_css(error_info, css_dir)

        logger.info(f"No automated fix available for error type: {error_type}")
        return False

    except Exception as e:
        logger.warning(f"Error applying fix for {error_type}: {e}")
        return False


def _fix_undefined_variable(error_info: dict, css_dir: str) -> bool:
    """Fix undefined SCSS variables by uncommenting them in _variables.scss or replacing with CSS variables."""
    variable_name = error_info["match_groups"][0] if error_info["match_groups"] else None

    if not variable_name:
        return False

    logger.info(f"Attempting to fix undefined variable: ${variable_name}")

    # First, try to uncomment the variable in _variables.scss
    variables_file = os.path.join(css_dir, "_variables.scss")
    if os.path.exists(variables_file):
        try:
            with open(variables_file) as f:
                content = f.read()

            lines = content.splitlines()
            modified = False

            for i, line in enumerate(lines):
                # Look for commented variable definition
                if (f"${variable_name}:" in line and
                    line.strip().startswith("//") and
                    not line.strip().startswith("// SCSS CONVERTED:")):
                    # Uncomment the line
                    uncommented_line = line.lstrip("/ ").strip()
                    if uncommented_line.startswith("$"):
                        lines[i] = uncommented_line
                        modified = True
                        logger.info(f"Uncommented variable definition: ${variable_name}")
                        break

            if modified:
                with open(variables_file, "w") as f:
                    f.write("\n".join(lines))
                return True

        except Exception as e:
            logger.warning(f"Error fixing variable in _variables.scss: {e}")

    # Fallback: Replace undefined variable with CSS variable equivalent in test files
    for file_name in os.listdir(css_dir):
        if file_name.startswith("test-") and file_name.endswith(".scss"):
            file_path = os.path.join(css_dir, file_name)

            try:
                with open(file_path) as f:
                    content = f.read()

                # Replace undefined variable with CSS variable equivalent
                original_content = content
                content = content.replace(f"${variable_name}", f"var(--{variable_name})")

                if content != original_content:
                    with open(file_path, "w") as f:
                        f.write(content)

                    logger.info(f"Fixed undefined variable ${variable_name} in {file_name}")
                    return True

            except Exception as e:
                logger.warning(f"Error fixing variable in {file_name}: {e}")

    return False


def _fix_undefined_mixin(error_info: dict, css_dir: str) -> bool:
    """Fix undefined mixins by commenting them out."""
    if "match_groups" not in error_info or not error_info["match_groups"]:
        return False

    mixin_name = error_info["match_groups"][0]
    logger.info(f"Attempting to fix undefined mixin: {mixin_name}")

    # Find and comment out mixin usage
    for file_name in os.listdir(css_dir):
        if file_name.startswith("test-") and file_name.endswith(".scss"):
            file_path = os.path.join(css_dir, file_name)

            try:
                with open(file_path) as f:
                    lines = f.readlines()

                modified = False
                for i, line in enumerate(lines):
                    if f"@include {mixin_name}" in line:
                        lines[i] = f"// COMMENTED OUT: {line.strip()}\n"
                        modified = True
                        logger.info(f"Commented out mixin usage: {mixin_name}")

                if modified:
                    with open(file_path, "w") as f:
                        f.writelines(lines)
                    return True

            except Exception as e:
                logger.warning(f"Error fixing mixin in {file_name}: {e}")

    return False


def _fix_syntax_error(error_info: dict, css_dir: str) -> bool:
    """Fix common SCSS syntax errors."""
    if "file" not in error_info or "line_number" not in error_info:
        return False

    file_name = error_info["file"]
    line_number = error_info["line_number"]

    # Find the test file
    test_file_path = None
    for fname in os.listdir(css_dir):
        if fname.startswith("test-") and file_name in fname:
            test_file_path = os.path.join(css_dir, fname)
            break

    if not test_file_path or not os.path.exists(test_file_path):
        return False

    try:
        with open(test_file_path) as f:
            lines = f.readlines()

        if line_number <= len(lines):
            problematic_line = lines[line_number - 1]

            # Common syntax fixes
            fixed_line = problematic_line

            # Fix missing semicolons
            if not problematic_line.strip().endswith((";", "{", "}")) and ":" in problematic_line:
                fixed_line = problematic_line.rstrip() + ";\n"

            # Fix lighten/darken functions with CSS variables
            import re

            fixed_line = re.sub(
                r"(lighten|darken)\(var\([^)]+\),\s*\d+%\)", lambda m: "var(--primary)", fixed_line
            )

            if fixed_line != problematic_line:
                lines[line_number - 1] = fixed_line

                with open(test_file_path, "w") as f:
                    f.writelines(lines)

                logger.info(f"Applied syntax fix at line {line_number} in {file_name}")
                return True

    except Exception as e:
        logger.warning(f"Error applying syntax fix: {e}")

    return False


def _fix_invalid_css(error_info: dict, css_dir: str) -> bool:
    """Fix invalid CSS syntax errors."""
    error_message = error_info.get("message", "")

    # Handle dangling comma selectors (like .navbar .navbar-inner ul.nav li a,)
    if "expected 1 selector or at-rule" in error_message and (".navbar" in error_message or "navbar-inn" in error_message):
        return _fix_dangling_comma_selector(error_info, css_dir)

    # Handle specific mixin parameter syntax errors
    if "fade-transition(" in error_message and "var(--element))" in error_message:
        return _fix_mixin_parameter_syntax(error_info, css_dir)

    # Handle other invalid CSS patterns
    if 'expected ")"' in error_message or 'expected "{"' in error_message:
        return _fix_parenthesis_mismatch(error_info, css_dir)

    # Fall back to commenting out the line
    return _comment_out_error_line(error_info, css_dir)


def _fix_dangling_comma_selector(error_info: dict, css_dir: str) -> bool:
    """Fix dangling comma selectors followed by comments that break SCSS compilation."""
    for file_name in os.listdir(css_dir):
        if file_name.startswith("test-") and file_name.endswith(".scss"):
            file_path = os.path.join(css_dir, file_name)

            try:
                with open(file_path) as f:
                    lines = f.readlines()

                modified = False
                for i, line in enumerate(lines):
                    # Look for lines ending with comma followed by EXCLUDED comments
                    if (
                        line.strip().endswith(",") and
                        i + 1 < len(lines) and
                        "EXCLUDED" in lines[i + 1] and
                        "RULE:" in lines[i + 1]
                    ):
                        # Remove the comma and comment out the problematic line
                        lines[i] = f"// FIXED DANGLING COMMA: {line.strip().rstrip(',')}"
                        # Also comment out the EXCLUDED comment line
                        lines[i + 1] = f"// REMOVED EXCLUSION COMMENT: {lines[i + 1].strip()}\n"
                        modified = True
                        logger.info(f"Fixed dangling comma selector in {file_name} at line {i + 1}")

                if modified:
                    with open(file_path, "w") as f:
                        f.writelines(lines)
                    return True

            except Exception as e:
                logger.warning(f"Error fixing dangling comma in {file_name}: {e}")

    return False


def _fix_mixin_parameter_syntax(error_info: dict, css_dir: str) -> bool:
    """Fix mixin parameter syntax errors like fade-transition(var(--element))."""
    for file_name in os.listdir(css_dir):
        if file_name.startswith("test-") and file_name.endswith(".scss"):
            file_path = os.path.join(css_dir, file_name)

            try:
                with open(file_path) as f:
                    content = f.read()

                # Fix fade-transition mixin with double closing parentheses
                import re

                fixed_content = re.sub(
                    r"fade-transition\(var\(--([^)]+)\)\)", r"fade-transition(var(--\1))", content
                )

                if fixed_content != content:
                    with open(file_path, "w") as f:
                        f.write(fixed_content)
                    logger.info(f"Fixed mixin parameter syntax in {file_name}")
                    return True

            except Exception as e:
                logger.warning(f"Error fixing mixin parameters in {file_name}: {e}")

    return False


def _fix_parenthesis_mismatch(error_info: dict, css_dir: str) -> bool:
    """Fix parenthesis mismatch errors."""
    for file_name in os.listdir(css_dir):
        if file_name.startswith("test-") and file_name.endswith(".scss"):
            file_path = os.path.join(css_dir, file_name)

            try:
                with open(file_path) as f:
                    lines = f.readlines()

                modified = False
                for i, line in enumerate(lines):
                    # Fix common parenthesis issues
                    if ")" in line and "(" in line:
                        # Count parentheses
                        open_count = line.count("(")
                        close_count = line.count(")")

                        if close_count > open_count:
                            # Remove extra closing parentheses
                            while close_count > open_count and ")" in line:
                                line = line.replace(")", "", 1)
                                close_count -= 1

                            lines[i] = line
                            modified = True
                            logger.info(f"Fixed parenthesis mismatch in {file_name} line {i + 1}")

                if modified:
                    with open(file_path, "w") as f:
                        f.writelines(lines)
                    return True

            except Exception as e:
                logger.warning(f"Error fixing parentheses in {file_name}: {e}")

    return False


def _comment_out_error_line(error_info: dict, css_dir: str) -> bool:
    """Comment out a problematic line of code."""
    if "file" not in error_info or "line_number" not in error_info:
        return False

    file_name = error_info["file"]
    line_number = error_info["line_number"]

    # Find the test file
    test_file_path = None
    for fname in os.listdir(css_dir):
        if fname.startswith("test-") and file_name in fname:
            test_file_path = os.path.join(css_dir, fname)
            break

    if not test_file_path or not os.path.exists(test_file_path):
        return False

    try:
        with open(test_file_path) as f:
            lines = f.readlines()

        if line_number <= len(lines):
            original_line = lines[line_number - 1]
            lines[line_number - 1] = f"// ERROR COMMENTED OUT: {original_line.strip()}\n"

            with open(test_file_path, "w") as f:
                f.writelines(lines)

            logger.info(f"Commented out problematic line {line_number} in {file_name}")
            return True

    except Exception as e:
        logger.warning(f"Error commenting out line: {e}")

    return False


def _cleanup_compilation_test_files(css_dir: str, test_files: list) -> None:
    """
    Clean up test files created during compilation testing.

    Args:
        css_dir: Path to CSS directory
        test_files: List of (test_filename, scss_path) tuples
    """
    for test_filename, _ in test_files:
        test_path = os.path.join(css_dir, test_filename)
        css_filename = test_filename.replace(".scss", ".css")
        css_path = os.path.join(css_dir, css_filename)

        # Remove test SCSS file
        if os.path.exists(test_path):
            os.remove(test_path)
            logger.info(f"Removed test file: {test_filename}")

        # Remove generated CSS file
        if os.path.exists(css_path):
            os.remove(css_path)
            logger.info(f"Removed generated CSS: {css_filename}")

    # Wait for cleanup cycle to complete
    time.sleep(1)

    # Reset any tracked changes
    try:
        subprocess.run(
            ["git", "reset", "--hard"],
            check=False,
            cwd=os.path.dirname(css_dir),
            capture_output=True,
            timeout=10,
        )
        logger.info("Reset git working directory after test cleanup")
    except Exception as e:
        logger.warning(f"Could not reset git directory: {e}")


def _comment_out_problematic_code(test_files: list, css_dir: str) -> list:
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

    # Get current Docker logs to identify specific errors
    docker_errors = _get_current_compilation_errors()

    if docker_errors:
        # Comment out lines based on actual errors
        for error in docker_errors:
            if "fade-transition" in error.get("message", ""):
                lines_commented = _comment_lines_containing(
                    test_files, css_dir, "fade-transition", "fade-transition mixin"
                )
                commented_lines.extend(lines_commented)
            elif "undefined mixin" in error.get("message", "").lower():
                mixin_name = _extract_mixin_name_from_error(error)
                if mixin_name:
                    lines_commented = _comment_lines_containing(
                        test_files,
                        css_dir,
                        f"@include {mixin_name}",
                        f"undefined mixin: {mixin_name}",
                    )
                    commented_lines.extend(lines_commented)
            elif "lighten(" in error.get("message", "") or "darken(" in error.get("message", ""):
                lines_commented = _comment_lines_containing(
                    test_files, css_dir, ["lighten(", "darken("], "SCSS color functions"
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
            lines_commented = _comment_lines_containing(test_files, css_dir, pattern, description)
            commented_lines.extend(lines_commented)
            if lines_commented:  # Stop after first successful comment
                break
    return commented_lines


def _get_current_compilation_errors():
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


def _extract_mixin_name_from_error(error):
    """Extract mixin name from error message."""
    message = error.get("message", "")
    # Look for patterns like "Undefined mixin 'fade-transition'"
    import re

    match = re.search(r"mixin['\s]+([a-zA-Z_-]+)", message)
    return match.group(1) if match else None


def _comment_lines_containing(test_files, css_dir, patterns, description):
    """Comment out lines containing specific patterns."""
    if isinstance(patterns, str):
        patterns = [patterns]

    commented_lines = []

    for test_filename, _ in test_files:
        test_file_path = os.path.join(css_dir, test_filename)

        if not os.path.exists(test_file_path):
            continue

        try:
            with open(test_file_path) as f:
                content = f.read()

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
                with open(test_file_path, "w") as f:
                    f.write("\n".join(lines))

                logger.info(f"Commented out {description} in {test_filename}")

        except Exception as e:
            logger.warning(f"Error processing {test_filename}: {e}")

    return commented_lines


def _copy_successful_test_files_to_originals(
    test_files: list, css_dir: str, theme_dir: str
) -> None:
    """
    Copy successful test files back to original locations.

    Args:
        test_files: List of (test_filename, original_path) tuples
        css_dir: CSS directory path
        theme_dir: Theme directory path
    """
    logger.info("Copying successful test files back to original locations...")

    for test_filename, _ in test_files:
        test_file_path = os.path.join(css_dir, test_filename)
        original_filename = test_filename.replace("test-", "")
        original_path = os.path.join(theme_dir, original_filename)

        if os.path.exists(test_file_path):
            try:
                shutil.copy2(test_file_path, original_path)
                logger.info(f"Copied {test_filename} back to {original_filename}")
            except Exception as e:
                logger.warning(f"Error copying {test_filename} to {original_filename}: {e}")


def _report_commented_code(commented_lines: list, slug: str) -> None:
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
        f"🔧 {len(commented_lines)} lines of code were automatically commented out to fix compilation errors:"
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
