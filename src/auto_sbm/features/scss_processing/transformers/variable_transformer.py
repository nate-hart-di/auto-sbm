"""SCSS Variable Transformer

Converts SCSS variables to CSS custom properties following the Site Builder pattern.
This replaces the variable processing logic from the legacy processor.py file.
"""

import logging
import re
from typing import Dict, List

from ..models import ScssTransformationContext, ScssVariable
from .base import BaseTransformer

logger = logging.getLogger(__name__)


class VariableTransformer(BaseTransformer):
    """
    Transforms SCSS variables to CSS custom properties.
    
    Handles the complex logic of:
    - Extracting SCSS variable declarations
    - Converting to CSS custom properties format
    - Intelligently replacing variable usage in different contexts
    - Avoiding conversion in SCSS-specific contexts (mixins, maps, etc.)
    """

    def _compile_patterns(self) -> None:
        """Compile regex patterns for variable processing"""
        self._compiled_patterns = {
            "variable_declaration": re.compile(
                r"^\s*(\$[\w-]+)\s*:\s*(.*?);",
                re.MULTILINE
            ),
            "variable_usage": re.compile(r"\$([\w-]+)"),
            "mixin_definition": re.compile(r"@mixin\s+[\w-]+"),
            "map_definition": re.compile(r"^\s*\$[\w-]+\s*:\s*\(", re.MULTILINE),
            "scss_function": re.compile(r"@(include|extend|if|else|each|for|function)"),
            "interpolation": re.compile(r"#\{[^}]*\}"),
            "css_property_line": re.compile(r"^\s*[\w-]+\s*:\s*[^;]+;", re.MULTILINE)
        }

    async def transform(self, context: ScssTransformationContext) -> ScssTransformationContext:
        """Transform SCSS variables to CSS custom properties"""
        try:
            logger.info("Starting SCSS variable transformation")

            # Extract variable declarations
            context = await self.extract_elements(context)

            # Process variables into :root block
            content_with_root = self._process_variables_to_root(
                context.current_content,
                context.variables
            )

            # Convert variable usage to CSS custom properties
            final_content = self._convert_variable_usage(content_with_root)

            # Update context
            context.update_content(final_content, context.processing_step)

            self._log_transformation(
                context,
                f"Converted {len(context.variables)} variables to CSS custom properties"
            )

            logger.info(f"Variable transformation completed: {len(context.variables)} variables processed")
            return context

        except Exception as e:
            logger.error(f"Variable transformation failed: {e}")
            self._add_error(context, "variable_transformation", str(e))
            return context

    async def extract_elements(self, context: ScssTransformationContext) -> ScssTransformationContext:
        """Extract SCSS variables from content"""
        variables = []

        # Find all variable declarations
        matches = self._compiled_patterns["variable_declaration"].finditer(context.current_content)

        for match in matches:
            var_name = match.group(1).lstrip("$")  # Remove $ prefix
            var_value = match.group(2).strip()
            line_number = self._find_line_number(context.current_content, match.group(0))

            # Create variable model
            variable = ScssVariable(
                name=var_name,
                value=var_value,
                source_line=line_number
            )

            # Check for dependencies on other variables
            dependencies = self._find_variable_dependencies(var_value)
            variable.dependencies = dependencies

            variables.append(variable)

        context.variables = variables
        return context

    def _find_variable_dependencies(self, value: str) -> List[str]:
        """Find other variables used in this variable's value"""
        dependencies = []

        # Find all variable references in the value
        var_matches = self._compiled_patterns["variable_usage"].findall(value)

        for var_name in var_matches:
            if var_name not in dependencies:
                dependencies.append(var_name)

        return dependencies

    def _process_variables_to_root(self, content: str, variables: List[ScssVariable]) -> str:
        """Process SCSS variables into a :root block"""
        if not variables:
            return content

        # Remove original variable declarations
        content_without_vars = self._compiled_patterns["variable_declaration"].sub("", content)

        # Build :root block
        root_properties = []
        for variable in variables:
            # Convert variable value (replace nested variables)
            converted_value = self._convert_variable_references_in_value(variable.value)
            root_properties.append(f"  {variable.css_custom_property}: {converted_value};")

        # Create :root block
        root_block = ":root {\n" + "\n".join(root_properties) + "\n}\n\n"

        # Prepend to content
        return root_block + content_without_vars.lstrip()

    def _convert_variable_references_in_value(self, value: str) -> str:
        """Convert SCSS variable references in a value to CSS custom properties"""
        def replace_var(match):
            var_name = match.group(1)
            return f"var(--{var_name})"

        return self._compiled_patterns["variable_usage"].sub(replace_var, value)

    def _convert_variable_usage(self, content: str) -> str:
        """Convert SCSS variable usage to CSS custom properties intelligently"""
        lines = content.split("\n")
        inside_mixin = False
        inside_map = False
        brace_depth = 0

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Track brace depth for nested structures
            brace_depth += line.count("{") - line.count("}")

            # Check context flags
            if self._compiled_patterns["mixin_definition"].search(stripped):
                inside_mixin = True
            elif inside_mixin and stripped == "}" and brace_depth == 0:
                inside_mixin = False
            elif self._compiled_patterns["map_definition"].search(stripped):
                inside_map = True
            elif inside_map and stripped.endswith(");"):
                inside_map = False

            # Skip conversion in SCSS contexts
            if self._should_skip_variable_conversion(line, inside_mixin, inside_map):
                continue

            # Convert variables in CSS contexts
            if self._is_css_context(line):
                lines[i] = self._convert_variables_in_line(line)

        return "\n".join(lines)

    def _should_skip_variable_conversion(
        self,
        line: str,
        inside_mixin: bool,
        inside_map: bool
    ) -> bool:
        """Determine if variable conversion should be skipped for this line"""
        stripped = line.strip()

        # Skip SCSS-specific contexts
        if (inside_mixin or inside_map or
            stripped.startswith("@") or
            "map-get(" in stripped or
            "map-keys(" in stripped or
            stripped.startswith("%")):
            return True

        # Skip interpolation contexts
        if self._compiled_patterns["interpolation"].search(line):
            return True

        return False

    def _is_css_context(self, line: str) -> bool:
        """Check if line is in a CSS property context"""
        stripped = line.strip()

        # CSS property pattern: property: value;
        if ":" in stripped and not stripped.startswith("@"):
            # Not a variable declaration
            if not re.match(r"^\s*\$[\w-]+\s*:", stripped):
                return True

        return False

    def _convert_variables_in_line(self, line: str) -> str:
        """Convert SCSS variables to CSS custom properties in a line"""
        # Handle interpolation specially
        if "#{" in line:
            return self._convert_with_interpolation(line)

        # Simple variable replacement
        def replace_var(match):
            var_name = match.group(1)
            return f"var(--{var_name})"

        return self._compiled_patterns["variable_usage"].sub(replace_var, line)

    def _convert_with_interpolation(self, line: str) -> str:
        """Convert variables while preserving interpolation"""
        # Split line into parts, only convert variables outside interpolation
        parts = re.split(r"(#\{[^}]*\})", line)

        for i, part in enumerate(parts):
            if not part.startswith("#{"):
                parts[i] = self._compiled_patterns["variable_usage"].sub(
                    lambda m: f"var(--{m.group(1)})",
                    part
                )

        return "".join(parts)

    def get_variable_statistics(self, context: ScssTransformationContext) -> Dict[str, any]:
        """Get statistics about variable processing"""
        if not context.variables:
            return {"variables_found": 0}

        stats = {
            "variables_found": len(context.variables),
            "variable_types": {},
            "variables_with_dependencies": 0,
            "max_dependencies": 0
        }

        # Analyze variable types
        for variable in context.variables:
            var_type = variable.type.value
            stats["variable_types"][var_type] = stats["variable_types"].get(var_type, 0) + 1

            if variable.dependencies:
                stats["variables_with_dependencies"] += 1
                stats["max_dependencies"] = max(stats["max_dependencies"], len(variable.dependencies))

        return stats
