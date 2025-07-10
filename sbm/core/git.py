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


class CommentIntelligence:
    """Intelligent comment analysis to understand change intent."""
    
    def __init__(self):
        self.intent_keywords = {
            'testing': ['testing', 'test', 'experiment', 'trying', 'trial'],
            'integration': ['adding', 'integrating', 'including', 'importing', 'merging'],
            'fixing': ['fix', 'fixing', 'repair', 'correct', 'resolve', 'bug'],
            'enhancement': ['improve', 'enhance', 'optimize', 'better', 'upgrade'],
            'temporary': ['temp', 'temporary', 'quick', 'hotfix', 'placeholder'],
            'migration': ['migrat', 'mov', 'transfer', 'port', 'convert'],
            'customization': ['custom', 'dealer', 'brand', 'specific', 'override']
        }
        
        self.automotive_terms = {
            'vdp': 'Vehicle Detail Page',
            'vrp': 'Vehicle Results Page', 
            'inventory': 'Inventory Management',
            'ctabox': 'Call-to-Action Component',
            'premium-features': 'Premium Feature Display',
            'incentives': 'Vehicle Incentives',
            'badge': 'Vehicle Badge/Award',
            'results-page': 'Search Results Page'
        }
    
    def analyze_comment(self, comment_text: str) -> Dict[str, Any]:
        """Analyze a comment to extract intent, action, and target."""
        comment_lower = comment_text.lower().strip()
        
        # Remove comment markers
        comment_clean = re.sub(r'^//\s*|^/\*\s*|\s*\*/$', '', comment_lower).strip()
        
        analysis = {
            'raw_text': comment_text,
            'clean_text': comment_clean,
            'intent': None,
            'action': None,
            'target': None,
            'automotive_context': [],
            'confidence': 0.0,
            'description': None
        }
        
        # Extract intent
        for intent_type, keywords in self.intent_keywords.items():
            if any(keyword in comment_clean for keyword in keywords):
                analysis['intent'] = intent_type
                break
        
        # Extract action words
        action_patterns = [
            r'\b(adding|integrating|including|importing)\b',
            r'\b(fixing|correcting|resolving)\b', 
            r'\b(improving|enhancing|optimizing)\b',
            r'\b(testing|experimenting)\b'
        ]
        
        for pattern in action_patterns:
            match = re.search(pattern, comment_clean)
            if match:
                analysis['action'] = match.group(1)
                break
        
        # Extract automotive context
        for term, description in self.automotive_terms.items():
            if term in comment_clean:
                analysis['automotive_context'].append({
                    'term': term,
                    'description': description
                })
        
        # Extract target (what's being modified)
        target_patterns = [
            r'(vdp|vrp)\.css',
            r'(vdp|vrp)\s+styles',
            r'#([\w-]+)',  # CSS IDs
            r'\.([\w-]+)',  # CSS classes
        ]
        
        for pattern in target_patterns:
            match = re.search(pattern, comment_clean)
            if match:
                analysis['target'] = match.group(1) if match.group(1) else match.group(0)
                break
        
        # Calculate confidence and generate description
        analysis['confidence'] = self._calculate_confidence(analysis)
        if analysis['confidence'] > 0.5:
            analysis['description'] = self._generate_description(analysis)
        
        return analysis
    
    def _calculate_confidence(self, analysis: Dict[str, Any]) -> float:
        """Calculate confidence score for the analysis."""
        confidence = 0.0
        
        # Base confidence from having intent
        if analysis['intent']:
            confidence += 0.3
        
        # Boost for having action
        if analysis['action']:
            confidence += 0.2
        
        # Boost for automotive context
        if analysis['automotive_context']:
            confidence += 0.3
        
        # Boost for having target
        if analysis['target']:
            confidence += 0.2
        
        return min(confidence, 1.0)
    
    def _generate_description(self, analysis: Dict[str, Any]) -> str:
        """Generate human-readable description from analysis."""
        parts = []
        
        # Start with action if available
        if analysis['action']:
            parts.append(analysis['action'].capitalize())
        else:
            parts.append("Modified")
        
        # Add target context
        if analysis['target']:
            if analysis['automotive_context']:
                # Use automotive context for better description
                auto_desc = analysis['automotive_context'][0]['description']
                parts.append(f"{auto_desc.lower()} ({analysis['target']})")
            else:
                parts.append(f"styles for {analysis['target']}")
        elif analysis['automotive_context']:
            auto_desc = analysis['automotive_context'][0]['description']
            parts.append(f"{auto_desc.lower()} styles")
        
        # Add intent context
        if analysis['intent'] and analysis['intent'] != 'customization':
            if analysis['intent'] == 'testing':
                parts.append("for testing purposes")
            elif analysis['intent'] == 'integration':
                parts.append("integration")
            elif analysis['intent'] == 'fixing':
                parts.append("to resolve issues")
        
        return " ".join(parts)


class CSSIntelligence:
    """Intelligent CSS analysis to understand what selectors and properties do."""
    
    def __init__(self):
        self.selector_types = {
            # Page-specific selectors
            '#results-page': 'Vehicle Results Page (VRP)',
            '#lvrp-results-wrapper': 'Live Vehicle Results Page',
            '#ctabox-premium-features': 'Premium Features CTA Component',
            '#header': 'Site Header',
            '#footer': 'Site Footer',
            
            # Component selectors
            '.vehicle-description-text': 'Vehicle Description Content',
            '.features-link': 'Feature Link Component',
            '.list-group-item': 'List Item Component',
            '.incentives': 'Vehicle Incentives Display',
            '.badge-row': 'Vehicle Badge/Award Row',
            '.cookie-banner': 'Cookie Consent Banner',
            '.navbar': 'Navigation Menu',
            '.fat-footer': 'Footer Content Area'
        }
        
        self.property_purposes = {
            'display': 'visibility control',
            'position': 'element positioning',
            'z-index': 'layering/stacking order',
            'background': 'background styling',
            'color': 'text color',
            'border': 'border styling',
            'padding': 'internal spacing',
            'margin': 'external spacing',
            'max-width': 'responsive width control',
            'max-height': 'height constraint',
            'overflow': 'content overflow handling',
            'overflow-y': 'content overflow handling'
        }
    
    def analyze_css_block(self, css_lines: List[str]) -> Dict[str, Any]:
        """Analyze a block of CSS changes."""
        analysis = {
            'selectors': [],
            'properties': [],
            'purposes': [],
            'component_type': None,
            'business_context': None,
            'confidence': 0.0
        }
        
        # Extract selectors and properties
        for line in css_lines:
            line_clean = line.strip().lstrip('+').strip()
            
            # Extract CSS selectors
            selector_match = re.match(r'^([#\.\w\-\s\[\]:,>+~]+)\s*\{?', line_clean)
            if selector_match:
                selector = selector_match.group(1).strip()
                analysis['selectors'].append(selector)
                
                # Check if we know this selector
                for known_selector, description in self.selector_types.items():
                    if known_selector in selector:
                        analysis['component_type'] = description
                        break
            
            # Extract CSS properties
            property_match = re.match(r'^([\w-]+)\s*:', line_clean)
            if property_match:
                prop = property_match.group(1)
                analysis['properties'].append(prop)
                
                # Add purpose if we know it
                if prop in self.property_purposes:
                    purpose = self.property_purposes[prop]
                    if purpose not in analysis['purposes']:
                        analysis['purposes'].append(purpose)
        
        # Calculate confidence
        analysis['confidence'] = self._calculate_css_confidence(analysis)
        
        return analysis
    
    def _calculate_css_confidence(self, analysis: Dict[str, Any]) -> float:
        """Calculate confidence for CSS analysis."""
        confidence = 0.0
        
        if analysis['component_type']:
            confidence += 0.5
        
        if analysis['purposes']:
            confidence += 0.3
        
        if analysis['selectors']:
            confidence += 0.2
        
        return min(confidence, 1.0)


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
            
            # Clean up any snapshot files that might have been created after the initial cleanup
            snapshot_dir = os.path.join(get_dealer_theme_dir(slug), '.sbm-snapshots')
            if os.path.exists(snapshot_dir):
                import shutil
                shutil.rmtree(snapshot_dir)
                logger.info(f"Cleaned up snapshot directory before commit: {snapshot_dir}")
            
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
                logger.warning("No files were added to git")
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
            # Set up environment with custom token if available
            env = os.environ.copy()
            
            # Check for custom GitHub token in config
            if hasattr(self.config, 'github_token') and self.config.github_token:
                env['GH_TOKEN'] = self.config.github_token
                logger.debug("Using custom GitHub token from config")
            elif hasattr(self.config, 'git') and self.config.git:
                git_config = self.config.git
                if isinstance(git_config, dict) and 'github_token' in git_config:
                    env['GH_TOKEN'] = git_config['github_token']
                    logger.debug("Using custom GitHub token from git config")
                elif hasattr(git_config, 'github_token') and git_config.github_token:
                    env['GH_TOKEN'] = git_config.github_token
                    logger.debug("Using custom GitHub token from git config")
            
            result = subprocess.run(cmd, check=True, capture_output=True, text=True, 
                                  cwd=get_platform_dir(), env=env)
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
                # Set up environment with custom token if available
                env = os.environ.copy()
                
                # Check for custom GitHub token in config
                if hasattr(self.config, 'github_token') and self.config.github_token:
                    env['GH_TOKEN'] = self.config.github_token
                elif hasattr(self.config, 'git') and self.config.git:
                    git_config = self.config.git
                    if isinstance(git_config, dict) and 'github_token' in git_config:
                        env['GH_TOKEN'] = git_config['github_token']
                    elif hasattr(git_config, 'github_token') and git_config.github_token:
                        env['GH_TOKEN'] = git_config.github_token
                
                list_result = subprocess.run([
                    'gh', 'pr', 'list', '--head', head_branch, '--json', 'url'
                ], capture_output=True, text=True, check=True, cwd=get_platform_dir(), env=env)
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
                if (current_dir / "css" / "_support-requests.scss").exists():
                    source_files.append("_support-requests.scss")
                
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
                # sb-home.scss is always created blank for developer use
                what_items.append("- Created sb-home.scss for home page styles (blank for developer use)")
            
            logger.debug(f"Analyzed {len(css_files)} CSS file changes, generated {len(what_items)} what items")
            
        except subprocess.CalledProcessError as e:
            logger.warning(f"Could not analyze Git changes: {e}")
        except Exception as e:
            logger.warning(f"Error analyzing migration changes: {e}")
        
        return what_items

    def _detect_manual_changes(self) -> Dict[str, Any]:
        """
        Detect manual changes by comparing current files with automation snapshots.
        """
        manual_changes = {
            'has_manual_changes': False,
            'change_descriptions': [],
            'files_modified': [],
            'estimated_manual_lines': 0,
            'added_lines': [],
            'file_line_counts': {}  # Track lines per file
        }
        
        try:
            # Get current working directory to find theme
            current_dir = Path.cwd()
            
            # Look for snapshots directory
            snapshot_dir = current_dir / '.sbm-snapshots'
            if not snapshot_dir.exists():
                logger.debug("No snapshot directory found, falling back to git diff method")
                return self._detect_manual_changes_fallback()
            
            # Check each snapshot file against current file
            migration_files = ['sb-inside.scss', 'sb-vdp.scss', 'sb-vrp.scss', 'sb-home.scss']
            
            for sb_file in migration_files:
                snapshot_file = snapshot_dir / f"{sb_file}.automated"
                current_file = current_dir / sb_file
                
                if snapshot_file.exists() and current_file.exists():
                    # Read both files
                    snapshot_content = snapshot_file.read_text()
                    current_content = current_file.read_text()
                    
                    # Compare content
                    if snapshot_content != current_content:
                        # Calculate line differences
                        snapshot_lines = snapshot_content.splitlines()
                        current_lines = current_content.splitlines()
                        
                        # Simple line count difference (could be more sophisticated)
                        line_diff = len(current_lines) - len(snapshot_lines)
                        
                        if line_diff != 0:
                            manual_changes['has_manual_changes'] = True
                            manual_changes['file_line_counts'][sb_file] = abs(line_diff)
                            manual_changes['files_modified'].append(sb_file)
                            
                            # Create description
                            if line_diff > 0:
                                manual_changes['change_descriptions'].append(
                                    f"Manual changes to {sb_file} ({line_diff} lines added) - please add details if needed"
                                )
                            else:
                                manual_changes['change_descriptions'].append(
                                    f"Manual changes to {sb_file} ({abs(line_diff)} lines removed) - please add details if needed"
                                )
            
            # Calculate total manual lines
            manual_changes['estimated_manual_lines'] = sum(manual_changes['file_line_counts'].values())
            
            logger.debug(f"Snapshot comparison found {manual_changes['estimated_manual_lines']} manual lines")
            
        except Exception as e:
            logger.debug(f"Error in snapshot-based manual change detection: {e}")
            return self._detect_manual_changes_fallback()
        
        return manual_changes

    def _detect_manual_changes_fallback(self) -> Dict[str, Any]:
        """
        Simple, honest detection of manual changes - just count lines and let user explain.
        """
        manual_changes = {
            'has_manual_changes': False,
            'change_descriptions': [],
            'files_modified': [],
            'estimated_manual_lines': 0,
            'added_lines': [],
            'file_line_counts': {}  # Track lines per file
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
            
            lines = diff_content.split('\n')
            added_lines = [line for line in lines if line.startswith('+') and not line.startswith('+++')]
            manual_changes['added_lines'] = added_lines
            
            if not added_lines:
                return manual_changes
            
            # Get list of files that were changed
            file_result = subprocess.run(
                ['git', 'diff', '--name-status', 'main...HEAD'],
                capture_output=True, text=True, check=True,
                cwd=get_platform_dir()
            )
            
            changed_files = file_result.stdout.strip().split('\n') if file_result.stdout.strip() else []
            
            # Check if files are newly created (A) vs modified (M)
            new_files = []
            modified_files = []
            
            for line in changed_files:
                if not line.strip():
                    continue
                parts = line.split('\t', 1)
                if len(parts) == 2:
                    status, filepath = parts
                    filename = os.path.basename(filepath)
                    if filename.endswith('.scss'):
                        if status == 'A':
                            new_files.append(filename)
                        elif status == 'M':
                            modified_files.append(filename)
            
            # Only count modifications to existing files as potential manual changes
            # New files created by migration (sb-*.scss) should not be counted as manual
            migration_files = {'sb-inside.scss', 'sb-vdp.scss', 'sb-vrp.scss', 'sb-home.scss'}
            
            # Count manual lines per file - only for modified existing files or new non-migration files
            current_file = None
            for line in lines:
                # Track which file we're in
                if line.startswith('+++'):
                    file_match = re.search(r'\+\+\+ b/(.+)', line)
                    if file_match:
                        current_file = os.path.basename(file_match.group(1))
                        if current_file.endswith('.scss'):
                            # Only initialize count for files that aren't migration files
                            # Exclude ALL migration files regardless of git status (A or M)
                            if current_file not in migration_files:
                                manual_changes['file_line_counts'][current_file] = 0
                
                # Count added lines for current file (only if it's not a migration file)
                elif line.startswith('+') and current_file and current_file.endswith('.scss'):
                    if current_file in manual_changes['file_line_counts']:
                        manual_changes['file_line_counts'][current_file] += 1
            
            # Calculate totals
            total_manual_lines = sum(manual_changes['file_line_counts'].values())
            if total_manual_lines > 0:
                manual_changes['has_manual_changes'] = True
                manual_changes['estimated_manual_lines'] = total_manual_lines
                
                # Generate simple descriptions based on line counts
                for filename, line_count in manual_changes['file_line_counts'].items():
                    if line_count > 0:
                        manual_changes['change_descriptions'].append(
                            f"Manual changes to {filename} ({line_count} lines) - please add details if needed"
                        )
            
            # Only include modified files in the list, excluding ALL migration files
            manual_changes['files_modified'] = [
                filename for filename in modified_files
                if filename.endswith('.scss') and filename not in migration_files
            ]
            
        except subprocess.CalledProcessError as e:
            logger.debug(f"Could not analyze manual changes: {e}")
        except Exception as e:
            logger.debug(f"Error detecting manual changes: {e}")
        
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
        """Generate human-readable descriptions of the changes - ONLY for clear, specific changes."""
        type_descriptions = {
            'custom_comments': 'Added explanatory comments for custom modifications',
            'custom_classes': 'Created custom CSS classes for specific styling needs',
            'brand_specific': 'Implemented brand-specific customizations',
            'important_overrides': 'Added CSS !important overrides for specificity',
            'z_index_adjustments': 'Fixed layering issues with z-index adjustments',
            'position_fixes': 'Corrected element positioning'
            # REMOVED: Generic template descriptions that don't provide meaningful information:
            # - 'media_queries': 'Enhanced responsive design with custom media queries'
            # - 'pseudo_selectors': 'Improved interactive states (hover, focus, etc.)'  
            # - 'color_customizations': 'Applied custom color schemes'
            # - 'spacing_tweaks': 'Fine-tuned spacing and layout'
        }
        
        descriptions = []
        for change_type in manual_changes['change_types']:
            if change_type in type_descriptions:
                descriptions.append(type_descriptions[change_type])
        
        return descriptions

    def _build_stellantis_pr_content(self, slug: str, branch: str, repo_info: Dict[str, str]) -> Dict[str, str]:
        """Build PR content using Stellantis template with dynamic What section based on actual Git changes."""
        title = f"{slug} - SBM FE Audit"
        
        # Get automated migration changes
        automated_items = self._analyze_migration_changes()
        
        # Detect manual changes using git diff analysis
        manual_analysis = self._detect_manual_changes()
        
        # Build the what section
        what_items = []
        
        # Add automated changes
        if automated_items:
            what_items.extend(automated_items)
        else:
            # Fallback if no changes detected
            what_items.append("- Migrated interior page styles from style.scss, inside.scss, and _support-requests.scss to sb-inside.scss")
        
        # Add manual changes ONLY if they exist - with intelligent analysis
        if manual_analysis['has_manual_changes']:
            if manual_analysis['change_descriptions']:
                # We have clear, identifiable changes - add specific descriptions
                for description in manual_analysis['change_descriptions']:
                    what_items.append(f"- {description}")
            else:
                # Manual changes detected but unclear what they are - prompt for details
                manual_lines = manual_analysis.get('estimated_manual_lines', 0)
                if manual_lines > 0:
                    what_items.append(f"- Manual modifications added ({manual_lines} lines) - details need review")
        
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
            salesforce_message = f"""FED Site Builder Migration Complete:

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
            if hasattr(self.config, 'git') and self.config.git:
                git_config = self.config.git
                if isinstance(git_config, dict):
                    pr_reviewers = reviewers or git_config.get('default_reviewers', ['carsdotcom/fe-dev'])
                    pr_labels = labels or git_config.get('default_labels', ['fe-dev'])
                else:
                    pr_reviewers = reviewers or getattr(git_config, 'default_reviewers', ['carsdotcom/fe-dev'])
                    pr_labels = labels or getattr(git_config, 'default_labels', ['fe-dev'])
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
    from ..config import Config
    # Initialize config with safe defaults
    config_dict = {
        'default_branch': 'main',
        'git': {
            'default_reviewers': ['carsdotcom/fe-dev'],
            'default_labels': ['fe-dev']
        }
    }
    git_ops = GitOperations(Config(config_dict))
    return git_ops.create_pr(slug=slug, branch_name=branch_name, **kwargs)
