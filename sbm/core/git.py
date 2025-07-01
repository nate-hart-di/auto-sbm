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
            
            # Add specific files in the theme directory, excluding snapshots
            logger.info(f"Adding changes in {theme_path}")
            
            # Add specific SCSS files instead of the entire directory to avoid snapshots
            scss_files = ['sb-inside.scss', 'sb-vdp.scss', 'sb-vrp.scss', 'sb-home.scss']
            files_added = False
            
            for scss_file in scss_files:
                file_path = os.path.join(theme_path, scss_file)
                if os.path.exists(os.path.join(get_platform_dir(), file_path)):
                    add_command = f"git add {file_path}"
                    add_success, _, _, _ = execute_command(add_command, f"Failed to add {scss_file}", cwd=get_platform_dir())
                    if add_success:
                        files_added = True
                    else:
                        logger.warning(f"Failed to add {scss_file}, continuing with other files")
            
            if not files_added:
                logger.warning("No SCSS files were added to git")
                return True  # Not necessarily a failure if no files to add
                
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
                if (current_dir / "css" / "style.scss").exists():
                    source_files.append("style.scss")
                if (current_dir / "css" / "inside.scss").exists():
                    source_files.append("inside.scss")
                
                if source_files:
                    source_text = " and ".join(source_files)
                    what_items.append(f"- Migrated interior page styles from {source_text} to sb-inside.scss")
                else:
                    what_items.append("- Created sb-inside.scss for interior page styles")
            
            # Check for VDP migration (only from lvdp.scss)
            if 'sb-vdp.scss' in css_files:
                if (Path.cwd() / "css" / "lvdp.scss").exists():
                    what_items.append("- Migrated VDP styles from lvdp.scss to sb-vdp.scss")
                else:
                    what_items.append("- Created sb-vdp.scss for VDP styles")
            
            # Check for VRP migration (only from lvrp.scss)
            if 'sb-vrp.scss' in css_files:
                if (Path.cwd() / "css" / "lvrp.scss").exists():
                    what_items.append("- Migrated VRP styles from lvrp.scss to sb-vrp.scss")
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

    def _detect_manual_changes(self) -> Dict[str, Any]:
        """
        Detect manual changes made during the review process by analyzing git commit history
        and diff content patterns that indicate manual refinements vs automated changes.
        """
        manual_changes = {
            'has_manual_changes': False,
            'change_types': [],
            'files_modified': [],
            'estimated_manual_lines': 0,
            'change_descriptions': []
        }
        
        try:
            # Get detailed diff content to analyze
            result = subprocess.run(
                ['git', 'diff', '--unified=3', 'main...HEAD'],
                capture_output=True, text=True, check=True,
                cwd=get_platform_dir()
            )
            
            diff_content = result.stdout
            if not diff_content.strip():
                return manual_changes
            
            # Patterns that suggest manual changes beyond automation
            manual_indicators = {
                'custom_comments': r'\+\s*\/\*.*(?:custom|manual|added|fix|tweak|adjust).*\*\/',
                'media_queries': r'\+.*@media.*\(',
                'pseudo_selectors': r'\+.*:(?:hover|focus|active|before|after)',
                'custom_classes': r'\+.*\.(?:custom|manual|fix|temp|override)-',
                'brand_specific': r'\+.*(?:brand-specific|dealer-custom)',
                'important_overrides': r'\+.*!important',
                'z_index_adjustments': r'\+.*z-index:\s*\d+',
                'position_fixes': r'\+.*position:\s*(?:absolute|relative|fixed)',
                'color_customizations': r'\+.*(?:color|background).*#[0-9a-fA-F]{3,6}',
                'spacing_tweaks': r'\+.*(?:margin|padding).*(?:\d+px|\d+rem|\d+em)'
            }
            
            lines = diff_content.split('\n')
            added_lines = [line for line in lines if line.startswith('+') and not line.startswith('+++')]
            
            # Analyze each added line for manual change indicators
            for line in added_lines:
                for change_type, pattern in manual_indicators.items():
                    if re.search(pattern, line, re.IGNORECASE):
                        if change_type not in manual_changes['change_types']:
                            manual_changes['change_types'].append(change_type)
                        manual_changes['has_manual_changes'] = True
            
            # Count estimated manual lines (heuristic)
            manual_changes['estimated_manual_lines'] = len([
                line for line in added_lines 
                if any(re.search(pattern, line, re.IGNORECASE) for pattern in manual_indicators.values())
            ])
            
            # Generate human-readable descriptions
            type_descriptions = {
                'custom_comments': 'Added explanatory comments for custom modifications',
                'media_queries': 'Enhanced responsive design with custom media queries',
                'pseudo_selectors': 'Improved interactive states (hover, focus, etc.)',
                'custom_classes': 'Created custom CSS classes for specific styling needs',
                'brand_specific': 'Implemented brand-specific customizations',
                'important_overrides': 'Added CSS !important overrides for specificity',
                'z_index_adjustments': 'Fixed layering issues with z-index adjustments',
                'position_fixes': 'Corrected element positioning',
                'color_customizations': 'Applied custom color schemes',
                'spacing_tweaks': 'Fine-tuned spacing and layout'
            }
            
            manual_changes['change_descriptions'] = [
                type_descriptions[change_type] for change_type in manual_changes['change_types']
                if change_type in type_descriptions
            ]
            
            # Get list of files that were manually modified
            file_result = subprocess.run(
                ['git', 'diff', '--name-only', 'main...HEAD'],
                capture_output=True, text=True, check=True,
                cwd=get_platform_dir()
            )
            
            manual_changes['files_modified'] = [
                os.path.basename(f) for f in file_result.stdout.strip().split('\n')
                if f.strip().endswith('.scss')
            ]
            
        except subprocess.CalledProcessError as e:
            logger.debug(f"Could not analyze manual changes: {e}")
        except Exception as e:
            logger.debug(f"Error detecting manual changes: {e}")
        
        return manual_changes

    def create_automation_snapshot(self, slug: str) -> bool:
        """
        Create a snapshot of the current state after automated migration but before manual review.
        This allows us to later detect what changes were made manually.
        """
        try:
            theme_dir = get_dealer_theme_dir(slug)
            snapshot_dir = os.path.join(theme_dir, '.sbm-snapshots')
            os.makedirs(snapshot_dir, exist_ok=True)
            
            # Files to snapshot
            files_to_snapshot = ['sb-inside.scss', 'sb-vdp.scss', 'sb-vrp.scss', 'sb-home.scss']
            
            for filename in files_to_snapshot:
                source_path = os.path.join(theme_dir, filename)
                if os.path.exists(source_path):
                    snapshot_path = os.path.join(snapshot_dir, f"{filename}.automated")
                    with open(source_path, 'r') as src, open(snapshot_path, 'w') as dst:
                        dst.write(src.read())
                    logger.debug(f"Created snapshot: {snapshot_path}")
            
            logger.info(f"Created automation snapshot for {slug}")
            return True
            
        except Exception as e:
            logger.warning(f"Failed to create automation snapshot: {e}")
            return False

    def _detect_manual_changes_from_snapshots(self, slug: str) -> Dict[str, Any]:
        """
        Detect manual changes by comparing current state with automation snapshots.
        This is more accurate than analyzing git diff patterns.
        """
        manual_changes = {
            'has_manual_changes': False,
            'change_types': [],
            'files_modified': [],
            'estimated_manual_lines': 0,
            'change_descriptions': [],
            'detailed_changes': {}
        }
        
        try:
            theme_dir = get_dealer_theme_dir(slug)
            snapshot_dir = os.path.join(theme_dir, '.sbm-snapshots')
            
            if not os.path.exists(snapshot_dir):
                logger.debug("No snapshots found, falling back to git diff analysis")
                return self._detect_manual_changes()
            
            files_to_check = ['sb-inside.scss', 'sb-vdp.scss', 'sb-vrp.scss', 'sb-home.scss']
            
            for filename in files_to_check:
                current_path = os.path.join(theme_dir, filename)
                snapshot_path = os.path.join(snapshot_dir, f"{filename}.automated")
                
                if not os.path.exists(current_path) or not os.path.exists(snapshot_path):
                    continue
                
                # Compare files
                with open(current_path, 'r') as current_file, open(snapshot_path, 'r') as snapshot_file:
                    current_content = current_file.read()
                    snapshot_content = snapshot_file.read()
                
                if current_content != snapshot_content:
                    manual_changes['has_manual_changes'] = True
                    manual_changes['files_modified'].append(filename)
                    
                    # Analyze the differences
                    current_lines = current_content.splitlines()
                    snapshot_lines = snapshot_content.splitlines()
                    
                    # Simple diff analysis
                    added_lines = []
                    for i, line in enumerate(current_lines):
                        if i >= len(snapshot_lines) or line != snapshot_lines[i]:
                            added_lines.append(line)
                    
                    manual_changes['detailed_changes'][filename] = {
                        'lines_added': len(added_lines),
                        'content_added': added_lines
                    }
                    
                    manual_changes['estimated_manual_lines'] += len(added_lines)
                    
                    # Analyze types of changes
                    self._analyze_change_types(added_lines, manual_changes)
            
            # Generate descriptions
            if manual_changes['has_manual_changes']:
                manual_changes['change_descriptions'] = self._generate_change_descriptions(manual_changes)
            
        except Exception as e:
            logger.debug(f"Error detecting manual changes from snapshots: {e}")
            # Fallback to git diff analysis
            return self._detect_manual_changes()
        
        return manual_changes

    def _analyze_change_types(self, added_lines: List[str], manual_changes: Dict[str, Any]):
        """Analyze the types of changes made in the added lines."""
        change_patterns = {
            'custom_comments': r'\/\*.*(?:custom|manual|added|fix|tweak|adjust).*\*\/',
            'media_queries': r'@media.*\(',
            'pseudo_selectors': r':(?:hover|focus|active|before|after)',
            'custom_classes': r'\.(?:custom|manual|fix|temp|override)-',
            'brand_specific': r'(?:brand-specific|dealer-custom)',
            'important_overrides': r'!important',
            'z_index_adjustments': r'z-index:\s*\d+',
            'position_fixes': r'position:\s*(?:absolute|relative|fixed)',
            'color_customizations': r'(?:color|background).*#[0-9a-fA-F]{3,6}',
            'spacing_tweaks': r'(?:margin|padding).*(?:\d+px|\d+rem|\d+em)'
        }
        
        for line in added_lines:
            for change_type, pattern in change_patterns.items():
                if re.search(pattern, line, re.IGNORECASE):
                    if change_type not in manual_changes['change_types']:
                        manual_changes['change_types'].append(change_type)

    def _generate_change_descriptions(self, manual_changes: Dict[str, Any]) -> List[str]:
        """Generate human-readable descriptions of the changes."""
        type_descriptions = {
            'custom_comments': 'Added explanatory comments for custom modifications',
            'media_queries': 'Enhanced responsive design with custom media queries',
            'pseudo_selectors': 'Improved interactive states (hover, focus, etc.)',
            'custom_classes': 'Created custom CSS classes for specific styling needs',
            'brand_specific': 'Implemented brand-specific customizations',
            'important_overrides': 'Added CSS !important overrides for specificity',
            'z_index_adjustments': 'Fixed layering issues with z-index adjustments',
            'position_fixes': 'Corrected element positioning',
            'color_customizations': 'Applied custom color schemes',
            'spacing_tweaks': 'Fine-tuned spacing and layout'
        }
        
        descriptions = []
        for change_type in manual_changes['change_types']:
            if change_type in type_descriptions:
                descriptions.append(type_descriptions[change_type])
        
        return descriptions

    def cleanup_snapshots(self, slug: str):
        """Clean up snapshot files after PR creation."""
        try:
            theme_dir = get_dealer_theme_dir(slug)
            snapshot_dir = os.path.join(theme_dir, '.sbm-snapshots')
            
            if os.path.exists(snapshot_dir):
                import shutil
                shutil.rmtree(snapshot_dir)
                logger.debug(f"Cleaned up snapshots for {slug}")
        except Exception as e:
            logger.debug(f"Failed to cleanup snapshots: {e}")

    def _build_stellantis_pr_content(self, slug: str, branch: str, repo_info: Dict[str, str]) -> Dict[str, str]:
        """Build PR content using Stellantis template with dynamic What section based on actual Git changes."""
        title = f"{slug} - SBM FE Audit"
        
        # Get automated migration changes
        automated_items = self._analyze_migration_changes()
        
        # Detect manual changes using snapshots (more accurate)
        manual_analysis = self._detect_manual_changes_from_snapshots(slug)
        
        # Build the what section
        what_items = []
        
        # Add automated changes
        if automated_items:
            what_items.extend(automated_items)
        else:
            # Fallback if no changes detected
            what_items.append("- Migrated interior page styles from style.scss and inside.scss to sb-inside.scss")
        
        # Add manual changes ONLY if they exist (simple format)
        if manual_analysis['has_manual_changes'] and manual_analysis['change_descriptions']:
            for description in manual_analysis['change_descriptions']:
                what_items.append(f"- {description}")
        
        # Add FCA-specific items for Stellantis brands (only if files were actually changed)
        if automated_items and any(brand in slug.lower() for brand in ['chrysler', 'dodge', 'jeep', 'ram', 'fiat', 'cdjr', 'fca']):
            what_items.append("- Added FCA Direction Row Styles")
            what_items.append("- Added FCA Cookie Banner styles")
        
        what_section = "\n".join(what_items)
        
        # Build the body using the original clean format
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
            'what_section': what_section,
            'manual_analysis': manual_analysis
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

    def create_pr(self, slug: str, branch_name: str = None, title: str = None, body: str = None,
                  base: str = None, head: str = None, reviewers: List[str] = None,
                  labels: List[str] = None, draft: bool = False) -> Dict[str, Any]:
        """
        Create a GitHub Pull Request for a given theme. This is the primary method for PR creation.

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
            pr_content = self._build_stellantis_pr_content(slug, current_branch, repo_info)
            pr_title = title or pr_content['title']
            pr_body = body or pr_content['body']
            what_section = pr_content['what_section']

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

            # Open the PR in browser after creation
            self._open_pr_in_browser(pr_url)

            # Copy Salesforce message to clipboard
            self._copy_salesforce_message_to_clipboard(what_section, pr_url)

            return {
                "success": True,
                "pr_url": pr_url,
                "branch": current_branch,
                "title": pr_title,
                "body": pr_body
            }

        except Exception as e:
            error_str = str(e)
            logger.error(f"PR creation failed: {error_str}")

            # Handle existing PR gracefully
            if self._is_pr_exists_error(error_str):
                try:
                    existing_pr_url = self._handle_existing_pr(error_str, head or branch_name)
                    logger.info(f"PR already exists: {existing_pr_url}")
                    # Still copy Salesforce message since migration likely completed
                    pr_content = self._build_stellantis_pr_content(slug, head or branch_name, {})
                    self._copy_salesforce_message_to_clipboard(pr_content['what_section'], existing_pr_url)

                    return {
                        "success": True,
                        "pr_url": existing_pr_url,
                        "branch": head or branch_name,
                        "title": pr_content['title'],
                        "existing": True
                    }
                except Exception as handle_e:
                     logger.error(f"Failed to handle existing PR: {handle_e}")


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

def create_pr(slug, branch_name=None, **kwargs):
    """Legacy wrapper for create_pr."""
    git_ops = GitOperations(Config({}))
    return git_ops.create_pr(slug=slug, branch_name=branch_name, **kwargs)

def create_automation_snapshot(slug):
    """Legacy wrapper for create_automation_snapshot."""
    git_ops = GitOperations(Config({}))
    return git_ops.create_automation_snapshot(slug)

def cleanup_snapshots(slug):
    """Legacy wrapper for cleanup_snapshots."""
    git_ops = GitOperations(Config({}))
    return git_ops.cleanup_snapshots(slug)
