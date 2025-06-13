"""
Core migration functionality for SBM Tool V2.

This module provides the main migration function that orchestrates
the complete dealer theme migration process based on real Stellantis SBM patterns.
"""

from typing import Dict, Any, Optional
from pathlib import Path
import time

from sbm.config import get_config
from sbm.utils.logger import get_logger
from sbm.utils.errors import SBMError, ValidationError, MigrationError


def migrate_dealer_theme(
    slug: str,
    environment: str = "prod",
    dry_run: bool = False,
    force: bool = False,
    config_override: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Migrate a dealer theme using the Site Builder Migration process.
    
    This is the main entry point for theme migration. It orchestrates
    the complete process including validation, OEM detection, Git operations,
    site initialization, SCSS processing, and final validation.
    
    Based on analysis of 20+ real Stellantis SBM PRs, this process:
    1. Validates the theme and detects OEM
    2. Creates appropriate Git branch
    3. Processes SCSS files (sb-inside.scss, sb-vdp.scss, sb-vrp.scss)
    4. Adds map components and preserves existing styles
    5. Validates the migration results
    
    Args:
        slug: Dealer theme slug (e.g., 'chryslerofportland')
        environment: Target environment ('prod', 'staging', 'dev')
        dry_run: If True, perform validation only without making changes
        force: If True, continue migration despite validation warnings
        config_override: Optional configuration overrides
        
    Returns:
        Dictionary containing migration results:
        {
            'success': bool,
            'slug': str,
            'environment': str,
            'dry_run': bool,
            'force_mode': bool,
            'duration': float,
            'oem': str,
            'brand': str,
            'files_created': List[str],
            'files_modified': List[str],
            'styles_migrated': int,
            'map_components_added': bool,
            'branch_name': str,
            'steps_completed': List[str],
            'validation_results': Dict[str, Any],
            'errors': List[str],
            'warnings': List[str]
        }
        
    Raises:
        ValidationError: If theme validation fails and force=False
        MigrationError: If migration process fails
        ConfigurationError: If configuration is invalid
        SBMError: For other migration-related errors
    """
    logger = get_logger("migration")
    start_time = time.time()
    
    try:
        # Load configuration
        config = get_config()
        if config_override:
            # Apply any configuration overrides
            for key, value in config_override.items():
                if hasattr(config, key):
                    setattr(config, key, value)
        
        logger.info(f"Starting SBM migration for dealer theme: {slug}")
        logger.info(f"Environment: {environment}, Dry run: {dry_run}, Force: {force}")
        
        # Initialize result tracking
        result = {
            "success": False,
            "slug": slug,
            "environment": environment,
            "dry_run": dry_run,
            "force_mode": force,
            "duration": 0.0,
            "oem": None,
            "brand": None,
            "files_created": [],
            "files_modified": [],
            "styles_migrated": 0,
            "map_components_added": False,
            "branch_name": None,
            "steps_completed": [],
            "validation_results": {},
            "errors": [],
            "warnings": []
        }
        
        # Step 1: Validate theme and detect OEM
        logger.info("Step 1: Validating theme and detecting OEM")
        try:
            from sbm.core.validation import ValidationEngine
            from sbm.oem.factory import OEMFactory
            
            validator = ValidationEngine(config)
            validation_results = validator.validate_theme(slug)
            result["validation_results"] = validation_results
            result["steps_completed"].append("validation")
            
            # Detect OEM
            oem_handler = OEMFactory.create_handler(slug, config)
            oem_info = oem_handler.detect_oem(slug)
            result["oem"] = oem_info.get("oem", "Unknown")
            result["brand"] = oem_info.get("brand", "Unknown")
            result["steps_completed"].append("oem_detection")
            
            logger.info(f"Theme validated. OEM: {result['oem']}, Brand: {result['brand']}")
            
        except Exception as e:
            error_msg = f"Validation/OEM detection failed: {str(e)}"
            result["errors"].append(error_msg)
            if not force:
                raise ValidationError(error_msg, slug=slug)
            else:
                result["warnings"].append(f"Continuing despite validation error: {error_msg}")
        
        # Step 2: Git operations (if not dry run)
        if not dry_run:
            logger.info("Step 2: Setting up Git branch")
            try:
                from sbm.core.git_operations import GitOperations
                
                git_ops = GitOperations(config)
                branch_info = git_ops.create_migration_branch(slug)
                result["branch_name"] = branch_info.get("branch_name")
                result["steps_completed"].append("git_setup")
                
                logger.info(f"Git branch created: {result['branch_name']}")
                
            except Exception as e:
                error_msg = f"Git operations failed: {str(e)}"
                result["errors"].append(error_msg)
                if not force:
                    raise MigrationError(error_msg, slug=slug, step="git_setup")
                else:
                    result["warnings"].append(f"Continuing despite git error: {error_msg}")
        
        # Step 3: SCSS Processing (main migration work)
        logger.info("Step 3: Processing SCSS files using real SBM patterns")
        try:
            from sbm.scss.processor import SCSSProcessor
            
            scss_processor = SCSSProcessor(config)
            scss_results = scss_processor.process_theme(slug)
            
            # Merge SCSS results into main result
            result["files_created"].extend(scss_results.get("files_created", []))
            result["files_modified"].extend(scss_results.get("files_modified", []))
            result["styles_migrated"] = len(scss_results.get("legacy_styles_preserved", []))
            result["map_components_added"] = scss_results.get("map_components_added", False)
            result["steps_completed"].append("scss_processing")
            
            logger.info(f"SCSS processing completed. Files created: {len(result['files_created'])}, "
                       f"Files modified: {len(result['files_modified'])}")
            
        except Exception as e:
            error_msg = f"SCSS processing failed: {str(e)}"
            result["errors"].append(error_msg)
            raise MigrationError(error_msg, slug=slug, step="scss_processing")
        
        # Step 4: Site initialization (if not dry run)
        if not dry_run:
            logger.info("Step 4: Initializing site builder components")
            try:
                from sbm.core.site_initializer import SiteInitializer
                
                site_init = SiteInitializer(config)
                init_results = site_init.initialize_site_builder(slug)
                result["steps_completed"].append("site_initialization")
                
                logger.info("Site builder initialization completed")
                
            except Exception as e:
                error_msg = f"Site initialization failed: {str(e)}"
                result["errors"].append(error_msg)
                if not force:
                    raise MigrationError(error_msg, slug=slug, step="site_initialization")
                else:
                    result["warnings"].append(f"Continuing despite initialization error: {error_msg}")
        
        # Step 5: Final validation
        logger.info("Step 5: Final validation")
        try:
            final_validation = validator.validate_migration_results(slug, result)
            result["validation_results"]["final"] = final_validation
            result["steps_completed"].append("final_validation")
            
        except Exception as e:
            warning_msg = f"Final validation warning: {str(e)}"
            result["warnings"].append(warning_msg)
            logger.warning(warning_msg)
        
        # Calculate duration and mark success
        result["duration"] = time.time() - start_time
        result["success"] = len(result["errors"]) == 0
        
        if result["success"]:
            logger.info(f"SBM migration completed successfully for {slug} in {result['duration']:.2f}s")
        else:
            logger.error(f"SBM migration failed for {slug}. Errors: {result['errors']}")
        
        return result
        
    except ValidationError as e:
        logger.error(f"Validation failed for {slug}: {e}")
        result["duration"] = time.time() - start_time
        result["errors"].append(str(e))
        return result
    except MigrationError as e:
        logger.error(f"Migration failed for {slug}: {e}")
        result["duration"] = time.time() - start_time
        result["errors"].append(str(e))
        return result
    except Exception as e:
        logger.error(f"Unexpected error during migration of {slug}: {e}")
        result["duration"] = time.time() - start_time
        result["errors"].append(f"Unexpected error: {str(e)}")
        return result


def validate_dealer_theme(slug: str) -> Dict[str, Any]:
    """
    Validate a dealer theme without performing migration.
    
    Args:
        slug: Dealer theme slug
        
    Returns:
        Validation results dictionary
        
    Raises:
        ValidationError: If validation fails
    """
    logger = get_logger("validation")
    
    try:
        config = get_config()
        
        # Import here to avoid circular imports
        from sbm.core.validation import ValidationEngine
        
        validator = ValidationEngine(config)
        results = validator.validate_theme(slug)
        
        logger.info(f"Validation completed for {slug}")
        return results
        
    except Exception as e:
        logger.error(f"Validation error for {slug}: {e}")
        raise ValidationError(f"Theme validation failed: {str(e)}", slug=slug)


def get_migration_status(slug: str) -> Dict[str, Any]:
    """
    Get the current migration status for a dealer theme.
    
    Args:
        slug: Dealer theme slug
        
    Returns:
        Status information dictionary
    """
    logger = get_logger("status")
    
    try:
        config = get_config()
        theme_path = config.get_theme_path(slug)
        
        if not theme_path.exists():
            return {
                "exists": False,
                "slug": slug,
                "message": "Theme not found"
            }
        
        # Check for Site Builder files
        sb_files = [
            "sb-home.scss",
            "sb-vdp.scss", 
            "sb-vrp.scss",
            "sb-inside.scss"
        ]
        
        sb_files_present = []
        for sb_file in sb_files:
            if (theme_path / sb_file).exists():
                sb_files_present.append(sb_file)
        
        # Check for legacy files
        legacy_files = ["lvdp.scss", "lvrp.scss"]
        legacy_files_present = []
        for legacy_file in legacy_files:
            if (theme_path / legacy_file).exists():
                legacy_files_present.append(legacy_file)
        
        # Determine migration status
        if sb_files_present and not legacy_files_present:
            status = "migrated"
        elif sb_files_present and legacy_files_present:
            status = "partial"
        elif legacy_files_present:
            status = "legacy"
        else:
            status = "unknown"
        
        return {
            "exists": True,
            "slug": slug,
            "status": status,
            "sb_files": sb_files_present,
            "legacy_files": legacy_files_present,
            "theme_path": str(theme_path)
        }
        
    except Exception as e:
        logger.error(f"Error getting status for {slug}: {e}")
        return {
            "exists": False,
            "slug": slug,
            "error": str(e)
        }


def list_available_themes() -> Dict[str, Any]:
    """
    List all available dealer themes in the platform.
    
    Returns:
        Dictionary with theme information
    """
    logger = get_logger("themes")
    
    try:
        config = get_config()
        themes_dir = config.dealer_themes_dir
        
        if not themes_dir.exists():
            return {
                "success": False,
                "error": f"Dealer themes directory not found: {themes_dir}"
            }
        
        themes = []
        for theme_path in themes_dir.iterdir():
            if theme_path.is_dir() and not theme_path.name.startswith('.'):
                status = get_migration_status(theme_path.name)
                themes.append({
                    "slug": theme_path.name,
                    "status": status.get("status", "unknown"),
                    "sb_files_count": len(status.get("sb_files", [])),
                    "legacy_files_count": len(status.get("legacy_files", []))
                })
        
        # Sort themes by slug
        themes.sort(key=lambda x: x["slug"])
        
        return {
            "success": True,
            "total_themes": len(themes),
            "themes": themes,
            "themes_dir": str(themes_dir)
        }
        
    except Exception as e:
        logger.error(f"Error listing themes: {e}")
        return {
            "success": False,
            "error": str(e)
        } 
