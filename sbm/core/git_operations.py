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
        
        just_start_cmd = f"just start {slug} prod" if use_prod_db else f"just start {slug}"
        self.logger.step(f"Monitoring '{just_start_cmd}' process...")
        self.logger.warning("⚠️  Looking for existing 'just start' process...")
        self.logger.warning(f"⚠️  Make sure you've already run '{just_start_cmd}' in another terminal")
        
        try:
            # Look for existing just start process
            just_start_process = None
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = proc.info['cmdline']
                    if cmdline and 'just' in cmdline and 'start' in cmdline and slug in cmdline:
                        just_start_process = proc
                        self.logger.info(f"Found existing 'just start {slug}' process (PID: {proc.pid})")
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            if not just_start_process:
                self.logger.warning("No existing 'just start' process found. Starting new one...")
                # Fall back to starting the process ourselves
                cmd = ['just', 'start', slug]
                if use_prod_db:
                    cmd.append('prod')
                process = subprocess.Popen(
                    cmd,
                    cwd=self.config.di_platform_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,  # Merge stderr into stdout
                    text=True,
                    bufsize=1,  # Line buffered
                    universal_newlines=True
                )
            else:
                # Monitor the existing process by tailing Docker logs
                self.logger.info("Monitoring existing process via Docker logs...")
                # First check if the container exists, if not wait for it
                container_name = f'di-websites-platform-{slug}-1'
                
                # Wait for container to be created (up to 60 seconds)
                container_exists = False
                for i in range(60):
                    try:
                        result = subprocess.run(['docker', 'inspect', container_name], 
                                              capture_output=True, check=True)
                        container_exists = True
                        break
                    except subprocess.CalledProcessError:
                        time.sleep(1)
                
                if not container_exists:
                    self.logger.warning(f"Container {container_name} not found after 60 seconds, falling back to starting new process...")
                    cmd = ['just', 'start', slug]
                    if use_prod_db:
                        cmd.append('prod')
                    process = subprocess.Popen(
                        cmd,
                        cwd=self.config.di_platform_dir,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        bufsize=1,
                        universal_newlines=True
                    )
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
            start_time = time.time()
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
            try:
                # Check if branch exists locally
                result = subprocess.run(['git', 'show-ref', '--verify', '--quiet', f'refs/heads/{branch_name}'], 
                                      capture_output=True)
                if result.returncode == 0:
                    # Branch exists, switch to it
                    self.logger.info(f"Branch {branch_name} already exists, switching to it...")
                    subprocess.run(['git', 'checkout', branch_name], check=True, capture_output=True)
                else:
                    # Branch doesn't exist, create it
                    self.logger.info(f"Creating new branch: {branch_name}")
                    subprocess.run(['git', 'checkout', '-b', branch_name], check=True, capture_output=True)
            except subprocess.CalledProcessError:
                # If there's any issue, try creating with a unique suffix
                import time
                unique_suffix = int(time.time()) % 10000
                branch_name = f"{slug}-sbm{date_suffix}-{unique_suffix}"
                self.logger.info(f"Creating unique branch: {branch_name}")
                subprocess.run(['git', 'checkout', '-b', branch_name], check=True, capture_output=True)
            
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
            # Check if we're in a git repository
            if not self._is_git_repo():
                error_msg = "Not in a git repository"
                self.logger.error(error_msg)
                return {"committed": False, "error": error_msg}
            
            # Add files to staging area
            if files:
                for file_path in files:
                    # Check if file exists before trying to add it
                    if not os.path.exists(file_path):
                        error_msg = f"File does not exist: {file_path}"
                        self.logger.error(error_msg)
                        return {"committed": False, "error": error_msg}
                    
                    try:
                        result = subprocess.run(['git', 'add', file_path], 
                                              check=True, capture_output=True, text=True, cwd=self.config.di_platform_dir)
                        self.logger.debug(f"Added {file_path} to staging area")
                    except subprocess.CalledProcessError as e:
                        error_msg = f"Failed to add {file_path} to git: {e}"
                        if e.stderr:
                            error_msg += f" - {e.stderr.strip()}"
                        self.logger.error(error_msg)
                        return {"committed": False, "error": error_msg}
            else:
                # Add all changes if no specific files provided
                try:
                    subprocess.run(['git', 'add', '.'], 
                                 check=True, capture_output=True, text=True)
                    self.logger.debug("Added all changes to staging area")
                except subprocess.CalledProcessError as e:
                    error_msg = f"Failed to add changes to git: {e}"
                    if e.stderr:
                        error_msg += f" - {e.stderr.strip()}"
                    self.logger.error(error_msg)
                    return {"committed": False, "error": error_msg}
            
            # Check if there are any changes to commit
            status_result = subprocess.run(['git', 'status', '--porcelain'], 
                                         capture_output=True, text=True, check=True)
            if not status_result.stdout.strip():
                self.logger.info("No changes to commit")
                return {"committed": False, "message": "No changes to commit"}
            
            # Commit the changes
            try:
                commit_result = subprocess.run(['git', 'commit', '-m', message], 
                                             check=True, capture_output=True, text=True)
                self.logger.success(f"✅ Committed changes: {message}")
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
                return {"committed": False, "error": error_msg}
            
        except subprocess.CalledProcessError as e:
            error_msg = f"Git operation failed: {e}"
            if hasattr(e, 'stderr') and e.stderr:
                error_msg += f" - {e.stderr.strip()}"
            self.logger.error(error_msg)
            return {"committed": False, "error": error_msg}
        except Exception as e:
            error_msg = f"Unexpected error during commit: {e}"
            self.logger.error(error_msg)
            return {"committed": False, "error": error_msg}

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
                         check=True, capture_output=True)
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
                ['git', 'branch', '--show-current'], text=True
            ).strip()
            
            # Get repository name
            repo_root = subprocess.check_output(
                ['git', 'rev-parse', '--show-toplevel'], text=True
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
                capture_output=True, text=True, check=True
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
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            # gh pr create returns the PR URL
            pr_url = result.stdout.strip()
            return pr_url
        except subprocess.CalledProcessError as e:
            raise Exception(f"GitHub CLI error: {e.stderr}")
    
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
        """Push branch to remote repository."""
        try:
            subprocess.run(['git', 'push', '-u', 'origin', branch_name], 
                         check=True, capture_output=True)
            self.logger.info(f"Pushed branch {branch_name} to origin")
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to push branch: {e}")
            return False
    
    def check_repository_status(self) -> bool:
        """Check if repository is in a clean state."""
        try:
            # Check if there are uncommitted changes
            result = subprocess.run(['git', 'status', '--porcelain'], 
                                  capture_output=True, text=True)
            return len(result.stdout.strip()) == 0
        except subprocess.CalledProcessError:
            return False 
