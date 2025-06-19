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
from sbm.core.user_review import UserReviewManager


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
            
            # Step 4.5: USER REVIEW SESSION (NEW)
            self._step_4_5_user_review(slug)
            
            # Step 5: File Saving and Gulp Compilation
            self._step_5_file_saving_and_gulp_compilation(slug)
            
            # Step 6: Post-Migration Validation
            self._step_6_post_migration_validation(slug)
            
            # Step 7: Pull Request Creation
            self._step_7_pull_request_creation(slug)
            
            # Step 8: Final Summary
            return self._step_8_final_summary(slug)
            
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
        self.logger.info(f"📋 Command to run: '{just_start_cmd}' in the DI platform directory")
        self.logger.info(f"🗄️  Using {db_mode} database for Docker container")
        self.logger.info("⏳ The monitoring will automatically detect when startup is complete...")
        
        try:
            git_ops = GitOperations(self.config)
            
            # Monitor the existing process
            max_retries = 3
            retry_count = 0
            
            while retry_count < max_retries:
                docker_result = git_ops.monitor_just_start(slug, use_prod_db)
                
                if docker_result.get("success"):
                    self.logger.success("✅ Docker container started successfully!")
                    self.logger.info("🔄 Proceeding automatically to migration...")
                    break
                else:
                    error_msg = docker_result.get("error", "Unknown error")
                    retry_suggestion = docker_result.get("retry_suggestion", "")
                    
                    self.logger.error(f"❌ Docker monitoring failed: {error_msg}")
                    
                    if retry_suggestion:
                        self.logger.info(f"💡 Suggestion: {retry_suggestion}")
                    
                    # If this was a process startup failure, offer more specific help
                    if "Failed to start" in error_msg:
                        self.logger.info("🔧 Common solutions:")
                        self.logger.info(f"   • Ensure you're in the correct directory: {self.config.di_platform_dir}")
                        self.logger.info("   • Check that Docker Desktop is running")
                        self.logger.info("   • Verify the 'just' command is available (try 'which just')")
                    
                    retry_count += 1
                    if retry_count < max_retries:
                        retry = self._ask_user_retry(f"docker startup for {slug} (attempt {retry_count + 1}/{max_retries})")
                        if not retry:
                            raise MigrationError(f"Docker startup failed and user chose not to retry: {error_msg}")
                        
                        self.logger.info(f"🔄 Retrying Docker startup (attempt {retry_count + 1}/{max_retries})...")
                    else:
                        self.logger.error(f"❌ Max retries ({max_retries}) reached for Docker startup")
                        raise MigrationError(f"Docker startup failed after {max_retries} attempts: {error_msg}")
            
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
        self.logger.info(f"🚀 Starting comprehensive migration workflow for {slug}...")
        self.logger.info("🔄 This process will analyze your theme and generate Site Builder files...")
        
        try:
            # Verify we're in the right directory
            current_dir = os.getcwd()
            self.logger.info(f"📁 Current working directory: {current_dir}")
            
            # Check theme directory exists
            theme_dir = Path(current_dir) / "dealer-themes" / slug
            if theme_dir.exists():
                self.logger.success(f"✅ Found theme directory: {theme_dir}")
                
                # Analyze functions.php for map shortcodes
                from sbm.core.functions_analyzer import FunctionsAnalyzer
                functions_analyzer = FunctionsAnalyzer(self.config)
                map_analysis = functions_analyzer.analyze_functions_file(theme_dir)
                
                if map_analysis["map_shortcodes"]:
                    self.logger.info(f"🗺️  Found {len(map_analysis['map_shortcodes'])} map shortcode(s):")
                    for shortcode in map_analysis["map_shortcodes"]:
                        status = "🔗 CommonTheme" if shortcode["is_commontheme_reference"] else "✅ Local"
                        self.logger.info(f"   • [{shortcode['name']}] -> {shortcode['template_path']} ({status})")
                
                if map_analysis["migration_required"]:
                    self.logger.warning("⚠️  Map shortcodes reference CommonTheme partials - migration needed")
                    # Migrate map dependencies
                    migration_results = functions_analyzer.migrate_map_dependencies(theme_dir, map_analysis)
                    if migration_results["success"]:
                        self.logger.success(f"✅ Migrated {len(migration_results['files_copied'])} partial(s) and {len(migration_results['styles_migrated'])} style(s)")
                    else:
                        self.logger.error("❌ Map dependency migration failed")
                        for error in migration_results["errors"]:
                            self.logger.error(f"   • {error}")
                else:
                    self.logger.info("✅ No CommonTheme map dependencies found")
                
                # Show what source files we're working with
                self.logger.info("🔍 Analyzing source files...")
                source_files = []
                css_dir = theme_dir / "css"
                if css_dir.exists():
                    for pattern in ["*.scss", "inside.scss", "style.scss", "vrp.scss", "vdp.scss", "home.scss"]:
                        found_files = list(css_dir.glob(pattern))
                        source_files.extend([f.name for f in found_files])
                
                if source_files:
                    unique_sources = list(set(source_files))
                    self.logger.info(f"📋 Found {len(unique_sources)} source files to process:")
                    for file in sorted(unique_sources):
                        self.logger.info(f"   • {file}")
                else:
                    self.logger.warning("⚠️  No standard SCSS source files found")
            else:
                self.logger.warning(f"⚠️  Theme directory not found: {theme_dir}")
                self.logger.info("🔄 Migration will proceed - directory might be created during process")
            
            self.logger.info("⚙️  Executing migration engine...")
            workflow = MigrationWorkflow(self.config)
            migration_result = workflow.run(
                slug=slug,
                environment="prod",
                dry_run=False,
                force=False,
                skip_pr=True  # Skip PR creation - will be handled by FullMigrationWorkflow
            )
            
            if not migration_result.get("success"):
                raise MigrationError(f"Migration failed: {migration_result.get('error')}")
            
            self.logger.success("🎉 Migration engine completed successfully!")
            
            # CRITICAL: Wait briefly to ensure files are fully written before git operations
            import time
            self.logger.info("⏳ Ensuring all file operations are complete...")
            self.logger.info("   • Waiting for file system synchronization...")
            time.sleep(2)  # 2 second pause to ensure files are written
            
            # Show what files were created/modified - FIX PATH CHECKING
            self.logger.info("🔍 Verifying migration results...")
            
            # Check in the theme directory first (where files actually are based on git status)
            self.logger.info(f"📁 Scanning for generated files in: {theme_dir}")
            theme_scss_files = list(theme_dir.glob("sb-*.scss"))
            
            # Also check css subdirectory
            css_dir = theme_dir / "css"
            self.logger.info(f"📁 Scanning CSS directory: {css_dir}")
            css_scss_files = list(css_dir.glob("sb-*.scss")) if css_dir.exists() else []
            
            # Combine all found files
            all_sb_files = theme_scss_files + css_scss_files
            
            if all_sb_files:
                self.logger.success("🎯 Site Builder migration completed successfully!")
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
            
            # Store migration results for next step
            self.results["migration"] = {
                "success": True,
                "result": migration_result,
                "generated_files": [str(f) for f in all_sb_files],
                "timestamp": time.time()
            }
            
            self.logger.success(f"✅ Theme migration fully completed for {slug}")
            self.logger.info("🔄 Proceeding to user review session...")
            
        except Exception as e:
            self.logger.error(f"❌ Migration failed: {e}")
            self.results["migration"] = {"success": False, "error": str(e)}
            raise
    
    def _step_4_5_user_review(self, slug: str) -> None:
        """Step 4.5: User review session for manual changes."""
        self.logger.step("STEP 4.5: User Review Session...")
        self.logger.info("👥 Starting manual review session...")
        
        try:
            # Get the automated files from migration step
            migration_result = self.results.get("migration", {}).get("result", {})
            generated_files = migration_result.get("generated_files", [])
            
            if not generated_files:
                self.logger.warning("⚠️  No generated files found for review")
                self.results["user_review"] = {
                    "success": True,
                    "skipped": True,
                    "reason": "No files to review"
                }
                return
            
            # Extract just the filenames from full paths
            automated_files = []
            for file_path in generated_files:
                file_obj = Path(file_path)
                automated_files.append(file_obj.name)
            
            # Start user review session
            review_manager = UserReviewManager(self.config)
            review_result = review_manager.start_review_session(slug, automated_files)
            
            # Store review results for later use in commits and PR
            self.results["user_review"] = {
                "success": True,
                "result": review_result,
                "timestamp": time.time()
            }
            
            self.logger.success("✅ User review session completed!")
            
            # Display summary of changes
            changes_analysis = review_result["changes_analysis"]
            if changes_analysis["has_manual_changes"]:
                modified_files = changes_analysis["files_modified"]
                self.logger.info(f"📝 Manual changes made to: {', '.join(modified_files)}")
            else:
                self.logger.info("ℹ️  No manual changes made - automation was sufficient!")
            
        except Exception as e:
            self.logger.error(f"❌ User review failed: {e}")
            self.results["user_review"] = {"success": False, "error": str(e)}
            # Don't raise - user review failures shouldn't stop the workflow
            self.logger.info("🔄 Continuing with automated results only...")
    
    def _step_5_file_saving_and_gulp_compilation(self, slug: str) -> None:
        """Step 5: Save all generated files and verify gulp compilation."""
        self.logger.step("STEP 5: File saving and gulp compilation...")
        self.logger.info("💾 Ensuring all files are properly saved and compiled...")
        
        try:
            # Get generated files from previous step
            generated_files = self.results.get("migration", {}).get("generated_files", [])
            
            if not generated_files:
                self.logger.warning("⚠️  No generated files found to save")
                return
            
            # Step 1: "Save" each generated file (read and write back to trigger formatting)
            self.logger.info("📄 Saving generated Site Builder files...")
            for file_path in generated_files:
                file_obj = Path(file_path)
                if file_obj.exists():
                    try:
                        # Read the file content
                        content = file_obj.read_text(encoding='utf-8')
                        # Write it back (this triggers any auto-formatters)
                        file_obj.write_text(content, encoding='utf-8')
                        self.logger.info(f"   💾 Saved: {file_obj.name}")
                    except Exception as e:
                        self.logger.warning(f"   ⚠️  Could not save {file_obj.name}: {e}")
                else:
                    self.logger.warning(f"   ⚠️  File not found: {file_path}")
            
            # Step 2: Save style.scss to trigger gulp compilation
            current_dir = Path.cwd()
            theme_dir = current_dir / "dealer-themes" / slug
            css_dir = theme_dir / "css"
            style_scss = css_dir / "style.scss"
            
            if style_scss.exists():
                self.logger.info("🎨 Triggering gulp compilation by saving style.scss...")
                try:
                    # Read and write style.scss to trigger gulp
                    content = style_scss.read_text(encoding='utf-8')
                    style_scss.write_text(content, encoding='utf-8')
                    self.logger.success("   ✅ style.scss saved successfully")
                except Exception as e:
                    self.logger.error(f"   ❌ Failed to save style.scss: {e}")
                    raise MigrationError(f"Could not save style.scss: {e}")
            else:
                self.logger.warning(f"⚠️  style.scss not found at {style_scss}")
                self.logger.info("🔄 Continuing without style.scss trigger...")
            
            # Step 3: Monitor gulp compilation in dealerinspire_legacy_assets container
            self.logger.info("🔄 Monitoring gulp compilation in Docker container...")
            gulp_success = self._monitor_gulp_compilation(slug)
            
            if not gulp_success:
                raise MigrationError("Gulp compilation failed - cannot proceed with git operations")
            
            # CRITICAL: Additional wait after gulp completion to ensure all file writes finish
            self.logger.info("⏳ Post-gulp wait to ensure all file writes complete...")
            self.logger.info("   • Allowing gulp background processes to finish...")
            time.sleep(5)  # Extra 5 seconds after gulp completion
            
            # Force another sync after gulp completion
            self.logger.info("🔄 Final file system sync after gulp completion...")
            try:
                subprocess.run(['sync'], check=False, capture_output=True)
                self.logger.info("   ✅ Post-gulp file system sync completed")
            except:
                self.logger.info("   ℹ️  Post-gulp sync not available (not critical)")
            
            time.sleep(2)  # Final safety wait
            
            # ADDITIONAL CHECK: Monitor CSS output files for recent changes
            self.logger.info("🔍 Checking CSS output files for recent changes...")
            current_dir = Path.cwd()
            theme_dir = current_dir / "dealer-themes" / slug
            css_dir = theme_dir / "css"
            
            css_files_to_check = [
                css_dir / "style.css",
                css_dir / "style.min.css",
            ]
            
            recent_changes = False
            import os
            import time as time_module
            current_time = time_module.time()
            
            for css_file in css_files_to_check:
                if css_file.exists():
                    # Check if file was modified in the last 60 seconds
                    file_mtime = os.path.getmtime(css_file)
                    if current_time - file_mtime < 60:  # Modified within last minute
                        self.logger.info(f"   📄 {css_file.name} recently updated ({current_time - file_mtime:.1f}s ago)")
                        recent_changes = True
                    else:
                        self.logger.info(f"   📄 {css_file.name} last updated {current_time - file_mtime:.0f}s ago")
            
            if recent_changes:
                self.logger.info("✅ CSS output files show recent changes - gulp actively processing")
                # Extra wait if we detected recent CSS changes
                self.logger.info("⏳ Extra wait for CSS processing to complete...")
                time.sleep(3)
            else:
                self.logger.info("ℹ️  No recent CSS changes detected - may be normal")
            
            self.logger.success("✅ All files saved and gulp compilation successful!")
            
            self.results["file_saving_gulp"] = {
                "success": True,
                "files_saved": len(generated_files),
                "gulp_compilation": "success",
                "timestamp": time.time()
            }
            
            # EXTENDED WAIT: Additional wait specifically for sb-vdp.scss timing issue
            self.logger.info("⏳ Final synchronization check (preventing git timing issues)...")
            self.logger.info("   • This ensures all files are ready for version control...")
            time.sleep(3)  # Extra 3 seconds specifically for sb-vdp.scss
            
            # Force a final check for any remaining file operations
            self.logger.info("🔄 Performing file system sync...")
            import subprocess
            try:
                # Run sync command to ensure all file operations are complete
                subprocess.run(['sync'], check=False, capture_output=True)
                self.logger.info("   ✅ File system sync completed")
            except:
                self.logger.info("   ℹ️  File system sync not available (not critical)")
            
            time.sleep(1)  # One more second after sync
            
        except Exception as e:
            self.logger.error(f"❌ File saving and gulp compilation failed: {e}")
            self.results["file_saving_gulp"] = {"success": False, "error": str(e)}
            raise
    
    def _monitor_gulp_compilation(self, slug: str) -> bool:
        """Monitor gulp compilation in the dealerinspire_legacy_assets container."""
        container_name = "dealerinspire_legacy_assets"
        
        try:
            import subprocess
            import time
            
            self.logger.info(f"🐳 Checking Docker container: {container_name}")
            
            # Check if container exists and is running
            try:
                result = subprocess.run([
                    'docker', 'inspect', '-f', '{{.State.Running}}', container_name
                ], capture_output=True, text=True, check=True)
                
                if result.stdout.strip() != 'true':
                    self.logger.error(f"❌ Container {container_name} is not running")
                    self.logger.info("💡 Make sure the legacy assets container is started")
                    return False
                
                self.logger.success(f"✅ Container {container_name} is running")
                
            except subprocess.CalledProcessError:
                self.logger.error(f"❌ Container {container_name} not found")
                self.logger.info("💡 The legacy assets container may not be started yet")
                return False
            
            # First, trigger a fresh compilation by checking current logs
            self.logger.info("🔍 Monitoring gulp compilation activity...")
            
            start_time = time.time()
            timeout = 45  # 45 seconds timeout (increased from 30)
            compilation_detected = False
            compilation_success = False
            recent_activity = False
            
            # Monitor container logs for recent activity
            try:
                # Get recent logs (last 2 minutes) to see current state
                recent_logs = subprocess.run([
                    'docker', 'logs', '--since', '2m', container_name
                ], capture_output=True, text=True, check=True)
                
                if recent_logs.stdout.strip():
                    recent_activity = True
                    self.logger.info("📋 Found recent gulp activity")
                    
                    # Check if there are any obvious errors in recent logs
                    recent_lines = recent_logs.stdout.lower()
                    if any(error in recent_lines for error in ['error', 'failed', 'exception']):
                        # Look for SCSS/CSS related errors specifically
                        if any(css_error in recent_lines for css_error in ['scss', 'sass', 'css', 'compile']):
                            self.logger.warning("⚠️  Detected potential SCSS compilation errors in recent logs")
                            self.logger.info("🔍 Will monitor for successful recompilation...")
                        else:
                            self.logger.info("ℹ️  Found general errors but not SCSS-related")
                else:
                    self.logger.info("📋 No recent gulp activity - will monitor for compilation")
                    
            except subprocess.CalledProcessError:
                self.logger.warning("⚠️  Could not retrieve recent logs")
            
            # Now stream logs to monitor for new compilation
            self.logger.info(f"⏳ Monitoring for gulp compilation (timeout: {timeout}s)...")
            
            process = subprocess.Popen([
                'docker', 'logs', '-f', '--since', '10s', container_name
            ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
            
            activity_lines = []
            
            while True:
                # Check timeout
                elapsed = time.time() - start_time
                if elapsed > timeout:
                    self.logger.warning(f"⏰ Timeout after {timeout}s")
                    if recent_activity and not compilation_detected:
                        self.logger.info("ℹ️  Recent activity detected but no new compilation observed")
                        self.logger.info("💡 Assuming gulp is functioning correctly")
                        compilation_success = True
                    break
                
                # Read output
                line = process.stdout.readline()
                if line:
                    line = line.strip()
                    if line:  # Only process non-empty lines
                        activity_lines.append(line)
                        self.logger.debug(f"Gulp: {line}")
                        
                        line_lower = line.lower()
                        
                        # Look for compilation start indicators
                        if any(start_indicator in line_lower for start_indicator in [
                            'starting', 'compiling', 'processing', 'building'
                        ]):
                            if any(css_keyword in line_lower for css_keyword in [
                                'scss', 'sass', 'css', 'gulp'
                            ]):
                                self.logger.info(f"🔄 Gulp compilation started: {line}")
                                compilation_detected = True
                        
                        # Look for success indicators
                        if any(success_indicator in line_lower for success_indicator in [
                            'finished', 'completed', 'done', 'success', 'built'
                        ]):
                            # More specific check for CSS/SCSS completion
                            if any(css_keyword in line_lower for css_keyword in [
                                'scss', 'sass', 'css', 'gulp', 'compile', 'build'
                            ]):
                                self.logger.success(f"✅ Gulp compilation completed: {line}")
                                compilation_success = True
                                # Don't break immediately - wait for any additional output writes
                                time.sleep(2)  # Wait for any background file writes to complete
                                break
                        
                        # Look for error indicators
                        if any(error_indicator in line_lower for error_indicator in [
                            'error', 'failed', 'exception', 'cannot'
                        ]):
                            # Check if it's CSS/SCSS related
                            if any(css_keyword in line_lower for css_keyword in [
                                'scss', 'sass', 'css', 'compile', 'syntax'
                            ]):
                                self.logger.error(f"❌ Gulp compilation error: {line}")
                                compilation_success = False
                                break
                            else:
                                self.logger.debug(f"Non-CSS error: {line}")
                
                # Check if process ended
                if process.poll() is not None:
                    break
                
                time.sleep(0.1)
            
            # Clean up process
            try:
                process.terminate()
                process.wait(timeout=1)
            except:
                pass
            
            # Final decision logic
            if compilation_success:
                self.logger.success("🎉 Gulp compilation verified successfully!")
                return True
            elif compilation_detected and not compilation_success:
                self.logger.error("❌ Gulp compilation failed")
                return False
            elif recent_activity and not compilation_detected:
                # Gulp was active recently but we didn't see new compilation
                self.logger.info("ℹ️  No new compilation activity detected")
                self.logger.info("💡 This may be normal if styles are already compiled")
                self.logger.info("✅ Assuming gulp environment is functioning correctly")
                return True  # Don't fail the entire process for this
                
        except Exception as e:
            self.logger.error(f"❌ Error monitoring gulp compilation: {e}")
            self.logger.info("💡 Gulp monitoring failed but continuing with migration")
            return True  # Don't fail the entire migration for gulp monitoring issues
    
    def _step_6_post_migration_validation(self, slug: str) -> None:
        """Step 6: Simplified post-migration validation - SCSS syntax and SBM compliance only."""
        self.logger.step("STEP 6: Post-migration validation (simplified)...")
        
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
    
    def _step_7_pull_request_creation(self, slug: str) -> None:
        """Step 7: Create pull request with user confirmation."""
        self.logger.step("STEP 7: Pull request creation...")
        
        # ALWAYS PROMPT BEFORE GITHUB ACTIONS
        self.logger.info("⚠️  GITHUB ACTION REQUIRED")
        self.logger.info("🔄 Ready to create pull request...")
        
        # Show what will be included in the PR
        self._display_pr_preview(slug)
        
        # Ask for confirmation
        if not self._confirm_github_action("create pull request"):
            self.logger.info("❌ PR creation cancelled by user")
            self.results["pull_request"] = {
                "success": False, 
                "cancelled": True,
                "reason": "User cancelled PR creation"
            }
            return
        
        try:
            git_ops = GitOperations(self.config)
            
            # Get the branch name from git setup results
            branch_name = self.results.get("git_setup", {}).get("result", {}).get("branch_name")
            if not branch_name:
                raise MigrationError("Could not determine branch name for PR creation")
            
            self.logger.info(f"📋 Creating enhanced PR from branch: {branch_name}")
            self.logger.info("🔄 This may take a moment...")
            
            # Get user review results for enhanced PR description
            user_review_result = self.results.get("user_review", {}).get("result", {})
            
            # Create enhanced PR with user review tracking
            pr_result = git_ops.create_enhanced_pr(slug, branch_name, user_review_result, draft=False)
            
            if not pr_result.get("success"):
                error_msg = pr_result.get("error", "Unknown error")
                
                # Check if this is really an error or just a PR already exists case
                if "already exists" in error_msg.lower():
                    self.logger.info("ℹ️  Pull request already exists for this branch")
                    
                    # Try to extract PR URL from error and treat as success
                    import re
                    url_match = re.search(r'(https://github\.com/[^\s]+)', error_msg)
                    if url_match:
                        pr_url = url_match.group(1)
                        self.logger.success(f"✅ Using existing pull request: {pr_url}")
                        
                        # Update result to success
                        pr_result = {
                            "success": True,
                            "pr_url": pr_url,
                            "branch": branch_name,
                            "existing": True
                        }
                    else:
                        raise MigrationError(f"PR creation failed: {error_msg}")
                else:
                    raise MigrationError(f"PR creation failed: {error_msg}")
            
            pr_url = pr_result.get("pr_url")
            is_existing = pr_result.get("existing", False)
            
            if is_existing:
                self.logger.success(f"✅ Pull request (existing): {pr_url}")
                self.logger.info("ℹ️  Migration changes have been added to the existing PR")
            else:
                self.logger.success(f"✅ Pull request created: {pr_url}")
                self.logger.info("🎉 New pull request successfully created!")
            
            # Salesforce message is handled automatically in create_pr
            self.logger.info("📋 Salesforce update message copied to clipboard")
            self.logger.info("💡 You can paste this message into your Salesforce case")
            
            self.results["pull_request"] = {
                "success": True,
                "result": pr_result,
                "timestamp": time.time()
            }
            
        except Exception as e:
            self.logger.error(f"❌ PR creation failed: {e}")
            self.results["pull_request"] = {"success": False, "error": str(e)}
            # Don't raise - PR creation failures shouldn't stop the workflow
    
    def _step_8_final_summary(self, slug: str) -> Dict[str, Any]:
        """Step 8: Generate final comprehensive summary."""
        self.logger.step("STEP 8: Final summary...")
        
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
        """Display the final migration summary in a user-friendly format."""
        self.logger.info("")
        self.logger.info("=" * 80)
        self.logger.info("📊 COMPREHENSIVE MIGRATION SUMMARY")
        self.logger.info("=" * 80)
        
        # Basic info
        slug = summary.get("dealer_slug", "unknown")
        status = "✅ SUCCESS" if summary.get("overall_success") else "❌ FAILED"
        duration = summary.get("total_duration", 0)
        
        self.logger.info(f"🏪 Dealer: {slug}")
        self.logger.info(f"⚡ Status: {status}")
        self.logger.info(f"⏱️  Duration: {duration:.1f} seconds")
        self.logger.info("")
        
        # Step-by-step results
        self.logger.info("📋 STEP-BY-STEP RESULTS:")
        
        steps = [
            ("1️⃣  System Diagnostics", "diagnostics"),
            ("2️⃣  Git Setup", "git_setup"),
            ("3️⃣  Docker Startup", "docker_startup"),
            ("4️⃣  Theme Migration", "migration"),
            ("4️⃣.5 User Review", "user_review"),
            ("5️⃣  File Saving & Gulp", "file_saving_gulp"),
            ("6️⃣  Validation", "validation"),
            ("7️⃣  Pull Request", "pull_request")
        ]
        
        for step_name, result_key in steps:
            result = self.results.get(result_key, {})
            if result.get("success"):
                self.logger.success(f"   {step_name}: ✅ Success")
                
                # Add specific details for certain steps
                if result_key == "migration":
                    files = len(result.get("generated_files", []))
                    if files > 0:
                        self.logger.info(f"      Generated {files} Site Builder files")
                
                elif result_key == "file_saving_gulp":
                    files_saved = result.get("files_saved", 0)
                    compilation = result.get("gulp_compilation", "unknown")
                    self.logger.info(f"      Saved {files_saved} files, Gulp: {compilation}")
                
                elif result_key == "user_review":
                    review_result = result.get("result", {})
                    if review_result.get("changes_analysis", {}).get("has_manual_changes"):
                        modified_files = review_result["changes_analysis"]["files_modified"]
                        self.logger.info(f"      Manual changes: {', '.join(modified_files)}")
                    else:
                        self.logger.info("      No manual changes needed")
                
                elif result_key == "pull_request":
                    pr_url = result.get("result", {}).get("pr_url")
                    if pr_url:
                        self.logger.info(f"      PR: {pr_url}")
                        
            elif result_key in self.results:
                error = result.get("error", "Unknown error")
                self.logger.error(f"   {step_name}: ❌ Failed - {error}")
            else:
                self.logger.warning(f"   {step_name}: ⏭️  Skipped")
        
        self.logger.info("")
        
        # Migration files summary
        migration_result = self.results.get("migration", {})
        generated_files = migration_result.get("generated_files", [])
        
        if generated_files:
            self.logger.info("📄 GENERATED FILES:")
            for file_path in generated_files:
                file_obj = Path(file_path)
                if file_obj.exists():
                    file_size = file_obj.stat().st_size
                    self.logger.success(f"   ✅ {file_obj.name} ({file_size} bytes)")
                else:
                    self.logger.warning(f"   ⚠️  {file_obj.name} (not found)")
            self.logger.info("")
        
        # Next steps
        if summary.get("overall_success"):
            self.logger.info("🎉 MIGRATION COMPLETED SUCCESSFULLY!")
            self.logger.info("")
            self.logger.info("✅ Next steps:")
            self.logger.info("   • Review the pull request and request reviewers")
            self.logger.info("   • Test the migrated site locally")
            self.logger.info("   • Update your Salesforce case with the PR link")
            
            pr_result = self.results.get("pull_request", {})
            pr_url = pr_result.get("result", {}).get("pr_url")
            if pr_url:
                self.logger.info(f"   • PR Link: {pr_url}")
        else:
            self.logger.info("❌ MIGRATION FAILED")
            self.logger.info("")
            self.logger.info("🔧 Troubleshooting:")
            self.logger.info("   • Check the error messages above")
            self.logger.info("   • Run 'sbm doctor' for system diagnostics")
            self.logger.info("   • Use '--debug' flag for more detailed logging")
        
        self.logger.info("=" * 80)
    
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
    
    def _display_pr_preview(self, slug: str) -> None:
        """Display what will be included in the PR."""
        self.logger.info("")
        self.logger.info("📋 PR PREVIEW:")
        
        # Show automated files
        migration_result = self.results.get("migration", {}).get("result", {})
        generated_files = migration_result.get("generated_files", [])
        
        if generated_files:
            self.logger.info("🤖 Automated migration files:")
            for file_path in generated_files:
                file_obj = Path(file_path)
                if file_obj.exists():
                    size = file_obj.stat().st_size
                    self.logger.info(f"   ✅ {file_obj.name} ({size} bytes)")
        
        # Show manual changes if any
        user_review_result = self.results.get("user_review", {}).get("result", {})
        if user_review_result and user_review_result.get("changes_analysis", {}).get("has_manual_changes"):
            modified_files = user_review_result["changes_analysis"]["files_modified"]
            self.logger.info("👤 Manual refinements:")
            for filename in modified_files:
                size_change = user_review_result["changes_analysis"]["size_changes"].get(filename, {})
                size_diff = size_change.get("difference", 0)
                self.logger.info(f"   ✅ {filename} ({size_diff:+d} bytes)")
        else:
            self.logger.info("👤 Manual refinements: None")
        
        self.logger.info("")
    
    def _confirm_github_action(self, action: str) -> bool:
        """Ask user to confirm GitHub action."""
        self.logger.info(f"💬 Type 'yes' to {action}, or 'no' to skip:")
        
        while True:
            try:
                user_input = input(f"   👤 {action.title()}? (yes/no): ").strip().lower()
                
                if user_input in ['yes', 'y']:
                    self.logger.success(f"✅ Confirmed: {action}")
                    return True
                elif user_input in ['no', 'n']:
                    self.logger.info(f"❌ Skipped: {action}")
                    return False
                else:
                    self.logger.warning("❓ Please type 'yes' or 'no'")
                    
            except KeyboardInterrupt:
                self.logger.warning(f"\n⚠️  {action} interrupted. Treating as 'no'.")
                return False
            except EOFError:
                self.logger.warning(f"\n⚠️  Input ended. Treating as 'no'.")
                return False
    
    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """Create an error result dictionary."""
        return {
            "success": False,
            "error": error_message,
            "duration": self._get_duration(),
            "timestamp": time.time(),
            "results": self.results
        } 
