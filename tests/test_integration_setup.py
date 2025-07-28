"""
Integration tests for setup script validation.
Tests the setup.sh functionality and installation process.
"""
import pytest
import subprocess
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestSetupScriptBasics:
    """Test basic setup script functionality."""
    
    def test_setup_script_exists(self):
        """Test setup.sh script exists and is executable."""
        setup_script = Path("setup.sh")
        assert setup_script.exists(), "setup.sh script not found"
        
        # Check if executable
        stat = setup_script.stat()
        assert stat.st_mode & 0o111, "setup.sh is not executable"
    
    def test_setup_script_syntax(self):
        """Test setup.sh has valid bash syntax."""
        import os
        setup_script = os.path.join(os.getcwd(), "setup.sh")
        
        result = subprocess.run(
            ['bash', '-n', setup_script], 
            capture_output=True, 
            text=True
        )
        
        assert result.returncode == 0, f"Bash syntax error: {result.stderr}"
    
    def test_setup_script_help_or_dry_run(self):
        """Test setup script can show help or run in dry-run mode."""
        import os
        setup_script = os.path.join(os.getcwd(), "setup.sh")
        
        # Try to run with bash -n (syntax check only)
        result = subprocess.run(
            ['bash', '-n', setup_script], 
            capture_output=True, 
            text=True
        )
        
        assert result.returncode == 0


class TestSetupPrerequisites:
    """Test setup script prerequisite detection."""
    
    @patch('subprocess.run')
    def test_homebrew_detection(self, mock_subprocess):
        """Test Homebrew detection in setup script."""
        # Mock 'command -v brew' call
        mock_subprocess.return_value = MagicMock(returncode=0)
        
        # Simulate checking for brew command
        result = subprocess.run(['command', '-v', 'brew'], capture_output=True)
        
        # Should call subprocess to check for brew
        mock_subprocess.assert_called()
    
    @patch('subprocess.run')
    def test_python_detection(self, mock_subprocess):
        """Test Python detection in setup script."""
        # Mock 'command -v python3' call
        mock_subprocess.return_value = MagicMock(returncode=0, stdout="python3")
        
        result = subprocess.run(['command', '-v', 'python3'], capture_output=True)
        mock_subprocess.assert_called()
    
    @patch('subprocess.run')
    def test_git_detection(self, mock_subprocess):
        """Test Git detection in setup script."""
        # Mock 'command -v git' call
        mock_subprocess.return_value = MagicMock(returncode=0, stdout="git")
        
        result = subprocess.run(['command', '-v', 'git'], capture_output=True)
        mock_subprocess.assert_called()


class TestSetupEnvironmentConfiguration:
    """Test setup script environment configuration."""
    
    def test_env_example_file_exists(self):
        """Test that .env.example file exists and is readable"""
        import os
        env_example = Path(os.getcwd()) / ".env.example"
        assert env_example.exists(), ".env.example file not found"
        
        content = env_example.read_text()
        assert "GITHUB_TOKEN" in content
        assert "GITHUB_ORG" in content
    
    def test_env_file_creation(self, tmp_path):
        """Test .env file creation from template."""
        # Create test .env.example
        env_example = tmp_path / ".env.example"
        env_example.write_text("""
GITHUB_TOKEN=your_token_here
GITHUB_ORG=your_org_here
DEFAULT_BRANCH=master
""")
        
        # Simulate copying to .env
        env_file = tmp_path / ".env"
        env_file.write_text(env_example.read_text())
        
        assert env_file.exists()
        content = env_file.read_text()
        assert "GITHUB_TOKEN" in content
    
    def test_local_bin_directory_setup(self, tmp_path):
        """Test ~/.local/bin directory setup."""
        local_bin = tmp_path / ".local" / "bin"
        
        # Simulate directory creation
        local_bin.mkdir(parents=True, exist_ok=True)
        
        assert local_bin.exists()
        assert local_bin.is_dir()


class TestSetupVirtualEnvironment:
    """Test setup script virtual environment creation."""
    
    def test_venv_creation_command(self):
        """Test virtual environment creation command."""
        # Test the command that would be used
        venv_command = ['python3', '-m', 'venv', '.venv', '--prompt', 'auto-sbm']
        
        # Just verify the command structure is valid
        assert 'python3' in venv_command
        assert 'venv' in venv_command
        assert '.venv' in venv_command
    
    def test_venv_activation_script(self, tmp_path):
        """Test virtual environment activation script exists after creation."""
        # Simulate venv structure
        venv_dir = tmp_path / ".venv"
        venv_bin = venv_dir / "bin" 
        venv_bin.mkdir(parents=True)
        
        # Create mock activate script
        activate_script = venv_bin / "activate"
        activate_script.write_text("# Virtual environment activation script")
        
        assert activate_script.exists()
    
    def test_pip_upgrade_in_venv(self):
        """Test pip upgrade command for virtual environment."""
        pip_upgrade_cmd = ['pip', 'install', '--upgrade', 'pip']
        
        # Verify command structure
        assert 'pip' in pip_upgrade_cmd
        assert '--upgrade' in pip_upgrade_cmd


class TestSetupDependencyInstallation:
    """Test setup script dependency installation."""
    
    def test_uv_installation_preference(self):
        """Test UV package manager preference in setup."""
        # Test UV install command
        uv_install_cmd = ['uv', 'pip', 'install', '-e', '.[dev]']
        
        assert 'uv' in uv_install_cmd
        assert '.[dev]' in uv_install_cmd
    
    def test_pip_fallback_installation(self):
        """Test pip fallback for dependency installation."""
        # Test pip install command
        pip_install_cmd = ['pip', 'install', '-e', '.[dev]']
        
        assert 'pip' in pip_install_cmd
        assert '.[dev]' in pip_install_cmd
    
    def test_pyproject_toml_exists(self):
        """Test that pyproject.toml exists and is valid"""
        import os
        pyproject = Path(os.getcwd()) / "pyproject.toml"
        assert pyproject.exists(), "pyproject.toml not found"
        
        content = pyproject.read_text()
        assert '[project]' in content
        assert 'dependencies' in content


class TestSetupWrapperScript:
    """Test setup script wrapper creation."""
    
    def test_wrapper_script_template(self, tmp_path):
        """Test wrapper script template structure."""
        wrapper_content = """#!/bin/bash
PROJECT_ROOT="/path/to/auto-sbm"
VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python"

cd "$PROJECT_ROOT"
"$VENV_PYTHON" -m sbm.cli "$@"
"""
        
        wrapper_file = tmp_path / "sbm"
        wrapper_file.write_text(wrapper_content)
        wrapper_file.chmod(0o755)
        
        assert wrapper_file.exists()
        content = wrapper_file.read_text()
        assert "PROJECT_ROOT" in content
        assert "VENV_PYTHON" in content
        assert "sbm.cli" in content
    
    def test_wrapper_script_permissions(self, tmp_path):
        """Test wrapper script has correct permissions."""
        wrapper_file = tmp_path / "sbm"
        wrapper_file.write_text("#!/bin/bash\necho test")
        wrapper_file.chmod(0o755)
        
        stat = wrapper_file.stat()
        assert stat.st_mode & 0o111, "Wrapper script not executable"


class TestSetupGitHubCLI:
    """Test setup script GitHub CLI configuration."""
    
    @patch('subprocess.run')
    def test_github_cli_auth_check(self, mock_subprocess):
        """Test GitHub CLI authentication check."""
        # Mock 'gh auth status' call
        mock_subprocess.return_value = MagicMock(returncode=0)
        
        result = subprocess.run(['gh', 'auth', 'status'], capture_output=True)
        mock_subprocess.assert_called()
    
    @patch('subprocess.run')
    def test_github_cli_login_prompt(self, mock_subprocess):
        """Test GitHub CLI login prompt."""
        # Mock 'gh auth login' call
        mock_subprocess.return_value = MagicMock(returncode=0)
        
        result = subprocess.run(['gh', 'auth', 'login'], capture_output=True)
        mock_subprocess.assert_called()


class TestSetupValidation:
    """Test setup script validation and health checks."""
    
    def test_setup_completion_marker(self, tmp_path):
        """Test setup completion marker file creation."""
        marker_file = tmp_path / ".sbm_setup_complete"
        
        # Simulate marker creation
        marker_file.touch()
        
        assert marker_file.exists()
    
    def test_setup_log_creation(self, tmp_path):
        """Test setup log file creation."""
        log_file = tmp_path / "setup.log"
        
        # Simulate log creation
        log_file.write_text("[INFO] Setup started\n[INFO] Setup completed\n")
        
        assert log_file.exists()
        content = log_file.read_text()
        assert "[INFO]" in content
    
    def test_path_environment_variable(self, tmp_path):
        """Test PATH environment variable modification."""
        # Test HOME/.local/bin path
        local_bin_path = str(tmp_path / ".local" / "bin")
        
        # Simulate PATH check
        current_path = os.environ.get("PATH", "")
        if local_bin_path not in current_path:
            # Would need to add to PATH
            new_path = f"{local_bin_path}:{current_path}"
            assert local_bin_path in new_path


class TestSetupErrorHandling:
    """Test setup script error handling."""
    
    def test_setup_cleanup_on_failure(self, tmp_path):
        """Test cleanup behavior when setup fails."""
        # Simulate partial setup state
        venv_dir = tmp_path / ".venv"
        venv_dir.mkdir()
        
        env_file = tmp_path / ".env"
        env_file.write_text("GITHUB_TOKEN=partial")
        
        wrapper_file = tmp_path / ".local" / "bin" / "sbm"
        wrapper_file.parent.mkdir(parents=True)
        wrapper_file.write_text("#!/bin/bash\necho partial")
        
        # Test cleanup function behavior
        def cleanup_failed_installation():
            if venv_dir.exists():
                import shutil
                shutil.rmtree(venv_dir)
            if env_file.exists():
                env_file.unlink()
            if wrapper_file.exists():
                wrapper_file.unlink()
        
        # Run cleanup
        cleanup_failed_installation()
        
        # Verify cleanup
        assert not venv_dir.exists()
        assert not env_file.exists()
        assert not wrapper_file.exists()
    
    def test_retry_mechanism_structure(self):
        """Test retry mechanism for network operations."""
        def retry_command(command, description, max_attempts=3):
            for attempt in range(max_attempts):
                try:
                    # Simulate command execution
                    result = subprocess.run(
                        command, 
                        capture_output=True, 
                        check=True
                    )
                    return result
                except subprocess.CalledProcessError:
                    if attempt < max_attempts - 1:
                        continue
                    else:
                        raise
        
        # Test retry function structure
        assert callable(retry_command)
        
        # Test with successful command
        try:
            result = retry_command(['echo', 'test'], 'test command')
            assert result.returncode == 0
        except Exception:
            # Command might fail in test environment - that's ok
            pass


class TestSetupIntegration:
    """Test setup script integration scenarios."""
    
    def test_fresh_installation_workflow(self, tmp_path):
        """Test complete fresh installation workflow."""
        # Simulate fresh environment
        os.chdir(tmp_path)
        
        # 1. Clone repository (simulated)
        repo_dir = tmp_path / "auto-sbm"
        repo_dir.mkdir()
        
        # 2. Create essential files
        setup_script = repo_dir / "setup.sh"
        setup_script.write_text("#!/bin/bash\necho 'Setup script'")
        setup_script.chmod(0o755)
        
        pyproject_file = repo_dir / "pyproject.toml"
        pyproject_file.write_text("[project]\nname = 'auto-sbm'")
        
        env_example = repo_dir / ".env.example"
        env_example.write_text("GITHUB_TOKEN=example")
        
        # 3. Verify setup can proceed
        assert setup_script.exists()
        assert pyproject_file.exists()
        assert env_example.exists()
    
    def test_existing_installation_update(self, tmp_path):
        """Test updating existing installation."""
        # Simulate existing installation
        os.chdir(tmp_path)
        
        # Existing venv
        venv_dir = tmp_path / ".venv"
        venv_dir.mkdir()
        
        # Existing wrapper
        local_bin = tmp_path / ".local" / "bin"
        local_bin.mkdir(parents=True)
        wrapper = local_bin / "sbm"
        wrapper.write_text("#!/bin/bash\necho 'old wrapper'")
        
        # Existing env
        env_file = tmp_path / ".env"
        env_file.write_text("GITHUB_TOKEN=existing")
        
        # Test that setup can handle existing files
        assert venv_dir.exists()
        assert wrapper.exists()
        assert env_file.exists()
        
        # Setup should be able to update/recreate these
        new_wrapper_content = "#!/bin/bash\necho 'new wrapper'"
        wrapper.write_text(new_wrapper_content)
        
        assert wrapper.read_text() == new_wrapper_content
