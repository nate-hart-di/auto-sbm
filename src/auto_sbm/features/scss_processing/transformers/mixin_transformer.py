"""SCSS Mixin Transformer

Converts SCSS mixins to CSS following the Site Builder pattern.
This is a simplified version that demonstrates the architecture.
"""

import logging
import re

from ..models import ScssMixinDefinition, ScssMixinType, ScssTransformationContext
from .base import BaseTransformer

logger = logging.getLogger(__name__)


class MixinTransformer(BaseTransformer):
    """Transforms SCSS mixins to CSS"""

    def _compile_patterns(self) -> None:
        """Compile regex patterns for mixin processing"""
        self._compiled_patterns = {
            "mixin_include": re.compile(r"@include\s+([\w-]+)(?:\([^)]*\))?\s*(?:\{[^}]*\})?;?"),
            "mixin_definition": re.compile(r"@mixin\s+([\w-]+)(?:\([^)]*\))?\s*\{[^}]*\}")
        }

    async def transform(self, context: ScssTransformationContext) -> ScssTransformationContext:
        """Transform SCSS mixins to CSS"""
        try:
            logger.info("Starting mixin transformation")

            # Extract mixins first
            context = await self.extract_elements(context)

            # Convert mixin includes to CSS
            converted_content = self._convert_mixin_includes(context.current_content)

            # Remove mixin definitions
            final_content = self._remove_mixin_definitions(converted_content)

            context.update_content(final_content, context.processing_step)

            self._log_transformation(
                context,
                f"Converted {len(context.mixins)} mixins to CSS"
            )

            return context

        except Exception as e:
            logger.error(f"Mixin transformation failed: {e}")
            self._add_error(context, "mixin_transformation", str(e))
            return context

    async def extract_elements(self, context: ScssTransformationContext) -> ScssTransformationContext:
        """Extract SCSS mixins from content"""
        mixins = []

        # Find mixin includes
        matches = self._compiled_patterns["mixin_include"].finditer(context.current_content)

        for match in matches:
            mixin_name = match.group(1)
            line_number = self._find_line_number(context.current_content, match.group(0))

            mixin = ScssMixinDefinition(
                name=mixin_name,
                type=ScssMixinType.CUSTOM,  # Default type
                source_line=line_number
            )

            mixins.append(mixin)

        context.mixins = mixins
        return context

    def _convert_mixin_includes(self, content: str) -> str:
        """Convert @include statements to CSS"""
        # Simplified conversion - in a real implementation, this would use
        # the comprehensive mixin parser from the legacy code

        def replace_mixin(match):
            mixin_name = match.group(1)

            # Simple mixin conversions (placeholder implementations)
            if mixin_name == "flexbox":
                return "display: flex;"
            if mixin_name == "clearfix":
                return '&::after { content: ""; display: table; clear: both; }'
            # Unknown mixin - leave a comment
            return f"/* TODO: Convert @include {mixin_name} */"

        return self._compiled_patterns["mixin_include"].sub(replace_mixin, content)

    def _remove_mixin_definitions(self, content: str) -> str:
        """Remove @mixin definitions"""
        return self._compiled_patterns["mixin_definition"].sub("", content)
