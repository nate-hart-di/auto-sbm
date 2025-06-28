"""
Core migration functionality for the SBM tool.

This module handles the main migration logic for dealer themes.
"""

import os
import time
from ..utils.logger import logger
from ..utils.path import get_dealer_theme_dir
from ..utils.command import execute_command, format_scss_with_prettier
from .git import git_operations
from ..scss.processor import SCSSProcessor
from .maps import migrate_map_components
from ..oem.factory import OEMFactory


def run_just_start(slug):
    """
    Run the 'just start' command for the given slug with production database.
    
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
    
    # Run the 'just start' command in the background
    logger.info(f"Running 'just start {slug} prod' in background. Waiting for platform to be ready...")
    success, stdout_lines, stderr_lines, process = execute_command(
        f"just start {slug} prod", 
        f"Failed to run 'just start {slug} prod'",
        wait_for_completion=False
    )
    
    if not success or process is None:
        logger.error("Failed to start 'just start' process.")
        return False

    # Wait for the "Welcome to the DI Website Platform!" message with a timeout
    timeout = 180  # 3 minutes timeout
    start_time = time.time()
    platform_ready = False

    while time.time() - start_time < timeout:
        output = "\n".join(stdout_lines)
        if "Welcome to the DI Website Platform!" in output:
            platform_ready = True
            break
        time.sleep(5)  # Check every 5 seconds

    if platform_ready:
        logger.info("'just start' command completed and platform is ready.")
        return True
    else:
        logger.error("'just start' command did not indicate successful platform startup within timeout.")
        logger.error("Last 20 lines of stdout:")
        for line in stdout_lines[-20:]:
            logger.error(f"  {line.strip()}")
        logger.error("Last 20 lines of stderr:")
        for line in stderr_lines[-20:]:
            logger.error(f"  {line.strip()}")
        
        # Terminate the background process if it's still running
        if process.poll() is None:
            logger.info("Terminating 'just start' background process.")
            process.terminate()
            process.wait()
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


def migrate_dealer_theme(slug, skip_just=False, force_reset=False, skip_git=False, skip_maps=False, oem_handler=None, create_pr=False):
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
    logger.info(f"Step 3/6: Creating Site Builder files for {slug}...")
    if not create_sb_files(slug, force_reset):
        logger.error(f"Failed to create Site Builder files for {slug}")
        return False
    
    # Migrate styles
    logger.info(f"Step 4/6: Migrating styles for {slug}...")
    if not migrate_styles(slug):
        logger.error(f"Failed to migrate styles for {slug}")
        return False
    
    # Add cookie banner and directions row styles as a separate step (after style migration)
    # This ensures these predetermined styles are not affected by the validators and parsers
    logger.info(f"Step 5/6: Adding predetermined styles for {slug}...")
    if not add_predetermined_styles(slug, oem_handler):
        logger.warning(f"Could not add all predetermined styles for {slug}")
    
    # Migrate map components if not skipped
    logger.info(f"Step 6/6: Migrating map components for {slug}...")
    if not skip_maps:
        if not migrate_map_components(slug, oem_handler):
            logger.error(f"Failed to migrate map components for {slug}")
            return False
        
        logger.info(f"Map components migrated successfully for {slug}")
    
    logger.info(f"Migration completed successfully for {slug}")

    # Create PR if requested and Git operations were performed
    if create_pr and branch_name:
        logger.info(f"Creating Pull Request for {slug} on branch {branch_name}...")
        from .git import create_pull_request # Import here to avoid circular dependency
        pr_title = f"SBM: Migrate {slug} to Site Builder format"
        pr_body = f"This PR migrates the {slug} theme to the Site Builder format.\n\n" \
                  f"**What:**\n- Converted SCSS to Site Builder compatible format.\n- Added predetermined styles for cookie banner and directions row.\n\n" \
                  f"**Why:**\n- To enable the theme to be used with the new Site Builder platform.\n\n" \
                  f"**Review Instructions:**\n- Review the changes in the Files Changed tab.\n- Verify the site loads correctly on the new platform."
        
        # Assuming 'main' is the base branch, adjust if needed
        pr_url = create_pull_request(pr_title, pr_body, "main", branch_name, reviewers="carsdotcom/fe-dev", labels="fe-dev")
        if pr_url:
            logger.info(f"Pull Request created successfully: {pr_url}")
        else:
            logger.error(f"Failed to create Pull Request for {slug}.")

    return True


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
