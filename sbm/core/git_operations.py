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


class GitOperations:
    """Handles Git operations for migration."""
    
    def __init__(self, config: Config):
        """Initialize Git operations."""
        self.config = config
        self.logger = get_logger("git")
    
    def monitor_just_start(self, slug: str) -> Dict[str, Any]:
        """Monitor the 'just start' process and wait for completion."""
        import time
        
        self.logger.step(f"Starting 'just start {slug}' process...")
        
        try:
            # Start the just start process
            process = subprocess.Popen(
                ['just', 'start', slug],
                cwd=self.config.di_platform_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            self.logger.info(f"Started 'just start {slug}' (PID: {process.pid})")
            self.logger.warning("⚠️  Monitoring Docker container startup...")
            
            # Monitor the process
            start_time = time.time()
            timeout = 300  # 5 minutes timeout
            
            while process.poll() is None:
                elapsed = time.time() - start_time
                
                if elapsed > timeout:
                    self.logger.error("Timeout waiting for 'just start' to complete")
                    process.terminate()
                    return {
                        "success": False,
                        "error": "Timeout waiting for Docker container to start"
                    }
                
                # Check every 5 seconds
                time.sleep(5)
                self.logger.info(f"Still waiting... ({int(elapsed)}s elapsed)")
            
            # Process completed
            stdout, stderr = process.communicate()
            
            if process.returncode == 0:
                self.logger.success("Docker container started successfully!")
                self.logger.info("Ready to proceed with migration")
                return {
                    "success": True,
                    "message": "Docker container ready",
                    "duration": time.time() - start_time
                }
            else:
                self.logger.error(f"'just start' failed with return code {process.returncode}")
                if stderr:
                    self.logger.error(f"Error output: {stderr}")
                return {
                    "success": False,
                    "error": f"just start failed: {stderr or 'Unknown error'}"
                }
                
        except Exception as e:
            self.logger.error(f"Failed to start/monitor 'just start' process: {e}")
            return {
                "success": False,
                "error": str(e)
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
            
            # Check status
            status_result = subprocess.run(['git', 'status', '--porcelain'], 
                                         capture_output=True, text=True, check=True)
            if status_result.stdout.strip():
                self.logger.warning("Working directory has uncommitted changes")
            
            # Step 2: git pull (second pull as specified)
            self.logger.info("Second pull to ensure up-to-date...")
            subprocess.run(['git', 'pull'], check=True, capture_output=True)
            
            # Step 3: Create branch with correct naming
            import datetime
            date_suffix = datetime.datetime.now().strftime("%m%y")  # MMYY format
            branch_name = f"{slug}-SBM{date_suffix}"
            
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
                branch_name = f"{slug}-SBM{date_suffix}-{unique_suffix}"
                self.logger.info(f"Creating unique branch: {branch_name}")
                subprocess.run(['git', 'checkout', '-b', branch_name], check=True, capture_output=True)
            
            # Step 4: Add dealer to sparse checkout
            self.logger.info(f"Adding {slug} to sparse checkout...")
            subprocess.run(['git', 'sparse-checkout', 'add', f'dealer-themes/{slug}'], 
                         check=True, capture_output=True)
            
            self.logger.success("Pre-migration git setup completed")
            
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

    def create_branch(self, slug: str) -> str:
        """Create a migration branch."""
        import datetime
        date_suffix = datetime.datetime.now().strftime("%m%d")
        branch_name = f"{slug}-sbm{date_suffix}"
        self.logger.info(f"Creating branch: {branch_name}")
        return branch_name
    
    def commit_changes(self, message: str, files: Optional[List[str]] = None) -> Dict[str, Any]:
        """Commit changes to git repository."""
        try:
            # Add files to staging area
            if files:
                for file_path in files:
                    subprocess.run(['git', 'add', file_path], check=True, capture_output=True)
                    self.logger.debug(f"Added {file_path} to staging area")
            else:
                # Add all changes if no specific files provided
                subprocess.run(['git', 'add', '.'], check=True, capture_output=True)
                self.logger.debug("Added all changes to staging area")
            
            # Check if there are any changes to commit
            status_result = subprocess.run(['git', 'status', '--porcelain'], 
                                         capture_output=True, text=True, check=True)
            if not status_result.stdout.strip():
                self.logger.info("No changes to commit")
                return {"committed": False, "message": "No changes to commit"}
            
            # Commit the changes
            subprocess.run(['git', 'commit', '-m', message], check=True, capture_output=True)
            self.logger.info(f"Committed changes: {message}")
            
            return {"committed": True, "message": message}
            
        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to commit changes: {e}"
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
            self.logger.error(f"PR creation failed: {e}")
            return {
                "success": False,
                "error": str(e)
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
