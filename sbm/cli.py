"""
Command-line interface for the SBM tool.

This module provides the command-line interface for the SBM tool.
"""

import argparse
import sys
import os
from .utils.logger import setup_logger, logger
from .utils.helpers import validate_slug


def parse_args():
    """
    Parse command-line arguments.
    
    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Site Builder Migration Tool - Automate dealer website migrations to the Site Builder platform."
    )
    
    parser.add_argument("slugs", nargs="*", help="Dealer theme slugs to migrate")
    
    parser.add_argument(
        "--platform-dir",
        help="Path to the DI Websites Platform directory (overrides DI_WEBSITES_PLATFORM_DIR env var)"
    )
    
    parser.add_argument(
        "--skip-just",
        action="store_true",
        help="Skip the 'just start' command (use if the site is already started)"
    )
    
    parser.add_argument(
        "--force-reset",
        action="store_true",
        help="Force reset the Site Builder files if they already exist"
    )
    
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate SCSS syntax without running the full migration"
    )
    
    parser.add_argument(
        "--skip-git",
        action="store_true",
        help="Skip Git operations (checkout, branch creation)"
    )
    
    parser.add_argument(
        "--skip-maps",
        action="store_true",
        help="Skip map components migration"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    return parser.parse_args()


def validate_args(args):
    """
    Validate command-line arguments.
    
    Args:
        args (argparse.Namespace): Parsed arguments
        
    Returns:
        bool: True if valid, False otherwise
    """
    # If platform directory is provided, set it as an environment variable
    if args.platform_dir:
        os.environ["DI_WEBSITES_PLATFORM_DIR"] = args.platform_dir
    
    # Check if DI_WEBSITES_PLATFORM_DIR is set
    if not os.environ.get("DI_WEBSITES_PLATFORM_DIR"):
        logger.error("DI_WEBSITES_PLATFORM_DIR environment variable is not set.")
        logger.error("Please set it or provide --platform-dir on the command line.")
        return False
    
    # Check if the platform directory exists
    platform_dir = os.environ.get("DI_WEBSITES_PLATFORM_DIR")
    if not os.path.isdir(platform_dir):
        logger.error(f"Platform directory not found: {platform_dir}")
        return False
    
    # In validate-only mode, we need at least one slug
    if args.validate_only and not args.slugs:
        logger.error("At least one slug is required with --validate-only")
        return False
    
    # If not validate-only and no slugs, show help
    if not args.validate_only and not args.slugs:
        logger.error("At least one slug is required")
        return False
    
    # Validate each slug
    for slug in args.slugs:
        if not validate_slug(slug):
            logger.error(f"Invalid slug: {slug}")
            logger.error("Slugs can only contain letters, numbers, dashes, underscores, and slashes.")
            return False
    
    return True


def main():
    """
    Main entry point for the SBM tool.
    """
    # Parse arguments
    args = parse_args()
    
    # Set up logger with appropriate verbosity
    log_level = "DEBUG" if args.verbose else "INFO"
    logger = setup_logger(level=log_level)
    
    # Validate arguments
    if not validate_args(args):
        return 1
    
    logger.info("Site Builder Migration Tool - Starting migration process")
    
    # If validate-only mode, just validate SCSS files
    if args.validate_only:
        from .scss.validator import validate_scss_syntax
        
        success = True
        for slug in args.slugs:
            # Get the site builder files
            from .utils.path import get_dealer_theme_dir
            
            try:
                theme_dir = get_dealer_theme_dir(slug)
                
                # Validate sb-inside.scss
                inside_file = os.path.join(theme_dir, "sb-inside.scss")
                if os.path.exists(inside_file):
                    logger.info(f"Validating {inside_file}")
                    if not validate_scss_syntax(inside_file):
                        success = False
                
                # Validate sb-home.scss
                home_file = os.path.join(theme_dir, "sb-home.scss")
                if os.path.exists(home_file):
                    logger.info(f"Validating {home_file}")
                    if not validate_scss_syntax(home_file):
                        success = False
                
                # Validate sb-vdp.scss
                vdp_file = os.path.join(theme_dir, "sb-vdp.scss")
                if os.path.exists(vdp_file):
                    logger.info(f"Validating {vdp_file}")
                    if not validate_scss_syntax(vdp_file):
                        success = False
                
                # Validate sb-vrp.scss
                vrp_file = os.path.join(theme_dir, "sb-vrp.scss")
                if os.path.exists(vrp_file):
                    logger.info(f"Validating {vrp_file}")
                    if not validate_scss_syntax(vrp_file):
                        success = False
            
            except Exception as e:
                logger.error(f"Error validating {slug}: {e}")
                success = False
        
        return 0 if success else 1
    
    # Process each slug
    success = True
    for slug in args.slugs:
        logger.info(f"Processing {slug}")
        
        try:
            # Import here to avoid circular dependencies
            from .core.migration import migrate_dealer_theme
            
            # Migrate the dealer theme
            if not migrate_dealer_theme(
                slug, 
                skip_just=args.skip_just, 
                force_reset=args.force_reset,
                skip_git=args.skip_git,
                skip_maps=args.skip_maps
            ):
                success = False
        
        except Exception as e:
            logger.error(f"Error migrating {slug}: {e}")
            success = False
    
    logger.info("Migration process complete")
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main()) 
