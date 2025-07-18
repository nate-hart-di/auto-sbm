"""Migration-specific models and data structures"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from pathlib import Path
from datetime import datetime
from enum import Enum

from ...models.migration import MigrationStep, MigrationResult
from ...models.theme import Theme


class MigrationContextState(str, Enum):
    """Migration context states"""
    INITIALIZED = "initialized"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MigrationStepTracker(BaseModel):
    """Track individual migration step progress and metadata"""
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    step: MigrationStep
    state: MigrationContextState = MigrationContextState.INITIALIZED
    progress_percentage: int = Field(default=0, ge=0, le=100)
    status_message: str = Field(default="", description="Current status message")
    
    # Timing
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    
    # File processing stats
    files_to_process: int = Field(default=0, ge=0)
    files_processed: int = Field(default=0, ge=0)
    files_failed: int = Field(default=0, ge=0)
    
    # Step-specific data
    step_data: Dict[str, Any] = Field(default_factory=dict)
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    
    def start(self) -> None:
        """Mark step as started"""
        self.state = MigrationContextState.RUNNING
        self.start_time = datetime.now()
        self.progress_percentage = 0
    
    def update_progress(self, percentage: int, message: str = "") -> None:
        """Update step progress"""
        self.progress_percentage = max(0, min(100, percentage))
        if message:
            self.status_message = message
    
    def add_processed_file(self, file_path: Path, success: bool = True) -> None:
        """Record a processed file"""
        self.files_processed += 1
        if not success:
            self.files_failed += 1
    
    def complete(self, success: bool = True) -> None:
        """Mark step as completed"""
        self.end_time = datetime.now()
        self.state = MigrationContextState.COMPLETED if success else MigrationContextState.FAILED
        self.progress_percentage = 100 if success else self.progress_percentage
        
        if self.end_time and self.start_time:
            delta = self.end_time - self.start_time
            self.duration_seconds = delta.total_seconds()
    
    def fail(self, error_message: str) -> None:
        """Mark step as failed"""
        self.state = MigrationContextState.FAILED
        self.errors.append(error_message)
        self.complete(success=False)


class MigrationContext(BaseModel):
    """Comprehensive migration context for tracking and coordination"""
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    # Core migration info
    theme: Theme
    migration_id: str = Field(description="Unique migration identifier")
    
    # Git context
    branch_name: Optional[str] = None
    original_branch: Optional[str] = None
    
    # Step tracking
    step_trackers: Dict[MigrationStep, MigrationStepTracker] = Field(default_factory=dict)
    current_step: Optional[MigrationStep] = None
    
    # Overall state
    state: MigrationContextState = MigrationContextState.INITIALIZED
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    # Flags and options
    dry_run: bool = Field(default=False)
    force_reset: bool = Field(default=False)
    skip_git: bool = Field(default=False)
    skip_maps: bool = Field(default=False)
    interactive_mode: bool = Field(default=True)
    
    # File tracking
    created_files: List[Path] = Field(default_factory=list)
    modified_files: List[Path] = Field(default_factory=list)
    backup_files: List[Path] = Field(default_factory=list)
    
    # Processing results
    overall_result: Optional[MigrationResult] = None
    
    # Progress callbacks
    progress_callback: Optional[Any] = Field(default=None, exclude=True)
    
    def initialize_steps(self, enabled_steps: List[MigrationStep]) -> None:
        """Initialize step trackers for enabled steps"""
        for step in enabled_steps:
            self.step_trackers[step] = MigrationStepTracker(step=step)
    
    def start_migration(self) -> None:
        """Start the migration process"""
        self.state = MigrationContextState.RUNNING
        self.start_time = datetime.now()
    
    def start_step(self, step: MigrationStep, message: str = "") -> MigrationStepTracker:
        """Start a specific migration step"""
        if step not in self.step_trackers:
            self.step_trackers[step] = MigrationStepTracker(step=step)
        
        self.current_step = step
        tracker = self.step_trackers[step]
        tracker.start()
        
        if message:
            tracker.status_message = message
        
        # Call progress callback if available
        if self.progress_callback:
            try:
                self.progress_callback(step, 0, message)
            except Exception:
                pass  # Don't fail migration due to callback issues
        
        return tracker
    
    def update_step_progress(self, step: MigrationStep, percentage: int, message: str = "") -> None:
        """Update progress for a specific step"""
        if step in self.step_trackers:
            self.step_trackers[step].update_progress(percentage, message)
            
            # Call progress callback if available
            if self.progress_callback:
                try:
                    self.progress_callback(step, percentage, message)
                except Exception:
                    pass
    
    def complete_step(self, step: MigrationStep, success: bool = True) -> None:
        """Complete a specific migration step"""
        if step in self.step_trackers:
            self.step_trackers[step].complete(success)
            
            # Call progress callback if available
            if self.progress_callback:
                try:
                    self.progress_callback(step, 100 if success else -1, 
                                         "Completed" if success else "Failed")
                except Exception:
                    pass
        
        # Clear current step if it matches
        if self.current_step == step:
            self.current_step = None
    
    def fail_step(self, step: MigrationStep, error_message: str) -> None:
        """Fail a specific migration step"""
        if step in self.step_trackers:
            self.step_trackers[step].fail(error_message)
        
        # Call progress callback if available
        if self.progress_callback:
            try:
                self.progress_callback(step, -1, f"Failed: {error_message}")
            except Exception:
                pass
    
    def complete_migration(self, success: bool = True) -> None:
        """Complete the entire migration"""
        self.end_time = datetime.now()
        self.state = MigrationContextState.COMPLETED if success else MigrationContextState.FAILED
        self.current_step = None
    
    def get_overall_progress(self) -> float:
        """Get overall migration progress (0.0 to 1.0)"""
        if not self.step_trackers:
            return 0.0
        
        total_progress = sum(tracker.progress_percentage for tracker in self.step_trackers.values())
        return total_progress / (len(self.step_trackers) * 100)
    
    def get_completed_steps(self) -> List[MigrationStep]:
        """Get list of completed steps"""
        return [
            step for step, tracker in self.step_trackers.items() 
            if tracker.state == MigrationContextState.COMPLETED
        ]
    
    def get_failed_steps(self) -> List[MigrationStep]:
        """Get list of failed steps"""
        return [
            step for step, tracker in self.step_trackers.items() 
            if tracker.state == MigrationContextState.FAILED
        ]
    
    def add_created_file(self, file_path: Path) -> None:
        """Track a created file"""
        if file_path not in self.created_files:
            self.created_files.append(file_path)
    
    def add_modified_file(self, file_path: Path) -> None:
        """Track a modified file"""
        if file_path not in self.modified_files:
            self.modified_files.append(file_path)
    
    def add_backup_file(self, backup_path: Path) -> None:
        """Track a backup file"""
        if backup_path not in self.backup_files:
            self.backup_files.append(backup_path)
    
    def get_migration_summary(self) -> Dict[str, Any]:
        """Get comprehensive migration summary"""
        duration = None
        if self.start_time and self.end_time:
            delta = self.end_time - self.start_time
            duration = delta.total_seconds()
        
        return {
            "migration_id": self.migration_id,
            "theme_name": self.theme.name,
            "state": self.state.value,
            "overall_progress": self.get_overall_progress(),
            "duration_seconds": duration,
            "total_steps": len(self.step_trackers),
            "completed_steps": len(self.get_completed_steps()),
            "failed_steps": len(self.get_failed_steps()),
            "files_created": len(self.created_files),
            "files_modified": len(self.modified_files),
            "files_backed_up": len(self.backup_files),
            "branch_name": self.branch_name,
            "dry_run": self.dry_run
        }


class CompilationTestResult(BaseModel):
    """Result of SCSS compilation testing"""
    
    success: bool
    theme_name: str
    files_tested: List[str] = Field(default_factory=list)
    files_compiled: List[str] = Field(default_factory=list)
    files_failed: List[str] = Field(default_factory=list)
    
    # Error details
    compilation_errors: List[str] = Field(default_factory=list)
    fixes_applied: List[str] = Field(default_factory=list)
    
    # Timing
    test_duration_seconds: Optional[float] = None
    
    def get_success_rate(self) -> float:
        """Get compilation success rate"""
        if not self.files_tested:
            return 0.0
        return len(self.files_compiled) / len(self.files_tested)


class SnapshotInfo(BaseModel):
    """Information about migration snapshots"""
    
    snapshot_directory: Path
    files_snapshotted: List[str] = Field(default_factory=list)
    snapshot_time: datetime = Field(default_factory=datetime.now)
    
    def cleanup(self) -> bool:
        """Clean up snapshot files"""
        try:
            import shutil
            if self.snapshot_directory.exists():
                shutil.rmtree(self.snapshot_directory)
                return True
            return True
        except Exception:
            return False