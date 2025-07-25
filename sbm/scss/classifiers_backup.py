"""
SCSS/CSS style classification for migration filtering.

This module provides functionality to classify CSS/SCSS rules and determine
which styles should be excluded from Site Builder migration to prevent
conflicts with Site Builder's own header, footer, and navigation components.
"""

from __future__ import annotations

import re
import subprocess
import tempfile
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol

from sbm.utils.logger import logger

if TYPE_CHECKING:
    from pathlib import Path


@dataclass
class ExclusionResult:
    """Result of style exclusion analysis."""
    excluded_count: int
    included_count: int
    excluded_rules: list[str]
    patterns_matched: dict[str, int]


@dataclass
class CSSRule:
    """Normalized CSS rule representation."""
    selectors: str
    css_text: str
    rule_type: str = "style"


class CSSParser(Protocol):
    """Protocol for CSS parser implementations."""

    def parse_stylesheet(self, content: str) -> Any:
        """Parse CSS content and return parsed data."""
        ...

    def extract_rules(self, parsed_data: Any) -> list[CSSRule]:
        """Extract CSS rules from parsed data."""
        ...


class TinyCSS2Parser:
    """CSS parser implementation using tinycss2 library."""

    def parse_stylesheet(self, content: str) -> Any:
        """Parse CSS content using tinycss2."""
        try:
            import tinycss2
            return tinycss2.parse_stylesheet(content)
        except ImportError as e:
            logger.error(f"tinycss2 not available: {e}")
            raise

    def extract_rules(self, rules: Any) -> list[CSSRule]:
        """Extract CSS rules from tinycss2 parsed data."""
        import tinycss2
        extracted = []

        # tinycss2.parse_stylesheet returns a list of rules and tokens
        if not isinstance(rules, list):
            return extracted

        for rule in rules:
            if hasattr(rule, "type") and rule.type == "qualified-rule":
                try:
                    selectors = tinycss2.serialize(rule.prelude).strip()
                    # Construct CSS text from selector and content
                    content = tinycss2.serialize(rule.content)
                    css_text = f"{selectors} {{{content}}}"
                    extracted.append(CSSRule(selectors, css_text))
                except Exception as e:
                    logger.warning(f"Failed to serialize rule: {e}")
                    continue

        return extracted


class CSSUtilsParser:
    """CSS parser implementation using cssutils library."""

    def parse_stylesheet(self, content: str) -> Any:
        """Parse CSS content using cssutils."""
        try:
            import cssutils
            # Suppress cssutils warnings
            cssutils.log.setLevel("ERROR")
            return cssutils.parseString(content)
        except ImportError as e:
            logger.error(f"cssutils not available: {e}")
            raise

    def extract_rules(self, sheet: Any) -> list[CSSRule]:
        """Extract CSS rules from cssutils parsed data."""
        import cssutils
        extracted = []

        for rule in sheet.cssRules:
            if rule.type == cssutils.css.CSSRule.STYLE_RULE:
                extracted.append(CSSRule(rule.selectorText, rule.cssText))

        return extracted


class SCSSPreprocessor:
    """Convert SCSS to CSS for parsing."""

    def __init__(self, strategy: str = "minimal") -> None:
        """Initialize SCSS preprocessor with strategy."""
        self.strategy = strategy

    def process(self, scss_content: str) -> str:
        """Convert SCSS to CSS."""
        if self.strategy == "external":
            return self._external_sass_compiler(scss_content)
        if self.strategy == "minimal":
            return self._minimal_scss_processing(scss_content)
        # Try to determine if it's simple CSS or needs processing
        if "$" in scss_content or ("&" in scss_content and "{" in scss_content):
            # Has SCSS features, use minimal processing
            return self._minimal_scss_processing(scss_content)
        # Pass through as CSS (for simple cases)
        return scss_content

    def _external_sass_compiler(self, scss_content: str) -> str:
        """Use external sass compiler."""
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".scss", delete=False) as f:
                f.write(scss_content)
                f.flush()

                result = subprocess.run(
                    ["sass", "--no-source-map", f.name],
                    check=False, capture_output=True,
                    text=True,
                    timeout=30
                )

                if result.returncode == 0:
                    return result.stdout
                logger.warning(f"SASS compilation failed: {result.stderr}")
                raise subprocess.CalledProcessError(result.returncode, "sass")

        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
            logger.warning(f"External SASS compiler failed: {e}")
            return self._minimal_scss_processing(scss_content)

    def _minimal_scss_processing(self, scss_content: str) -> str:
        """Basic SCSS-to-CSS conversion for simple cases."""
        import re

        # Remove SCSS variables (convert to CSS custom properties)
        content = re.sub(r"^\s*\$([a-zA-Z-]+)\s*:\s*(.*?);",
                        r"  --\1: \2;", scss_content, flags=re.MULTILINE)

        # Convert SCSS variable usage to CSS custom properties
        content = re.sub(r"\$([a-zA-Z-]+)", r"var(--\1)", content)

        # Remove SCSS imports (keep only CSS imports)
        content = re.sub(r'@import\s+["\'](?!.*\.css)[^"\']*["\'];?', "", content)

        return content


class StyleClassifier:
    """Classify CSS/SCSS rules to determine if they should be migrated to Site Builder."""

    # Patterns for styles that MUST NOT be migrated to Site Builder
    # These conflict with Site Builder's own components
    HEADER_PATTERNS = [
        r"header",          # Match 'header' anywhere - catches #header, #desktopHeader, #mobileHeader, .header-top, etc.
        r"\.masthead",
        r"\.banner"
    ]

    NAVIGATION_PATTERNS = [
        r"\.nav\b",         # Match .nav followed by word boundary (catches .nav, .nav-anything, etc.)
        r"\.nav-",          # Match .nav- followed by anything (.nav-item, .nav-link, etc.)
        r"\.navbar",        # Match .navbar followed by anything (.navbar, .navbar-inner, etc.)
        r"navbar",          # Match 'navbar' anywhere - catches .navbar, #navbar, etc.
        r"navigation",      # Match 'navigation' anywhere - catches .navigation, #navigation, etc.
        r"\.menu",
        r"\.breadcrumb",
        r"ul\.nav",         # Common pattern for nav lists
        r"li\.nav",         # Navigation list items
        r"\.megamenu",      # Megamenu patterns
        r"\.dropdown-menu", # Dropdown navigation
        r"\.sub-menu"       # Submenu patterns
    ]

    FOOTER_PATTERNS = [
        r"footer",        # Match 'footer' anywhere - catches #footer, #footerTop, #bb-footer, .footer-wrap, etc.
        r"\.main-footer",
        r"\.site-footer", 
        r"\.page-footer",
        r"\.bottom-footer",
        r"\.footer-content"
    ]

    def __init__(self, strict_mode: bool = True) -> None:
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

    def _compile_patterns(self) -> list[re.Pattern]:
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
        Remove excluded styles from SCSS content with improved multiline rule handling.

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

        # Track current rule context with improved multiline handling
        current_rule = []
        brace_depth = 0
        in_rule = False
        rule_start_line = 0

        # Simple line-by-line processing with orphaned property filtering
        skip_next_lines = 0
        
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            
            # Skip lines that were marked for skipping
            if skip_next_lines > 0:
                skip_next_lines -= 1
                i += 1
                continue
            
            # Skip empty lines and comments
            if not stripped or stripped.startswith(('//','/*')):
                filtered_lines.append(line)
                i += 1
                continue
            
            # Check for orphaned CSS properties (properties without selectors)
            if (':' in stripped and not stripped.startswith(('$', '@', '//')) 
                and not stripped.endswith(',') and '{' not in stripped
                and not any(stripped.startswith(sel) for sel in ['.', '#', '&', '*', '[', '::', '::before', '::after', '@media', '@supports'])):
                # This looks like an orphaned CSS property - skip it
                i += 1
                continue
            
            # Check if this line contains navigation/header/footer patterns that should be excluded
            should_exclude_line = False
            reason = None
            
            for pattern in self.NAVIGATION_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    should_exclude_line = True
                    reason = "navigation"
                    break
                    
            if not should_exclude_line:
                for pattern in self.HEADER_PATTERNS:
                    if re.search(pattern, line, re.IGNORECASE):
                        should_exclude_line = True
                        reason = "header"
                        break
                        
            if not should_exclude_line:
                for pattern in self.FOOTER_PATTERNS:
                    if re.search(pattern, line, re.IGNORECASE):
                        should_exclude_line = True
                        reason = "footer"
                        break
            
            if should_exclude_line:
                # Found a line that should be excluded - now determine how much to skip
                if '{' in line:
                    # This line starts a rule block - skip until the matching closing brace
                    brace_count = line.count('{') - line.count('}')
                    rule_lines = [line]
                    j = i + 1
                    
                    while j < len(lines) and brace_count > 0:
                        next_line = lines[j]
                        rule_lines.append(next_line)
                        brace_count += next_line.count('{') - next_line.count('}')
                        j += 1
                    
                    # Skip this entire rule block
                    excluded_rules.append('\n'.join(rule_lines))
                    patterns_matched[reason] = patterns_matched.get(reason, 0) + 1
                    self._exclusion_stats[reason] += 1
                    skip_next_lines = j - i - 1
                else:
                    # Single line to exclude
                    excluded_rules.append(line)
                    patterns_matched[reason] = patterns_matched.get(reason, 0) + 1
                    self._exclusion_stats[reason] += 1
                    
                i += 1
                continue
            
            # Line is not excluded - include it
            filtered_lines.append(line)
            i += 1

        # Update stats
        self._exclusion_stats["total_excluded"] = len(excluded_rules)
        self._exclusion_stats["total_processed"] += 1

        filtered_content = "\n".join(filtered_lines)

        result = ExclusionResult(
            excluded_count=len(excluded_rules),
            included_count=len([line for line in lines if line.strip()]) - len(excluded_rules),
            excluded_rules=excluded_rules,
            patterns_matched=patterns_matched
        )

        # Log exclusion summary
        if excluded_rules:
            exclusion_summary = ", ".join([f"{k}: {v}" for k, v in patterns_matched.items()])
            logger.info(f"Excluded {len(excluded_rules)} rules: {exclusion_summary}")

        return filtered_content, result

    def _should_exclude_selectors(self, selectors: str) -> tuple[bool, str | None]:
        """Check if ANY selector in comma-separated list should be excluded."""
        # Handle malformed rules that mix selectors with media queries
        if "@media" in selectors or "@supports" in selectors:
            # This is a malformed rule mixing selectors with at-rules - exclude it
            # Check if any part contains navigation patterns before excluding
            for pattern in self.NAVIGATION_PATTERNS:
                compiled_pattern = re.compile(pattern, re.IGNORECASE)
                if compiled_pattern.search(selectors):
                    return True, "navigation"
            for pattern in self.HEADER_PATTERNS:
                compiled_pattern = re.compile(pattern, re.IGNORECASE)
                if compiled_pattern.search(selectors):
                    return True, "header"
            for pattern in self.FOOTER_PATTERNS:
                compiled_pattern = re.compile(pattern, re.IGNORECASE)
                if compiled_pattern.search(selectors):
                    return True, "footer"
            return True, "malformed"  # Exclude malformed rules regardless
        
        # Handle orphaned CSS properties (properties without selectors)
        if selectors.strip().startswith(("color:", "font-", "display:", "background:", "border:", "margin:", "padding:", "width:", "height:", "position:", "top:", "left:", "right:", "bottom:")):
            return True, "orphaned_property"
        
        # Split comma-separated selectors and check each one
        individual_selectors = [s.strip() for s in selectors.split(",") if s.strip()]
        
        for selector in individual_selectors:
            should_exclude, reason = self.should_exclude_rule(selector)
            if should_exclude:
                return True, reason  # If ANY selector matches, exclude entire rule
        
        return False, None

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

    def get_exclusion_stats(self) -> dict[str, int]:
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


class ProfessionalStyleClassifier(StyleClassifier):
    """Professional CSS parser-based style classifier."""

    def __init__(self, parser_strategy: str = "auto", strict_mode: bool = True) -> None:
        """Initialize professional style classifier."""
        super().__init__(strict_mode)
        self.parser = self._create_parser(parser_strategy)
        self.scss_preprocessor = SCSSPreprocessor()

    def filter_scss_content(self, content: str) -> tuple[str, ExclusionResult]:
        """Filter SCSS content using professional parsing."""
        if not content.strip():
            return content, ExclusionResult(0, 0, [], {})

        try:
            # Step 1: Preprocess SCSS to CSS
            css_content = self.scss_preprocessor.process(content)

            # Step 2: Parse with professional library
            parsed_data = self.parser.parse_stylesheet(css_content)
            rules = self.parser.extract_rules(parsed_data)

            # Step 3: Apply exclusion logic
            return self._filter_parsed_rules(rules, content)

        except Exception as e:
            logger.warning(f"Professional parsing failed: {e}, using fallback")
            return self._fallback_processing(content)

    def _filter_parsed_rules(self, rules: list[CSSRule], original_content: str) -> tuple[str, ExclusionResult]:
        """Apply exclusion logic to parsed CSS rules."""
        filtered_rules = []
        excluded_rules = []
        patterns_matched = {}

        for rule in rules:
            should_exclude, reason = self._should_exclude_rule_selectors(rule.selectors)

            if should_exclude:
                excluded_rules.append(rule.css_text)
                patterns_matched[reason] = patterns_matched.get(reason, 0) + 1
                self._exclusion_stats[reason] += 1
                logger.debug(f"Excluded {reason} rule: {rule.selectors}")
            else:
                filtered_rules.append(rule.css_text)

        # Preserve non-rule content (variables, comments, imports)
        filtered_content = self._merge_with_non_rule_content(
            original_content, filtered_rules
        )

        result = ExclusionResult(
            excluded_count=len(excluded_rules),
            included_count=len(filtered_rules),
            excluded_rules=excluded_rules,
            patterns_matched=patterns_matched
        )

        # Log exclusion summary
        if excluded_rules:
            exclusion_summary = ", ".join([f"{k}: {v}" for k, v in patterns_matched.items()])
            logger.info(f"Excluded {len(excluded_rules)} rules: {exclusion_summary}")

        return filtered_content, result

    def _should_exclude_rule_selectors(self, selectors: str) -> tuple[bool, str | None]:
        """Check if ANY selector in comma-separated list should be excluded."""
        # Handle malformed rules that mix selectors with media queries
        if "@media" in selectors or "@supports" in selectors:
            # This is a malformed rule mixing selectors with at-rules - exclude it
            # Check if any part contains navigation patterns before excluding
            for pattern in self.NAVIGATION_PATTERNS:
                compiled_pattern = re.compile(pattern, re.IGNORECASE)
                if compiled_pattern.search(selectors):
                    return True, "navigation"
            for pattern in self.HEADER_PATTERNS:
                compiled_pattern = re.compile(pattern, re.IGNORECASE)
                if compiled_pattern.search(selectors):
                    return True, "header"
            for pattern in self.FOOTER_PATTERNS:
                compiled_pattern = re.compile(pattern, re.IGNORECASE)
                if compiled_pattern.search(selectors):
                    return True, "footer"
            return True, "malformed"  # Exclude malformed rules regardless
        
        # Handle orphaned CSS properties (properties without selectors)
        if selectors.strip().startswith(("color:", "font-", "display:", "background:", "border:", "margin:", "padding:", "width:", "height:", "position:", "top:", "left:", "right:", "bottom:")):
            return True, "orphaned_property"
        
        # Split comma-separated selectors and check each one
        individual_selectors = [s.strip() for s in selectors.split(",")]

        for selector in individual_selectors:
            should_exclude, reason = self.should_exclude_rule(selector)
            if should_exclude:
                return True, reason  # If ANY selector matches, exclude entire rule

        return False, None

    def _merge_with_non_rule_content(self, original_content: str, filtered_rules: list[str]) -> str:
        """Merge filtered rules with non-rule content from original."""
        # This is a simplified approach - in practice, we'd need more sophisticated
        # reconstruction of the original structure
        lines = original_content.split("\n")
        result_lines = []

        # Extract variables, imports, and comments
        for line in lines:
            stripped = line.strip()
            if (stripped.startswith("$") or
                stripped.startswith("@import") or
                stripped.startswith("//") or
                stripped.startswith("/*") or
                not stripped):
                result_lines.append(line)

        # Add filtered rules
        result_lines.extend(filtered_rules)

        return "\n".join(result_lines)

    def _create_parser(self, strategy: str) -> CSSParser:
        """Factory method for CSS parser selection."""
        if strategy == "tinycss2":
            return TinyCSS2Parser()
        if strategy == "cssutils":
            return CSSUtilsParser()
        if strategy == "auto":
            # Try tinycss2 first, fallback to cssutils
            try:
                import tinycss2
                return TinyCSS2Parser()
            except ImportError:
                try:
                    import cssutils
                    return CSSUtilsParser()
                except ImportError:
                    raise ImportError("No CSS parsing library available")
        else:
            raise ValueError(f"Unknown parser strategy: {strategy}")

    def _fallback_processing(self, content: str) -> tuple[str, ExclusionResult]:
        """Conservative fallback when professional parsing fails."""
        logger.warning("Using conservative line-by-line exclusion fallback")

        # Use original StyleClassifier logic as ultimate fallback
        return super().filter_scss_content(content)


def robust_css_processing(content: str) -> tuple[str, ExclusionResult]:
    """Multi-layer error handling with graceful degradation."""

    # Layer 1: Professional parsing
    try:
        classifier = ProfessionalStyleClassifier(parser_strategy="auto")
        return classifier.filter_scss_content(content)
    except ImportError as e:
        logger.error(f"No professional CSS parser available: {e}")
    except Exception as e:
        logger.warning(f"Professional CSS parsing failed: {e}")

    # Layer 2: Original implementation
    try:
        classifier = StyleClassifier()  # Original implementation
        return classifier.filter_scss_content(content)
    except Exception as e:
        logger.error(f"Original CSS parsing failed: {e}")

    # Layer 3: Conservative keyword-based exclusion
    logger.error("All CSS parsing failed, using conservative keyword exclusion")
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
            if '{' in line:
                # This line starts a rule block - skip until the matching closing brace
                brace_count = line.count('{') - line.count('}')
                rule_lines = [line]
                j = i + 1
                
                while j < len(lines) and brace_count > 0:
                    next_line = lines[j]
                    rule_lines.append(next_line)
                    brace_count += next_line.count('{') - next_line.count('}')
                    j += 1
                
                # Skip this entire rule block
                excluded_rules.append('\n'.join(rule_lines))
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
