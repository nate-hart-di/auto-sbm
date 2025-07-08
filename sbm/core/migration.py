"""
Core migration functionality for the SBM tool.

This module handles the main migration logic for dealer themes.
"""

import os
import time
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
        sb_files = ['sb-inside.scss', 'sb-vdp.scss', 'sb-vrp.scss']
        
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
    3. Processes the main SCSS files (style.scss, inside.scss, lvdp.scss, lvrp.scss).
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

        # Define source files - include both style.scss and inside.scss for sb-inside
        inside_sources = [
            os.path.join(source_scss_dir, 'style.scss'),
            os.path.join(source_scss_dir, 'inside.scss')
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
        
        # Path to the sb-inside.scss file
        sb_inside_path = os.path.join(theme_dir, "sb-inside.scss")
        
        if not os.path.exists(sb_inside_path):
            logger.warning(f"sb-inside.scss not found for {slug}")
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
        
        # 1. Add cookie banner styles (directly from source file)
        # Get the auto-sbm directory path
        auto_sbm_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        cookie_banner_source = os.path.join(auto_sbm_dir, 'stellantis', 'add-to-sb-inside', 'stellantis-cookie-banner-styles.scss')
        if os.path.exists(cookie_banner_source):
            with open(cookie_banner_source, 'r') as f:
                cookie_styles = f.read()
                
            # Check if cookie banner styles already exist
            with open(sb_inside_path, 'r') as f:
                content = f.read()
                
            if '.cookie-banner' not in content:
                # Append the cookie styles
                with open(sb_inside_path, 'a') as f:
                    f.write('\n\n/* Cookie Banner Styles */\n')
                    f.write(cookie_styles)
                logger.info("Added cookie banner styles")
            else:
                logger.info("Cookie banner styles already exist")
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
