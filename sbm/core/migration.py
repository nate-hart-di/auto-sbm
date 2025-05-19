"""
Core migration functionality for the SBM tool.

This module handles the main migration logic for dealer themes.
"""

import os
from ..utils.logger import logger
from ..utils.path import get_dealer_theme_dir
from ..utils.command import execute_command
from .git import git_operations
from ..scss.parser import extract_styles
from ..scss.transformer import transform_scss
from ..scss.validator import validate_scss_syntax
from .maps import migrate_map_components


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
    if not execute_command("which just", "'just' command not found"):
        logger.error("Please install 'just' or ensure it's in your PATH.")
        return False
    
    # Run the 'just start' command with 'prod' parameter to pull production database
    if not execute_command(f"just start {slug} prod", 
                          f"Failed to run 'just start {slug} prod'"):
        return False
    
    return True


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


def migrate_styles(slug):
    """
    Migrate styles from source files to Site Builder files.
    
    Args:
        slug (str): Dealer theme slug
        
    Returns:
        bool: True if successful, False otherwise
    """
    logger.info(f"Migrating styles for {slug}")
    
    try:
        theme_dir = get_dealer_theme_dir(slug)
        
        # Extract styles from source files
        styles = extract_styles(slug, theme_dir)
        
        if not styles:
            logger.error(f"No styles extracted for {slug}")
            return False
        
        # Process and write each style file
        for file_name, content in styles.items():
            if not content.strip():
                logger.warning(f"No content for {file_name}, skipping")
                continue
            
            # Transform SCSS content
            transformed = transform_scss(content, slug)
            
            # Write the transformed content to the Site Builder file
            file_path = os.path.join(theme_dir, file_name)
            with open(file_path, 'w') as f:
                f.write(transformed)
            
            logger.info(f"Wrote {len(transformed.splitlines())} lines to {file_name}")
            
            # Validate the syntax
            validate_scss_syntax(file_path)
        
        return True
        
    except Exception as e:
        logger.error(f"Error migrating styles: {e}")
        return False


def migrate_dealer_theme(slug, skip_just=False, force_reset=False, skip_git=False, skip_maps=False):
    """
    Migrate a dealer theme to the Site Builder platform.
    
    Args:
        slug (str): Dealer theme slug
        skip_just (bool): Whether to skip the 'just start' command
        force_reset (bool): Whether to reset existing Site Builder files
        skip_git (bool): Whether to skip Git operations
        skip_maps (bool): Whether to skip map components migration
        
    Returns:
        bool: True if successful, False otherwise
    """
    logger.info(f"Starting migration for {slug}")
    
    # Perform Git operations if not skipped
    if not skip_git:
        success, branch_name = git_operations(slug)
        if not success:
            logger.error(f"Git operations failed for {slug}")
            return False
        
        logger.info(f"Git operations completed successfully, branch: {branch_name}")
    
    # Run 'just start' if not skipped
    if not skip_just:
        if not run_just_start(slug):
            logger.error(f"Failed to start site for {slug}")
            return False
        
        logger.info(f"Site started successfully for {slug}")
    
    # Create Site Builder files
    if not create_sb_files(slug, force_reset):
        logger.error(f"Failed to create Site Builder files for {slug}")
        return False
    
    # Migrate styles
    if not migrate_styles(slug):
        logger.error(f"Failed to migrate styles for {slug}")
        return False
    
    # Add cookie banner and directions row styles as a separate step (after style migration)
    # This ensures these predetermined styles are not affected by the validators and parsers
    if not add_predetermined_styles(slug):
        logger.warning(f"Could not add all predetermined styles for {slug}")
    
    # Migrate map components if not skipped
    if not skip_maps:
        if not migrate_map_components(slug):
            logger.error(f"Failed to migrate map components for {slug}")
            return False
        
        logger.info(f"Map components migrated successfully for {slug}")
    
    logger.info(f"Migration completed successfully for {slug}")
    return True


def add_predetermined_styles(slug):
    """
    Add predetermined styles like cookie banner and directions row.
    This function adds these styles directly without any parsing or transformation.
    
    Args:
        slug (str): Dealer theme slug
        
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
        
        # 2. Add directions row styles (directly from source file)
        directions_row_source = os.path.join(os.getcwd(), 'stellantis', 'add-to-sb-inside', 'stellantis-directions-row-styles.scss')
        if os.path.exists(directions_row_source):
            with open(directions_row_source, 'r') as f:
                directions_styles = f.read()
                
            # Check if directions row styles already exist
            with open(sb_inside_path, 'r') as f:
                content = f.read()
                
            if '#mapRow' not in content and '#directionsBox' not in content:
                # Append the directions styles
                with open(sb_inside_path, 'a') as f:
                    f.write("\n\n" + directions_styles)
                
                logger.info(f"Added directions row styles to sb-inside.scss for {slug}")
            else:
                logger.info(f"Directions row styles already exist in sb-inside.scss for {slug}")
        else:
            # If directions file not found, use the styles from the add_directions_row_styles function
            directions_styles = """
/* MAP ROW **************************************************/
#mapRow {
  position: relative;
  .mapwrap {
    height: 600px;
  }
}
#map-canvas {
  height: 100%;
}
/* DIRECTIONS BOX **************************************************/
#directionsBox {
  padding: 50px 0;
  text-align: left;
  width: 400px;
  position: absolute;
  top: 200px;
  left: 50px;
  background: #fff;
  text-align: left;
  color: #111;
  font-family: "Lato", sans-serif;
  .getdirectionstext {
    display: inline-block;
    font-size: 24px;
    margin: 0;
  }
  .locationtext {
    text-transform: uppercase;
    font-weight: 700;
    margin-bottom: 20px;
  }
  .address {
    margin-bottom: 20px;
  }
}
@media (max-width: 920px) {
  #mapRow {
    .mapwrap {
      height: 250px;
    }
    #directionsBox {
      width: unset;
      height: 100%;
      top: 0;
      left: 0;
      padding: 20px;
      max-width: 45%;
    }
  }
}"""
            
            # Check if directions row styles already exist
            with open(sb_inside_path, 'r') as f:
                content = f.read()
                
            if '#mapRow' not in content and '#directionsBox' not in content:
                # Append the directions styles
                with open(sb_inside_path, 'a') as f:
                    f.write("\n\n" + directions_styles)
                
                logger.info(f"Added directions row styles to sb-inside.scss for {slug} (using default styles)")
            else:
                logger.info(f"Directions row styles already exist in sb-inside.scss for {slug}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error adding predetermined styles: {e}")
        return False 
