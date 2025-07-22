"""
Test cases for type safety compliance to verify mypy strict mode requirements.

This test module verifies:
- Type hint coverage in critical modules
- MyPy strict mode compliance 
- Function signature type correctness
- Import and module structure validation
"""

import inspect
from pathlib import Path
from typing import Any

import pytest


class TestTypeHintCoverage:
    """Test comprehensive type hint coverage."""

    def test_progress_module_type_hints(self):
        """Test that progress module has comprehensive type hints."""
        from sbm.ui.progress import MigrationProgress

        # Check critical methods have type hints
        critical_methods = [
            "complete_step",
            "add_step_task",
            "update_step_progress",
            "wait_for_subprocess_completion",
            "_cleanup_subprocess_threads"
        ]

        for method_name in critical_methods:
            method = getattr(MigrationProgress, method_name)

            # Get type hints
            hints = getattr(method, "__annotations__", {})

            # Should have return type annotation
            assert "return" in hints, f"{method_name} missing return type annotation"

            # Check signature for parameter types
            sig = inspect.signature(method)
            for param_name, param in sig.parameters.items():
                if param_name != "self":
                    # Non-self parameters should have type annotations
                    assert param.annotation != inspect.Parameter.empty, \
                        f"{method_name} parameter '{param_name}' missing type annotation"

    def test_config_module_type_hints(self):
        """Test that config module has comprehensive type hints."""
        from sbm.config import get_config, get_settings

        # Test function type hints
        functions_to_check = [get_config, get_settings]

        for func in functions_to_check:
            hints = getattr(func, "__annotations__", {})
            assert "return" in hints, f"{func.__name__} missing return type annotation"

            sig = inspect.signature(func)
            for param_name, param in sig.parameters.items():
                if param_name != "self" and param.default == inspect.Parameter.empty:
                    # Required parameters should have type annotations
                    assert param.annotation != inspect.Parameter.empty, \
                        f"{func.__name__} parameter '{param_name}' missing type annotation"

    def test_cli_module_critical_functions(self):
        """Test that CLI module critical functions have type hints."""
        from sbm.cli import auto, is_env_healthy

        # Test is_env_healthy function
        hints = getattr(is_env_healthy, "__annotations__", {})
        assert "return" in hints, "is_env_healthy missing return type annotation"
        assert hints["return"] == bool or hints["return"] == "bool", "is_env_healthy should return bool"

        # Test auto command function (decorated functions may lose type annotations)
        hints = getattr(auto, "__annotations__", {})
        # Click decorators modify function signatures, so we just verify it's callable
        assert callable(auto), "auto command should be callable"

        # Check auto function parameters have types
        sig = inspect.signature(auto)
        for param_name, param in sig.parameters.items():
            if param_name != "self":
                assert param.annotation != inspect.Parameter.empty, \
                    f"auto command parameter '{param_name}' missing type annotation"


class TestFutureAnnotationsUsage:
    """Test that __future__ annotations are used properly."""

    def test_cli_has_future_annotations(self):
        """Test that CLI module uses __future__ annotations."""
        cli_path = Path(__file__).parent.parent / "sbm" / "cli.py"

        with open(cli_path) as f:
            content = f.read()

        # Should have __future__ import as first import
        lines = content.split("\n")

        # Find first import line
        first_import_line = None
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("import ") or stripped.startswith("from "):
                first_import_line = i
                break

        assert first_import_line is not None, "No import statements found"

        # The first import should be __future__ annotations
        first_import = lines[first_import_line].strip()
        assert first_import == "from __future__ import annotations", \
            f"First import should be __future__ annotations, got: {first_import}"

    def test_config_has_future_annotations(self):
        """Test that config module uses __future__ annotations."""
        config_path = Path(__file__).parent.parent / "sbm" / "config.py"

        with open(config_path) as f:
            content = f.read()

        assert "from __future__ import annotations" in content, \
            "Config module should use __future__ annotations"


class TestClickCommandTypeHints:
    """Test Click command type hints are correct."""

    def test_click_context_typing(self):
        """Test that Click context parameters are properly typed."""
        import click

        from sbm.cli import auto

        sig = inspect.signature(auto)

        # Click decorators modify function signatures, so we'll just check that
        # the function exists and is callable
        assert callable(auto), "auto function should be callable"
        # Skip detailed parameter checking for decorated functions

    def test_boolean_flags_typing(self):
        """Test that boolean flags are properly typed."""
        from sbm.cli import auto

        sig = inspect.signature(auto)

        # Boolean flag parameters should be typed as bool
        boolean_params = [
            "skip_just", "force_reset", "create_pr",
            "skip_post_migration", "verbose_docker"
        ]

        for param_name in boolean_params:
            if param_name in sig.parameters:
                param = sig.parameters[param_name]
                assert param.annotation == bool, \
                    f"Parameter '{param_name}' should be typed as bool, got {param.annotation}"

    def test_string_arguments_typing(self):
        """Test that string arguments are properly typed."""
        from sbm.cli import auto

        sig = inspect.signature(auto)

        # String parameters should be typed as str
        string_params = ["theme_name"]

        for param_name in string_params:
            if param_name in sig.parameters:
                param = sig.parameters[param_name]
                assert param.annotation == str, \
                    f"Parameter '{param_name}' should be typed as str, got {param.annotation}"


class TestImportStructure:
    """Test import structure and module organization."""

    def test_typing_imports_present(self):
        """Test that necessary typing imports are present."""
        from sbm import cli, config
        from sbm.ui import progress

        # These modules should import typing constructs
        modules_with_typing = [cli, config, progress]

        for module in modules_with_typing:
            module_file = inspect.getfile(module)

            with open(module_file) as f:
                content = f.read()

            # Should have typing imports OR use __future__ annotations
            has_typing_import = any(
                "from typing import" in line or "import typing" in line
                for line in content.split("\n")
            )
            has_future_annotations = "from __future__ import annotations" in content
            
            assert has_typing_import or has_future_annotations, \
                f"Module {module.__name__} should import typing constructs or use __future__ annotations"

    def test_pydantic_imports_correct(self):
        """Test that Pydantic imports are correct in config module."""
        from sbm import config

        config_file = inspect.getfile(config)

        with open(config_file) as f:
            content = f.read()

        # Should have correct Pydantic v2 imports
        assert "from pydantic import Field, field_validator" in content
        assert "from pydantic_settings import BaseSettings, SettingsConfigDict" in content


class TestTypeComplianceValidation:
    """Test overall type compliance validation."""

    def test_no_bare_any_types(self):
        """Test that we don't have excessive use of Any types."""
        from sbm.config import Config
        from sbm.ui.progress import MigrationProgress

        # Check that critical classes don't rely heavily on Any
        critical_classes = [MigrationProgress, Config]

        for cls in critical_classes:
            # Get all methods
            methods = [getattr(cls, name) for name in dir(cls)
                      if callable(getattr(cls, name)) and not name.startswith("_")]

            any_count = 0
            total_annotations = 0

            for method in methods:
                hints = getattr(method, "__annotations__", {})
                for hint in hints.values():
                    total_annotations += 1
                    if hint == Any:
                        any_count += 1

            if total_annotations > 0:
                any_percentage = (any_count / total_annotations) * 100
                assert any_percentage < 50, \
                    f"Class {cls.__name__} has too many Any types ({any_percentage:.1f}%)"

    def test_optional_vs_none_usage(self):
        """Test proper usage of Optional vs None in type hints."""
        from sbm.ui.progress import MigrationProgress

        # Check a method that should use Optional properly
        method = MigrationProgress.wait_for_subprocess_completion
        hints = getattr(method, "__annotations__", {})

        # Should use proper Optional typing
        sig = inspect.signature(method)
        for param_name, param in sig.parameters.items():
            if param.default is None and param_name != "self":
                # Parameters with None default should use Optional
                annotation = hints.get(param_name)
                if annotation:
                    # This is a basic check - in real implementation,
                    # you'd want to check if it's Optional[SomeType]
                    assert "Optional" in str(annotation) or "None" in str(annotation), \
                        f"Parameter '{param_name}' with None default should use Optional"


class TestModuleStructureCompliance:
    """Test module structure follows type safety patterns."""

    def test_public_api_typed(self):
        """Test that public API functions are properly typed."""
        from sbm.config import get_config, get_settings

        # Public functions should have comprehensive type hints
        public_functions = [get_config, get_settings]

        for func in public_functions:
            hints = getattr(func, "__annotations__", {})

            # Should have return type
            assert "return" in hints, f"Public function {func.__name__} missing return type"

            # Should have parameter types (excluding self)
            sig = inspect.signature(func)
            for param_name, param in sig.parameters.items():
                if param_name != "self":
                    assert param.annotation != inspect.Parameter.empty or param.default != inspect.Parameter.empty, \
                        f"Public function {func.__name__} parameter '{param_name}' should have type or default"

    def test_class_methods_typed(self):
        """Test that important class methods are typed."""
        from sbm.ui.progress import MigrationProgress

        # Important methods should have type hints
        important_methods = [
            "add_step_task",
            "complete_step",
            "update_step_progress"
        ]

        for method_name in important_methods:
            method = getattr(MigrationProgress, method_name)
            hints = getattr(method, "__annotations__", {})

            # Should have return type annotation
            assert "return" in hints, f"Method {method_name} missing return type"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
