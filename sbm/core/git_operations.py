"""
Git operations for SBM Tool V2.

Handles Git repository operations for migration workflow.
"""

import os
import subprocess
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from sbm.config import Config
from sbm.utils.logger import get_logger
from sbm.utils.errors import GitError


class GitOperations:
    """Handles Git operations for migration."""
    
    def __init__(self, config: Config):
        """Initialize Git operations."""
        self.config = config
        self.logger = get_logger("git")
    
    def monitor_just_start(self, slug: str, use_prod_db: bool = False) -> Dict[str, Any]:
        """Monitor an existing 'just start' process with real-time output visible to user."""
        import time
        import psutil
        
        try:
            start_time = time.time()
            just_start_cmd = f"just start {slug} prod" if use_prod_db else f"just start {slug}"
            
            self.logger.warning("⚠️  Looking for existing 'just start' process...")
            self.logger.warning(f"⚠️  Make sure you've already run '{just_start_cmd}' in another terminal")
            
            # Look for existing just start process
            process = None
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if proc.info['cmdline'] and 'just' in proc.info['cmdline'][0] and 'start' in ' '.join(proc.info['cmdline']):
                        if slug in ' '.join(proc.info['cmdline']):
                            process = proc
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            if process:
                self.logger.info(f"Found existing 'just start {slug}' process (PID: {process.pid})")
                # We found an existing process, so we'll monitor Docker logs instead
                process = None  # Clear this to go to Docker monitoring path below
            else:
                self.logger.warning("No existing 'just start' process found. Starting new one...")
            
            # Start new process or monitor via Docker logs
            if not process:
                # Try to monitor via Docker logs first (faster than waiting)
                container_name = f'di-websites-platform-{slug}-1'
                
                # Reduced wait time from 60 to 10 seconds for container detection
                self.logger.info(f"🔍 Checking for Docker container: {container_name}")
                container_exists = False
                for i in range(10):  # Only wait 10 seconds instead of 60
                    try:
                        result = subprocess.run(['docker', 'inspect', container_name], 
                                              capture_output=True, check=True)
                        container_exists = True
                        self.logger.info("✅ Found existing Docker container, monitoring logs...")
                        break
                    except subprocess.CalledProcessError:
                        if i == 0:
                            self.logger.info("🔄 Container not found yet, checking for startup...")
                        time.sleep(1)
                
                if not container_exists:
                    self.logger.info(f"Container {container_name} not found after 10 seconds, starting new 'just start' process...")
                    cmd = ['just', 'start', slug]
                    if use_prod_db:
                        cmd.append('prod')
                    
                    try:
                        process = subprocess.Popen(
                            cmd,
                            cwd=self.config.di_platform_dir,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            text=True,
                            bufsize=1,  # Line buffered
                            universal_newlines=True
                        )
                        self.logger.info(f"✅ Started new 'just start {slug}' process (PID: {process.pid})")
                    except Exception as e:
                        return {
                            "success": False,
                            "error": f"Failed to start 'just start' process: {e}",
                            "retry_suggestion": f"Try running '{just_start_cmd}' manually in {self.config.di_platform_dir}"
                        }
                else:
                    process = subprocess.Popen(
                        ['docker', 'logs', '-f', container_name],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        bufsize=1,
                        universal_newlines=True
                    )
            
            self.logger.info(f"Started 'just start {slug}' (PID: {process.pid})")
            print("=" * 60)
            print(f"DOCKER STARTUP OUTPUT FOR {slug.upper()}")
            print("=" * 60)
            
            # Monitor the process with real-time output
            timeout = 300  # 5 minutes timeout
            output_lines = []
            happy_coding_detected = False
            
            # Read output line by line in real-time
            while True:
                # Check if process is still running
                if process.poll() is not None and not happy_coding_detected:
                    break
                    
                # Check for timeout
                elapsed = time.time() - start_time
                if elapsed > timeout:
                    self.logger.error("Timeout waiting for 'just start' to complete")
                    process.terminate()
                    print("=" * 60)
                    return {
                        "success": False,
                        "error": "Timeout waiting for Docker container to start (5 minutes)"
                    }
                
                # Read a line of output
                try:
                    line = process.stdout.readline()
                    if line:
                        # Print the line immediately so user can see it
                        print(line.rstrip())
                        output_lines.append(line.rstrip())
                        
                        # Check for common success indicators
                        line_lower = line.lower()
                        
                        # Check for mysqldump error and handle it
                        if 'mysqldump transfer failed' in line_lower or 'file contained invalid output' in line_lower:
                            self.logger.warning("⚠️  Detected mysqldump error - this is common and usually not critical for SBM")
                            self.logger.info("Continuing to monitor for successful startup...")
                        
                        if any(indicator in line_lower for indicator in [
                            'happy coding', 'server started', 'ready', 'listening on', 
                            'compiled successfully', 'webpack compiled', 'development server is running',
                            'finished make:vhosts', 'welcome to the di website platform'
                        ]):
                            self.logger.info(f"Detected startup indicator: {line.strip()}")
                            
                            # If we see "Happy coding!" - that's the definitive completion signal
                            if 'happy coding' in line_lower:
                                self.logger.success("✅ 🎉 Docker startup completed - detected 'Happy coding!' message")
                                happy_coding_detected = True
                                # Terminate the process and exit immediately
                                try:
                                    process.terminate()
                                except:
                                    pass
                                print("=" * 60)
                                # CRITICAL FIX: Return success immediately when Happy coding! is detected
                                return {
                                    "success": True,
                                    "message": "Docker container ready - Happy coding! detected",
                                    "duration": time.time() - start_time,
                                    "output": output_lines
                                }
                    else:
                        # No output, sleep briefly but check if we already detected happy coding
                        if happy_coding_detected:
                            break
                        time.sleep(0.1)
                except:
                    if happy_coding_detected:
                        break
                    # If there's an error but we detected happy coding, still return success
                    if any('happy coding' in line.lower() for line in output_lines):
                        return {
                            "success": True,
                            "message": "Docker container ready - Happy coding! detected",
                            "duration": time.time() - start_time,
                            "output": output_lines
                        }
                    break
            
            # If we get here and happy_coding_detected is True, return success
            if happy_coding_detected:
                return {
                    "success": True,
                    "message": "Docker container ready - Happy coding! detected",
                    "duration": time.time() - start_time,
                    "output": output_lines
                }
            
            # Process completed, get final output
            try:
                remaining_output, _ = process.communicate(timeout=5)
                if remaining_output:
                    print(remaining_output)
                    output_lines.extend(remaining_output.split('\n'))
            except:
                pass
            
            print("=" * 60)
            
            # Check if we detected "Happy coding!" in the complete output
            happy_coding_in_output = any('happy coding' in line.lower() for line in output_lines)
            
            if process.returncode == 0 or happy_coding_in_output:
                self.logger.success("✅ Docker container started successfully!")
                self.logger.info("Ready to proceed with migration")
                return {
                    "success": True,
                    "message": "Docker container ready",
                    "duration": time.time() - start_time,
                    "output": output_lines
                }
            else:
                # Look for error indicators in output, but exclude mysqldump errors
                error_lines = [line for line in output_lines if any(err in line.lower() for err in [
                    'error', 'failed', 'exception', 'cannot', 'unable'
                ]) and not any(ignore in line.lower() for ignore in [
                    'mysqldump transfer failed', 'file contained invalid output'
                ])]
                
                # If we only have mysqldump errors, consider it a success if we got other indicators
                if not error_lines and any('mysqldump' in line.lower() for line in output_lines):
                    self.logger.warning("⚠️  Only mysqldump errors detected - treating as successful startup")
                    return {
                        "success": True,
                        "message": "Docker container ready (with mysqldump warnings)",
                        "duration": time.time() - start_time,
                        "output": output_lines
                    }
                
                error_msg = "Docker startup failed"
                if error_lines:
                    error_msg = f"Docker startup failed: {error_lines[-1]}"
                
                self.logger.error(f"'just start' failed with return code {process.returncode}")
                return {
                    "success": False,
                    "error": error_msg,
                    "output": output_lines
                }
                
        except Exception as e:
            self.logger.error(f"Error monitoring just start: {e}")
            return {
                "success": False,
                "error": f"Failed to monitor Docker startup: {e}",
                "output": []
            }

    def pre_migration_setup(self, slug: str, auto_start: bool = False) -> Dict[str, Any]:
        """Execute the pre-migration git workflow."""
        try:
            self.logger.step("Starting pre-migration git workflow...")
            
            # Step 1: git switch main && git pull && git fetch --prune && git status
            self.logger.info("Switching to main branch...")
            subprocess.run(['git', 'switch', 'main'], check=True, capture_output=True)
            
            self.logger.info("Pulling latest changes...")
            subprocess.run(['git', 'pull'], check=True, capture_output=True)
            
            self.logger.info("Fetching and pruning...")
            subprocess.run(['git', 'fetch', '--prune'], check=True, capture_output=True)
            
            # Check status and handle uncommitted changes
            status_result = subprocess.run(['git', 'status', '--porcelain'], 
                                         capture_output=True, text=True, check=True)
            if status_result.stdout.strip():
                self.logger.warning("Working directory has uncommitted changes, stashing them...")
                subprocess.run(['git', 'stash'], check=True, capture_output=True)
            
            # Step 2: git pull (second pull as specified)
            self.logger.info("Second pull to ensure up-to-date...")
            subprocess.run(['git', 'pull'], check=True, capture_output=True)
            
            # Step 3: Create branch with correct naming - FIXED to use MMYY format (month+year)
            import datetime
            date_suffix = datetime.datetime.now().strftime("%m%y")  # Use MMYY format (month+year)
            branch_name = f"{slug}-sbm{date_suffix}"  # lowercase 'sbm'
            
            # Check if branch already exists
            branch_created = False
            try:
                # Check if branch exists locally
                result = subprocess.run(['git', 'show-ref', '--verify', '--quiet', f'refs/heads/{branch_name}'], 
                                      capture_output=True)
                if result.returncode == 0:
                    # Branch exists, switch to it
                    self.logger.info(f"Branch {branch_name} already exists, switching to it...")
                    subprocess.run(['git', 'checkout', branch_name], check=True, capture_output=True)
                    branch_created = False
                else:
                    # Branch doesn't exist, create it
                    self.logger.info(f"Creating new branch: {branch_name}")
                    subprocess.run(['git', 'checkout', '-b', branch_name], check=True, capture_output=True)
                    branch_created = True
            except subprocess.CalledProcessError:
                # If there's any issue, try creating with a unique suffix
                import time
                unique_suffix = int(time.time()) % 10000
                branch_name = f"{slug}-sbm{date_suffix}-{unique_suffix}"
                self.logger.info(f"Creating unique branch: {branch_name}")
                subprocess.run(['git', 'checkout', '-b', branch_name], check=True, capture_output=True)
                branch_created = True
            
            # Step 4: Add dealer to sparse checkout
            self.logger.info(f"Adding {slug} to sparse checkout...")
            subprocess.run(['git', 'sparse-checkout', 'add', f'dealer-themes/{slug}'], 
                         check=True, capture_output=True)
            
            self.logger.success(f"✅ Pre-migration git setup completed - Branch: {branch_name}")
            
            if auto_start:
                # Automatically start and monitor the just start process
                start_result = self.monitor_just_start(slug)
                if start_result['success']:
                    return {
                        "success": True,
                        "branch_name": branch_name,
                        "message": "Pre-migration setup and Docker startup completed",
                        "docker_ready": True
                    }
                else:
                    return {
                        "success": False,
                        "branch_name": branch_name,
                        "error": f"Git setup succeeded but Docker startup failed: {start_result['error']}"
                    }
            else:
                self.logger.warning("⚠️  WAITING FOR DOCKER CONTAINER TO START...")
                self.logger.warning("⚠️  Sparse checkout will trigger Docker/Gulp processes")
                self.logger.warning("⚠️  DO NOT PROCEED until container is fully started!")
                self.logger.info(f"Run: 'just start {slug}' in {self.config.di_platform_dir}")
                
                return {
                    "success": True,
                    "branch_name": branch_name,
                    "message": "Pre-migration setup completed - waiting for Docker container"
                }
            
        except subprocess.CalledProcessError as e:
            error_msg = f"Git command failed: {e}"
            self.logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }
        except Exception as e:
            error_msg = f"Pre-migration setup failed: {e}"
            self.logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }

    def create_branch(self, slug: str) -> Dict[str, Any]:
        """Create a migration branch with actual git operations."""
        import datetime
        date_suffix = datetime.datetime.now().strftime("%m%y")  # MMYY format (month+year)
        branch_name = f"{slug}-sbm{date_suffix}"  # lowercase 'sbm'
        
        try:
            self.logger.info(f"Creating branch: {branch_name}")
            
            # Check if branch already exists
            result = subprocess.run(['git', 'show-ref', '--verify', '--quiet', f'refs/heads/{branch_name}'], 
                                  capture_output=True, cwd=self.config.di_platform_dir)
            if result.returncode == 0:
                # Branch exists, switch to it
                self.logger.info(f"Branch {branch_name} already exists, switching to it...")
                subprocess.run(['git', 'checkout', branch_name], check=True, capture_output=True, cwd=self.config.di_platform_dir)
            else:
                # Branch doesn't exist, create it
                self.logger.info(f"Creating new branch: {branch_name}")
                subprocess.run(['git', 'checkout', '-b', branch_name], check=True, capture_output=True, cwd=self.config.di_platform_dir)
            
            self.logger.success(f"✅ Successfully created/switched to branch: {branch_name}")
            
            return {
                "success": True,
                "branch": branch_name,
                "message": "Branch created successfully"
            }
            
        except subprocess.CalledProcessError as e:
            # If there's any issue, try creating with a unique suffix
            try:
                import time
                unique_suffix = int(time.time()) % 10000
                branch_name = f"{slug}-sbm{date_suffix}-{unique_suffix}"
                self.logger.info(f"Creating unique branch: {branch_name}")
                subprocess.run(['git', 'checkout', '-b', branch_name], check=True, capture_output=True, cwd=self.config.di_platform_dir)
                
                return {
                    "success": True,
                    "branch": branch_name,
                    "message": "Branch created with unique suffix"
                }
            except subprocess.CalledProcessError as fallback_error:
                error_msg = f"Failed to create branch: {fallback_error}"
                self.logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg
                }
        except Exception as e:
            error_msg = f"Unexpected error creating branch: {e}"
            self.logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }
    
    def commit_changes(self, message: str, files: Optional[List[str]] = None) -> Dict[str, Any]:
        """Commit changes to git repository with better error handling."""
        try:
            # Check if we're in a git repository - ensure we're in the right directory
            original_cwd = os.getcwd()
            os.chdir(self.config.di_platform_dir)
            
            if not self._is_git_repo():
                error_msg = "Not in a git repository"
                self.logger.error(error_msg)
                os.chdir(original_cwd)  # Restore directory
                return {"committed": False, "error": error_msg}
            
            # Wait a moment to ensure all file operations are complete
            import time
            time.sleep(1)
            
            # EXTENDED PRE-COMMIT CHECK: Look for files still being modified
            self.logger.info("🔍 Pre-commit check for file modifications...")
            
            # Check git status multiple times to detect files still being written
            for attempt in range(3):
                try:
                    status_result = subprocess.run(['git', 'status', '--porcelain'], 
                                                 capture_output=True, text=True, check=True,
                                                 cwd=self.config.di_platform_dir)
                    current_changes = status_result.stdout.strip().split('\n') if status_result.stdout.strip() else []
                    
                    if current_changes:
                        self.logger.info(f"   📋 Attempt {attempt + 1}: Found {len(current_changes)} file changes")
                        
                        # DEBUG: Show all files that have changes
                        for change in current_changes:
                            if change.strip():
                                self.logger.debug(f"      Git status: {change}")
                        
                        # Check if sb-vdp.scss is among the changes
                        vdp_changes = [line for line in current_changes if 'sb-vdp.scss' in line]
                        if vdp_changes:
                            self.logger.warning(f"   ⚠️  sb-vdp.scss still showing changes: {vdp_changes[0]}")
                            if attempt < 2:  # Only wait if we have more attempts
                                self.logger.info("   ⏳ Waiting additional time for sb-vdp.scss to stabilize...")
                                time.sleep(3)
                                continue
                    else:
                        self.logger.info(f"   📋 Attempt {attempt + 1}: No changes detected")
                    
                    break  # Exit the loop if we didn't find concerning changes
                    
                except subprocess.CalledProcessError:
                    break
            
            time.sleep(0.5)  # Final brief wait
            
            # Add files to staging area
            if files:
                for file_path in files:
                    # Convert absolute paths to relative paths from di_platform_dir
                    if os.path.isabs(file_path):
                        # Convert absolute path to relative path from di_platform_dir
                        try:
                            relative_path = os.path.relpath(file_path, self.config.di_platform_dir)
                            file_path = relative_path
                        except ValueError:
                            # Path is not under di_platform_dir, use absolute path
                            pass
                    
                    # Check if file exists before trying to add it
                    full_path = os.path.join(self.config.di_platform_dir, file_path) if not os.path.isabs(file_path) else file_path
                    if not os.path.exists(full_path):
                        error_msg = f"File does not exist: {full_path}"
                        self.logger.error(error_msg)
                        os.chdir(original_cwd)  # Restore directory
                        return {"committed": False, "error": error_msg}
                    
                    try:
                        result = subprocess.run(['git', 'add', file_path], 
                                              check=True, capture_output=True, text=True, 
                                              cwd=self.config.di_platform_dir)
                        self.logger.debug(f"Added {file_path} to staging area")
                    except subprocess.CalledProcessError as e:
                        error_msg = f"Failed to add {file_path} to git: {e}"
                        if e.stderr:
                            error_msg += f" - {e.stderr.strip()}"
                        self.logger.error(error_msg)
                        os.chdir(original_cwd)  # Restore directory
                        return {"committed": False, "error": error_msg}
            else:
                # Add all changes if no specific files provided
                try:
                    subprocess.run(['git', 'add', '.'], 
                                 check=True, capture_output=True, text=True,
                                 cwd=self.config.di_platform_dir)
                    self.logger.debug("Added all changes to staging area")
                except subprocess.CalledProcessError as e:
                    error_msg = f"Failed to add changes to git: {e}"
                    if e.stderr:
                        error_msg += f" - {e.stderr.strip()}"
                    self.logger.error(error_msg)
                    os.chdir(original_cwd)  # Restore directory
                    return {"committed": False, "error": error_msg}
                
            # ADDITIONAL: Force add all sb-*.scss files to ensure they're staged
            self.logger.info("🔍 Ensuring all Site Builder SCSS files are staged...")
            try:
                # Use git add with glob pattern to catch all sb-*.scss files
                subprocess.run(['git', 'add', 'dealer-themes/*/sb-*.scss'], 
                             check=False, capture_output=True, text=True,
                             cwd=self.config.di_platform_dir)
                self.logger.debug("Force-added all sb-*.scss files")
            except Exception as e:
                self.logger.debug(f"Force add sb-*.scss failed (not critical): {e}")
            
            # Wait another moment after adding files to ensure they're properly staged
            time.sleep(0.5)
            
            # Check if there are any changes to commit
            status_result = subprocess.run(['git', 'status', '--porcelain'], 
                                         capture_output=True, text=True, check=True,
                                         cwd=self.config.di_platform_dir)
            if not status_result.stdout.strip():
                self.logger.info("No changes to commit")
                os.chdir(original_cwd)  # Restore directory
                return {"committed": False, "message": "No changes to commit"}
            
            # Show what's being committed for transparency
            staged_files = [line.strip() for line in status_result.stdout.strip().split('\n') if line.strip()]
            self.logger.debug(f"Committing {len(staged_files)} changed files")
            
            # Commit the changes
            try:
                commit_result = subprocess.run(['git', 'commit', '-m', message], 
                                             check=True, capture_output=True, text=True,
                                             cwd=self.config.di_platform_dir)
                self.logger.success(f"✅ Committed changes: {message}")
                os.chdir(original_cwd)  # Restore directory
                return {"committed": True, "message": message}
            except subprocess.CalledProcessError as e:
                # Clean up error message - don't include random stdout/stderr
                error_msg = f"Command '['git', 'commit', '-m', '{message}']' returned non-zero exit status {e.returncode}."
                
                # Only include stderr if it's actually from git and not mixed with other output
                if e.stderr and e.stderr.strip():
                    stderr_lines = e.stderr.strip().split('\n')
                    # Filter out non-git related lines (like Docker build output)
                    git_error_lines = [line for line in stderr_lines 
                                     if any(keyword in line.lower() for keyword in 
                                           ['git', 'commit', 'nothing to commit', 'working tree clean', 
                                            'author', 'email', 'config', 'branch'])]
                    if git_error_lines:
                        error_msg += f" Git error: {git_error_lines[0]}"
                
                self.logger.error(f"Failed to commit changes: {error_msg}")
                os.chdir(original_cwd)  # Restore directory
                return {"committed": False, "error": error_msg}
            
        except subprocess.CalledProcessError as e:
            error_msg = f"Git operation failed: {e}"
            if hasattr(e, 'stderr') and e.stderr:
                error_msg += f" - {e.stderr.strip()}"
            self.logger.error(error_msg)
            if 'original_cwd' in locals():
                os.chdir(original_cwd)  # Restore directory
            return {"committed": False, "error": error_msg}
        except Exception as e:
            error_msg = f"Unexpected error during commit: {e}"
            self.logger.error(error_msg)
            if 'original_cwd' in locals():
                os.chdir(original_cwd)  # Restore directory
            return {"committed": False, "error": error_msg}

    def create_enhanced_pr(self, slug: str, branch_name: str, user_review_result: Dict[str, Any] = None, draft: bool = False) -> Dict[str, Any]:
        """Create a PR with enhanced tracking of automated vs manual changes."""
        try:
            # Check if we're in a Git repository
            if not self._is_git_repo():
                raise Exception("Not in a Git repository")
            
            # Check GitHub CLI availability and auth
            if not self._check_gh_cli():
                raise Exception("GitHub CLI not available or not authenticated")
            
            # Get repository info
            repo_info = self._get_repo_info()
            current_branch = repo_info.get('current_branch', branch_name)
            
            # Build enhanced PR content
            pr_content = self._build_enhanced_pr_content(slug, current_branch, repo_info, user_review_result)
            
            # Create the PR
            pr_url = self._execute_gh_pr_create(
                title=pr_content['title'],
                body=pr_content['body'],
                base=self.config.git.default_branch,
                head=current_branch,
                draft=draft,
                reviewers=self.config.git.default_reviewers,
                labels=self.config.git.default_labels
            )
            
            # Open the PR in browser after creation
            self._open_pr_in_browser(pr_url)
            
            # Copy enhanced Salesforce message to clipboard
            self._copy_salesforce_message_to_clipboard(pr_content['what_section'], pr_url)
            
            return {
                "success": True,
                "pr_url": pr_url,
                "branch": current_branch,
                "title": pr_content['title'],
                "pr_body": pr_content['body']
            }
            
        except Exception as e:
            error_str = str(e)
            self.logger.error(f"Enhanced PR creation failed: {error_str}")
            
            # Check if it's an "already exists" error and handle gracefully
            if "already exists" in error_str:
                # Try to extract PR URL from error message
                import re
                url_match = re.search(r'(https://github\.com/[^\s]+)', error_str)
                if url_match:
                    existing_pr_url = url_match.group(1)
                    self.logger.info(f"PR already exists: {existing_pr_url}")
                    
                    # Still copy enhanced Salesforce message since migration completed
                    pr_content = self._build_enhanced_pr_content(slug, branch_name, {}, user_review_result)
                    self._copy_salesforce_message_to_clipboard(pr_content['what_section'], existing_pr_url)
                    
                    return {
                        "success": True,  # Mark as success since PR exists
                        "pr_url": existing_pr_url,
                        "branch": branch_name,
                        "title": pr_content['title'],
                        "existing": True
                    }
            
            return {
                "success": False,
                "error": error_str
            }
    
    def _generate_enhanced_pr_description(self, slug: str, user_review_result: Dict[str, Any] = None) -> str:
        """Generate enhanced PR description with automated vs manual tracking."""
        from sbm.core.user_review import UserReviewManager
        
        # Base PR template
        description = f"""## Site Builder Migration - {slug.replace('_', ' ').title()}

### Summary
This PR contains the Site Builder migration for {slug}, including both automated migration and manual refinements.

"""
        
        # Add automated section
        description += "### 🤖 Automated Migration\n"
        description += "The SBM tool automatically migrated the following files:\n"
        description += "- `sb-inside.scss`\n"
        description += "- `sb-vdp.scss`\n" 
        description += "- `sb-vrp.scss`\n\n"
        
        # Add manual section if user review data exists
        if user_review_result and user_review_result.get("changes_analysis", {}).get("has_manual_changes"):
            changes_analysis = user_review_result["changes_analysis"]
            modified_files = changes_analysis["files_modified"]
            
            description += "### 👤 Manual Refinements\n"
            description += "Developer made additional manual improvements to:\n"
            for filename in modified_files:
                size_change = changes_analysis["size_changes"].get(filename, {})
                size_diff = size_change.get("difference", 0)
                description += f"- `{filename}` ({size_diff:+d} bytes)\n"
            
            description += "\n**Manual changes help improve the automation** - these will be reviewed to enhance future migrations.\n\n"
        else:
            description += "### 👤 Manual Refinements\n"
            description += "No manual changes were needed - automation was sufficient!\n\n"
        
        # Add WHAT section for Salesforce
        description += "## WHAT\n"
        description += f"Site Builder migration for {slug} completed:\n\n"
        
        if user_review_result and user_review_result.get("changes_analysis", {}).get("has_manual_changes"):
            description += "**🤖 Automated Migration:**\n"
            description += "- Created Site Builder SCSS files (sb-inside.scss, sb-vdp.scss, sb-vrp.scss)\n"
            description += "- Migrated legacy styles to Site Builder format\n"
            description += "- Applied standard SBM transformations\n\n"
            
            description += "**👤 Manual Refinements:**\n"
            changes_analysis = user_review_result["changes_analysis"]
            for filename in changes_analysis["files_modified"]:
                description += f"- Enhanced {filename} with custom improvements\n"
            description += "- Added dealer-specific styling optimizations\n\n"
            
            description += "**🎯 Result:** Combined automated + manual migration provides optimal Site Builder implementation.\n"
        else:
            description += "**🤖 Automated Migration:**\n"
            description += "- Created Site Builder SCSS files (sb-inside.scss, sb-vdp.scss, sb-vrp.scss)\n"
            description += "- Migrated legacy styles to Site Builder format\n"
            description += "- Applied standard SBM transformations\n\n"
            
            description += "**🎯 Result:** Automation was sufficient - no manual changes needed.\n"
        
        return description
    
    def _build_enhanced_pr_content(self, slug: str, branch: str, repo_info: Dict[str, str], user_review_result: Dict[str, Any] = None) -> Dict[str, str]:
        """Build enhanced PR content with automated vs manual tracking."""
        title = f"{slug} - SBM FE Audit"
        
        # Build WHAT section with enhanced tracking
        what_items = []
        
        # Automated migration items
        what_items.extend([
            "**🤖 Automated Migration:**",
            "- Migrated interior page styles from inside.scss and style.scss to sb-inside.scss",
            "- Created Site Builder SCSS files (sb-inside.scss, sb-vdp.scss, sb-vrp.scss)",
            "- Applied standard SBM transformations and pattern matching"
        ])
        
        # Manual refinements if any
        if user_review_result and user_review_result.get("changes_analysis", {}).get("has_manual_changes"):
            changes_analysis = user_review_result["changes_analysis"]
            modified_files = changes_analysis["files_modified"]
            
            what_items.extend([
                "",
                "**👤 Manual Refinements:**"
            ])
            
            for filename in modified_files:
                size_change = changes_analysis["size_changes"].get(filename, {})
                size_diff = size_change.get("difference", 0)
                what_items.append(f"- Enhanced {filename} with custom improvements ({size_diff:+d} bytes)")
            
            what_items.extend([
                "- Added dealer-specific styling optimizations",
                "- Fine-tuned responsive behavior and brand alignment"
            ])
        else:
            what_items.extend([
                "",
                "**✅ Automation Status:** No manual changes needed - automation was sufficient!"
            ])
        
        # Add FCA-specific items for Stellantis brands if applicable
        if any(brand in slug.lower() for brand in ['chrysler', 'dodge', 'jeep', 'ram', 'fiat', 'cdjr', 'fca']):
            what_items.extend([
                "",
                "**🏁 Stellantis Specific:**",
                "- Added FCA Direction Row Styles",
                "- Added FCA Cookie Banner styles"
            ])
        
        what_section = "\n".join(what_items)
        
        # Build full PR body with enhanced sections
        body = f"""## What

{what_section}

## Why

Site Builder Migration with enhanced tracking of automated vs manual work.

"""
        
        # Add detailed breakdown section
        if user_review_result and user_review_result.get("changes_analysis", {}).get("has_manual_changes"):
            body += """## Development Notes

This migration includes both automated and manual work:

### 🤖 Automated Migration
The SBM tool successfully migrated legacy styles to Site Builder format with pattern matching and transformation rules.

### 👤 Manual Refinements  
Developer made additional improvements to optimize the migration for this specific dealer's needs. These manual changes will be analyzed to improve future automation.

"""
        else:
            body += """## Development Notes

This migration was completed entirely through automation - no manual changes were required! This indicates the SBM tool is working optimally for this type of theme.

"""
        
        body += f"""## Instructions for Reviewers

Within the di-websites-platform directory:

```bash
git checkout main
git pull
git checkout {branch}
just start {slug}
```

- Review all code found in "Files Changed"
- Open up a browser, go to localhost
- Verify that homepage and interior pages load properly
- Request changes as needed"""
        
        return {
            'title': title,
            'body': body,  
            'what_section': what_section
        }
    
    def create_pr(self, slug: str, branch_name: str, draft: bool = False) -> Dict[str, Any]:
        """Create a GitHub pull request using enhanced PR creation logic."""
        try:
            # Check if we're in a Git repository
            if not self._is_git_repo():
                raise Exception("Not in a Git repository")
            
            # Check GitHub CLI availability and auth
            if not self._check_gh_cli():
                raise Exception("GitHub CLI not available or not authenticated")
            
            # Get repository info
            repo_info = self._get_repo_info()
            current_branch = repo_info.get('current_branch', branch_name)
            
            # Build PR content for SBM using Stellantis template
            pr_content = self._build_stellantis_pr_content(slug, current_branch, repo_info)
            
            # Create the PR
            pr_url = self._execute_gh_pr_create(
                title=pr_content['title'],
                body=pr_content['body'],
                base=self.config.git.default_branch,
                head=current_branch,
                draft=draft,
                reviewers=self.config.git.default_reviewers,
                labels=self.config.git.default_labels
            )
            
            # Open the PR in browser after creation
            self._open_pr_in_browser(pr_url)
            
            # Copy Salesforce message to clipboard
            self._copy_salesforce_message_to_clipboard(pr_content['what_section'], pr_url)
            
            return {
                "success": True,
                "pr_url": pr_url,
                "branch": current_branch,
                "title": pr_content['title']
            }
            
        except Exception as e:
            error_str = str(e)
            self.logger.error(f"PR creation failed: {error_str}")
            
            # Check if it's an "already exists" error and handle gracefully
            if "already exists" in error_str:
                # Try to extract PR URL from error message
                import re
                url_match = re.search(r'(https://github\.com/[^\s]+)', error_str)
                if url_match:
                    existing_pr_url = url_match.group(1)
                    self.logger.info(f"PR already exists: {existing_pr_url}")
                    
                    # Still copy Salesforce message since migration completed
                    pr_content = self._build_stellantis_pr_content(slug, branch_name, {})
                    self._copy_salesforce_message_to_clipboard(pr_content['what_section'], existing_pr_url)
                    
                    return {
                        "success": True,  # Mark as success since PR exists
                        "pr_url": existing_pr_url,
                        "branch": branch_name,
                        "title": pr_content['title'],
                        "existing": True
                    }
            
            return {
                "success": False,
                "error": error_str
            }
    
    def _is_git_repo(self) -> bool:
        """Check if current directory is a Git repository."""
        try:
            subprocess.run(['git', 'rev-parse', '--is-inside-work-tree'], 
                         check=True, capture_output=True, cwd=self.config.di_platform_dir)
            return True
        except subprocess.CalledProcessError:
            return False
    
    def _check_gh_cli(self) -> bool:
        """Check if GitHub CLI is available and authenticated."""
        try:
            # Check if gh is installed
            subprocess.run(['gh', '--version'], check=True, capture_output=True)
            # Check if authenticated
            subprocess.run(['gh', 'auth', 'status'], check=True, capture_output=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def _get_repo_info(self) -> Dict[str, str]:
        """Get repository information."""
        try:
            # Get current branch
            current_branch = subprocess.check_output(
                ['git', 'branch', '--show-current'], text=True, cwd=self.config.di_platform_dir
            ).strip()
            
            # Get repository name
            repo_root = subprocess.check_output(
                ['git', 'rev-parse', '--show-toplevel'], text=True, cwd=self.config.di_platform_dir
            ).strip()
            repo_name = os.path.basename(repo_root)
            
            return {
                'current_branch': current_branch,
                'repo_name': repo_name,
                'repo_root': repo_root
            }
        except subprocess.CalledProcessError as e:
            raise Exception(f"Failed to get repository info: {e}")
    
    def _build_stellantis_pr_content(self, slug: str, branch: str, repo_info: Dict[str, str]) -> Dict[str, str]:
        """Build PR content using Stellantis template with dynamic What section based on actual Git changes."""
        title = f"{slug} - SBM FE Audit"
        
        # Get actual changes from Git diff
        what_items = self._analyze_migration_changes()
        
        # Add FCA-specific items for Stellantis brands (only if files were actually changed)
        if what_items and any(brand in slug.lower() for brand in ['chrysler', 'dodge', 'jeep', 'ram', 'fiat', 'cdjr', 'fca']):
            what_items.extend([
                "- Added FCA Direction Row Styles",
                "- Added FCA Cookie Banner styles"
            ])
        
        # Fallback if no changes detected
        if not what_items:
            what_items = ["- Migrated interior page styles from inside.scss and style.scss to sb-inside.scss"]
        
        what_section = "\n".join(what_items)
        
        # Use the Stellantis template format
        body = f"""## What

{what_section}

## Why

Site Builder Migration

## Instructions for Reviewers

Within the di-websites-platform directory:

```bash
git checkout main
git pull
git checkout {branch}
just start {slug}
```

- Review all code found in "Files Changed"
- Open up a browser, go to localhost
- Verify that homepage and interior pages load properly
- Request changes as needed"""
        
        return {
            'title': title,
            'body': body,
            'what_section': what_section
        }
    
    def _analyze_migration_changes(self) -> List[str]:
        """Analyze Git changes to determine what was actually migrated."""
        what_items = []
        
        try:
            # Get the diff between current branch and main
            result = subprocess.run(
                ['git', 'diff', '--name-status', 'main...HEAD'],
                capture_output=True, text=True, check=True,
                cwd=self.config.di_platform_dir
            )
            
            changed_files = result.stdout.strip().split('\n') if result.stdout.strip() else []
            
            # Parse the git diff output (format: "A\tfilename" or "M\tfilename")
            added_files = []
            modified_files = []
            
            for line in changed_files:
                if not line.strip():
                    continue
                parts = line.split('\t', 1)
                if len(parts) == 2:
                    status, filepath = parts
                    if status == 'A':
                        added_files.append(filepath)
                    elif status == 'M':
                        modified_files.append(filepath)
            
            # Analyze what was actually migrated based on file changes
            # Filter for SCSS files and extract just the filename for easier matching
            css_files = []
            for f in added_files + modified_files:
                if f.endswith('.scss') and ('css/' in f or f.endswith('.scss')):
                    # Extract just the filename for easier matching
                    filename = os.path.basename(f)
                    css_files.append(filename)
            
            self.logger.debug(f"Found changed SCSS files: {css_files}")
            
            # Check for sb-inside.scss creation/modification
            if 'sb-inside.scss' in css_files:
                # Check what source files exist to be more specific
                source_files = []
                current_dir = Path.cwd()
                if (current_dir / "css" / "inside.scss").exists():
                    source_files.append("inside.scss")
                if (current_dir / "css" / "style.scss").exists():
                    source_files.append("style.scss")
                
                if source_files:
                    source_text = " and ".join(source_files)
                    what_items.append(f"- Migrated interior page styles from {source_text} to sb-inside.scss")
                else:
                    what_items.append("- Created sb-inside.scss for interior page styles")
            
            # Check for VRP migration
            if 'sb-vrp.scss' in css_files:
                if (Path.cwd() / "css" / "vrp.scss").exists():
                    what_items.append("- Migrated VRP styles from vrp.scss to sb-vrp.scss")
                else:
                    what_items.append("- Created sb-vrp.scss for VRP styles")
            
            # Check for VDP migration
            if 'sb-vdp.scss' in css_files:
                if (Path.cwd() / "css" / "vdp.scss").exists():
                    what_items.append("- Migrated VDP styles from vdp.scss to sb-vdp.scss")
                else:
                    what_items.append("- Created sb-vdp.scss for VDP styles")
            
            # Check for LVRP/LVDP migration
            lvrp_changed = 'sb-lvrp.scss' in css_files
            lvdp_changed = 'sb-lvdp.scss' in css_files
            
            if lvrp_changed or lvdp_changed:
                source_files = []
                if (Path.cwd() / "css" / "lvrp.scss").exists():
                    source_files.append("lvrp.scss")
                if (Path.cwd() / "css" / "lvdp.scss").exists():
                    source_files.append("lvdp.scss")
                
                if source_files:
                    source_text = " and ".join(source_files)
                    what_items.append(f"- Migrated LVRP/LVDP styles from {source_text} to sb-lvrp.scss and sb-lvdp.scss")
                else:
                    what_items.append("- Created sb-lvrp.scss and sb-lvdp.scss for LVRP/LVDP styles")
            
            # Check for home page migration
            if 'sb-home.scss' in css_files:
                if (Path.cwd() / "css" / "home.scss").exists():
                    what_items.append("- Migrated home page styles from home.scss to sb-home.scss")
                else:
                    what_items.append("- Created sb-home.scss for home page styles")
            
            self.logger.debug(f"Analyzed {len(css_files)} CSS file changes, generated {len(what_items)} what items")
            
        except subprocess.CalledProcessError as e:
            self.logger.warning(f"Could not analyze Git changes: {e}")
        except Exception as e:
            self.logger.warning(f"Error analyzing migration changes: {e}")
        
        return what_items
    
    def _execute_gh_pr_create(self, title: str, body: str, base: str, head: str, 
                            draft: bool, reviewers: List[str], labels: List[str]) -> str:
        """Execute GitHub CLI PR creation command."""
        cmd = [
            'gh', 'pr', 'create',
            '--title', title,
            '--body', body,
            '--base', base,
            '--head', head
        ]
        
        if draft:
            cmd.append('--draft')
        
        if reviewers:
            cmd.extend(['--reviewer', ','.join(reviewers)])
        
        if labels:
            cmd.extend(['--label', ','.join(labels)])
        
        try:
            # Run the command in the di_platform_dir to ensure correct repository context
            result = subprocess.run(cmd, check=True, capture_output=True, text=True, 
                                  cwd=self.config.di_platform_dir)
            # gh pr create returns the PR URL
            pr_url = result.stdout.strip()
            return pr_url
        except subprocess.CalledProcessError as e:
            # Check if this is a "PR already exists" error rather than a real failure
            error_output = e.stderr if e.stderr else str(e)
            
            # Look for indicators that PR already exists
            if any(indicator in error_output.lower() for indicator in [
                'already exists', 'pull request for branch', 'into branch'
            ]):
                # Try to extract the existing PR URL from the error message
                import re
                url_pattern = r'(https://github\.com/[^\s\n]+)'
                url_match = re.search(url_pattern, error_output)
                
                if url_match:
                    existing_pr_url = url_match.group(1)
                    self.logger.info(f"✅ PR already exists at: {existing_pr_url}")
                    return existing_pr_url
                else:
                    # If we can't extract URL, try to get it via gh pr list
                    try:
                        list_result = subprocess.run([
                            'gh', 'pr', 'list', '--head', head, '--json', 'url'
                        ], capture_output=True, text=True, check=True,
                        cwd=self.config.di_platform_dir)
                        
                        import json
                        pr_data = json.loads(list_result.stdout)
                        if pr_data and len(pr_data) > 0:
                            existing_pr_url = pr_data[0]['url']
                            self.logger.info(f"✅ Found existing PR at: {existing_pr_url}")
                            return existing_pr_url
                    except:
                        pass  # Fall through to raise original error
            
            # If it's not a "PR already exists" case, raise the original error
            raise Exception(f"GitHub CLI error: {error_output}")
    
    def _open_pr_in_browser(self, pr_url: str) -> None:
        """Open the PR in the default browser."""
        try:
            import webbrowser
            webbrowser.open(pr_url)
            self.logger.info(f"Opened PR in browser: {pr_url}")
        except Exception as e:
            self.logger.warning(f"Could not open PR in browser: {e}")
    
    def _copy_salesforce_message_to_clipboard(self, what_section: str, pr_url: str) -> None:
        """Copy Salesforce update message to clipboard."""
        try:
            # Format the Salesforce message
            salesforce_message = f"""FED Site Builder Migration Complete
Notes:
{what_section}
Pull Request Link: {pr_url}"""
            
            # Copy to clipboard using pbcopy on macOS
            import subprocess
            process = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
            process.communicate(salesforce_message.encode('utf-8'))
            
            self.logger.info("📋 Salesforce message copied to clipboard")
            
        except Exception as e:
            self.logger.warning(f"Could not copy Salesforce message to clipboard: {e}")
    
    def push_branch(self, branch_name: str) -> bool:
        """Push branch to origin."""
        try:
            subprocess.run(['git', 'push', 'origin', branch_name], 
                         check=True, capture_output=True, cwd=self.config.di_platform_dir)
            self.logger.success(f"✅ Pushed branch: {branch_name}")
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to push branch {branch_name}: {e}")
            return False
    
    def check_repository_status(self) -> bool:
        """Check if repository is ready for operations."""
        try:
            # Check if we're in a git repo
            if not self._is_git_repo():
                return False
            
            # Check for uncommitted changes
            result = subprocess.run(['git', 'status', '--porcelain'], 
                                  capture_output=True, text=True, cwd=self.config.di_platform_dir)
            has_changes = bool(result.stdout.strip())
            
            return not has_changes
        except:
            return False 
