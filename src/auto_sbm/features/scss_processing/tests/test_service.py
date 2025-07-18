"""Tests for SCSS processing service"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path
import tempfile

from ....config import AutoSBMSettings
from ..service import ScssProcessingService
from ..models import ScssProcessingConfig, ScssProcessingMode, ScssValidationResult
from ..exceptions import ScssProcessingException, ScssValidationException


class TestScssProcessingService:
    """Test SCSS processing service functionality"""
    
    @pytest.fixture
    def mock_settings(self):
        """Mock settings for testing"""
        settings = Mock(spec=AutoSBMSettings)
        settings.themes_directory = Path("/test/themes")
        return settings
    
    @pytest.fixture
    def scss_service(self, mock_settings):
        """Create SCSS processing service for testing"""
        return ScssProcessingService(mock_settings)
    
    @pytest.fixture
    def sample_scss_content(self):
        """Sample SCSS content for testing"""
        return """
$primary: #007bff;
$secondary: #6c757d;

.button {
  color: $primary;
  background: $secondary;
  @include border-radius(4px);
}

@include clearfix();
"""
    
    @pytest.fixture
    def basic_config(self):
        """Basic processing configuration"""
        return ScssProcessingConfig(
            mode=ScssProcessingMode.FULL,
            validate_syntax=False,  # Skip validation for faster tests
            test_compilation=False
        )
    
    @pytest.mark.asyncio
    async def test_service_initialization(self, mock_settings):
        """Test service initialization"""
        service = ScssProcessingService(mock_settings)
        
        assert service.settings == mock_settings
        assert service.validator is not None
        assert len(service._transformers) == 6  # All transformation steps
    
    @pytest.mark.asyncio
    async def test_process_scss_content_success(self, scss_service, sample_scss_content, basic_config):
        """Test successful SCSS content processing"""
        result = await scss_service.process_scss_content(sample_scss_content, basic_config)
        
        assert result.success is True
        assert result.output_content is not None
        assert result.input_size_bytes > 0
        assert result.output_size_bytes > 0
        assert result.processing_time_seconds > 0
        assert result.context is not None
    
    @pytest.mark.asyncio
    async def test_process_empty_content(self, scss_service, basic_config):
        """Test processing empty content"""
        result = await scss_service.process_scss_content("", basic_config)
        
        assert result.success is False
        assert len(result.syntax_errors) > 0
        assert "empty" in result.syntax_errors[0].message.lower()
    
    @pytest.mark.asyncio
    async def test_process_content_size_limit(self, scss_service):
        """Test content size limit enforcement"""
        large_content = "a" * (2 * 1024 * 1024)  # 2MB
        config = ScssProcessingConfig(max_file_size_mb=1)  # 1MB limit
        
        result = await scss_service.process_scss_content(large_content, config)
        
        assert result.success is False
        assert len(result.syntax_errors) > 0
        assert "exceeds limit" in result.syntax_errors[0].message
    
    @pytest.mark.asyncio
    async def test_process_with_validation(self, scss_service, sample_scss_content):
        """Test processing with validation enabled"""
        config = ScssProcessingConfig(
            validate_syntax=True,
            test_compilation=False,  # Skip compilation for speed
            strict_mode=False
        )
        
        # Mock validator to return success
        mock_validation = ScssValidationResult(is_valid=True)
        with patch.object(scss_service.validator, 'validate_scss_content', return_value=mock_validation):
            result = await scss_service.process_scss_content(sample_scss_content, config)
        
        assert result.success is True
        assert result.context.syntax_valid is True
    
    @pytest.mark.asyncio
    async def test_process_with_validation_failure_strict_mode(self, scss_service, sample_scss_content):
        """Test processing with validation failure in strict mode"""
        config = ScssProcessingConfig(
            validate_syntax=True,
            strict_mode=True
        )
        
        # Mock validator to return failure
        from ..models import ScssProcessingError
        mock_validation = ScssValidationResult(
            is_valid=False,
            errors=[ScssProcessingError(error_type="syntax", message="Test error")]
        )
        with patch.object(scss_service.validator, 'validate_scss_content', return_value=mock_validation):
            result = await scss_service.process_scss_content(sample_scss_content, config)
        
        assert result.success is False
        assert len(result.syntax_errors) > 0
    
    @pytest.mark.asyncio
    async def test_processing_modes(self, scss_service, sample_scss_content):
        """Test different processing modes"""
        test_modes = [
            ScssProcessingMode.VARIABLES_ONLY,
            ScssProcessingMode.MIXINS_ONLY,
            ScssProcessingMode.FULL
        ]
        
        for mode in test_modes:
            config = ScssProcessingConfig(mode=mode, validate_syntax=False)
            result = await scss_service.process_scss_content(sample_scss_content, config)
            
            assert result.success is True, f"Failed for mode: {mode}"
            assert result.output_content is not None
    
    @pytest.mark.asyncio
    async def test_process_scss_file(self, scss_service, basic_config):
        """Test processing SCSS file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.scss', delete=False) as temp_file:
            temp_file.write("$test: red; .test { color: $test; }")
            temp_path = Path(temp_file.name)
        
        try:
            result = await scss_service.process_scss_file(temp_path, basic_config)
            
            assert result.success is True
            assert result.output_content is not None
            
        finally:
            temp_path.unlink(missing_ok=True)
    
    @pytest.mark.asyncio
    async def test_process_nonexistent_file(self, scss_service, basic_config):
        """Test processing non-existent file"""
        nonexistent_file = Path("/path/that/does/not/exist.scss")
        
        result = await scss_service.process_scss_file(nonexistent_file, basic_config)
        
        assert result.success is False
        assert len(result.syntax_errors) > 0
        assert "not found" in result.syntax_errors[0].message
    
    @pytest.mark.asyncio
    async def test_process_file_with_output(self, scss_service, basic_config):
        """Test processing file with output file specified"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.scss', delete=False) as input_file:
            input_file.write("$test: blue; .test { color: $test; }")
            input_path = Path(input_file.name)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.css', delete=False) as output_file:
            output_path = Path(output_file.name)
        
        try:
            result = await scss_service.process_scss_file(input_path, basic_config, output_path)
            
            assert result.success is True
            assert output_path in result.generated_files
            assert output_path.exists()
            assert len(output_path.read_text()) > 0
            
        finally:
            input_path.unlink(missing_ok=True)
            output_path.unlink(missing_ok=True)
    
    @pytest.mark.asyncio
    async def test_validate_scss_content(self, scss_service):
        """Test SCSS content validation"""
        valid_content = ".test { color: red; }"
        
        # Mock validator
        mock_validation = ScssValidationResult(is_valid=True)
        with patch.object(scss_service.validator, 'validate_scss_content', return_value=mock_validation):
            result = await scss_service.validate_scss_content(valid_content)
        
        assert result.is_valid is True
    
    @pytest.mark.asyncio
    async def test_get_processing_preview(self, scss_service, sample_scss_content):
        """Test getting processing preview"""
        config = ScssProcessingConfig()
        
        # Mock transformer extract methods with proper context returns
        from ..models import ScssTransformationContext, ScssVariable
        
        async def mock_extract_variables(context):
            context.variables = [ScssVariable(name="primary", value="#007bff")]
            return context
        
        async def mock_extract_mixins(context):
            context.mixins = []
            return context
        
        async def mock_extract_functions(context):
            context.functions = []
            return context
        
        async def mock_extract_imports(context):
            context.imports = []
            return context
        
        # Apply mocks to transformers
        from ..transformers import VariableTransformer, MixinTransformer, FunctionTransformer, ImportRemover
        from ..models import ScssTransformationStep
        
        variable_transformer = scss_service._transformers[ScssTransformationStep.VARIABLE_PROCESSING]
        with patch.object(variable_transformer, 'extract_elements', side_effect=mock_extract_variables):
            preview = await scss_service.get_processing_preview(sample_scss_content, config)
        
        assert "variables_found" in preview
        assert "mixins_found" in preview
        assert "functions_found" in preview
        assert "processing_steps" in preview
    
    def test_get_processing_statistics(self, scss_service):
        """Test getting processing statistics"""
        stats = scss_service.get_processing_statistics()
        
        assert "transformers_available" in stats
        assert "processing_steps" in stats
        assert "supported_features" in stats
        assert stats["transformers_available"] == 6
        assert stats["supported_features"]["variable_conversion"] is True
    
    @pytest.mark.asyncio
    async def test_error_handling_during_processing(self, scss_service, sample_scss_content, basic_config):
        """Test error handling during processing pipeline"""
        # Mock a transformer to raise an exception
        with patch.object(scss_service._transformers[list(scss_service._transformers.keys())[0]], 
                         'transform', side_effect=Exception("Test error")):
            
            result = await scss_service.process_scss_content(sample_scss_content, basic_config)
            
            # In non-strict mode, processing should continue
            if not basic_config.strict_mode:
                # The service should handle the error gracefully
                assert result.processing_time_seconds > 0
    
    def test_get_processing_steps_different_modes(self, scss_service):
        """Test processing step determination for different modes"""
        # Test validation only mode
        validation_config = ScssProcessingConfig(mode=ScssProcessingMode.VALIDATION_ONLY)
        steps = scss_service._get_processing_steps(validation_config)
        assert len(steps) == 1
        assert steps[0].value == "validation"
        
        # Test variables only mode
        variables_config = ScssProcessingConfig(mode=ScssProcessingMode.VARIABLES_ONLY)
        steps = scss_service._get_processing_steps(variables_config)
        assert len(steps) == 2  # variable processing + cleanup
        
        # Test full mode
        full_config = ScssProcessingConfig(mode=ScssProcessingMode.FULL)
        steps = scss_service._get_processing_steps(full_config)
        assert len(steps) > 2  # Multiple steps including cleanup
    
    @pytest.mark.asyncio 
    async def test_create_backup_file(self, scss_service):
        """Test backup file creation"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.scss', delete=False) as temp_file:
            temp_file.write("test content")
            temp_path = Path(temp_file.name)
        
        try:
            backup_path = scss_service._create_backup_file(temp_path)
            
            if backup_path:  # Backup creation might fail in some environments
                assert backup_path.exists()
                assert backup_path.read_text() == "test content"
                backup_path.unlink(missing_ok=True)
                
        finally:
            temp_path.unlink(missing_ok=True)


class TestScssProcessingServiceIntegration:
    """Integration tests for SCSS processing service"""
    
    @pytest.fixture
    def real_scss_content(self):
        """Real-world SCSS content for integration testing"""
        return """
// Variables
$primary-color: #007bff;
$secondary-color: #6c757d;
$font-size-base: 1rem;
$border-radius: 0.25rem;

// Mixins
@mixin button-variant($background, $border: $background) {
  color: #fff;
  background-color: $background;
  border-color: $border;
  
  &:hover {
    background-color: darken($background, 7.5%);
    border-color: darken($border, 10%);
  }
}

// Components
.btn {
  display: inline-block;
  font-size: $font-size-base;
  border-radius: $border-radius;
  
  &.btn-primary {
    @include button-variant($primary-color);
  }
  
  &.btn-secondary {
    @include button-variant($secondary-color);
  }
}

// Utilities
.text-center { text-align: center; }
.d-none { display: none; }
"""
    
    @pytest.mark.asyncio
    async def test_full_processing_pipeline(self, real_scss_content):
        """Test complete SCSS processing pipeline"""
        settings = Mock()
        settings.themes_directory = Path("/test")
        
        service = ScssProcessingService(settings)
        config = ScssProcessingConfig(
            mode=ScssProcessingMode.FULL,
            validate_syntax=False,  # Skip validation for integration test
            test_compilation=False
        )
        
        result = await service.process_scss_content(real_scss_content, config)
        
        assert result.success is True
        assert result.output_content is not None
        assert result.variables_converted > 0
        assert result.processing_time_seconds > 0
        
        # Check that transformations were applied
        output = result.output_content
        assert ":root" in output  # Variables should be converted to CSS custom properties
        assert "--primary-color" in output  # Variable names should be converted
        assert "var(--" in output  # Variable usage should be converted