"""Tests for SCSS processing models"""

import pytest
from pathlib import Path
from datetime import datetime

from ..models import (
    ScssVariable, ScssVariableType, ScssMixinDefinition, ScssMixinType,
    ScssTransformationContext, ScssProcessingConfig, ScssProcessingResult,
    ScssProcessingError, ScssValidationResult, ScssProcessingMode,
    ScssTransformationStep
)


class TestScssVariable:
    """Test SCSS variable model"""
    
    def test_variable_creation(self):
        """Test basic variable creation"""
        var = ScssVariable(name="primary", value="#007bff")
        
        assert var.name == "primary"
        assert var.value == "#007bff"
        assert var.css_custom_property == "--primary"
        assert var.type == ScssVariableType.COLOR
    
    def test_variable_name_normalization(self):
        """Test variable name normalization (removes $ prefix)"""
        var = ScssVariable(name="$primary-color", value="#007bff")
        
        assert var.name == "primary-color"
        assert var.css_custom_property == "--primary-color"
    
    def test_color_type_detection(self):
        """Test automatic color type detection"""
        test_cases = [
            ("#007bff", ScssVariableType.COLOR),
            ("rgb(0, 123, 255)", ScssVariableType.COLOR),
            ("hsl(210, 100%, 50%)", ScssVariableType.COLOR),
            ("transparent", ScssVariableType.COLOR),
            ("red", ScssVariableType.COLOR),
        ]
        
        for value, expected_type in test_cases:
            var = ScssVariable(name="test", value=value)
            assert var.type == expected_type, f"Failed for value: {value}"
    
    def test_size_type_detection(self):
        """Test automatic size type detection"""
        test_cases = [
            ("16px", ScssVariableType.SIZE),
            ("1.5rem", ScssVariableType.SIZE),
            ("100%", ScssVariableType.SIZE),
            ("50vh", ScssVariableType.SIZE),
        ]
        
        for value, expected_type in test_cases:
            var = ScssVariable(name="test", value=value)
            assert var.type == expected_type, f"Failed for value: {value}"
    
    def test_number_type_detection(self):
        """Test automatic number type detection"""
        test_cases = [
            ("1", ScssVariableType.NUMBER),
            ("0.5", ScssVariableType.NUMBER),
            ("-10", ScssVariableType.NUMBER),
        ]
        
        for value, expected_type in test_cases:
            var = ScssVariable(name="test", value=value)
            assert var.type == expected_type, f"Failed for value: {value}"
    
    def test_boolean_type_detection(self):
        """Test automatic boolean type detection"""
        test_cases = [
            ("true", ScssVariableType.BOOLEAN),
            ("false", ScssVariableType.BOOLEAN),
        ]
        
        for value, expected_type in test_cases:
            var = ScssVariable(name="test", value=value)
            assert var.type == expected_type, f"Failed for value: {value}"
    
    def test_invalid_variable_name(self):
        """Test validation of variable names"""
        with pytest.raises(ValueError):
            ScssVariable(name="", value="test")


class TestScssMixinDefinition:
    """Test SCSS mixin definition model"""
    
    def test_mixin_creation(self):
        """Test basic mixin creation"""
        mixin = ScssMixinDefinition(name="flexbox", type=ScssMixinType.FLEXBOX)
        
        assert mixin.name == "flexbox"
        assert mixin.type == ScssMixinType.FLEXBOX
        assert mixin.parameters == []
        assert mixin.vendor_prefixes_needed == []
    
    def test_mixin_name_validation(self):
        """Test mixin name validation"""
        # Valid names
        valid_names = ["flexbox", "border-radius", "flex_wrap", "test123"]
        for name in valid_names:
            mixin = ScssMixinDefinition(name=name)
            assert mixin.name == name
        
        # Invalid names
        with pytest.raises(ValueError):
            ScssMixinDefinition(name="invalid name with spaces")


class TestScssTransformationContext:
    """Test SCSS transformation context model"""
    
    def test_context_creation(self):
        """Test basic context creation"""
        content = "$primary: #007bff;\n.test { color: $primary; }"
        context = ScssTransformationContext(source_content=content)
        
        assert context.source_content == content
        assert context.current_content == content
        assert context.processing_step == ScssTransformationStep.VARIABLE_PROCESSING
        assert context.lines_processed == 2
        assert isinstance(context.created_at, datetime)
    
    def test_add_transformation(self):
        """Test adding transformations"""
        context = ScssTransformationContext(source_content="test")
        
        context.add_transformation("variable_conversion")
        context.add_transformation("mixin_conversion")
        context.add_transformation("variable_conversion")  # Duplicate
        
        assert len(context.transformations_applied) == 2
        assert "variable_conversion" in context.transformations_applied
        assert "mixin_conversion" in context.transformations_applied
    
    def test_update_content(self):
        """Test updating content and step"""
        context = ScssTransformationContext(source_content="original")
        
        context.update_content("modified", ScssTransformationStep.MIXIN_CONVERSION)
        
        assert context.current_content == "modified"
        assert context.processing_step == ScssTransformationStep.MIXIN_CONVERSION
    
    def test_processing_summary(self):
        """Test getting processing summary"""
        context = ScssTransformationContext(source_content="test")
        context.variables = [ScssVariable(name="test", value="value")]
        context.add_transformation("test_transformation")
        
        summary = context.get_processing_summary()
        
        assert summary["variables_found"] == 1
        assert summary["transformations_applied"] == 1
        assert summary["current_step"] == ScssTransformationStep.VARIABLE_PROCESSING.value


class TestScssProcessingConfig:
    """Test SCSS processing configuration model"""
    
    def test_default_config(self):
        """Test default configuration values"""
        config = ScssProcessingConfig()
        
        assert config.mode == ScssProcessingMode.FULL
        assert config.convert_variables is True
        assert config.convert_mixins is True
        assert config.validate_syntax is True
        assert config.max_file_size_mb == 10
        assert config.target_browsers == ["last 2 versions", "IE 11"]
    
    def test_config_validation(self):
        """Test configuration validation"""
        # Valid config
        config = ScssProcessingConfig(max_file_size_mb=5)
        assert config.max_file_size_mb == 5
        
        # Invalid file size
        with pytest.raises(ValueError):
            ScssProcessingConfig(max_file_size_mb=0)
        
        with pytest.raises(ValueError):
            ScssProcessingConfig(max_file_size_mb=150)


class TestScssProcessingResult:
    """Test SCSS processing result model"""
    
    def test_result_creation(self):
        """Test basic result creation"""
        result = ScssProcessingResult(
            success=True,
            output_content="processed content"
        )
        
        assert result.success is True
        assert result.output_content == "processed content"
        assert result.output_size_bytes == len("processed content".encode('utf-8'))
    
    def test_error_summary(self):
        """Test error summary generation"""
        result = ScssProcessingResult(
            success=False,
            syntax_errors=[
                ScssProcessingError(error_type="syntax", message="error1"),
                ScssProcessingError(error_type="syntax", message="error2")
            ],
            warnings=[
                ScssProcessingError(error_type="warning", message="warning1")
            ]
        )
        
        summary = result.get_error_summary()
        
        assert summary["syntax_errors"] == 2
        assert summary["warnings"] == 1
        assert summary["total_issues"] == 3
    
    def test_transformation_summary(self):
        """Test transformation summary generation"""
        result = ScssProcessingResult(
            success=True,
            variables_converted=5,
            mixins_converted=3,
            input_size_bytes=1000,
            output_size_bytes=800,
            processing_time_seconds=1.5
        )
        
        summary = result.get_transformation_summary()
        
        assert summary["variables_converted"] == 5
        assert summary["mixins_converted"] == 3
        assert summary["size_reduction_percent"] == 20.0
        assert summary["processing_time"] == 1.5


class TestScssValidationResult:
    """Test SCSS validation result model"""
    
    def test_validation_result_creation(self):
        """Test basic validation result creation"""
        result = ScssValidationResult(is_valid=True)
        
        assert result.is_valid is True
        assert result.errors == []
        assert result.warnings == []
        assert result.balanced_braces is True
    
    def test_validation_summary(self):
        """Test validation summary generation"""
        # Valid result
        valid_result = ScssValidationResult(is_valid=True)
        assert valid_result.get_validation_summary() == "✅ SCSS validation passed"
        
        # Invalid result with errors
        invalid_result = ScssValidationResult(
            is_valid=False,
            errors=[ScssProcessingError(error_type="syntax", message="error")],
            warnings=[ScssProcessingError(error_type="warning", message="warning")]
        )
        assert "❌ SCSS validation failed: 1 errors, 1 warnings" in invalid_result.get_validation_summary()
    
    def test_remaining_scss_analysis(self):
        """Test remaining SCSS content analysis"""
        result = ScssValidationResult(
            is_valid=True,
            has_remaining_scss=True,
            remaining_variables=["$primary", "$secondary"],
            remaining_mixins=["flexbox", "clearfix"],
            remaining_functions=["lighten", "darken"]
        )
        
        assert result.has_remaining_scss is True
        assert len(result.remaining_variables) == 2
        assert len(result.remaining_mixins) == 2
        assert len(result.remaining_functions) == 2


class TestScssProcessingError:
    """Test SCSS processing error model"""
    
    def test_error_creation(self):
        """Test basic error creation"""
        error = ScssProcessingError(
            error_type="syntax_error",
            message="Missing semicolon",
            line_number=42,
            source_snippet="color: red",
            severity="error"
        )
        
        assert error.error_type == "syntax_error"
        assert error.message == "Missing semicolon"
        assert error.line_number == 42
        assert error.source_snippet == "color: red"
        assert error.severity == "error"
    
    def test_error_defaults(self):
        """Test error default values"""
        error = ScssProcessingError(
            error_type="test_error",
            message="Test message"
        )
        
        assert error.line_number is None
        assert error.column_number is None
        assert error.source_snippet is None
        assert error.severity == "error"
        assert error.suggestion is None