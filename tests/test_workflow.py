"""
Tests for sbm.core.workflow module.

Tests migration workflow orchestration and step execution.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from sbm.core.workflow import MigrationWorkflow
from sbm.utils.errors import ValidationError, GitError, MigrationError


class TestMigrationWorkflow:
    """Test the MigrationWorkflow class."""
    
    def test_workflow_initialization(self, test_config):
        """Test workflow initialization."""
        workflow = MigrationWorkflow(test_config)
        assert workflow.config == test_config
        assert workflow.logger is not None
        assert workflow.current_step is None
        assert workflow.results == {}
    
    @patch('sbm.core.workflow.ValidationEngine')
    @patch('sbm.core.workflow.GitOperations')
    @patch('sbm.core.workflow.SiteInitializer')
    @patch('sbm.core.workflow.SCSSProcessor')
    @patch('sbm.core.workflow.OEMHandler')
    def test_workflow_run_success(self, mock_oem, mock_scss, mock_site, mock_git, mock_validator, test_config):
        """Test successful workflow execution."""
        # Setup mocks
        mock_validator_instance = Mock()
        mock_validator_instance.validate_theme.return_value = {"valid": True}
        mock_validator.return_value = mock_validator_instance
        
        mock_git_instance = Mock()
        mock_git_instance.create_branch.return_value = "test-branch"
        mock_git.return_value = mock_git_instance
        
        mock_site_instance = Mock()
        mock_site_instance.initialize.return_value = {"files_created": 4}
        mock_site.return_value = mock_site_instance
        
        mock_scss_instance = Mock()
        mock_scss_instance.process_theme.return_value = {"styles_migrated": 15}
        mock_scss.return_value = mock_scss_instance
        
        mock_oem_instance = Mock()
        mock_oem_instance.detect_oem.return_value = {"oem": "Stellantis", "brand": "Chrysler"}
        mock_oem.return_value = mock_oem_instance
        
        # Run workflow
        workflow = MigrationWorkflow(test_config)
        result = workflow.run("chryslerofportland", "prod", False, False)
        
        # Verify result
        assert result["success"] is True
        assert result["slug"] == "chryslerofportland"
        assert "duration" in result
        assert "steps_completed" in result
        
        # Verify all steps were called
        mock_validator_instance.validate_theme.assert_called_once()
        mock_oem_instance.detect_oem.assert_called_once()
        mock_git_instance.create_branch.assert_called_once()
        mock_site_instance.initialize.assert_called_once()
        mock_scss_instance.process_theme.assert_called_once()
    
    @patch('sbm.core.workflow.ValidationEngine')
    def test_workflow_validation_failure(self, mock_validator, test_config):
        """Test workflow with validation failure."""
        # Setup mock to fail validation
        mock_validator_instance = Mock()
        mock_validator_instance.validate_theme.side_effect = ValidationError("Theme not found")
        mock_validator.return_value = mock_validator_instance
        
        # Run workflow
        workflow = MigrationWorkflow(test_config)
        
        with pytest.raises(ValidationError):
            workflow.run("nonexistent", "prod", False, False)
    
    @patch('sbm.core.workflow.ValidationEngine')
    @patch('sbm.core.workflow.GitOperations')
    def test_workflow_git_failure(self, mock_git, mock_validator, test_config):
        """Test workflow with Git operation failure."""
        # Setup mocks
        mock_validator_instance = Mock()
        mock_validator_instance.validate_theme.return_value = {"valid": True}
        mock_validator.return_value = mock_validator_instance
        
        mock_git_instance = Mock()
        mock_git_instance.create_branch.side_effect = GitError("Branch creation failed")
        mock_git.return_value = mock_git_instance
        
        # Run workflow
        workflow = MigrationWorkflow(test_config)
        
        with pytest.raises(GitError):
            workflow.run("testtheme", "prod", False, False)
    
    @patch('sbm.core.workflow.ValidationEngine')
    @patch('sbm.core.workflow.GitOperations')
    @patch('sbm.core.workflow.SiteInitializer')
    @patch('sbm.core.workflow.SCSSProcessor')
    @patch('sbm.core.workflow.OEMHandler')
    def test_workflow_dry_run(self, mock_oem, mock_scss, mock_site, mock_git, mock_validator, test_config):
        """Test workflow in dry-run mode."""
        # Setup mocks
        mock_validator_instance = Mock()
        mock_validator_instance.validate_theme.return_value = {"valid": True}
        mock_validator.return_value = mock_validator_instance
        
        mock_oem_instance = Mock()
        mock_oem_instance.detect_oem.return_value = {"oem": "Stellantis", "brand": "Chrysler"}
        mock_oem.return_value = mock_oem_instance
        
        # Run workflow in dry-run mode
        workflow = MigrationWorkflow(test_config)
        result = workflow.run("testtheme", "prod", True, False)
        
        # Verify dry-run behavior
        assert result["success"] is True
        assert result["dry_run"] is True
        
        # Git operations should not be called in dry-run
        mock_git.assert_not_called()
        mock_site.assert_not_called()
        mock_scss.assert_not_called()
    
    @patch('sbm.core.workflow.ValidationEngine')
    @patch('sbm.core.workflow.OEMHandler')
    def test_workflow_stellantis_detection(self, mock_oem, mock_validator, test_config):
        """Test workflow with Stellantis brand detection."""
        # Setup mocks
        mock_validator_instance = Mock()
        mock_validator_instance.validate_theme.return_value = {"valid": True}
        mock_validator.return_value = mock_validator_instance
        
        mock_oem_instance = Mock()
        mock_oem_instance.detect_oem.return_value = {
            "oem": "Stellantis",
            "brand": "Chrysler",
            "enhanced_processing": True
        }
        mock_oem.return_value = mock_oem_instance
        
        # Run workflow
        workflow = MigrationWorkflow(test_config)
        result = workflow.run("chryslerofportland", "prod", True, False)
        
        # Verify Stellantis detection
        assert result["oem"] == "Stellantis"
        assert result["brand"] == "Chrysler"
        mock_oem_instance.detect_oem.assert_called_once_with("chryslerofportland")
    
    def test_workflow_step_tracking(self, test_config):
        """Test workflow step tracking."""
        workflow = MigrationWorkflow(test_config)
        
        # Test step progression
        workflow._set_current_step("validation")
        assert workflow.current_step == "validation"
        
        workflow._complete_step("validation", {"result": "success"})
        assert "validation" in workflow.results
        assert workflow.results["validation"]["result"] == "success"
    
    def test_workflow_error_handling(self, test_config):
        """Test workflow error handling and cleanup."""
        workflow = MigrationWorkflow(test_config)
        
        # Test error during step execution
        workflow._set_current_step("test_step")
        
        try:
            raise ValueError("Test error")
        except Exception as e:
            workflow._handle_step_error("test_step", e)
        
        # Verify error was recorded
        assert "test_step" in workflow.results
        assert workflow.results["test_step"]["success"] is False
        assert "Test error" in workflow.results["test_step"]["error"]
    
    @patch('sbm.core.workflow.ValidationEngine')
    @patch('sbm.core.workflow.GitOperations')
    @patch('sbm.core.workflow.SiteInitializer')
    @patch('sbm.core.workflow.SCSSProcessor')
    @patch('sbm.core.workflow.OEMHandler')
    def test_workflow_force_mode(self, mock_oem, mock_scss, mock_site, mock_git, mock_validator, test_config):
        """Test workflow in force mode."""
        # Setup mocks with some failures
        mock_validator_instance = Mock()
        mock_validator_instance.validate_theme.return_value = {"valid": False, "warnings": ["Minor issues"]}
        mock_validator.return_value = mock_validator_instance
        
        mock_oem_instance = Mock()
        mock_oem_instance.detect_oem.return_value = {"oem": "Unknown", "brand": "Unknown"}
        mock_oem.return_value = mock_oem_instance
        
        mock_git_instance = Mock()
        mock_git_instance.create_branch.return_value = "test-branch"
        mock_git.return_value = mock_git_instance
        
        mock_site_instance = Mock()
        mock_site_instance.initialize.return_value = {"files_created": 4}
        mock_site.return_value = mock_site_instance
        
        mock_scss_instance = Mock()
        mock_scss_instance.process_theme.return_value = {"styles_migrated": 10}
        mock_scss.return_value = mock_scss_instance
        
        # Run workflow in force mode
        workflow = MigrationWorkflow(test_config)
        result = workflow.run("testtheme", "prod", False, True)
        
        # Should succeed despite validation warnings
        assert result["success"] is True
        assert result["force_mode"] is True
    
    def test_workflow_environment_handling(self, test_config):
        """Test workflow environment-specific behavior."""
        workflow = MigrationWorkflow(test_config)
        
        # Test different environments
        environments = ["prod", "staging", "dev"]
        
        for env in environments:
            # Should accept valid environments
            assert workflow._validate_environment(env) is True
        
        # Should reject invalid environment
        assert workflow._validate_environment("invalid") is False
    
    @patch('sbm.core.workflow.ValidationEngine')
    @patch('sbm.core.workflow.OEMHandler')
    def test_workflow_partial_failure(self, mock_oem, mock_validator, test_config):
        """Test workflow behavior with partial failures."""
        # Setup mocks
        mock_validator_instance = Mock()
        mock_validator_instance.validate_theme.return_value = {"valid": True}
        mock_validator.return_value = mock_validator_instance
        
        mock_oem_instance = Mock()
        mock_oem_instance.detect_oem.return_value = {"oem": "Stellantis", "brand": "Chrysler"}
        mock_oem.return_value = mock_oem_instance
        
        # Mock a step that fails
        with patch('sbm.core.workflow.SiteInitializer') as mock_site:
            mock_site_instance = Mock()
            mock_site_instance.initialize.side_effect = Exception("Site initialization failed")
            mock_site.return_value = mock_site_instance
            
            workflow = MigrationWorkflow(test_config)
            
            with pytest.raises(MigrationError):
                workflow.run("testtheme", "prod", False, False)
    
    def test_workflow_timing(self, test_config):
        """Test workflow timing and duration tracking."""
        workflow = MigrationWorkflow(test_config)
        
        # Test timing functionality
        workflow._start_timing()
        assert workflow._start_time is not None
        
        duration = workflow._get_duration()
        assert duration >= 0
        assert isinstance(duration, float)
    
    @patch('sbm.core.workflow.ValidationEngine')
    @patch('sbm.core.workflow.OEMHandler')
    def test_workflow_demo_mode(self, mock_oem, mock_validator, test_config):
        """Test workflow behavior in demo mode."""
        # Enable demo mode in config
        test_config.demo.enabled = True
        test_config.demo.timeout = 180
        
        # Setup mocks
        mock_validator_instance = Mock()
        mock_validator_instance.validate_theme.return_value = {"valid": True}
        mock_validator.return_value = mock_validator_instance
        
        mock_oem_instance = Mock()
        mock_oem_instance.detect_oem.return_value = {"oem": "Stellantis", "brand": "Chrysler"}
        mock_oem.return_value = mock_oem_instance
        
        # Run workflow
        workflow = MigrationWorkflow(test_config)
        result = workflow.run("chryslerofportland", "prod", True, False)
        
        # Should complete quickly in demo mode
        assert result["success"] is True
        assert result["demo_mode"] is True


class TestWorkflowSteps:
    """Test individual workflow steps."""
    
    def test_validation_step(self, test_config):
        """Test theme validation step."""
        workflow = MigrationWorkflow(test_config)
        
        with patch('sbm.core.workflow.ValidationEngine') as mock_validator:
            mock_validator_instance = Mock()
            mock_validator_instance.validate_theme.return_value = {
                "valid": True,
                "checks": {"structure": True, "files": True}
            }
            mock_validator.return_value = mock_validator_instance
            
            result = workflow._run_validation_step("testtheme")
            
            assert result["valid"] is True
            assert "checks" in result
    
    def test_oem_detection_step(self, test_config):
        """Test OEM detection step."""
        workflow = MigrationWorkflow(test_config)
        
        with patch('sbm.core.workflow.OEMHandler') as mock_oem:
            mock_oem_instance = Mock()
            mock_oem_instance.detect_oem.return_value = {
                "oem": "Stellantis",
                "brand": "Chrysler",
                "confidence": 0.95
            }
            mock_oem.return_value = mock_oem_instance
            
            result = workflow._run_oem_detection_step("chryslerofportland")
            
            assert result["oem"] == "Stellantis"
            assert result["brand"] == "Chrysler"
            assert result["confidence"] == 0.95
    
    def test_git_setup_step(self, test_config):
        """Test Git setup step."""
        workflow = MigrationWorkflow(test_config)
        
        with patch('sbm.core.workflow.GitOperations') as mock_git:
            mock_git_instance = Mock()
            mock_git_instance.create_branch.return_value = "testtheme-sbm1224"
            mock_git_instance.setup_repository.return_value = True
            mock_git.return_value = mock_git_instance
            
            result = workflow._run_git_setup_step("testtheme")
            
            assert result["branch_name"] == "testtheme-sbm1224"
            assert result["repository_ready"] is True
    
    def test_site_initialization_step(self, test_config):
        """Test site initialization step."""
        workflow = MigrationWorkflow(test_config)
        
        with patch('sbm.core.workflow.SiteInitializer') as mock_site:
            mock_site_instance = Mock()
            mock_site_instance.initialize.return_value = {
                "files_created": 4,
                "templates_processed": ["sb-home.scss", "sb-vdp.scss"]
            }
            mock_site.return_value = mock_site_instance
            
            result = workflow._run_site_initialization_step("testtheme", "prod")
            
            assert result["files_created"] == 4
            assert "templates_processed" in result
    
    def test_scss_processing_step(self, test_config):
        """Test SCSS processing step."""
        workflow = MigrationWorkflow(test_config)
        
        with patch('sbm.core.workflow.SCSSProcessor') as mock_scss:
            mock_scss_instance = Mock()
            mock_scss_instance.process_theme.return_value = {
                "styles_migrated": 15,
                "files_processed": ["lvdp.scss", "lvrp.scss"],
                "context7_used": True
            }
            mock_scss.return_value = mock_scss_instance
            
            result = workflow._run_scss_processing_step("testtheme")
            
            assert result["styles_migrated"] == 15
            assert result["context7_used"] is True
            assert "files_processed" in result


class TestWorkflowIntegration:
    """Test workflow integration scenarios."""
    
    @patch('sbm.core.workflow.ValidationEngine')
    @patch('sbm.core.workflow.GitOperations')
    @patch('sbm.core.workflow.SiteInitializer')
    @patch('sbm.core.workflow.SCSSProcessor')
    @patch('sbm.core.workflow.OEMHandler')
    def test_full_stellantis_workflow(self, mock_oem, mock_scss, mock_site, mock_git, mock_validator, test_config):
        """Test complete workflow for Stellantis dealer."""
        # Setup enhanced Stellantis mode
        test_config.stellantis.enhanced_mode = True
        
        # Setup all mocks for successful execution
        mock_validator_instance = Mock()
        mock_validator_instance.validate_theme.return_value = {"valid": True}
        mock_validator.return_value = mock_validator_instance
        
        mock_oem_instance = Mock()
        mock_oem_instance.detect_oem.return_value = {
            "oem": "Stellantis",
            "brand": "Chrysler",
            "enhanced_processing": True
        }
        mock_oem.return_value = mock_oem_instance
        
        mock_git_instance = Mock()
        mock_git_instance.create_branch.return_value = "chryslerofportland-sbm1224"
        mock_git_instance.commit_changes.return_value = True
        mock_git.return_value = mock_git_instance
        
        mock_site_instance = Mock()
        mock_site_instance.initialize.return_value = {"files_created": 4}
        mock_site.return_value = mock_site_instance
        
        mock_scss_instance = Mock()
        mock_scss_instance.process_theme.return_value = {
            "styles_migrated": 20,
            "stellantis_enhancements": True
        }
        mock_scss.return_value = mock_scss_instance
        
        # Run complete workflow
        workflow = MigrationWorkflow(test_config)
        result = workflow.run("chryslerofportland", "prod", False, False)
        
        # Verify Stellantis-specific results
        assert result["success"] is True
        assert result["oem"] == "Stellantis"
        assert result["brand"] == "Chrysler"
        assert result["styles_migrated"] == 20
        
        # Verify all components were called
        mock_oem_instance.detect_oem.assert_called_once()
        mock_scss_instance.process_theme.assert_called_once()
        mock_git_instance.commit_changes.assert_called_once()
    
    def test_workflow_cleanup_on_failure(self, test_config):
        """Test workflow cleanup when failures occur."""
        workflow = MigrationWorkflow(test_config)
        
        with patch('sbm.core.workflow.ValidationEngine') as mock_validator:
            mock_validator_instance = Mock()
            mock_validator_instance.validate_theme.side_effect = Exception("Validation failed")
            mock_validator.return_value = mock_validator_instance
            
            # Should handle cleanup gracefully
            with pytest.raises(Exception):
                workflow.run("testtheme", "prod", False, False)
            
            # Verify cleanup was attempted
            assert workflow.current_step is None 
