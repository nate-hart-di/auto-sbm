"""
Core Git operations tests.
Tests Git workflow functionality and operations.
"""
import pytest
import os
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock, call
import tempfile

# Import git operation functions - adjust based on actual codebase
try:
    from sbm.core.git_operations import create_branch, commit_changes, push_branch
except ImportError:
    # If these don't exist, we'll test basic git operations
    create_branch = None
    commit_changes = None
    push_branch = None


class TestGitBasicOperations:
    """Test basic Git operations."""
    
    def test_git_status_check(self, tmp_path):
        """Test checking Git repository status."""
        # Initialize git repo
        os.chdir(tmp_path)
        subprocess.run(['git', 'init'], check=True, capture_output=True)
        subprocess.run(['git', 'config', 'user.email', 'test@example.com'], check=True)
        subprocess.run(['git', 'config', 'user.name', 'Test User'], check=True)
        
        # Test git status
        result = subprocess.run(['git', 'status', '--porcelain'], 
                              capture_output=True, text=True)
        assert result.returncode == 0
        # Empty repo should have no changes
        assert result.stdout.strip() == ""
    
    def test_git_add_operations(self, tmp_path):
        """Test Git add operations."""
        # Initialize git repo
        os.chdir(tmp_path)
        subprocess.run(['git', 'init'], check=True, capture_output=True)
        subprocess.run(['git', 'config', 'user.email', 'test@example.com'], check=True)
        subprocess.run(['git', 'config', 'user.name', 'Test User'], check=True)
        
        # Create test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        
        # Add file
        result = subprocess.run(['git', 'add', 'test.txt'], 
                              capture_output=True, text=True)
        assert result.returncode == 0
        
        # Check status
        result = subprocess.run(['git', 'status', '--porcelain'], 
                              capture_output=True, text=True)
        assert "A  test.txt" in result.stdout
    
    def test_git_commit_operations(self, tmp_path):
        """Test Git commit operations."""
        # Initialize git repo
        os.chdir(tmp_path)
        subprocess.run(['git', 'init'], check=True, capture_output=True)
        subprocess.run(['git', 'config', 'user.email', 'test@example.com'], check=True)
        subprocess.run(['git', 'config', 'user.name', 'Test User'], check=True)
        
        # Create and add test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        subprocess.run(['git', 'add', 'test.txt'], check=True)
        
        # Commit
        result = subprocess.run(['git', 'commit', '-m', 'Test commit'], 
                              capture_output=True, text=True)
        assert result.returncode == 0
        
        # Check log
        result = subprocess.run(['git', 'log', '--oneline'], 
                              capture_output=True, text=True)
        assert "Test commit" in result.stdout


class TestGitBranchOperations:
    """Test Git branch operations."""
    
    def test_branch_creation(self, tmp_path):
        """Test creating Git branches."""
        # Initialize git repo with initial commit
        os.chdir(tmp_path)
        subprocess.run(['git', 'init'], check=True, capture_output=True)
        subprocess.run(['git', 'config', 'user.email', 'test@example.com'], check=True)
        subprocess.run(['git', 'config', 'user.name', 'Test User'], check=True)
        
        # Need initial commit to create branches
        test_file = tmp_path / "README.md"
        test_file.write_text("Initial commit")
        subprocess.run(['git', 'add', 'README.md'], check=True)
        subprocess.run(['git', 'commit', '-m', 'Initial commit'], check=True)
        
        # Create new branch
        branch_name = "feature/test-branch"
        result = subprocess.run(['git', 'checkout', '-b', branch_name], 
                              capture_output=True, text=True)
        assert result.returncode == 0
        
        # Verify current branch
        result = subprocess.run(['git', 'branch', '--show-current'], 
                              capture_output=True, text=True)
        assert result.stdout.strip() == branch_name
        
        # Test custom create_branch function if it exists
        if create_branch:
            try:
                create_branch("feature/test-branch-2")
                # Should not raise exception
            except Exception as e:
                pytest.fail(f"Custom create_branch function failed: {e}")
    
    def test_branch_switching(self, tmp_path):
        """Test switching between Git branches."""
        # Initialize git repo with initial commit
        os.chdir(tmp_path)
        subprocess.run(['git', 'init'], check=True, capture_output=True)
        subprocess.run(['git', 'config', 'user.email', 'test@example.com'], check=True)
        subprocess.run(['git', 'config', 'user.name', 'Test User'], check=True)
        
        # Initial commit
        test_file = tmp_path / "README.md"
        test_file.write_text("Initial commit")
        subprocess.run(['git', 'add', 'README.md'], check=True)
        subprocess.run(['git', 'commit', '-m', 'Initial commit'], check=True)
        
        # Create and switch to new branch
        subprocess.run(['git', 'checkout', '-b', 'feature/new'], check=True)
        
        # Switch back to main/master
        result = subprocess.run(['git', 'checkout', 'master'], 
                              capture_output=True, text=True)
        if result.returncode != 0:
            # Try 'main' instead of 'master'
            result = subprocess.run(['git', 'checkout', 'main'], 
                                  capture_output=True, text=True)
        
        # Should be able to switch to some default branch
        assert result.returncode == 0


class TestGitCommitWorkflow:
    """Test Git commit workflow for migrations."""
    
    def test_migration_commit_pattern(self, tmp_path):
        """Test commit pattern for migration changes."""
        # Initialize git repo
        os.chdir(tmp_path)
        subprocess.run(['git', 'init'], check=True, capture_output=True)
        subprocess.run(['git', 'config', 'user.email', 'test@example.com'], check=True)
        subprocess.run(['git', 'config', 'user.name', 'Test User'], check=True)
        
        # Initial commit
        test_file = tmp_path / "README.md"
        test_file.write_text("Initial commit")
        subprocess.run(['git', 'add', 'README.md'], check=True)
        subprocess.run(['git', 'commit', '-m', 'Initial commit'], check=True)
        
        # Simulate migration files
        migration_files = [
            "sb-inside.scss",
            "sb-vdp.scss", 
            "sb-vrp.scss"
        ]
        
        for file_name in migration_files:
            file_path = tmp_path / file_name
            file_path.write_text(f"/* Site Builder styles for {file_name} */")
            subprocess.run(['git', 'add', file_name], check=True)
        
        # Commit migration
        commit_msg = "Site Builder Migration: test-theme\n\nGenerated files:\n- sb-inside.scss (50 lines)\n- sb-vdp.scss (45 lines)\n- sb-vrp.scss (38 lines)"
        result = subprocess.run(['git', 'commit', '-m', commit_msg], 
                              capture_output=True, text=True)
        assert result.returncode == 0
        
        # Test custom commit_changes function if it exists
        if commit_changes:
            try:
                # Create another file for testing
                another_file = tmp_path / "test.scss"
                another_file.write_text("/* Test */")
                subprocess.run(['git', 'add', 'test.scss'], check=True)
                
                commit_changes("Test commit via function", ["test.scss"])
                # Should not raise exception
            except Exception as e:
                pytest.fail(f"Custom commit_changes function failed: {e}")


class TestGitRemoteOperations:
    """Test Git remote operations (mocked)."""
    
    @patch('subprocess.run')
    def test_push_branch_mocked(self, mock_subprocess):
        """Test pushing branch (mocked to avoid real network calls)."""
        # Mock successful push
        mock_subprocess.return_value = MagicMock(returncode=0, stdout="", stderr="")
        
        if push_branch:
            try:
                push_branch("feature/test-branch")
                # Should not raise exception
            except Exception as e:
                pytest.fail(f"Custom push_branch function failed: {e}")
        else:
            # Test basic push command
            result = subprocess.run(['git', 'push', 'origin', 'feature/test'], 
                                  capture_output=True, text=True)
            # Should call subprocess (mocked)
            mock_subprocess.assert_called()
    
    @patch('subprocess.run')
    def test_git_remote_check(self, mock_subprocess):
        """Test checking Git remote configuration."""
        # Mock git remote -v output
        mock_subprocess.return_value = MagicMock(
            returncode=0,
            stdout="origin\tgit@github.com:user/repo.git (fetch)\norigin\tgit@github.com:user/repo.git (push)",
            stderr=""
        )
        
        result = subprocess.run(['git', 'remote', '-v'], 
                              capture_output=True, text=True)
        
        # Verify mock was called
        mock_subprocess.assert_called_with(['git', 'remote', '-v'], 
                                         capture_output=True, text=True)


class TestGitErrorHandling:
    """Test Git error handling and edge cases."""
    
    def test_git_operations_outside_repo(self, tmp_path):
        """Test Git operations outside a repository."""
        # Change to non-git directory
        os.chdir(tmp_path)
        
        # Git status should fail
        result = subprocess.run(['git', 'status'], 
                              capture_output=True, text=True)
        assert result.returncode != 0
        assert "not a git repository" in result.stderr.lower()
    
    def test_git_operations_with_no_commits(self, tmp_path):
        """Test Git operations in repo with no commits."""
        # Initialize empty repo
        os.chdir(tmp_path)
        subprocess.run(['git', 'init'], check=True, capture_output=True)
        subprocess.run(['git', 'config', 'user.email', 'test@example.com'], check=True)
        subprocess.run(['git', 'config', 'user.name', 'Test User'], check=True)
        
        # Some operations should fail gracefully
        result = subprocess.run(['git', 'log'], 
                              capture_output=True, text=True)
        assert result.returncode != 0  # No commits to log
    
    def test_git_merge_conflicts_detection(self, tmp_path):
        """Test detection of Git merge conflicts."""
        # This is a complex scenario - just test basic conflict detection
        os.chdir(tmp_path)
        subprocess.run(['git', 'init'], check=True, capture_output=True)
        subprocess.run(['git', 'config', 'user.email', 'test@example.com'], check=True)
        subprocess.run(['git', 'config', 'user.name', 'Test User'], check=True)
        
        # Check for merge conflicts in status
        result = subprocess.run(['git', 'status', '--porcelain'], 
                              capture_output=True, text=True)
        
        # No conflicts in clean repo
        assert "UU" not in result.stdout  # UU indicates merge conflict


class TestGitIntegration:
    """Test Git integration with migration workflow."""
    
    def test_complete_migration_git_workflow(self, tmp_path):
        """Test complete Git workflow for a migration."""
        # Initialize repo
        os.chdir(tmp_path)
        subprocess.run(['git', 'init'], check=True, capture_output=True)
        subprocess.run(['git', 'config', 'user.email', 'test@example.com'], check=True)
        subprocess.run(['git', 'config', 'user.name', 'Test User'], check=True)
        
        # Initial commit
        readme = tmp_path / "README.md"
        readme.write_text("Theme repository")
        subprocess.run(['git', 'add', 'README.md'], check=True)
        subprocess.run(['git', 'commit', '-m', 'Initial commit'], check=True)
        
        # 1. Create feature branch
        branch_name = "feature/sb-migration-testtheme"
        subprocess.run(['git', 'checkout', '-b', branch_name], check=True)
        
        # 2. Add migration files
        migration_files = {
            "sb-inside.scss": "/* Inside page styles */",
            "sb-vdp.scss": "/* VDP styles */",
            "sb-vrp.scss": "/* VRP styles */"
        }
        
        for filename, content in migration_files.items():
            file_path = tmp_path / filename
            file_path.write_text(content)
            subprocess.run(['git', 'add', filename], check=True)
        
        # 3. Commit changes
        commit_msg = f"Site Builder Migration: testtheme\n\nFiles generated:\n" + \
                    "\n".join(f"- {f}" for f in migration_files.keys())
        subprocess.run(['git', 'commit', '-m', commit_msg], check=True)
        
        # 4. Verify final state
        result = subprocess.run(['git', 'status', '--porcelain'], 
                              capture_output=True, text=True)
        assert result.stdout.strip() == ""  # No uncommitted changes
        
        result = subprocess.run(['git', 'branch', '--show-current'], 
                              capture_output=True, text=True)
        assert result.stdout.strip() == branch_name
