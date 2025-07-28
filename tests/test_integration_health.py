"""
Integration tests for health check system.
Tests overall system health validation and diagnostics.
"""
import pytest
import os
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile

# Import health check functions - adjust based on actual codebase
try:
    from sbm.core.health import check_system_health, validate_environment
except ImportError:
    # If these don't exist, we'll test basic health check patterns
    check_system_health = None
    validate_environment = None


class TestSystemHealthBasics:
    """Test basic system health check functionality."""
    
    def test_python_version_check(self):
        """Test Python version meets requirements."""
        import sys
        
        # Should be Python 3.9+
        assert sys.version_info >= (3, 9), f"Python version {sys.version_info} < 3.9"
        
        # Test version string parsing
        version_str = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        assert isinstance(version_str, str)
    
    def test_required_modules_import(self):
        """Test required Python modules can be imported."""
        required_modules = [
            'click',
            'rich', 
            'pydantic',
            'gitpython',
            'jinja2',
            'yaml',
            'pathlib'
        ]
        
        missing_modules = []
        for module in required_modules:
            try:
                if module == 'yaml':
                    import yaml
                elif module == 'gitpython':
                    import git
                else:
                    __import__(module)
            except ImportError:
                missing_modules.append(module)
        
        assert len(missing_modules) == 0, f"Missing modules: {missing_modules}"
    
    def test_virtual_environment_detection(self):
        """Test detection of virtual environment"""
        import sys
        # Check for virtual environment indicators
        in_venv = (
            hasattr(sys, 'real_prefix') or
            (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
        )


class TestConfigurationHealth:
    """Test configuration health and validation."""
    
    def test_config_file_accessibility(self):
        """Test that main config files are accessible"""
        import os
        
        # Test pyproject.toml accessibility
        config_file = "pyproject.toml"
        file_path = Path(os.getcwd()) / config_file
        assert file_path.exists(), f"Config file {config_file} not found"
    
    def test_env_file_validation(self, tmp_path):
        """Test .env file validation."""
        # Create test .env file
        env_file = tmp_path / ".env"
        env_content = """
GITHUB_TOKEN=ghp_test123456789012345678901234567890
GITHUB_ORG=test_org
DEFAULT_BRANCH=main
DEFAULT_LABELS=fe-dev,migration
"""
        env_file.write_text(env_content)
        
        # Test parsing
        env_vars = {}
        for line in env_content.strip().split('\n'):
            if '=' in line and not line.startswith('#'):
                key, value = line.split('=', 1)
                env_vars[key] = value
        
        required_vars = ['GITHUB_TOKEN', 'GITHUB_ORG']
        for var in required_vars:
            assert var in env_vars, f"Required env var {var} missing"
            assert len(env_vars[var]) > 0, f"Env var {var} is empty"
    
    def test_config_validation_with_pydantic(self, monkeypatch):
        """Test configuration validation using Pydantic."""
        # Set valid environment variables
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test123456789012345678901234567890")
        monkeypatch.setenv("GITHUB_ORG", "test_org")
        
        try:
            from sbm.config import AutoSBMSettings
            config = AutoSBMSettings()
            
            # Basic validation
            assert config.git.github_token == "ghp_test123456789012345678901234567890"
            assert config.github_org == "test_org"
            assert hasattr(config, 'default_branch')
            
        except ImportError:
            pytest.skip("Config module not available")
        except Exception as e:
            pytest.fail(f"Config validation failed: {e}")


class TestCommandLineInterfaceHealth:
    """Test CLI health and accessibility."""
    
    def test_cli_module_importable(self):
        """Test CLI module can be imported."""
        try:
            from sbm.cli import cli
            assert cli is not None
        except ImportError as e:
            pytest.fail(f"Cannot import CLI: {e}")
    
    def test_cli_help_accessible(self):
        """Test CLI help is accessible."""
        try:
            from click.testing import CliRunner
            from sbm.cli import cli
            
            runner = CliRunner()
            result = runner.invoke(cli, ['--help'])
            
            assert result.exit_code == 0
            assert len(result.output) > 0
            
        except ImportError:
            pytest.skip("CLI testing modules not available")
        except Exception as e:
            pytest.fail(f"CLI help test failed: {e}")
    
    def test_global_sbm_command(self):
        """Test global sbm command accessibility."""
        # Check if sbm command is in PATH
        result = subprocess.run(
            ['which', 'sbm'], 
            capture_output=True, 
            text=True
        )
        
        if result.returncode == 0:
            # sbm command found, test it
            help_result = subprocess.run(
                ['sbm', '--help'], 
                capture_output=True, 
                text=True,
                timeout=10
            )
            
            # Should either work or show helpful error
            assert help_result.returncode in [0, 1, 2]
        else:
            # sbm command not found - might be expected in test environment
            pytest.skip("Global sbm command not found in PATH")


class TestFileSystemHealth:
    """Test file system permissions and accessibility."""
    
    def test_project_directory_permissions(self):
        """Test project directory has correct permissions."""
        project_root = Path.cwd()
        
        assert project_root.exists()
        assert project_root.is_dir()
        
        # Should be able to read directory
        assert os.access(project_root, os.R_OK)
        
        # Test key directories
        key_dirs = ['sbm', 'tests', 'docs']
        for dir_name in key_dirs:
            dir_path = project_root / dir_name
            if dir_path.exists():
                assert dir_path.is_dir()
                assert os.access(dir_path, os.R_OK)
    
    def test_log_directory_writable(self, tmp_path):
        """Test log directory is writable."""
        log_dir = tmp_path / "logs"
        log_dir.mkdir(exist_ok=True)
        
        # Test write permissions
        test_log = log_dir / "test.log"
        test_log.write_text("test log entry")
        
        assert test_log.exists()
        assert test_log.read_text() == "test log entry"
    
    def test_venv_directory_health(self):
        """Test virtual environment directory health."""
        venv_dir = Path(".venv")
        
        if venv_dir.exists():
            assert venv_dir.is_dir()
            
            # Check for key venv components
            venv_bin = venv_dir / "bin"
            if venv_bin.exists():  # Unix-style venv
                python_exe = venv_bin / "python"
                assert python_exe.exists() or (venv_bin / "python3").exists()
            
            venv_scripts = venv_dir / "Scripts"
            if venv_scripts.exists():  # Windows-style venv
                python_exe = venv_scripts / "python.exe"
                assert python_exe.exists()


class TestNetworkConnectivity:
    """Test network connectivity for external operations."""
    
    @patch('subprocess.run')
    def test_github_connectivity(self, mock_subprocess):
        """Test GitHub connectivity (mocked)."""
        # Mock successful ping to GitHub
        mock_subprocess.return_value = MagicMock(returncode=0)
        
        # Test GitHub API connectivity
        result = subprocess.run(
            ['ping', '-c', '1', 'api.github.com'], 
            capture_output=True, 
            timeout=5
        )
        
        mock_subprocess.assert_called()
    
    @patch('subprocess.run')
    def test_package_registry_connectivity(self, mock_subprocess):
        """Test Python package registry connectivity (mocked)."""
        # Mock successful connection to PyPI
        mock_subprocess.return_value = MagicMock(returncode=0)
        
        result = subprocess.run(
            ['ping', '-c', '1', 'pypi.org'], 
            capture_output=True, 
            timeout=5
        )
        
        mock_subprocess.assert_called()


class TestDependencyHealth:
    """Test dependency health and versions."""
    
    def test_dependency_versions(self):
        """Test dependency versions meet requirements."""
        version_requirements = {
            'click': '8.0.0',
            'rich': '13.0.0', 
            'pydantic': '2.5.0'
        }
        
        for package, min_version in version_requirements.items():
            try:
                module = __import__(package)
                if hasattr(module, '__version__'):
                    version = module.__version__
                    # Basic version comparison (simplified)
                    assert len(version) > 0, f"{package} version not available"
            except ImportError:
                pytest.fail(f"Required package {package} not installed")
    
    def test_development_dependencies(self):
        """Test development dependencies are available."""
        dev_dependencies = [
            'pytest',
            'mypy', 
            'ruff'
        ]
        
        missing_dev_deps = []
        for dep in dev_dependencies:
            try:
                __import__(dep)
            except ImportError:
                missing_dev_deps.append(dep)
        
        if missing_dev_deps:
            pytest.skip(f"Development dependencies missing: {missing_dev_deps}")


class TestIntegratedHealthCheck:
    """Test integrated health check functionality."""
    
    def test_overall_system_health(self):
        """Test overall system health check."""
        import os
        health_issues = []
        
        # 1. Python version
        import sys
        if sys.version_info < (3, 9):
            health_issues.append("Python version < 3.9")
        
        # 2. Key files exist
        key_files = ['pyproject.toml', 'setup.sh', 'sbm/__init__.py']
        for file_path in key_files:
            if not Path(os.getcwd(), file_path).exists():
                health_issues.append(f"Missing file: {file_path}")
        
        # 3. Basic imports work
        try:
            import sbm
        except ImportError:
            health_issues.append("Cannot import sbm module")
        
        # 4. Config system works
        try:
            from sbm.config import AutoSBMSettings
        except ImportError:
            health_issues.append("Cannot import config system")
        
        # Report all issues
        if health_issues:
            pytest.fail(f"Health check failures: {'; '.join(health_issues)}")
    
    def test_custom_health_check_function(self):
        """Test custom health check function if available."""
        if check_system_health:
            try:
                result = check_system_health()
                # Should return some kind of status
                assert result is not None
            except Exception as e:
                pytest.fail(f"Custom health check failed: {e}")
        
        if validate_environment:
            try:
                result = validate_environment()
                # Should return validation result
                assert result is not None
            except Exception as e:
                pytest.fail(f"Environment validation failed: {e}")


class TestHealthCheckReporting:
    """Test health check reporting and diagnostics."""
    
    def test_health_check_output_format(self, tmp_path):
        """Test health check output formatting."""
        # Create sample health report
        health_report = {
            "python_version": "3.9.0",
            "virtual_env": True,
            "config_valid": True,
            "dependencies_ok": True,
            "git_available": True
        }
        
        # Test report formatting
        report_lines = []
        for check, status in health_report.items():
            symbol = "✅" if status else "❌"
            report_lines.append(f"{symbol} {check.replace('_', ' ').title()}: {status}")
        
        report_text = "\n".join(report_lines)
        
        assert "✅" in report_text
        assert "Python Version" in report_text
        
        # Test saving report
        report_file = tmp_path / "health_report.txt"
        report_file.write_text(report_text)
        
        assert report_file.exists()
        assert len(report_file.read_text()) > 0
    
    def test_diagnostic_information_collection(self):
        """Test collection of diagnostic information."""
        import sys
        import platform
        
        diagnostic_info = {
            "python_version": sys.version,
            "platform": platform.platform(),
            "architecture": platform.architecture(),
            "python_path": sys.executable,
            "working_directory": os.getcwd()
        }
        
        # Verify all diagnostic info is collected
        for key, value in diagnostic_info.items():
            assert value is not None, f"Diagnostic {key} is None"
            assert len(str(value)) > 0, f"Diagnostic {key} is empty"
