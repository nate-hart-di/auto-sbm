"""Import Remover - Removes @import statements"""

import re

from ..models import ScssImport, ScssTransformationContext
from .base import BaseTransformer


class ImportRemover(BaseTransformer):
    """Removes @import statements from SCSS"""

    def _compile_patterns(self) -> None:
        self._compiled_patterns = {
            "import_statement": re.compile(r"@import\s+.*?;")
        }

    async def transform(self, context: ScssTransformationContext) -> ScssTransformationContext:
        """Remove @import statements"""
        content = context.current_content

        # Count imports before removal
        imports_found = len(self._compiled_patterns["import_statement"].findall(content))

        # Remove all @import statements
        content = self._compiled_patterns["import_statement"].sub("", content)

        context.update_content(content, context.processing_step)
        self._log_transformation(context, f"Removed {imports_found} @import statements")
        return context

    async def extract_elements(self, context: ScssTransformationContext) -> ScssTransformationContext:
        """Extract @import statements for analysis"""
        imports = []
        matches = self._compiled_patterns["import_statement"].finditer(context.current_content)

        for match in matches:
            import_text = match.group(0)
            # Extract path from @import "path" or @import 'path'
            path_match = re.search(r'@import\s+["\']([^"\']+)["\']', import_text)
            if path_match:
                imports.append(ScssImport(
                    path=path_match.group(1),
                    is_external=not path_match.group(1).startswith("."),
                    source_line=self._find_line_number(context.current_content, import_text)
                ))

        context.imports = imports
        return context
