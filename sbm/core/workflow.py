"""
Migration workflow orchestrator for SBM Tool V2.

Coordinates the complete migration process including initialization,
file creation, style migration, validation, and Git operations.
"""

import time
from pathlib import Path
from typing import Dict, Any, Optional

from sbm.config import Config
from sbm.utils.logger import get_logger
from sbm.utils.errors import MigrationError, ThemeError, ValidationError, GitError
from sbm.core.validation import ValidationEngine
from sbm.core.git_operations import GitOperations
from sbm.core.site_initializer import SiteInitializer
from sbm.scss.processor import SCSSProcessor
from sbm.oem.handler import OEMHandler


class MigrationWorkflow:
    """
    Orchestrates the complete dealer theme migration workflow.
    
    This class manages the step-by-step process of migrating a dealer theme
    from legacy SCSS to Site Builder format, including validation, OEM detection,
    Git operations, file creation, SCSS processing, and final validation.
    """
    
    def __init__(self, config: Config):
        """
        Initialize the migration workflow.
        
        Args:
            config: Configuration instance
        """
        self.config = config
        self.logger = get_logger("workflow")
        self.current_step: Optional[str] = None
        self.results: Dict[str, Any] = {}
        self._start_time: Optional[float] = None
    
    def run(
        self, 
        slug: str, 
        environment: str, 
        dry_run: bool, 
        force: bool
    ) -> Dict[str, Any]:
        """
        Execute the complete migration workflow.
        
        Args:
            slug: Dealer theme slug
            environment: Target environment
            dry_run: If True, validate only without making changes
            force: If True, continue despite validation warnings
            
        Returns:
            Migration results dictionary
            
        Raises:
            ValidationError: If validation fails and force=False
            MigrationError: If migration process fails
            GitError: If Git operations fail
        """
        self.logger.info(f"Starting migration workflow for {slug}")
        self._start_timing()
        
        try:
            # Step 1: Validation
            validation_result = self._run_validation_step(slug)
            if not validation_result.get("valid", False) and not force:
                raise ValidationError("Theme validation failed")
            
            # Step 2: OEM Detection
            oem_result = self._run_oem_detection_step(slug)
            
            # Step 3: Git Setup (skip in dry run or demo mode)
            if not dry_run and not self.config.demo.skip_git:
                git_result = self._run_git_setup_step(slug)
            else:
                git_result = {"branch_name": f"{slug}-sbm-dryrun", "repository_ready": False}
            
            # Step 4: Site Initialization (skip in dry run)
            if not dry_run:
                site_result = self._run_site_initialization_step(slug, environment)
            else:
                site_result = {"files_created": 0, "dry_run": True}
            
            # Step 5: SCSS Processing
            scss_result = self._run_scss_processing_step(slug)
            
            # Step 6: Git Commit (if Git operations enabled and not dry run)
            commit_result = {}
            if not dry_run and not self.config.demo.skip_git and git_result.get("repository_ready"):
                commit_result = self._run_git_commit_step(slug, scss_result)
            
            # Step 7: PR Creation (if Git operations enabled and not dry run)
            pr_result = {}
            if not dry_run and not self.config.demo.skip_git and git_result.get("repository_ready") and commit_result.get("committed"):
                pr_result = self._run_pr_creation_step(slug, git_result["branch_name"])
            
            # Compile final result
            result = {
                "success": True,
                "slug": slug,
                "environment": environment,
                "force_mode": force,
                "dry_run": dry_run,
                "duration": self._get_duration(),
                "oem": oem_result.get("oem", "Unknown"),
                "brand": oem_result.get("brand", "Unknown"),
                "files_created": site_result.get("files_created", 0),
                "styles_migrated": scss_result.get("styles_migrated", 0),
                "branch_name": git_result.get("branch_name"),
                "pr_url": pr_result.get("pr_url"),
                "steps_completed": list(self.results.keys())
            }
            
            # Add demo mode flag if enabled
            if self.config.demo.enabled:
                result["demo_mode"] = True
            
            return result
            
        except Exception as e:
            self._handle_step_error(self.current_step or "unknown", e)
            raise
        finally:
            self.current_step = None
    
    def _set_current_step(self, step: str) -> None:
        """Set the current workflow step."""
        self.current_step = step
        self.logger.debug(f"Starting step: {step}")
    
    def _complete_step(self, step: str, result: Dict[str, Any]) -> None:
        """Mark a workflow step as completed."""
        self.results[step] = {
            "success": True,
            "result": result,
            "timestamp": time.time()
        }
        self.logger.debug(f"Completed step: {step}")
    
    def _handle_step_error(self, step: str, error: Exception) -> None:
        """Handle error during workflow step."""
        self.results[step] = {
            "success": False,
            "error": str(error),
            "timestamp": time.time()
        }
        self.logger.error(f"Step {step} failed: {error}")
    
    def _start_timing(self) -> None:
        """Start timing the workflow."""
        self._start_time = time.time()
    
    def _get_duration(self) -> float:
        """Get workflow duration in seconds."""
        if self._start_time is None:
            return 0.0
        return time.time() - self._start_time
    
    def _validate_environment(self, environment: str) -> bool:
        """Validate environment parameter."""
        valid_environments = ["prod", "staging", "dev"]
        return environment in valid_environments
    
    def _run_validation_step(self, slug: str) -> Dict[str, Any]:
        """Run theme validation step."""
        self._set_current_step("validation")
        validator = ValidationEngine(self.config)
        result = validator.validate_theme(slug)
        self._complete_step("validation", result)
        return result
    
    def _run_oem_detection_step(self, slug: str) -> Dict[str, Any]:
        """Run OEM detection step."""
        self._set_current_step("oem_detection")
        oem_handler = OEMHandler(self.config)
        result = oem_handler.detect_oem(slug)
        self._complete_step("oem_detection", result)
        return result
    
    def _run_git_setup_step(self, slug: str) -> Dict[str, Any]:
        """Run Git setup step."""
        self._set_current_step("git_setup")
        git_ops = GitOperations(self.config)
        branch_result = git_ops.create_branch(slug)
        
        if branch_result.get("success", False):
            result = {
                "branch_name": branch_result["branch"],
                "repository_ready": True
            }
        else:
            result = {
                "branch_name": None,
                "repository_ready": False,
                "error": branch_result.get("error", "Unknown error creating branch")
            }
        
        self._complete_step("git_setup", result)
        return result
    
    def _run_site_initialization_step(self, slug: str, environment: str) -> Dict[str, Any]:
        """Run site initialization step."""
        self._set_current_step("site_initialization")
        site_init = SiteInitializer(self.config)
        result = site_init.initialize(slug, environment)
        self._complete_step("site_initialization", result)
        return result
    
    def _run_scss_processing_step(self, slug: str) -> Dict[str, Any]:
        """Run SCSS processing step."""
        self._set_current_step("scss_processing")
        scss_processor = SCSSProcessor(self.config)
        result = scss_processor.process_theme(slug)
        self._complete_step("scss_processing", result)
        return result
    
    def _run_git_commit_step(self, slug: str, scss_result: Dict[str, Any]) -> Dict[str, Any]:
        """Run git commit step for SCSS files."""
        self._set_current_step("git_commit")
        git_ops = GitOperations(self.config)
        
        # Build commit message based on SCSS processing results
        files_created = scss_result.get("files_created", [])
        files_modified = scss_result.get("files_modified", [])
        
        # Create list of SCSS files to commit
        scss_files = []
        for file_list in [files_created, files_modified]:
            if isinstance(file_list, list):
                scss_files.extend([f"dealer-themes/{slug}/{f}" for f in file_list if f.endswith('.scss')])
        
        # Generate commit message
        commit_message = f"{slug.replace('-', ' ').title()} SBM FE Audit"
        if files_created:
            commit_message += f" - Created {', '.join(files_created)}"
        if files_modified:
            commit_message += f" - Modified {', '.join(files_modified)}"
        
        # Commit the changes
        result = git_ops.commit_changes(commit_message, scss_files if scss_files else None)
        
        # Push the branch if commit was successful
        if result.get("committed"):
            current_branch = git_ops._get_repo_info().get('current_branch')
            if current_branch:
                push_success = git_ops.push_branch(current_branch)
                result["pushed"] = push_success
                result["branch"] = current_branch
        
        self._complete_step("git_commit", result)
        return result
    
    def _run_pr_creation_step(self, slug: str, branch_name: str) -> Dict[str, Any]:
        """Run PR creation step."""
        self._set_current_step("pr_creation")
        git_ops = GitOperations(self.config)
        result = git_ops.create_pr(slug, branch_name)
        self._complete_step("pr_creation", result)
        return result 
