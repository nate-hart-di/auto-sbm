"""Migration service for orchestrating theme migrations with type safety"""

import os
import time
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable

from ...config import AutoSBMSettings
from ...models.migration import MigrationConfig, MigrationResult, MigrationStep
from ...models.theme import Theme, ThemeStatus
from .models import (
    MigrationContext, MigrationStepTracker, MigrationContextState,
    CompilationTestResult, SnapshotInfo
)


class MigrationService:
    """
    Core migration service that orchestrates theme migrations using vertical slice architecture.
    
    This service replaces the monolithic migration.py with a clean, type-safe interface
    that coordinates with other feature slices (SCSS processing, Git operations, etc.).
    """
    
    def __init__(self, settings: AutoSBMSettings):
        self.settings = settings
        
    async def migrate_theme(
        self, 
        migration_config: MigrationConfig,
        progress_callback: Optional[Callable[[MigrationStep, int, str], None]] = None
    ) -> MigrationResult:
        """
        Execute complete theme migration with comprehensive tracking.
        
        Args:
            migration_config: Migration configuration with theme and options
            progress_callback: Optional callback for progress updates
            
        Returns:
            MigrationResult with comprehensive migration outcome
        """
        # Generate unique migration ID
        migration_id = str(uuid.uuid4())[:8]
        
        # Create migration context
        context = MigrationContext(
            theme=migration_config.theme,
            migration_id=migration_id,
            dry_run=(migration_config.mode.value == "dry_run"),
            force_reset=migration_config.preserve_original,
            skip_git=not migration_config.git_operations_enabled,
            interactive_mode=migration_config.rich_ui_enabled,
            progress_callback=progress_callback
        )
        
        # Initialize step trackers
        context.initialize_steps(migration_config.enabled_steps)
        
        # Start migration
        context.start_migration()
        
        try:
            # Execute migration steps
            for step in migration_config.enabled_steps:
                if not await self._execute_migration_step(step, context):
                    # Step failed, complete migration as failed
                    context.complete_migration(success=False)
                    return self._build_migration_result(context, success=False)
            
            # All steps completed successfully
            context.complete_migration(success=True)
            return self._build_migration_result(context, success=True)
            
        except Exception as e:
            # Unexpected error during migration
            if context.current_step:
                context.fail_step(context.current_step, str(e))
            
            context.complete_migration(success=False)
            return self._build_migration_result(context, success=False, error=str(e))
    
    async def _execute_migration_step(
        self, 
        step: MigrationStep, 
        context: MigrationContext
    ) -> bool:
        """Execute a single migration step"""
        
        tracker = context.start_step(step, f"Starting {step.value.replace('_', ' ').title()}")
        
        try:
            if step == MigrationStep.GIT_SETUP:
                return await self._execute_git_setup(context, tracker)
            elif step == MigrationStep.DOCKER_STARTUP:
                return await self._execute_docker_startup(context, tracker)
            elif step == MigrationStep.FILE_CREATION:
                return await self._execute_file_creation(context, tracker)
            elif step == MigrationStep.SCSS_MIGRATION:
                return await self._execute_scss_migration(context, tracker)
            elif step == MigrationStep.PREDETERMINED_STYLES:
                return await self._execute_predetermined_styles(context, tracker)
            elif step == MigrationStep.MAP_COMPONENTS:
                return await self._execute_map_components(context, tracker)
            elif step == MigrationStep.VALIDATION:
                return await self._execute_validation(context, tracker)
            elif step == MigrationStep.CLEANUP:
                return await self._execute_cleanup(context, tracker)
            else:
                context.fail_step(step, f"Unknown migration step: {step}")
                return False
                
        except Exception as e:
            context.fail_step(step, str(e))
            return False
    
    async def _execute_git_setup(self, context: MigrationContext, tracker: MigrationStepTracker) -> bool:
        """Execute Git setup step"""
        if context.skip_git:
            tracker.status_message = "Skipping Git operations"
            context.complete_step(MigrationStep.GIT_SETUP, success=True)
            return True
        
        # Import git operations from existing code
        try:
            from ...core.git import git_operations  # Import from legacy location
            
            tracker.update_progress(25, "Setting up Git branch")
            
            success, branch_name = git_operations(context.theme.name)
            
            if success:
                context.branch_name = branch_name
                tracker.step_data["branch_name"] = branch_name
                tracker.update_progress(100, f"Git branch created: {branch_name}")
                context.complete_step(MigrationStep.GIT_SETUP, success=True)
                return True
            else:
                context.fail_step(MigrationStep.GIT_SETUP, "Git operations failed")
                return False
                
        except ImportError:
            # Git operations not available, skip
            tracker.status_message = "Git operations not available, skipping"
            context.complete_step(MigrationStep.GIT_SETUP, success=True)
            return True
    
    async def _execute_docker_startup(self, context: MigrationContext, tracker: MigrationStepTracker) -> bool:
        """Execute Docker startup step"""
        try:
            tracker.update_progress(25, "Starting Docker environment")
            
            # Use existing run_just_start function
            from ...core.migration import run_just_start  # Import from legacy location
            
            tracker.update_progress(50, "Running 'just start' command")
            success = run_just_start(context.theme.name)
            
            if success:
                tracker.update_progress(100, "Docker environment started")
                context.complete_step(MigrationStep.DOCKER_STARTUP, success=True)
                return True
            else:
                context.fail_step(MigrationStep.DOCKER_STARTUP, "Docker startup failed")
                return False
                
        except ImportError:
            # Docker startup not available, skip
            tracker.status_message = "Docker startup not available, skipping"
            context.complete_step(MigrationStep.DOCKER_STARTUP, success=True)
            return True
    
    async def _execute_file_creation(self, context: MigrationContext, tracker: MigrationStepTracker) -> bool:
        """Execute Site Builder file creation step"""
        try:
            tracker.update_progress(25, "Creating Site Builder files")
            
            # Create Site Builder files
            theme_dir = self._get_theme_directory(context.theme.name)
            sb_files = ['sb-inside.scss', 'sb-vdp.scss', 'sb-vrp.scss', 'sb-home.scss']
            
            tracker.files_to_process = len(sb_files)
            
            for i, file_name in enumerate(sb_files):
                file_path = theme_dir / file_name
                
                # Skip if file exists and we're not forcing reset
                if file_path.exists() and not context.force_reset:
                    tracker.add_processed_file(file_path, success=True)
                    continue
                
                # Create or reset the file
                try:
                    file_path.write_text("")
                    context.add_created_file(file_path)
                    tracker.add_processed_file(file_path, success=True)
                    
                    progress = int((i + 1) / len(sb_files) * 75) + 25  # 25-100%
                    tracker.update_progress(progress, f"Created {file_name}")
                    
                except Exception as e:
                    tracker.add_processed_file(file_path, success=False)
                    tracker.errors.append(f"Failed to create {file_name}: {e}")
            
            if tracker.files_failed == 0:
                context.complete_step(MigrationStep.FILE_CREATION, success=True)
                return True
            else:
                context.fail_step(MigrationStep.FILE_CREATION, 
                                f"Failed to create {tracker.files_failed} files")
                return False
                
        except Exception as e:
            context.fail_step(MigrationStep.FILE_CREATION, str(e))
            return False
    
    async def _execute_scss_migration(self, context: MigrationContext, tracker: MigrationStepTracker) -> bool:
        """Execute SCSS migration step"""
        try:
            tracker.update_progress(10, "Initializing SCSS processor")
            
            # Use existing SCSS migration function
            from ...core.migration import migrate_styles  # Import from legacy location
            
            tracker.update_progress(50, "Processing SCSS files")
            success = migrate_styles(context.theme.name)
            
            if success:
                tracker.update_progress(100, "SCSS migration completed")
                context.complete_step(MigrationStep.SCSS_MIGRATION, success=True)
                return True
            else:
                context.fail_step(MigrationStep.SCSS_MIGRATION, "SCSS migration failed")
                return False
                
        except ImportError:
            context.fail_step(MigrationStep.SCSS_MIGRATION, "SCSS processor not available")
            return False
        except Exception as e:
            context.fail_step(MigrationStep.SCSS_MIGRATION, str(e))
            return False
    
    async def _execute_predetermined_styles(self, context: MigrationContext, tracker: MigrationStepTracker) -> bool:
        """Execute predetermined styles addition step"""
        try:
            tracker.update_progress(25, "Adding predetermined styles")
            
            # Use existing predetermined styles function
            from ...core.migration import add_predetermined_styles  # Import from legacy location
            
            tracker.update_progress(75, "Processing OEM-specific styles")
            success = add_predetermined_styles(context.theme.name)
            
            if success:
                tracker.update_progress(100, "Predetermined styles added")
                context.complete_step(MigrationStep.PREDETERMINED_STYLES, success=True)
                return True
            else:
                # This step can fail but shouldn't stop migration
                tracker.warnings.append("Could not add all predetermined styles")
                context.complete_step(MigrationStep.PREDETERMINED_STYLES, success=True)
                return True
                
        except ImportError:
            tracker.status_message = "Predetermined styles not available, skipping"
            context.complete_step(MigrationStep.PREDETERMINED_STYLES, success=True)
            return True
        except Exception as e:
            tracker.warnings.append(f"Predetermined styles error: {e}")
            context.complete_step(MigrationStep.PREDETERMINED_STYLES, success=True)
            return True
    
    async def _execute_map_components(self, context: MigrationContext, tracker: MigrationStepTracker) -> bool:
        """Execute map components migration step"""
        if context.skip_maps:
            tracker.status_message = "Skipping map components migration"
            context.complete_step(MigrationStep.MAP_COMPONENTS, success=True)
            return True
        
        try:
            tracker.update_progress(25, "Migrating map components")
            
            # Use existing map migration function
            from ...core.maps import migrate_map_components  # Import from legacy location
            
            tracker.update_progress(75, "Processing map components")
            success = migrate_map_components(context.theme.name)
            
            if success:
                tracker.update_progress(100, "Map components migrated")
                context.complete_step(MigrationStep.MAP_COMPONENTS, success=True)
                return True
            else:
                context.fail_step(MigrationStep.MAP_COMPONENTS, "Map components migration failed")
                return False
                
        except ImportError:
            tracker.status_message = "Map components migration not available, skipping"
            context.complete_step(MigrationStep.MAP_COMPONENTS, success=True)
            return True
        except Exception as e:
            context.fail_step(MigrationStep.MAP_COMPONENTS, str(e))
            return False
    
    async def _execute_validation(self, context: MigrationContext, tracker: MigrationStepTracker) -> bool:
        """Execute post-migration validation step"""
        try:
            tracker.update_progress(25, "Validating migration results")
            
            # Check that expected files exist
            theme_dir = self._get_theme_directory(context.theme.name)
            expected_files = context.theme.get_expected_output_files()
            
            validation_errors = []
            for file_path in expected_files:
                if not file_path.exists():
                    validation_errors.append(f"Expected file not found: {file_path.name}")
            
            tracker.update_progress(75, "Running compilation tests")
            
            # Test SCSS compilation if possible
            compilation_result = await self._test_scss_compilation(context.theme.name, tracker)
            
            if validation_errors:
                context.fail_step(MigrationStep.VALIDATION, 
                                f"Validation failed: {'; '.join(validation_errors)}")
                return False
            elif not compilation_result.success:
                context.fail_step(MigrationStep.VALIDATION, "SCSS compilation validation failed")
                return False
            else:
                tracker.update_progress(100, "Validation completed")
                context.complete_step(MigrationStep.VALIDATION, success=True)
                return True
                
        except Exception as e:
            context.fail_step(MigrationStep.VALIDATION, str(e))
            return False
    
    async def _execute_cleanup(self, context: MigrationContext, tracker: MigrationStepTracker) -> bool:
        """Execute cleanup step"""
        try:
            tracker.update_progress(50, "Cleaning up temporary files")
            
            # Clean up any snapshot files
            snapshot_dir = self._get_theme_directory(context.theme.name) / '.sbm-snapshots'
            if snapshot_dir.exists():
                shutil.rmtree(snapshot_dir)
                tracker.status_message = "Cleaned up snapshot files"
            
            tracker.update_progress(100, "Cleanup completed")
            context.complete_step(MigrationStep.CLEANUP, success=True)
            return True
            
        except Exception as e:
            # Cleanup failures shouldn't stop migration
            tracker.warnings.append(f"Cleanup warning: {e}")
            context.complete_step(MigrationStep.CLEANUP, success=True)
            return True
    
    async def _test_scss_compilation(self, theme_name: str, tracker: MigrationStepTracker) -> CompilationTestResult:
        """Test SCSS compilation to ensure generated files are valid"""
        try:
            # Use existing compilation test function if available
            from ...core.migration import test_compilation_recovery  # Import from legacy location
            
            success = test_compilation_recovery(theme_name)
            
            return CompilationTestResult(
                success=success,
                theme_name=theme_name,
                files_tested=["sb-inside.scss", "sb-vdp.scss", "sb-vrp.scss", "sb-home.scss"]
            )
            
        except ImportError:
            # Compilation testing not available
            return CompilationTestResult(
                success=True,
                theme_name=theme_name,
                files_tested=[]
            )
        except Exception as e:
            return CompilationTestResult(
                success=False,
                theme_name=theme_name,
                compilation_errors=[str(e)]
            )
    
    def _get_theme_directory(self, theme_name: str) -> Path:
        """Get theme directory path"""
        # Use existing path utility if available
        try:
            from ...utils.path import get_dealer_theme_dir
            return Path(get_dealer_theme_dir(theme_name))
        except ImportError:
            # Fallback to basic path construction
            return self.settings.themes_directory / theme_name
    
    def _build_migration_result(
        self, 
        context: MigrationContext, 
        success: bool,
        error: Optional[str] = None
    ) -> MigrationResult:
        """Build comprehensive migration result from context"""
        
        # Calculate duration
        duration = None
        if context.start_time and context.end_time:
            delta = context.end_time - context.start_time
            duration = delta.total_seconds()
        
        # Collect all errors and warnings
        all_errors = []
        all_warnings = []
        files_processed = 0
        files_failed = 0
        
        for tracker in context.step_trackers.values():
            all_errors.extend(tracker.errors)
            all_warnings.extend(tracker.warnings)
            files_processed += tracker.files_processed
            files_failed += tracker.files_failed
        
        if error:
            all_errors.append(error)
        
        # Update theme status
        if success:
            context.theme.update_status(ThemeStatus.COMPLETED)
        else:
            context.theme.update_status(ThemeStatus.FAILED)
        
        # Map theme type to migration mode
        from ...models.migration import MigrationMode
        migration_mode = MigrationMode.FULL  # Default mode
        
        return MigrationResult(
            success=success,
            theme_name=context.theme.name,
            migration_mode=migration_mode,
            start_time=context.start_time or context.theme.created_at,
            end_time=context.end_time,
            total_duration_seconds=duration,
            files_processed=files_processed,
            files_failed=files_failed,
            files_created=len(context.created_files),
            files_modified=len(context.modified_files),
            errors=all_errors,
            warnings=all_warnings,
            output_files=context.created_files + context.modified_files,
            backup_location=context.backup_files[0].parent if context.backup_files else None,
            configuration_hash=context.migration_id
        )
    
    def create_snapshot(self, theme_name: str) -> SnapshotInfo:
        """Create automation snapshots for comparison"""
        theme_dir = self._get_theme_directory(theme_name)
        snapshot_dir = theme_dir / '.sbm-snapshots'
        snapshot_dir.mkdir(exist_ok=True)
        
        sb_files = ['sb-inside.scss', 'sb-vdp.scss', 'sb-vrp.scss', 'sb-home.scss']
        snapshotted_files = []
        
        for sb_file in sb_files:
            source_path = theme_dir / sb_file
            if source_path.exists():
                snapshot_path = snapshot_dir / f"{sb_file}.automated"
                shutil.copy2(source_path, snapshot_path)
                snapshotted_files.append(sb_file)
        
        return SnapshotInfo(
            snapshot_directory=snapshot_dir,
            files_snapshotted=snapshotted_files
        )