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
        
    def run(self, slug: str, skip_docker_wait: bool = False, use_prod_db: bool = False) -> Dict[str, Any]:
        """
        Execute the complete automated migration workflow.
        
        Args:
            slug: Dealer theme slug
            skip_docker_wait: Skip Docker container startup monitoring
            use_prod_db: Use production database for Docker container
            
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
                self._step_3_docker_startup_monitoring(slug, use_prod_db)
            
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
            self.logger.info(f"🔄 Looking for DI platform directory: {self.config.di_platform_dir}")
            if not self.config.di_platform_dir.exists():
                raise MigrationError(f"DI platform directory not found: {self.config.di_platform_dir}")
            
            self.logger.info(f"📁 Changing to directory: {self.config.di_platform_dir}")
            os.chdir(self.config.di_platform_dir)
            self.logger.info(f"✅ Successfully changed to: {os.getcwd()}")
            
            # Perform git setup
            self.logger.info("🔄 Starting git setup operations...")
            git_ops = GitOperations(self.config)
            git_result = git_ops.pre_migration_setup(slug, auto_start=False)
            
            if not git_result.get("success"):
                raise GitError(f"Git setup failed: {git_result.get('error')}")
            
            branch_name = git_result.get('branch_name')
            self.logger.success(f"✅ Git setup completed - Branch: {branch_name}")
            
            self.results["git_setup"] = {
                "success": True,
                "result": git_result,
                "timestamp": time.time()
            }
            
        except Exception as e:
            self.logger.error(f"❌ Git setup failed: {e}")
            self.results["git_setup"] = {"success": False, "error": str(e)}
            raise
    
    def _step_3_docker_startup_monitoring(self, slug: str, use_prod_db: bool = False) -> None:
        """Step 3: Monitor Docker container startup."""
        self.logger.step("STEP 3: Docker container startup monitoring...")
        db_mode = "prod" if use_prod_db else "dev"
        just_start_cmd = f"just start {slug} prod" if use_prod_db else f"just start {slug}"
        self.logger.info(f"Now run '{just_start_cmd}' in the DI platform directory")
        self.logger.info(f"Using {db_mode} database for Docker container")
        self.logger.info("The monitoring will automatically detect when it's complete...")
        
        try:
            git_ops = GitOperations(self.config)
            
            # Monitor the existing process
            while True:
                docker_result = git_ops.monitor_just_start(slug, use_prod_db)
                
                if docker_result.get("success"):
                    self.logger.success("✅ Docker container started successfully!")
                    self.logger.info("🔄 Proceeding automatically to migration...")
                    break
                else:
                    error_msg = docker_result.get("error", "Unknown error")
                    self.logger.error(f"❌ Docker monitoring failed: {error_msg}")
                    
                    # Ask user if they want to retry monitoring
                    retry = self._ask_user_retry(f"monitor just start {slug}")
                    if not retry:
                        raise MigrationError(f"Docker monitoring failed and user chose not to retry: {error_msg}")
                    
                    self.logger.info("🔄 Retrying Docker monitoring...")
            
            self.results["docker_startup"] = {
                "success": True,
                "result": docker_result,
                "timestamp": time.time()
            }
            
        except Exception as e:
            self.logger.error(f"❌ Docker monitoring failed: {e}")
            self.results["docker_startup"] = {"success": False, "error": str(e)}
            raise
    
    def _step_4_theme_migration(self, slug: str) -> None:
        """Step 4: Execute theme migration."""
        self.logger.step("STEP 4: Theme migration...")
        self.logger.info(f"🔄 Starting migration workflow for {slug}...")
        
        try:
            # Verify we're in the right directory
            current_dir = os.getcwd()
            self.logger.info(f"📁 Current working directory: {current_dir}")
            
            # Check theme directory exists
            theme_dir = Path(current_dir) / "dealer-themes" / slug
            if theme_dir.exists():
                self.logger.info(f"✅ Found theme directory: {theme_dir}")
            else:
                self.logger.warning(f"⚠️  Theme directory not found: {theme_dir}")
            
            workflow = MigrationWorkflow(self.config)
            migration_result = workflow.run(
                slug=slug,
                environment="prod",
                dry_run=False,
                force=False
            )
            
            if not migration_result.get("success"):
                raise MigrationError(f"Migration failed: {migration_result.get('error')}")
            
            # CRITICAL: Wait briefly to ensure files are fully written before git operations
            import time
            self.logger.info("⏳ Waiting for file operations to complete...")
            time.sleep(2)  # 2 second pause to ensure files are written
            
            # Show what files were created/modified - FIX PATH CHECKING
            self.logger.info("🔍 Checking migration results...")
            
            # Check in the theme directory first (where files actually are based on git status)
            self.logger.info(f"📁 Looking for sb-*.scss files in theme dir: {theme_dir}")
            theme_scss_files = list(theme_dir.glob("sb-*.scss"))
            
            # Also check css subdirectory
            css_dir = theme_dir / "css"
            self.logger.info(f"📁 Looking for sb-*.scss files in css dir: {css_dir}")
            css_scss_files = list(css_dir.glob("sb-*.scss")) if css_dir.exists() else []
            
            # Combine all found files
            all_sb_files = theme_scss_files + css_scss_files
            
            if all_sb_files:
                self.logger.success("📝 Generated Site Builder files:")
                for file in all_sb_files:
                    file_size = file.stat().st_size if file.exists() else 0
                    relative_path = file.relative_to(theme_dir)
                    self.logger.success(f"   ✅ {relative_path} ({file_size} bytes)")
            else:
                self.logger.warning("⚠️  No sb-*.scss files found after migration")
                # Show what files DO exist for debugging
                if theme_dir.exists():
                    all_theme_files = list(theme_dir.glob("*.scss"))
                    if css_dir.exists():
                        all_theme_files.extend(css_dir.glob("*.scss"))
                    self.logger.warning(f"   Found {len(all_theme_files)} other SCSS files")
                    for f in all_theme_files[:10]:  # Show first 10 files
                        relative_path = f.relative_to(theme_dir)
                        self.logger.warning(f"     - {relative_path}")
            
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
        """Step 5: Simplified post-migration validation - SCSS syntax and SBM compliance only."""
        self.logger.step("STEP 5: Post-migration validation (simplified)...")
        
        try:
            validator = ValidationEngine(self.config)
            validation_result = validator.validate_migrated_files(slug)
            
            # Check if validation passed
            overall_passed = validation_result.get("overall", False)
            
            if not overall_passed:
                self.logger.warning("⚠️  Validation issues found:")
                
                # Report SCSS syntax errors
                scss_errors = validation_result.get("scss_syntax", {}).get("errors", [])
                if scss_errors:
                    self.logger.warning("  📝 SCSS Syntax Errors:")
                    for error in scss_errors:
                        self.logger.warning(f"    - {error}")
                
                # Report SBM compliance issues  
                compliance_issues = validation_result.get("sbm_compliance", {}).get("issues", [])
                if compliance_issues:
                    self.logger.warning("  📋 SBM Compliance Issues:")
                    for issue in compliance_issues:
                        self.logger.warning(f"    - {issue}")
                        
                self.logger.info("💡 You can use --force to skip validation and proceed anyway")
            else:
                self.logger.success("✅ All validation checks passed")
            
            self.results["validation"] = {
                "success": overall_passed,
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
            
            # Determine success based on CRITICAL vs NON-CRITICAL steps
            # CRITICAL: diagnostics, git_setup, migration  
            # NON-CRITICAL: docker_startup (can be skipped), validation (warnings only), pull_request (can fail if exists)
            
            critical_steps = ["diagnostics", "git_setup", "migration"]
            non_critical_steps = ["docker_startup", "validation", "pull_request"]
            
            critical_success = all(
                self.results.get(step, {}).get("success", False) 
                for step in critical_steps
            )
            
            # Count all steps for reporting
            successful_steps = sum(1 for step in self.results.values() if step.get("success"))
            total_steps = len(self.results)
            
            # Migration is successful if all critical steps passed
            migration_successful = critical_success
            
            # Check for non-critical warnings
            warnings = []
            if not self.results.get("validation", {}).get("success", True):
                warnings.append("Validation issues found (review recommended)")
            if not self.results.get("pull_request", {}).get("success", True):
                pr_error = self.results.get("pull_request", {}).get("error", "")
                if "already exists" in pr_error:
                    warnings.append("PR already exists (expected)")
                else:
                    warnings.append("PR creation failed")
            if not self.results.get("docker_startup", {}).get("success", True):
                warnings.append("Docker startup was skipped or failed")
            
            # Generate summary
            summary = {
                "success": migration_successful,  # Based on critical steps only
                "slug": slug,
                "duration": duration,
                "steps_completed": successful_steps,
                "total_steps": total_steps,
                "critical_success": critical_success,
                "warnings": warnings,
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
        warnings = summary.get("warnings", [])
        
        if success:
            if warnings:
                self.logger.success(f"✅ MIGRATION SUCCESSFUL for {slug} (with warnings)")
                self.logger.warning("⚠️  WARNINGS:")
                for warning in warnings:
                    self.logger.warning(f"   - {warning}")
            else:
                self.logger.success(f"✅ MIGRATION SUCCESSFUL for {slug}")
        else:
            self.logger.error(f"❌ MIGRATION FAILED for {slug}")
        
        self.logger.info(f"⏱️  Total Duration: {duration:.1f} seconds")
        self.logger.info(f"📊 Steps Completed: {summary['steps_completed']}/{summary['total_steps']}")
        
        # Display step-by-step results with better formatting
        self.logger.info("\n📋 DETAILED STEP RESULTS:")
        step_names = {
            "diagnostics": "1. System Diagnostics",
            "git_setup": "2. Git Repository Setup", 
            "docker_startup": "3. Docker Container Startup",
            "migration": "4. Theme Migration (CRITICAL)",
            "validation": "5. Post-Migration Validation",
            "pull_request": "6. Pull Request Creation"
        }
        
        for step_key, step_name in step_names.items():
            if step_key in self.results:
                result = self.results[step_key]
                success_status = result.get("success")
                
                if success_status is True:
                    status = "✅ PASSED"
                elif success_status is False:
                    # Special handling for known acceptable failures
                    error = result.get("error", "")
                    if step_key == "pull_request" and "already exists" in error:
                        status = "⚠️  SKIPPED (PR exists)"
                    elif step_key == "docker_startup":
                        status = "⚠️  SKIPPED"
                    elif step_key == "validation":
                        status = "⚠️  WARNINGS"
                    else:
                        status = "❌ FAILED"
                else:
                    status = "⏭️  SKIPPED"
                    
                self.logger.info(f"   {step_name}: {status}")
                
                # Show error details for actual failures
                if not success_status and result.get("error"):
                    error_msg = result["error"]
                    # Truncate very long error messages
                    if len(error_msg) > 100:
                        error_msg = error_msg[:100] + "..."
                    self.logger.info(f"      Details: {error_msg}")
        
        # Display key information
        if "pull_request" in self.results and self.results["pull_request"].get("success"):
            pr_url = self.results["pull_request"]["result"].get("pr_url")
            if pr_url:
                self.logger.info(f"\n🔗 Pull Request: {pr_url}")
        elif "pull_request" in self.results:
            # Even if PR creation "failed", show if it's because PR exists
            pr_error = self.results["pull_request"].get("error", "")
            if "already exists" in pr_error and "/pull/" in pr_error:
                # Extract PR URL from error message
                import re
                url_match = re.search(r'https://github\.com/[^\s]+', pr_error)
                if url_match:
                    self.logger.info(f"\n🔗 Existing Pull Request: {url_match.group()}")
        
        if "git_setup" in self.results and self.results["git_setup"].get("success"):
            branch_name = self.results["git_setup"]["result"].get("branch_name")
            if branch_name:
                self.logger.info(f"🌿 Branch: {branch_name}")
        
        # Show next steps
        if success:
            self.logger.info(f"\n🎯 NEXT STEPS:")
            self.logger.info(f"   1. Review the generated sb-*.scss files in dealer-themes/{slug}/css/")
            self.logger.info("   2. Test the theme in the browser")
            if warnings:
                self.logger.info("   3. Address any warnings listed above")
            self.logger.info("   4. Merge the PR when ready")
        
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
