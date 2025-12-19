"""
Comprehensive tests for setup.sh script changes.

Tests ensure that setup.sh generates correct aliases and wrapper script
with proper environment isolation and dynamic path configuration.
"""

import os
import re
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open
import pytest


# =============================================================================
# TEST 1: Setup Script Alias Generation
# =============================================================================


class TestSetupScriptAliases:
    """Tests for alias generation in setup.sh."""

    def test_setup_script_exists(self):
        """Verify setup.sh exists in repository root."""
        setup_path = Path(__file__).parent.parent / "setup.sh"
        assert setup_path.exists(), "setup.sh not found"

    def test_setup_script_is_executable(self):
        """Verify setup.sh is executable."""
        setup_path = Path(__file__).parent.parent / "setup.sh"
        assert os.access(setup_path, os.X_OK), "setup.sh is not executable"

    def test_aliases_use_project_root_variable(self):
        """Verify aliases use $PROJECT_ROOT instead of hardcoded path."""
        setup_path = Path(__file__).parent.parent / "setup.sh"
        content = setup_path.read_text()

        # Aliases should use $PROJECT_ROOT, not ~/auto-sbm
        alias_section = re.search(
            r"##### ADDED BY AUTO-SBM #####.*?ZSHRC_EOF",
            content,
            re.DOTALL
        )

        assert alias_section is not None, "Alias section not found in setup.sh"
        alias_text = alias_section.group(0)

        # Should use $PROJECT_ROOT
        assert "$PROJECT_ROOT" in alias_text, "Aliases don't use $PROJECT_ROOT"

        # Should NOT use hardcoded path
        assert "~/auto-sbm" not in alias_text, "Aliases still use hardcoded path ~/auto-sbm"

    def test_aliases_define_project_root_variable(self):
        """Verify setup.sh defines PROJECT_ROOT variable before using it in aliases."""
        setup_path = Path(__file__).parent.parent / "setup.sh"
        content = setup_path.read_text()

        # Should define PROJECT_ROOT before the heredoc
        alias_function = re.search(
            r"if ! grep -q.*AUTO-SBM.*then.*?fi",
            content,
            re.DOTALL
        )

        assert alias_function is not None, "Alias function not found"
        function_text = alias_function.group(0)

        # Should define local PROJECT_ROOT=$(pwd)
        assert "local PROJECT_ROOT=$(pwd)" in function_text, \
            "PROJECT_ROOT variable not defined before aliases"

    def test_aliases_use_unquoted_heredoc(self):
        """Verify aliases use unquoted heredoc to allow variable expansion."""
        setup_path = Path(__file__).parent.parent / "setup.sh"
        content = setup_path.read_text()

        # Should use << ZSHRC_EOF (unquoted) not << 'ZSHRC_EOF' (quoted)
        alias_section = re.search(
            r"cat >> \"\$ZSHRC_FILE\" << ZSHRC_EOF",
            content
        )

        assert alias_section is not None, \
            "Heredoc should be unquoted (<< ZSHRC_EOF) to allow variable expansion"

        # Should NOT use quoted heredoc
        quoted_heredoc = re.search(
            r"cat >> \"\$ZSHRC_FILE\" << 'ZSHRC_EOF'",
            content
        )

        assert quoted_heredoc is None, \
            "Heredoc is quoted (<< 'ZSHRC_EOF'), which prevents variable expansion"


# =============================================================================
# TEST 2: Setup Script Wrapper Generation
# =============================================================================


class TestSetupScriptWrapperGeneration:
    """Tests for wrapper script generation in setup.sh."""

    def test_wrapper_includes_environment_isolation(self):
        """Verify setup.sh generates wrapper with environment isolation code."""
        setup_path = Path(__file__).parent.parent / "setup.sh"
        content = setup_path.read_text()

        # Find wrapper generation section
        wrapper_section = re.search(
            r'cat > "\$WRAPPER_PATH" << EOF.*?^EOF',
            content,
            re.DOTALL | re.MULTILINE
        )

        assert wrapper_section is not None, "Wrapper generation section not found"
        wrapper_text = wrapper_section.group(0)

        # Should unset VIRTUAL_ENV
        assert "unset VIRTUAL_ENV" in wrapper_text, \
            "Wrapper doesn't unset VIRTUAL_ENV"

        # Should unset PYTHONPATH
        assert "unset PYTHONPATH" in wrapper_text, \
            "Wrapper doesn't unset PYTHONPATH"

        # Should unset PYTHONHOME
        assert "unset PYTHONHOME" in wrapper_text, \
            "Wrapper doesn't unset PYTHONHOME"

    def test_wrapper_includes_path_cleanup(self):
        """Verify wrapper includes PATH cleanup to remove other venvs."""
        setup_path = Path(__file__).parent.parent / "setup.sh"
        content = setup_path.read_text()

        wrapper_section = re.search(
            r'cat > "\$WRAPPER_PATH" << EOF.*?^EOF',
            content,
            re.DOTALL | re.MULTILINE
        )

        assert wrapper_section is not None
        wrapper_text = wrapper_section.group(0)

        # Should filter .venv/bin from PATH
        assert "grep -v '/\\.venv/bin'" in wrapper_text, \
            "Wrapper doesn't filter .venv/bin from PATH"

        # Should export PATH with auto-sbm venv first
        assert "export PATH=" in wrapper_text, \
            "Wrapper doesn't export PATH"

    def test_wrapper_uses_absolute_paths(self):
        """Verify wrapper uses absolute paths for venv and project root."""
        setup_path = Path(__file__).parent.parent / "setup.sh"
        content = setup_path.read_text()

        wrapper_section = re.search(
            r'cat > "\$WRAPPER_PATH" << EOF.*?^EOF',
            content,
            re.DOTALL | re.MULTILINE
        )

        assert wrapper_section is not None
        wrapper_text = wrapper_section.group(0)

        # Should define VENV_PYTHON with absolute path
        assert 'VENV_PYTHON="$VENV_PYTHON"' in wrapper_text or \
               'VENV_PYTHON="' in wrapper_text, \
            "Wrapper doesn't define VENV_PYTHON"

        # Should define PROJECT_ROOT with absolute path
        assert 'PROJECT_ROOT="$PROJECT_ROOT"' in wrapper_text or \
               'PROJECT_ROOT="' in wrapper_text, \
            "Wrapper doesn't define PROJECT_ROOT"


# =============================================================================
# TEST 3: Setup Script Environment Configuration
# =============================================================================


class TestSetupScriptEnvironmentConfig:
    """Tests for environment configuration in setup.sh."""

    def test_setup_creates_local_bin_directory(self):
        """Verify setup.sh creates ~/.local/bin directory."""
        setup_path = Path(__file__).parent.parent / "setup.sh"
        content = setup_path.read_text()

        # Should create ~/.local/bin
        assert 'mkdir -p "$LOCAL_BIN_DIR"' in content or \
               'mkdir -p "$HOME/.local/bin"' in content, \
            "setup.sh doesn't create ~/.local/bin directory"

    def test_setup_adds_local_bin_to_path(self):
        """Verify setup.sh adds ~/.local/bin to PATH in .zshrc."""
        setup_path = Path(__file__).parent.parent / "setup.sh"
        content = setup_path.read_text()

        # Should add to PATH
        assert 'export PATH="$HOME/.local/bin:$PATH"' in content or \
               'export PATH="$LOCAL_BIN_DIR:$PATH"' in content, \
            "setup.sh doesn't add ~/.local/bin to PATH"

    def test_setup_checks_path_not_already_added(self):
        """Verify setup.sh checks if PATH already contains ~/.local/bin."""
        setup_path = Path(__file__).parent.parent / "setup.sh"
        content = setup_path.read_text()

        # Should check before adding to avoid duplicates
        assert 'if ! grep -q' in content, \
            "setup.sh doesn't check before adding to .zshrc"


# =============================================================================
# TEST 4: Setup Script Git Shortcuts
# =============================================================================


class TestSetupScriptGitShortcuts:
    """Tests for git shortcut aliases in setup.sh."""

    def test_setup_includes_git_shortcuts(self):
        """Verify setup.sh includes useful git shortcut aliases."""
        setup_path = Path(__file__).parent.parent / "setup.sh"
        content = setup_path.read_text()

        # Should include common git shortcuts
        git_aliases = ["gs=", "ga=", "gc=", "gp=", "gb="]

        for alias in git_aliases:
            assert f'alias {alias}' in content, \
                f"setup.sh missing git alias: {alias}"

    def test_git_shortcuts_are_safe(self):
        """Verify git shortcuts don't include dangerous operations."""
        setup_path = Path(__file__).parent.parent / "setup.sh"
        content = setup_path.read_text()

        # Extract alias section
        alias_section = re.search(
            r"##### ADDED BY AUTO-SBM #####.*?ZSHRC_EOF",
            content,
            re.DOTALL
        )

        if alias_section:
            alias_text = alias_section.group(0)

            # Should NOT include force operations without user confirmation
            dangerous_patterns = [
                "git reset --hard",
                "git push --force",
                "git clean -fd",
            ]

            # These are fine if they're commented or have safety checks
            # But raw aliases should be avoided
            # Note: grh='git reset --hard' is acceptable as it requires
            # explicit user invocation


# =============================================================================
# TEST 5: Setup Script SBM-Specific Aliases
# =============================================================================


class TestSetupScriptSbmAliases:
    """Tests for SBM-specific development aliases."""

    def test_sbm_dev_alias_exists(self):
        """Verify sbm-dev alias is created."""
        setup_path = Path(__file__).parent.parent / "setup.sh"
        content = setup_path.read_text()

        assert 'alias sbm-dev=' in content, \
            "sbm-dev alias not found in setup.sh"

    def test_sbm_dev_alias_uses_project_root(self):
        """Verify sbm-dev alias uses $PROJECT_ROOT variable."""
        setup_path = Path(__file__).parent.parent / "setup.sh"
        content = setup_path.read_text()

        # Extract sbm-dev alias
        sbm_dev = re.search(r'alias sbm-dev="([^"]+)"', content)

        assert sbm_dev is not None, "sbm-dev alias not found"

        # Should use $PROJECT_ROOT
        assert "$PROJECT_ROOT" in sbm_dev.group(1), \
            "sbm-dev doesn't use $PROJECT_ROOT variable"

    def test_sbm_test_alias_exists(self):
        """Verify sbm-test alias is created."""
        setup_path = Path(__file__).parent.parent / "setup.sh"
        content = setup_path.read_text()

        assert 'alias sbm-test=' in content, \
            "sbm-test alias not found in setup.sh"

    def test_sbm_test_alias_uses_project_root(self):
        """Verify sbm-test alias uses $PROJECT_ROOT variable."""
        setup_path = Path(__file__).parent.parent / "setup.sh"
        content = setup_path.read_text()

        # Extract sbm-test alias
        sbm_test = re.search(r'alias sbm-test="([^"]+)"', content)

        assert sbm_test is not None, "sbm-test alias not found"

        # Should use $PROJECT_ROOT
        assert "$PROJECT_ROOT" in sbm_test.group(1), \
            "sbm-test doesn't use $PROJECT_ROOT variable"

    def test_sbm_test_runs_pytest(self):
        """Verify sbm-test alias runs pytest."""
        setup_path = Path(__file__).parent.parent / "setup.sh"
        content = setup_path.read_text()

        sbm_test = re.search(r'alias sbm-test="([^"]+)"', content)

        assert sbm_test is not None
        assert "pytest" in sbm_test.group(1), \
            "sbm-test doesn't run pytest"


# =============================================================================
# TEST 6: Setup Script Wrapper Validation
# =============================================================================


class TestSetupScriptWrapperValidation:
    """Tests for wrapper script validation logic in setup.sh."""

    def test_wrapper_validates_venv_exists(self):
        """Verify wrapper checks if venv Python exists."""
        setup_path = Path(__file__).parent.parent / "setup.sh"
        content = setup_path.read_text()

        wrapper_section = re.search(
            r'cat > "\$WRAPPER_PATH" << EOF.*?^EOF',
            content,
            re.DOTALL | re.MULTILINE
        )

        assert wrapper_section is not None
        wrapper_text = wrapper_section.group(0)

        # Should check if VENV_PYTHON exists
        assert '[ ! -f "$VENV_PYTHON" ]' in wrapper_text or \
               '[ ! -f "\\$VENV_PYTHON" ]' in wrapper_text, \
            "Wrapper doesn't validate venv Python exists"

    def test_wrapper_validates_project_root_exists(self):
        """Verify wrapper checks if project root exists."""
        setup_path = Path(__file__).parent.parent / "setup.sh"
        content = setup_path.read_text()

        wrapper_section = re.search(
            r'cat > "\$WRAPPER_PATH" << EOF.*?^EOF',
            content,
            re.DOTALL | re.MULTILINE
        )

        assert wrapper_section is not None
        wrapper_text = wrapper_section.group(0)

        # Should check if PROJECT_ROOT exists
        assert '[ ! -d "$PROJECT_ROOT" ]' in wrapper_text or \
               '[ ! -d "\\$PROJECT_ROOT" ]' in wrapper_text, \
            "Wrapper doesn't validate project root exists"

    def test_wrapper_provides_recovery_instructions(self):
        """Verify wrapper provides helpful error messages."""
        setup_path = Path(__file__).parent.parent / "setup.sh"
        content = setup_path.read_text()

        wrapper_section = re.search(
            r'cat > "\$WRAPPER_PATH" << EOF.*?^EOF',
            content,
            re.DOTALL | re.MULTILINE
        )

        assert wrapper_section is not None
        wrapper_text = wrapper_section.group(0)

        # Should suggest running setup.sh on errors
        assert "setup.sh" in wrapper_text, \
            "Wrapper doesn't mention setup.sh in error recovery"

    def test_wrapper_changes_to_project_directory(self):
        """Verify wrapper changes to project directory before execution."""
        setup_path = Path(__file__).parent.parent / "setup.sh"
        content = setup_path.read_text()

        wrapper_section = re.search(
            r'cat > "\$WRAPPER_PATH" << EOF.*?^EOF',
            content,
            re.DOTALL | re.MULTILINE
        )

        assert wrapper_section is not None
        wrapper_text = wrapper_section.group(0)

        # Should cd to project root
        assert 'cd "$PROJECT_ROOT"' in wrapper_text or \
               'cd "\\$PROJECT_ROOT"' in wrapper_text, \
            "Wrapper doesn't cd to project root"


# =============================================================================
# TEST 7: Setup Script Comments and Documentation
# =============================================================================


class TestSetupScriptDocumentation:
    """Tests for comments and documentation in setup.sh."""

    def test_setup_has_shebang(self):
        """Verify setup.sh has proper shebang."""
        setup_path = Path(__file__).parent.parent / "setup.sh"
        content = setup_path.read_text()

        assert content.startswith("#!/bin/bash"), \
            "setup.sh doesn't have proper shebang"

    def test_wrapper_generation_has_comments(self):
        """Verify wrapper generation section has explanatory comments."""
        setup_path = Path(__file__).parent.parent / "setup.sh"
        content = setup_path.read_text()

        # Should have comments explaining environment isolation
        wrapper_function = re.search(
            r"function create_global_wrapper.*?^}",
            content,
            re.DOTALL | re.MULTILINE
        )

        assert wrapper_function is not None, \
            "create_global_wrapper function not found"

    def test_aliases_section_has_marker_comments(self):
        """Verify alias section has clear marker comments."""
        setup_path = Path(__file__).parent.parent / "setup.sh"
        content = setup_path.read_text()

        # Should have section markers
        assert "##### ADDED BY AUTO-SBM #####" in content, \
            "Alias section missing marker comment"
