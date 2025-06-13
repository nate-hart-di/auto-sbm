"""
Pytest configuration and shared fixtures for SBM Tool V2 tests.
"""

import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch
from typing import Dict, Any

import pytest

from sbm.config import Config, reset_config
from sbm.utils.logger import reset_loggers


@pytest.fixture(autouse=True)
def reset_globals():
    """Reset global state before each test."""
    reset_config()
    reset_loggers()
    yield
    reset_config()
    reset_loggers()


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def mock_di_platform(temp_dir):
    """Create a mock DI platform directory structure."""
    platform_dir = temp_dir / "di-platform"
    platform_dir.mkdir()
    
    # Create dealer-themes directory
    dealer_themes_dir = platform_dir / "dealer-themes"
    dealer_themes_dir.mkdir()
    
    # Create common theme directory
    common_theme_dir = platform_dir / "app" / "dealer-inspire" / "wp-content" / "themes" / "DealerInspireCommonTheme"
    common_theme_dir.mkdir(parents=True)
    
    # Create test dealer themes
    test_dealers = [
        "chryslerofportland",
        "dodgeofseattle", 
        "jeepnorthwest",
        "ramofportland",
        "fiatofseattle",
        "cdjrportland"
    ]
    
    for dealer in test_dealers:
        dealer_dir = dealer_themes_dir / dealer
        dealer_dir.mkdir()
        
        # Create basic theme files
        (dealer_dir / "style.css").write_text("/* Basic theme styles */")
        (dealer_dir / "functions.php").write_text("<?php // Theme functions")
        
        # Create legacy SCSS files
        (dealer_dir / "lvdp.scss").write_text("$primary: #ff0000; .vdp { color: $primary; }")
        (dealer_dir / "lvrp.scss").write_text("$secondary: #00ff00; .vrp { color: $secondary; }")
    
    return platform_dir


@pytest.fixture
def mock_env_vars(mock_di_platform):
    """Mock environment variables for testing."""
    env_vars = {
        "DI_PLATFORM_DIR": str(mock_di_platform),
        "CONTEXT7_SERVER_URL": "http://localhost:3001",
        "CONTEXT7_API_KEY": "test_api_key",
        "CONTEXT7_TIMEOUT": "30",
        "GIT_USER_NAME": "Test User",
        "GIT_USER_EMAIL": "test@example.com",
        "GIT_DEFAULT_BRANCH": "main",
        "GITHUB_TOKEN": "test_token",
        "GITHUB_ORG": "carsdotcom",
        "GITHUB_REPO": "di-websites-platform",
        "SBM_DEFAULT_REVIEWERS": "reviewer1,reviewer2",
        "SBM_DEFAULT_LABELS": "sbm,migration",
        "STELLANTIS_ENHANCED_MODE": "true",
        "STELLANTIS_BRAND_DETECTION": "auto",
        "STELLANTIS_MAP_PROCESSING": "true",
        "LOG_LEVEL": "DEBUG"
    }
    
    with patch.dict(os.environ, env_vars, clear=False):
        yield env_vars


@pytest.fixture
def test_config(mock_env_vars):
    """Create a test configuration instance."""
    return Config()


@pytest.fixture
def mock_git_repo(temp_dir):
    """Create a mock git repository."""
    git_dir = temp_dir / ".git"
    git_dir.mkdir()
    
    # Create basic git files
    (git_dir / "HEAD").write_text("ref: refs/heads/main\n")
    (git_dir / "config").write_text("[core]\n\trepositoryformatversion = 0\n")
    
    refs_dir = git_dir / "refs" / "heads"
    refs_dir.mkdir(parents=True)
    (refs_dir / "main").write_text("abc123def456\n")
    
    return temp_dir


@pytest.fixture
def mock_subprocess():
    """Mock subprocess calls."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "Success"
        mock_run.return_value.stderr = ""
        yield mock_run


@pytest.fixture
def mock_context7_client():
    """Mock Context7 client for testing."""
    with patch('sbm.scss.context7.Context7Client') as mock_client:
        mock_instance = Mock()
        mock_instance.test_connection.return_value = True
        mock_instance.transform_scss.return_value = "/* transformed css */"
        mock_client.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def sample_scss_content():
    """Sample SCSS content for testing transformations."""
    return """
$primary-color: #ff0000;
$secondary-color: #00ff00;

@mixin flexbox() {
    display: -webkit-box;
    display: -moz-box;
    display: -ms-flexbox;
    display: -webkit-flex;
    display: flex;
}

.header {
    color: $primary-color;
    @include flexbox();
    
    .logo {
        background: url('../images/logo.png');
    }
}

.content {
    color: $secondary-color;
    @include flexbox();
}
"""


@pytest.fixture
def sample_migration_result():
    """Sample migration result for testing."""
    return {
        'success': True,
        'slug': 'chryslerofportland',
        'files_created': 4,
        'styles_migrated': 15,
        'map_components': 2,
        'oem': 'Stellantis',
        'brand': 'Chrysler',
        'duration': 45.2,
        'steps_completed': [
            'theme_validation',
            'oem_detection', 
            'git_setup',
            'site_initialization',
            'core_migration',
            'validation',
            'git_commit'
        ],
        'branch_name': 'chryslerofportland-sbm1224',
        'validation_results': {
            'scss_syntax': {'passed': True, 'message': 'All SCSS files valid'},
            'file_structure': {'passed': True, 'message': 'All required files present'},
            'theme_integrity': {'passed': True, 'message': 'Theme structure intact'}
        }
    }


@pytest.fixture
def stellantis_test_cases():
    """Test cases for Stellantis brand detection."""
    return {
        'chrysler': [
            'chryslerofportland',
            'chryslerseattle',
            'chrysler-downtown'
        ],
        'dodge': [
            'dodgeofseattle',
            'dodgeperformance',
            'dodge-northwest'
        ],
        'jeep': [
            'jeepofportland',
            'jeepnorthwest',
            'jeep-adventure'
        ],
        'ram': [
            'ramofportland',
            'ramtrucksseattle',
            'ram-power'
        ],
        'fiat': [
            'fiatofportland',
            'fiatseattle',
            'fiat-european'
        ],
        'cdjr': [
            'cdjrportland',
            'cdjrnorthwest',
            'chryslerdodgejeepram'
        ],
        'fca': [
            'fcaportland',
            'fcaof',
            'fiat-chrysler'
        ]
    }


@pytest.fixture
def cli_runner():
    """Click CLI test runner."""
    from click.testing import CliRunner
    return CliRunner()


@pytest.fixture
def mock_logger():
    """Mock logger for testing."""
    with patch('sbm.utils.logger.get_logger') as mock_get_logger:
        mock_logger_instance = Mock()
        mock_get_logger.return_value = mock_logger_instance
        yield mock_logger_instance 
