"""Migration data models with comprehensive validation and progress tracking"""

from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .theme import Theme


class MigrationStep(str, Enum):
    """Migration step enumeration for progress tracking"""
    GIT_SETUP = "git_setup"
    DOCKER_STARTUP = "docker_startup"
    FILE_CREATION = "file_creation"
    SCSS_MIGRATION = "scss_migration"
    PREDETERMINED_STYLES = "predetermined_styles"
    MAP_COMPONENTS = "map_components"
    VALIDATION = "validation"
    CLEANUP = "cleanup"


class MigrationPriority(str, Enum):
    """Migration priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class MigrationMode(str, Enum):
    """Migration execution modes"""
    FULL = "full"              # Complete migration
    DRY_RUN = "dry_run"        # Simulation only
    INCREMENTAL = "incremental" # Step-by-step with pauses
    ROLLBACK = "rollback"      # Undo migration


class StepResult(BaseModel):
    """Result of a single migration step"""

    step: MigrationStep
    success: bool = Field(default=False, description="Whether the step succeeded")
    start_time: datetime = Field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    files_processed: int = 0
    files_failed: int = 0
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def complete(self, success: bool = True) -> None:
        """Mark step as completed"""
        self.end_time = datetime.now()
        self.success = success
        if self.end_time:
            delta = self.end_time - self.start_time
            self.duration_seconds = delta.total_seconds()


class MigrationConfig(BaseModel):
    """Migration configuration with comprehensive validation"""

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True,
        extra="forbid"
    )

    # Core configuration
    theme: Theme = Field(..., description="Theme to migrate")
    mode: MigrationMode = Field(default=MigrationMode.FULL)
    priority: MigrationPriority = Field(default=MigrationPriority.NORMAL)

    # Feature flags
    backup_enabled: bool = Field(default=True, description="Create backups before migration")
    validation_enabled: bool = Field(default=True, description="Enable post-migration validation")
    rich_ui_enabled: bool = Field(default=True, description="Enable Rich UI progress tracking")
    git_operations_enabled: bool = Field(default=True, description="Enable Git operations")

    # Processing configuration
    max_concurrent_files: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum concurrent file processing"
    )
    timeout_seconds: int = Field(
        default=3600,  # 1 hour
        ge=60,
        le=14400,  # 4 hours max
        description="Migration timeout in seconds"
    )

    # Output configuration
    output_directory: Optional[Path] = Field(
        None,
        description="Custom output directory (default: theme source + '_sb')"
    )
    preserve_original: bool = Field(
        default=True,
        description="Keep original files after migration"
    )

    # Step configuration
    enabled_steps: List[MigrationStep] = Field(
        default_factory=lambda: list(MigrationStep),
        description="Steps to execute during migration"
    )
    step_pause_seconds: int = Field(
        default=0,
        ge=0,
        le=300,
        description="Pause between steps (for incremental mode)"
    )

    # OEM-specific configuration
    oem_config: Dict[str, Any] = Field(
        default_factory=dict,
        description="OEM-specific configuration overrides"
    )

    @field_validator("enabled_steps")
    @classmethod
    def validate_enabled_steps(cls, v: List[MigrationStep]) -> List[MigrationStep]:
        """Validate enabled steps"""
        if not v:
            raise ValueError("At least one migration step must be enabled")

        # Ensure git_setup is first if git operations are enabled
        if MigrationStep.GIT_SETUP in v and v[0] != MigrationStep.GIT_SETUP:
            v_copy = v.copy()
            v_copy.remove(MigrationStep.GIT_SETUP)
            v_copy.insert(0, MigrationStep.GIT_SETUP)
            return v_copy

        return v

    @field_validator("output_directory")
    @classmethod
    def validate_output_directory(cls, v: Optional[Path], info: Any) -> Optional[Path]:
        """Validate or generate output directory"""
        if v is None and hasattr(info, "data") and info.data and info.data.get("theme"):
            # Generate default output directory
            theme = info.data["theme"]
            return Path(theme.source_path.parent / f"{theme.source_path.name}_sb")
        return v

    def get_timeout_delta(self) -> timedelta:
        """Get timeout as timedelta object"""
        return timedelta(seconds=self.timeout_seconds)

    def is_step_enabled(self, step: MigrationStep) -> bool:
        """Check if a specific step is enabled"""
        return step in self.enabled_steps


class MigrationResult(BaseModel):
    """Comprehensive migration operation result"""

    # Core result data
    success: bool = Field(..., description="Overall migration success")
    theme_name: str = Field(description="Name of migrated theme")
    migration_mode: MigrationMode = Field(description="Migration mode used")

    # Timing information
    start_time: datetime = Field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    total_duration_seconds: Optional[float] = None

    # File processing statistics
    files_processed: int = Field(default=0, description="Total files processed")
    files_failed: int = Field(default=0, description="Total files that failed")
    files_created: int = Field(default=0, description="New files created")
    files_modified: int = Field(default=0, description="Existing files modified")

    # Step results
    step_results: List[StepResult] = Field(
        default_factory=list,
        description="Results for each migration step"
    )

    # Issue tracking
    errors: List[str] = Field(default_factory=list, description="Critical errors")
    warnings: List[str] = Field(default_factory=list, description="Non-critical warnings")

    # Output information
    output_files: List[Path] = Field(
        default_factory=list,
        description="Files created during migration"
    )
    backup_location: Optional[Path] = Field(
        None,
        description="Location of backup files"
    )

    # Migration metadata
    sbm_version: str = Field(default="2.0.0", description="SBM version used")
    configuration_hash: Optional[str] = Field(
        None,
        description="Hash of migration configuration for reproducibility"
    )

    def complete(self, success: bool = True) -> None:
        """Mark migration as completed"""
        self.end_time = datetime.now()
        self.success = success
        if self.end_time:
            delta = self.end_time - self.start_time
            self.total_duration_seconds = delta.total_seconds()

    def add_step_result(self, step_result: StepResult) -> None:
        """Add a step result to the migration"""
        self.step_results.append(step_result)

        # Update statistics
        self.files_processed += step_result.files_processed
        self.files_failed += step_result.files_failed
        self.errors.extend(step_result.errors)
        self.warnings.extend(step_result.warnings)

    def get_step_result(self, step: MigrationStep) -> Optional[StepResult]:
        """Get result for a specific step"""
        for result in self.step_results:
            if result.step == step:
                return result
        return None

    def get_failed_steps(self) -> List[StepResult]:
        """Get all failed steps"""
        return [result for result in self.step_results if not result.success]

    def get_success_rate(self) -> float:
        """Get overall success rate (0.0 to 1.0)"""
        if not self.step_results:
            return 1.0 if self.success else 0.0

        successful_steps = sum(1 for result in self.step_results if result.success)
        return successful_steps / len(self.step_results)

    def get_performance_summary(self) -> Dict[str, Union[float, int, str]]:
        """Get performance summary statistics"""
        return {
            "total_duration": self.total_duration_seconds or 0.0,
            "files_per_second": (
                self.files_processed / self.total_duration_seconds
                if self.total_duration_seconds and self.total_duration_seconds > 0
                else 0.0
            ),
            "success_rate": self.get_success_rate(),
            "steps_completed": len(self.step_results),
            "errors_count": len(self.errors),
            "warnings_count": len(self.warnings),
            "fastest_step": min(
                (r.step.value for r in self.step_results if r.duration_seconds),
                key=lambda s: next(
                    r.duration_seconds for r in self.step_results
                    if r.step.value == s and r.duration_seconds
                ),
                default="none"
            ),
            "slowest_step": max(
                (r.step.value for r in self.step_results if r.duration_seconds),
                key=lambda s: next(
                    r.duration_seconds for r in self.step_results
                    if r.step.value == s and r.duration_seconds
                ),
                default="none"
            )
        }


class BatchMigrationConfig(BaseModel):
    """Configuration for batch migration of multiple themes"""

    themes: List[Theme] = Field(..., min_items=1, description="Themes to migrate")
    migration_config_template: MigrationConfig = Field(
        ...,
        description="Template configuration applied to all themes"
    )

    # Batch-specific settings
    max_concurrent_migrations: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum concurrent theme migrations"
    )
    continue_on_failure: bool = Field(
        default=True,
        description="Continue batch if individual themes fail"
    )

    # Progress tracking
    progress_reporting_interval: int = Field(
        default=30,
        ge=5,
        le=300,
        description="Progress update interval in seconds"
    )


class BatchMigrationResult(BaseModel):
    """Result of batch migration operation"""

    # Overall batch status
    success: bool = Field(..., description="Overall batch success")
    start_time: datetime = Field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    total_duration_seconds: Optional[float] = None

    # Individual theme results
    theme_results: List[MigrationResult] = Field(
        default_factory=list,
        description="Results for each theme migration"
    )

    # Batch statistics
    themes_processed: int = Field(default=0)
    themes_successful: int = Field(default=0)
    themes_failed: int = Field(default=0)

    def complete(self) -> None:
        """Mark batch migration as completed"""
        self.end_time = datetime.now()
        if self.end_time:
            delta = self.end_time - self.start_time
            self.total_duration_seconds = delta.total_seconds()

        # Calculate final statistics
        self.themes_processed = len(self.theme_results)
        self.themes_successful = sum(1 for r in self.theme_results if r.success)
        self.themes_failed = self.themes_processed - self.themes_successful
        self.success = self.themes_failed == 0

    def add_theme_result(self, result: MigrationResult) -> None:
        """Add a theme migration result"""
        self.theme_results.append(result)

    def get_overall_success_rate(self) -> float:
        """Get overall success rate across all themes"""
        if not self.theme_results:
            return 0.0
        return self.themes_successful / len(self.theme_results)
