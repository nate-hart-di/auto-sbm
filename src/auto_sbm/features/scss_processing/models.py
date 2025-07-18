"""Pydantic models for SCSS processing data structures

This module provides comprehensive type-safe models for all SCSS processing operations,
replacing the scattered data structures in the legacy processor.py file.
"""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ScssVariableType(str, Enum):
    """SCSS variable value types for auto-detection"""
    COLOR = "color"
    SIZE = "size"
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    LIST = "list"
    MAP = "map"
    UNKNOWN = "unknown"


class ScssMixinType(str, Enum):
    """Types of SCSS mixins for categorization"""
    FLEXBOX = "flexbox"
    POSITIONING = "positioning"
    TRANSFORM = "transform"
    TRANSITION = "transition"
    LAYOUT = "layout"
    BACKGROUND = "background"
    GRADIENT = "gradient"
    TYPOGRAPHY = "typography"
    BREAKPOINT = "breakpoint"
    UTILITY = "utility"
    CUSTOM = "custom"


class ScssTransformationStep(str, Enum):
    """Steps in the SCSS transformation pipeline"""
    VARIABLE_PROCESSING = "variable_processing"
    MIXIN_CONVERSION = "mixin_conversion"
    FUNCTION_CONVERSION = "function_conversion"
    PATH_CONVERSION = "path_conversion"
    IMPORT_REMOVAL = "import_removal"
    VALIDATION = "validation"
    CLEANUP = "cleanup"


class ScssProcessingMode(str, Enum):
    """SCSS processing modes"""
    FULL = "full"
    VARIABLES_ONLY = "variables_only"
    MIXINS_ONLY = "mixins_only"
    VALIDATION_ONLY = "validation_only"
    DRY_RUN = "dry_run"


class ScssVariable(BaseModel):
    """Represents an SCSS variable with metadata and type detection"""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(..., pattern=r"^\$?[\w-]+$", description="Variable name without $ prefix")
    value: str = Field(..., min_length=1, description="Variable value")
    type: ScssVariableType = Field(default=ScssVariableType.UNKNOWN, description="Auto-detected variable type")
    css_custom_property: str = Field(default="", description="Converted CSS custom property name")
    source_line: Optional[int] = Field(default=None, description="Source line number")
    dependencies: List[str] = Field(default_factory=list, description="Other variables this depends on")

    def __init__(self, **data):
        super().__init__(**data)
        # Auto-generate CSS custom property name
        if not self.css_custom_property:
            self.css_custom_property = f"--{self.name.lstrip('$')}"
        # Auto-detect variable type
        if self.type == ScssVariableType.UNKNOWN:
            self.type = self._detect_type()

    def _detect_type(self) -> ScssVariableType:
        """Auto-detect variable type from value"""
        value = self.value.strip()

        # Color detection
        if (value.startswith("#") or
            value.startswith("rgb") or
            value.startswith("hsl") or
            value in ["transparent", "inherit", "currentColor"] or
            value in ["red", "blue", "green", "black", "white", "gray", "yellow", "orange", "purple"]):
            return ScssVariableType.COLOR

        # Size detection
        if any(value.endswith(unit) for unit in ["px", "rem", "em", "%", "vh", "vw", "pt"]):
            return ScssVariableType.SIZE

        # Number detection
        try:
            float(value)
            return ScssVariableType.NUMBER
        except ValueError:
            pass

        # Boolean detection
        if value.lower() in ["true", "false"]:
            return ScssVariableType.BOOLEAN

        # List detection
        if "," in value and not value.startswith("("):
            return ScssVariableType.LIST

        # Map detection
        if value.startswith("(") and value.endswith(")"):
            return ScssVariableType.MAP

        # String (quoted or default)
        if value.startswith('"') or value.startswith("'"):
            return ScssVariableType.STRING

        return ScssVariableType.UNKNOWN

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Ensure variable name is valid"""
        # Remove $ prefix for normalization
        name = v.lstrip("$")
        if not name:
            raise ValueError("Variable name cannot be empty")
        return name


class ScssMixinParameter(BaseModel):
    """Represents a mixin parameter with type information"""

    name: str = Field(..., description="Parameter name")
    value: Optional[str] = Field(default=None, description="Parameter value")
    default_value: Optional[str] = Field(default=None, description="Default parameter value")
    type_hint: Optional[str] = Field(default=None, description="Expected parameter type")


class ScssMixinDefinition(BaseModel):
    """Represents an SCSS mixin definition with conversion metadata"""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(..., min_length=1, description="Mixin name")
    type: ScssMixinType = Field(default=ScssMixinType.CUSTOM, description="Mixin category")
    parameters: List[ScssMixinParameter] = Field(default_factory=list, description="Mixin parameters")
    content_block: Optional[str] = Field(default=None, description="Mixin content block if any")
    css_output: Optional[str] = Field(default=None, description="Generated CSS output")
    vendor_prefixes_needed: List[str] = Field(default_factory=list, description="Required vendor prefixes")
    browser_support: Dict[str, str] = Field(default_factory=dict, description="Browser support information")
    source_line: Optional[int] = Field(default=None, description="Source line number")
    conversion_notes: List[str] = Field(default_factory=list, description="Notes about the conversion process")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Ensure mixin name is valid"""
        if not v.replace("-", "").replace("_", "").isalnum():
            raise ValueError("Mixin name must contain only alphanumeric characters, hyphens, and underscores")
        return v


class ScssFunction(BaseModel):
    """Represents an SCSS function call with conversion metadata"""

    name: str = Field(..., description="Function name")
    arguments: List[str] = Field(default_factory=list, description="Function arguments")
    css_replacement: Optional[str] = Field(default=None, description="CSS replacement value")
    requires_compilation: bool = Field(default=False, description="Whether function needs pre-compilation")
    source_line: Optional[int] = Field(default=None, description="Source line number")


class ScssImport(BaseModel):
    """Represents an SCSS import statement"""

    path: str = Field(..., description="Import path")
    is_external: bool = Field(default=False, description="Whether import is external")
    resolved_path: Optional[Path] = Field(default=None, description="Resolved file path")
    source_line: Optional[int] = Field(default=None, description="Source line number")


class ScssTransformationContext(BaseModel):
    """Context object for SCSS transformation pipeline"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    # Input
    source_content: str = Field(..., description="Original SCSS content")
    source_file: Optional[Path] = Field(default=None, description="Source file path")

    # Processing state
    current_content: str = Field(default="", description="Current transformed content")
    processing_step: ScssTransformationStep = Field(default=ScssTransformationStep.VARIABLE_PROCESSING)

    # Extracted elements
    variables: List[ScssVariable] = Field(default_factory=list, description="Extracted SCSS variables")
    mixins: List[ScssMixinDefinition] = Field(default_factory=list, description="Found SCSS mixins")
    functions: List[ScssFunction] = Field(default_factory=list, description="Found SCSS functions")
    imports: List[ScssImport] = Field(default_factory=list, description="Found SCSS imports")

    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)
    processing_time_seconds: Optional[float] = Field(default=None, description="Processing duration")
    lines_processed: int = Field(default=0, description="Number of lines processed")
    transformations_applied: List[str] = Field(default_factory=list, description="Applied transformations")

    # Validation results
    syntax_valid: bool = Field(default=True, description="Whether syntax is valid")
    compilation_tested: bool = Field(default=False, description="Whether compilation was tested")
    compilation_successful: Optional[bool] = Field(default=None, description="Compilation test result")

    def __init__(self, **data):
        super().__init__(**data)
        if not self.current_content:
            self.current_content = self.source_content
        if not self.lines_processed:
            self.lines_processed = len(self.source_content.splitlines())

    def add_transformation(self, transformation: str) -> None:
        """Add a transformation to the applied list"""
        if transformation not in self.transformations_applied:
            self.transformations_applied.append(transformation)

    def update_content(self, new_content: str, step: ScssTransformationStep) -> None:
        """Update current content and processing step"""
        self.current_content = new_content
        self.processing_step = step

    def get_processing_summary(self) -> Dict[str, Any]:
        """Get processing summary statistics"""
        return {
            "variables_found": len(self.variables),
            "mixins_found": len(self.mixins),
            "functions_found": len(self.functions),
            "imports_found": len(self.imports),
            "transformations_applied": len(self.transformations_applied),
            "processing_time": self.processing_time_seconds,
            "syntax_valid": self.syntax_valid,
            "compilation_successful": self.compilation_successful,
            "current_step": self.processing_step.value
        }


class ScssProcessingConfig(BaseModel):
    """Configuration for SCSS processing operations"""

    mode: ScssProcessingMode = Field(default=ScssProcessingMode.FULL, description="Processing mode")

    # Processing options
    convert_variables: bool = Field(default=True, description="Convert SCSS variables to CSS custom properties")
    convert_mixins: bool = Field(default=True, description="Convert SCSS mixins to CSS")
    convert_functions: bool = Field(default=True, description="Convert SCSS functions")
    remove_imports: bool = Field(default=True, description="Remove @import statements")
    convert_image_paths: bool = Field(default=True, description="Convert relative image paths")

    # Validation options
    validate_syntax: bool = Field(default=True, description="Validate SCSS syntax")
    test_compilation: bool = Field(default=True, description="Test SCSS compilation")
    strict_mode: bool = Field(default=False, description="Fail on any validation errors")

    # Output options
    minify_output: bool = Field(default=False, description="Minify generated CSS")
    preserve_comments: bool = Field(default=True, description="Preserve CSS comments")
    add_source_maps: bool = Field(default=False, description="Generate source maps")

    # Performance options
    max_file_size_mb: int = Field(default=10, description="Maximum file size to process")
    max_processing_time_seconds: int = Field(default=300, description="Maximum processing time")
    enable_caching: bool = Field(default=True, description="Enable transformation caching")

    # Browser support
    target_browsers: List[str] = Field(
        default_factory=lambda: ["last 2 versions", "IE 11"],
        description="Target browser versions for vendor prefixes"
    )

    @field_validator("max_file_size_mb")
    @classmethod
    def validate_max_file_size(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Max file size must be positive")
        if v > 100:
            raise ValueError("Max file size cannot exceed 100MB")
        return v


class ScssProcessingError(BaseModel):
    """Represents an error during SCSS processing"""

    error_type: str = Field(..., description="Error category")
    message: str = Field(..., description="Error message")
    line_number: Optional[int] = Field(default=None, description="Line number where error occurred")
    column_number: Optional[int] = Field(default=None, description="Column number where error occurred")
    source_snippet: Optional[str] = Field(default=None, description="Code snippet causing error")
    severity: str = Field(default="error", description="Error severity level")
    suggestion: Optional[str] = Field(default=None, description="Suggested fix")


class ScssProcessingResult(BaseModel):
    """Result of SCSS processing operation"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    # Processing outcome
    success: bool = Field(..., description="Whether processing succeeded")
    output_content: Optional[str] = Field(default=None, description="Transformed SCSS/CSS content")

    # Processing context
    context: Optional[ScssTransformationContext] = Field(default=None, description="Processing context")

    # Metrics
    input_size_bytes: int = Field(default=0, description="Input file size")
    output_size_bytes: int = Field(default=0, description="Output file size")
    processing_time_seconds: float = Field(default=0.0, description="Total processing time")
    memory_usage_mb: Optional[float] = Field(default=None, description="Peak memory usage")

    # Validation results
    syntax_errors: List[ScssProcessingError] = Field(default_factory=list, description="Syntax errors found")
    compilation_errors: List[ScssProcessingError] = Field(default_factory=list, description="Compilation errors")
    warnings: List[ScssProcessingError] = Field(default_factory=list, description="Processing warnings")

    # Transformation summary
    variables_converted: int = Field(default=0, description="Number of variables converted")
    mixins_converted: int = Field(default=0, description="Number of mixins converted")
    functions_converted: int = Field(default=0, description="Number of functions converted")
    imports_removed: int = Field(default=0, description="Number of imports removed")

    # Output files
    generated_files: List[Path] = Field(default_factory=list, description="Generated output files")
    backup_files: List[Path] = Field(default_factory=list, description="Created backup files")

    def __init__(self, **data):
        super().__init__(**data)
        if self.output_content and not self.output_size_bytes:
            self.output_size_bytes = len(self.output_content.encode("utf-8"))

    def get_error_summary(self) -> Dict[str, int]:
        """Get summary of errors and warnings"""
        return {
            "syntax_errors": len(self.syntax_errors),
            "compilation_errors": len(self.compilation_errors),
            "warnings": len(self.warnings),
            "total_issues": len(self.syntax_errors) + len(self.compilation_errors) + len(self.warnings)
        }

    def get_transformation_summary(self) -> Dict[str, Any]:
        """Get summary of transformations applied"""
        return {
            "variables_converted": self.variables_converted,
            "mixins_converted": self.mixins_converted,
            "functions_converted": self.functions_converted,
            "imports_removed": self.imports_removed,
            "size_reduction_percent": self._calculate_size_reduction(),
            "processing_time": self.processing_time_seconds
        }

    def _calculate_size_reduction(self) -> float:
        """Calculate size reduction percentage"""
        if self.input_size_bytes == 0:
            return 0.0
        reduction = (self.input_size_bytes - self.output_size_bytes) / self.input_size_bytes
        return round(reduction * 100, 2)


class ScssValidationResult(BaseModel):
    """Result of SCSS validation operations"""

    is_valid: bool = Field(..., description="Overall validation result")
    errors: List[ScssProcessingError] = Field(default_factory=list, description="Validation errors")
    warnings: List[ScssProcessingError] = Field(default_factory=list, description="Validation warnings")

    # Syntax validation
    balanced_braces: bool = Field(default=True, description="Braces are balanced")
    valid_selectors: bool = Field(default=True, description="All selectors are valid")
    valid_properties: bool = Field(default=True, description="All properties are valid")

    # Compilation validation
    compilation_successful: Optional[bool] = Field(default=None, description="Compilation test result")
    compilation_time_ms: Optional[float] = Field(default=None, description="Compilation time")

    # Content analysis
    has_remaining_scss: bool = Field(default=False, description="Contains unconverted SCSS syntax")
    remaining_variables: List[str] = Field(default_factory=list, description="Remaining SCSS variables")
    remaining_mixins: List[str] = Field(default_factory=list, description="Remaining SCSS mixins")
    remaining_functions: List[str] = Field(default_factory=list, description="Remaining SCSS functions")

    def get_validation_summary(self) -> str:
        """Get human-readable validation summary"""
        if self.is_valid:
            return "✅ SCSS validation passed"

        issues = []
        if self.errors:
            issues.append(f"{len(self.errors)} errors")
        if self.warnings:
            issues.append(f"{len(self.warnings)} warnings")

        return f"❌ SCSS validation failed: {', '.join(issues)}"
