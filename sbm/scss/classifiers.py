"""
Fixed SCSS classifiers with proper CSS rule parsing.
This replaces the broken line-by-line approach.
"""

import logging
import re
from dataclasses import dataclass
from typing import NamedTuple

logger = logging.getLogger(__name__)


class ExclusionResult(NamedTuple):
    excluded_count: int
    included_count: int
    excluded_rules: list[str]
    patterns_matched: dict[str, int]


@dataclass
class CSSRule:
    selectors: str
    css_text: str
    start_line: int
    end_line: int


class StyleClassifier:
    """Fixed classifier that properly parses CSS rules before exclusion."""

    HEADER_PATTERNS = [
        r"header",          # Match 'header' anywhere
        r"\.masthead",
        r"\.banner"
    ]

    NAVIGATION_PATTERNS = [
        r"\.nav",                # Match .nav followed by ANYTHING (.nav*)
        r"\.navbar",             # Match .navbar followed by ANYTHING (.navbar*)
        r"menu-item",            # Match menu-item classes
        r"\.menu-",              # Match .menu- classes
    ]

    FOOTER_PATTERNS = [
        r"footer",        # Match 'footer' anywhere
        r"\.main-footer",
        r"\.site-footer",
        r"\.page-footer",
        r"\.bottom-footer",
        r"\.footer-content"
    ]

    def __init__(self, strict_mode: bool = True):
        self.strict_mode = strict_mode
        self.excluded_patterns = self._compile_patterns()
        self._exclusion_stats = {
            "header": 0,
            "navigation": 0,
            "footer": 0,
            "total_excluded": 0,
            "total_processed": 0
        }

    def _compile_patterns(self):
        """Compile all exclusion patterns into regex objects."""
        all_patterns = (
            self.HEADER_PATTERNS +
            self.NAVIGATION_PATTERNS +
            self.FOOTER_PATTERNS
        )
        return [re.compile(pattern, re.IGNORECASE) for pattern in all_patterns]

    def should_exclude_rule(self, css_rule: str) -> tuple[bool, str | None]:
        """Check if a CSS rule should be excluded."""
        if not css_rule.strip():
            return False, None

        # Check each exclusion pattern
        for pattern in self.excluded_patterns:
            if pattern.search(css_rule):
                # Determine which category matched
                if any(p.search(css_rule) for p in [re.compile(p, re.IGNORECASE) for p in self.HEADER_PATTERNS]):
                    return True, "header"
                if any(p.search(css_rule) for p in [re.compile(p, re.IGNORECASE) for p in self.NAVIGATION_PATTERNS]):
                    return True, "navigation"
                if any(p.search(css_rule) for p in [re.compile(p, re.IGNORECASE) for p in self.FOOTER_PATTERNS]):
                    return True, "footer"

        return False, None

    def parse_css_rules(self, content: str) -> tuple[list[CSSRule], list[tuple[int, str]]]:
        """Parse content into complete CSS rules and non-rule lines."""
        lines = content.split("\n")
        rules = []
        non_rule_lines = []

        current_rule_lines = []
        current_selectors = []
        brace_depth = 0
        in_rule = False
        rule_start_line = 0

        i = 0
        while i < len(lines):
            line = lines[i]

            # Count braces
            open_braces = line.count("{")
            close_braces = line.count("}")

            if not in_rule:
                # Not in a rule currently
                if open_braces > 0:
                    # Starting a rule
                    # Collect preceding selector lines
                    j = i - 1
                    preceding_lines = []
                    while j >= 0:
                        prev_line = lines[j]
                        prev_stripped = prev_line.strip()

                        # Stop at empty lines, comments, or end of previous rule
                        if (not prev_stripped or
                            prev_stripped.startswith(("//","/*")) or
                            "}" in prev_line or
                            prev_stripped.startswith(("@import", "$", "@media", "@supports", "@include")) or
                            (prev_stripped.endswith(";") and ":" in prev_stripped)):
                            break

                        preceding_lines.insert(0, prev_line)
                        j -= 1

                    # Start the rule
                    current_rule_lines = preceding_lines + [line]
                    # Extract selectors (everything before the {)
                    selector_text = ""
                    for rule_line in current_rule_lines:
                        if "{" in rule_line:
                            selector_text += rule_line.split("{")[0]
                            break
                        selector_text += rule_line + "\n"

                    current_selectors = selector_text.strip()
                    rule_start_line = i - len(preceding_lines)
                    brace_depth = open_braces - close_braces
                    in_rule = True
                # Non-rule line
                elif not any(line_num == i for line_num, _ in non_rule_lines):
                    non_rule_lines.append((i, line))
            else:
                # In a rule
                current_rule_lines.append(line)
                brace_depth += open_braces - close_braces

                if brace_depth <= 0:
                    # Rule complete
                    rule_content = "\n".join(current_rule_lines)
                    rules.append(CSSRule(
                        selectors=current_selectors,
                        css_text=rule_content,
                        start_line=rule_start_line,
                        end_line=i
                    ))

                    # Reset
                    current_rule_lines = []
                    current_selectors = []
                    in_rule = False
                    brace_depth = 0

            i += 1

        # Handle incomplete rule at end
        if current_rule_lines and in_rule:
            rule_content = "\n".join(current_rule_lines)
            rules.append(CSSRule(
                selectors=current_selectors,
                css_text=rule_content,
                start_line=rule_start_line,
                end_line=len(lines) - 1
            ))

        return rules, non_rule_lines

    def filter_scss_content(self, content: str) -> tuple[str, ExclusionResult]:
        """Filter SCSS content by excluding complete CSS rules."""
        if not content.strip():
            return content, ExclusionResult(0, 0, [], {})

        # Parse into rules and non-rule content
        rules, non_rule_lines = self.parse_css_rules(content)

        # Filter rules
        filtered_rules = []
        excluded_rules = []
        patterns_matched = {}

        for rule in rules:
            # Check both selectors and full CSS content for patterns
            should_exclude_by_selector, reason1 = self.should_exclude_rule(rule.selectors)
            should_exclude_by_content, reason2 = self.should_exclude_rule(rule.css_text)

            should_exclude = should_exclude_by_selector or should_exclude_by_content
            reason = reason1 or reason2

            if should_exclude:
                excluded_rules.append(rule.css_text)
                patterns_matched[reason] = patterns_matched.get(reason, 0) + 1
                self._exclusion_stats[reason] += 1
                logger.debug(f"Excluded {reason} rule: {rule.selectors[:50]}...")
            else:
                filtered_rules.append(rule)

        # Reconstruct content
        all_lines = {}

        # Create set of excluded rule line ranges for filtering
        excluded_line_ranges = set()
        for rule in rules:
            # Check both selectors and full CSS content for patterns
            should_exclude_by_selector, _ = self.should_exclude_rule(rule.selectors)
            should_exclude_by_content, _ = self.should_exclude_rule(rule.css_text)
            should_exclude = should_exclude_by_selector or should_exclude_by_content

            if should_exclude:
                for line_num in range(rule.start_line, rule.end_line + 1):
                    excluded_line_ranges.add(line_num)

        # Add non-rule lines that are not part of excluded rules
        for line_num, line in non_rule_lines:
            if line_num not in excluded_line_ranges:
                all_lines[line_num] = line

        # Add kept rules
        for rule in filtered_rules:
            rule_lines = rule.css_text.split("\n")
            for i, line in enumerate(rule_lines):
                all_lines[rule.start_line + i] = line

        # Sort by line number and join
        sorted_lines = [all_lines[i] for i in sorted(all_lines.keys())]
        filtered_content = "\n".join(sorted_lines)

        # Update stats
        self._exclusion_stats["total_excluded"] = len(excluded_rules)
        self._exclusion_stats["total_processed"] += 1

        result = ExclusionResult(
            excluded_count=len(excluded_rules),
            included_count=len(filtered_rules),
            excluded_rules=excluded_rules,
            patterns_matched=patterns_matched
        )

        if excluded_rules:
            exclusion_summary = ", ".join([f"{pattern}: {count}" for pattern, count in patterns_matched.items()])
            logger.debug(f"Excluded {len(excluded_rules)} rules: {exclusion_summary}")

        return filtered_content, result


def filter_scss_for_site_builder(content: str, strict_mode: bool = True) -> tuple[str, ExclusionResult]:
    """Filter SCSS content to exclude header/footer/nav styles for Site Builder."""
    classifier = StyleClassifier(strict_mode=strict_mode)
    return classifier.filter_scss_content(content)


class ProfessionalStyleClassifier(StyleClassifier):
    """Professional CSS parser-based style classifier."""

    def __init__(self, parser_strategy: str = "auto", strict_mode: bool = True) -> None:
        """Initialize professional style classifier."""
        super().__init__(strict_mode)
        # For now, just use the base implementation
        # Could be extended later with actual CSS parsers

    def filter_scss_content(self, content: str) -> tuple[str, ExclusionResult]:
        """Filter SCSS content using professional parsing (fallback to base for now)."""
        return super().filter_scss_content(content)


def robust_css_processing(content: str) -> tuple[str, ExclusionResult]:
    """Multi-layer error handling with graceful degradation."""
    try:
        classifier = StyleClassifier()
        return classifier.filter_scss_content(content)
    except Exception as e:
        logger.error(f"CSS processing failed: {e}")
        # Conservative fallback - exclude complete rules with keywords
        return conservative_keyword_exclusion(content)


def conservative_keyword_exclusion(content: str) -> tuple[str, ExclusionResult]:
    """Ultra-conservative fallback - exclude complete rules with keywords."""
    exclusion_keywords = ["header", "nav", "footer", "navbar", "navigation"]

    lines = content.split("\n")
    filtered_lines = []
    excluded_rules = []
    skip_next_lines = 0

    i = 0
    while i < len(lines):
        line = lines[i]

        # Skip lines that were marked for skipping
        if skip_next_lines > 0:
            skip_next_lines -= 1
            i += 1
            continue

        line_lower = line.lower()

        # Check if this line contains excluded keywords
        if any(keyword in line_lower for keyword in exclusion_keywords):
            if "{" in line:
                # This line starts a rule block - skip until the matching closing brace
                brace_count = line.count("{") - line.count("}")
                rule_lines = [line]
                j = i + 1

                while j < len(lines) and brace_count > 0:
                    next_line = lines[j]
                    rule_lines.append(next_line)
                    brace_count += next_line.count("{") - next_line.count("}")
                    j += 1

                # Skip this entire rule block
                excluded_rules.append("\n".join(rule_lines))
                skip_next_lines = j - i - 1
                logger.debug(f"Conservative exclusion of rule block starting with: {line.strip()}")
            else:
                # Single line with keyword - exclude it
                excluded_rules.append(line)
                logger.debug(f"Conservative exclusion: {line.strip()}")
        else:
            # Line doesn't contain excluded keywords - include it
            filtered_lines.append(line)

        i += 1

    return "\n".join(filtered_lines), ExclusionResult(
        excluded_count=len(excluded_rules),
        included_count=len(filtered_lines),
        excluded_rules=excluded_rules,
        patterns_matched={"conservative": len(excluded_rules)}
    )
