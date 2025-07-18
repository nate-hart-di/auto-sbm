"""SCSS Validation Module

This module provides comprehensive SCSS validation with improved type safety,
replacing the basic validation in the legacy validator.py.
"""

import logging
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .exceptions import ScssCompilationException
from .models import ScssProcessingError, ScssValidationResult

logger = logging.getLogger(__name__)


class ScssValidator:
    """
    Comprehensive SCSS validator with syntax checking and compilation testing.
    
    Provides both basic syntax validation and advanced compilation testing
    to ensure SCSS content is valid and will compile correctly.
    """

    def __init__(self):
        self._compiled_patterns = self._compile_validation_patterns()
        self._sass_available = self._check_sass_availability()
        logger.info(f"SCSS Validator initialized (Sass available: {self._sass_available})")

    def _compile_validation_patterns(self) -> Dict[str, re.Pattern]:
        """Pre-compile regex patterns for better performance"""
        return {
            "scss_variable": re.compile(r"\$[a-zA-Z][\w-]*"),
            "scss_mixin_include": re.compile(r"@include\s+[\w-]+"),
            "scss_mixin_definition": re.compile(r"@mixin\s+[\w-]+"),
            "scss_function": re.compile(r"(lighten|darken|mix|rgba|hsla)\s*\("),
            "scss_import": re.compile(r'@import\s+["\']?[^"\';\s]+["\']?\s*;'),
            "css_property": re.compile(r"^\s*[\w-]+\s*:\s*[^;]+;", re.MULTILINE),
            "selector": re.compile(r"^[^{}]*\{", re.MULTILINE),
            "comment_block": re.compile(r"/\*.*?\*/", re.DOTALL),
            "comment_line": re.compile(r"//.*$", re.MULTILINE),
            "interpolation": re.compile(r"#\{[^}]*\}"),
            "nested_selector": re.compile(r"&[\w\s.:>#-]*")
        }

    def _check_sass_availability(self) -> bool:
        """Check if Sass compiler is available"""
        try:
            result = subprocess.run(
                ["sass", "--version"],
                check=False, capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    async def validate_scss_content(
        self,
        content: str,
        test_compilation: bool = True
    ) -> ScssValidationResult:
        """
        Comprehensive SCSS content validation.
        
        Args:
            content: SCSS content to validate
            test_compilation: Whether to test actual compilation
            
        Returns:
            ScssValidationResult with detailed validation information
        """
        try:
            errors: List[ScssProcessingError] = []
            warnings: List[ScssProcessingError] = []

            # Basic validation checks
            syntax_checks = self._validate_basic_syntax(content)
            errors.extend(syntax_checks["errors"])
            warnings.extend(syntax_checks["warnings"])

            # Advanced validation
            advanced_checks = self._validate_advanced_syntax(content)
            errors.extend(advanced_checks["errors"])
            warnings.extend(advanced_checks["warnings"])

            # Compilation testing
            compilation_result = None
            compilation_time = None

            if test_compilation and self._sass_available:
                try:
                    compilation_result, compilation_time = await self._test_compilation(content)
                except ScssCompilationException as e:
                    errors.append(ScssProcessingError(
                        error_type="compilation_error",
                        message=str(e),
                        severity="error"
                    ))
                    compilation_result = False

            # Analyze remaining SCSS content
            remaining_analysis = self._analyze_remaining_scss(content)

            # Determine overall validation result
            is_valid = len(errors) == 0 and (compilation_result is not False)

            return ScssValidationResult(
                is_valid=is_valid,
                errors=errors,
                warnings=warnings,
                balanced_braces=syntax_checks["balanced_braces"],
                valid_selectors=syntax_checks["valid_selectors"],
                valid_properties=syntax_checks["valid_properties"],
                compilation_successful=compilation_result,
                compilation_time_ms=compilation_time,
                has_remaining_scss=remaining_analysis["has_remaining_scss"],
                remaining_variables=remaining_analysis["remaining_variables"],
                remaining_mixins=remaining_analysis["remaining_mixins"],
                remaining_functions=remaining_analysis["remaining_functions"]
            )

        except Exception as e:
            logger.error(f"SCSS validation failed: {e}")
            return ScssValidationResult(
                is_valid=False,
                errors=[ScssProcessingError(
                    error_type="validation_error",
                    message=f"Validation failed: {e}",
                    severity="error"
                )]
            )

    def _validate_basic_syntax(self, content: str) -> Dict[str, Any]:
        """Perform basic syntax validation"""
        errors: List[ScssProcessingError] = []
        warnings: List[ScssProcessingError] = []

        # Check balanced braces
        opening_braces = content.count("{")
        closing_braces = content.count("}")
        balanced_braces = opening_braces == closing_braces

        if not balanced_braces:
            errors.append(ScssProcessingError(
                error_type="syntax_error",
                message=f"Mismatched braces: {opening_braces} opening, {closing_braces} closing",
                severity="error"
            ))

        # Check for unterminated strings
        unterminated_strings = self._check_unterminated_strings(content)
        if unterminated_strings:
            for line_num, line_content in unterminated_strings:
                errors.append(ScssProcessingError(
                    error_type="syntax_error",
                    message="Unterminated string literal",
                    line_number=line_num,
                    source_snippet=line_content,
                    severity="error"
                ))

        # Check for invalid property declarations
        valid_properties = self._validate_property_declarations(content)
        if not valid_properties["is_valid"]:
            for error in valid_properties["errors"]:
                errors.append(error)

        # Check for invalid selectors
        valid_selectors = self._validate_selectors(content)
        if not valid_selectors["is_valid"]:
            for error in valid_selectors["errors"]:
                errors.append(error)

        # Check for malformed CSS functions
        malformed_functions = self._check_malformed_functions(content)
        for error in malformed_functions:
            warnings.append(error)

        return {
            "errors": errors,
            "warnings": warnings,
            "balanced_braces": balanced_braces,
            "valid_selectors": valid_selectors["is_valid"],
            "valid_properties": valid_properties["is_valid"]
        }

    def _validate_advanced_syntax(self, content: str) -> Dict[str, Any]:
        """Perform advanced syntax validation"""
        errors: List[ScssProcessingError] = []
        warnings: List[ScssProcessingError] = []

        # Check for conflicting variable definitions
        variable_conflicts = self._check_variable_conflicts(content)
        for conflict in variable_conflicts:
            warnings.append(conflict)

        # Check for missing mixin definitions
        missing_mixins = self._check_missing_mixins(content)
        for missing in missing_mixins:
            errors.append(missing)

        # Check for circular dependencies
        circular_deps = self._check_circular_dependencies(content)
        for dep in circular_deps:
            errors.append(dep)

        # Check for deprecated syntax
        deprecated_syntax = self._check_deprecated_syntax(content)
        for deprecated in deprecated_syntax:
            warnings.append(deprecated)

        return {
            "errors": errors,
            "warnings": warnings
        }

    def _check_unterminated_strings(self, content: str) -> List[Tuple[int, str]]:
        """Check for unterminated string literals"""
        unterminated = []
        lines = content.splitlines()

        for line_num, line in enumerate(lines, 1):
            # Remove comments first
            line_clean = re.sub(r"//.*$", "", line)
            line_clean = re.sub(r"/\*.*?\*/", "", line_clean)

            # Check for unterminated quoted strings
            in_double_quote = False
            in_single_quote = False
            escape_next = False

            for char in line_clean:
                if escape_next:
                    escape_next = False
                    continue

                if char == "\\":
                    escape_next = True
                elif char == '"' and not in_single_quote:
                    in_double_quote = not in_double_quote
                elif char == "'" and not in_double_quote:
                    in_single_quote = not in_single_quote

            if in_double_quote or in_single_quote:
                unterminated.append((line_num, line.strip()))

        return unterminated

    def _validate_property_declarations(self, content: str) -> Dict[str, Any]:
        """Validate CSS property declarations"""
        errors = []

        # Find all property declarations
        properties = self._compiled_patterns["css_property"].findall(content)

        for prop in properties:
            prop_clean = prop.strip()

            # Check for basic property format
            if ":" not in prop_clean:
                errors.append(ScssProcessingError(
                    error_type="syntax_error",
                    message="Invalid property declaration: missing colon",
                    source_snippet=prop_clean,
                    severity="error"
                ))
                continue

            # Check for empty property names or values
            parts = prop_clean.split(":", 1)
            if not parts[0].strip():
                errors.append(ScssProcessingError(
                    error_type="syntax_error",
                    message="Empty property name",
                    source_snippet=prop_clean,
                    severity="error"
                ))

            if len(parts) > 1 and not parts[1].strip().rstrip(";"):
                errors.append(ScssProcessingError(
                    error_type="syntax_error",
                    message="Empty property value",
                    source_snippet=prop_clean,
                    severity="error"
                ))

        return {
            "is_valid": len(errors) == 0,
            "errors": errors
        }

    def _validate_selectors(self, content: str) -> Dict[str, Any]:
        """Validate CSS selectors"""
        errors = []

        # Extract selectors
        selectors = self._compiled_patterns["selector"].findall(content)

        for selector in selectors:
            selector_clean = selector.rstrip("{").strip()

            # Skip empty selectors
            if not selector_clean:
                continue

            # Check for invalid characters in selectors
            if re.search(r"[{}]", selector_clean):
                errors.append(ScssProcessingError(
                    error_type="syntax_error",
                    message="Invalid characters in selector",
                    source_snippet=selector_clean,
                    severity="error"
                ))

            # Check for malformed pseudo-selectors
            if "::" in selector_clean:
                pseudo_elements = re.findall(r"::[a-zA-Z-]+", selector_clean)
                valid_pseudo_elements = ["::before", "::after", "::first-line", "::first-letter", "::selection"]
                for pseudo in pseudo_elements:
                    if pseudo not in valid_pseudo_elements:
                        errors.append(ScssProcessingError(
                            error_type="syntax_warning",
                            message=f"Unknown pseudo-element: {pseudo}",
                            source_snippet=selector_clean,
                            severity="warning"
                        ))

        return {
            "is_valid": len(errors) == 0,
            "errors": errors
        }

    def _check_malformed_functions(self, content: str) -> List[ScssProcessingError]:
        """Check for malformed CSS/SCSS functions"""
        errors = []

        # Find function calls
        function_pattern = re.compile(r"(\w+)\s*\([^)]*\)")
        functions = function_pattern.findall(content)

        for func in functions:
            # Check for malformed function syntax
            full_match = re.search(rf"{func}\s*\([^)]*\)", content)
            if full_match:
                func_call = full_match.group(0)

                # Check for unbalanced parentheses
                open_parens = func_call.count("(")
                close_parens = func_call.count(")")

                if open_parens != close_parens:
                    errors.append(ScssProcessingError(
                        error_type="syntax_error",
                        message=f"Unbalanced parentheses in function {func}",
                        source_snippet=func_call,
                        severity="warning"
                    ))

        return errors

    def _check_variable_conflicts(self, content: str) -> List[ScssProcessingError]:
        """Check for conflicting variable definitions"""
        warnings = []
        variable_definitions = {}

        lines = content.splitlines()
        for line_num, line in enumerate(lines, 1):
            # Find variable definitions
            var_match = re.match(r"^\s*(\$[\w-]+)\s*:\s*([^;]+);", line)
            if var_match:
                var_name = var_match.group(1)
                var_value = var_match.group(2).strip()

                if var_name in variable_definitions:
                    warnings.append(ScssProcessingError(
                        error_type="variable_conflict",
                        message=f"Variable {var_name} redefined",
                        line_number=line_num,
                        source_snippet=line.strip(),
                        severity="warning"
                    ))
                else:
                    variable_definitions[var_name] = {
                        "value": var_value,
                        "line": line_num
                    }

        return warnings

    def _check_missing_mixins(self, content: str) -> List[ScssProcessingError]:
        """Check for missing mixin definitions"""
        errors = []

        # Find mixin includes
        includes = self._compiled_patterns["scss_mixin_include"].findall(content)
        # Find mixin definitions
        definitions = self._compiled_patterns["scss_mixin_definition"].findall(content)

        # Extract mixin names
        included_mixins = set()
        for include in includes:
            mixin_name = re.search(r"@include\s+([\w-]+)", include)
            if mixin_name:
                included_mixins.add(mixin_name.group(1))

        defined_mixins = set()
        for definition in definitions:
            mixin_name = re.search(r"@mixin\s+([\w-]+)", definition)
            if mixin_name:
                defined_mixins.add(mixin_name.group(1))

        # Check for missing definitions
        missing_mixins = included_mixins - defined_mixins
        for mixin in missing_mixins:
            errors.append(ScssProcessingError(
                error_type="missing_mixin",
                message=f"Mixin '{mixin}' is used but not defined",
                severity="error"
            ))

        return errors

    def _check_circular_dependencies(self, content: str) -> List[ScssProcessingError]:
        """Check for circular dependencies in variables/mixins"""
        # This is a simplified check - a full implementation would require
        # building a dependency graph
        errors = []

        # Extract variable dependencies
        variable_deps = {}
        lines = content.splitlines()

        for line in lines:
            var_match = re.match(r"^\s*(\$[\w-]+)\s*:\s*([^;]+);", line)
            if var_match:
                var_name = var_match.group(1)
                var_value = var_match.group(2)

                # Find variables used in the value
                used_vars = self._compiled_patterns["scss_variable"].findall(var_value)
                variable_deps[var_name] = used_vars

        # Simple circular dependency check (A -> B -> A)
        for var, deps in variable_deps.items():
            for dep in deps:
                if dep in variable_deps and var in variable_deps[dep]:
                    errors.append(ScssProcessingError(
                        error_type="circular_dependency",
                        message=f"Circular dependency detected between {var} and {dep}",
                        severity="error"
                    ))

        return errors

    def _check_deprecated_syntax(self, content: str) -> List[ScssProcessingError]:
        """Check for deprecated SCSS syntax"""
        warnings = []

        # Check for deprecated division operator
        if re.search(r"\$[\w-]+\s*/\s*\$?[\w-]+", content):
            warnings.append(ScssProcessingError(
                error_type="deprecated_syntax",
                message="Division with '/' is deprecated, use math.div() instead",
                severity="warning",
                suggestion="Replace '/' with math.div() function"
            ))

        # Check for deprecated @import
        imports = self._compiled_patterns["scss_import"].findall(content)
        if imports:
            warnings.append(ScssProcessingError(
                error_type="deprecated_syntax",
                message="@import is deprecated, use @use instead",
                severity="warning",
                suggestion="Replace @import with @use directive"
            ))

        return warnings

    def _analyze_remaining_scss(self, content: str) -> Dict[str, Any]:
        """Analyze remaining SCSS syntax in content"""
        remaining_variables = self._compiled_patterns["scss_variable"].findall(content)
        remaining_mixins = self._compiled_patterns["scss_mixin_include"].findall(content)
        remaining_functions = self._compiled_patterns["scss_function"].findall(content)

        has_remaining_scss = bool(remaining_variables or remaining_mixins or remaining_functions)

        return {
            "has_remaining_scss": has_remaining_scss,
            "remaining_variables": list(set(remaining_variables)),
            "remaining_mixins": [re.search(r"@include\s+([\w-]+)", m).group(1)
                                for m in remaining_mixins if re.search(r"@include\s+([\w-]+)", m)],
            "remaining_functions": list(set(remaining_functions))
        }

    async def _test_compilation(self, content: str) -> Tuple[bool, Optional[float]]:
        """Test SCSS compilation with Sass compiler"""
        if not self._sass_available:
            raise ScssCompilationException("Sass compiler not available")

        try:
            import asyncio
            start_time = asyncio.get_event_loop().time()

            # Create temporary files
            with tempfile.NamedTemporaryFile(mode="w", suffix=".scss", delete=False) as temp_input:
                temp_input.write(content)
                input_path = temp_input.name

            with tempfile.NamedTemporaryFile(mode="w", suffix=".css", delete=False) as temp_output:
                output_path = temp_output.name

            # Run Sass compilation
            result = subprocess.run(
                ["sass", "--no-source-map", input_path, output_path],
                check=False, capture_output=True,
                text=True,
                timeout=30
            )

            end_time = asyncio.get_event_loop().time()
            compilation_time = (end_time - start_time) * 1000  # Convert to milliseconds

            # Clean up temporary files
            Path(input_path).unlink(missing_ok=True)
            Path(output_path).unlink(missing_ok=True)

            if result.returncode != 0:
                raise ScssCompilationException(f"Sass compilation failed: {result.stderr}")

            return True, compilation_time

        except subprocess.TimeoutExpired:
            raise ScssCompilationException("Sass compilation timed out")
        except Exception as e:
            raise ScssCompilationException(f"Compilation test failed: {e}")

    def validate_scss_file(self, file_path: Path, test_compilation: bool = True) -> ScssValidationResult:
        """Validate an SCSS file"""
        try:
            if not file_path.exists():
                return ScssValidationResult(
                    is_valid=False,
                    errors=[ScssProcessingError(
                        error_type="file_error",
                        message=f"File not found: {file_path}",
                        severity="error"
                    )]
                )

            content = file_path.read_text(encoding="utf-8")
            import asyncio
            return asyncio.run(self.validate_scss_content(content, test_compilation))

        except Exception as e:
            return ScssValidationResult(
                is_valid=False,
                errors=[ScssProcessingError(
                    error_type="file_error",
                    message=f"Failed to validate file {file_path}: {e}",
                    severity="error"
                )]
            )
