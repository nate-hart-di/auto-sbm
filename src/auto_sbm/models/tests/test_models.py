"""Comprehensive tests for Auto-SBM Pydantic models"""

import pytest
from pathlib import Path
import tempfile
from datetime import datetime, timedelta
from typing import List

from ..theme import (
    Theme, ThemeType, ThemeStatus, OEMType, ThemeCollection
)
from ..migration import (
    MigrationConfig, MigrationResult, MigrationStep, MigrationMode,
    MigrationPriority, StepResult, BatchMigrationConfig, BatchMigrationResult
)
from ..scss import (
    ScssVariable, ScssVariableContext, ScssVariableType,
    ScssProcessingResult, ScssConversionContext, ScssProcessingMode,
    BatchScssProcessingResult
)


class TestThemeModels:
    """Test theme-related models"""
    
    @pytest.fixture
    def temp_theme_dir(self):
        """Create temporary theme directory for testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            theme_path = Path(temp_dir) / "test-theme"
            theme_path.mkdir()
            
            # Create some test files
            (theme_path / "style.scss").write_text("$primary: #007bff;")
            (theme_path / "template.html").write_text("<html></html>")
            
            yield theme_path
    
    def test_theme_creation_valid(self, temp_theme_dir):
        """Test valid theme creation"""
        theme = Theme(
            name="test-theme",
            type=ThemeType.LEGACY,
            source_path=temp_theme_dir
        )
        
        assert theme.name == "test-theme"
        assert theme.type == ThemeType.LEGACY
        assert theme.status == ThemeStatus.PENDING
        assert theme.oem_type == OEMType.GENERIC
        assert theme.source_path == temp_theme_dir
        assert theme.slug == "test-theme"  # Auto-generated
    
    def test_theme_name_validation(self):
        """Test theme name validation"""
        with pytest.raises(ValueError, match="String should have at least 1 character"):
            Theme(
                name="",  # Empty name should fail
                type=ThemeType.LEGACY,
                source_path=Path("/test/path")
            )
    
    def test_theme_source_path_validation(self):
        """Test source path validation"""
        with pytest.raises(ValueError, match="Source path does not exist"):
            Theme(
                name="test-theme",
                type=ThemeType.LEGACY,
                source_path=Path("/nonexistent/path")
            )
    
    def test_theme_slug_generation(self, temp_theme_dir):
        """Test automatic slug generation"""
        theme = Theme(
            name="My Theme Name!",
            type=ThemeType.LEGACY,
            source_path=temp_theme_dir
        )
        
        assert theme.slug == "my-theme-name"
    
    def test_theme_status_update(self, temp_theme_dir):
        """Test theme status update with timestamps"""
        theme = Theme(
            name="test-theme",
            type=ThemeType.LEGACY,
            source_path=temp_theme_dir
        )
        
        # Test starting migration
        start_time = datetime.now()
        theme.update_status(ThemeStatus.IN_PROGRESS)
        
        assert theme.status == ThemeStatus.IN_PROGRESS
        assert theme.migration_started_at is not None
        assert theme.migration_started_at >= start_time
        
        # Test completing migration
        completion_time = datetime.now()
        theme.update_status(ThemeStatus.COMPLETED)
        
        assert theme.status == ThemeStatus.COMPLETED
        assert theme.migration_completed_at is not None
        assert theme.migration_completed_at >= completion_time
    
    def test_theme_expected_output_files(self, temp_theme_dir):
        """Test expected output files generation"""
        output_dir = temp_theme_dir.parent / "output"
        theme = Theme(
            name="test-theme",
            type=ThemeType.LEGACY,
            source_path=temp_theme_dir,
            destination_path=output_dir
        )
        
        expected_files = theme.get_expected_output_files()
        
        assert len(expected_files) == 4
        assert any("sb-inside.scss" in str(f) for f in expected_files)
        assert any("sb-vdp.scss" in str(f) for f in expected_files)
        assert any("sb-vrp.scss" in str(f) for f in expected_files)
        assert any("sb-home.scss" in str(f) for f in expected_files)
    
    def test_theme_collection(self, temp_theme_dir):
        """Test theme collection operations"""
        collection = ThemeCollection()
        
        theme1 = Theme(
            name="theme-1",
            type=ThemeType.LEGACY,
            source_path=temp_theme_dir
        )
        
        theme2 = Theme(
            name="theme-2",
            type=ThemeType.SITE_BUILDER,
            source_path=temp_theme_dir,
            status=ThemeStatus.COMPLETED
        )
        
        collection.add_theme(theme1)
        collection.add_theme(theme2)
        
        assert len(collection.themes) == 2
        assert collection.get_theme_by_name("theme-1") == theme1
        assert collection.get_theme_by_name("nonexistent") is None
        
        pending_themes = collection.get_themes_by_status(ThemeStatus.PENDING)
        assert len(pending_themes) == 1
        assert pending_themes[0] == theme1
        
        completed_themes = collection.get_themes_by_status(ThemeStatus.COMPLETED)
        assert len(completed_themes) == 1
        assert completed_themes[0] == theme2
    
    def test_theme_collection_duplicate_name(self, temp_theme_dir):
        """Test theme collection rejects duplicate names"""
        collection = ThemeCollection()
        
        theme1 = Theme(
            name="duplicate-name",
            type=ThemeType.LEGACY,
            source_path=temp_theme_dir
        )
        
        theme2 = Theme(
            name="duplicate-name",
            type=ThemeType.SITE_BUILDER,
            source_path=temp_theme_dir
        )
        
        collection.add_theme(theme1)
        
        with pytest.raises(ValueError, match="already exists"):
            collection.add_theme(theme2)


class TestMigrationModels:
    """Test migration-related models"""
    
    @pytest.fixture
    def sample_theme(self, temp_theme_dir):
        """Create sample theme for testing"""
        return Theme(
            name="test-theme",
            type=ThemeType.LEGACY,
            source_path=temp_theme_dir
        )
    
    @pytest.fixture 
    def temp_theme_dir(self):
        """Create temporary theme directory for testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            theme_path = Path(temp_dir) / "test-theme"
            theme_path.mkdir()
            (theme_path / "style.scss").write_text("$primary: #007bff;")
            yield theme_path
    
    def test_migration_config_creation(self, sample_theme):
        """Test migration configuration creation"""
        config = MigrationConfig(theme=sample_theme)
        
        assert config.theme == sample_theme
        assert config.mode == MigrationMode.FULL
        assert config.priority == MigrationPriority.NORMAL
        assert config.backup_enabled is True
        assert config.validation_enabled is True
        assert config.rich_ui_enabled is True
        assert config.max_concurrent_files == 10
        assert len(config.enabled_steps) == len(MigrationStep)
    
    def test_migration_config_validation(self, sample_theme):
        """Test migration configuration validation"""
        # Test invalid max_concurrent_files
        with pytest.raises(ValueError):
            MigrationConfig(
                theme=sample_theme,
                max_concurrent_files=0  # Should be >= 1
            )
        
        with pytest.raises(ValueError):
            MigrationConfig(
                theme=sample_theme,
                max_concurrent_files=100  # Should be <= 50
            )
    
    def test_migration_config_step_ordering(self, sample_theme):
        """Test that git_setup is ordered first"""
        config = MigrationConfig(
            theme=sample_theme,
            enabled_steps=[
                MigrationStep.SCSS_MIGRATION,
                MigrationStep.GIT_SETUP,
                MigrationStep.VALIDATION
            ]
        )
        
        # git_setup should be moved to first position
        assert config.enabled_steps[0] == MigrationStep.GIT_SETUP
    
    def test_step_result_completion(self):
        """Test step result completion tracking"""
        step_result = StepResult(step=MigrationStep.SCSS_MIGRATION)
        start_time = step_result.start_time
        
        # Complete the step
        step_result.complete(success=True)
        
        assert step_result.success is True
        assert step_result.end_time is not None
        assert step_result.end_time >= start_time
        assert step_result.duration_seconds is not None
        assert step_result.duration_seconds >= 0
    
    def test_migration_result_step_management(self, sample_theme):
        """Test migration result step management"""
        result = MigrationResult(
            success=True,
            theme_name=sample_theme.name,
            migration_mode=MigrationMode.FULL
        )
        
        # Add step results
        git_step = StepResult(step=MigrationStep.GIT_SETUP, files_processed=2)
        git_step.complete(success=True)
        
        scss_step = StepResult(step=MigrationStep.SCSS_MIGRATION, files_processed=5, files_failed=1)
        scss_step.errors.append("SCSS parsing error")
        scss_step.complete(success=False)
        
        result.add_step_result(git_step)
        result.add_step_result(scss_step)
        
        assert len(result.step_results) == 2
        assert result.files_processed == 7  # 2 + 5
        assert result.files_failed == 1
        assert len(result.errors) == 1
        assert result.get_success_rate() == 0.5  # 1 success, 1 failure
        
        # Test getting specific step
        git_result = result.get_step_result(MigrationStep.GIT_SETUP)
        assert git_result == git_step
        
        # Test getting failed steps
        failed_steps = result.get_failed_steps()
        assert len(failed_steps) == 1
        assert failed_steps[0] == scss_step
    
    def test_migration_result_performance_summary(self, sample_theme):
        """Test migration result performance summary"""
        result = MigrationResult(
            success=True,
            theme_name=sample_theme.name,
            migration_mode=MigrationMode.FULL,
            files_processed=10
        )
        
        # Simulate completed migration
        result.complete(success=True)
        
        summary = result.get_performance_summary()
        
        assert "total_duration" in summary
        assert "files_per_second" in summary
        assert "success_rate" in summary
        assert summary["success_rate"] == 1.0  # No step results = 100% success
    
    def test_batch_migration_config(self, sample_theme):
        """Test batch migration configuration"""
        theme2 = Theme(
            name="theme-2",
            type=ThemeType.LEGACY,
            source_path=sample_theme.source_path
        )
        
        template_config = MigrationConfig(theme=sample_theme)
        
        batch_config = BatchMigrationConfig(
            themes=[sample_theme, theme2],
            migration_config_template=template_config,
            max_concurrent_migrations=2
        )
        
        assert len(batch_config.themes) == 2
        assert batch_config.max_concurrent_migrations == 2
        assert batch_config.continue_on_failure is True


class TestScssModels:
    """Test SCSS-related models"""
    
    def test_scss_variable_creation(self):
        """Test SCSS variable creation and validation"""
        variable = ScssVariable(
            name="primary-color",
            value="#007bff",
            original_value="#007bff",
            line_number=5
        )
        
        assert variable.name == "primary-color"
        assert variable.value == "#007bff"
        assert variable.context == ScssVariableContext.GLOBAL
        assert variable.variable_type == ScssVariableType.UNKNOWN
        assert variable.get_full_name() == "$primary-color"
    
    def test_scss_variable_name_validation(self):
        """Test SCSS variable name validation"""
        # Test removing $ prefix
        variable = ScssVariable(
            name="$primary-color",
            value="#007bff",
            original_value="#007bff",
            line_number=1
        )
        assert variable.name == "primary-color"
        
        # Test invalid name
        with pytest.raises(ValueError, match="Invalid SCSS variable name"):
            ScssVariable(
                name="123invalid",  # Can't start with number
                value="#007bff",
                original_value="#007bff",
                line_number=1
            )
    
    def test_scss_variable_type_detection(self):
        """Test automatic variable type detection"""
        # Test color detection
        color_var = ScssVariable(
            name="primary",
            value="#007bff",
            original_value="#007bff",
            line_number=1
        )
        assert color_var.is_color_variable() is True
        assert color_var.auto_detect_type() == ScssVariableType.COLOR
        
        # Test size detection
        size_var = ScssVariable(
            name="font-size",
            value="16px",
            original_value="16px",
            line_number=2
        )
        assert size_var.is_size_variable() is True
        assert size_var.auto_detect_type() == ScssVariableType.SIZE
        
        # Test string detection
        string_var = ScssVariable(
            name="font-family",
            value='"Helvetica, Arial, sans-serif"',
            original_value='"Helvetica, Arial, sans-serif"',
            line_number=3
        )
        assert string_var.auto_detect_type() == ScssVariableType.STRING
        
        # Test boolean detection
        bool_var = ScssVariable(
            name="debug",
            value="true",
            original_value="true",
            line_number=4
        )
        assert bool_var.auto_detect_type() == ScssVariableType.BOOLEAN
        
        # Test number detection
        number_var = ScssVariable(
            name="z-index",
            value="100",
            original_value="100",
            line_number=5
        )
        assert number_var.auto_detect_type() == ScssVariableType.NUMBER
    
    def test_scss_conversion_context(self):
        """Test SCSS conversion context management"""
        with tempfile.NamedTemporaryFile(suffix=".scss", delete=False) as temp_file:
            source_file = Path(temp_file.name)
            
        context = ScssConversionContext(
            source_file=source_file,
            mode=ScssProcessingMode.STANDARD
        )
        
        # Add variables
        var1 = ScssVariable(
            name="primary",
            value="#007bff",
            original_value="#007bff",
            line_number=1,
            context=ScssVariableContext.GLOBAL
        )
        
        var2 = ScssVariable(
            name="secondary",
            value="#6c757d",
            original_value="#6c757d",
            line_number=2,
            context=ScssVariableContext.MIXIN
        )
        
        context.add_variable(var1)
        context.add_variable(var2)
        
        assert len(context.all_variables) == 2
        assert len(context.global_variables) == 1  # Only var1 is global
        
        # Test retrieval methods
        found_var = context.get_variable_by_name("primary")
        assert found_var == var1
        
        found_var_with_prefix = context.get_variable_by_name("$primary")
        assert found_var_with_prefix == var1
        
        global_vars = context.get_variables_by_context(ScssVariableContext.GLOBAL)
        assert len(global_vars) == 1
        assert global_vars[0] == var1
        
        # Cleanup
        source_file.unlink()
    
    def test_scss_processing_result(self):
        """Test SCSS processing result tracking"""
        with tempfile.NamedTemporaryFile(suffix=".scss", delete=False) as temp_file:
            source_file = Path(temp_file.name)
            
        result = ScssProcessingResult(
            success=True,
            source_file=source_file,
            original_content="$primary: #007bff;",
            processed_content="$primary: var(--primary-color);",
            original_size_bytes=20,
            processed_size_bytes=35
        )
        
        # Add variables
        converted_var = ScssVariable(
            name="primary",
            value="var(--primary-color)",
            original_value="#007bff",
            line_number=1,
            is_converted=True
        )
        
        skipped_var = ScssVariable(
            name="secondary",
            value="#6c757d",
            original_value="#6c757d", 
            line_number=2
        )
        
        result.add_converted_variable(converted_var)
        result.add_skipped_variable(skipped_var, "Complex expression")
        result.complete(success=True)
        
        assert len(result.variables_converted) == 1
        assert len(result.variables_skipped) == 1
        assert result.variables_found == 2
        assert len(result.warnings) == 1  # Skipped variable warning
        assert result.end_time is not None
        assert result.processing_duration_seconds is not None
        assert result.size_change_percent == 75.0  # (35-20)/20 * 100
        
        # Test conversion stats
        stats = result.get_conversion_stats()
        assert stats["total_variables"] == 2
        assert stats["converted_count"] == 1
        assert stats["skipped_count"] == 1
        assert stats["conversion_rate"] == 0.5
        
        # Cleanup
        source_file.unlink()
    
    def test_batch_scss_processing_result(self):
        """Test batch SCSS processing result aggregation"""
        batch_result = BatchScssProcessingResult(success=True)
        
        # Create mock file results
        with tempfile.NamedTemporaryFile(suffix=".scss", delete=False) as temp_file1:
            file1 = Path(temp_file1.name)
        with tempfile.NamedTemporaryFile(suffix=".scss", delete=False) as temp_file2:
            file2 = Path(temp_file2.name)
            
        result1 = ScssProcessingResult(
            success=True,
            source_file=file1,
            original_content="$primary: #007bff;",
            processed_content="$primary: var(--primary);"
        )
        result1.variables_converted = [
            ScssVariable(name="primary", value="var(--primary)", original_value="#007bff", line_number=1)
        ]
        result1.complete(success=True)
        
        result2 = ScssProcessingResult(
            success=False,
            source_file=file2,
            original_content="$invalid: broken;",
            processed_content="$invalid: broken;"
        )
        result2.errors = ["Parse error"]
        result2.complete(success=False)
        
        batch_result.add_file_result(result1)
        batch_result.add_file_result(result2)
        batch_result.complete()
        
        assert batch_result.files_processed == 2
        assert batch_result.files_successful == 1
        assert batch_result.files_failed == 1
        assert batch_result.success is False  # Overall failure due to 1 failed file
        assert batch_result.total_variables_converted == 1
        assert len(batch_result.total_errors) == 1
        assert batch_result.get_overall_success_rate() == 0.5
        
        # Test performance summary
        summary = batch_result.get_performance_summary()
        assert summary["total_files"] == 2
        assert summary["success_rate"] == 0.5
        assert summary["conversion_rate"] == 1.0  # All found variables were converted
        
        # Cleanup
        file1.unlink()
        file2.unlink()


class TestModelIntegration:
    """Test integration between different models"""
    
    @pytest.fixture
    def temp_theme_dir(self):
        """Create temporary theme directory for testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            theme_path = Path(temp_dir) / "test-theme"
            theme_path.mkdir()
            (theme_path / "style.scss").write_text("$primary: #007bff;")
            yield theme_path
    
    def test_theme_migration_integration(self, temp_theme_dir):
        """Test integration between theme and migration models"""
        # Create theme
        theme = Theme(
            name="integration-test",
            type=ThemeType.LEGACY,
            source_path=temp_theme_dir
        )
        
        # Create migration config
        config = MigrationConfig(
            theme=theme,
            mode=MigrationMode.FULL,
            enabled_steps=[
                MigrationStep.GIT_SETUP,
                MigrationStep.SCSS_MIGRATION,
                MigrationStep.VALIDATION
            ]
        )
        
        # Create migration result
        result = MigrationResult(
            success=True,
            theme_name=theme.name,
            migration_mode=config.mode
        )
        
        # Add step results
        for step in config.enabled_steps:
            step_result = StepResult(step=step, files_processed=1)
            step_result.complete(success=True)
            result.add_step_result(step_result)
        
        result.complete(success=True)
        
        # Update theme status
        theme.update_status(ThemeStatus.COMPLETED)
        
        # Verify integration
        assert result.theme_name == theme.name
        assert len(result.step_results) == len(config.enabled_steps)
        assert result.get_success_rate() == 1.0
        assert theme.status == ThemeStatus.COMPLETED
        assert theme.migration_completed_at is not None
    
    def test_scss_migration_integration(self, temp_theme_dir):
        """Test integration between SCSS and migration models"""
        # Create SCSS file with content
        scss_file = temp_theme_dir / "variables.scss"
        scss_content = """
$primary-color: #007bff;
$secondary-color: #6c757d;
$font-size: 16px;
"""
        scss_file.write_text(scss_content)
        
        # Create theme with SCSS files
        theme = Theme(
            name="scss-integration-test",
            type=ThemeType.LEGACY,
            source_path=temp_theme_dir,
            scss_files=[scss_file]
        )
        
        # Create SCSS processing result
        scss_result = ScssProcessingResult(
            success=True,
            source_file=scss_file,
            original_content=scss_content,
            processed_content=scss_content.replace("#007bff", "var(--primary)")
        )
        
        # Add converted variables
        primary_var = ScssVariable(
            name="primary-color",
            value="var(--primary)",
            original_value="#007bff",
            line_number=2,
            is_converted=True
        )
        scss_result.add_converted_variable(primary_var)
        scss_result.complete(success=True)
        
        # Create migration step for SCSS processing
        scss_step = StepResult(
            step=MigrationStep.SCSS_MIGRATION,
            files_processed=1,
            metadata={"scss_result": scss_result.model_dump()}
        )
        scss_step.complete(success=True)
        
        # Verify integration
        assert len(theme.scss_files) == 1
        assert theme.scss_files[0] == scss_file
        assert scss_result.success is True
        assert len(scss_result.variables_converted) == 1
        assert scss_step.step == MigrationStep.SCSS_MIGRATION
        assert scss_step.files_processed == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])