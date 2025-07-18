"""SCSS processing models with comprehensive validation and context tracking"""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ScssVariableContext(str, Enum):
    """SCSS variable context enumeration"""
    GLOBAL = "global"
    MIXIN = "mixin"
    MAP = "map"
    PROPERTY = "property"
    FUNCTION = "function"
    SELECTOR = "selector"
    MEDIA_QUERY = "media_query"


class ScssVariableType(str, Enum):
    """SCSS variable type enumeration"""
    COLOR = "color"
    SIZE = "size"
    FONT = "font"
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    LIST = "list"
    MAP = "map"
    NULL = "null"
    UNKNOWN = "unknown"


class ScssProcessingMode(str, Enum):
    """SCSS processing mode enumeration"""
    STANDARD = "standard"
    CONSERVATIVE = "conservative"  # Minimal changes
    AGGRESSIVE = "aggressive"      # Maximum transformation
    SITE_BUILDER = "site_builder"  # SB-specific optimizations


class ScssVariable(BaseModel):
    """SCSS variable with comprehensive context and type information"""

    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid"
    )

    # Core variable data
    name: str = Field(..., description="Variable name (without $)")
    value: str = Field(..., description="Variable value as string")
    original_value: str = Field(..., description="Original unmodified value")

    # Context information
    context: ScssVariableContext = Field(default=ScssVariableContext.GLOBAL)
    variable_type: ScssVariableType = Field(default=ScssVariableType.UNKNOWN)
    line_number: int = Field(..., ge=1, description="Line number in source file")
    column_start: int = Field(default=1, ge=1, description="Starting column position")
    column_end: Optional[int] = Field(None, description="Ending column position")

    # Transformation tracking
    is_converted: bool = Field(default=False, description="Whether variable was converted")
    conversion_target: Optional[str] = Field(None, description="Target format after conversion")
    requires_manual_review: bool = Field(default=False, description="Requires manual review")

    # Dependencies and relationships
    depends_on: List[str] = Field(
        default_factory=list,
        description="Other variables this variable depends on"
    )
    used_by: List[str] = Field(
        default_factory=list,
        description="Other variables that use this variable"
    )

    # Metadata
    scope: str = Field(default="global", description="Variable scope (global, local, etc.)")
    importance: int = Field(default=1, ge=1, le=5, description="Variable importance (1-5)")
    tags: Set[str] = Field(default_factory=set, description="Custom tags for categorization")

    @field_validator("name")
    @classmethod
    def validate_variable_name(cls, v: str) -> str:
        """Validate SCSS variable name format"""
        if not v:
            raise ValueError("Variable name cannot be empty")

        # Remove leading $ if present
        if v.startswith("$"):
            v = v[1:]

        # Validate SCSS variable name rules
        import re
        if not re.match(r"^[a-zA-Z_][\w-]*$", v):
            raise ValueError(f"Invalid SCSS variable name: {v}")

        return v

    def get_full_name(self) -> str:
        """Get full variable name with $ prefix"""
        return f"${self.name}"

    def is_color_variable(self) -> bool:
        """Check if variable appears to be a color"""
        import re
        color_patterns = [
            r"^#[0-9a-fA-F]{3,8}$",  # Hex colors
            r"^rgb\(",               # RGB functions
            r"^rgba\(",              # RGBA functions
            r"^hsl\(",               # HSL functions
            r"^hsla\(",              # HSLA functions
        ]

        value = self.value.strip()
        return any(re.match(pattern, value) for pattern in color_patterns) or \
               value.lower() in ["transparent", "inherit", "initial", "unset"] or \
               value.lower() in ["red", "blue", "green", "yellow", "black", "white", "gray", "purple"]

    def is_size_variable(self) -> bool:
        """Check if variable appears to be a size/dimension"""
        import re
        return bool(re.match(r"^\d*\.?\d+(px|em|rem|%|vh|vw|pt|pc|in|cm|mm|ex|ch)$", self.value.strip()))

    def auto_detect_type(self) -> ScssVariableType:
        """Auto-detect variable type based on value"""
        if self.is_color_variable():
            return ScssVariableType.COLOR
        if self.is_size_variable():
            return ScssVariableType.SIZE
        if self.value.strip().startswith('"') or self.value.strip().startswith("'"):
            return ScssVariableType.STRING
        if self.value.strip() in ["true", "false"]:
            return ScssVariableType.BOOLEAN
        if self.value.strip() == "null":
            return ScssVariableType.NULL
        if "," in self.value:
            return ScssVariableType.LIST
        if ":" in self.value and "(" in self.value:
            return ScssVariableType.MAP
        # Try to parse as number
        try:
            float(self.value.strip())
            return ScssVariableType.NUMBER
        except ValueError:
            return ScssVariableType.UNKNOWN


class ScssConversionRule(BaseModel):
    """Rule for converting SCSS variables"""

    pattern: str = Field(..., description="Regex pattern to match")
    replacement: str = Field(..., description="Replacement pattern")
    context_filter: Optional[List[ScssVariableContext]] = Field(
        None,
        description="Only apply in these contexts"
    )
    type_filter: Optional[List[ScssVariableType]] = Field(
        None,
        description="Only apply to these variable types"
    )
    priority: int = Field(default=1, ge=1, le=10, description="Rule priority (higher = earlier)")
    enabled: bool = Field(default=True, description="Whether rule is enabled")


class ScssConversionContext(BaseModel):
    """Context information for SCSS conversion process"""

    # File information
    source_file: Path = Field(..., description="Source SCSS file")
    target_file: Optional[Path] = Field(None, description="Target output file")
    file_size_bytes: int = Field(default=0, ge=0, description="Source file size")

    # Processing configuration
    mode: ScssProcessingMode = Field(default=ScssProcessingMode.STANDARD)
    conversion_rules: List[ScssConversionRule] = Field(
        default_factory=list,
        description="Active conversion rules"
    )

    # Variable tracking
    all_variables: Dict[str, ScssVariable] = Field(
        default_factory=dict,
        description="All variables found in file"
    )
    global_variables: Dict[str, ScssVariable] = Field(
        default_factory=dict,
        description="Global scope variables"
    )

    # Statistics
    total_lines: int = Field(default=0, ge=0, description="Total lines in file")
    variable_lines: int = Field(default=0, ge=0, description="Lines containing variables")
    comment_lines: int = Field(default=0, ge=0, description="Lines with comments")
    empty_lines: int = Field(default=0, ge=0, description="Empty lines")

    def add_variable(self, variable: ScssVariable) -> None:
        """Add a variable to the context"""
        self.all_variables[variable.name] = variable

        if variable.context == ScssVariableContext.GLOBAL:
            self.global_variables[variable.name] = variable

    def get_variable_by_name(self, name: str) -> Optional[ScssVariable]:
        """Get variable by name (with or without $ prefix)"""
        clean_name = name.lstrip("$")
        return self.all_variables.get(clean_name)

    def get_variables_by_type(self, variable_type: ScssVariableType) -> List[ScssVariable]:
        """Get all variables of a specific type"""
        return [var for var in self.all_variables.values() if var.variable_type == variable_type]

    def get_variables_by_context(self, context: ScssVariableContext) -> List[ScssVariable]:
        """Get all variables in a specific context"""
        return [var for var in self.all_variables.values() if var.context == context]


class ScssProcessingResult(BaseModel):
    """Comprehensive result of SCSS file processing"""

    # Core result data
    success: bool = Field(..., description="Whether processing succeeded")
    source_file: Path = Field(..., description="Source file processed")
    target_file: Optional[Path] = Field(None, description="Target file created")

    # Content data
    original_content: str = Field(..., description="Original file content")
    processed_content: str = Field(..., description="Processed file content")

    # Processing statistics
    variables_found: int = Field(default=0, ge=0, description="Total variables found")
    variables_converted: List[ScssVariable] = Field(
        default_factory=list,
        description="Variables that were converted"
    )
    variables_skipped: List[ScssVariable] = Field(
        default_factory=list,
        description="Variables that were skipped"
    )

    # Timing information
    start_time: datetime = Field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    processing_duration_seconds: Optional[float] = None

    # Issue tracking
    errors: List[str] = Field(default_factory=list, description="Processing errors")
    warnings: List[str] = Field(default_factory=list, description="Processing warnings")

    # Conversion context
    conversion_context: Optional[ScssConversionContext] = Field(
        None,
        description="Detailed conversion context"
    )

    # File statistics
    original_size_bytes: int = Field(default=0, ge=0, description="Original file size")
    processed_size_bytes: int = Field(default=0, ge=0, description="Processed file size")
    size_change_percent: float = Field(default=0.0, description="Size change percentage")

    # Quality metrics
    syntax_valid: bool = Field(default=True, description="Whether output syntax is valid")
    semantic_equivalent: bool = Field(default=True, description="Whether semantically equivalent")
    requires_review: bool = Field(default=False, description="Whether manual review is needed")

    def complete(self, success: bool = True) -> None:
        """Mark processing as completed"""
        self.end_time = datetime.now()
        self.success = success
        if self.end_time:
            delta = self.end_time - self.start_time
            self.processing_duration_seconds = delta.total_seconds()

        # Calculate size change
        if self.original_size_bytes > 0:
            self.size_change_percent = (
                (self.processed_size_bytes - self.original_size_bytes) /
                self.original_size_bytes * 100
            )

    def add_converted_variable(self, variable: ScssVariable) -> None:
        """Add a successfully converted variable"""
        self.variables_converted.append(variable)
        self.variables_found += 1

    def add_skipped_variable(self, variable: ScssVariable, reason: str) -> None:
        """Add a skipped variable with reason"""
        self.variables_skipped.append(variable)
        self.variables_found += 1
        self.warnings.append(f"Skipped variable ${variable.name}: {reason}")

    def get_conversion_stats(self) -> Dict[str, Union[int, float, str]]:
        """Get conversion statistics summary"""
        total_vars = len(self.variables_converted) + len(self.variables_skipped)
        conversion_rate = (
            len(self.variables_converted) / total_vars
            if total_vars > 0 else 0.0
        )

        return {
            "total_variables": total_vars,
            "converted_count": len(self.variables_converted),
            "skipped_count": len(self.variables_skipped),
            "conversion_rate": conversion_rate,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "processing_time": self.processing_duration_seconds or 0.0,
            "size_change_percent": self.size_change_percent,
            "requires_review": self.requires_review
        }


class BatchScssProcessingResult(BaseModel):
    """Result of processing multiple SCSS files"""

    # Overall batch status
    success: bool = Field(..., description="Overall batch success")
    start_time: datetime = Field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    total_duration_seconds: Optional[float] = None

    # Individual file results
    file_results: List[ScssProcessingResult] = Field(
        default_factory=list,
        description="Results for each processed file"
    )

    # Batch statistics
    files_processed: int = Field(default=0, description="Total files processed")
    files_successful: int = Field(default=0, description="Files processed successfully")
    files_failed: int = Field(default=0, description="Files that failed processing")

    # Aggregated statistics
    total_variables_converted: int = Field(default=0, description="Total variables converted")
    total_variables_skipped: int = Field(default=0, description="Total variables skipped")
    total_errors: List[str] = Field(default_factory=list, description="All errors encountered")
    total_warnings: List[str] = Field(default_factory=list, description="All warnings encountered")

    def complete(self) -> None:
        """Mark batch processing as completed"""
        self.end_time = datetime.now()
        if self.end_time:
            delta = self.end_time - self.start_time
            self.total_duration_seconds = delta.total_seconds()

        # Calculate final statistics
        self.files_processed = len(self.file_results)
        self.files_successful = sum(1 for r in self.file_results if r.success)
        self.files_failed = self.files_processed - self.files_successful
        self.success = self.files_failed == 0

        # Aggregate statistics
        for result in self.file_results:
            self.total_variables_converted += len(result.variables_converted)
            self.total_variables_skipped += len(result.variables_skipped)
            self.total_errors.extend(result.errors)
            self.total_warnings.extend(result.warnings)

    def add_file_result(self, result: ScssProcessingResult) -> None:
        """Add a file processing result"""
        self.file_results.append(result)

    def get_overall_success_rate(self) -> float:
        """Get overall success rate across all files"""
        if not self.file_results:
            return 0.0
        return self.files_successful / len(self.file_results)

    def get_performance_summary(self) -> Dict[str, Union[int, float, str]]:
        """Get performance summary across all files"""
        avg_time_per_file = (
            self.total_duration_seconds / self.files_processed
            if self.total_duration_seconds and self.files_processed > 0
            else 0.0
        )

        return {
            "total_files": self.files_processed,
            "success_rate": self.get_overall_success_rate(),
            "total_variables": self.total_variables_converted + self.total_variables_skipped,
            "conversion_rate": (
                self.total_variables_converted /
                (self.total_variables_converted + self.total_variables_skipped)
                if (self.total_variables_converted + self.total_variables_skipped) > 0
                else 0.0
            ),
            "avg_time_per_file": avg_time_per_file,
            "total_errors": len(self.total_errors),
            "total_warnings": len(self.total_warnings)
        }
