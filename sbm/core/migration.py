
"""
Core migration functionality for the SBM tool.

This module handles the main migration logic for dealer themes.
"""

import os
import time
import click # Import click for interactive prompts
from ..utils.logger import logger
from ..utils.path import get_dealer_theme_dir
from ..utils.command import execute_command, execute_interactive_command, format_scss_with_prettier
from .git import git_operations, commit_changes, push_changes, create_pull_request # Import new git functions
from ..scss.processor import SCSSProcessor
from ..scss.validator import validate_scss_files # Import SCSS validator
from .maps import migrate_map_components
from ..oem.factory import OEMFactory


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
    3. Processes the main SCSS files (style.scss, lvdp.scss, lvrp.scss).
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

        # Define source files
        inside_sources = [os.path.join(source_scss_dir, 'style.scss')]
        vdp_sources = [os.path.join(source_scss_dir, 'lvdp.scss'), os.path.join(source_scss_dir, 'vdp.scss')]
        vrp_sources = [os.path.join(source_scss_dir, 'lvrp.scss'), os.path.join(source_scss_dir, 'vrp.scss')]

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
        
        # 1. Add cookie banner styles (directly from source file)
        cookie_banner_source = os.path.join(os.getcwd(), 'stellantis', 'add-to-sb-inside', 'stellantis-cookie-banner-styles.scss')
        if os.path.exists(cookie_banner_source):
            with open(cookie_banner_source, 'r') as f:
                cookie_styles = f.read()
                
            # Check if cookie banner styles already exist
            with open(sb_inside_path, 'r') as f:
                content = f.read()
                
            if '.cookie-banner' not in content:
                # Append the cookie styles
                with open(sb_inside_path, 'a') as f:
                    f.write("\n\n" + cookie_styles)
                
                logger.info(f"Added cookie banner styles to sb-inside.scss for {slug}")
            else:
                logger.info(f"Cookie banner styles already exist in sb-inside.scss for {slug}")
        else:
            logger.warning(f"Cookie banner styles source file not found at {cookie_banner_source}")
        
        # 2. Add directions row styles using OEM handler
        # Check if directions row styles already exist
        with open(sb_inside_path, 'r') as f:
            content = f.read()
        
        if '#mapRow' not in content and '#directionsBox' not in content:
            # Get directions styles from OEM handler
            directions_styles = oem_handler.get_directions_styles()
            
            # Append the directions styles
            with open(sb_inside_path, 'a') as f:
                f.write("\n\n" + directions_styles)
            
            logger.info(f"Added directions row styles to sb-inside.scss for {slug}")
        else:
            logger.info("Directions row styles already exist in sb-inside.scss")
        
        return True
        
    except Exception as e:
        logger.error(f"Error adding predetermined styles: {e}")
        return False


def run_post_migration_workflow(slug, branch_name, skip_git=False, create_pr=False, interactive_review=True, interactive_git=True, interactive_pr=True):
    """
    Runs the interactive post-migration workflow steps.
    
    Args:
        slug (str): Dealer theme slug.
        branch_name (str): The Git branch name created for the migration.
        skip_git (bool): Whether to skip Git operations (add, commit, push).
        create_pr (bool): Whether to create a GitHub Pull Request after successful post-migration steps.
        interactive_review (bool): Whether to prompt for manual review and re-validation.
        interactive_git (bool): Whether to prompt for Git add, commit, push.
        interactive_pr (bool): Whether to prompt for PR creation.
        
    Returns:
        bool: True if successful, False otherwise.
    """
    
    # --- Interactive Break for Manual Review ---
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

        # --- Re-validation after Manual Review ---
        logger.info(f"Re-validating SCSS files for {slug} after manual review...")
        if not validate_scss_files(slug):
            click.echo("\n" + "="*80)
            click.echo(f"SCSS re-validation failed for {slug}.")
            click.echo("Please address the validation errors manually.")
            click.echo("="*80 + "\n")
            if not click.confirm("Continue despite SCSS validation errors? (Not recommended)"):
                logger.info("Post-migration workflow stopped by user due to SCSS validation errors.")
                return False
        else:
            logger.info(f"SCSS re-validation passed for {slug}.")

    # --- Prompt for Git Add, Commit, Push ---
    if interactive_git and not skip_git and branch_name:
        click.echo("\n" + "="*80)
        click.echo(f"Next Step: Git Operations (Add, Commit, Push)")
        click.echo(f"This will add changes, commit to branch '{branch_name}', and push to origin.")
        click.echo("="*80 + "\n")
        if click.confirm("Proceed with Git add, commit, and push to remote branch?"):
            if not commit_changes(slug):
                logger.error(f"Failed to commit changes for {slug}.")
                return False
            if not push_changes(branch_name):
                logger.error(f"Failed to push changes for {slug}.")
                return False
            logger.info(f"Changes successfully added, committed, and pushed for {slug}.")
        else:
            logger.info("Git operations skipped by user.")
            return False
    elif interactive_git and not skip_git and not branch_name:
        logger.warning("Skipping Git operations: No branch name available (perhaps git_operations was skipped or failed earlier).")
    elif not interactive_git:
        logger.info("Git operations skipped due to interactive_git=False.")
    else:
        logger.info("Git operations skipped due to --skip-git flag.")

    # --- Prompt for PR Generation ---
    if interactive_pr and create_pr and branch_name:
        click.echo("\n" + "="*80)
        click.echo(f"Next Step: Create Pull Request")
        click.echo(f"This will create a draft PR for branch '{branch_name}'.")
        click.echo("="*80 + "\n")
        if click.confirm("Proceed with creating a Pull Request?"):
            pr_title = f"SBM: Migrate {slug} to Site Builder format"
            pr_body = f"This PR migrates the {slug} theme to the Site Builder format.\n\n" \
                      f"**What:**\n- Converted SCSS to Site Builder compatible format.\n- Added predetermined styles for cookie banner and directions row.\n\n" \
                      f"**Why:**\n- To enable the theme to be used with the new Site Builder platform.\n\n" \
                      f"**Review Instructions:**\n- Review the changes in the Files Changed tab.\n- Verify the site loads correctly on the new platform."
            
            pr_url = create_pull_request(pr_title, pr_body, "main", branch_name, reviewers="carsdotcom/fe-dev", labels="fe-dev")
            if pr_url:
                logger.info(f"Pull Request created successfully: {pr_url}")
                click.echo(f"Pull Request created: {pr_url}")
            else:
                logger.error(f"Failed to create Pull Request for {slug}.")
        else:
            logger.info("Pull Request creation skipped by user.")
    elif interactive_pr and create_pr and not branch_name:
        logger.warning("Skipping PR creation: No branch name available (perhaps git_operations was skipped or failed earlier).")
    elif not interactive_pr:
        logger.info("PR creation skipped due to interactive_pr=False.")
    else:
        logger.info("PR creation skipped (no --create-pr flag).")

    return True


def migrate_dealer_theme(slug, skip_just=False, force_reset=False, skip_git=False, skip_maps=False, oem_handler=None, create_pr=False, interactive_review=True, interactive_git=True, interactive_pr=True):
    """
    Migrate a dealer theme to the Site Builder platform.
    
    Args:
        slug (str): Dealer theme slug
        skip_just (bool): Whether to skip the 'just start' command
        force_reset (bool): Whether to reset existing Site Builder files
        skip_git (bool): Whether to skip Git operations
        skip_maps (bool): Whether to skip map components migration
        oem_handler (BaseOEMHandler, optional): Manually specified OEM handler
        create_pr (bool): Whether to create a GitHub Pull Request after successful migration.
        interactive_review (bool): Whether to prompt for manual review and re-validation.
        interactive_git (bool): Whether to prompt for Git add, commit, push.
        interactive_pr (bool): Whether to prompt for PR creation.
        
    Returns:
        bool: True if successful, False otherwise
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
