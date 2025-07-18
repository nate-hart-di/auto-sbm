"""Theme data models with comprehensive validation and type safety"""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ThemeType(str, Enum):
    """Theme type enumeration"""
    LEGACY = "legacy"
    SITE_BUILDER = "site_builder"
    HYBRID = "hybrid"  # During migration


class ThemeStatus(str, Enum):
    """Theme migration status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLBACK = "rollback"


class OEMType(str, Enum):
    """OEM type enumeration"""
    STELLANTIS = "stellantis"
    FORD = "ford"
    GM = "gm"
    TOYOTA = "toyota"
    GENERIC = "generic"


class Theme(BaseModel):
    """
    Core theme data model with comprehensive validation.
    
    Represents a dealer theme with all associated metadata and file paths
    required for the migration process.
    """
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True,
        use_enum_values=True,
        extra="forbid"
    )

    # Core identification
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Theme name (must be unique)"
    )
    slug: Optional[str] = Field(
        None,
        pattern=r"^[a-z0-9]([a-z0-9\-]*[a-z0-9])?$",
        description="URL-safe theme identifier"
    )

    # Theme classification
    type: ThemeType = Field(default=ThemeType.LEGACY)
    status: ThemeStatus = Field(default=ThemeStatus.PENDING)
    oem_type: OEMType = Field(default=OEMType.GENERIC)

    # File system paths
    source_path: Path = Field(..., description="Source theme directory")
    destination_path: Optional[Path] = Field(None, description="Destination for Site Builder files")
    backup_path: Optional[Path] = Field(None, description="Backup directory path")

    # File collections
    scss_files: List[Path] = Field(default_factory=list, description="SCSS files to process")
    template_files: List[Path] = Field(default_factory=list, description="Template files to migrate")
    asset_files: List[Path] = Field(default_factory=list, description="Asset files to copy")

    # OEM-specific data
    oem_specific: Dict[str, Any] = Field(
        default_factory=dict,
        description="OEM-specific configuration and metadata"
    )

    # Migration metadata
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = Field(None)
    migration_started_at: Optional[datetime] = Field(None)
    migration_completed_at: Optional[datetime] = Field(None)

    # Version tracking
    version: str = Field(default="1.0.0", description="Theme version")
    sbm_version: str = Field(default="2.0.0", description="SBM tool version used")

    @field_validator("source_path")
    @classmethod
    def validate_source_path_exists(cls, v: Path) -> Path:
        """Validate that source path exists"""
        if not v.exists():
            raise ValueError(f"Source path does not exist: {v}")
        if not v.is_dir():
            raise ValueError(f"Source path is not a directory: {v}")
        return v

    @field_validator("scss_files", "template_files", "asset_files")
    @classmethod
    def validate_file_paths(cls, v: List[Path]) -> List[Path]:
        """Validate that all file paths exist"""
        for file_path in v:
            if not file_path.exists():
                raise ValueError(f"File does not exist: {file_path}")
        return v

    @model_validator(mode="after")
    def generate_slug_from_name(self) -> "Theme":
        """Generate slug from name if not provided"""
        if self.slug is None:
            # Convert name to URL-safe slug
            import re
            slug = re.sub(r"[^a-z0-9]+", "-", self.name.lower())
            slug = slug.strip("-")
            self.slug = slug
        return self

    def update_status(self, new_status: ThemeStatus) -> None:
        """Update theme status with timestamp"""
        self.status = new_status
        self.updated_at = datetime.now()

        if new_status == ThemeStatus.IN_PROGRESS:
            self.migration_started_at = datetime.now()
        elif new_status in [ThemeStatus.COMPLETED, ThemeStatus.FAILED]:
            self.migration_completed_at = datetime.now()

    def get_expected_output_files(self) -> List[Path]:
        """Get list of expected Site Builder output files"""
        if not self.destination_path:
            return []

        expected_files = [
            "sb-inside.scss",
            "sb-vdp.scss",
            "sb-vrp.scss",
            "sb-home.scss"
        ]

        return [self.destination_path / filename for filename in expected_files]

    def is_migration_complete(self) -> bool:
        """Check if migration appears complete"""
        if self.status != ThemeStatus.COMPLETED:
            return False

        expected_files = self.get_expected_output_files()
        return all(file_path.exists() for file_path in expected_files)

    def get_migration_duration(self) -> Optional[float]:
        """Get migration duration in seconds"""
        if not self.migration_started_at or not self.migration_completed_at:
            return None

        delta = self.migration_completed_at - self.migration_started_at
        return delta.total_seconds()


class ThemeCollection(BaseModel):
    """Collection of themes with batch operations"""

    themes: List[Theme] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)

    def add_theme(self, theme: Theme) -> None:
        """Add theme to collection"""
        # Ensure unique names
        existing_names = [t.name for t in self.themes]
        if theme.name in existing_names:
            raise ValueError(f"Theme with name '{theme.name}' already exists")

        self.themes.append(theme)

    def get_theme_by_name(self, name: str) -> Optional[Theme]:
        """Get theme by name"""
        for theme in self.themes:
            if theme.name == name:
                return theme
        return None

    def get_themes_by_status(self, status: ThemeStatus) -> List[Theme]:
        """Get all themes with specified status"""
        return [theme for theme in self.themes if theme.status == status]

    def get_themes_by_oem(self, oem_type: OEMType) -> List[Theme]:
        """Get all themes for specified OEM"""
        return [theme for theme in self.themes if theme.oem_type == oem_type]
