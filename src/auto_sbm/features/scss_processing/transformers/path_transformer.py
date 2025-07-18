"""Path Transformer - Converts relative paths to absolute paths"""

import re

from ..models import ScssTransformationContext
from .base import BaseTransformer


class PathTransformer(BaseTransformer):
    """Transforms relative image paths to absolute paths"""

    def _compile_patterns(self) -> None:
        self._compiled_patterns = {
            "relative_path": re.compile(r"url\((['\"]?)\.\.\/images\/(.*?)(['\"]?)\)")
        }

    async def transform(self, context: ScssTransformationContext) -> ScssTransformationContext:
        """Convert relative paths to absolute paths"""
        content = context.current_content

        # Convert ../images/ to absolute path
        content = self._compiled_patterns["relative_path"].sub(
            r'url("/wp-content/themes/DealerInspireDealerTheme/images/\2")',
            content
        )

        context.update_content(content, context.processing_step)
        self._log_transformation(context, "Converted relative paths to absolute paths")
        return context
