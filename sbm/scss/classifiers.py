"""
SCSS/CSS style classification for migration filtering.

This module provides functionality to classify CSS/SCSS rules and determine
which styles should be excluded from Site Builder migration to prevent
conflicts with Site Builder's own header, footer, and navigation components.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from ..utils.logger import logger


@dataclass
class ExclusionResult:
    """Result of style exclusion analysis."""
    excluded_count: int
    included_count: int
    excluded_rules: List[str]
    patterns_matched: Dict[str, int]


class StyleClassifier:
    """Classify CSS/SCSS rules to determine if they should be migrated to Site Builder."""

    # Patterns for styles that MUST NOT be migrated to Site Builder
    # These conflict with Site Builder's own components
    HEADER_PATTERNS = [
        r"\.header\b",
        r"#header\b",
        r"\.main-header\b",
        r"\.site-header\b",
        r"\.page-header\b",
        r"\.top-header\b",
        r"\.masthead\b",
        r"\.banner\b"
    ]

    NAVIGATION_PATTERNS = [
        r"\.nav\b",
        r"\.navigation\b",
        r"\.main-nav\b",
        r"\.navbar\b",
        r"\.menu\b",
        r"\.primary-menu\b",
        r"\.main-menu\b",
        r"\.site-nav\b",
        r"\.nav-menu\b",
        r"\.breadcrumb\b"
    ]

    FOOTER_PATTERNS = [
        r"\.footer\b",
        r"#footer\b",
        r"\.main-footer\b",
        r"\.site-footer\b",
        r"\.page-footer\b",
        r"\.bottom-footer\b",
        r"\.footer-content\b"
    ]

    def __init__(self, strict_mode: bool = True):
        """
        Initialize the style classifier.
        
        Args:
            strict_mode: If True, use strict exclusion patterns. If False, use relaxed patterns.
        """
        self.strict_mode = strict_mode
        self.excluded_patterns = self._compile_patterns()
        self._exclusion_stats = {
            "header": 0,
            "navigation": 0,
            "footer": 0,
            "total_excluded": 0,
            "total_processed": 0
        }

    def _compile_patterns(self) -> List[re.Pattern]:
        """Compile all exclusion patterns into regex objects."""
        all_patterns = (
            self.HEADER_PATTERNS +
            self.NAVIGATION_PATTERNS +
            self.FOOTER_PATTERNS
        )

        compiled_patterns = []
        for pattern in all_patterns:
            try:
                # Use case-insensitive matching for CSS selectors
                compiled_patterns.append(re.compile(pattern, re.IGNORECASE))
            except re.error as e:
                logger.warning(f"Invalid regex pattern '{pattern}': {e}")
                continue

        return compiled_patterns

    def should_exclude_rule(self, css_rule: str) -> tuple[bool, str | None]:
        """
        Determine if a CSS rule should be excluded from migration.
        
        Args:
            css_rule: The CSS rule content to analyze
            
        Returns:
            Tuple of (should_exclude, reason)
        """
        # Skip empty rules
        if not css_rule.strip():
            return False, None

        # Check each exclusion pattern
        for pattern in self.excluded_patterns:
            if pattern.search(css_rule):
                # Determine which category matched
                if any(p.search(css_rule) for p in [re.compile(p, re.IGNORECASE) for p in self.HEADER_PATTERNS]):
                    reason = "header"
                elif any(p.search(css_rule) for p in [re.compile(p, re.IGNORECASE) for p in self.NAVIGATION_PATTERNS]):
                    reason = "navigation"
                elif any(p.search(css_rule) for p in [re.compile(p, re.IGNORECASE) for p in self.FOOTER_PATTERNS]):
                    reason = "footer"
                else:
                    reason = "unknown"

                return True, reason

        return False, None

    def filter_scss_content(self, content: str) -> tuple[str, ExclusionResult]:
        """
        Remove excluded styles from SCSS content.
        
        Args:
            content: The original SCSS content
            
        Returns:
            Tuple of (filtered_content, exclusion_result)
        """
        if not content.strip():
            return content, ExclusionResult(0, 0, [], {})

        lines = content.split("\n")
        filtered_lines = []
        excluded_rules = []
        patterns_matched = {}

        # Track current rule context
        current_rule = []
        brace_depth = 0
        in_rule = False

        for line_num, line in enumerate(lines, 1):
            # Count braces to track rule boundaries
            brace_depth += line.count("{") - line.count("}")

            # If we're starting a new rule
            if "{" in line and not in_rule:
                in_rule = True
                current_rule = [line]
            elif in_rule:
                current_rule.append(line)
            else:
                # Not in a rule, include the line (comments, variables, etc.)
                filtered_lines.append(line)
                continue

            # If we've completed a rule (brace_depth returns to 0)
            if in_rule and brace_depth == 0:
                rule_content = "\n".join(current_rule)
                should_exclude, reason = self.should_exclude_rule(rule_content)

                if should_exclude:
                    # Log the exclusion
                    logger.debug(f"Excluding {reason} rule at line {line_num}: {current_rule[0].strip()}")
                    excluded_rules.append(rule_content)
                    patterns_matched[reason] = patterns_matched.get(reason, 0) + 1
                    self._exclusion_stats[reason] += 1

                    # Add a comment about the exclusion
                    filtered_lines.append(f"/* EXCLUDED {reason.upper()} RULE: {current_rule[0].strip()} */")
                else:
                    # Include the rule
                    filtered_lines.extend(current_rule)

                # Reset for next rule
                current_rule = []
                in_rule = False

        # Handle incomplete rules (shouldn't happen with valid SCSS)
        if current_rule and in_rule:
            logger.warning("Incomplete SCSS rule found at end of file")
            filtered_lines.extend(current_rule)

        # Update stats
        self._exclusion_stats["total_excluded"] = len(excluded_rules)
        self._exclusion_stats["total_processed"] += 1

        filtered_content = "\n".join(filtered_lines)

        result = ExclusionResult(
            excluded_count=len(excluded_rules),
            included_count=len(lines) - len(excluded_rules),
            excluded_rules=excluded_rules,
            patterns_matched=patterns_matched
        )

        return filtered_content, result

    def analyze_file(self, file_path: Path) -> ExclusionResult:
        """
        Analyze a SCSS file and return exclusion information without modifying it.
        
        Args:
            file_path: Path to the SCSS file to analyze
            
        Returns:
            ExclusionResult with analysis information
        """
        try:
            content = file_path.read_text(encoding="utf-8")
            _, result = self.filter_scss_content(content)
            return result
        except Exception as e:
            logger.error(f"Error analyzing file {file_path}: {e}")
            return ExclusionResult(0, 0, [], {})

    def get_exclusion_stats(self) -> Dict[str, int]:
        """Get current exclusion statistics."""
        return self._exclusion_stats.copy()

    def reset_stats(self) -> None:
        """Reset exclusion statistics."""
        self._exclusion_stats = {
            "header": 0,
            "navigation": 0,
            "footer": 0,
            "total_excluded": 0,
            "total_processed": 0
        }


# Convenience function for quick style filtering
def filter_scss_for_site_builder(content: str, strict_mode: bool = True) -> tuple[str, ExclusionResult]:
    """
    Filter SCSS content to exclude header/footer/nav styles for Site Builder.
    
    Args:
        content: The SCSS content to filter
        strict_mode: Use strict exclusion patterns
        
    Returns:
        Tuple of (filtered_content, exclusion_result)
    """
    classifier = StyleClassifier(strict_mode=strict_mode)
    return classifier.filter_scss_content(content)
