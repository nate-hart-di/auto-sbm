"""Content Cleaner - Cleans up whitespace and formatting"""

import re

from ..models import ScssTransformationContext
from .base import BaseTransformer


class ContentCleaner(BaseTransformer):
    """Cleans up whitespace and formatting in the final output"""

    def _compile_patterns(self) -> None:
        self._compiled_patterns = {
            "multiple_newlines": re.compile(r"\n\s*\n"),
            "trailing_whitespace": re.compile(r"[ \t]+$", re.MULTILINE),
            "empty_lines": re.compile(r"^\s*$", re.MULTILINE)
        }

    async def transform(self, context: ScssTransformationContext) -> ScssTransformationContext:
        """Clean up the final content"""
        content = context.current_content

        # Replace multiple blank lines with single blank line
        content = self._compiled_patterns["multiple_newlines"].sub("\n\n", content)

        # Remove trailing whitespace
        content = self._compiled_patterns["trailing_whitespace"].sub("", content)

        # Clean up final content
        content = content.strip()

        context.update_content(content, context.processing_step)
        self._log_transformation(context, "Cleaned up whitespace and formatting")
        return context
