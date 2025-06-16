"""
Full migration workflow orchestrator for SBM Tool V2.

Provides comprehensive, fully automated migration workflow that handles
the complete end-to-end process including diagnostics, git operations,
Docker container management, migration, validation, and PR creation.
"""

import os
import sys
import time
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

from sbm.config import Config
from sbm.utils.logger import get_logger
from sbm.utils.errors import MigrationError, ValidationError, GitError
from sbm.core.diagnostics import SystemDiagnostics
from sbm.core.git_operations import GitOperations
from sbm.core.workflow import MigrationWorkflow
from sbm.core.validation import ValidationEngine


class FullMigrationWorkflow:
    """
    Orchestrates the complete, fully automated SBM migration workflow.
    
    This class manages the entire end-to-end process including:
    - System diagnostics and dependency checks
    - Directory navigation and git operations
    - Docker container startup and monitoring
    - Theme migration and validation
    - Pull request creation and documentation
    - Comprehensive reporting and summary
    """
    
    def __init__(self, config: Config):
        """Initialize the full migration workflow."""
        self.config = config
        self.logger = get_logger("full_workflow")
        self.results: Dict[str, Any] = {}
        self._start_time: Optional[float] = None
        self._current_directory: Optional[str] = None
        
    def run(self, slug: str, skip_docker_wait: bool = False) -> Dict[str, Any]:
        """
        Execute the complete automated migration workflow.
        
        Args:
            slug: Dealer theme slug
            skip_docker_wait: Skip Docker container startup monitoring
            
        Returns:
            Complete workflow results dictionary
            
        Raises:
            MigrationError: If any critical step fails
        """
        self.logger.info(f"🚀 Starting FULL AUTOMATED SBM WORKFLOW for {slug}")
        self._start_timing()
        self._save_current_directory()
        
        try:
            # Step 1: System Diagnostics
            self._step_1_diagnostics()
            
            # Step 2: Directory Navigation & Git Setup
            self._step_2_navigation_and_git_setup(slug)
            
            # Step 3: Docker Container Startup & Monitoring
            if not skip_docker_wait:
                self._step_3_docker_startup_monitoring(slug)
            
            # Step 4: Theme Migration
            self._step_4_theme_migration(slug)
            
            # Step 5: Post-Migration Validation
            self._step_5_post_migration_validation(slug)
            
            # Step 6: Pull Request Creation
            self._step_6_pull_request_creation(slug)
            
            # Step 7: Final Summary
            return self._step_7_final_summary(slug)
            
        except KeyboardInterrupt:
            self.logger.warning("❌ Workflow interrupted by user")
            return self._create_error_result("Workflow interrupted by user")
        except Exception as e:
            self.logger.error(f"❌ Workflow failed: {str(e)}")
            return self._create_error_result(str(e))
        finally:
            self._restore_directory()
    
    def _step_1_diagnostics(self) -> None:
        """Step 1: Run system diagnostics and dependency checks."""
        self.logger.step("STEP 1: Running system diagnostics...")
        
        try:
            diagnostics = SystemDiagnostics(self.config)
            diag_result = diagnostics.run_all_checks()
            
            if diag_result.get("overall_health") != "healthy":
                self.logger.warning("⚠️  System diagnostics found issues")
                # Could add auto-fix here in the future
            else:
                self.logger.success("✅ System diagnostics passed")
            
            self.results["diagnostics"] = {
                "success": True,
                "result": diag_result,
                "timestamp": time.time()
            }
            
        except Exception as e:
            self.logger.error(f"❌ Diagnostics failed: {e}")
            self.results["diagnostics"] = {"success": False, "error": str(e)}
            raise MigrationError(f"System diagnostics failed: {e}")
    
    def _step_2_navigation_and_git_setup(self, slug: str) -> None:
        """Step 2: Navigate to di-websites-platform and perform git setup."""
        self.logger.step("STEP 2: Git repository setup...")
        
        try:
            # Navigate to di-websites-platform directory
            if not self.config.di_platform_dir.exists():
                raise MigrationError(f"DI platform directory not found: {self.config.di_platform_dir}")
            
            os.chdir(self.config.di_platform_dir)
            self.logger.info(f"📁 Changed to directory: {self.config.di_platform_dir}")
            
            # Perform git setup
            git_ops = GitOperations(self.config)
            git_result = git_ops.pre_migration_setup(slug, auto_start=False)
            
            if not git_result.get("success"):
                raise GitError(f"Git setup failed: {git_result.get('error')}")
            
            self.logger.success(f"✅ Git setup completed - Branch: {git_result.get('branch_name')}")
            
            self.results["git_setup"] = {
                "success": True,
                "result": git_result,
                "timestamp": time.time()
            }
            
        except Exception as e:
            self.logger.error(f"❌ Git setup failed: {e}")
            self.results["git_setup"] = {"success": False, "error": str(e)}
            raise
    
    def _step_3_docker_startup_monitoring(self, slug: str) -> None:
        """Step 3: Start and monitor Docker container."""
        self.logger.step("STEP 3: Docker container startup and monitoring...")
        
        try:
            git_ops = GitOperations(self.config)
            
            # Start the monitoring process
            while True:
                docker_result = git_ops.monitor_just_start(slug)
                
                if docker_result.get("success"):
                    self.logger.success("✅ Docker container started successfully!")
                    break
                else:
                    error_msg = docker_result.get("error", "Unknown error")
                    self.logger.error(f"❌ Docker startup failed: {error_msg}")
                    
                    # Ask user if they want to retry
                    retry = self._ask_user_retry(f"just start {slug}")
                    if not retry:
                        raise MigrationError(f"Docker startup failed and user chose not to retry: {error_msg}")
                    
                    self.logger.info("🔄 Retrying Docker container startup...")
            
            self.results["docker_startup"] = {
                "success": True,
                "result": docker_result,
                "timestamp": time.time()
            }
            
        except Exception as e:
            self.logger.error(f"❌ Docker startup failed: {e}")
            self.results["docker_startup"] = {"success": False, "error": str(e)}
            raise
    
    def _step_4_theme_migration(self, slug: str) -> None:
        """Step 4: Execute theme migration."""
        self.logger.step("STEP 4: Theme migration...")
        
        try:
            workflow = MigrationWorkflow(self.config)
            migration_result = workflow.run(
                slug=slug,
                environment="prod",
                dry_run=False,
                force=False
            )
            
            if not migration_result.get("success"):
                raise MigrationError(f"Migration failed: {migration_result.get('error')}")
            
            self.logger.success(f"✅ Theme migration completed for {slug}")
            
            self.results["migration"] = {
                "success": True,
                "result": migration_result,
                "timestamp": time.time()
            }
            
        except Exception as e:
            self.logger.error(f"❌ Migration failed: {e}")
            self.results["migration"] = {"success": False, "error": str(e)}
            raise
    
    def _step_5_post_migration_validation(self, slug: str) -> None:
        """Step 5: Validate the migrated theme."""
        self.logger.step("STEP 5: Post-migration validation...")
        
        try:
            validator = ValidationEngine(self.config)
            validation_result = validator.validate_migrated_theme(slug)
            
            # Check if validation passed
            all_passed = all(
                check.get("passed", False) 
                for check in validation_result.values()
                if isinstance(check, dict)
            )
            
            if not all_passed:
                self.logger.warning("⚠️  Some validation checks failed")
                for check_name, check_result in validation_result.items():
                    if isinstance(check_result, dict) and not check_result.get("passed"):
                        self.logger.warning(f"  - {check_name}: {check_result.get('message', 'Failed')}")
            else:
                self.logger.success("✅ All validation checks passed")
            
            self.results["validation"] = {
                "success": all_passed,
                "result": validation_result,
                "timestamp": time.time()
            }
            
        except Exception as e:
            self.logger.error(f"❌ Validation failed: {e}")
            self.results["validation"] = {"success": False, "error": str(e)}
            # Don't raise - validation failures shouldn't stop the workflow
    
    def _step_6_pull_request_creation(self, slug: str) -> None:
        """Step 6: Create pull request."""
        self.logger.step("STEP 6: Pull request creation...")
        
        try:
            git_ops = GitOperations(self.config)
            
            # Get the branch name from git setup results
            branch_name = self.results.get("git_setup", {}).get("result", {}).get("branch_name")
            if not branch_name:
                raise MigrationError("Could not determine branch name for PR creation")
            
            pr_result = git_ops.create_pr(slug, branch_name, draft=False)
            
            if not pr_result.get("success"):
                raise MigrationError(f"PR creation failed: {pr_result.get('error')}")
            
            pr_url = pr_result.get("pr_url")
            self.logger.success(f"✅ Pull request created: {pr_url}")
            
            # Salesforce message is handled automatically in create_pr
            self.logger.info("📋 Salesforce message copied to clipboard")
            
            self.results["pull_request"] = {
                "success": True,
                "result": pr_result,
                "timestamp": time.time()
            }
            
        except Exception as e:
            self.logger.error(f"❌ PR creation failed: {e}")
            self.results["pull_request"] = {"success": False, "error": str(e)}
            # Don't raise - PR creation failures shouldn't stop the workflow
    
    def _step_7_final_summary(self, slug: str) -> Dict[str, Any]:
        """Step 7: Generate final comprehensive summary."""
        self.logger.step("STEP 7: Final summary...")
        
        try:
            duration = self._get_duration()
            
            # Count successful steps
            successful_steps = sum(1 for step in self.results.values() if step.get("success"))
            total_steps = len(self.results)
            
            # Generate summary
            summary = {
                "success": successful_steps == total_steps,
                "slug": slug,
                "duration": duration,
                "steps_completed": successful_steps,
                "total_steps": total_steps,
                "timestamp": time.time(),
                "results": self.results
            }
            
            # Display comprehensive summary
            self._display_final_summary(summary)
            
            return summary
            
        except Exception as e:
            self.logger.error(f"❌ Summary generation failed: {e}")
            return self._create_error_result(f"Summary generation failed: {e}")
    
    def _display_final_summary(self, summary: Dict[str, Any]) -> None:
        """Display the final workflow summary."""
        self.logger.info("\n" + "="*80)
        self.logger.info("🎉 FULL SBM MIGRATION WORKFLOW COMPLETE")
        self.logger.info("="*80)
        
        slug = summary["slug"]
        duration = summary["duration"]
        success = summary["success"]
        
        if success:
            self.logger.success(f"✅ MIGRATION SUCCESSFUL for {slug}")
        else:
            self.logger.error(f"❌ MIGRATION INCOMPLETE for {slug}")
        
        self.logger.info(f"⏱️  Total Duration: {duration:.1f} seconds")
        self.logger.info(f"📊 Steps Completed: {summary['steps_completed']}/{summary['total_steps']}")
        
        # Display step-by-step results
        self.logger.info("\n📋 STEP-BY-STEP RESULTS:")
        step_names = {
            "diagnostics": "1. System Diagnostics",
            "git_setup": "2. Git Setup", 
            "docker_startup": "3. Docker Startup",
            "migration": "4. Theme Migration",
            "validation": "5. Post-Migration Validation",
            "pull_request": "6. Pull Request Creation"
        }
        
        for step_key, step_name in step_names.items():
            if step_key in self.results:
                result = self.results[step_key]
                status = "✅ PASSED" if result.get("success") else "❌ FAILED"
                self.logger.info(f"   {step_name}: {status}")
                if not result.get("success") and result.get("error"):
                    self.logger.info(f"      Error: {result['error']}")
        
        # Display key information
        if "pull_request" in self.results and self.results["pull_request"].get("success"):
            pr_url = self.results["pull_request"]["result"].get("pr_url")
            if pr_url:
                self.logger.info(f"\n🔗 Pull Request: {pr_url}")
        
        if "git_setup" in self.results and self.results["git_setup"].get("success"):
            branch_name = self.results["git_setup"]["result"].get("branch_name")
            if branch_name:
                self.logger.info(f"🌿 Branch: {branch_name}")
        
        self.logger.info("\n" + "="*80)
    
    def _ask_user_retry(self, command: str) -> bool:
        """Ask user if they want to retry a failed command."""
        try:
            response = input(f"\n❓ Do you want to run '{command}' again? (y/n): ").strip().lower()
            return response in ['y', 'yes']
        except (EOFError, KeyboardInterrupt):
            return False
    
    def _start_timing(self) -> None:
        """Start timing the workflow."""
        self._start_time = time.time()
    
    def _get_duration(self) -> float:
        """Get workflow duration in seconds."""
        if self._start_time is None:
            return 0.0
        return time.time() - self._start_time
    
    def _save_current_directory(self) -> None:
        """Save the current working directory."""
        self._current_directory = os.getcwd()
    
    def _restore_directory(self) -> None:
        """Restore the original working directory."""
        if self._current_directory:
            try:
                os.chdir(self._current_directory)
            except Exception as e:
                self.logger.warning(f"Could not restore directory: {e}")
    
    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """Create an error result dictionary."""
        return {
            "success": False,
            "error": error_message,
            "duration": self._get_duration(),
            "timestamp": time.time(),
            "results": self.results
        } 
