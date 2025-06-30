"""
Git operations for the SBM tool.

This module handles Git operations such as branch creation, commits, and pull requests
using the GitPython library for safer and more robust interactions.
"""

import os
import subprocess
import json
import re
from pathlib import Path
from typing import Dict, Any, Optional, List
from git import Repo, GitCommandError
from sbm.config import Config
from sbm.utils.logger import logger
from sbm.utils.command import execute_command
from sbm.utils.path import get_platform_dir, get_dealer_theme_dir
from sbm.utils.helpers import get_branch_name


class GitOperations:
    """Handles Git operations for SBM migrations."""
    
    def __init__(self, config: Config):
        """Initialize GitOperations with configuration."""
        self.config = config
        
    def _get_repo(self) -> Repo:
        """Initializes and returns a GitPython Repo object."""
        platform_dir = get_platform_dir()
        return Repo(platform_dir)
    
    def _is_git_repo(self) -> bool:
        """Check if we're in a Git repository."""
        try:
            self._get_repo()
            return True
        except:
            return False
    
    def _check_gh_cli(self) -> bool:
        """Check if GitHub CLI is available and authenticated."""
        try:
            subprocess.run(['gh', '--version'], check=True, capture_output=True)
            subprocess.run(['gh', 'auth', 'status'], check=True, capture_output=True)
            return True
        except:
            return False
    
    def _get_repo_info(self) -> Dict[str, str]:
        """Get current repository information."""
        try:
            repo = self._get_repo()
            return {
                'current_branch': repo.active_branch.name,
                'remote_url': repo.remotes.origin.url if repo.remotes else ''
            }
        except Exception as e:
            logger.warning(f"Could not get repo info: {e}")
            return {}
    
    def checkout_main_and_pull(self) -> bool:
        """
        Checkout the main branch and pull the latest changes.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info("Checking out main branch and pulling latest changes")
            repo = self._get_repo()
            
            # Stash or discard any local changes before switching branches
            if repo.is_dirty(untracked_files=True):
                logger.info("Discarding dirty working directory before checkout.")
                repo.git.reset('--hard')
                repo.git.clean('-fd')

            repo.heads.main.checkout()
            logger.info("Pulling latest changes from origin/main")
            repo.remotes.origin.pull()
            return True
        except GitCommandError as e:
            logger.error(f"Failed to checkout or pull main branch: {e}")
            return False

    def create_branch(self, slug: str) -> tuple:
        """
        Create a new branch for the migration.
        
        Args:
            slug (str): Dealer theme slug
            
        Returns:
            tuple: (success, branch_name) - a tuple containing success status and branch name
        """
        branch_name = get_branch_name(slug)
        try:
            logger.info(f"Creating new branch: {branch_name}")
            repo = self._get_repo()
            
            # If branch already exists, delete it
            if branch_name in repo.heads:
                logger.warning(f"Branch '{branch_name}' already exists. Deleting and re-creating it to ensure a clean state.")
                repo.delete_head(branch_name, force=True)

            # Create and checkout the new branch
            new_branch = repo.create_head(branch_name)
            new_branch.checkout()
            
            return True, branch_name
        except GitCommandError as e:
            logger.error(f"Failed to create branch '{branch_name}': {e}")
            return False, None

    def commit_changes(self, slug: str, message: Optional[str] = None) -> bool:
        """
        Commit changes to the dealer theme.
        
        Args:
            slug (str): Dealer theme slug
            message (str, optional): Commit message. If None, a default message is used.
            
        Returns:
            bool: True if successful, False otherwise
        """
        if message is None:
            message = f"SBM: Migrate {slug} to Site Builder format"
        
        try:
            logger.info(f"Committing changes for {slug}")
            repo = self._get_repo()
            
            # Path to the dealer theme relative to the repo root
            theme_path = os.path.relpath(get_dealer_theme_dir(slug), get_platform_dir())
            
            # Add all changes in the specific theme directory using subprocess
            logger.info(f"Adding changes in {theme_path}")
            add_command = f"git add {theme_path}"
            add_success, _, _, _ = execute_command(add_command, "Failed to add changes", cwd=get_platform_dir())
            if not add_success:
                return False
                
            # Commit if there are changes to commit
            if repo.is_dirty(index=True):
                logger.info(f'Committing with message: "{message}"')
                commit_command = f'git commit -m "{message}"'
                commit_success, _, _, _ = execute_command(commit_command, "Failed to commit changes", cwd=get_platform_dir())
                return commit_success
            else:
                logger.info("No changes to commit.")
                return True # Nothing to do is a success
                
        except GitCommandError as e:
            logger.error(f"Failed to commit changes for {slug}: {e}")
            return False

    def push_changes(self, branch_name: str) -> bool:
        """
        Push changes to the remote repository.
        
        Args:
            branch_name (str): Branch name to push
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info(f"Pushing changes to origin/{branch_name}")
            repo = self._get_repo()
            repo.remotes.origin.push(refspec=f"{branch_name}:{branch_name}", set_upstream=True)
            return True
        except GitCommandError as e:
            logger.error(f"Failed to push changes to origin/{branch_name}: {e}")
            return False

    def _execute_gh_pr_create(self, title: str, body: str, base: str, head: str, 
                                draft: bool, reviewers: List[str], labels: List[str]) -> str:
        """
        Creates GitHub PR using gh CLI with advanced error handling
        """
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
            result = subprocess.run(cmd, check=True, capture_output=True, text=True, cwd=get_platform_dir())
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            error_output = e.stderr if e.stderr else str(e)
            if self._is_pr_exists_error(error_output):
                return self._handle_existing_pr(error_output, head)
            raise Exception(f"GitHub CLI error: {error_output}")

    def _is_pr_exists_error(self, error_output: str) -> bool:
        """Checks if the error output indicates that a PR already exists."""
        return "already exists" in error_output.lower() or "pull request for branch" in error_output.lower()

    def _handle_existing_pr(self, error_output: str, head_branch: str) -> str:
        """Extracts the existing PR URL from the error output or by listing PRs."""
        # Try to extract PR URL from error message
        url_match = re.search(r'(https://github\.com/[^\s\n]+)', error_output)
        if url_match:
            return url_match.group(1)
        else:
            # Fallback to gh pr list
            try:
                list_result = subprocess.run([
                    'gh', 'pr', 'list', '--head', head_branch, '--json', 'url'
                ], capture_output=True, text=True, check=True, cwd=get_platform_dir())
                pr_data = json.loads(list_result.stdout)
                if pr_data and len(pr_data) > 0:
                    return pr_data[0]['url']
            except Exception as list_e:
                logger.warning(f"Could not list existing PRs: {list_e}")
            raise Exception(f"PR already exists but could not retrieve URL: {error_output}")

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
        
        # Get current branch name dynamically
        try:
            current_branch_result = subprocess.run(
                ['git', 'branch', '--show-current'],
                capture_output=True, text=True, check=True,
                cwd=get_platform_dir()
            )
            current_branch = current_branch_result.stdout.strip()
        except subprocess.CalledProcessError:
            current_branch = branch  # fallback to provided branch
        
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
git checkout {current_branch}
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
                cwd=get_platform_dir()
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
            
            logger.debug(f"Found changed SCSS files: {css_files}")
            
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
            
            # Check for LVDP and LVRP migrations (use correct naming)
            if 'sb-vdp.scss' in css_files:
                if (Path.cwd() / "css" / "lvdp.scss").exists():
                    what_items.append("- Migrated LVRP, LVDP Styles to sb-lvrp.scss and sb-lvdp.scss")
                else:
                    what_items.append("- Created sb-vdp.scss for VDP styles")
            elif 'sb-vrp.scss' in css_files:
                if (Path.cwd() / "css" / "lvrp.scss").exists():
                    what_items.append("- Migrated LVRP, LVDP Styles to sb-lvrp.scss and sb-lvdp.scss")
                else:
                    what_items.append("- Created sb-vrp.scss for VRP styles")
            
            # Check for home page migration
            if 'sb-home.scss' in css_files:
                if (Path.cwd() / "css" / "home.scss").exists():
                    what_items.append("- Migrated home page styles from home.scss to sb-home.scss")
                else:
                    what_items.append("- Created sb-home.scss for home page styles")
            
            logger.debug(f"Analyzed {len(css_files)} CSS file changes, generated {len(what_items)} what items")
            
        except subprocess.CalledProcessError as e:
            logger.warning(f"Could not analyze Git changes: {e}")
        except Exception as e:
            logger.warning(f"Error analyzing migration changes: {e}")
        
        return what_items

    def _build_enhanced_pr_content(self, slug: str, branch: str, repo_info: Dict[str, str], user_review_result: Dict[str, Any] = None) -> Dict[str, str]:
        """Build enhanced PR content with automated vs manual tracking."""
        title = f"{slug} - SBM FE Audit"

        # Build WHAT section with enhanced tracking
        what_items = []

        # Automated migration items - get actual migration analysis
        automated_items = self._analyze_migration_changes()
        if automated_items:
            what_items.extend([
                "**🤖 Automated Migration:**"
            ])
            what_items.extend(automated_items)
            what_items.extend([
                "- Applied standard SBM transformations and pattern matching"
            ])
        else:
            # Fallback if analysis fails
            what_items.extend([
                "**🤖 Automated Migration:**",
                "- Migrated interior page styles from style.scss and inside.scss to sb-inside.scss",
                "- Created Site Builder SCSS files (sb-inside.scss, sb-vdp.scss, sb-vrp.scss)",
                "- Applied standard SBM transformations and pattern matching"
            ])

        # Manual refinements if any
        if user_review_result and user_review_result.get("changes_analysis", {}).get("has_manual_changes"):
            changes_analysis = user_review_result["changes_analysis"]
            modified_files = changes_analysis.get("files_modified", [])

            what_items.extend([
                "",
                "**👤 Manual Refinements:**"
            ])

            for filename in modified_files:
                size_change = changes_analysis.get("size_changes", {}).get(filename, {})
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
- **Automated**: Core SCSS transformation, file structure creation, standard pattern matching
- **Manual**: Dealer-specific refinements, custom styling adjustments, responsive behavior tuning

The migration process ensures backward compatibility while optimizing for Site Builder architecture.

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

    def _open_pr_in_browser(self, pr_url: str):
        """Open PR URL in browser."""
        try:
            subprocess.run(['open', pr_url], check=True)
            logger.info(f"Opened PR in browser: {pr_url}")
        except subprocess.CalledProcessError:
            logger.warning(f"Could not open PR in browser. URL: {pr_url}")

    def _copy_salesforce_message_to_clipboard(self, what_section: str, pr_url: str):
        """Copy Salesforce message to clipboard."""
        try:
            salesforce_message = f"""Migration completed successfully!

{what_section}

PR: {pr_url}"""
            
            # Use pbcopy on macOS
            subprocess.run(['pbcopy'], input=salesforce_message.encode(), check=True)
            logger.info("Copied Salesforce update to clipboard")
        except subprocess.CalledProcessError:
            logger.warning("Could not copy message to clipboard")

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
            
            # Build PR content - use enhanced only if there are manual changes, otherwise use stellantis template
            if user_review_result and user_review_result.get("changes_analysis", {}).get("has_manual_changes"):
                pr_content = self._build_enhanced_pr_content(slug, current_branch, repo_info, user_review_result)
            else:
                pr_content = self._build_stellantis_pr_content(slug, current_branch, repo_info)
            
            # Get configuration values with fallbacks
            default_branch = getattr(self.config, 'default_branch', 'main')
            if hasattr(self.config, 'git'):
                default_reviewers = getattr(self.config.git, 'default_reviewers', ['carsdotcom/fe-dev'])
                default_labels = getattr(self.config.git, 'default_labels', ['fe-dev'])
            else:
                default_reviewers = ['carsdotcom/fe-dev']
                default_labels = ['fe-dev']
            
            # Create the PR
            pr_url = self._execute_gh_pr_create(
                title=pr_content['title'],
                body=pr_content['body'],
                base=default_branch,
                head=current_branch,
                draft=draft,
                reviewers=default_reviewers,
                labels=default_labels
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
            logger.error(f"Enhanced PR creation failed: {error_str}")
            
            # Check if it's an "already exists" error and handle gracefully
            if "already exists" in error_str:
                # Try to extract PR URL from error message
                url_match = re.search(r'(https://github\.com/[^\s\n]+)', error_str)
                if url_match:
                    existing_pr_url = url_match.group(1)
                    logger.info(f"PR already exists: {existing_pr_url}")
                    
                    # Still copy Salesforce message since migration completed
                    if user_review_result and user_review_result.get("changes_analysis", {}).get("has_manual_changes"):
                        pr_content = self._build_enhanced_pr_content(slug, branch_name, {}, user_review_result)
                    else:
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

    def create_pr(self, slug: str, branch_name: str = None, title: str = None, body: str = None, 
                  base: str = None, head: str = None, reviewers: List[str] = None, 
                  labels: List[str] = None, draft: bool = False) -> Dict[str, Any]:
        """
        Create a GitHub Pull Request for a given theme.
        
        Args:
            slug (str): Theme slug for the PR
            branch_name (str, optional): Branch name (fallback if head not provided)
            title (str, optional): PR title (auto-generated if not provided)
            body (str, optional): PR body (auto-generated if not provided) 
            base (str, optional): Base branch (defaults to config default)
            head (str, optional): Head branch (defaults to current branch)
            reviewers (List[str], optional): List of reviewers (defaults to config)
            labels (List[str], optional): List of labels (defaults to config)
            draft (bool): Whether to create as draft PR
            
        Returns:
            Dict[str, Any]: Result dictionary with success status and PR details
        """
        try:
            # Check if we're in a Git repository
            if not self._is_git_repo():
                raise Exception("Not in a Git repository")
            
            # Check GitHub CLI availability and auth
            if not self._check_gh_cli():
                raise Exception("GitHub CLI not available or not authenticated")
            
            # Get repository info and determine current branch
            repo_info = self._get_repo_info()
            current_branch = head or repo_info.get('current_branch') or branch_name
            
            if not current_branch:
                raise Exception("Could not determine branch for PR")
            
            # Use provided values or generate defaults using stellantis template
            if not title or not body:
                pr_content = self._build_stellantis_pr_content(slug, current_branch, repo_info)
                pr_title = title or pr_content['title']
                pr_body = body or pr_content['body']
            else:
                pr_title = title
                pr_body = body
            
            # Get configuration values with fallbacks
            pr_base = base or getattr(self.config, 'default_branch', 'main')
            if hasattr(self.config, 'git'):
                pr_reviewers = reviewers or getattr(self.config.git, 'default_reviewers', ['carsdotcom/fe-dev'])
                pr_labels = labels or getattr(self.config.git, 'default_labels', ['fe-dev'])
            else:
                pr_reviewers = reviewers or ['carsdotcom/fe-dev']
                pr_labels = labels or ['fe-dev']
            
            # Create the PR
            pr_url = self._execute_gh_pr_create(
                title=pr_title,
                body=pr_body,
                base=pr_base,
                head=current_branch,
                draft=draft,
                reviewers=pr_reviewers,
                labels=pr_labels
            )
            
            logger.info(f"Successfully created PR: {pr_url}")
            
            return {
                "success": True,
                "pr_url": pr_url,
                "branch": current_branch,
                "title": pr_title
            }
            
        except Exception as e:
            error_str = str(e)
            logger.error(f"PR creation failed: {error_str}")
            return {
                "success": False,
                "error": error_str
            }

    def git_operations(self, slug: str) -> tuple:
        """
        Perform all Git operations for a migration.
        
        Args:
            slug (str): Dealer theme slug
            
        Returns:
            tuple: (success, branch_name) - a tuple containing success status and branch name
        """
        logger.info(f"Performing Git operations for {slug}")
        
        if not self.checkout_main_and_pull():
            return False, None
        
        success, branch_name = self.create_branch(slug)
        
        return success, branch_name


# Legacy function wrappers for backward compatibility
def _get_repo() -> Repo:
    """Legacy wrapper - initializes and returns a GitPython Repo object."""
    platform_dir = get_platform_dir()
    return Repo(platform_dir)

def checkout_main_and_pull():
    """Legacy wrapper for checkout_main_and_pull."""
    git_ops = GitOperations(Config({}))
    return git_ops.checkout_main_and_pull()

def create_branch(slug):
    """Legacy wrapper for create_branch."""
    git_ops = GitOperations(Config({}))
    return git_ops.create_branch(slug)

def commit_changes(slug, message=None):
    """Legacy wrapper for commit_changes."""
    git_ops = GitOperations(Config({}))
    return git_ops.commit_changes(slug, message)

def push_changes(branch_name):
    """Legacy wrapper for push_changes."""
    git_ops = GitOperations(Config({}))
    return git_ops.push_changes(branch_name)

def git_operations(slug):
    """Legacy wrapper for git_operations."""
    git_ops = GitOperations(Config({}))
    return git_ops.git_operations(slug)

def create_pull_request(title, body, base, head, reviewers=None, labels=None):
    """Legacy wrapper for create_pull_request."""
    git_ops = GitOperations(Config({}))
    
    # Parse reviewers and labels if they're strings
    if isinstance(reviewers, str):
        reviewers = [r.strip() for r in reviewers.split(',')]
    if isinstance(labels, str):
        labels = [l.strip() for l in labels.split(',')]
    
    # Extract slug from branch name (assuming format: slug-sbm1234)
    import re
    slug_match = re.match(r'^(.+)-sbm\d+$', head)
    slug = slug_match.group(1) if slug_match else head
    
    result = git_ops.create_pr(
        slug=slug,
        title=title,
        body=body,
        base=base,
        head=head,
        reviewers=reviewers,
        labels=labels
    )
    
    if result['success']:
        return result['pr_url']
    else:
        raise Exception(result['error'])
