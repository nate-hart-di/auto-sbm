"""
Core migration functionality for the SBM tool.

This module handles the main migration logic for dealer themes.
"""

import os
import time
import subprocess
import shutil
import click # Import click for interactive prompts
from ..utils.logger import logger
from ..utils.path import get_dealer_theme_dir
from ..utils.command import execute_command, execute_interactive_command
from .git import git_operations, commit_changes, push_changes # Import git functions
from .git import create_pr as git_create_pr  # Import with alias to avoid naming conflicts
from ..scss.processor import SCSSProcessor
from ..scss.validator import validate_scss_files # Import SCSS validator
from .maps import migrate_map_components
from ..oem.factory import OEMFactory


def _cleanup_snapshot_files(slug):
    """
    Remove any .sbm-snapshots directories and files before committing.
    
    Args:
        slug (str): Dealer theme slug
    """
    try:
        theme_dir = get_dealer_theme_dir(slug)
        snapshot_dir = os.path.join(theme_dir, '.sbm-snapshots')
        
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


def _create_automation_snapshots(slug):
    """
    Create snapshots of the automated migration output for comparison with manual changes.
    
    Args:
        slug (str): Dealer theme slug
    """
    try:
        theme_dir = get_dealer_theme_dir(slug)
        snapshot_dir = os.path.join(theme_dir, '.sbm-snapshots')
        
        # Create snapshot directory
        os.makedirs(snapshot_dir, exist_ok=True)
        
        # List of Site Builder files to snapshot
        sb_files = ['sb-inside.scss', 'sb-vdp.scss', 'sb-vrp.scss', 'sb-home.scss']
        
        snapshots_created = 0
        for sb_file in sb_files:
            source_path = os.path.join(theme_dir, sb_file)
            if os.path.exists(source_path):
                snapshot_path = os.path.join(snapshot_dir, f"{sb_file}.automated")
                
                # Copy the automated output to snapshot
                with open(source_path, 'r') as source:
                    content = source.read()
                
                with open(snapshot_path, 'w') as snapshot:
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


def run_just_start(slug):
    """
    Run the 'just start' command for the given slug with production database.
    Uses interactive execution to allow password prompts and user input.
    
    Args:
        slug (str): Dealer theme slug
        
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
    from ..utils.path import get_platform_dir
    platform_dir = get_platform_dir()
    
    # Run the 'just start' command interactively to allow password input
    logger.info(f"Running 'just start {slug} prod' interactively...")
    logger.warning("⚠️  You may be prompted for AWS login credentials - please respond as needed")
    
    success = execute_interactive_command(
        f"just start {slug} prod", 
        f"Failed to run 'just start {slug} prod'",
        cwd=platform_dir
    )
    
    if success:
        logger.info("'just start' command completed successfully.")
        return True
    else:
        logger.error("'just start' command failed.")
        return False


def create_sb_files(slug, force_reset=False):

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
        sb_files = ['sb-inside.scss', 'sb-vdp.scss', 'sb-vrp.scss', 'sb-home.scss']
        
        for file in sb_files:
            file_path = os.path.join(theme_dir, file)
            
            # Skip if file exists and we're not forcing reset
            if os.path.exists(file_path) and not force_reset:
                logger.info(f"File {file} already exists, skipping creation")
                continue
                
            # Create or reset the file
            with open(file_path, 'w') as f:
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
        source_scss_dir = os.path.join(theme_dir, 'css')

        if not os.path.isdir(source_scss_dir):
            logger.error(f"Source SCSS directory not found: {source_scss_dir}")
            return False

        processor = SCSSProcessor(slug)

        # Define source files - include style.scss, inside.scss, and _support-requests.scss for sb-inside
        inside_sources = [
            os.path.join(source_scss_dir, 'style.scss'),
            os.path.join(source_scss_dir, 'inside.scss'),
            os.path.join(source_scss_dir, '_support-requests.scss')
        ]
        # Only use lvdp.scss and lvrp.scss, not vdp.scss and vrp.scss
        vdp_sources = [os.path.join(source_scss_dir, 'lvdp.scss')]
        vrp_sources = [os.path.join(source_scss_dir, 'lvrp.scss')]

        # Process each category
        inside_content = "\n".join([processor.process_scss_file(f) for f in inside_sources if os.path.exists(f)])
        vdp_content = "\n".join([processor.process_scss_file(f) for f in vdp_sources if os.path.exists(f)])
        vrp_content = "\n".join([processor.process_scss_file(f) for f in vrp_sources if os.path.exists(f)])
        
        # Combine results
        results = {
            'sb-inside.scss': inside_content,
            'sb-vdp.scss': vdp_content,
            'sb-vrp.scss': vrp_content,
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


def add_predetermined_styles(slug, oem_handler=None):
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
        from ..oem.stellantis import StellantisHandler
        if not isinstance(oem_handler, StellantisHandler):
            logger.info(f"Skipping Stellantis-specific styles for non-Stellantis dealer: {slug}")
            return True
        
        # 1. Add cookie banner styles to both sb-inside.scss and sb-home.scss (directly from source file)
        # Get the auto-sbm directory path
        auto_sbm_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        cookie_banner_source = os.path.join(auto_sbm_dir, 'stellantis', 'add-to-sb-inside', 'stellantis-cookie-banner-styles.scss')
        if os.path.exists(cookie_banner_source):
            with open(cookie_banner_source, 'r') as f:
                cookie_styles = f.read()
            
            # Add to sb-inside.scss
            with open(sb_inside_path, 'r') as f:
                inside_content = f.read()
                
            if '.cookie-banner' not in inside_content:
                with open(sb_inside_path, 'a') as f:
                    f.write('\n\n/* Cookie Banner Styles */\n')
                    f.write(cookie_styles)
                logger.info("Added cookie banner styles to sb-inside.scss")
            else:
                logger.info("Cookie banner styles already exist in sb-inside.scss")
            
            # Add to sb-home.scss
            with open(sb_home_path, 'r') as f:
                home_content = f.read()
                
            if '.cookie-banner' not in home_content:
                with open(sb_home_path, 'a') as f:
                    f.write('\n\n/* Cookie Banner Styles */\n')
                    f.write(cookie_styles)
                logger.info("Added cookie banner styles to sb-home.scss")
            else:
                logger.info("Cookie banner styles already exist in sb-home.scss")
        else:
            logger.warning(f"Cookie banner source file not found: {cookie_banner_source}")
        
        # 2. Add directions row styles (directly from source file)
        directions_row_source = os.path.join(auto_sbm_dir, 'stellantis', 'add-to-sb-inside', 'stellantis-directions-row-styles.scss')
        if os.path.exists(directions_row_source):
            with open(directions_row_source, 'r') as f:
                directions_styles = f.read()
                
            # Check if directions row styles already exist
            with open(sb_inside_path, 'r') as f:
                content = f.read()
                
            if '.directions-row' not in content:
                # Append the directions styles
                with open(sb_inside_path, 'a') as f:
                    f.write('\n\n/* Directions Row Styles */\n')
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


def _check_prettier_available():
    """
    Check if prettier is available on the system.
    
    Returns:
        bool: True if prettier is available, False otherwise
    """
    try:
        # First check if prettier command exists
        success, stdout, stderr, _ = execute_command(
            "prettier --version", 
            "Checking prettier availability", 
            wait_for_completion=True
        )
        
        if success and stdout:
            # Parse version to ensure it's actually prettier
            version_output = ''.join(stdout).strip()
            if version_output and any(char.isdigit() for char in version_output):
                logger.debug(f"Prettier version detected: {version_output}")
                return True
        
        return False
    except Exception as e:
        logger.debug(f"Prettier not available: {e}")
        return False


def _format_scss_with_prettier(file_path):
    """
    Format an SCSS file with prettier if available.
    
    Args:
        file_path (str): Path to the SCSS file to format
        
    Returns:
        bool: True if formatting succeeded, False otherwise
    """
    try:
        # Use prettier to format the file in place with explicit SCSS parser
        success, stdout, stderr, _ = execute_command(
            f"prettier --write --parser scss --tab-width 2 --single-quote '{file_path}'",
            f"Failed to format {os.path.basename(file_path)} with prettier",
            wait_for_completion=True
        )
        
        if success:
            return True
        else:
            # Log stderr for debugging if formatting failed
            if stderr:
                error_msg = ''.join(stderr).strip()
                logger.debug(f"Prettier formatting error for {os.path.basename(file_path)}: {error_msg}")
            return False
            
    except Exception as e:
        logger.warning(f"Could not format {os.path.basename(file_path)} with prettier: {e}")
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
        css_dir = os.path.join(theme_dir, 'css')
        
        if not os.path.exists(css_dir):
            logger.error(f"CSS directory not found: {css_dir}")
            return False
        
        # List of Site Builder files to test
        sb_files = ['sb-inside.scss', 'sb-vdp.scss', 'sb-vrp.scss', 'sb-home.scss']
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


def reprocess_manual_changes(slug):
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
        processor = SCSSProcessor(slug)
        
        # List of Site Builder files to reprocess
        sb_files = ['sb-inside.scss', 'sb-vdp.scss', 'sb-vrp.scss', 'sb-home.scss']
        
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
                # Read the current content
                with open(file_path, 'r', encoding='utf-8') as f:
                    original_content = f.read()
                
                # Skip if file is empty
                if not original_content.strip():
                    continue
                
                # Apply the same transformations as initial migration
                processed_content = processor.transform_scss_content(original_content)
                
                # Check if any changes were made
                if processed_content != original_content:
                    # Write the processed content back with explicit flushing
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(processed_content)
                        f.flush()  # Ensure content is written to disk
                        os.fsync(f.fileno())  # Force write to disk
                    
                    changes_made = True
                    processed_files.append(sb_file)
                    
                    # Count lines for feedback
                    original_lines = len(original_content.splitlines())
                    processed_lines = len(processed_content.splitlines())
                    logger.info(f"Reprocessed {sb_file}: {original_lines} → {processed_lines} lines")
                    
                    # Format with prettier if available
                    if prettier_available:
                        if _format_scss_with_prettier(file_path):
                            logger.info(f"Formatted {sb_file} with prettier")
                        else:
                            logger.warning(f"Prettier formatting failed for {sb_file}, using default formatting")
                
                # Even if no content changes, still format with prettier if available
                elif prettier_available:
                    if _format_scss_with_prettier(file_path):
                        logger.info(f"Formatted {sb_file} with prettier (no content changes)")
        
        if changes_made:
            logger.info(f"Reprocessing completed for {slug}. Files updated: {', '.join(processed_files)}")
        else:
            logger.info(f"No reprocessing needed for {slug} - all files already properly formatted")
            
        # Summary of formatting
        if prettier_available:
            logger.info(f"Applied prettier formatting to all {len([f for f in sb_files if os.path.exists(os.path.join(theme_dir, f))])} SCSS files")
        
        # MANDATORY: Verify SCSS compilation using Docker Gulp
        if not _verify_scss_compilation_with_docker(theme_dir, slug, sb_files):
            raise Exception("SCSS compilation verification failed - files do not compile with Docker Gulp")
        
        logger.info("✅ All SCSS files verified to compile successfully with Docker Gulp")
        return True
            
    except Exception as e:
        logger.error(f"Error reprocessing manual changes for {slug}: {e}")
        return False


def run_post_migration_workflow(slug, branch_name, skip_git=False, create_pr=True, interactive_review=True, interactive_git=True, interactive_pr=True):
    """
    Run the post-migration workflow including manual review, git operations, and PR creation.
    
    Args:
        slug (str): Dealer theme slug
        branch_name (str): Git branch name
        skip_git (bool): Whether to skip git operations
        create_pr (bool): Whether to create a pull request
        interactive_review (bool): Whether to prompt for manual review
        interactive_git (bool): Whether to prompt for git operations
        interactive_pr (bool): Whether to prompt for PR creation
        
    Returns:
        bool: True if all steps are successful, False otherwise.
    """
    logger.info(f"Starting post-migration workflow for {slug} on branch {branch_name}")

    # Manual review phase
    if interactive_review:
        click.echo("\n" + "="*80)
        click.echo(f"Manual Review Required for {slug}")
        click.echo("Please review the migrated SCSS files in your theme directory:")
        click.echo(f"  - {get_dealer_theme_dir(slug)}/sb-inside.scss")
        click.echo(f"  - {get_dealer_theme_dir(slug)}/sb-vdp.scss")
        click.echo(f"  - {get_dealer_theme_dir(slug)}/sb-vrp.scss")
        click.echo(f"  - {get_dealer_theme_dir(slug)}/sb-home.scss")
        click.echo("\nVerify the content and make any necessary manual adjustments.")
        click.echo("Once you are satisfied, proceed to the next step.")
        click.echo("="*80 + "\n")

        if not click.confirm("Continue with the migration after manual review?"):
            logger.info("Post-migration workflow stopped by user after manual review.")
            return False

    # Reprocess manual changes to ensure consistency
    logger.info(f"Reprocessing manual changes for {slug} to ensure consistency...")
    if not reprocess_manual_changes(slug):
        logger.error("Failed to reprocess manual changes.")
        return False

    # Clean up snapshot files after manual review phase
    logger.info("Cleaning up automation snapshots after manual review")
    _cleanup_snapshot_files(slug)

    if not interactive_git or click.confirm(f"Commit all changes for {slug}?", default=True):
        # Clean up any snapshot files before committing - do this right before git operations
        _cleanup_snapshot_files(slug)
        
        if not commit_changes(slug):
            logger.error("Failed to commit changes.")
            return False
        
        # Clean up snapshots again after commit in case they were recreated
        _cleanup_snapshot_files(slug)
    else:
        logger.info("Skipping commit.")
        return True # End workflow if user skips commit

    if not interactive_git or click.confirm(f"Push changes to origin/{branch_name}?", default=True):
        if not push_changes(branch_name):
            logger.error("Failed to push changes.")
            return False
    else:
        logger.info("Skipping push.")
        return True # End workflow if user skips push

    if create_pr:
        if not interactive_pr or click.confirm("Create a pull request?", default=True):
            logger.info("Creating pull request...")
            try:
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


def migrate_dealer_theme(slug, skip_just=False, force_reset=False, skip_git=False, skip_maps=False, oem_handler=None, create_pr=True, interactive_review=True, interactive_git=True, interactive_pr=True):
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
        interactive_review (bool): Whether to prompt for manual review and re-validation.
        interactive_git (bool): Whether to prompt for Git add, commit, push.
        interactive_pr (bool): Whether to prompt for PR creation.
        
    Returns:
        bool: True if all steps are successful, False otherwise.
    """
    logger.info(f"Starting migration for {slug}")
    
    # Create the appropriate OEM handler for this slug if not provided
    if oem_handler is None:
        oem_handler = OEMFactory.detect_from_theme(slug)
    
    logger.info(f"Using {oem_handler} for {slug}")
    
    branch_name = None # Initialize branch_name

    # Perform Git operations if not skipped
    if not skip_git:
        logger.info(f"Step 1/6: Performing Git operations for {slug}...")
        success, branch_name = git_operations(slug)
        if not success:
            logger.error(f"Git operations failed for {slug}")
            return False
        
        logger.info(f"Git operations completed successfully, branch: {branch_name}")
    
    # Run 'just start' if not skipped
    if not skip_just:
        logger.info(f"Step 2/6: Running 'just start' for {slug}...")
        just_start_success = run_just_start(slug)
        logger.info(f"'just start' returned: {just_start_success}")
        if not just_start_success:
            logger.error(f"Failed to start site for {slug}")
            return False
        
        logger.info(f"Site started successfully for {slug}")
    
    # Create Site Builder files
    logger.info(f"Step 3/6: Creating Site Builder files for {slug}...\n")
    if not create_sb_files(slug, force_reset):
        logger.error(f"Failed to create Site Builder files for {slug}")
        return False
    
    # Migrate styles
    logger.info(f"Step 4/6: Migrating styles for {slug}...\n")
    if not migrate_styles(slug):
        logger.error(f"Failed to migrate styles for {slug}")
        return False
    
    # Add cookie banner and directions row styles as a separate step (after style migration)
    # This ensures these predetermined styles are not affected by the validators and parsers
    logger.info(f"Step 5/6: Adding predetermined styles for {slug}...\n")
    if not add_predetermined_styles(slug, oem_handler):
        logger.warning(f"Could not add all predetermined styles for {slug}")
    
    # Migrate map components if not skipped
    logger.info(f"Step 6/6: Migrating map components for {slug}...\n")
    if not skip_maps:
        if not migrate_map_components(slug, oem_handler):
            logger.error(f"Failed to migrate map components for {slug}")
            return False
        
        logger.info(f"Map components migrated successfully for {slug}")
    
    logger.info(f"Migration completed successfully for {slug}")

    # Create snapshots of the automated migration output for comparison
    _create_automation_snapshots(slug)

    # Conditionally run post-migration workflow
    if interactive_review or interactive_git or interactive_pr:
        return run_post_migration_workflow(
            slug, 
            branch_name, 
            skip_git=skip_git, 
            create_pr=create_pr, 
            interactive_review=interactive_review, 
            interactive_git=interactive_git, 
            interactive_pr=interactive_pr
        )
    
    return True


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
    css_dir = os.path.join(theme_dir, 'css')
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
        max_wait = 30  # 30 seconds max wait time
        start_time = time.time()
        compiled_files = []
        
        while (time.time() - start_time) < max_wait and len(compiled_files) < len(test_files):
            for test_filename, scss_path in test_files:
                if test_filename in compiled_files:
                    continue
                    
                # Check for corresponding CSS file
                css_filename = test_filename.replace('.scss', '.css')
                css_path = os.path.join(css_dir, css_filename)
                
                if os.path.exists(css_path):
                    compiled_files.append(test_filename)
                    logger.info(f"✅ {test_filename} compiled successfully to {css_filename}")
            
            if len(compiled_files) < len(test_files):
                time.sleep(1)
        
        # Step 4: Monitor compilation with iterative error handling
        try:
            # Attempt compilation with error handling loop
            if not _handle_compilation_with_error_recovery(css_dir, test_files, theme_dir, slug):
                logger.error("❌ SCSS compilation failed after error recovery attempts")
                return False
                
        except Exception as e:
            logger.error(f"Critical error during compilation monitoring: {e}")
            return False
        
        # Step 5: Verify compilation success
        compilation_success = len(compiled_files) == len(test_files)
        
        if compilation_success:
            logger.info(f"✅ All {len(test_files)} SCSS files compiled successfully with Docker Gulp")
        else:
            failed_files = [f for f, _ in test_files if f not in compiled_files]
            logger.error(f"❌ Docker Gulp compilation failed for: {', '.join(failed_files)}")
        
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
                    css_filename = test_filename.replace('.scss', '.css')
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
                    result = subprocess.run([
                        'docker', 'logs', '--tail', '10', 'dealerinspire_legacy_assets'
                    ], capture_output=True, text=True, timeout=5)
                    
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
            result = subprocess.run([
                'git', 'checkout', 'HEAD', 'css/'
            ], cwd=theme_dir, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                logger.info("✅ CSS directory reset to original state using git checkout")
            else:
                logger.warning(f"Git checkout of CSS directory failed: {result.stderr}")
                        
        except Exception as e:
            logger.warning(f"Error during CSS directory cleanup: {e}")


def _handle_compilation_with_error_recovery(css_dir: str, test_files: list, theme_dir: str, slug: str) -> bool:
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
            result = subprocess.run([
                'docker', 'logs', '--tail', '50', 'dealerinspire_legacy_assets'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0 and result.stdout:
                logs = result.stdout.lower()
                
                # Look for compilation success indicators
                if "finished 'sass'" in logs and "finished 'processcss'" in logs:
                    # Check if any errors in recent logs
                    if not any(error_indicator in logs for error_indicator in [
                        'error:', 'failed', 'scss compilation error', 'syntax error'
                    ]):
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
                        logger.info(f"Applied {fixes_applied} automated fixes, retrying compilation...")
                        # Prompt user about changes
                        click.echo(f"\n🔧 Applied {fixes_applied} automated SCSS fixes")
                        click.echo("Files have been automatically repaired. Retrying compilation...")
                        continue
                    else:
                        logger.warning("No automated fixes available for detected errors")
                        break
                else:
                    # No specific errors found, but compilation may still be in progress
                    logger.info("No specific errors detected, waiting for compilation...")
                    
        except subprocess.TimeoutExpired:
            logger.warning("Docker logs command timed out")
        except Exception as e:
            logger.warning(f"Error checking Docker logs: {e}")
        
        # Check for successful CSS file generation
        success_count = 0
        for test_filename, _ in test_files:
            css_filename = test_filename.replace('.scss', '.css')
            css_path = os.path.join(css_dir, css_filename)
            if os.path.exists(css_path):
                success_count += 1
        
        if success_count == len(test_files):
            logger.info("✅ All CSS files generated successfully")
            return True
        
        logger.info(f"Compilation status: {success_count}/{len(test_files)} files compiled")
    
    # Final attempt - aggressively comment out problematic code until it compiles
    logger.warning(f"❌ Compilation failed after {max_iterations} attempts, entering aggressive fix mode...")
    click.echo(f"\n🔧 Entering aggressive compilation fix mode...")
    click.echo(f"Will automatically comment out problematic code until compilation succeeds...")
    
    # Track what was commented out for user reporting
    commented_lines = []
    
    # Try up to 3 aggressive fix attempts
    for aggressive_attempt in range(1, 4):
        logger.info(f"🔧 Aggressive fix attempt {aggressive_attempt}/3")
        click.echo(f"🔧 Aggressive fix attempt {aggressive_attempt}/3")
        
        # Comment out problematic code
        attempt_comments = _comment_out_problematic_code(test_files, css_dir)
        commented_lines.extend(attempt_comments)
        
        # Wait for compilation
        time.sleep(2)
        
        # Check compilation status
        try:
            result = subprocess.run([
                'docker', 'logs', '--tail', '30', 'dealerinspire_legacy_assets'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0 and result.stdout:
                logs = result.stdout.lower()
                
                if "finished 'sass'" in logs and "finished 'processcss'" in logs:
                    if not any(error_indicator in logs for error_indicator in [
                        'error:', 'failed', 'scss compilation error', 'syntax error'
                    ]):
                        logger.info("✅ Compilation succeeded after aggressive fixes")
                        click.echo("✅ Compilation succeeded after aggressive fixes")
                        
                        # Copy successful test files back to originals
                        _copy_successful_test_files_to_originals(test_files, css_dir, theme_dir)
                        
                        # Report what was commented out
                        _report_commented_code(commented_lines, slug)
                        
                        return True
                
                # Parse new errors for next iteration
                new_errors = _parse_compilation_errors(logs, test_files)
                if new_errors:
                    logger.info(f"Found {len(new_errors)} new errors, continuing aggressive fixes...")
                else:
                    logger.warning("No specific errors found but compilation still failing")
        
        except Exception as e:
            logger.warning(f"Error checking compilation status: {e}")
    
    logger.error("❌ Compilation still failing after all aggressive fix attempts")
    click.echo("❌ Compilation still failing after all aggressive fix attempts")
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
        {
            'pattern': r'error.*?([^/\s]+\.s?css):(\d+):(\d+):?\s*(.+)',
            'type': 'syntax_error'
        },
        {
            'pattern': r'undefined variable.*?\$([a-zA-Z_][a-zA-Z0-9_-]*)',
            'type': 'undefined_variable'
        },
        {
            'pattern': r'undefined mixin.*?([a-zA-Z_][a-zA-Z0-9_-]*)',
            'type': 'undefined_mixin'
        },
        {
            'pattern': r'invalid css.*?after.*?"([^"]*)"',
            'type': 'invalid_css'
        }
    ]
    
    lines = logs.split('\n')
    
    for line in lines:
        for pattern_info in error_patterns:
            import re
            match = re.search(pattern_info['pattern'], line, re.IGNORECASE)
            if match:
                error = {
                    'type': pattern_info['type'],
                    'line_content': line.strip(),
                    'match_groups': match.groups(),
                    'original_line': line
                }
                
                # Extract file information if available
                if len(match.groups()) >= 3 and match.group(1) and match.group(2):
                    error['file'] = match.group(1)
                    error['line_number'] = int(match.group(2))
                    if len(match.groups()) >= 4:
                        error['error_message'] = match.group(4)
                
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
    error_type = error_info.get('type')
    
    try:
        if error_type == 'undefined_variable':
            return _fix_undefined_variable(error_info, css_dir)
        
        elif error_type == 'undefined_mixin':
            return _fix_undefined_mixin(error_info, css_dir)
        
        elif error_type == 'syntax_error':
            return _fix_syntax_error(error_info, css_dir)
        
        elif error_type == 'invalid_css':
            return _fix_invalid_css(error_info, css_dir)
        
        else:
            logger.info(f"No automated fix available for error type: {error_type}")
            return False
            
    except Exception as e:
        logger.warning(f"Error applying fix for {error_type}: {e}")
        return False


def _fix_undefined_variable(error_info: dict, css_dir: str) -> bool:
    """Fix undefined SCSS variables by replacing with CSS variables or commenting out."""
    variable_name = error_info['match_groups'][0] if error_info['match_groups'] else None
    
    if not variable_name:
        return False
    
    logger.info(f"Attempting to fix undefined variable: ${variable_name}")
    
    # Find test files in CSS directory and apply fix
    for file_name in os.listdir(css_dir):
        if file_name.startswith('test-') and file_name.endswith('.scss'):
            file_path = os.path.join(css_dir, file_name)
            
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                
                # Replace undefined variable with CSS variable equivalent
                original_content = content
                content = content.replace(f'${variable_name}', f'var(--{variable_name})')
                
                if content != original_content:
                    with open(file_path, 'w') as f:
                        f.write(content)
                    
                    logger.info(f"Fixed undefined variable ${variable_name} in {file_name}")
                    return True
                    
            except Exception as e:
                logger.warning(f"Error fixing variable in {file_name}: {e}")
    
    return False


def _fix_undefined_mixin(error_info: dict, css_dir: str) -> bool:
    """Fix undefined mixins by commenting them out."""
    if 'match_groups' not in error_info or not error_info['match_groups']:
        return False
    
    mixin_name = error_info['match_groups'][0]
    logger.info(f"Attempting to fix undefined mixin: {mixin_name}")
    
    # Find and comment out mixin usage
    for file_name in os.listdir(css_dir):
        if file_name.startswith('test-') and file_name.endswith('.scss'):
            file_path = os.path.join(css_dir, file_name)
            
            try:
                with open(file_path, 'r') as f:
                    lines = f.readlines()
                
                modified = False
                for i, line in enumerate(lines):
                    if f'@include {mixin_name}' in line:
                        lines[i] = f'// COMMENTED OUT: {line.strip()}\n'
                        modified = True
                        logger.info(f"Commented out mixin usage: {mixin_name}")
                
                if modified:
                    with open(file_path, 'w') as f:
                        f.writelines(lines)
                    return True
                    
            except Exception as e:
                logger.warning(f"Error fixing mixin in {file_name}: {e}")
    
    return False


def _fix_syntax_error(error_info: dict, css_dir: str) -> bool:
    """Fix common SCSS syntax errors."""
    if 'file' not in error_info or 'line_number' not in error_info:
        return False
    
    file_name = error_info['file']
    line_number = error_info['line_number']
    
    # Find the test file
    test_file_path = None
    for fname in os.listdir(css_dir):
        if fname.startswith('test-') and file_name in fname:
            test_file_path = os.path.join(css_dir, fname)
            break
    
    if not test_file_path or not os.path.exists(test_file_path):
        return False
    
    try:
        with open(test_file_path, 'r') as f:
            lines = f.readlines()
        
        if line_number <= len(lines):
            problematic_line = lines[line_number - 1]
            
            # Common syntax fixes
            fixed_line = problematic_line
            
            # Fix missing semicolons
            if not problematic_line.strip().endswith((';', '{', '}')) and ':' in problematic_line:
                fixed_line = problematic_line.rstrip() + ';\n'
            
            # Fix lighten/darken functions with CSS variables
            import re
            fixed_line = re.sub(r'(lighten|darken)\(var\([^)]+\),\s*\d+%\)', 
                              lambda m: 'var(--primary)', fixed_line)
            
            if fixed_line != problematic_line:
                lines[line_number - 1] = fixed_line
                
                with open(test_file_path, 'w') as f:
                    f.writelines(lines)
                
                logger.info(f"Applied syntax fix at line {line_number} in {file_name}")
                return True
                
    except Exception as e:
        logger.warning(f"Error applying syntax fix: {e}")
    
    return False


def _fix_invalid_css(error_info: dict, css_dir: str) -> bool:
    """Fix invalid CSS syntax errors."""
    error_message = error_info.get('message', '')
    
    # Handle specific mixin parameter syntax errors
    if 'fade-transition(' in error_message and 'var(--element))' in error_message:
        return _fix_mixin_parameter_syntax(error_info, css_dir)
    
    # Handle other invalid CSS patterns
    if 'expected ")"' in error_message or 'expected "{"' in error_message:
        return _fix_parenthesis_mismatch(error_info, css_dir)
    
    # Fall back to commenting out the line
    return _comment_out_error_line(error_info, css_dir)


def _fix_mixin_parameter_syntax(error_info: dict, css_dir: str) -> bool:
    """Fix mixin parameter syntax errors like fade-transition(var(--element))."""
    for file_name in os.listdir(css_dir):
        if file_name.startswith('test-') and file_name.endswith('.scss'):
            file_path = os.path.join(css_dir, file_name)
            
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                
                # Fix fade-transition mixin with double closing parentheses
                import re
                fixed_content = re.sub(
                    r'fade-transition\(var\(--([^)]+)\)\)',
                    r'fade-transition(var(--\1))',
                    content
                )
                
                if fixed_content != content:
                    with open(file_path, 'w') as f:
                        f.write(fixed_content)
                    logger.info(f"Fixed mixin parameter syntax in {file_name}")
                    return True
                    
            except Exception as e:
                logger.warning(f"Error fixing mixin parameters in {file_name}: {e}")
    
    return False


def _fix_parenthesis_mismatch(error_info: dict, css_dir: str) -> bool:
    """Fix parenthesis mismatch errors."""
    for file_name in os.listdir(css_dir):
        if file_name.startswith('test-') and file_name.endswith('.scss'):
            file_path = os.path.join(css_dir, file_name)
            
            try:
                with open(file_path, 'r') as f:
                    lines = f.readlines()
                
                modified = False
                for i, line in enumerate(lines):
                    # Fix common parenthesis issues
                    if ')' in line and '(' in line:
                        # Count parentheses
                        open_count = line.count('(')
                        close_count = line.count(')')
                        
                        if close_count > open_count:
                            # Remove extra closing parentheses
                            while close_count > open_count and ')' in line:
                                line = line.replace(')', '', 1)
                                close_count -= 1
                            
                            lines[i] = line
                            modified = True
                            logger.info(f"Fixed parenthesis mismatch in {file_name} line {i+1}")
                
                if modified:
                    with open(file_path, 'w') as f:
                        f.writelines(lines)
                    return True
                    
            except Exception as e:
                logger.warning(f"Error fixing parentheses in {file_name}: {e}")
    
    return False


def _comment_out_error_line(error_info: dict, css_dir: str) -> bool:
    """Comment out a problematic line of code."""
    if 'file' not in error_info or 'line_number' not in error_info:
        return False
    
    file_name = error_info['file']
    line_number = error_info['line_number']
    
    # Find the test file
    test_file_path = None
    for fname in os.listdir(css_dir):
        if fname.startswith('test-') and file_name in fname:
            test_file_path = os.path.join(css_dir, fname)
            break
    
    if not test_file_path or not os.path.exists(test_file_path):
        return False
    
    try:
        with open(test_file_path, 'r') as f:
            lines = f.readlines()
        
        if line_number <= len(lines):
            original_line = lines[line_number - 1]
            lines[line_number - 1] = f'// ERROR COMMENTED OUT: {original_line.strip()}\n'
            
            with open(test_file_path, 'w') as f:
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
        css_filename = test_filename.replace('.scss', '.css')
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
        subprocess.run(['git', 'reset', '--hard'], 
                      cwd=os.path.dirname(css_dir), 
                      capture_output=True, 
                      timeout=10)
        logger.info("Reset git working directory after test cleanup")
    except Exception as e:
        logger.warning(f"Could not reset git directory: {e}")


def _comment_out_problematic_code(test_files: list, css_dir: str) -> list:
    """
    Comment out all potentially problematic SCSS code as a last resort.
    
    Args:
        test_files: List of test files
        css_dir: CSS directory path
        
    Returns:
        list: List of commented out lines with file info
    """
    logger.warning("Commenting out potentially problematic SCSS code...")
    
    commented_lines = []
    
    # Target specific problematic patterns we've seen
    problematic_patterns = [
        (r'@mixin\s+fade-transition\([^)]*var\([^)]*\)[^)]*\)', 'malformed fade-transition mixin definition'),
        (r'@include\s+fade-transition\([^)]*\)', 'fade-transition mixin call'),
        (r'@mixin\s+[a-zA-Z_][a-zA-Z0-9_-]*\([^)]*var\([^)]*\)[^)]*\)', 'mixin definition with CSS variables'),
        (r'@include\s+[a-zA-Z_][a-zA-Z0-9_-]*\([^)]*var\([^)]*\)[^)]*\)', 'mixin call with CSS variables'),
        (r'lighten\([^)]+\)', 'lighten function'),
        (r'darken\([^)]+\)', 'darken function'),
        (r'@include\s+[a-zA-Z_][a-zA-Z0-9_-]*\([^)]*\)', 'unknown mixin call'),
        (r'\$[a-zA-Z_][a-zA-Z0-9_-]*', 'SCSS variable usage'),
    ]
    
    for test_filename, _ in test_files:
        test_file_path = os.path.join(css_dir, test_filename)
        
        if not os.path.exists(test_file_path):
            continue
            
        try:
            with open(test_file_path, 'r') as f:
                content = f.read()
            
            lines = content.split('\n')
            modified = False
            
            for i, line in enumerate(lines):
                if line.strip().startswith('//'):
                    continue  # Skip already commented lines
                    
                for pattern, description in problematic_patterns:
                    import re
                    if re.search(pattern, line):
                        original_line = line.strip()
                        lines[i] = f'// COMMENTED OUT: {line}'
                        modified = True
                        
                        # Track what was commented out
                        commented_lines.append({
                            'file': test_filename.replace('test-', ''),
                            'line': original_line,
                            'reason': description
                        })
                        
                        logger.info(f"Commented out {description} in {test_filename}: {original_line}")
                        break
            
            if modified:
                with open(test_file_path, 'w') as f:
                    f.write('\n'.join(lines))
                
                logger.info(f"Commented out problematic code in {test_filename}")
            else:
                logger.warning(f"No problematic patterns found to comment in {test_filename}")
                
        except Exception as e:
            logger.warning(f"Error processing {test_filename}: {e}")
    
    return commented_lines


def _copy_successful_test_files_to_originals(test_files: list, css_dir: str, theme_dir: str) -> None:
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
        original_filename = test_filename.replace('test-', '')
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
    click.echo(f"✅ SCSS files now compile successfully!")
    click.echo(f"🔧 {len(commented_lines)} lines of code were automatically commented out to fix compilation errors:")
    click.echo()
    
    # Group by file
    by_file = {}
    for item in commented_lines:
        if item['file'] not in by_file:
            by_file[item['file']] = []
        by_file[item['file']].append(item)
    
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
