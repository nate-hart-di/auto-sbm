"""Base transformer class for SCSS transformations"""

import logging
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from ..models import ScssTransformationContext

logger = logging.getLogger(__name__)


class BaseTransformer(ABC):
    """
    Abstract base class for SCSS transformers.
    
    Each transformer implements a specific aspect of SCSS-to-CSS transformation
    with consistent error handling and logging.
    """

    def __init__(self):
        self.name = self.__class__.__name__
        self._compiled_patterns: Dict[str, re.Pattern] = {}
        self._compile_patterns()
        logger.debug(f"{self.name} transformer initialized")

    def _compile_patterns(self) -> None:
        """Override in subclasses to compile commonly used regex patterns"""

    @abstractmethod
    async def transform(self, context: ScssTransformationContext) -> ScssTransformationContext:
        """
        Transform SCSS content in the given context.
        
        Args:
            context: Current transformation context
            
        Returns:
            Updated transformation context
        """

    async def extract_elements(self, context: ScssTransformationContext) -> ScssTransformationContext:
        """
        Extract relevant elements without transforming (for preview/analysis).
        
        Default implementation does nothing - override in subclasses as needed.
        """
        return context

    def _add_error(
        self,
        context: ScssTransformationContext,
        error_type: str,
        message: str,
        line_number: Optional[int] = None,
        source_snippet: Optional[str] = None,
        severity: str = "error"
    ) -> None:
        """Add an error to the processing context"""
        # Note: This is a simplified implementation since ScssTransformationContext
        # doesn't have an errors list. In a real implementation, you might want to
        # extend the context model or handle errors differently.
        logger.error(f"{self.name}: {message}")

    def _add_warning(
        self,
        context: ScssTransformationContext,
        message: str,
        line_number: Optional[int] = None
    ) -> None:
        """Add a warning to the processing context"""
        logger.warning(f"{self.name}: {message}")

    def _log_transformation(self, context: ScssTransformationContext, transformation: str) -> None:
        """Log a successful transformation"""
        context.add_transformation(f"{self.name}: {transformation}")
        logger.debug(f"{self.name}: {transformation}")

    def _find_line_number(self, content: str, pattern: str) -> Optional[int]:
        """Find the line number where a pattern occurs"""
        lines = content.splitlines()
        for i, line in enumerate(lines, 1):
            if pattern in line:
                return i
        return None

    def _safe_replace(
        self,
        content: str,
        pattern: str,
        replacement: str,
        count: int = 0
    ) -> tuple[str, int]:
        """
        Safely replace patterns with error tracking.
        
        Returns:
            Tuple of (modified_content, replacement_count)
        """
        try:
            if isinstance(pattern, str):
                if count == 0:
                    new_content = content.replace(pattern, replacement)
                    replacement_count = content.count(pattern)
                else:
                    new_content = content.replace(pattern, replacement, count)
                    replacement_count = min(content.count(pattern), count)
            else:
                # Assume pattern is a compiled regex
                new_content, replacement_count = pattern.subn(replacement, content, count=count)

            return new_content, replacement_count

        except Exception as e:
            logger.error(f"{self.name}: Failed to replace pattern: {e}")
            return content, 0

    def _extract_between_braces(self, content: str, start_index: int) -> tuple[str, int]:
        """
        Extract content between matching braces starting from start_index.
        
        Returns:
            Tuple of (extracted_content, end_index)
        """
        brace_count = 0
        start_found = False
        start_content_index = start_index

        for i in range(start_index, len(content)):
            char = content[i]

            if char == "{":
                if not start_found:
                    start_found = True
                    start_content_index = i + 1
                brace_count += 1
            elif char == "}":
                brace_count -= 1
                if brace_count == 0 and start_found:
                    return content[start_content_index:i], i

        # Unmatched braces
        if start_found:
            return content[start_content_index:], len(content)
        return "", start_index

    def _normalize_whitespace(self, content: str) -> str:
        """Normalize whitespace in content"""
        # Replace multiple spaces with single space
        content = re.sub(r"[ \t]+", " ", content)
        # Replace multiple newlines with single newline
        content = re.sub(r"\n\s*\n", "\n\n", content)
        return content.strip()

    def _is_inside_comment(self, content: str, position: int) -> bool:
        """Check if a position is inside a comment"""
        # Check for single-line comment
        line_start = content.rfind("\n", 0, position) + 1
        line_content = content[line_start:position]
        if "//" in line_content:
            return True

        # Check for multi-line comment
        comment_start = content.rfind("/*", 0, position)
        if comment_start != -1:
            comment_end = content.find("*/", comment_start)
            if comment_end == -1 or comment_end > position:
                return True

        return False

    def _is_inside_string(self, content: str, position: int) -> bool:
        """Check if a position is inside a string literal"""
        # Simple implementation - count quotes before position
        line_start = content.rfind("\n", 0, position) + 1
        line_content = content[line_start:position]

        double_quotes = line_content.count('"') - line_content.count('\\"')
        single_quotes = line_content.count("'") - line_content.count("\\'")

        return (double_quotes % 2 != 0) or (single_quotes % 2 != 0)

    def _get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics for this transformer"""
        return {
            "transformer": self.name,
            "compiled_patterns": len(self._compiled_patterns)
        }
